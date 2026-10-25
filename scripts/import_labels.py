"""
Copy scores from a filled Excel labelling sheet into the CSV labelling
sheet the agreement scripts read.

Usage:
    python scripts/import_labels.py --xlsx data/labels/<file>.xlsx --labeller 1
    python scripts/import_labels.py --xlsx "data/data 2 labeled by Youssef.xlsx" --labeller 2

Reads the "Labels" sheet (Item, ..., Correctness, Politeness, Completeness,
Notes) and writes the scores into
data/labelling_sheet_labeler<N>_stage2.csv, matching rows by item id.
Refuses to import if an item in the workbook isn't in the CSV, if a score
isn't 0/1/2/NA, or if the item's reply text differs from the CSV (i.e. the
sheet was made from an older version of the item).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from openpyxl import load_workbook

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
AXES = ["correctness", "politeness", "completeness"]
VALID = {"0", "1", "2", "NA"}


def read_workbook(path: Path) -> dict[str, dict]:
    ws = load_workbook(path, data_only=True)["Labels"]
    header = [str(c.value or "").strip().lower() for c in ws[1]]
    col = {name: header.index(name) for name in ["item", "reply to grade", *AXES, "notes"]}
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        item_id = row[col["item"]]
        if not item_id:
            continue
        scores = {}
        for axis in AXES:
            v = row[col[axis]]
            v = "" if v is None else str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
            if v not in VALID and v != "":
                raise ValueError(f"{path.name} {item_id}: {axis} = {v!r} is not 0/1/2/NA")
            scores[axis] = v
        out[str(item_id).strip()] = {
            **scores,
            "notes": str(row[col["notes"]] or "").strip(),
            "reply": str(row[col["reply to grade"]] or ""),
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--labeller", type=int, choices=[1, 2], required=True)
    args = parser.parse_args()

    labels = read_workbook(args.xlsx)
    csv_path = DATA / f"labelling_sheet_labeler{args.labeller}_stage2.csv"
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    by_id = {r["item_id"]: r for r in rows}
    unknown = sorted(set(labels) - set(by_id))
    if unknown:
        raise SystemExit(f"Items in the workbook but not in {csv_path.name}: {unknown}")
    changed = [i for i, l in labels.items() if l["reply"].strip() != by_id[i]["candidate_reply"].strip()]
    if changed:
        raise SystemExit(f"Reply text differs from the current golden set for {changed[:10]} -- "
                         "the sheet was built from an older version of these items.")

    filled = 0
    for item_id, l in labels.items():
        row = by_id[item_id]
        for axis in AXES:
            row[f"{axis}_score_0_1_2"] = l[axis]
        row["labeller_notes"] = l["notes"]
        filled += all(l[a] for a in AXES)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    missing = [r["item_id"] for r in rows if r["item_id"] not in labels]
    print(f"Imported {len(labels)} items from {args.xlsx.name} into {csv_path.name} "
          f"({filled} fully scored).")
    if missing:
        print(f"Not in the workbook (left unchanged): {missing}")


if __name__ == "__main__":
    main()
