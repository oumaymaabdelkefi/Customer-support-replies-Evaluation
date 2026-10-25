"""
Judge reliability report: compares the LLM judge's scores against a human
labeler's scores on the same items, using Cohen's kappa per axis (same
metric and threshold as inter-annotator agreement -- the brief's target is
kappa >= 0.6, interpreted here the same way as human-vs-human agreement).

Usage:
    python scripts/judge_reliability.py \
        --judge-results results/llm_judge_<timestamp>.jsonl \
        --human-labels data/labelling_sheet_labeler1_completed.csv \
        --out data/judge_reliability_report.md

Notes:
- Only items present in BOTH files are compared. Items where the judge
  produced a parse_error (output is null) are counted and reported, but
  excluded from the kappa calculation -- a parse failure isn't a
  disagreement, it's missing data, and folding it into kappa would hide
  the failure rate rather than surface it.
- This does not replace human-vs-human kappa; it's a separate reliability
  check (judge-vs-human), which the brief also asks for.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

AXES = ["correctness", "politeness", "completeness"]


def load_judge_results(path: Path) -> dict[str, dict | None]:
    """item_id -> {axis: score} or None if the judge failed to parse."""
    out: dict[str, dict | None] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            item_id = row["item_id"]
            output = row.get("output")
            if output is None:
                out[item_id] = None
            else:
                out[item_id] = {axis: output[axis] for axis in AXES}
    return out


def load_human_labels(path: Path) -> dict[str, dict]:
    """item_id -> {axis: score}, skipping blank/NA cells per axis."""
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row["item_id"]
            scores = {}
            for axis in AXES:
                raw = row.get(f"{axis}_score_0_1_2", "").strip()
                scores[axis] = int(raw) if raw and raw.upper() != "NA" else None
            out[item_id] = scores
    return out


def cohen_kappa(pairs: list[tuple[int, int]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    categories = sorted({v for pair in pairs for v in pair})
    if len(categories) < 2:
        return 1.0  # everyone agreed on the single category used

    observed_agreement = sum(1 for a, b in pairs if a == b) / n

    a_counts = Counter(a for a, _ in pairs)
    b_counts = Counter(b for _, b in pairs)
    expected_agreement = sum(
        (a_counts[c] / n) * (b_counts[c] / n) for c in categories
    )

    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def interpret(kappa: float | None) -> str:
    if kappa is None:
        return "undefined (no comparable data)"
    if kappa < 0:
        return "poor (worse than chance)"
    if kappa < 0.2:
        return "slight"
    if kappa < 0.4:
        return "fair"
    if kappa < 0.6:
        return "moderate (below the 0.6 target)"
    if kappa < 0.8:
        return "substantial (meets the >= 0.6 target)"
    return "almost perfect (meets the >= 0.6 target)"


def build_report(judge: dict[str, dict | None], human: dict[str, dict]) -> str:
    common_ids = sorted(set(judge) & set(human))
    parse_failures = [i for i in common_ids if judge[i] is None]
    comparable_ids = [i for i in common_ids if judge[i] is not None]

    lines = [
        "# Judge Reliability Report (judge vs. human labels)",
        "",
        f"Items in both files: {len(common_ids)}",
        f"Judge parse failures (excluded from kappa): {len(parse_failures)}"
        + (f" ({', '.join(parse_failures)})" if parse_failures else ""),
        f"Items compared: {len(comparable_ids)}",
        "",
        "## Kappa per axis (judge vs. human)",
        "",
        "| Axis | N | Skipped (human NA/disputed) | Exact agreement | Kappa | Interpretation |",
        "|---|---|---|---|---|---|",
    ]

    disagreement_sections = []

    for axis in AXES:
        pairs = []
        skipped = 0
        disagreements = []
        for item_id in comparable_ids:
            h_score = human[item_id][axis]
            j_score = judge[item_id][axis]
            if h_score is None:
                skipped += 1
                continue
            pairs.append((h_score, j_score))
            if h_score != j_score:
                disagreements.append((item_id, h_score, j_score))

        kappa = cohen_kappa(pairs)
        kappa_str = f"{kappa:.3f}" if kappa is not None else "n/a"
        same = len(pairs) - len(disagreements)
        exact = f"{same}/{len(pairs)} ({same / len(pairs):.0%})" if pairs else "n/a"
        lines.append(
            f"| {axis} | {len(pairs)} | {skipped} | {exact} | {kappa_str} | {interpret(kappa)} |"
        )

        section = [f"### {axis} ({len(disagreements)} disagreements)", ""]
        if disagreements:
            section += ["| item_id | human | judge |", "|---|---|---|"]
            for item_id, h, j in disagreements:
                section.append(f"| {item_id} | {h} | {j} |")
        else:
            section.append("None.")
        disagreement_sections.append("\n".join(section))

    lines.append("")
    lines.append("## Disagreements by axis")
    lines.append("")
    lines.append("\n\n".join(disagreement_sections))

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-results", required=True, type=Path)
    parser.add_argument("--human-labels", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    judge = load_judge_results(args.judge_results)
    human = load_human_labels(args.human_labels)
    report = build_report(judge, human)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
