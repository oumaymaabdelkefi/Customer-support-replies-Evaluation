"""
Exceptions a system can raise to tell the harness something about the
run as a whole, not just the current item.
"""

from __future__ import annotations


class QuotaExhausted(RuntimeError):
    """The system's provider quota is used up for a long period (e.g.
    Groq's tokens-per-day limit). Retrying won't help, so the harness
    stops calling the system and marks every remaining item as skipped
    instead of hammering the API with requests that are bound to fail."""
