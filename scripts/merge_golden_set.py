#!/usr/bin/env python3
"""Merge the pilot batch (data/pilot_items.jsonl, 20 items), the golden-set
stage-1 batch (data/golden_sample_stage1.jsonl, 28 items), and the golden-set
stage-2 batch (data/golden_sample_stage2.jsonl, 30 items) into one combined
file.

Writes into <repo>/data/:
  - golden_set.jsonl                       (unified schema, superset of every
                                             batch's fields with nulls where a
                                             field doesn't apply)
  - labelling_sheet_labeler1_stage2.csv     (one row per stage-2 item, so the
  - labelling_sheet_labeler2_stage2.csv      two of you label just the new
                                             items. Scores and notes already
                                             in these sheets are KEPT: re-run
                                             this safely after adding items.)

Validation: every "[RULE-ID] text" in a policy_excerpt must be copied word
for word from data/policy_technest.md (whitespace and dash style aside).
The excerpt is the only source of truth the judge and labellers see, so a
paraphrased rule silently changes what "correct" means.

Does NOT modify or delete pilot_items.jsonl / golden_sample_stage1.jsonl /
golden_sample_stage2.jsonl -- those remain the per-batch provenance record.

Does NOT touch labelling_sheet_labeler1_completed.csv /
labelling_sheet_labeler2_completed.csv -- your real labels for the first 48
items are never overwritten by this script.
"""
import csv
import json
import re
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


LABEL_COLUMNS = [
    "correctness_score_0_1_2", "politeness_score_0_1_2",
    "completeness_score_0_1_2", "labeller_notes",
]
SHEET_COLUMNS = [
    "item_id", "batch", "theme", "customer_message", "policy_excerpt",
    "candidate_reply", *LABEL_COLUMNS,
]


def _normalize_text(text):
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(text.split())


def check_excerpts_match_policy(rows):
    """Fail if any rule quoted in a policy_excerpt isn't verbatim policy text."""
    policy = _normalize_text((REPO_DATA / "policy_technest.md").read_text(encoding="utf-8"))
    problems = []
    for r in rows:
        for rule_id, text in re.findall(r"\[([A-Z]+-\d+)\]\s*([^\[]+)", r["policy_excerpt"]):
            if _normalize_text(text) not in policy:
                problems.append(f"  {r['item_id']} [{rule_id}] {text.strip()[:70]}...")
    assert not problems, (
        "These policy excerpts are not copied word for word from "
        "data/policy_technest.md -- paste the rule text exactly:\n" + "\n".join(problems)
    )


def write_sheet(path, rows):
    """Write one row per item, keeping any scores/notes already in the sheet."""
    existing = {}
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for old in csv.DictReader(f):
                existing[old["item_id"]] = old

    kept = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(SHEET_COLUMNS)
        for r in rows:
            old = existing.get(r["item_id"], {})
            labels = [(old.get(c) or "") for c in LABEL_COLUMNS]
            if any(labels):
                kept += 1
                if (old.get("candidate_reply") != r["candidate_reply"]
                        or old.get("policy_excerpt") != r["policy_excerpt"]):
                    print(f"WARNING: {path.name} {r['item_id']} was labelled, but its reply or "
                          "policy excerpt has changed since -- re-check that label.")
            w.writerow([
                r["item_id"], r["batch"], r["theme"], r["customer_message"],
                r["policy_excerpt"], r["candidate_reply"], *labels,
            ])
    return kept


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
    check_excerpts_match_policy(combined)

    jsonl_path = REPO_DATA / "golden_set.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Only write sheets for stage-2 items -- pilot + stage1 already have
    # real, completed labels sitting in labelling_sheet_*_completed.csv and
    # must never be touched by this script.
    kept = {}
    if stage2:
        for labeller in ("labeler1", "labeler2"):
            path = REPO_DATA / f"labelling_sheet_{labeller}_stage2.csv"
            kept[labeller] = write_sheet(path, stage2)

    batch_counts = Counter(r["batch"] for r in combined)
    theme_counts = Counter(r["theme"] for r in combined)
    print(f"Wrote {len(combined)} items to {jsonl_path}")
    print("By batch:", dict(batch_counts))
    print("By theme:", dict(theme_counts))
    if stage2:
        print(f"Wrote {len(stage2)}-row stage-2 sheets (labels kept: "
              f"labeler1 {kept['labeler1']}, labeler2 {kept['labeler2']})")
    else:
        print("No golden_sample_stage2.jsonl found -- merged pilot + stage1 only.")
    print("Validation: OK (unique item_ids, required fields non-empty, "
          "policy excerpts verbatim)")
    print("NOTE: labelling_sheet_*_completed.csv were NOT touched by this run.")


if __name__ == "__main__":
    main()