"""Unified LLM pricing table and cost estimation.

This is the canonical price table for the Beacon SDK. If you update prices
here, also update the sister copy in backend/app/services/llm_client.py
which maintains its own table for backend-side cost estimation.

Prices are (input_cost_per_1M_tokens, output_cost_per_1M_tokens) in USD.

Keys are model name prefixes, ordered most-specific to least-specific.
The estimate_cost() function uses prefix matching so that dated model names
(e.g. "claude-sonnet-4-6-20250514") match their base prefix ("claude-sonnet-4").
"""

from __future__ import annotations

# Price table: (input_cost_per_1M, output_cost_per_1M)
# IMPORTANT: Order entries most-specific first within each prefix group.
# Prefix matching iterates in insertion order, so "gpt-4o-mini" must appear
# before "gpt-4o" to avoid a false prefix match.
PRICE_TABLE: dict[str, tuple[float, float]] = {
    # OpenAI — latest
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "o4-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    "o3": (2.00, 8.00),
    "o1-mini": (3.00, 12.00),
    "o1": (15.00, 60.00),
    # OpenAI — legacy
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    # Anthropic — latest
    "claude-opus-4": (5.00, 25.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (1.00, 5.00),
    # Anthropic — legacy
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (1.00, 5.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    # Google Gemini — latest
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    # Google Gemini — legacy
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model name and token counts.

    Uses prefix matching: the model string from the API response
    (e.g. "claude-sonnet-4-6-20250514") is matched against the
    shortest prefix in PRICE_TABLE (e.g. "claude-sonnet-4").

    Returns 0.0 for unrecognized models.
    """
    for prefix, (input_price, output_price) in PRICE_TABLE.items():
        if model.startswith(prefix):
            return (
                (input_tokens / 1_000_000) * input_price
                + (output_tokens / 1_000_000) * output_price
            )
    return 0.0
