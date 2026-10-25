"""
Cost model (brief: "cost per 1k requests, today and at 100x", "cost and
latency per judged item"). Reads the measured token counts and latencies
from results/*.jsonl -- no API calls -- and writes results/cost_model.md.

Usage:
    python scripts/cost_model.py
    python scripts/cost_model.py --requests-per-day 1000

Assumptions (stated in the output):
- Prices are Groq's on-demand list prices per 1M tokens, as configured in
  harness/systems/judge_stub.py and reply_system.py.
- "Today" = --requests-per-day customer replies (default 1,000/day);
  "100x" = 100 times that. Per-1k cost is the same at both volumes on
  pay-per-token pricing; what changes is the daily total and whether the
  free tier is usable at all.
- In production every reply is written by the system; judging is an
  evaluation cost, shown both for "judge every reply" and "judge a 5%
  sample".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"
OUT = RESULTS / "cost_model.md"
FREE_TIER_TOKENS_PER_DAY = 200_000  # Groq free tier, per model (observed in 429 messages)


def metas(pattern: str, key_cost: str = "cost_usd") -> list[dict]:
    out = []
    for path in sorted(RESULTS.glob(pattern)):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                m = row.get("meta")
                if m and row.get("output") and key_cost in m:
                    out.append(m)
    return out


def summarize(ms: list[dict], cost="cost_usd", lat="latency_s", tin="prompt_tokens", tout="completion_tokens"):
    if not ms:
        return None
    costs = [m[cost] for m in ms]
    lats = sorted(m[lat] for m in ms if lat in m)
    tokens = [m.get(tin, 0) + m.get(tout, 0) for m in ms]
    return {
        "n": len(ms),
        "cost": sum(costs) / len(costs),
        "p50": median(lats) if lats else None,
        "p95": lats[min(len(lats) - 1, int(len(lats) * 0.95))] if lats else None,
        "tokens": sum(tokens) / len(tokens),
    }


def money(x: float) -> str:
    return f"${x:,.2f}" if x >= 0.1 else f"${x:,.4f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--requests-per-day", type=int, default=1000)
    args = parser.parse_args()

    judge = summarize([m for m in metas("llm_judge_*.jsonl") if "generated_reply" not in m])
    reply_ms = metas("reply_v*.jsonl", "system_cost_usd")
    system = summarize(reply_ms, cost="system_cost_usd", lat="system_latency_s",
                       tin="system_prompt_tokens", tout="system_completion_tokens")

    lines = ["# Cost model", "",
             "Measured from the token counts and latencies recorded in `results/*.jsonl` "
             "(paid-tier list prices; the Groq free tier used for this project costs $0).", "",
             "## Per item (measured)", "",
             "| Component | Model | Calls measured | Avg tokens | Cost / item | Cost / 1k | p50 latency | p95 latency |",
             "|---|---|---|---|---|---|---|---|"]
    for name, model, s in [("Judge (grade one reply)", "gpt-oss-120b", judge),
                           ("System (write one reply)", "gpt-oss-20b", system)]:
        if s:
            lines.append(f"| {name} | {model} | {s['n']} | {s['tokens']:,.0f} | {money(s['cost'])} | "
                         f"{money(s['cost'] * 1000)} | {s['p50']:.2f}s | {s['p95']:.2f}s |")
        else:
            lines.append(f"| {name} | {model} | 0 | – | – | – | – | – |")

    v = args.requests_per_day
    lines += ["", f"## Daily cost: today ({v:,} replies/day) vs 100x ({100 * v:,}/day)", "",
              "| Scenario | Cost / 1k requests | Today / day | Today / month | 100x / day | 100x / month |",
              "|---|---|---|---|---|---|"]
    scenarios = []
    if system:
        scenarios.append(("System only (write replies)", system["cost"], system["tokens"]))
    if system and judge:
        scenarios.append(("System + judge 5% sample", system["cost"] + 0.05 * judge["cost"],
                          system["tokens"] + 0.05 * judge["tokens"]))
        scenarios.append(("System + judge every reply", system["cost"] + judge["cost"],
                          system["tokens"] + judge["tokens"]))
    elif judge:
        scenarios.append(("Judge every reply", judge["cost"], judge["tokens"]))
    for name, per_item, _ in scenarios:
        lines.append(f"| {name} | {money(per_item * 1000)} | {money(per_item * v)} | {money(per_item * v * 30)} | "
                     f"{money(per_item * v * 100)} | {money(per_item * v * 100 * 30)} |")

    lines += ["", "## What changes at 100x", ""]
    if judge:
        per_day_free = FREE_TIER_TOKENS_PER_DAY / judge["tokens"]
        lines.append(f"- **Free tier stops being an option.** At ~{judge['tokens']:,.0f} tokens per judged "
                     f"item, the free tier's {FREE_TIER_TOKENS_PER_DAY:,} tokens/day per model allows about "
                     f"{per_day_free:,.0f} judged items a day -- already below {v:,}/day, far below {100 * v:,}.")
    lines += [
        "- **Per-1k cost stays the same** on pay-per-token pricing; the monthly total scales linearly.",
        "- **Levers:** judge a sample instead of every reply; Groq's Batch API (50% off, 24h turnaround) "
        "for offline evaluation; cache the fixed rubric prefix (prompt caching discounts repeated "
        "prefix tokens); a smaller judge only if it keeps agreement with humans.",
        "- **Latency** is per call and doesn't grow with volume, but per-minute rate limits do: at 100x, "
        "requests must be spread out or a higher tier used.",
        "",
        f"Assumptions: {v:,} replies/day today (`--requests-per-day`), 30-day month, prices as configured in "
        "`harness/systems/judge_stub.py` (gpt-oss-120b $0.15/$0.60 per 1M in/out) and "
        "`harness/systems/reply_system.py` (gpt-oss-20b $0.075/$0.30). Verify at https://groq.com/pricing.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
