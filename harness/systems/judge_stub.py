"""
Role C's LLM judge, wired into the harness, using Groq's API to serve
openai/gpt-oss-120b (an open-weight model, free tier available, no credit
card required).

Assumption: "openai/gpt-oss-120b" is the exact model id Groq uses for this
model (https://console.groq.com/docs/model/openai/gpt-oss-120b). If you
actually meant a different host for this model (OpenRouter, Together,
Fireworks, etc.), the code below only needs BASE_URL, the env var name,
and the sign-up URL changed -- everything else (prompt building, JSON
extraction, retry/backoff) is provider-agnostic since Groq speaks the
OpenAI-compatible chat completions format.

Setup:
    pip install openai --break-system-packages
    Get a free API key at https://console.groq.com/keys
    export GROQ_API_KEY=gsk_...      (never commit this)

Rate limits: Groq's free tier is generous but still finite and can return
429s under bursty load, especially on a run of 70+ items back to back.
This module retries with backoff on 429/5xx, printing progress so a long
wait doesn't look like a frozen terminal, and paces requests slightly to
avoid tripping the limit in the first place. The openai SDK's own built-in
retry logic is disabled (max_retries=0) because it retries silently
*before* our code sees the exception -- that silent sleep is what looked
like a hang and got Ctrl+C'd in testing. A 429 for the *daily* token
quota (TPD/RPD) is not retried at all: it won't clear for hours, so the
judge raises QuotaExhausted and the harness skips the remaining items.

Structured output: the request passes a strict JSON schema
(response_format=json_schema), so the model is constrained to the
JudgeOutput shape at decode time rather than us parsing free text.

Cost and latency: every call returns a "_meta" dict (tokens, latency,
USD cost) alongside the scores. The harness moves it into the row's
`meta` field before validating the scores.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from harness.errors import QuotaExhausted
from harness.schema import ItemInput

PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "judge_v1.txt"
MODEL_NAME = "openai/gpt-oss-120b"
BASE_URL = "https://api.groq.com/openai/v1"

MAX_RETRIES = 4
DEFAULT_RETRY_DELAY_SECONDS = 20.0  # fallback if the API doesn't say how long to wait
MIN_SECONDS_BETWEEN_CALLS = 1.5  # light pacing so a 70+ item run doesn't burst into a 429

# Groq on-demand price for openai/gpt-oss-120b, USD per 1M tokens.
# Check https://groq.com/pricing before quoting cost numbers in the report.
PRICE_PER_M_INPUT_TOKENS = 0.15
PRICE_PER_M_OUTPUT_TOKENS = 0.60

_SCORE = {"type": "integer", "enum": [0, 1, 2]}
_REASON = {"type": "string"}
JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "judge_output",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "correctness": _SCORE,
                "correctness_reason": _REASON,
                "politeness": _SCORE,
                "politeness_reason": _REASON,
                "completeness": _SCORE,
                "completeness_reason": _REASON,
            },
            "required": [
                "item_id",
                "correctness",
                "correctness_reason",
                "politeness",
                "politeness_reason",
                "completeness",
                "completeness_reason",
            ],
            "additionalProperties": False,
        },
    },
}

_PROMPT_TEMPLATE: str | None = None
_last_call_time: float = 0.0  # module-level, shared across calls in one run


def _load_template() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Judge prompt not found at {PROMPT_PATH}. "
                "Make sure prompts/judge_v1.txt is in the repo."
            )
        _PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")
    return _PROMPT_TEMPLATE


def _build_prompt(item: ItemInput) -> str:
    return _load_template().format(
        item_id=item.item_id,
        customer_message=item.customer_message,
        policy_excerpt=item.policy_excerpt,
        candidate_reply=item.candidate_reply,
    )


def _extract_json(raw_text: str) -> dict:
    """Models sometimes wrap JSON in markdown fences despite instructions
    not to. Strip those before parsing, but don't silently fix anything
    else -- malformed output should still surface as a parse_error in the
    harness, not be papered over here."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)  # let json.JSONDecodeError propagate on bad output


def _throttle():
    """Block until at least MIN_SECONDS_BETWEEN_CALLS has passed since the
    last call this process made -- cheap insurance against tripping the
    rate limit on a long batch."""
    global _last_call_time
    elapsed = time.monotonic() - _last_call_time
    wait = MIN_SECONDS_BETWEEN_CALLS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.monotonic()


def _extract_retry_delay(error) -> float:
    """Groq's 429 responses (OpenAI-compatible) often include a suggested
    wait in the message (e.g. 'try again in 12.4s'). Parse it if present;
    fall back to a fixed default otherwise."""
    text = str(error)
    match = re.search(r"try again in ([\d.]+)s", text, re.IGNORECASE)
    if not match:
        match = re.search(r"retry.*?([\d.]+)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0  # small safety margin
    return DEFAULT_RETRY_DELAY_SECONDS


def _is_daily_quota_error(error) -> bool:
    """Groq names the exhausted limit in the 429 message: 'tokens per day
    (TPD)' or 'requests per day (RPD)' won't clear within a retry window,
    unlike the per-minute limits."""
    text = str(error)
    return "(TPD)" in text or "(RPD)" in text or "per day" in text.lower()


def _cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens * PRICE_PER_M_INPUT_TOKENS
        + completion_tokens * PRICE_PER_M_OUTPUT_TOKENS
    ) / 1_000_000


def llm_judge(item: ItemInput) -> dict:
    try:
        import openai
    except ImportError as e:
        raise RuntimeError(
            "The 'openai' package isn't installed. Run: "
            "pip install openai --break-system-packages"
        ) from e

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at "
            "https://console.groq.com/keys and export it -- never "
            "hard-code it or commit it."
        )

    # max_retries=0: the SDK's own built-in retry logic sleeps *silently*
    # before our except block ever runs, which on a long 429 backoff looks
    # exactly like a frozen terminal. Disabling it means every retry goes
    # through our own loop below, which prints what it's doing.
    client = openai.OpenAI(api_key=api_key, base_url=BASE_URL, max_retries=0)
    prompt = _build_prompt(item)

    last_error: Exception | None = None
    response = None
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        started = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,  # deterministic-as-possible grading, not creative writing
                max_tokens=2048,  # generous headroom in case the model reasons before answering
                response_format=JUDGE_RESPONSE_FORMAT,
            )
            latency_s = time.monotonic() - started
            break  # success -- fall through to JSON parsing below
        except (openai.APIStatusError, openai.APIConnectionError) as e:
            last_error = e
            status = getattr(e, "status_code", None)
            if status == 429 and _is_daily_quota_error(e):
                raise QuotaExhausted(f"Groq daily quota exhausted: {e}") from e
            is_retryable = status in (429, 500, 502, 503, 504) or status is None
            if not is_retryable or attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Groq API call failed after {attempt} attempt(s): {e}"
                ) from e
            delay = _extract_retry_delay(e)
            print(
                f"  [{item.item_id}] Groq rate-limited (attempt {attempt}/{MAX_RETRIES}), "
                f"waiting {delay:.0f}s before retrying..."
            )
            time.sleep(delay)
    else:  # pragma: no cover -- defensive, loop always breaks or raises above
        raise RuntimeError(f"Groq API call failed: {last_error}")

    raw_text = response.choices[0].message.content
    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    meta = {
        "model": MODEL_NAME,
        "latency_s": round(latency_s, 3),
        "attempts": attempt,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": _cost_usd(prompt_tokens, completion_tokens),
    }

    try:
        parsed = _extract_json(raw_text)
    except json.JSONDecodeError as e:
        # Surface the actual raw text (truncated) in the error so a failed
        # run's parse_error is diagnosable without re-running by hand.
        preview = (raw_text or "")[:800]
        raise RuntimeError(
            f"Judge response was not valid JSON ({e}). Raw response "
            f"(first 800 chars): {preview!r}"
        ) from e
    if isinstance(parsed, dict):
        parsed["_meta"] = meta
    return parsed