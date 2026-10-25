# Data Sources and Licensing — Pilot Set

## Bitext customer support dataset

- **Dataset**: `bitext/Bitext-customer-support-llm-chatbot-training-dataset`
  on Hugging Face.
- **License**: `cdla-sharing-1.0` (Community Data License Agreement —
  Sharing, Version 1.0), as declared in the dataset's own README front
  matter on Hugging Face (checked 2026-09-27). CDLA-Sharing is a
  share-alike license: modified/derived data we publish must remain
  available under the same license, and we must keep this provenance
  notice. **We are not claiming any other license for this data — do not
  relicense it in the final repo without re-checking this file.**
- **What we used**: only the `instruction` column (a synthetic customer
  message) from selected rows, identified by `row_idx` in the dataset's
  `train` split (26,872 rows total, accessed via the public
  `datasets-server.huggingface.co` API — no local download or HF account
  needed). We did **not** use the dataset's `response` column as a gold
  answer anywhere: those responses were written for a different, generic
  fictional company and are not verified correct under our TechNest
  policy.
- **How we picked rows**: the dataset is organized in contiguous blocks by
  `intent` (~1,000 rows each). We sampled rows from the blocks whose
  intent matched our four policy areas: `check_refund_policy`,
  `get_refund`, `cancel_order` (returns); `complaint` (damaged products,
  see caveat below); `delivery_options`, `change_shipping_address`
  (shipping); `recover_password`, `delete_account` (account security).
- **Known limitation**: this dataset is a generic intent-detection corpus
  with templated instructions (e.g., `"cancel order {{Order Number}}"`)
  and no product-specific detail. It has **no built-in "damaged/defective
  product" intent** with concrete detail — its `complaint` intent is a
  generic "I want to file a complaint against your company," with no
  mention of what's wrong. Every damaged-product item in this pilot is
  therefore either team-written from scratch or a Bitext `complaint` row
  with team-added product/damage detail (marked `adapted: true` with the
  original instruction preserved in `original_instruction`).

## Per-item provenance

Every row in `pilot_items.jsonl` carries:

- `source`: `"bitext"` or `"team_written"`.
- `source_id`: the Bitext `row_idx` (an integer, stable for this dataset
  revision) when `source` is `"bitext"`; `null` for team-written items.
- `adapted`: `true` if we changed the Bitext instruction (filled a
  `{{placeholder}}` with a concrete value, or added detail beyond the
  original), `false` if used verbatim.
- `original_instruction`: the exact original Bitext `instruction` string,
  kept whenever `adapted` is `true`, so the edit is auditable.

13 of the 20 pilot items are Bitext-sourced (6 used verbatim, 7 adapted);
7 are team-written. See `pilot_items.jsonl` for the
full per-item breakdown.

## Golden set, stage 1 (`golden_sample_stage1.jsonl`, 28 items)

A second, separate batch, built after the pilot for a different purpose:
testing whether **real** Bitext `instruction` + `response` pairs (not
team-written replies) can serve as the source for scaling to 150+. All 28
items are Bitext-sourced; none are team-written. Every item carries
`original_instruction` and `original_response` (the raw Bitext text) plus
an `edits` list documenting exactly what, if anything, changed, and why —
see `GOLDEN_SAMPLE_REVIEW.md` for the full method and evidence review.

**We did not use the Twitter Customer Support dataset for either batch.**
Two Hugging Face mirrors were checked; the one with real message/reply
structure (`TNE-AI/customer-support-on-twitter-conversation`) contains
real tweets from real people directed at real companies (Amazon, Apple,
Uber support handles, etc.) — personal data from real users, and replies
written under a real company's real policy, not gradable against our
fictional TechNest rules. Skipped for both reasons; flagged here in case
the team wants to revisit this decision with the instructor.

## What still needs review

- A teammate other than the author should spot-check the `adapted` items
  against `original_instruction` to confirm the edits are fair
  (placeholder fill-ins that don't change the intent) rather than
  leading.
- Before scaling to 150+ items, decide whether to keep sourcing
  customer messages from Bitext at all, given how few of its intents map
  cleanly onto "damaged product" — we may end up writing most of that
  theme ourselves regardless of source dataset, and Bitext's share-alike
  license needs to be reflected wherever the final data package is
  described (README, report) if any Bitext-derived text remains in the
  150+ set.
- Confirm with the instructor/TA that mixing a licensed dataset's
  instructions with team-written material, as documented here, satisfies
  "collecting real examples" for the golden-set requirement — or whether
  the final 150+ set should lean more heavily on one or the other.

## Stage-2 items G69-G130 (AI-drafted)

The 62 items G69-G130 were drafted with an AI assistant (Claude) to bring
the golden set to 150 items, and are marked `"source": "llm_drafted"` in
`golden_sample_stage2.jsonl`. Customer messages and replies are invented;
every policy excerpt is copied word for word from `policy_technest.md`
(enforced by `scripts/merge_golden_set.py`). They are spread over all four
themes and cover correct replies, policy contradictions, missing details,
rude-but-correct replies, GEN-1 "check and get back to you" promises,
right-answer-wrong-reason, policy gaps (escalated vs. invented) and
effusive or padded replies. `challenge_type`/`author_note` record the
drafting intent only; the labels come from the two human labellers, who
label blind via `labelling_sheet_stage2.xlsx` (no intent fields shown).
The team should review these items before relying on them.
