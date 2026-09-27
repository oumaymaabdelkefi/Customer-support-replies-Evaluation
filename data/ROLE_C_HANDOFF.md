# Handoff to Role C (Judge & Prompts Lead)

From Role A (Golden Set & Labelling Lead), 2026-09-27. This is a **pilot**
for you to start building and smoke-testing the judge prompt against — it
is not the 150+ item golden set. Please read the caveats at the bottom
before you treat any of this as ground truth.

## Files to use

| File | What it's for |
|---|---|
| `data/policy_technest.md` | The fictional TechNest Gadgets policy. This is the only source of truth for correctness — your judge prompt should either be given the relevant `policy_excerpt` per item (recommended for the pilot) or the whole file if you want to test the judge doing its own rule lookup. |
| `data/pilot_items.jsonl` | 20 items, machine-readable, one JSON object per line. Use this as your judge's input feed. |
| `data/pilot_items.csv` | Same content, flattened for eyeballing in a spreadsheet. Not for programmatic use (rule IDs are joined with `;`). |
| `data/labelling_guide.md` | The rubric (0/1/2 × correctness/politeness/completeness) your judge prompt should mirror. Your judge's scoring instructions should be a direct, faithful translation of this guide, not a reinvention of it. |
| `data/labelling_sheet_labeler1.csv`, `labelling_sheet_labeler2.csv` | Currently **blank**. Human labels don't exist yet — see "What's still pending" below. |
| `data/SOURCE_AND_LICENSE.md` | Where each item's `customer_message` came from (Bitext dataset vs. team-written) and the CDLA-Sharing-1.0 license terms that apply to the Bitext-derived ones. |

## `pilot_items.jsonl` field reference

```json
{
  "item_id": "P07",
  "scenario_id": "SC06",
  "theme": "damaged_products",
  "customer_message": "My new laptop's screen arrived with a big scratch across it...",
  "policy_rule_ids": ["DMG-1", "DMG-2", "DMG-3"],
  "policy_excerpt": "[DMG-1] Damage or defects present on arrival must be reported within 7 calendar days... [DMG-2] ... [DMG-3] ...",
  "candidate_reply": "Sorry about that! Since you noticed it right at unboxing...",
  "source": "bitext | team_written",
  "source_id": 12001,
  "adapted": false,
  "original_instruction": null,
  "challenge_type": "correct | incorrect | incomplete | impolite | asks_for_missing_info",
  "author_note": "free text — see caveat below",
  "policy_source_dataset": "bitext/Bitext-customer-support-llm-chatbot-training-dataset | null"
}
```

`scenario_id` groups items that share the same `customer_message`
(5 scenarios have 2 candidate replies each, e.g. SC01/SC06/SC07/SC08/SC13)
— useful if you want paired good/bad comparisons while iterating on the
prompt.

## Proposed judge I/O shape (please confirm against Role B's actual harness schema before hard-coding)

No harness schema exists in the repo yet — I checked before writing this and
`harness/` doesn't exist. Please sync with Role B directly; the shape below
is only my proposal so you're not blocked:

**Input to judge**: `customer_message`, `policy_excerpt`, `candidate_reply`
(exactly the three fields a human labeller sees — the judge should not get
`challenge_type` or `author_note`, since those don't exist for real items).

**Proposed output** (structured, one object per item):

```json
{
  "item_id": "P07",
  "correctness": 0,
  "correctness_reason": "short justification citing a rule id",
  "politeness": 0,
  "politeness_reason": "short justification",
  "completeness": 0,
  "completeness_reason": "short justification"
}
```

Scores are integers 0/1/2 per the guide; each needs its own reason string
so a human can audit a disagreement without re-reading the whole reply.
If Role B's schema differs (e.g., a single combined `reason` field, or an
overall score), please reconcile with them rather than shipping two
incompatible schemas — that will break the harness's scorer.

## What's still pending before this is "golden" in any sense

1. **No human labels exist yet.** The two labelling sheets are blank on
   purpose. You can use the pilot to smoke-test that your judge *runs* and
   produces structured output, but **you cannot yet compute judge-vs-human
   agreement** — that requires two teammates to independently label the 20
   items first (see `labelling_guide.md`, "Process for this pilot").
2. **`challenge_type` and `author_note` are not labels.** They're my design
   intent for each item (what I was trying to test), written before any
   human scored anything. Do not use them as ground truth for accuracy
   metrics — use them at most to sanity-check that your judge's own
   reasoning roughly lines up with the intended failure mode, and only
   *after* real human labels exist should agreement be measured against
   those, not against `challenge_type`.
3. **This is 20 items, not 150+.** It's sized for judge development and
   your position-bias / verbosity-bias probes (P07/P08 and P01/P02 are a
   ready-made pair for a verbosity-style A/B test if you pad one of them;
   P17/P18 and P09/P10 are ready-made stress tests for the judge
   confidently rejecting a policy-violating "correct-sounding" reply).
   The real 150+ golden set, with double-labelling and Cohen's kappa,
   comes next and will likely change the exact item mix.
4. **Bitext-derived items carry a share-alike license (CDLA-Sharing-1.0).**
   See `SOURCE_AND_LICENSE.md`. Not a blocker for pilot judge development,
   but flag it to Role D before the final data package is described in
   the README/report.
5. **Independent review of `adapted` items is still open** — someone other
   than me should check the 7 `adapted: true` rows against their
   `original_instruction` to confirm the placeholder fills/added detail
   didn't lead the scenario in an unfair direction.
