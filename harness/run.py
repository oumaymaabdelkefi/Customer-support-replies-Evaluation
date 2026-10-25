"""
The harness runner. Runs any registered "system" over a jsonl item set
and writes one row per item to results/. This is the single command the
brief requires: "Runs any system on the whole set with one command."

Usage:
    python -m harness.run --system always_perfect --items data/pilot_items.jsonl
    python -m harness.run --system keyword_baseline --items data/pilot_items.jsonl
    python -m harness.run --system llm_judge --items data/pilot_items.jsonl

Each run writes results/<system>_<timestamp>.jsonl and prints a summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from harness.errors import QuotaExhausted
from harness.metrics import summarize
from harness.schema import ItemInput, ScoredRow, validate_system_output
from harness.systems.baselines import SYSTEMS as BASELINE_SYSTEMS

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"

# Fields a system is allowed to see. Pilot items carry extra internal-only
# fields (challenge_type, author_note, source, ...) that must never reach
# a system under test -- ROLE_C_HANDOFF.md is explicit about this.
INPUT_FIELDS = {"item_id", "customer_message", "policy_excerpt", "candidate_reply"}


def load_items(path: Path) -> list[ItemInput]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            trimmed = {k: raw[k] for k in INPUT_FIELDS if k in raw}
            missing = INPUT_FIELDS - trimmed.keys()
            if missing:
                raise ValueError(f"{path}:{line_no} missing fields {missing}")
            items.append(ItemInput.model_validate(trimmed))
    return items


def resolve_system(name: str):
    if name in BASELINE_SYSTEMS:
        return BASELINE_SYSTEMS[name]
    if name == "llm_judge":
        from harness.systems.judge_stub import llm_judge

        return llm_judge
    raise ValueError(
        f"Unknown system '{name}'. Available: {list(BASELINE_SYSTEMS) + ['llm_judge']}"
    )


def run_system_on_item(system_fn, item: ItemInput) -> ScoredRow:
    try:
        raw = system_fn(item)
    except QuotaExhausted:
        raise  # run() handles this: it ends the API calls for the whole run
    except NotImplementedError as e:
        return ScoredRow(item_id=item.item_id, input=item, parse_error=str(e))
    except Exception:  # noqa: BLE001 -- a broken system must not crash the run
        return ScoredRow(
            item_id=item.item_id,
            input=item,
            parse_error=f"system raised an exception:\n{traceback.format_exc()}",
        )

    meta = raw.pop("_meta", None) if isinstance(raw, dict) else None

    output, error = validate_system_output(raw)
    if error is not None:
        return ScoredRow(
            item_id=item.item_id,
            input=item,
            parse_error=error,
            raw_response=json.dumps(raw, ensure_ascii=False),
            meta=meta,
        )

    return ScoredRow(
        item_id=item.item_id,
        input=item,
        output=output,
        score=ScoredRow.total_score(output),
        passed=ScoredRow.overall_pass(output),
        meta=meta,
    )


def run(system_name: str, items_path: Path) -> Path:
    items = load_items(items_path)
    system_fn = resolve_system(system_name)

    rows: list[ScoredRow] = []
    quota_error: str | None = None
    for item in items:
        if quota_error is None:
            try:
                rows.append(run_system_on_item(system_fn, item))
                continue
            except QuotaExhausted as e:
                quota_error = str(e)
                print(f"\n{quota_error}\nSkipping the remaining items.", file=sys.stderr)
        # Still one row per item, so a partial run is visibly partial.
        rows.append(
            ScoredRow(
                item_id=item.item_id,
                input=item,
                parse_error=f"skipped: quota exhausted earlier in this run ({quota_error})",
            )
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{system_name}_{int(time.time())}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(row.model_dump_json() + "\n")

    summary = summarize(rows)
    try:
        wrote = out_path.relative_to(REPO_ROOT)
    except ValueError:
        wrote = out_path
    print(f"\nSystem: {system_name}")
    print(f"Items:  {len(rows)}")
    print(f"Wrote:  {wrote}\n")
    print(summary.render())

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Run a system over an item set.")
    parser.add_argument(
        "--system",
        required=True,
        help="Registered system name (always_perfect, keyword_baseline, llm_judge)",
    )
    parser.add_argument(
        "--items",
        required=True,
        type=Path,
        help="Path to a jsonl item file (e.g. data/pilot_items.jsonl)",
    )
    args = parser.parse_args()

    if not args.items.exists():
        print(f"error: {args.items} not found", file=sys.stderr)
        sys.exit(1)

    run(args.system, args.items)


if __name__ == "__main__":
    main()
