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
