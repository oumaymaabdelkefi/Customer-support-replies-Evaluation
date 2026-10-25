# Golden Set Scaling — Evidence Review and Validation Batch (Stage 1)

Team SupportScore, Role A. This document covers the step **before** scaling
to 150+ items: sampling 20-30 real Bitext instruction/response pairs,
checking whether they actually support our fictional TechNest policy (or
should revise it), and building a small validation batch to be human-labelled
before committing to the full 150+. **Nothing here is the 150+ golden set.**
That comes after this batch is labelled and its score distribution checked.

## Method

Sampled 2 rows each (1 for smaller/account-only intents) from 16 Bitext
intents mapped to our 4 policy themes, from the same `train` split as the
pilot (`bitext/Bitext-customer-support-llm-chatbot-training-dataset`,
26,872 rows, `datasets-server.huggingface.co` API). For each intent, read
the full `response` text across ~15-25 rows, not just the 1-2 selected for
the batch, looking specifically for **claims that recur consistently
across independently-generated rows** (real signal) versus claims that
appear once or vary row-to-row (not evidence of anything, per the
instruction not to invent policy from a single vague answer).

## What converged (supports existing policy — no change made)

- **Refund eligibility grounds** (`check_refund_policy`, ~20 rows read):
  nearly every row independently lists "product/service defect" and
  "change of mind within a grace period" as the two core grounds for a
  refund. This corroborates our existing RET-1 (unconditional 30-day
  return) / DMG-\* (defect path) split — we kept it as-is.
- **Password reset flow** (`recover_password`, ~15 rows read): every row
  describes the same self-service pattern (visit login page → "Forgot
  password" → email link → set new password), never a support-side reset.
  Corroborates SEC-1 as written.

## What did NOT converge (no policy number changed on this basis)

- **Refund processing time** (`check_refund_policy`, "how long" framings):
  varies row to row — "a few business days," "a few days to a couple of
  weeks," "a few days to a few weeks," and one row (6021) gives a specific
  per-payment-method breakdown (credit card 5-7 days, bank/PayPal 3-5 days,
  check up to 10 days, store credit instant). Row 6021's credit-card figure
  happens to match our existing RET-4 (5-7 business days), but since the
  other ~10 rows on the same question give vaguer, non-matching answers,
  this is **one data point, not a convergent pattern** — per your
  instruction, we did not rewrite RET-4 off it. RET-4 remains a
  TechNest-authored (fictional) number, disclosed as such.
- **Shipping timeframes / costs** (`delivery_options`, `delivery_period`):
  unresolved `{{Date Range}}` template placeholders mean no concrete
  numbers are recoverable from this data extract at all — inconclusive,
  not contradictory. SHIP-1's numbers remain TechNest-authored.
- **Account deletion grace period** (`delete_account`): no row states a
  specific number of days. SEC-4's 14-day figure remains TechNest-authored.

## Real behavior we chose to preserve as-is (not "fixed")

- **`track_refund` / `delivery_period` replies routinely ask for an order
  or tracking number and imply they'll check and report back** — a
  reasonable real-world behavior, but it conflicts with our own GEN-1
  constraint (support has no live order lookup in this project). We did
  **not** edit these replies to remove the promise; they're kept
  unchanged as a genuine test of whether a labeller/judge catches an
  over-promise that's realistic but not actually deliverable here. Added
  explicit scoring guidance for this to `labelling_guide.md`.
- **One `check_refund_policy` response (6001) lists "event cancellation"**
  as a refund ground — irrelevant to an electronics retailer, a
  leftover from the generic multi-vertical template. Left unchanged as a
  naturally-occurring minor irrelevance, not corrected.
- **`edit_account` / `switch_account` responses have an oddly effusive,
  over-the-top tone** ("How remarkable it is to witness your
  determination...", "the thrill of embarking on this extraordinary
  journey...") for routine account changes. Left unchanged — it's a real
  and slightly unnatural artifact of the source data worth the team
  discussing: is gushing-but-not-rude "polite" under our rubric, or does
  it read as insincere? Flagged for discussion, not resolved here.

## Gaps found (no rule invented to cover them)

Real customer questions exist for five things this policy doesn't
address at all: modifying an order's contents (`change_order`),
sign-up/registration problems, generic (non-email) profile edits,
account tier switching, and account creation. Per your instruction, no
rule was invented to cover these from the sample. They're now listed in
`policy_technest.md` under "Known gaps," and the corresponding items in
this batch carry `policy_rule_ids: []` with a note — the *correct* reply
to these is to say the policy doesn't cover it and escalate, which is
already how `labelling_guide.md`'s "Policy gaps" rule handles this.
**Team decision needed**: leave these as permanent out-of-scope test
cases, or write new rules for one or more of them before scaling to 150.

## Edits made, and how many

Every item's `candidate_reply` is the real Bitext `response`, subject
only to two documented edit types — no rewriting for quality, no
correcting wrong/vague content:

1. `placeholder_resolved` — an unresolved `{{token}}` (e.g.
   `{{Company Name}}`, `{{Order Number}}`, `{{Login Page URL}}`) replaced
   with a concrete, consistent value so the text reads naturally.
2. `message_augmented_with_damage_detail` — used only for the 4
   `complaint`-intent items, since Bitext has no native damaged-product
   intent (see `SOURCE_AND_LICENSE.md`); a concrete damage detail was
   added to the customer message so the item is gradable against DMG-\*.
   The reply text itself was **not** touched in any of these 4 cases.

No "align explicit facts with policy" edits were made in this batch —
the evidence review above found nothing that needed correcting rather
than left as a natural weak/vague signal; see `pilot_items.jsonl`'s
sibling file `golden_sample_stage1.jsonl` for the per-item `edits` list.

**Counts** (of 28 items): **15 replies fully unchanged** (verbatim
Bitext `response`, zero edits, including several weak/vague or
tonally-odd ones on purpose), **13 replies with placeholder resolution
only**, **0 replies with a fact alignment edit**. 4 of the 15 unchanged
replies pair with an adapted (damage-augmented) message.

## What's next (do not skip)

**Update**: since neither this batch nor the pilot had been labelled yet,
they were merged into one combined file, `data/golden_set.jsonl` (48
items = 20 pilot + 28 from this batch; see `scripts/merge_golden_set.py`).
Label the combined file, not this one in isolation — a `batch` field on
each row still tells you which batch an item came from, so results can
be split back apart for the comparison in step 2 below.

1. Two teammates independently label `data/golden_set.jsonl` using
   `data/labelling_sheet_labeler1_completed.csv` / `..._labeler2_completed.csv`
   (48 rows; same blind, independent process as before).
2. Check the resulting score distribution **specifically for the
   `golden_sample_stage1` rows** (filter on `batch`): if
   correctness/completeness are overwhelmingly stuck at one value (e.g.,
   everything scores 1), that's a signal this real-data sourcing method
   isn't producing enough gradable variance and needs rethinking before
   scaling to 150 — not just more of the same rows. Worth comparing
   against the pilot rows' distribution too, since those were
   deliberately engineered for variance and make a useful contrast.
3. Resolve the "known gaps" team decision above.
4. Only then, scale the same reviewed method to 150+.
