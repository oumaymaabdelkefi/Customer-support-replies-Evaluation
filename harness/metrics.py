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
    # Only populated for systems that report meta (e.g. the LLM judge).
    calls_with_meta: int = 0
    total_cost_usd: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    latencies_s: list[float] = field(default_factory=list)

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
        if self.calls_with_meta:
            n = self.calls_with_meta
            lines.append("")
            lines.append(
                f"Tokens:        {self.total_prompt_tokens} in / "
                f"{self.total_completion_tokens} out over {n} calls"
            )
            lines.append(
                f"Cost:          ${self.total_cost_usd:.4f} total, "
                f"${self.total_cost_usd / n:.6f}/item, "
                f"${self.total_cost_usd / n * 1000:.2f} per 1k items"
            )
            lat = sorted(self.latencies_s)
            if lat:
                p50 = lat[len(lat) // 2]
                p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))]
                lines.append(f"Latency:       p50 {p50:.2f}s, p95 {p95:.2f}s, max {lat[-1]:.2f}s")
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
    for r in rows:
        if r.meta:
            s.calls_with_meta += 1
            s.total_cost_usd += r.meta.get("cost_usd", 0.0)
            s.total_prompt_tokens += r.meta.get("prompt_tokens", 0)
            s.total_completion_tokens += r.meta.get("completion_tokens", 0)
            if "latency_s" in r.meta:
                s.latencies_s.append(r.meta["latency_s"])
    for r in scored_rows:
        s.correctness_dist[r.output.correctness] += 1
        s.politeness_dist[r.output.politeness] += 1
        s.completeness_dist[r.output.completeness] += 1
    return s
