"""
Fixed output schema for anything the harness scores (a judge, a baseline,
a future trained model). This is the contract from ROLE_C_HANDOFF.md,
confirmed here so Role C's judge and Role B's harness never drift apart.

Score scale: 0 / 1 / 2 per axis, matching data/labelling_guide.md exactly.
  2 = fully meets the axis
  1 = partially meets it
  0 = fails it
Each axis carries its own short reason string, so a human can audit a
disagreement without re-reading the whole reply.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

Score = Literal[0, 1, 2]


class ItemInput(BaseModel):
    """What a system is given for one item. Mirrors exactly what a human
    labeller sees per data/labelling_guide.md -- no challenge_type, no
    author_note, no other pilot-only metadata."""

    item_id: str
    customer_message: str
    policy_excerpt: str
    candidate_reply: str


class JudgeOutput(BaseModel):
    """What any system must return for one item. Extra/missing fields,
    or scores outside {0,1,2}, fail validation -- the harness never
    guesses from free text."""

    item_id: str
    correctness: Score
    correctness_reason: str = Field(min_length=1)
    politeness: Score
    politeness_reason: str = Field(min_length=1)
    completeness: Score
    completeness_reason: str = Field(min_length=1)

    model_config = {"extra": "forbid"}


class ScoredRow(BaseModel):
    """One row of results/*.jsonl: the harness's actual unit of output.
    Combines the item's input with the system's validated output, plus
    a derived overall pass/fail, or a parse_error if validation failed."""

    item_id: str
    input: ItemInput
    output: JudgeOutput | None = None
    score: int | None = None  # correctness + politeness + completeness, 0-6
    passed: bool | None = None
    parse_error: str | None = None
    raw_response: str | None = None
    # Per-call cost/latency info a system chooses to report (tokens,
    # latency_s, cost_usd, ...). Kept apart from `output` so it never
    # affects schema validation of the scores themselves.
    meta: dict | None = None

    @staticmethod
    def total_score(output: JudgeOutput) -> int:
        return output.correctness + output.politeness + output.completeness

    @staticmethod
    def overall_pass(output: JudgeOutput) -> bool:
        """A reply passes overall only if all three axes score 2.
        (Matches the SupportScore doc's "all three must pass" rule,
        translated to the 0/1/2 scale: pass = perfect on every axis.)"""
        return output.correctness == 2 and output.politeness == 2 and output.completeness == 2


def validate_system_output(raw: dict) -> tuple[JudgeOutput | None, str | None]:
    """Validate a system's raw dict against JudgeOutput.
    Returns (parsed_output, None) on success, or (None, error_message)
    on failure -- the harness never silently accepts malformed output."""
    try:
        return JudgeOutput.model_validate(raw), None
    except ValidationError as e:
        return None, str(e)
