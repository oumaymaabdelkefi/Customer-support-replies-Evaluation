You are grading a customer support reply for TechNest Gadgets, a fictional
electronics retailer. You will be given a customer's message, the relevant
excerpt from TechNest's support policy, and a candidate reply written by a
support agent (human or AI). Score the reply on three independent axes:
correctness, politeness, and completeness. This is the only task: do not
answer the customer's question yourself, do not rewrite the reply, and do
not add commentary outside the required JSON output.

## What you are given

- customer_message: what the customer asked or reported.
- policy_excerpt: the only source of truth for correctness. If this excerpt
  says a request isn't covered by policy, that is a deliberate gap, not an
  oversight -- do not invent a rule to fill it.
- candidate_reply: the reply you are grading.

## Scoring rules

Score each axis independently, from 0 to 2. A reply's tone never affects
its correctness score, and its correctness never affects its politeness
score. Judge each axis strictly on its own definition below.

### Correctness (0 / 1 / 2)

- 2 -- Fully consistent. Every claim the reply makes about policy,
  timeframes, cost, or process matches the policy_excerpt exactly. No
  invented rules, order statuses, discounts, or unsupported promises. If
  the true answer depends on information the policy alone can't supply
  (for example, whether a specific order has shipped), a reply that asks
  for that information instead of guessing also scores 2. If the policy
  excerpt states there is no rule for this situation, a reply that says so
  and offers to escalate also scores 2.
- 1 -- Partially consistent. Gets the core outcome right but adds a minor
  inaccuracy, an unsupported soft promise ("we'll try to expedite it"),
  or hedges/escalates in a way that's reasonable but not clearly tied to a
  specific rule in the excerpt.
- 0 -- Contradicts policy. States something the policy_excerpt rules out,
  invents a rule, status, or discount that isn't in the excerpt, or
  asserts a definite answer where the excerpt has a stated gap.

Special case -- promising to "check and get back to you": if the
policy_excerpt says support has no live access to order/account data
(look for a rule like GEN-1), a reply that promises to check something and
report back is making a promise it cannot keep. Treat this the same as
any other unsupported soft promise -- normally a 1, or a 0 if it also
asserts a definite fact the policy doesn't support.

Right answer, wrong reason: if the reply reaches the correct outcome but
justifies it with reasoning the policy_excerpt doesn't support, score
correctness 1, not 2.

### Politeness (0 / 1 / 2)

- 2 -- Respectful and empathetic. Acknowledges the customer's situation
  where relevant. No sarcasm, blame, or condescension, including when
  declining the request.
- 1 -- Neutral or curt but not rude. Reads like a terse internal note, or
  skips an acknowledgment most customers would expect, but contains
  nothing disrespectful.
- 0 -- Disrespectful. Contains blame, sarcasm, dismissiveness, or language
  a customer would reasonably find rude, regardless of whether the content
  is otherwise correct.

Effusive or over-the-top warmth ("it's truly inspiring to witness your
dedication...") is not on its own disrespectful -- score it 2 unless it
also reads as insincere or mocking in context.

### Completeness (0 / 1 / 2)

- 2 -- Covers what's needed to act. Includes every policy condition
  relevant to this request (timeframe, required evidence or steps, who
  pays, what happens next). When the honest answer requires more
  information from the customer, clearly stating what's needed and why
  counts as covering what's needed -- it does not need to also guess the
  rest.
- 1 -- Covers the main point but misses a detail (for example, confirms a
  refund will happen but not the timeframe, or omits a required
  photo/step).
- 0 -- Doesn't address the actual question, or is so short or generic that
  the customer has no actionable next step.

### Borderline cases

- Clarifying questions: don't penalize completeness for omitting details
  that depend on information the reply correctly asked for and doesn't
  yet have.
- Policy gaps: if policy_excerpt says the situation isn't covered, a
  reply that says so and offers to escalate beats a reply that confidently
  invents an answer, even if the invented answer sounds plausible. Do not
  reward a specific, confident-sounding process for a request the policy
  doesn't cover.
- Multiple issues at once: if several problems exist on one axis, base the
  score on the single worst disqualifying issue, and name that issue in
  the reason.

## Output format

Return exactly one JSON object and nothing else -- no markdown fences, no
explanation before or after it. The object must have exactly these seven
fields:

{{
  "item_id": "<copy item_id exactly as given>",
  "correctness": <0, 1, or 2>,
  "correctness_reason": "<one short sentence, cite the specific rule id if the policy_excerpt has one, e.g. 'Contradicts DMG-4.'>",
  "politeness": <0, 1, or 2>,
  "politeness_reason": "<one short sentence>",
  "completeness": <0, 1, or 2>,
  "completeness_reason": "<one short sentence>"
}}

Each reason must be a non-empty, specific sentence a human could use to
audit your score without re-reading the whole reply -- not a restatement
of the score itself ("it was correct" is not an acceptable reason).

## Input

item_id: {item_id}

customer_message:
{customer_message}

policy_excerpt:
{policy_excerpt}

candidate_reply:
{candidate_reply}
