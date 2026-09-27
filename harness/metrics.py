"""
Aggregates a list of ScoredRow into a summary: per-axis score
distributions, overall pass rate, and parse-error count. Kept separate
from run.py so Role C or Role D can reuse it against results/*.jsonl
files directly (e.g. for the judge reliability report) without re-running
anything.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from harness.schema import ScoredRow


@dataclass
class Summary:
    total: int
    parse_errors: int
    passed: int
    failed: int
    correctness_dist: Counter = field(default_factory=Counter)
    politeness_dist: Counter = field(default_factory=Counter)
    completeness_dist: Counter = field(default_factory=Counter)

    @property
    def scored(self) -> int:
        return self.total - self.parse_errors

    @property
    def pass_rate(self) -> float | None:
        return self.passed / self.scored if self.scored else None

    def render(self) -> str:
        lines = []
        lines.append(f"Parsed OK:     {self.scored}/{self.total}")
        if self.parse_errors:
            lines.append(f"Parse errors:  {self.parse_errors}  (see parse_error field in results)")
        if self.scored:
            lines.append(f"Overall pass:  {self.passed}/{self.scored} ({self.pass_rate:.0%})")
            lines.append("")
            for axis, dist in [
                ("correctness", self.correctness_dist),
                ("politeness", self.politeness_dist),
                ("completeness", self.completeness_dist),
            ]:
                counts = " | ".join(f"{score}: {dist.get(score, 0)}" for score in (0, 1, 2))
                lines.append(f"{axis:<13} {counts}")
        return "\n".join(lines)


def summarize(rows: list[ScoredRow]) -> Summary:
    total = len(rows)
    parse_errors = sum(1 for r in rows if r.output is None)
    scored_rows = [r for r in rows if r.output is not None]
    passed = sum(1 for r in scored_rows if r.passed)

    s = Summary(
        total=total,
        parse_errors=parse_errors,
        passed=passed,
        failed=len(scored_rows) - passed,
    )
    for r in scored_rows:
        s.correctness_dist[r.output.correctness] += 1
        s.politeness_dist[r.output.politeness] += 1
        s.completeness_dist[r.output.completeness] += 1
    return s
