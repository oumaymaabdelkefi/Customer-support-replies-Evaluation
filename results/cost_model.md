# Cost model

Measured from the token counts and latencies recorded in `results/*.jsonl` (paid-tier list prices; the Groq free tier used for this project costs $0).

## Per item (measured)

| Component | Model | Calls measured | Avg tokens | Cost / item | Cost / 1k | p50 latency | p95 latency |
|---|---|---|---|---|---|---|---|
| Judge (grade one reply) | gpt-oss-120b | 99 | 2,216 | $0.0006 | $0.57 | 1.64s | 2.94s |
| System (write one reply) | gpt-oss-20b | 0 | – | – | – | – | – |

## Daily cost: today (1,000 replies/day) vs 100x (100,000/day)

| Scenario | Cost / 1k requests | Today / day | Today / month | 100x / day | 100x / month |
|---|---|---|---|---|---|
| Judge every reply | $0.57 | $0.57 | $17.15 | $57.17 | $1,715.19 |

## What changes at 100x

- **Free tier stops being an option.** At ~2,216 tokens per judged item, the free tier's 200,000 tokens/day per model allows about 90 judged items a day -- already below 1,000/day, far below 100,000.
- **Per-1k cost stays the same** on pay-per-token pricing; the monthly total scales linearly.
- **Levers:** judge a sample instead of every reply; Groq's Batch API (50% off, 24h turnaround) for offline evaluation; cache the fixed rubric prefix (prompt caching discounts repeated prefix tokens); a smaller judge only if it keeps agreement with humans.
- **Latency** is per call and doesn't grow with volume, but per-minute rate limits do: at 100x, requests must be spread out or a higher tier used.

Assumptions: 1,000 replies/day today (`--requests-per-day`), 30-day month, prices as configured in `harness/systems/judge_stub.py` (gpt-oss-120b $0.15/$0.60 per 1M in/out) and `harness/systems/reply_system.py` (gpt-oss-20b $0.075/$0.30). Verify at https://groq.com/pricing.
