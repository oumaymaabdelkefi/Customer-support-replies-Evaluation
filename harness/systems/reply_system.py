"""
The prompted system under test: an LLM that writes a customer-support
reply from the customer message and the policy excerpt. The harness then
grades that reply with the LLM judge, so each result row is "how good was
the reply this system wrote", on the same 0/1/2 axes as the golden set.

Registered in harness/run.py as reply_v1, reply_v2, ... -- one per prompt
file prompts/system_v<N>.txt, so every prompt version can be run and
compared with one command:

    python -m harness.run --system reply_v1 --items data/golden_set.jsonl --split dev

The writer is a different, smaller model than the judge (gpt-oss-20b vs
gpt-oss-120b), so the judge isn't grading its own model's writing. On the
Groq free tier the two models also have separate daily quotas.

Each row's `meta` holds the generated reply plus cost/latency split into
the system's own cost (what a production deployment would pay) and the
judge's cost (the price of evaluating it).
"""

from __future__ import annotations

from pathlib import Path

from harness.schema import ItemInput
from harness.systems import judge_stub

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
SYSTEM_MODEL = "openai/gpt-oss-20b"
# Groq on-demand price for gpt-oss-20b, USD per 1M input/output tokens.
# Check https://groq.com/pricing before quoting cost numbers in the report.
SYSTEM_PRICES = (0.075, 0.30)


def prompt_path(version: int) -> Path:
    return PROMPTS_DIR / f"system_v{version}.txt"


def make_reply_system(version: int):
    path = prompt_path(version)
    if not path.exists():
        raise ValueError(f"No system prompt at {path}")
    template = path.read_text(encoding="utf-8")

    def reply_system(item: ItemInput) -> dict:
        prompt = template.format(
            customer_message=item.customer_message,
            policy_excerpt=item.policy_excerpt,
        )
        reply, gen_meta = judge_stub.chat_groq(
            prompt, f"{item.item_id} write", model=SYSTEM_MODEL, prices=SYSTEM_PRICES
        )
        reply = reply.strip()
        if not reply:
            raise RuntimeError("System returned an empty reply")

        # Grade the generated reply exactly like a golden-set reply.
        graded = judge_stub.llm_judge(item.model_copy(update={"candidate_reply": reply}))
        judge_meta = graded.pop("_meta", {})
        graded["_meta"] = {
            "generated_reply": reply,
            "system_model": SYSTEM_MODEL,
            "system_prompt": path.name,
            "system_cost_usd": gen_meta["cost_usd"],
            "system_latency_s": gen_meta["latency_s"],
            "system_prompt_tokens": gen_meta["prompt_tokens"],
            "system_completion_tokens": gen_meta["completion_tokens"],
            "judge_cost_usd": judge_meta.get("cost_usd", 0.0),
            # Totals, so the harness summary reports the full cost of a run.
            "cost_usd": gen_meta["cost_usd"] + judge_meta.get("cost_usd", 0.0),
            "latency_s": round(gen_meta["latency_s"] + judge_meta.get("latency_s", 0.0), 3),
            "prompt_tokens": gen_meta["prompt_tokens"] + judge_meta.get("prompt_tokens", 0),
            "completion_tokens": gen_meta["completion_tokens"] + judge_meta.get("completion_tokens", 0),
        }
        return graded

    reply_system.__name__ = f"reply_v{version}"
    return reply_system
