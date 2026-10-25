# Postmortem — SupportScore (Project 1: The Grader)

> **Draft for the team to review.** Every number below comes from files in
> this repo (named in brackets). Edit anything you remember differently.

## Summary

We built a harness, an LLM judge (Groq, `gpt-oss-120b`), a 150-item
golden set labelled by two people, a reply-writing system to measure, and
bias checks. What worked: the harness, structured output, the judge on
correctness, and the position-bias test. What didn't: getting two humans
to agree on **completeness**, keeping one version of the labelling rules,
and running everything inside a free API tier.

## What went wrong

### 1. Our labellers kept disagreeing on completeness
- First 48 items, first round: κ = 0.62 / 0.26 / 0.18 (correctness /
  politeness / completeness) [`kappa_report.md`, generated before the
  discussion round].
- After discussing and revising those labels: 0.97 / 1.00 / 0.45 — the
  discussion fixed correctness and politeness but not completeness.
- New 102 items: 0.65 / 0.57 / 0.43; completeness agreed on only 64/102
  [`kappa_report_stage2.md`].
- **Cause:** the guide never said whether a reply that *leaves out* a rule
  should lose correctness or only completeness. Half of our completeness
  disagreements were this one question. We only wrote the rule down
  (guide v0.3) after 48 items were labelled — and one labeller then used
  an older sheet without it.
- **Lesson:** run a small pilot, list the disagreements, and fix the
  guide *before* labelling at scale. We did the pilot but didn't act on
  its biggest disagreement in time.

### 2. The labelling process wasn't as clean as it should be
- The completeness revision named in commit `2080458` ("revise
  completeness labelling guide") was never saved to the guide file.
- One labeller labelled items they had written (G59–G68), so those
  labels aren't blind.
- Neither stage-2 labeller left notes, so disagreements can't be traced
  to a reason without re-reading every item.
- One labeller's file was pushed before the other's was finished, so we
  can't fully guarantee independence.
- We had no time for a second discussion round. Instead of adjudicated
  labels we use the **agreed subset** as gold: a score only counts where
  both labellers gave it (128 / 129 / 95 of 150 per axis)
  [`data/gold_labels.csv`].

### 3. Data quality slipped when the team grew
- 8 of 10 items in one batch had **paraphrased** policy excerpts, and
  some changed the rule's meaning ("30 days of *purchase*" instead of
  "of *delivery*"). The excerpt is the judge's only source of truth, so
  this silently changes what "correct" means. We fixed them by hand and
  made `merge_golden_set.py` reject any excerpt that isn't verbatim.
- That batch was committed as "labeled data" with no labels in it.
- `merge_golden_set.py` reset the labelling sheets to blank on every run;
  re-running it after labelling would have wiped labels. Fixed to keep
  existing scores.
- 62 of the 150 items were drafted with an AI assistant to reach the
  150-item target in time [`data/SOURCE_AND_LICENSE.md`]. They are
  labelled by humans like every other item, but they are more uniform
  than real customer messages.

### 4. The free API tier shaped (and broke) our runs
- Gemini's free tier (5 requests/min) caused constant 429s; we switched
  to Groq.
- Groq's free tier allows ~200k tokens/day per model, about 90 judged
  items. Two full runs failed completely: 78/78 items errored because
  the API key wasn't set, and a later run lost 4 of 5 items to the daily
  limit [`results/llm_judge_1790605244.jsonl`, `llm_judge_1790607252.jsonl`].
- The OpenAI SDK retried 429s *silently* before our code saw them, which
  looked like a frozen terminal and got killed with Ctrl+C.
- **Fixes:** disabled SDK retries and print our own; fail fast on the
  daily limit instead of retrying; `--resume` to finish a run the next
  day; light pacing between calls.
- A run started from our interface lost 30 of 43 items when we restarted
  the interface server mid-run (the judge crashed writing progress
  output to a closed pipe) [`results/llm_judge_1792946194.jsonl`]. Fixed.

### 5. Our first judge numbers were too optimistic
- On the 20 hand-written pilot items the judge scored κ 0.81 / 0.81 /
  0.69 against labeller 1. On the harder real-data items it dropped to
  0.21 / 0.83 / 0.25 — the pilot was too easy to tell us anything.
- Measured against gold (only where both humans agree) on 74 dev items,
  judge_v1 reaches 0.66 / 0.68 / 0.65 [`prompts/CHANGELOG.md`]: much of
  the "judge error" was really human disagreement.
- Main judge failure: it followed a stricter politeness standard than our
  labellers (all 8 politeness disagreements were the judge scoring a
  short, courteous reply as "curt"), and it penalised wrong facts twice
  (correctness and completeness).

### 6. Smaller mistakes
- The root `CHANGELOG.md` was accidentally a copy of the judge prompt;
  the real changelog was saved as `prompts/CHANGELOG (1).md`, and the
  package file as `__init__ (1).py`. Compiled `.pyc` files were committed.
- `kappa_report.md` went stale after the labels were revised and still
  showed the pre-discussion numbers.
- Our position-bias test (0/10 flips) uses pairs where one reply is
  clearly better, so it is an easy test; pairs of similar quality would
  test the judge harder.

## What we learned

1. **Fix the rubric's biggest ambiguity before scaling labelling.** One
   unresolved question cost us most of our completeness agreement.
2. **Measure the judge against what humans agree on**, not against one
   labeller; otherwise human noise looks like judge error.
3. **Validate data mechanically.** A check that excerpts are verbatim
   caught a problem no reviewer noticed.
4. **Design for the API limits you actually have:** resumable runs,
   fail-fast on quotas, visible progress.
5. **A judge that agrees with humans on easy items tells you little** —
   test it on hard and adversarial cases.

## If we did it again

- Pilot → fix guide → *then* label at scale, with notes required.
- Labellers never label items they wrote; files exchanged only when both
  are done.
- Budget API quota per day from the start, or pay for the (cheap) paid
  tier for the final runs — all our judging would have cost under $1.
