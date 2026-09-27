#!/usr/bin/env python3
"""Merge the pilot batch (data/pilot_items.jsonl, 20 items), the golden-set
stage-1 batch (data/golden_sample_stage1.jsonl, 28 items), and the golden-set
stage-2 batch (data/golden_sample_stage2.jsonl, 30 items) into one combined
file.

Writes into <repo>/data/:
  - golden_set.jsonl                       (78 items, unified schema, superset
                                             of every batch's fields with
                                             nulls where a field doesn't apply)
  - golden_set.csv                         (flattened, for eyeballing)
  - labelling_sheet_labeler1_stage2.csv     (BLANK, 30 rows -- stage-2 items
  - labelling_sheet_labeler2_stage2.csv      only, so the two of you label
                                             just the new items instead of
                                             re-doing the 48 you've already
                                             completed)

Does NOT modify or delete pilot_items.jsonl / golden_sample_stage1.jsonl /
golden_sample_stage2.jsonl -- those remain the per-batch provenance record.

Does NOT touch labelling_sheet_labeler1.csv / labelling_sheet_labeler2.csv
or their *_completed.csv versions -- your real, already-filled-in labels for
the first 48 items are never overwritten by this script.
"""
import csv
import json
import os
from collections import Counter
from pathlib import Path

# Resolves relative to this script's own location, so it works on any
# machine/repo checkout -- no more hardcoded absolute paths.
REPO_DATA = Path(__file__).resolve().parent.parent / "data"

# Union of every field any batch uses, in a sensible display order.
# item_id/customer_message/policy_excerpt/candidate_reply are the 4 the
# harness (harness/schema.py::ItemInput) actually reads -- everything
# else is internal-only and gets stripped by harness/run.py::load_items.
FIELD_ORDER = [
    "item_id", "batch", "scenario_id", "theme",
    "customer_message", "policy_rule_ids", "policy_excerpt", "candidate_reply",
    "source", "source_id", "adapted",
    "original_instruction", "original_response",
    "edits", "challenge_type", "author_note", "review_note",
    "policy_source_dataset",
]


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize(row, batch_name):
    out = {k: row.get(k, None) for k in FIELD_ORDER}
    out["batch"] = batch_name
    return out


def write_blank_sheet(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "batch", "theme", "customer_message", "policy_excerpt",
            "candidate_reply", "correctness_score_0_1_2", "politeness_score_0_1_2",
            "completeness_score_0_1_2", "labeller_notes",
        ])
        for r in rows:
            w.writerow([
                r["item_id"], r["batch"], r["theme"], r["customer_message"],
                r["policy_excerpt"], r["candidate_reply"], "", "", "", "",
            ])


def main():
    pilot = [normalize(r, "pilot") for r in load_jsonl(REPO_DATA / "pilot_items.jsonl")]
    stage1 = [normalize(r, "golden_sample_stage1") for r in load_jsonl(REPO_DATA / "golden_sample_stage1.jsonl")]

    stage2_path = REPO_DATA / "golden_sample_stage2.jsonl"
    stage2 = [normalize(r, "golden_sample_stage2") for r in load_jsonl(stage2_path)] if stage2_path.exists() else []

    combined = pilot + stage1 + stage2

    ids = [r["item_id"] for r in combined]
    assert len(ids) == len(set(ids)), f"duplicate item_id across batches: {[i for i in ids if ids.count(i) > 1]}"
    for r in combined:
        for f in ("item_id", "customer_message", "policy_excerpt", "candidate_reply"):
            assert r.get(f), f"{r['item_id']}: missing/empty required field {f}"

    jsonl_path = REPO_DATA / "golden_set.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = REPO_DATA / "golden_set.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELD_ORDER)
        w.writeheader()
        for r in combined:
            row = dict(r)
            if isinstance(row.get("policy_rule_ids"), list):
                row["policy_rule_ids"] = ";".join(row["policy_rule_ids"])
            if isinstance(row.get("edits"), list):
                row["edits"] = json.dumps(row["edits"], ensure_ascii=False)
            w.writerow(row)

    # Only write blank sheets for stage-2 items -- pilot + stage1 already
    # have real, completed labels sitting in labelling_sheet_*_completed.csv
    # and must never be touched by this script.
    if stage2:
        for labeller in ("labeler1", "labeler2"):
            path = REPO_DATA / f"labelling_sheet_{labeller}_stage2.csv"
            write_blank_sheet(path, stage2)

    batch_counts = Counter(r["batch"] for r in combined)
    theme_counts = Counter(r["theme"] for r in combined)
    print(f"Wrote {len(combined)} items to {jsonl_path}")
    print("By batch:", dict(batch_counts))
    print("By theme:", dict(theme_counts))
    if stage2:
        print(f"Wrote {len(stage2)}-row blank sheets: labelling_sheet_labeler1_stage2.csv, labelling_sheet_labeler2_stage2.csv")
    else:
        print("No golden_sample_stage2.jsonl found -- merged pilot + stage1 only.")
    print("Validation: OK (unique item_ids, all 4 harness-required fields non-empty)")
    print("NOTE: labelling_sheet_labeler1.csv / labeler2.csv and their")
    print("      *_completed.csv versions were NOT touched by this run.")


if __name__ == "__main__":
    main()