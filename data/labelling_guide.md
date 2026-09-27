# Labelling Guide — Customer Support Reply Grading (Pilot v0.1)

Team SupportScore, Project 1 (The Grader). This guide covers the **pilot
set** (`pilot_items.jsonl`, 20 items). It will be revised once we run the
full 150+ golden set, based on real disagreements between labellers.

## What you are grading

For each item you are given: a `customer_message`, the relevant
`policy_excerpt` from `policy_technest.md` (a fictional electronics
retailer's policy — this is the *only* source of truth for correctness),
and one `candidate_reply` to grade. Score the reply on three axes, each
0/1/2, **independently of each other**. A rude-but-correct reply should
still score 2 on correctness. A warm-but-wrong reply should still score 0
on correctness.

Do not read `author_note` or `challenge_type` in the pilot data before
labelling — those are our own design notes describing what we intended to
test, not a human label, and reading them first will bias you.

## Correctness (0 / 1 / 2)

- **2 — Fully consistent.** Everything the reply asserts about policy,
  timeframes, cost, or process matches the supplied excerpt. No invented
  rules, order statuses, discounts, or promises the policy doesn't
  support. **If the true answer depends on information the policy alone
  can't supply (e.g., "has the order shipped yet?"), a reply that asks
  for that information — instead of guessing — scores 2.** Likewise, if
  the policy has a genuine gap for this situation, a reply that says so
  and offers to escalate scores 2.
- **1 — Partially consistent.** Gets the core outcome right but adds a
  minor inaccuracy (e.g., timeframe off by a little), an unsupported soft
  promise ("we'll try to expedite it"), or hedges/escalates in a way
  that's reasonable but not clearly tied to a specific rule.
- **0 — Contradicts policy.** States something the policy rules out
  (e.g., offers a free replacement for customer-caused damage, offers to
  reset a password directly, promises shipping to an unsupported
  country), invents a rule/order status/discount that isn't in the
  excerpt, or asserts a definite answer where the policy has a gap.

## Politeness (0 / 1 / 2)

- **2 — Respectful and empathetic.** Acknowledges the customer's
  situation where relevant (an apology for damage, empathy for an
  inconvenience). No sarcasm, blame, or condescension — including when
  declining the request.
- **1 — Neutral/curt but not rude.** Reads like a terse internal note
  rather than a message to a customer, or skips an apology/acknowledgment
  most customers would expect, but contains nothing disrespectful.
- **0 — Disrespectful.** Contains blame ("you probably did this
  yourself"), sarcasm, dismissiveness, or language a customer would
  reasonably find rude — regardless of whether the content is otherwise
  correct.

## Completeness (0 / 1 / 2)

- **2 — Covers what's needed to act.** Includes every policy condition
  relevant to this request (timeframe, required evidence/steps, who pays,
  what happens next). **When the honest answer requires more information
  from the customer, "covers what's needed" means clearly stating what
  information is needed and why** — do not require it to also guess the
  rest.
- **1 — Covers the main point, misses a detail.** E.g., confirms a refund
  will happen but not the timeframe, or forgets to mention a required
  photo/step.
- **0 — Doesn't address the actual question**, or is so short/generic
  that the customer has no actionable next step.

## Borderline cases

- **Correct question, wrong reasoning.** If the reply reaches the right
  outcome but for a reason not supported by the policy (e.g., right
  refund amount but wrong justification), score correctness 1, not 2.
- **Clarifying questions.** Don't penalize completeness for omitting
  details that depend on information the reply correctly asked for and
  didn't yet have.
- **Policy gaps.** If the policy doesn't specify an outcome, a reply that
  says so and offers to check/escalate beats a reply that confidently
  invents an answer, even if the invented answer sounds plausible.
- **Multiple issues at once.** Score each axis on its single worst
  disqualifying issue if there are several; add a one-line note
  explaining which issue drove the score, so we can trace disagreements
  later.
- **Off-topic or unanswerable requests.** None of the pilot items are
  designed to be unanswerable from the policy; if you hit one that
  genuinely can't be judged, mark all three scores `NA` and say why in
  the notes column rather than forcing a number.

## Process for this pilot

1. Two teammates each take a **blank, independent** copy of the sheet
   (`labelling_sheet_labeler1.csv`, `labelling_sheet_labeler2.csv`).
   Do not look at each other's sheet while labelling.
2. Score every item's three axes plus a short note.
3. Compare the two completed sheets. For every item where scores differ,
   discuss and note *why* (guide was unclear vs. simple mistake vs.
   genuine judgment call).
4. Revise this guide to close any real ambiguity found.
5. Only after that discussion do you write down agreed-upon final labels.
   Keep both original independent labels — do not overwrite them — since
   the disagreement rate itself is something we report (this pilot is too
   small to compute a meaningful Cohen's kappa; that's done on the full
   150+ set).
