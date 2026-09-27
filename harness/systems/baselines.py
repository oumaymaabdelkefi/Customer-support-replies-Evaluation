"""
A "system" is any callable: ItemInput -> dict, where the dict should
match harness.schema.JudgeOutput. The harness doesn't care whether it's
an LLM judge, a rule-based baseline, or a trained model -- it only
validates the shape that comes back.

This module holds simple baselines so the harness can be built and tested
before Role C's real judge prompt is ready.
"""

from __future__ import annotations

from harness.schema import ItemInput


def always_perfect(item: ItemInput) -> dict:
    """Dummy baseline: scores everything 2/2/2. Useless as a real judge,
    but lets us test that the harness plumbing works end to end."""
    return {
        "item_id": item.item_id,
        "correctness": 2,
        "correctness_reason": "baseline: always_perfect ignores content",
        "politeness": 2,
        "politeness_reason": "baseline: always_perfect ignores content",
        "completeness": 2,
        "completeness_reason": "baseline: always_perfect ignores content",
    }


def keyword_baseline(item: ItemInput) -> dict:
    """A slightly less dumb baseline: flags a few obvious rude/incorrect
    signal words. This is NOT a serious model -- it exists so the team
    has something non-trivial to compare the LLM judge against while
    Role C's real judge prompt is still being developed."""
    reply = item.candidate_reply.lower()

    rude_markers = ["you probably", "should've", "not our problem", "figure it out"]
    politeness = 0 if any(m in reply for m in rude_markers) else 2

    # crude correctness heuristic: flag if reply asserts something the
    # policy excerpt doesn't mention at all (e.g. "instantly", "same day")
    # when the excerpt talks about a multi-day window -- deliberately
    # naive, this is a baseline, not a competitor to the real judge.
    suspicious_claims = ["instantly", "same day", "immediately no matter"]
    correctness = 0 if any(c in reply for c in suspicious_claims) else 1

    completeness = 1  # baseline can't meaningfully judge this; always "partial"

    return {
        "item_id": item.item_id,
        "correctness": correctness,
        "correctness_reason": "baseline: keyword heuristic on suspicious claims",
        "politeness": politeness,
        "politeness_reason": "baseline: keyword heuristic on rude markers",
        "completeness": completeness,
        "completeness_reason": "baseline: no real completeness check, default partial",
    }


# ---------------------------------------------------------------------
# Role C plugs the real judge in here. Signature must match:
#   def llm_judge(item: ItemInput) -> dict
# and the dict must validate against harness.schema.JudgeOutput.
# See harness/systems/judge_stub.py for the expected call shape.
# ---------------------------------------------------------------------

SYSTEMS = {
    "always_perfect": always_perfect,
    "keyword_baseline": keyword_baseline,
}
