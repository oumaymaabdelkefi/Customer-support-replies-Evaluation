import importlib.util
import json
from pathlib import Path

import pytest

from harness.errors import QuotaExhausted

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


position_bias = load_script("position_bias")
verbosity_bias = load_script("verbosity_bias")


def golden_items():
    with open(REPO_ROOT / "data" / "golden_set.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------- position bias ----------------


def test_pairs_share_message_and_policy():
    pairs = position_bias.build_pairs(golden_items())
    assert "P01|P02" in {p["pair_id"] for p in pairs}
    assert all(len(p["items"]) == 2 for p in pairs)


def test_always_first_judge_is_flagged_as_position_biased(monkeypatch):
    def always_a(prompt, response_format, label):
        return {"winner": "A", "reason": "first", "_meta": {"cost_usd": 0.0, "latency_s": 0.1}}

    monkeypatch.setattr(position_bias.judge_stub, "call_groq", always_a)
    template = position_bias.PROMPT_PATH.read_text(encoding="utf-8")
    pair = position_bias.build_pairs(golden_items())[0]
    rows = [position_bias.judge_once(template, pair, order) for order in ("AB", "BA")]

    # Same position won both times -> a different *reply* won -> flipped.
    assert rows[0]["winner_item"] != rows[1]["winner_item"]
    report = position_bias.render_report(rows, REPO_ROOT / "results" / "x.jsonl")
    assert "| Verdict changed after swap | 1/1 (100%) |" in report


def test_consistent_judge_has_no_flips(monkeypatch):
    first_item = {}

    def prefers_one_reply(prompt, response_format, label):
        # Always pick whichever position holds the pair's first item.
        pair_first_reply = first_item["reply"]
        a_text = prompt.split("reply_A:\n", 1)[1].split("\n\nreply_B:", 1)[0]
        return {"winner": "A" if a_text == pair_first_reply else "B", "reason": "x"}

    monkeypatch.setattr(position_bias.judge_stub, "call_groq", prefers_one_reply)
    template = position_bias.PROMPT_PATH.read_text(encoding="utf-8")
    pair = position_bias.build_pairs(golden_items())[0]
    first_item["reply"] = next(iter(pair["items"].values()))
    rows = [position_bias.judge_once(template, pair, order) for order in ("AB", "BA")]

    assert rows[0]["winner_item"] == rows[1]["winner_item"]
    report = position_bias.render_report(rows, REPO_ROOT / "results" / "x.jsonl")
    assert "| Verdict changed after swap | 0/1 (0%) |" in report


def test_quota_exhausted_propagates(monkeypatch):
    def quota(prompt, response_format, label):
        raise QuotaExhausted("daily")

    monkeypatch.setattr(position_bias.judge_stub, "call_groq", quota)
    template = position_bias.PROMPT_PATH.read_text(encoding="utf-8")
    pair = position_bias.build_pairs(golden_items())[0]
    with pytest.raises(QuotaExhausted):
        position_bias.judge_once(template, pair, "AB")


# ---------------- verbosity bias ----------------


def test_padding_only_adds_filler():
    padded = verbosity_bias.pad_reply("Refunds take 5-7 business days.")
    assert "Refunds take 5-7 business days." in padded
    assert len(padded) > 300
    # Filler must not add policy facts or numbers that could change correctness.
    filler = padded.replace("Refunds take 5-7 business days.", "")
    assert not any(ch.isdigit() for ch in filler)


def _write_results(path, scores):
    with open(path, "w", encoding="utf-8") as f:
        for item_id, (c, p, m) in scores.items():
            out = {"correctness": c, "politeness": p, "completeness": m}
            f.write(json.dumps({"item_id": item_id, "output": out}) + "\n")


def test_report_counts_grade_increases(tmp_path):
    original = tmp_path / "orig.jsonl"
    padded = tmp_path / "pad.jsonl"
    _write_results(original, {"A": (1, 2, 1), "B": (2, 2, 2)})
    _write_results(padded, {"A~pad": (1, 2, 2), "B~pad": (2, 2, 2)})

    out = tmp_path / "report.md"
    args = type("Args", (), {"original": original, "padded": padded, "out": out})
    verbosity_bias.report(args)
    text = out.read_text(encoding="utf-8")
    assert "| completeness | 1/2 (50%) | 1/2 (50%) | 0/2 (0%) |" in text
    assert "| A | 1 → 1 | 2 → 2 | 1 → 2 | +1 |" in text
