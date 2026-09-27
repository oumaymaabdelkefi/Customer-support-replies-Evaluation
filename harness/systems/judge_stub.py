"""
Stub for Role C's real LLM judge. This file defines the exact call shape
the harness expects -- Role C should implement `llm_judge()` here (or
import their real implementation and re-export it as `llm_judge`) once
prompts/judge_v1.txt exists.

Until then this stub raises, so it's obvious in results/ if someone
accidentally runs "judge" before it's implemented, instead of silently
producing fake scores.
"""

from __future__ import annotations

from harness.schema import ItemInput


def llm_judge(item: ItemInput) -> dict:
    """
    Expected behavior once implemented:
      1. Build a prompt from prompts/judge_v1.txt, filling in
         item.customer_message, item.policy_excerpt, item.candidate_reply.
      2. Call the LLM API (Claude/GPT) with structured output requested.
      3. Parse the response into a dict matching harness.schema.JudgeOutput:
         {item_id, correctness, correctness_reason,
          politeness, politeness_reason, completeness, completeness_reason}
      4. Return that dict. The harness validates it -- do not pre-validate
         here, just return your best parse; malformed output should still
         come back as a dict so the harness's error path is exercised.

    Raises NotImplementedError until Role C wires in the real prompt call.
    """
    raise NotImplementedError(
        "Role C: implement llm_judge() here, or import your real "
        "implementation and re-export it as `llm_judge` from this module. "
        "See harness/systems/baselines.py for the expected dict shape."
    )
