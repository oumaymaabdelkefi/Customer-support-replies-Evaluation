import json
from pathlib import Path

import pytest

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
    # Without GEMINI_API_KEY set (or the google-genai package installed),
    # running "llm_judge" should fail gracefully per-item (parse_error set)
    # rather than crashing the whole run.
    monkeypatch.setattr("harness.run.RESULTS_DIR", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    out_path = run("llm_judge", PILOT_ITEMS)

    lines = out_path.read_text().strip().splitlines()
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 20
    assert all(r["output"] is None for r in rows)
    assert all(r["parse_error"] for r in rows)  # every row has *some* error message


def test_unknown_system_raises():
    with pytest.raises(ValueError, match="Unknown system"):
        run("not_a_real_system", PILOT_ITEMS)
