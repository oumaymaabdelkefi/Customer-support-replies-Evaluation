# SupportScore — Customer Support Reply Grader

CS496 AI Engineering, Project 1 (The Grader). An evaluation harness and an
LLM judge that grades customer-support replies for *TechNest Gadgets* (a
fictional retailer) on three axes, each scored 0 / 1 / 2:

- **Correctness**: consistent with the policy excerpt, nothing invented
- **Politeness**: respectful, no blame or sarcasm
- **Completeness**: gives the customer everything needed to act

## Setup

```bash
pip install -r requirements.txt
```

The LLM judge uses Groq (`openai/gpt-oss-120b`). Get a free key at
https://console.groq.com/keys and set it as an environment variable. Never
commit it.

```bash
export GROQ_API_KEY=gsk_...          # bash
$env:GROQ_API_KEY = "gsk_..."        # PowerShell
```

## Run

```bash
python -m harness.run --system llm_judge --items data/golden_set.jsonl
```

**Free tier:** the judge runs on Groq's free tier. On `gpt-oss-120b` the
free tier allows about 200k tokens per day, roughly 115 judged items at
~1.7k tokens each. If a run hits that limit, the remaining items are
marked as skipped. Finish the run the next day without re-paying for
items already scored:

```bash
python -m harness.run --system llm_judge --items data/golden_set.jsonl     --resume results/llm_judge_<timestamp>.jsonl
```

`cost_usd` in each row's `meta` is what the call *would* cost on Groq's
paid tier. Actual spend on the free tier is $0. The paid-tier figure is
the basis for the cost model (cost per 1k requests, today and at 100x).

Other systems: `always_perfect`, `keyword_baseline`. Each run writes one
row per item to `results/<system>_<timestamp>.jsonl` and prints a summary.

**Dev/test split** (`data/splits.json`, made by
`scripts/split_golden_set.py`): tune prompts on `dev`, report final
numbers on `test` only. Re-run the split script after adding items; it
assigns only new items and never moves existing ones.

```bash
python -m harness.run --system llm_judge --items data/golden_set.jsonl --split dev
```

Judge bias checks:

```bash
# Position bias: pairs of replies to the same message, judged in both orders
python scripts/position_bias.py

# Verbosity bias: pad replies with content-free filler, re-judge, compare
python scripts/verbosity_bias.py make --split dev
python -m harness.run --system llm_judge --items data/bias/verbosity_padded.jsonl
python scripts/verbosity_bias.py report --original results/llm_judge_dev_<ts>.jsonl     --padded results/llm_judge_<ts>.jsonl
```

Agreement reports:

```bash
python scripts/compute_kappa.py --labeler1 data/labelling_sheet_labeler1_completed.csv \
    --labeler2 data/labelling_sheet_labeler2_completed.csv --out kappa_report.md
python scripts/judge_reliability.py --judge-results results/<run>.jsonl \
    --human-labels data/labelling_sheet_labeler1_completed.csv
```

Tests: `python -m pytest tests/ -v`

## Repo layout

| Path | Contents |
|---|---|
| `data/` | Golden set (`golden_set.jsonl`), labelling guide, policy, labelling sheets |
| `harness/` | Runner, schema, metrics, systems (baselines + LLM judge) |
| `prompts/` | Versioned prompts + `CHANGELOG.md` (score before/after each change) |
| `results/` | Per-item results for every run |
| `scripts/` | Golden-set generation, kappa, judge reliability |
| `tests/` | Unit tests for schema, runner, judge |

## Results

<!-- TODO: fill in once the full golden set is labelled and split. -->

| Measure | Value |
|---|---|
| Golden set size | 78 items (target 150+) |
| Labeller agreement (κ) — correctness / politeness / completeness | 0.62 / 0.26 / 0.18 (48 items) |
| Judge vs. human (κ) — correctness / politeness / completeness | 0.81 / 0.81 / 0.69 (20 pilot items) |
| Position bias (verdict flips after swap) | TODO |
| Verbosity bias (grade up after padding) | TODO |
| Cost / latency per judged item | TODO |
| System score on test set | TODO |

See `kappa_report.md`, `data/judge_reliability_report.md`, `report.pdf`
and `postmortem.md` for details.

## Contributions

<!-- TODO: one entry per team member -->

- **Role A — Golden set & labelling:** TODO (name)
- **Role B — Harness:** TODO (name)
- **Role C — Judge & prompts:** TODO (name)
- **Role D — Evaluation & report:** TODO (name)
