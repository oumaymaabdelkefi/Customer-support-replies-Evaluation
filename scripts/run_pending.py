"""
Run every measurement that is still missing, in priority order, resuming
each from its last partial results file. Stops cleanly when the Groq free
tier's daily quota runs out; run it again the next day (or press
"Continue pending runs" in the interface) and it picks up where it
stopped. With a paid key it simply runs everything.

    python scripts/run_pending.py            # run what's pending
    python scripts/run_pending.py --status   # only show what's done / pending

Order (most important first):
  1. judge_v2 on dev                 -> decides the final judge version
  2. adversarial set                 -> "where the judge fails" (demo day)
  3. final judge on the test split   -> reported judge reliability
  4. verbosity bias (dev, padded)    -> second bias check
  5. reply system v1 on dev          -> system score before prompt changes
  6. reply system v2 on dev          -> score after (if prompts/system_v2.txt exists)
  7. best reply system on test       -> reported system score

The final judge is whichever of judge v1 / v2 agrees more with the gold
labels on dev (mean kappa over the three axes); later steps grade with it
via JUDGE_PROMPT_VERSION.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from judge_reliability import build_report, load_human_labels, load_judge_results  # noqa: E402

RESULTS = REPO_ROOT / "results"
DATA = REPO_ROOT / "data"
GOLDEN = DATA / "golden_set.jsonl"
PADDED = DATA / "bias" / "verbosity_padded.jsonl"
ADVERSARIAL = DATA / "bias" / "adversarial.jsonl"
AXES = ["correctness", "politeness", "completeness"]


def item_ids(items: Path, split: str | None) -> set[str]:
    ids = {json.loads(l)["item_id"] for l in open(items, encoding="utf-8") if l.strip()}
    if split:
        assignments = json.loads((DATA / "splits.json").read_text(encoding="utf-8"))["items"]
        ids = {i for i in ids if assignments.get(i) == split}
    return ids


def runs_for(system: str, split: str | None) -> list[Path]:
    tag = f"{system}_{split}" if split else system
    pattern = re.compile(rf"^{re.escape(tag)}_\d+\.jsonl$")
    return sorted((p for p in RESULTS.glob("*.jsonl") if pattern.match(p.name)), key=lambda p: p.stat().st_mtime)


def best_run(system: str, items: Path, split: str | None) -> tuple[Path | None, int, int]:
    """Newest run of `system` over exactly these items; (path, scored, total)."""
    wanted = item_ids(items, split)
    for path in reversed(runs_for(system, split)):
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        if {r["item_id"] for r in rows} == wanted:
            return path, sum(1 for r in rows if r.get("output")), len(wanted)
    return None, 0, len(wanted)


def mean_kappa_vs_gold(path: Path) -> float | None:
    report = build_report(load_judge_results(path), load_human_labels(DATA / "gold_labels.csv"))
    ks = [float(m.group(1)) for m in re.finditer(r"\| \d+/\d+ \(\d+%\) \| (-?[\d.]+) \|", report)]
    return sum(ks) / len(ks) if len(ks) == 3 else None


def final_judge_version() -> int:
    scores = {}
    for version, system in [(1, "llm_judge"), (2, "llm_judge_v2")]:
        path, scored, total = best_run(system, GOLDEN, "dev")
        if path and scored == total:
            scores[version] = mean_kappa_vs_gold(path)
    if 2 in scores and 1 in scores and scores[2] is not None and scores[1] is not None:
        return 2 if scores[2] > scores[1] else 1
    return 1


def mean_total_score(path: Path) -> float:
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    totals = [sum(r["output"][a] for a in AXES) for r in rows if r.get("output")]
    return sum(totals) / len(totals) if totals else 0.0


def steps() -> list[dict]:
    judge_v = final_judge_version()
    judge_sys = "llm_judge" if judge_v == 1 else "llm_judge_v2"
    out = [
        {"name": "judge_v2 on dev", "system": "llm_judge_v2", "items": GOLDEN, "split": "dev"},
        {"name": f"adversarial set (judge v{judge_v})", "system": judge_sys, "items": ADVERSARIAL, "split": None,
         "before": [[sys.executable, "scripts/make_adversarial_set.py"]]},
        {"name": f"judge v{judge_v} on test", "system": judge_sys, "items": GOLDEN, "split": "test"},
        {"name": f"verbosity bias, padded dev (judge v{judge_v})", "system": judge_sys, "items": PADDED,
         "split": None, "before": [[sys.executable, "scripts/verbosity_bias.py", "make", "--split", "dev"]]},
        {"name": "reply system v1 on dev", "system": "reply_v1", "items": GOLDEN, "split": "dev", "judge_v": judge_v},
    ]
    if (REPO_ROOT / "prompts" / "system_v2.txt").exists():
        out.append({"name": "reply system v2 on dev", "system": "reply_v2", "items": GOLDEN, "split": "dev",
                    "judge_v": judge_v})
    # Best system version on dev (complete runs only) goes to test.
    best, best_score = "reply_v1", -1.0
    for system in ("reply_v1", "reply_v2"):
        path, scored, total = best_run(system, GOLDEN, "dev")
        if path and scored == total and mean_total_score(path) > best_score:
            best, best_score = system, mean_total_score(path)
    out.append({"name": f"{best} on test", "system": best, "items": GOLDEN, "split": "test", "judge_v": judge_v})
    return out


def ensure_padded_set():
    """The padded set must cover the current dev split; rebuild if stale."""
    wanted = {i + "~pad" for i in item_ids(GOLDEN, "dev")}
    have = item_ids(PADDED, None) if PADDED.exists() else set()
    if have != wanted:
        subprocess.run([sys.executable, "scripts/verbosity_bias.py", "make", "--split", "dev"], cwd=REPO_ROOT, check=True)


def latest_any_run(system: str, items: Path, split: str | None) -> Path | None:
    """Newest run (any item set) to resume from: reused only where item text matches."""
    path, _, _ = best_run(system, items, split)
    if path:
        return path
    runs = runs_for(system, split)
    return runs[-1] if runs else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if not args.status:
        ensure_padded_set()
    n_steps = len(steps())
    for index in range(n_steps):
        plan = steps()  # re-plan: a finished step can change the final judge or best system
        if index >= len(plan):
            break
        step = plan[index]
        path, scored, total = best_run(step["system"], step["items"], step["split"])
        state = "done" if path and scored == total else f"{scored}/{total} scored" if path else "not started"
        print(f"[{state:>14}] {step['name']}")
        if args.status or state == "done":
            continue

        for cmd in step.get("before", []):
            subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        cmd = [sys.executable, "-u", "-m", "harness.run", "--system", step["system"], "--items",
               str(step["items"].relative_to(REPO_ROOT))]
        if step["split"]:
            cmd += ["--split", step["split"]]
        resume = latest_any_run(step["system"], step["items"], step["split"])
        if resume:
            cmd += ["--resume", str(resume.relative_to(REPO_ROOT))]
        env = dict(os.environ)
        if "judge_v" in step:
            env["JUDGE_PROMPT_VERSION"] = str(step["judge_v"])
        print("  $ " + " ".join(cmd[3:]), flush=True)
        proc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = [l for l in proc.stdout.splitlines() if "rate-limited" not in l][-12:]
        print("\n".join("    " + l for l in tail), flush=True)
        if "quota exhausted" in proc.stderr.lower() or "quota exhausted" in proc.stdout.lower():
            print("\nGroq daily quota used up -- run this again tomorrow (or with a paid key) to continue.")
            return
        if proc.returncode != 0:
            print(proc.stderr[-2000:])
            return
    print("\nAll pending runs are done." if not args.status else "")


if __name__ == "__main__":
    main()
