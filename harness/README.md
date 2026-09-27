# harness/

The evaluation harness. Runs any registered "system" over a jsonl item
set and writes one validated row per item to `results/`.

## Quick start

```bash
pip install pydantic pytest --break-system-packages   # or use a venv

# run a baseline against Role A's pilot set
python3 -m harness.run --system always_perfect --items data/pilot_items.jsonl
python3 -m harness.run --system keyword_baseline --items data/pilot_items.jsonl

# once Role C implements harness/systems/judge_stub.py::llm_judge
python3 -m harness.run --system llm_judge --items data/pilot_items.jsonl

# run the tests
python3 -m pytest tests/ -v
```

## How it fits together

```
data/pilot_items.jsonl
        |
        v
harness/run.py  --items ...  --system <name>
        |
        |  loads ItemInput (customer_message, policy_excerpt,
        |  candidate_reply only -- strips internal-only fields
        |  like challenge_type, author_note)
        v
harness/systems/<system>.py   <- the thing being measured
        |
        |  returns a raw dict
        v
harness/schema.py :: validate_system_output()
        |
        |  0/1/2 per axis + a reason string per axis,
        |  matching data/labelling_guide.md exactly
        v
results/<system>_<timestamp>.jsonl
        |
        |  one row per item: item_id, input, output,
        |  passed (all 3 axes == 2), parse_error if invalid
        v
harness/metrics.py :: summarize()   <- printed after every run
```

## Adding a new system

Any callable `ItemInput -> dict` can be registered. See
`harness/systems/baselines.py` for two working examples
(`always_perfect`, `keyword_baseline`), and
`harness/systems/judge_stub.py` for the stub Role C should fill in with
the real LLM judge. Register new systems in `SYSTEMS` in
`harness/systems/baselines.py`, or add an explicit case in
`harness/run.py::resolve_system` (as done for `llm_judge`).

## What's still open

- `llm_judge` is a stub (`NotImplementedError`) until Role C wires in the
  real prompt call. The harness already runs it gracefully -- every item
  comes back with `parse_error` set, not a crash -- so the pipeline can
  be tested today without blocking on Role C.
- `keyword_baseline` is a deliberately dumb heuristic, useful only as a
  sanity check that the harness distinguishes good/bad replies at all --
  not a real "baseline to beat."
- Once Role A's full 150+ golden set exists with real human labels,
  `harness/metrics.py` will need a second function to compare a system's
  output against those labels (agreement %, per-axis confusion), not just
  summarize a single run in isolation. Not built yet -- flagged for
  whoever owns the judge reliability report (Role C) and evaluation
  writeup (Role D).
