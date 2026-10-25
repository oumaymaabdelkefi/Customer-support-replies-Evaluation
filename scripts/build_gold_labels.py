"""
Build data/gold_labels.csv: one row per golden-set item, where each axis's
gold score is the score both human labellers agreed on, or blank if they
disagreed ("disputed"). Disputed axes are skipped by
scripts/judge_reliability.py, so the judge is only measured where the
humans themselves agree.

We did not run an adjudication round for the stage-2 items; this "agreed
subset" is the gold standard instead. Items P01-P20 and G01-G28 use the
labels in *_completed.csv, which were revised after a discussion round.

Usage:
    python scripts/build_gold_labels.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
AXES = ["correctness", "politeness", "completeness"]
OUT = DATA / "gold_labels.csv"


def read_sheets(*names: str) -> dict[str, dict]:
    out = {}
    for name in names:
        with open(DATA / name, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                out[row["item_id"]] = row
    return out


def score(row: dict | None, axis: str) -> str:
    v = (row or {}).get(f"{axis}_score_0_1_2", "").strip()
    return v if v in ("0", "1", "2") else ""


def main():
    golden = [json.loads(l) for l in open(DATA / "golden_set.jsonl", encoding="utf-8") if l.strip()]
    splits = json.loads((DATA / "splits.json").read_text(encoding="utf-8"))["items"]
    l1 = read_sheets("labelling_sheet_labeler1_completed.csv", "labelling_sheet_labeler1_stage2.csv")
    l2 = read_sheets("labelling_sheet_labeler2_completed.csv", "labelling_sheet_labeler2_stage2.csv")

    stats = {a: Counter() for a in AXES}
    rows = []
    for item in golden:
        i = item["item_id"]
        row = {"item_id": i, "split": splits.get(i, ""), "batch": item["batch"], "theme": item["theme"]}
        for axis in AXES:
            a, b = score(l1.get(i), axis), score(l2.get(i), axis)
            if a and b and a == b:
                row[f"{axis}_score_0_1_2"] = a
                row[f"{axis}_status"] = "agreed"
            elif a and b:
                row[f"{axis}_score_0_1_2"] = ""
                row[f"{axis}_status"] = f"disputed ({a} vs {b})"
            else:
                row[f"{axis}_score_0_1_2"] = ""
                row[f"{axis}_status"] = "unlabelled"
            stats[axis][row[f"{axis}_status"].split(" ")[0]] += 1
        rows.append(row)

    fields = ["item_id", "split", "batch", "theme"]
    for axis in AXES:
        fields += [f"{axis}_score_0_1_2", f"{axis}_status"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({len(rows)} items)")
    for axis in AXES:
        s = stats[axis]
        print(f"  {axis:13} agreed {s['agreed']:3}  disputed {s['disputed']:3}  unlabelled {s['unlabelled']}")


if __name__ == "__main__":
    main()
