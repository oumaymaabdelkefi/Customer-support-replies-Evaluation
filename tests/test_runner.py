import json
from pathlib import Path

import pytest

from harness.errors import QuotaExhausted
from harness.run import load_items, run

REPO_ROOT = Path(__file__).resolve().parent.parent
PILOT_ITEMS = REPO_ROOT / "data" / "pilot_items.jsonl"


def test_load_items_reads_pilot_set():
    items = load_items(PILOT_ITEMS)
    assert len(items) == 20
    assert items[0].item_id == "P01"
    # internal-only fields must never leak into ItemInput
    assert not hasattr(items[0], "challenge_type")
    assert not hasattr(items[0], "author_note")


def test_load_items_missing_field_raises(tmp_path):
    bad_file = tmp_path / "bad.jsonl"
    bad_file.write_text(
        json.dumps({"item_id": "X1", "customer_message": "hi"}) + "\n"
    )
    with pytest.raises(ValueError, match="missing fields"):
        load_items(bad_file)


def test_run_always_perfect_on_pilot_set(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    out_path = run("always_perfect", PILOT_ITEMS)

    lines = out_path.read_text().strip().splitlines()
    assert len(lines) == 20

    rows = [json.loads(line) for line in lines]
    assert all(r["passed"] is True for r in rows)
    assert all(r["parse_error"] is None for r in rows)


def test_run_llm_judge_without_api_key_fails_gracefully_not_crash(tmp_path, monkeypatch):
    # Without GROQ_API_KEY set (or the openai package installed), running
    # "llm_judge" should fail gracefully per-item (parse_error set) rather
    # than crashing the whole run.
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    out_path = run("llm_judge", PILOT_ITEMS)

    lines = out_path.read_text().strip().splitlines()
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 20
    assert all(r["output"] is None for r in rows)
    assert all(r["parse_error"] for r in rows)  # every row has *some* error message


def test_unknown_system_raises():
    with pytest.raises(ValueError, match="Unknown system"):
        run("not_a_real_system", PILOT_ITEMS)


def test_rows_carry_total_score(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    out_path = run("always_perfect", PILOT_ITEMS)
    rows = [json.loads(line) for line in out_path.read_text().strip().splitlines()]
    assert all(r["score"] == 6 for r in rows)


def _fake_judge(item):
    return {
        "item_id": item.item_id,
        "correctness": 2,
        "correctness_reason": "x",
        "politeness": 1,
        "politeness_reason": "x",
        "completeness": 0,
        "completeness_reason": "x",
        "_meta": {"latency_s": 0.5, "prompt_tokens": 1000, "completion_tokens": 100, "cost_usd": 0.001},
    }


def test_system_meta_is_moved_out_of_output(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    monkeypatch.setattr("harness.run.resolve_system", lambda name: _fake_judge)
    out_path = run("fake", PILOT_ITEMS)
    rows = [json.loads(line) for line in out_path.read_text().strip().splitlines()]
    assert all(r["parse_error"] is None for r in rows)  # _meta didn't break extra="forbid"
    assert rows[0]["meta"]["cost_usd"] == 0.001
    assert rows[0]["score"] == 3
    assert rows[0]["passed"] is False


def test_quota_exhausted_skips_remaining_items(tmp_path, monkeypatch):
    calls = []

    def judge(item):
        calls.append(item.item_id)
        if len(calls) == 3:
            raise QuotaExhausted("daily limit")
        return _fake_judge(item)

    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    monkeypatch.setattr("harness.run.resolve_system", lambda name: judge)
    out_path = run("fake", PILOT_ITEMS)
    rows = [json.loads(line) for line in out_path.read_text().strip().splitlines()]

    assert len(calls) == 3  # no calls after the quota error
    assert len(rows) == 20  # still one row per item
    assert [r["output"] is not None for r in rows[:2]] == [True, True]
    assert all(r["parse_error"].startswith("skipped: quota exhausted") for r in rows[2:])


def test_resume_reruns_only_failed_and_skipped_items(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)

    # Day 1: quota runs out on the 3rd item.
    day1_calls = []

    def day1_judge(item):
        day1_calls.append(item.item_id)
        if len(day1_calls) == 3:
            raise QuotaExhausted("daily limit")
        return _fake_judge(item)

    monkeypatch.setattr("harness.run.resolve_system", lambda name: day1_judge)
    first = run("fake", PILOT_ITEMS)

    # Day 2: resume -- only the 18 unscored items should be sent again.
    day2_calls = []

    def day2_judge(item):
        day2_calls.append(item.item_id)
        return _fake_judge(item)

    monkeypatch.setattr("harness.run.resolve_system", lambda name: day2_judge)
    monkeypatch.setattr("harness.run.time.time", lambda: 9999999999)  # distinct filename
    second = run("fake", PILOT_ITEMS, resume_from=first)

    rows = [json.loads(line) for line in second.read_text().strip().splitlines()]
    assert len(day2_calls) == 18
    assert "P01" not in day2_calls and "P02" not in day2_calls
    assert len(rows) == 20
    assert all(r["output"] is not None for r in rows)


def test_split_filters_items(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    splits = tmp_path / "splits.json"
    assignments = {f"P{n:02d}": ("dev" if n <= 5 else "test") for n in range(1, 21)}
    splits.write_text(json.dumps({"items": assignments}))
    monkeypatch.setattr("harness.run.SPLITS_PATH", splits)

    out_path = run("always_perfect", PILOT_ITEMS, split="dev")
    rows = [json.loads(line) for line in out_path.read_text().strip().splitlines()]
    assert [r["item_id"] for r in rows] == ["P01", "P02", "P03", "P04", "P05"]
    assert "_dev_" in out_path.name


def test_split_refuses_unassigned_items(tmp_path, monkeypatch):
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"items": {"P01": "dev"}}))
    monkeypatch.setattr("harness.run.SPLITS_PATH", splits)
    with pytest.raises(ValueError, match="no split"):
        run("always_perfect", PILOT_ITEMS, split="dev")


def test_committed_splits_cover_golden_set_and_keep_pairs_together():
    from harness.run import SPLITS_PATH

    assignments = json.loads(SPLITS_PATH.read_text())["items"]
    golden = [json.loads(l) for l in (REPO_ROOT / "data" / "golden_set.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert {g["item_id"] for g in golden} <= set(assignments)
    by_message = {}
    for g in golden:
        key = " ".join(g["customer_message"].lower().split())
        by_message.setdefault(key, set()).add(assignments[g["item_id"]])
    assert all(len(splits) == 1 for splits in by_message.values())
