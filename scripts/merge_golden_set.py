#!/usr/bin/env python3
"""Merge the pilot batch (data/pilot_items.jsonl, 20 items) and the
golden-set stage-1 batch (data/golden_sample_stage1.jsonl, 28 items) into
one combined file for a single round of double-labelling, since neither
batch has been labelled yet.

Writes into <repo>/data/:
  - golden_set.jsonl               (48 items, unified schema, superset of
                                     both batches' fields with nulls where
                                     a field doesn't apply)
  - golden_set.csv                 (flattened, for eyeballing)
  - labelling_sheet_labeler1.csv    (blank, 48 rows -- replaces the old
  - labelling_sheet_labeler2.csv     20-item and 28-item sheets)

Does NOT modify or delete pilot_items.jsonl / golden_sample_stage1.jsonl --
those remain the per-batch provenance record referenced by
SOURCE_AND_LICENSE.md and GOLDEN_SAMPLE_REVIEW.md.
"""
import csv
import json
import os
from collections import Counter

REPO_DATA = "/home/azizbzt/Desktop/ai-projects/grader/data"

# Union of every field either batch uses, in a sensible display order.
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

def main():
    pilot = [normalize(r, "pilot") for r in load_jsonl(os.path.join(REPO_DATA, "pilot_items.jsonl"))]
    stage1 = [normalize(r, "golden_sample_stage1") for r in load_jsonl(os.path.join(REPO_DATA, "golden_sample_stage1.jsonl"))]
    combined = pilot + stage1

    ids = [r["item_id"] for r in combined]
    assert len(ids) == len(set(ids)), f"duplicate item_id across batches: {[i for i in ids if ids.count(i) > 1]}"
    for r in combined:
        for f in ("item_id", "customer_message", "policy_excerpt", "candidate_reply"):
            assert r.get(f), f"{r['item_id']}: missing/empty required field {f}"

    jsonl_path = os.path.join(REPO_DATA, "golden_set.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = os.path.join(REPO_DATA, "golden_set.csv")
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

    # Replace the old per-batch sheets with 2 combined ones, same canonical
    # filenames as the (still-blank, never-filled-in) pilot sheets.
    for labeller in ("labeler1", "labeler2"):
        path = os.path.join(REPO_DATA, f"labelling_sheet_{labeller}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "item_id", "batch", "theme", "customer_message", "policy_excerpt",
                "candidate_reply", "correctness_score_0_1_2", "politeness_score_0_1_2",
                "completeness_score_0_1_2", "labeller_notes",
            ])
            for r in combined:
                w.writerow([
                    r["item_id"], r["batch"], r["theme"], r["customer_message"],
                    r["policy_excerpt"], r["candidate_reply"], "", "", "", "",
                ])

    # Superseded per-batch sheets -- safe to remove, nothing was ever filled in.
    removed = []
    for stale in ("labelling_sheet_golden_sample_labeler1.csv", "labelling_sheet_golden_sample_labeler2.csv"):
        p = os.path.join(REPO_DATA, stale)
        if os.path.exists(p):
            os.remove(p)
            removed.append(stale)

    batch_counts = Counter(r["batch"] for r in combined)
    theme_counts = Counter(r["theme"] for r in combined)
    print(f"Wrote {len(combined)} items to {jsonl_path}")
    print("By batch:", dict(batch_counts))
    print("By theme:", dict(theme_counts))
    print("Removed superseded sheets:", removed)
    print("Validation: OK (unique item_ids, all 4 harness-required fields non-empty)")

if __name__ == "__main__":
    main()
