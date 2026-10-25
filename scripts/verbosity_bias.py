"""
Verbosity-bias test for the LLM judge (brief: "make an answer longer
without making it better. Does the grade go up?").

Step 1 -- build padded copies of the items (no API calls):
    python scripts/verbosity_bias.py make --split dev

  Writes data/bias/verbosity_padded.jsonl. Each item keeps its customer
  message and policy excerpt; the reply is wrapped in filler that adds no
  policy claims, no next steps and no extra warmth, so a correct judge
  should give exactly the same grades. Padded ids end in "~pad".

Step 2 -- judge originals and padded copies with the normal harness:
    python -m harness.run --system llm_judge --items data/golden_set.jsonl --split dev
    python -m harness.run --system llm_judge --items data/bias/verbosity_padded.jsonl

  (Free tier: add --resume <results file> to finish either run later.)

Step 3 -- compare:
    python scripts/verbosity_bias.py report \
        --original results/llm_judge_dev_<ts>.jsonl \
        --padded results/llm_judge_<ts>.jsonl

  Writes data/verbosity_bias_report.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

GOLDEN_SET = REPO_ROOT / "data" / "golden_set.jsonl"
SPLITS_PATH = REPO_ROOT / "data" / "splits.json"
PADDED_PATH = REPO_ROOT / "data" / "bias" / "verbosity_padded.jsonl"
REPORT_PATH = REPO_ROOT / "data" / "verbosity_bias_report.md"
AXES = ["correctness", "politeness", "completeness"]
PAD_SUFFIX = "~pad"


def rel(path: Path) -> Path:
    """Path relative to the repo for display, or as-is if outside it."""
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path

# Content-free filler: describes the reply itself, makes no claim about
# policy, orders or timeframes, gives no next step, adds no empathy.
PAD_PREFIX = (
    "This message is a reply to the request you sent to TechNest Gadgets "
    "customer support. The reply to your request is set out below, and it "
    "addresses the request described in your message.\n\n"
)
PAD_SUFFIX_TEXT = (
    "\n\nThe text above is the reply to the request described in your "
    "message. It has been written in response to that request and it "
    "covers the request that your message describes. This is the end of "
    "the reply to your request."
)


def pad_reply(reply: str) -> str:
    return PAD_PREFIX + reply + PAD_SUFFIX_TEXT


def make(args):
    with open(args.items, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    if args.split:
        assignments = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))["items"]
        items = [i for i in items if assignments.get(i["item_id"]) == args.split]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for item in items:
            padded = {
                "item_id": item["item_id"] + PAD_SUFFIX,
                "customer_message": item["customer_message"],
                "policy_excerpt": item["policy_excerpt"],
                "candidate_reply": pad_reply(item["candidate_reply"]),
                "original_item_id": item["item_id"],
                "original_length": len(item["candidate_reply"]),
            }
            f.write(json.dumps(padded, ensure_ascii=False) + "\n")

    added = len(PAD_PREFIX) + len(PAD_SUFFIX_TEXT)
    print(f"Wrote {len(items)} padded items to {rel(args.out)} (+{added} chars each)")


def load_scores(path: Path) -> dict[str, dict | None]:
    scores = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                out = row.get("output")
                scores[row["item_id"]] = {a: out[a] for a in AXES} if out else None
    return scores


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else f"{n}/0"


def report(args):
    original = load_scores(args.original)
    padded = {k.removesuffix(PAD_SUFFIX): v for k, v in load_scores(args.padded).items()}

    both = sorted(k for k in padded if original.get(k) and padded.get(k))
    missing = sorted(k for k in padded if not (original.get(k) and padded.get(k)))

    changes = {a: Counter() for a in AXES}
    total_change = Counter()
    rows = []
    for item_id in both:
        o, p = original[item_id], padded[item_id]
        diffs = {a: p[a] - o[a] for a in AXES}
        for a, d in diffs.items():
            changes[a]["up" if d > 0 else "down" if d < 0 else "same"] += 1
        t = sum(diffs.values())
        total_change["up" if t > 0 else "down" if t < 0 else "same"] += 1
        if any(diffs.values()):
            rows.append(
                f"| {item_id} | "
                + " | ".join(f"{o[a]} → {p[a]}" for a in AXES)
                + f" | {t:+d} |"
            )

    n = len(both)
    out = [
        "# Verbosity Bias Report (padded vs. original replies)",
        "",
        f"Original run: `{args.original.name}`, padded run: `{args.padded.name}`.",
        "",
        f"Each padded reply is the original reply plus {len(PAD_PREFIX) + len(PAD_SUFFIX_TEXT)} characters",
        "of filler that adds no policy claim, no next step and no extra warmth",
        "(see `scripts/verbosity_bias.py`). A judge with no verbosity bias gives",
        "every padded reply the same grades as the original.",
        "",
        "## Summary",
        "",
        f"Items compared: {n}. Excluded (a parse error or missing from one run): {len(missing)}.",
        "",
        "| Axis | Grade went up | Unchanged | Grade went down |",
        "|---|---|---|---|",
    ]
    for a in AXES:
        c = changes[a]
        out.append(f"| {a} | {pct(c['up'], n)} | {pct(c['same'], n)} | {pct(c['down'], n)} |")
    c = total_change
    out.append(f"| **total (sum of axes)** | {pct(c['up'], n)} | {pct(c['same'], n)} | {pct(c['down'], n)} |")
    out += [
        "",
        "A grade going *up* is verbosity bias. A grade going *down* means the judge",
        "penalises filler, which is defensible for completeness/politeness but",
        "should not happen for correctness.",
        "",
        "## Items whose grade changed",
        "",
        "| Item | Correctness | Politeness | Completeness | Total |",
        "|---|---|---|---|---|",
        *(rows or ["| (none) | | | | |"]),
        "",
    ]
    if missing:
        out += [f"Excluded items: {', '.join(missing)}", ""]

    text = "\n".join(out)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {rel(args.out)}\n")
    print(text.split("## Items whose")[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_make = sub.add_parser("make", help="Write padded copies of the items")
    p_make.add_argument("--items", type=Path, default=GOLDEN_SET)
    p_make.add_argument("--split", choices=["dev", "test"], default=None)
    p_make.add_argument("--out", type=Path, default=PADDED_PATH)
    p_make.set_defaults(func=make)

    p_report = sub.add_parser("report", help="Compare judge results on original vs. padded items")
    p_report.add_argument("--original", type=Path, required=True)
    p_report.add_argument("--padded", type=Path, required=True)
    p_report.add_argument("--out", type=Path, default=REPORT_PATH)
    p_report.set_defaults(func=report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
