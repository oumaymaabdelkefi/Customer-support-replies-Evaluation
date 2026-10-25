# Prompt Changelog

Every prompt revision is logged here with the score before/after on the
same item set, per the course brief's requirement to link every prompt
change to a measured score change.

## judge_v1 -- 2026-09-27

Initial judge prompt. Not yet run against real human labels (labeler 2
still in progress), so no agreement score exists yet.

Smoke-tested manually against 3 pilot items (P01, P02, P08) by hand-tracing
the rubric before wiring into the harness:
- P01 (correct, polite, complete reply): expected 2/2/2 -- matches.
- P02 ("refunds are instant" -- contradicts RET-4): expected correctness=0
  -- matches.
- P08 (rude reply, "you probably scratched it yourself"): expected
  politeness=0 -- matches.

No score history yet since this is the first version. Once labeler 2
finishes and data/golden_set.jsonl has real human labels, the first
real judge-vs-human agreement run becomes the v1 baseline to beat with
future prompt revisions.

## judge_v1 -- 2026-09-28 (implementation notes, no prompt-text change)

Two non-prompt fixes landed while wiring judge_v1 into a real API. Neither
changes the prompt's wording, so this stays v1 -- logged here for
traceability since both affected whether the prompt could even run.

- Fixed a bug in the "Output format" JSON example block: literal `{` `}`
  characters collided with Python's `str.format()` placeholder syntax and
  raised a KeyError before any API call was made. Escaped to `{{` `}}`.
  Verified by filling all 4 placeholders (item_id, customer_message,
  policy_excerpt, candidate_reply) against a real item.
- Switched the judge's backing model from Gemini (`gemini-3.8-flash`,
  free-tier rate limit of 5 req/min, caused repeated 429s and required
  aggressive throttling/retry logic) to `openai/gpt-oss-120b` served by
  Groq's free-tier OpenAI-compatible API. Same prompt text, same JSON
  schema, same retry-on-429 handling -- only the API client and env var
  changed (`GEMINI_API_KEY` -> `GROQ_API_KEY`). Result: 20/20 pilot items
  and 48/48 golden-set items parsed cleanly with no throttling needed,
  versus repeated truncation/rate-limit failures on the Gemini free tier.

First real judge-vs-human agreement run (Groq-backed judge_v1 vs.
Labeler 1, pilot set, 20 items): correctness kappa 0.813, politeness
kappa 0.810, completeness kappa 0.688 -- all above the brief's 0.6
target. This is now the v1 baseline; a future prompt revision (v2) should
be compared against these numbers on the same 20 items before being
adopted.

## judge_v1 -- 2026-10-25 (implementation notes, no prompt-text change)

Harness/judge plumbing changes. The prompt wording is unchanged, so this
stays v1, but the first change affects how the model's answer is decoded,
so the v1 agreement numbers should be re-measured on the same items before
being compared to any v2.

- Structured output: the judge now sends a strict JSON schema
  (`response_format=json_schema`, `strict: true`) matching
  `harness.schema.JudgeOutput`, so scores are constrained at decode time
  instead of relying on the model following "return JSON only".
- Cost and latency per judged item are recorded in each result row's
  `meta` field (prompt/completion tokens, latency, USD cost at Groq's
  listed $0.15 / $0.60 per 1M input/output tokens) and summarised after
  every run.
- Groq's daily token quota (TPD) is no longer retried: the run stops
  calling the API and marks the remaining items as skipped. Previously
  each item burned 4 retries against a limit that resets only daily
  (see results/llm_judge_1790607252.jsonl).
