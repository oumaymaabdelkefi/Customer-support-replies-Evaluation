from harness.schema import ItemInput
from harness.systems.judge_stub import _build_prompt, _extract_json


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
