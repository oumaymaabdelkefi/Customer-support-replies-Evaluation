from harness.schema import ItemInput
import types

import pytest

from harness.errors import QuotaExhausted
from harness.systems import judge_stub
from harness.systems.judge_stub import _build_prompt, _extract_json, _is_daily_quota_error


def make_item():
    return ItemInput(
        item_id="P99",
        customer_message="Can I get a refund?",
        policy_excerpt="[RET-1] Refunds within 30 days.",
        candidate_reply="Yes, within 30 days of delivery.",
    )


def test_build_prompt_fills_all_placeholders():
    prompt = _build_prompt(make_item())
    assert "P99" in prompt
    assert "Can I get a refund?" in prompt
    assert "[RET-1] Refunds within 30 days." in prompt
    assert "Yes, within 30 days of delivery." in prompt
    # the JSON example block should survive formatting intact
    assert '"item_id"' in prompt
    assert '"correctness"' in prompt


def test_extract_json_plain():
    raw = '{"item_id": "P99", "correctness": 2, "correctness_reason": "x", "politeness": 2, "politeness_reason": "x", "completeness": 2, "completeness_reason": "x"}'
    parsed = _extract_json(raw)
    assert parsed["item_id"] == "P99"
    assert parsed["correctness"] == 2


def test_extract_json_strips_markdown_fences():
    raw = '```json\n{"item_id": "P99", "correctness": 1, "correctness_reason": "x", "politeness": 1, "politeness_reason": "x", "completeness": 1, "completeness_reason": "x"}\n```'
    parsed = _extract_json(raw)
    assert parsed["item_id"] == "P99"
    assert parsed["correctness"] == 1


def test_extract_json_bad_input_raises():
    import json

    try:
        _extract_json("not json at all")
        assert False, "should have raised"
    except json.JSONDecodeError:
        pass


def test_daily_quota_error_detection():
    tpd = "Rate limit reached ... on tokens per day (TPD): Limit 200000, Used 198722"
    tpm = "Rate limit reached ... on tokens per minute (TPM): Limit 8000. Please try again in 4.2s"
    assert _is_daily_quota_error(tpd)
    assert not _is_daily_quota_error(tpm)


class _FakeCompletions:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.behaviour()


def _install_fake_openai(monkeypatch, behaviour):
    import openai

    completions = _FakeCompletions(behaviour)
    fake_client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: fake_client)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(judge_stub, "MIN_SECONDS_BETWEEN_CALLS", 0)
    return completions


def test_llm_judge_requests_schema_and_reports_meta(monkeypatch):
    content = '{"item_id": "P99", "correctness": 2, "correctness_reason": "x", "politeness": 2, "politeness_reason": "x", "completeness": 1, "completeness_reason": "x"}'
    response = types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))],
        usage=types.SimpleNamespace(prompt_tokens=1_000_000, completion_tokens=1_000_000),
    )
    completions = _install_fake_openai(monkeypatch, lambda: response)

    result = judge_stub.llm_judge(make_item())

    assert completions.kwargs["response_format"]["type"] == "json_schema"
    assert completions.kwargs["response_format"]["json_schema"]["strict"] is True
    meta = result.pop("_meta")
    assert meta["prompt_tokens"] == 1_000_000
    assert meta["cost_usd"] == pytest.approx(
        judge_stub.PRICE_PER_M_INPUT_TOKENS + judge_stub.PRICE_PER_M_OUTPUT_TOKENS
    )
    assert meta["latency_s"] >= 0
    assert result["completeness"] == 1


def test_llm_judge_raises_quota_exhausted_without_retrying(monkeypatch):
    import httpx
    import openai

    calls = []

    def behaviour():
        calls.append(1)
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        raise openai.RateLimitError(
            "Rate limit reached on tokens per day (TPD): Limit 200000",
            response=httpx.Response(429, request=request),
            body=None,
        )

    _install_fake_openai(monkeypatch, behaviour)
    with pytest.raises(QuotaExhausted):
        judge_stub.llm_judge(make_item())
    assert len(calls) == 1
