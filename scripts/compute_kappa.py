#!/usr/bin/env python3
"""
scripts/compute_kappa.py

Computes Cohen's kappa (per axis: correctness, politeness, completeness)
between two completed, independent labelling sheets, and lists every item
where the two labellers disagreed -- the input to your team's tie-break
discussion.

No external dependencies beyond the standard library, so it runs anywhere
the rest of scripts/ runs.

Usage:
    python scripts/compute_kappa.py \
        --labeler1 data/labelling_sheet_labeler1_completed.csv \
        --labeler2 data/labelling_sheet_labeler2_completed.csv \
        --out data/kappa_report.md

If --out is omitted, the report is only printed to stdout.

Expected CSV columns (same as data/labelling_sheet_labeler*.csv):
    item_id, batch, theme, customer_message, policy_excerpt,
    candidate_reply, correctness_score_0_1_2, politeness_score_0_1_2,
    completeness_score_0_1_2, labeller_notes

Rows with a blank score, or 'NA', on a given axis are excluded from that
axis's kappa calculation (per labelling_guide.md's "mark all three NA and
say why" rule for genuinely unjudgeable items) and reported separately,
not silently dropped.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

AXES = ["correctness", "politeness", "completeness"]
COLUMN_SUFFIX = "_score_0_1_2"


def load_sheet(path: Path) -> dict[str, dict]:
    """Returns {item_id: {axis: int|None, ...}}. None means blank/NA."""
    rows: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row["item_id"].strip()
            if not item_id:
                continue
            parsed = {}
            for axis in AXES:
                col = f"{axis}{COLUMN_SUFFIX}"
                raw = (row.get(col) or "").strip()
                if raw == "" or raw.upper() == "NA":
                    parsed[axis] = None
                else:
                    try:
                        parsed[axis] = int(raw)
                    except ValueError:
                        raise ValueError(
                            f"{path}: item {item_id}, column {col} has "
                            f"non-integer value {raw!r}"
                        )
            rows[item_id] = {
                "scores": parsed,
                "batch": row.get("batch", ""),
                "notes": row.get("labeller_notes", ""),
            }
    return rows


def cohen_kappa(pairs: list[tuple[int, int]]) -> float | None:
    """Cohen's kappa for a list of (rater1_score, rater2_score) pairs.
    Returns None if there's nothing to compute (e.g. zero pairs, or every
    label the same for both raters on every item with only one category
    seen -- kappa is undefined in that degenerate case)."""
    n = len(pairs)
    if n == 0:
        return None

    categories = sorted(set(a for a, _ in pairs) | set(b for _, b in pairs))
    if len(categories) < 2:
        return None  # only one score value ever appears; kappa undefined

    observed_agreement = sum(1 for a, b in pairs if a == b) / n

    rater1_counts = Counter(a for a, _ in pairs)
    rater2_counts = Counter(b for _, b in pairs)
    expected_agreement = sum(
        (rater1_counts.get(c, 0) / n) * (rater2_counts.get(c, 0) / n)
        for c in categories
    )

    if expected_agreement == 1:
        return 1.0  # both raters always picked the same single category

    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def interpret(kappa: float | None) -> str:
    if kappa is None:
        return "undefined (not enough variance to compute)"
    if kappa >= 0.8:
        return "almost perfect"
    if kappa >= 0.6:
        return "substantial (meets the >= 0.6 target)"
    if kappa >= 0.4:
        return "moderate (below the 0.6 target)"
    if kappa >= 0.2:
        return "fair (below the 0.6 target)"
    if kappa > 0:
        return "slight (below the 0.6 target)"
    return "at or below chance"


def build_report(sheet1: dict, sheet2: dict) -> str:
    common_ids = sorted(set(sheet1) & set(sheet2))
    only1 = sorted(set(sheet1) - set(sheet2))
    only2 = sorted(set(sheet2) - set(sheet1))

    lines = ["# Kappa Report\n"]

    if only1 or only2:
        lines.append("## Warning: item ID mismatch between sheets\n")
        if only1:
            lines.append(f"- Only in labeler 1: {', '.join(only1)}")
        if only2:
            lines.append(f"- Only in labeler 2: {', '.join(only2)}")
        lines.append("")

    lines.append(f"Items scored by both labellers: {len(common_ids)}\n")

    disagreements_by_axis: dict[str, list[str]] = {axis: [] for axis in AXES}

    lines.append("## Kappa per axis\n")
    lines.append("| Axis | N (both scored) | Skipped (NA/blank) | Kappa | Interpretation |")
    lines.append("|---|---|---|---|---|")

    for axis in AXES:
        pairs = []
        skipped = 0
        for item_id in common_ids:
            s1 = sheet1[item_id]["scores"][axis]
            s2 = sheet2[item_id]["scores"][axis]
            if s1 is None or s2 is None:
                skipped += 1
                continue
            pairs.append((s1, s2))
            if s1 != s2:
                disagreements_by_axis[axis].append(item_id)

        k = cohen_kappa(pairs)
        k_str = f"{k:.3f}" if k is not None else "n/a"
        lines.append(f"| {axis} | {len(pairs)} | {skipped} | {k_str} | {interpret(k)} |")

    lines.append("")
    lines.append("## Disagreements by axis\n")
    for axis in AXES:
        ids = disagreements_by_axis[axis]
        lines.append(f"### {axis} ({len(ids)} disagreement{'s' if len(ids) != 1 else ''})\n")
        if not ids:
            lines.append("None.\n")
            continue
        lines.append("| item_id | batch | labeler1 | labeler2 | labeler1 notes | labeler2 notes |")
        lines.append("|---|---|---|---|---|---|")
        for item_id in ids:
            s1 = sheet1[item_id]["scores"][axis]
            s2 = sheet2[item_id]["scores"][axis]
            batch = sheet1[item_id]["batch"]
            n1 = sheet1[item_id]["notes"].replace("|", "/").replace("\n", " ")
            n2 = sheet2[item_id]["notes"].replace("|", "/").replace("\n", " ")
            lines.append(f"| {item_id} | {batch} | {s1} | {s2} | {n1} | {n2} |")
        lines.append("")

    all_disagreements = sorted(set().union(*disagreements_by_axis.values())) if common_ids else []
    lines.append(f"## Items needing tie-break discussion: {len(all_disagreements)}\n")
    if all_disagreements:
        lines.append(", ".join(all_disagreements))
    else:
        lines.append("None -- full agreement on every axis for every item.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labeler1", required=True, type=Path)
    parser.add_argument("--labeler2", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    for p in (args.labeler1, args.labeler2):
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            sys.exit(1)

    sheet1 = load_sheet(args.labeler1)
    sheet2 = load_sheet(args.labeler2)
    report = build_report(sheet1, sheet2)

    print(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"\nWrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()