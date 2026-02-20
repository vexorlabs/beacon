"""Shared LLM API client for OpenAI, Anthropic, and Google.

Extracted from replay_service so both replay and playground can reuse
the same calling logic and price table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

# Price table: (input_cost_per_1M, output_cost_per_1M)
# NOTE: The SDK maintains a sister price table in sdk/beacon_sdk/pricing.py
# with prefix-matching semantics. When updating prices here, also update there.
PRICE_TABLE: dict[str, tuple[float, float]] = {
    # OpenAI — latest
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o3": (2.00, 8.00),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    # OpenAI — legacy
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    # Anthropic — latest
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    # Anthropic — legacy
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (1.00, 5.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    # Google Gemini — latest
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    # Google Gemini — legacy
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}

# Model → provider mapping
MODEL_PROVIDER: dict[str, str] = {
    # OpenAI
    "gpt-4.1": "openai",
    "gpt-4.1-mini": "openai",
    "gpt-4.1-nano": "openai",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "o3": "openai",
    "o3-mini": "openai",
    "o4-mini": "openai",
    "o1": "openai",
    "o1-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    # Anthropic
    "claude-opus-4-6": "anthropic",
    "claude-sonnet-4-6": "anthropic",
    "claude-haiku-4-5-20251001": "anthropic",
    "claude-sonnet-4-5-20250929": "anthropic",
    "claude-sonnet-4-20250514": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-5-haiku-20241022": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    # Google Gemini
    "gemini-2.5-pro": "google",
    "gemini-2.5-flash": "google",
    "gemini-2.0-flash-lite": "google",
    "gemini-2.0-flash": "google",
    "gemini-1.5-pro": "google",
    "gemini-1.5-flash": "google",
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD using per-million-token pricing."""
    prices = PRICE_TABLE.get(model)
    if prices is None:
        return 0.0
    input_cost, output_cost = prices
    return (input_tokens / 1_000_000) * input_cost + (output_tokens / 1_000_000) * output_cost


def provider_for_model(model: str) -> str:
    """Return 'openai', 'anthropic', or 'google' based on the model name."""
    if model in MODEL_PROVIDER:
        return MODEL_PROVIDER[model]
    if model.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gemini"):
        return "google"
    raise ValueError(f"Unknown model: {model}")


async def call_openai(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 1.0,
    max_tokens: int | None = None,
) -> tuple[str, int, int]:
    """Call OpenAI chat completions API.

    Returns (completion, input_tokens, output_tokens).
    """
    if not api_key:
        raise ValueError("OpenAI API key is not configured")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            error_body = response.text[:200]  # Truncate to avoid leaking sensitive info
            raise ValueError(
                f"OpenAI API error {response.status_code}: {error_body}"
            )
        data = response.json()

    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        raise ValueError("OpenAI returned an empty or invalid response (no choices)")
    completion_text: str = choices[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    input_tokens: int = usage.get("prompt_tokens", 0)
    output_tokens: int = usage.get("completion_tokens", 0)
    return completion_text, input_tokens, output_tokens


async def call_anthropic(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 1.0,
    max_tokens: int | None = None,
) -> tuple[str, int, int]:
    """Call Anthropic messages API.

    Returns (completion, input_tokens, output_tokens).
    """
    if not api_key:
        raise ValueError("Anthropic API key is not configured")

    # Extract system message from the messages list
    system_text: str | None = None
    anthropic_messages: list[dict[str, str]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_text = msg.get("content", "")
        else:
            anthropic_messages.append(msg)

    payload: dict[str, Any] = {
        "model": model,
        "messages": anthropic_messages,
        "temperature": temperature,
        "max_tokens": max_tokens or 4096,
    }
    if system_text is not None:
        payload["system"] = system_text

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            error_body = response.text[:200]  # Truncate to avoid leaking sensitive info
            raise ValueError(
                f"Anthropic API error {response.status_code}: {error_body}"
            )
        data = response.json()

    content_blocks: list[dict[str, Any]] = data.get("content", [])
    completion_text = ""
    for block in content_blocks:
        if block.get("type") == "text":
            completion_text += block.get("text", "")

    usage = data.get("usage", {})
    input_tokens: int = usage.get("input_tokens", 0)
    output_tokens: int = usage.get("output_tokens", 0)
    return completion_text, input_tokens, output_tokens


async def call_google(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 1.0,
    max_tokens: int | None = None,
) -> tuple[str, int, int]:
    """Call Google Gemini generateContent API.

    Returns (completion, input_tokens, output_tokens).
    """
    if not api_key:
        raise ValueError("Google API key is not configured")

    # Convert OpenAI-style messages to Gemini contents format
    system_instruction: str | None = None
    contents: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_instruction = msg.get("content", "")
        else:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}],
            })

    generation_config: dict[str, Any] = {"temperature": temperature}
    if max_tokens is not None:
        generation_config["maxOutputTokens"] = max_tokens

    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": generation_config,
    }
    if system_instruction is not None:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            error_body = response.text[:200]
            raise ValueError(
                f"Google API error {response.status_code}: {error_body}"
            )
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Google API returned an empty response (no candidates)")

    parts = candidates[0].get("content", {}).get("parts", [])
    completion_text = "".join(p.get("text", "") for p in parts if "text" in p)

    usage = data.get("usageMetadata", {})
    input_tokens: int = usage.get("promptTokenCount", 0)
    output_tokens: int = usage.get("candidatesTokenCount", 0)
    return completion_text, input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Tool-calling variants (used by demo agents)
# ---------------------------------------------------------------------------


@dataclass
class LlmToolResponse:
    """Rich response from an LLM call that may include tool calls."""

    completion: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    raw_message: dict[str, Any] = field(default_factory=dict)


async def call_openai_with_tools(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 1.0,
) -> LlmToolResponse:
    """Call OpenAI chat completions with optional tool definitions.

    Returns an LlmToolResponse with parsed tool_calls if the model
    decided to invoke tools.
    """
    if not api_key:
        raise ValueError("OpenAI API key is not configured")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            error_body = response.text[:200]
            raise ValueError(
                f"OpenAI API error {response.status_code}: {error_body}"
            )
        data = response.json()

    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        raise ValueError("OpenAI returned an empty or invalid response")

    message = choices[0].get("message", {})
    completion_text: str = message.get("content") or ""
    finish_reason: str = choices[0].get("finish_reason", "stop")

    raw_tool_calls: list[dict[str, Any]] = message.get("tool_calls") or []
    tool_calls: list[dict[str, Any]] = []
    for tc in raw_tool_calls:
        tool_calls.append({
            "id": tc.get("id", ""),
            "type": "function",
            "function": {
                "name": tc.get("function", {}).get("name", ""),
                "arguments": tc.get("function", {}).get("arguments", "{}"),
            },
        })

    usage = data.get("usage", {})
    return LlmToolResponse(
        completion=completion_text,
        tool_calls=tool_calls,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        finish_reason=finish_reason,
        raw_message=message,
    )


async def call_anthropic_with_tools(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 1.0,
) -> LlmToolResponse:
    """Call Anthropic messages API with optional tool definitions.

    Returns an LlmToolResponse with parsed tool_calls if the model
    decided to invoke tools.
    """
    if not api_key:
        raise ValueError("Anthropic API key is not configured")

    system_text: str | None = None
    anthropic_messages: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_text = msg.get("content", "")
        else:
            anthropic_messages.append(msg)

    payload: dict[str, Any] = {
        "model": model,
        "messages": anthropic_messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }
    if system_text is not None:
        payload["system"] = system_text
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            error_body = response.text[:200]
            raise ValueError(
                f"Anthropic API error {response.status_code}: {error_body}"
            )
        data = response.json()

    content_blocks: list[dict[str, Any]] = data.get("content", [])
    completion_text = ""
    tool_calls: list[dict[str, Any]] = []

    for block in content_blocks:
        if block.get("type") == "text":
            completion_text += block.get("text", "")
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            })

    usage = data.get("usage", {})
    stop_reason: str = data.get("stop_reason", "end_turn")

    return LlmToolResponse(
        completion=completion_text,
        tool_calls=tool_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        finish_reason=stop_reason,
        raw_message={"content": content_blocks},
    )
