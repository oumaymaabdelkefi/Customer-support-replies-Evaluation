"""
Assign every golden-set item to a dev or test split, and record it in
data/splits.json.

- dev:  used to iterate on prompts (judge_v2, system_v2, ...).
- test: used only to report final numbers. Don't tune prompts on it.

Rules:
- Items that share a customer message (e.g. P01/P02, the same question
  answered well and badly) always go to the same split. Otherwise a
  near-duplicate of a test item would be visible while tuning on dev.
- Stratified by theme, so dev and test both cover returns, shipping,
  damaged products and account security in similar proportions.
- Existing assignments are never changed. Re-run this script after
  adding items to the golden set: only the new items are assigned, so
  the test set you've already reported on stays fixed.

Usage:
    python scripts/split_golden_set.py
    python scripts/split_golden_set.py --test-fraction 0.5 --seed 496
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = REPO_ROOT / "data" / "golden_set.jsonl"
SPLITS_PATH = REPO_ROOT / "data" / "splits.json"


def group_key(item: dict) -> str:
    return " ".join(item["customer_message"].lower().split())


def assign_splits(
    items: list[dict], existing: dict[str, str], test_fraction: float, seed: int
) -> dict[str, str]:
    assignments = dict(existing)

    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[group_key(item)].append(item)

    # A new item that shares a message with an already-assigned item
    # joins that item's split.
    new_groups = []
    for members in groups.values():
        known = {assignments[m["item_id"]] for m in members if m["item_id"] in assignments}
        if len(known) > 1:
            ids = [m["item_id"] for m in members]
            raise ValueError(f"Items {ids} share a message but are already split across dev/test")
        if known:
            split = known.pop()
            for m in members:
                assignments.setdefault(m["item_id"], split)
        else:
            new_groups.append(members)

    # Greedy, per theme: give each new group to whichever split is
    # furthest below its target share of that theme.
    by_theme: dict[str, list[list[dict]]] = defaultdict(list)
    for members in new_groups:
        by_theme[members[0]["theme"]].append(members)

    rng = random.Random(seed)
    theme_of = {item["item_id"]: item["theme"] for item in items}
    for theme in sorted(by_theme):
        theme_groups = by_theme[theme]
        theme_groups.sort(key=lambda g: g[0]["item_id"])  # deterministic before shuffle
        rng.shuffle(theme_groups)
        counts = Counter(s for i, s in assignments.items() if theme_of.get(i) == theme)
        for members in theme_groups:
            total = counts["dev"] + counts["test"] + len(members)
            test_deficit = test_fraction * total - counts["test"]
            dev_deficit = (1 - test_fraction) * total - counts["dev"]
            split = "test" if test_deficit >= dev_deficit else "dev"
            for m in members:
                assignments[m["item_id"]] = split
            counts[split] += len(members)

    return assignments


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=Path, default=GOLDEN_SET)
    parser.add_argument("--out", type=Path, default=SPLITS_PATH)
    parser.add_argument("--test-fraction", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=496)
    args = parser.parse_args()

    with open(args.items, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]

    existing = {}
    if args.out.exists():
        existing = json.loads(args.out.read_text(encoding="utf-8"))["items"]
    unknown = set(existing) - {i["item_id"] for i in items}
    if unknown:
        print(f"warning: {len(unknown)} ids in {args.out.name} are no longer in the golden set: {sorted(unknown)}")

    assignments = assign_splits(items, existing, args.test_fraction, args.seed)
    ordered = {i["item_id"]: assignments[i["item_id"]] for i in items}
    ordered.update({k: v for k, v in existing.items() if k not in ordered})

    args.out.write_text(
        json.dumps(
            {"test_fraction": args.test_fraction, "seed": args.seed, "items": ordered},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    added = len(ordered) - len(existing)
    print(f"Wrote {args.out.relative_to(REPO_ROOT)}: {added} newly assigned, {len(existing)} kept")
    table = Counter((i["theme"], ordered[i["item_id"]]) for i in items)
    print(f"\n{'theme':<20} {'dev':>4} {'test':>5}")
    for theme in sorted({i["theme"] for i in items}):
        print(f"{theme:<20} {table[(theme, 'dev')]:>4} {table[(theme, 'test')]:>5}")
    totals = Counter(ordered[i["item_id"]] for i in items)
    print(f"{'total':<20} {totals['dev']:>4} {totals['test']:>5}")


if __name__ == "__main__":
    main()
