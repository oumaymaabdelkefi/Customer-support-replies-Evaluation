# SupportScore — Customer Support Reply Grader

CS496 AI Engineering, Project 1 (The Grader). An evaluation harness, an
LLM judge and a prompted reply-writing system for customer-support replies
at *TechNest Gadgets* (a fictional retailer). Every reply is scored 0 / 1 / 2
on three axes:

- **Correctness**: consistent with the policy excerpt, nothing invented
- **Politeness**: respectful, no blame or sarcasm
- **Completeness**: gives the customer everything needed to act

## Setup

```bash
pip install -r requirements.txt
```

The judge and the system use Groq (free tier works). Get a key at
https://console.groq.com/keys and set it as an environment variable. Never
commit it.

```bash
export GROQ_API_KEY=gsk_...          # bash
$env:GROQ_API_KEY = "gsk_..."        # PowerShell
```

## Run

```bash
python -m harness.run --system llm_judge --items data/golden_set.jsonl --split test
```

Each run writes one row per item (input, output scores, reasons, cost,
latency) to `results/<system>_<timestamp>.jsonl` and prints a summary.

| System | What it does |
|---|---|
| `llm_judge` / `llm_judge_v2` | The judge (`gpt-oss-120b`) grading each golden-set reply, with `prompts/judge_v<N>.txt` |
| `reply_v1`, `reply_v2`, ... | The system under test: `gpt-oss-20b` writes a reply with `prompts/system_v<N>.txt`, then the judge grades it |
| `keyword_baseline`, `always_perfect` | Sanity-check baselines |

`--split dev|test` runs one split (`data/splits.json`): tune prompts on
`dev`, report on `test`. `--resume <results file>` finishes a run cut short
by the free tier's daily limit (~90 judged items/day) without repeating
scored items. `JUDGE_PROMPT_VERSION=2` makes `llm_judge` (and the reply
system's grading) use judge v2.

### Interface

```bash
python scripts/dashboard_server.py     # opens http://localhost:8765
```

Overview, judge vs humans per item (with gold / labeller filters and the
judge's reasons), position bias, verbosity bias, runs and cost, and a
**Run tests** tab with buttons for every run below and live output.

### Measurements

```bash
# Human agreement and gold labels
python scripts/compute_kappa.py --labeler1 data/labelling_sheet_labeler1_stage2.csv \
    --labeler2 data/labelling_sheet_labeler2_stage2.csv --out kappa_report_stage2.md
python scripts/build_gold_labels.py                     # -> data/gold_labels.csv

# Judge vs humans (gold = score both labellers agree on)
python scripts/judge_reliability.py --judge-results results/<run>.jsonl \
    --human-labels data/gold_labels.csv

# Judge bias
python scripts/position_bias.py                          # order swapped
python scripts/verbosity_bias.py make --split dev        # padded replies
python -m harness.run --system llm_judge --items data/bias/verbosity_padded.jsonl
python scripts/verbosity_bias.py report --original results/llm_judge_dev_<ts>.jsonl \
    --padded results/llm_judge_<ts>.jsonl

# Where the judge fails: replies built to trick it
python scripts/make_adversarial_set.py
python -m harness.run --system llm_judge --items data/bias/adversarial.jsonl
python scripts/judge_reliability.py --judge-results results/llm_judge_<ts>.jsonl \
    --human-labels data/bias/adversarial_expected.csv

# Cost model (from measured tokens; no API calls)
python scripts/cost_model.py                             # -> results/cost_model.md
```

### Golden set and labelling

```bash
python scripts/merge_golden_set.py      # batches -> data/golden_set.jsonl (checks excerpts are verbatim)
python scripts/split_golden_set.py      # assigns new items to dev/test, never moves old ones
python scripts/make_labelling_xlsx.py   # blind Excel labelling sheets
python scripts/import_labels.py --xlsx data/labels/<file>.xlsx --labeller 1
```

Tests: `python -m pytest tests/ -q`

## Repo layout

| Path | Contents |
|---|---|
| `data/` | Golden set (150 items), labelling guide (v0.3), policy, labelling sheets, gold labels, dev/test split |
| `data/labels/` | The labellers' filled Excel sheets |
| `data/bias/` | Padded (verbosity) and adversarial item sets |
| `harness/` | Runner, schema, metrics, judge, reply system, baselines |
| `prompts/` | Judge, pairwise and system prompts + `CHANGELOG.md` (score before/after each change) |
| `results/` | Per-item results for every run, cost model, dashboard |
| `scripts/` | Data building, agreement, bias tests, cost model, interface |
| `tests/` | Unit tests |

## Results

| Measure | Value | Source |
|---|---|---|
| Golden set | 150 items (dev 74 / test 76), 4 themes | `data/golden_set.jsonl`, `data/splits.json` |
| Human agreement, first 48 items, before discussion (κ C / P / M) | 0.62 / 0.26 / 0.18 | `kappa_report.md` |
| Human agreement, 102 new items (κ C / P / M) | 0.65 / 0.57 / 0.43 (exact 81 / 81 / 64 of 102) | `kappa_report_stage2.md` |
| Gold labels (both labellers agree) | 128 / 129 / 95 of 150 per axis | `data/gold_labels.csv` |
| Judge v1 vs gold, dev (κ C / P / M) | 0.66 / 0.68 / 0.65 (exact 51/64, 55/63, 39/48) | `prompts/CHANGELOG.md` |
| Judge v2 vs gold, dev | see `prompts/CHANGELOG.md` | |
| Judge run-to-run stability | 39/43 items identical on all three axes | `prompts/CHANGELOG.md` |
| Position bias | 0/10 verdicts changed after swapping order | `data/position_bias_report.md` |
| Verbosity bias | partial (13 items): total grade up on 3/13 | `results/dashboard.html` |
| Cost / latency per judged item | $0.00056 (paid-tier eq.), p50 ≈ 1.5 s | `results/cost_model.md` |
| System score on test set | see `prompts/CHANGELOG.md` | |

Details: `prompts/CHANGELOG.md`, `results/cost_model.md`, `postmortem.md`,
`report.pdf`.

## Contributions

From the git history; each member should check and expand their entry.

- **Oumayma Abdelkefi** — harness (runner, schema, metrics, tests), LLM
  judge and prompts, Groq integration, golden-set stage 2, dev/test split,
  bias tests, interface, data clean-up and validation.
- **Aziz Benzarti** — first golden-set batches (pilot / stage 1 items).
- **Youssef Turki** — 10 stage-2 items (G59–G68); labeller 2 for the
  stage-2 items.
- **Noura Haddaoui** — labeller 1 for the stage-2 items.
- _Labellers for the first 48 items: to be filled in._

AI assistance: Claude (Anthropic) was used for parts of the code, for
drafting 62 of the golden-set items (G69–G130, marked `llm_drafted`) and
for drafting the postmortem. All labels are human.
