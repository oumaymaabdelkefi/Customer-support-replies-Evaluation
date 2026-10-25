"""
Position-bias test for the LLM judge (brief: "when comparing two answers,
swap the order. Does the verdict change?").

Pairs: every two golden-set items that answer the same customer message
with the same policy excerpt (e.g. P01/P02). Each pair is judged twice
with prompts/pairwise_v1.txt, once as (A=first, B=second) and once
swapped. A judge without position bias picks the same *reply* both times.

Usage:
    python scripts/position_bias.py                      # run + report
    python scripts/position_bias.py --resume results/position_bias_<ts>.jsonl
    python scripts/position_bias.py --report-only results/position_bias_<ts>.jsonl

Writes results/position_bias_<ts>.jsonl (one row per judge call) and
data/position_bias_report.md. Uses the Groq free tier like the main
judge: if the daily quota runs out, the run stops and --resume finishes
it later without repeating calls that already succeeded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from harness.errors import QuotaExhausted  # noqa: E402
from harness.systems import judge_stub  # noqa: E402

GOLDEN_SET = REPO_ROOT / "data" / "golden_set.jsonl"
PROMPT_PATH = REPO_ROOT / "prompts" / "pairwise_v1.txt"
RESULTS_DIR = REPO_ROOT / "results"
REPORT_PATH = REPO_ROOT / "data" / "position_bias_report.md"


def rel(path: Path) -> Path:
    """Path relative to the repo for display, or as-is if outside it."""
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path

PAIRWISE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "pairwise_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "winner": {"type": "string", "enum": ["A", "B", "tie"]},
                "reason": {"type": "string"},
            },
            "required": ["winner", "reason"],
            "additionalProperties": False,
        },
    },
}


def build_pairs(items: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for item in items:
        message = " ".join(item["customer_message"].lower().split())
        groups[(message, item["policy_excerpt"])].append(item)

    pairs = []
    for members in groups.values():
        members.sort(key=lambda i: i["item_id"])
        for first, second in combinations(members, 2):
            pairs.append(
                {
                    "pair_id": f"{first['item_id']}|{second['item_id']}",
                    "customer_message": first["customer_message"],
                    "policy_excerpt": first["policy_excerpt"],
                    "items": {
                        first["item_id"]: first["candidate_reply"],
                        second["item_id"]: second["candidate_reply"],
                    },
                }
            )
    return sorted(pairs, key=lambda p: p["pair_id"])


def judge_once(template: str, pair: dict, order: str) -> dict:
    """order 'AB' shows the pair's first item as reply A; 'BA' swaps."""
    first, second = list(pair["items"])
    item_a, item_b = (first, second) if order == "AB" else (second, first)
    prompt = template.format(
        customer_message=pair["customer_message"],
        policy_excerpt=pair["policy_excerpt"],
        reply_a=pair["items"][item_a],
        reply_b=pair["items"][item_b],
    )
    row = {"pair_id": pair["pair_id"], "order": order, "item_a": item_a, "item_b": item_b}
    try:
        verdict = judge_stub.call_groq(prompt, PAIRWISE_RESPONSE_FORMAT, f"{pair['pair_id']} {order}")
    except QuotaExhausted:
        raise
    except Exception as e:  # noqa: BLE001 -- one bad call must not end the run
        return {**row, "error": str(e)}
    row["meta"] = verdict.pop("_meta", None)
    winner = verdict.get("winner")
    if winner not in ("A", "B", "tie"):
        return {**row, "error": f"invalid verdict: {verdict}"}
    row["winner_position"] = winner
    row["winner_item"] = {"A": item_a, "B": item_b, "tie": "tie"}[winner]
    row["reason"] = verdict.get("reason")
    return row


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else f"{n}/0"


def render_report(rows: list[dict], results_path: Path) -> str:
    ok = [r for r in rows if "error" not in r]
    by_pair: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in ok:
        by_pair[r["pair_id"]][r["order"]] = r

    complete = {p: v for p, v in by_pair.items() if {"AB", "BA"} <= v.keys()}
    consistent = flipped = 0
    lines_table = []
    for pair_id, v in sorted(complete.items()):
        same = v["AB"]["winner_item"] == v["BA"]["winner_item"]
        consistent += same
        flipped += not same
        lines_table.append(
            f"| {pair_id} | {v['AB']['winner_item']} | {v['BA']['winner_item']} | "
            f"{'consistent' if same else '**flipped**'} |"
        )

    positions = Counter(r["winner_position"] for r in ok)
    decided = positions["A"] + positions["B"]
    costs = [r["meta"]["cost_usd"] for r in ok if r.get("meta")]
    latencies = sorted(r["meta"]["latency_s"] for r in ok if r.get("meta"))

    out = [
        "# Position Bias Report (pairwise judge, order swapped)",
        "",
        f"Source: `{rel(results_path)}`, "
        f"prompt `prompts/{PROMPT_PATH.name}`, model `{judge_stub.MODEL_NAME}`.",
        "",
        "Each pair of replies to the same customer message is judged twice, with the",
        "order swapped. A judge with no position bias picks the same reply both times.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Pairs judged in both orders | {len(complete)} |",
        f"| Same reply picked in both orders | {pct(consistent, len(complete))} |",
        f"| Verdict changed after swap | {pct(flipped, len(complete))} |",
        f"| Calls where the first-shown reply (A) won | {pct(positions['A'], decided)} of non-tie calls |",
        f"| Tie verdicts | {pct(positions['tie'], len(ok))} of calls |",
        f"| Failed calls (excluded) | {len(rows) - len(ok)} |",
    ]
    if costs:
        out.append(f"| Cost per call (paid-tier equivalent) | ${sum(costs) / len(costs):.6f} |")
    if latencies:
        out.append(f"| Latency per call, p50 | {latencies[len(latencies) // 2]:.2f}s |")
    out += [
        "",
        "With no position bias, A should win about half of the non-tie calls, and",
        "no verdict should change after the swap.",
        "",
        "## Per pair",
        "",
        "| Pair | Winner (first item shown as A) | Winner (swapped) | Result |",
        "|---|---|---|---|",
        *lines_table,
        "",
    ]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=Path, default=GOLDEN_SET)
    parser.add_argument("--resume", type=Path, default=None, help="Earlier position_bias results to continue")
    parser.add_argument("--report-only", type=Path, default=None, help="Only write the report from this results file")
    parser.add_argument("--out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    if args.report_only:
        results_path = args.report_only
        rows = load_rows(results_path)
    else:
        with open(args.items, encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
        pairs = build_pairs(items)
        template = PROMPT_PATH.read_text(encoding="utf-8")
        done = {}
        if args.resume:
            done = {(r["pair_id"], r["order"]): r for r in load_rows(args.resume) if "error" not in r}
        print(f"{len(pairs)} pairs, {2 * len(pairs)} judge calls ({len(done)} reused)")

        rows = []
        quota_hit = False
        for pair in pairs:
            for order in ("AB", "BA"):
                if (pair["pair_id"], order) in done:
                    rows.append(done[(pair["pair_id"], order)])
                    continue
                if quota_hit:
                    rows.append({"pair_id": pair["pair_id"], "order": order, "error": "skipped: quota exhausted"})
                    continue
                try:
                    rows.append(judge_once(template, pair, order))
                except QuotaExhausted as e:
                    print(f"\n{e}\nSkipping the remaining calls; finish later with --resume.", file=sys.stderr)
                    quota_hit = True
                    rows.append({"pair_id": pair["pair_id"], "order": order, "error": "skipped: quota exhausted"})

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        results_path = RESULTS_DIR / f"position_bias_{int(time.time())}.jsonl"
        with open(results_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Wrote {rel(results_path)}")

    report = render_report(rows, results_path)
    args.out.write_text(report, encoding="utf-8")
    print(f"Wrote {rel(args.out)}\n")
    print(report.split("## Per pair")[0])


if __name__ == "__main__":
    main()
