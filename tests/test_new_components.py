import csv
import importlib.util
import json
from pathlib import Path

import pytest

from harness.run import resolve_system
from harness.schema import ItemInput
from harness.systems import judge_stub, reply_system

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ITEM = ItemInput(item_id="X1", customer_message="where is my refund", policy_excerpt="[RET-4] ...",
                 candidate_reply="original reply")


# ---------------- versioned systems ----------------


def test_resolve_versioned_systems():
    assert resolve_system("llm_judge_v2").__name__ == "llm_judge_v2"
    assert resolve_system("reply_v1").__name__ == "reply_v1"
    with pytest.raises(ValueError):
        resolve_system("reply_v99")
    with pytest.raises(ValueError, match="Unknown system"):
        resolve_system("llm_judge_vX")


def test_judge_versions_use_different_prompts():
    v1 = judge_stub._build_prompt(ITEM, 1)
    v2 = judge_stub._build_prompt(ITEM, 2)
    assert v1 != v2
    assert "Omissions are not correctness errors" in v2


def test_reply_system_judges_its_own_reply(monkeypatch):
    seen = {}

    def fake_chat(prompt, label, **kw):
        seen["prompt"] = prompt
        return "  Your refund arrives 5-7 business days after inspection.  ", {
            "cost_usd": 0.0001, "latency_s": 0.5, "prompt_tokens": 100, "completion_tokens": 50}

    def fake_judge(item):
        seen["graded_reply"] = item.candidate_reply
        return {"item_id": item.item_id, "correctness": 2, "correctness_reason": "x", "politeness": 2,
                "politeness_reason": "x", "completeness": 1, "completeness_reason": "x",
                "_meta": {"cost_usd": 0.0005, "latency_s": 1.0, "prompt_tokens": 1500, "completion_tokens": 300}}

    monkeypatch.setattr(reply_system.judge_stub, "chat_groq", fake_chat)
    monkeypatch.setattr(reply_system.judge_stub, "llm_judge", fake_judge)
    out = reply_system.make_reply_system(1)(ITEM)

    assert "where is my refund" in seen["prompt"]
    assert seen["graded_reply"] == "Your refund arrives 5-7 business days after inspection."
    meta = out["_meta"]
    assert meta["generated_reply"] == seen["graded_reply"]
    assert meta["cost_usd"] == pytest.approx(0.0006)
    assert meta["system_cost_usd"] == pytest.approx(0.0001)
    assert out["completeness"] == 1


# ---------------- gold labels ----------------


def test_gold_labels_only_keep_agreed_scores():
    load_script("build_gold_labels").main()
    gold = {r["item_id"]: r for r in csv.DictReader(open(REPO_ROOT / "data" / "gold_labels.csv", encoding="utf-8"))}
    sheets = {}
    for n in (1, 2):
        for name in (f"labelling_sheet_labeler{n}_completed.csv", f"labelling_sheet_labeler{n}_stage2.csv"):
            for r in csv.DictReader(open(REPO_ROOT / "data" / name, encoding="utf-8-sig")):
                sheets.setdefault(n, {})[r["item_id"]] = r
    for item_id, row in gold.items():
        for axis in ("correctness", "politeness", "completeness"):
            col = f"{axis}_score_0_1_2"
            a, b = sheets[1][item_id][col].strip(), sheets[2][item_id][col].strip()
            assert row[col] == (a if a == b else "")


# ---------------- Excel import ----------------


def test_import_reads_filled_workbook_and_rejects_bad_scores(tmp_path):
    make = load_script("make_labelling_xlsx")
    importer = load_script("import_labels")
    wb = make.build(1)
    ws = wb["Labels"]
    ws["F2"], ws["G2"], ws["H2"], ws["I2"] = 2, 1, 0, "note"
    path = tmp_path / "filled.xlsx"
    wb.save(path)
    labels = importer.read_workbook(path)
    first = ws["A2"].value
    assert labels[first]["correctness"] == "2" and labels[first]["completeness"] == "0"
    assert labels[first]["notes"] == "note"

    ws["F3"] = 7
    wb.save(path)
    with pytest.raises(ValueError, match="not 0/1/2/NA"):
        importer.read_workbook(path)


# ---------------- adversarial set + cost model ----------------


def test_adversarial_set_has_expected_scores():
    load_script("make_adversarial_set").main()
    items = [json.loads(l) for l in open(REPO_ROOT / "data" / "bias" / "adversarial.jsonl", encoding="utf-8")]
    expected = list(csv.DictReader(open(REPO_ROOT / "data" / "bias" / "adversarial_expected.csv", encoding="utf-8")))
    assert [i["item_id"] for i in items] == [e["item_id"] for e in expected]
    assert all(set(i) >= {"item_id", "customer_message", "policy_excerpt", "candidate_reply"} for i in items)


def test_cost_model_summary():
    cost = load_script("cost_model")
    s = cost.summarize([{"cost_usd": 0.001, "latency_s": 1.0, "prompt_tokens": 100, "completion_tokens": 50},
                        {"cost_usd": 0.003, "latency_s": 3.0, "prompt_tokens": 300, "completion_tokens": 50}])
    assert s["cost"] == pytest.approx(0.002)
    assert s["tokens"] == pytest.approx(250)
    assert s["p50"] == pytest.approx(2.0)
