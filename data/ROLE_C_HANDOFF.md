# Handoff to Role C (Judge & Prompts Lead)

From Role A (Golden Set & Labelling Lead). Originally written 2026-09-27
for the 20-item pilot; updated after adding a second batch and merging
both into one combined set. **Neither batch is human-labelled yet** —
please read "What's still pending" before treating any of this as ground
truth.

## Files to use

| File | What it's for |
|---|---|
| `data/policy_technest.md` | The fictional TechNest Gadgets policy, including a "Known gaps" section for requests it doesn't cover at all. This is the only source of truth for correctness — your judge prompt should be given the relevant `policy_excerpt` per item, not the whole file. |
| `data/golden_set.jsonl` | **Use this one.** All 48 items combined (20 pilot + 28 real-data batch), one JSON object per line, unified schema. `golden_set.csv` is the same, flattened for eyeballing. |
| `data/pilot_items.jsonl`, `data/golden_sample_stage1.jsonl` | The two batches individually, kept for provenance (see `SOURCE_AND_LICENSE.md` / `GOLDEN_SAMPLE_REVIEW.md`). You don't need these separately if you're using `golden_set.jsonl`. |
| `data/labelling_guide.md` | The rubric (0/1/2 × correctness/politeness/completeness) your judge prompt should mirror, plus a v0.2 addendum with two rules learned from real data (see below). Your judge's scoring instructions should be a direct, faithful translation of this guide, not a reinvention of it. |
| `data/labelling_sheet_labeler1.csv`, `labelling_sheet_labeler2.csv` | Currently **blank**, sized to all 48 items. Human labels don't exist yet for either batch — see "What's still pending" below. |
| `data/SOURCE_AND_LICENSE.md`, `data/GOLDEN_SAMPLE_REVIEW.md` | Where each item's `customer_message`/`candidate_reply` came from, what was and wasn't edited, and the evidence review behind the second batch. |
| `harness/` | **Already built by Role B** — see below, this supersedes the "proposed schema" I originally wrote here. |

## `golden_set.jsonl` field reference

Unified schema across both batches — fields that only apply to one batch
are `null` on the other's rows. `batch` tells you which.

```json
{
  "item_id": "G21",
  "batch": "pilot | golden_sample_stage1",
  "scenario_id": "G21",
  "theme": "damaged_products",
  "customer_message": "where to lodge a customer complaint - my new tablet arrived with a shattered screen inside a dented box.",
  "policy_rule_ids": ["DMG-1", "DMG-2", "DMG-3"],
  "policy_excerpt": "[DMG-1] Damage or defects present on arrival must be reported within 7 calendar days... [DMG-2] ... [DMG-3] ...  -- or, for the 5 'known gap' items, an explicit '(No rule covers this...)' string, never empty",
  "candidate_reply": "I'm sorry to hear that you're looking to lodge a customer complaint. ...",
  "source": "bitext | team_written",
  "source_id": 7003,
  "adapted": true,
  "original_instruction": "where to lodge a customer complaint",
  "original_response": "...raw Bitext response, null for pilot items...",
  "edits": [{"type": "message_augmented_with_damage_detail", "detail": "..."}],
  "challenge_type": "correct | incorrect | incomplete | impolite | asks_for_missing_info -- null for golden_sample_stage1 items",
  "author_note": "pilot-only design intent, null for golden_sample_stage1 items",
  "review_note": "golden_sample_stage1-only evidence-review note, null for pilot items",
  "policy_source_dataset": "bitext/Bitext-customer-support-llm-chatbot-training-dataset | null"
}
```

**Only 4 fields matter to the harness**: `item_id`, `customer_message`,
`policy_excerpt`, `candidate_reply` — everything else is internal-only
and gets stripped by `harness/run.py::load_items` (`INPUT_FIELDS`).
`challenge_type`/`author_note`/`review_note` are never ground truth (see
caveat below) — they're design/evidence notes written before any human
scored anything.

## Judge I/O shape (confirmed, matches `harness/schema.py`)

Role B has already built the harness with a schema that matches what I
proposed here originally — this is now the actual contract, not a
proposal. See `harness/schema.py` (`ItemInput`, `JudgeOutput`) and
`harness/README.md` for how to wire in `harness/systems/judge_stub.py`.

**Input to judge** (`ItemInput`): `item_id`, `customer_message`,
`policy_excerpt`, `candidate_reply`.

**Output your judge must return** (`JudgeOutput`, validated with
`extra="forbid"` — no extra or missing fields):

```json
{
  "item_id": "G21",
  "correctness": 0,
  "correctness_reason": "short justification citing a rule id",
  "politeness": 0,
  "politeness_reason": "short justification",
  "completeness": 0,
  "completeness_reason": "short justification"
}
```

Scores are integers 0/1/2 per the guide; each needs its own non-empty
reason string. `harness/schema.py::validate_system_output` will reject
anything that doesn't match this exactly — confirmed by running
`golden_set.jsonl` through `harness/run.py --system always_perfect`,
which parses all 48 items cleanly.

## What's still pending before this is "golden" in any sense

1. **No human labels exist for either batch yet.** Both `labelling_sheet_labeler1.csv`
   and `..._labeler2.csv` are blank on purpose, sized to all 48 items. You
   can use `golden_set.jsonl` to smoke-test that your judge *runs* and
   produces valid structured output, but **you cannot yet compute
   judge-vs-human agreement** — that requires two teammates to
   independently label all 48 items first (see `labelling_guide.md`,
   "Process for this pilot").
2. **`challenge_type`, `author_note`, and `review_note` are not labels.**
   They're design/evidence notes written before any human scored
   anything — the first two for the pilot's deliberately-engineered items,
   the third for the real-data batch's findings. Do not use them as ground
   truth for accuracy metrics; only *after* real human labels exist should
   agreement be measured against those.
3. **This is 48 items, not 150+.** Per an explicit team decision, the
   second batch (28 items) intentionally uses **real** Bitext
   instruction/response pairs instead of team-written replies, to test
   whether that sourcing method produces enough gradable variance —
   see `GOLDEN_SAMPLE_REVIEW.md`. Whether to scale *this* method to 150+
   depends on what the human labelling in point 1 finds (are scores
   varied, or degenerate/stuck on one value?). Don't assume the mix or
   sourcing method is final.
4. **5 items have no matching policy rule at all** (`policy_rule_ids: []`,
   `policy_excerpt` reads "No rule ... covers this request"): G03, G04,
   G24, G27, G28 — real requests (order-content changes, sign-up
   problems, tier upgrades, account creation) the policy doesn't address.
   See `policy_technest.md`, "Known gaps." Your judge should be tested on
   whether it correctly declines to invent an answer for these, per the
   labelling guide's "Policy gaps" rule — this is a good adversarial set.
5. **Bitext-derived items carry a share-alike license (CDLA-Sharing-1.0).**
   See `SOURCE_AND_LICENSE.md`. Not a blocker for judge development, but
   flag it to Role D before the final data package is described in the
   README/report.
6. **Independent review of `adapted` items is still open** — someone other
   than me should check the `adapted: true` rows against their
   `original_instruction`/`original_response` to confirm the edits
   (placeholder fills, or the damaged-product detail added to `complaint`
   messages) didn't lead the scenario in an unfair direction.
