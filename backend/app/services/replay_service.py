from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app import models
from app.schemas import ReplayDiff, ReplayResponse

# Simple price table: (input_cost_per_1k, output_cost_per_1k)
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4": (0.03, 0.06),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "claude-3-5-haiku-20241022": (0.001, 0.005),
    "claude-3-opus-20240229": (0.015, 0.075),
    "claude-3-sonnet-20240229": (0.003, 0.015),
    "claude-3-haiku-20240307": (0.00025, 0.00125),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD using a simple price table."""
    prices = _PRICE_TABLE.get(model)
    if prices is None:
        return 0.0
    input_cost, output_cost = prices
    return (input_tokens / 1000) * input_cost + (output_tokens / 1000) * output_cost


async def _call_openai(
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int | None,
) -> tuple[str, int, int]:
    """Call OpenAI chat completions API. Returns (completion, input_tokens, output_tokens)."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

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
        response.raise_for_status()
        data = response.json()

    completion_text: str = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    input_tokens: int = usage.get("prompt_tokens", 0)
    output_tokens: int = usage.get("completion_tokens", 0)
    return completion_text, input_tokens, output_tokens


async def _call_anthropic(
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int | None,
) -> tuple[str, int, int]:
    """Call Anthropic messages API. Returns (completion, input_tokens, output_tokens)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    # Convert from OpenAI message format: extract system message
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
        response.raise_for_status()
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


async def replay_llm_call(
    db: Session,
    span_id: str,
    modified_attributes: dict[str, Any],
) -> ReplayResponse:
    """Replay an LLM call span with modified attributes."""
    span = db.get(models.Span, span_id)
    if span is None:
        raise ValueError("Span not found")

    if span.span_type != "llm_call":
        raise ValueError("Replay only supported for llm_call spans")

    original_attrs: dict[str, Any] = json.loads(span.attributes or "{}")
    merged_attrs = {**original_attrs, **modified_attributes}

    provider: str = merged_attrs.get("llm.provider", "")
    prompt_raw = merged_attrs.get("llm.prompt", "[]")
    messages: list[dict[str, str]] = (
        json.loads(prompt_raw) if isinstance(prompt_raw, str) else prompt_raw
    )
    model: str = merged_attrs.get("llm.model", "")
    temperature: float = float(merged_attrs.get("llm.temperature", 1.0))
    max_tokens_raw = merged_attrs.get("llm.max_tokens")
    max_tokens: int | None = (
        int(max_tokens_raw) if max_tokens_raw is not None else None
    )

    if provider == "openai":
        new_completion, input_tokens, output_tokens = await _call_openai(
            model, messages, temperature, max_tokens
        )
    elif provider == "anthropic":
        new_completion, input_tokens, output_tokens = await _call_anthropic(
            model, messages, temperature, max_tokens
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    original_completion: str = original_attrs.get("llm.completion", "")
    diff = ReplayDiff(
        old_completion=original_completion,
        new_completion=new_completion,
        changed=original_completion != new_completion,
    )

    cost_usd = _estimate_cost(model, input_tokens, output_tokens)
    new_output: dict[str, Any] = {
        "llm.completion": new_completion,
        "llm.tokens.input": input_tokens,
        "llm.tokens.output": output_tokens,
        "llm.cost_usd": cost_usd,
    }

    replay_id = str(uuid4())
    replay_run = models.ReplayRun(
        replay_id=replay_id,
        original_span_id=span_id,
        trace_id=span.trace_id,
        modified_input=json.dumps(modified_attributes),
        new_output=json.dumps(new_output),
        diff=json.dumps(diff.model_dump()),
        created_at=time.time(),
    )
    db.add(replay_run)
    db.commit()

    return ReplayResponse(
        replay_id=replay_id,
        original_span_id=span_id,
        new_output=new_output,
        diff=diff,
    )
