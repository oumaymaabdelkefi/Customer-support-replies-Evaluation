from harness.schema import ItemInput, JudgeOutput, ScoredRow, validate_system_output


def make_item(**overrides):
    base = dict(
        item_id="T1",
        customer_message="Can I get a refund?",
        policy_excerpt="[RET-1] Refunds within 30 days.",
        candidate_reply="Yes, within 30 days of delivery.",
    )
    base.update(overrides)
    return ItemInput.model_validate(base)


def test_item_input_requires_all_fields():
    item = make_item()
    assert item.item_id == "T1"


def test_valid_output_parses():
    raw = {
        "item_id": "T1",
        "correctness": 2,
        "correctness_reason": "matches RET-1",
        "politeness": 2,
        "politeness_reason": "friendly tone",
        "completeness": 1,
        "completeness_reason": "missing timeframe detail",
    }
    output, error = validate_system_output(raw)
    assert error is None
    assert output.correctness == 2
    assert output.completeness == 1


def test_score_out_of_range_fails():
    raw = {
        "item_id": "T1",
        "correctness": 3,  # invalid: only 0/1/2 allowed
        "correctness_reason": "x",
        "politeness": 2,
        "politeness_reason": "x",
        "completeness": 2,
        "completeness_reason": "x",
    }
    output, error = validate_system_output(raw)
    assert output is None
    assert error is not None


def test_missing_reason_fails():
    raw = {
        "item_id": "T1",
        "correctness": 2,
        "correctness_reason": "",  # empty reason: not allowed
        "politeness": 2,
        "politeness_reason": "x",
        "completeness": 2,
        "completeness_reason": "x",
    }
    output, error = validate_system_output(raw)
    assert output is None
    assert error is not None


def test_extra_field_rejected():
    raw = {
        "item_id": "T1",
        "correctness": 2,
        "correctness_reason": "x",
        "politeness": 2,
        "politeness_reason": "x",
        "completeness": 2,
        "completeness_reason": "x",
        "unexpected_field": "should not be here",
    }
    output, error = validate_system_output(raw)
    assert output is None
    assert error is not None


def test_overall_pass_requires_all_axes_perfect():
    perfect = JudgeOutput(
        item_id="T1",
        correctness=2,
        correctness_reason="x",
        politeness=2,
        politeness_reason="x",
        completeness=2,
        completeness_reason="x",
    )
    assert ScoredRow.overall_pass(perfect) is True

    one_axis_short = perfect.model_copy(update={"completeness": 1})
    assert ScoredRow.overall_pass(one_axis_short) is False
