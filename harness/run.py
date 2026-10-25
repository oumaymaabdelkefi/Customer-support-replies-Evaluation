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
SPLITS_PATH = REPO_ROOT / "data" / "splits.json"

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


def filter_split(items: list[ItemInput], split: str, splits_path: Path | None = None) -> list[ItemInput]:
    """Keep only the items assigned to `split` ("dev" or "test") in
    data/splits.json (written by scripts/split_golden_set.py)."""
    splits_path = splits_path or SPLITS_PATH
    if not splits_path.exists():
        raise ValueError(f"{splits_path} not found -- run scripts/split_golden_set.py first")
    assignments = json.loads(splits_path.read_text(encoding="utf-8"))["items"]
    missing = [i.item_id for i in items if i.item_id not in assignments]
    if missing:
        raise ValueError(
            f"{len(missing)} items have no split (e.g. {missing[:5]}) -- "
            "re-run scripts/split_golden_set.py to assign new items"
        )
    return [i for i in items if assignments[i.item_id] == split]


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


def load_reusable_rows(path: Path) -> dict[str, ScoredRow]:
    """Rows from an earlier run that scored successfully, keyed by item_id.
    Used by --resume so a run cut short by a free-tier quota can be
    finished later without paying (in quota) for items already scored."""
    reusable = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = ScoredRow.model_validate_json(line)
                if row.output is not None:
                    reusable[row.item_id] = row
    return reusable


def run(
    system_name: str,
    items_path: Path,
    resume_from: Path | None = None,
    split: str | None = None,
) -> Path:
    items = load_items(items_path)
    if split:
        items = filter_split(items, split)
    system_fn = resolve_system(system_name)
    reusable = load_reusable_rows(resume_from) if resume_from else {}

    rows: list[ScoredRow] = []
    reused = 0
    quota_error: str | None = None
    for item in items:
        previous = reusable.get(item.item_id)
        # Only reuse a row if the item text is unchanged since that run.
        if previous is not None and previous.input == item:
            rows.append(previous)
            reused += 1
            continue
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
    tag = f"{system_name}_{split}" if split else system_name
    out_path = RESULTS_DIR / f"{tag}_{int(time.time())}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(row.model_dump_json() + "\n")

    summary = summarize(rows)
    try:
        wrote = out_path.relative_to(REPO_ROOT)
    except ValueError:
        wrote = out_path
    print(f"\nSystem: {system_name}")
    print(f"Items:  {len(rows)}" + (f" ({split} split)" if split else ""))
    if resume_from:
        print(f"Reused: {reused} already-scored rows from {resume_from}")
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
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Earlier results jsonl: reuse its successfully scored rows and "
        "only re-run items that failed or were skipped (e.g. after hitting "
        "a free-tier daily quota)",
    )
    parser.add_argument(
        "--split",
        choices=["dev", "test"],
        default=None,
        help="Only run items in this split (see data/splits.json). Tune "
        "prompts on dev; use test only to report final results.",
    )
    args = parser.parse_args()

    for path in (args.items, args.resume):
        if path is not None and not path.exists():
            print(f"error: {path} not found", file=sys.stderr)
            sys.exit(1)

    run(args.system, args.items, resume_from=args.resume, split=args.split)


if __name__ == "__main__":
    main()
