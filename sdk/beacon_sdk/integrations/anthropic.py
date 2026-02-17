"""Anthropic auto-instrumentation. Patches messages create to create LLM spans."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_create: Any = None
_original_async_create: Any = None

# Cost per 1K tokens: (input, output)
_COST_PER_1K: dict[str, tuple[float, float]] = {
    "claude-opus-4": (0.015, 0.075),
    "claude-sonnet-4": (0.003, 0.015),
    "claude-haiku-3-5": (0.0008, 0.004),
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-5-haiku": (0.0008, 0.004),
    "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model and token counts."""
    for prefix, (inp, out) in _COST_PER_1K.items():
        if model.startswith(prefix):
            return (input_tokens / 1000 * inp) + (output_tokens / 1000 * out)
    return 0.0


def _extract_completion(response: Any) -> str:
    """Extract the text completion from an Anthropic response."""
    if not hasattr(response, "content") or not response.content:
        return ""
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def _build_prompt_json(kwargs: dict[str, Any]) -> str:
    """Build a JSON string of the prompt including system and messages."""
    prompt_parts: list[dict[str, Any]] = []
    if "system" in kwargs:
        prompt_parts.append({"role": "system", "content": kwargs["system"]})
    for msg in kwargs.get("messages", []):
        prompt_parts.append(msg)
    return json.dumps(prompt_parts, default=str)


def _apply_response_attributes(span: Any, response: Any, model: str) -> None:
    """Extract attributes from an Anthropic message response."""
    span.set_attribute("llm.completion", _extract_completion(response))

    if hasattr(response, "stop_reason"):
        span.set_attribute("llm.finish_reason", response.stop_reason)

    if hasattr(response, "usage") and response.usage is not None:
        input_tokens = response.usage.input_tokens or 0
        output_tokens = response.usage.output_tokens or 0
        span.set_attribute("llm.tokens.input", input_tokens)
        span.set_attribute("llm.tokens.output", output_tokens)
        span.set_attribute("llm.tokens.total", input_tokens + output_tokens)
        span.set_attribute(
            "llm.cost_usd", _estimate_cost(model, input_tokens, output_tokens)
        )

    if hasattr(response, "model"):
        span.set_attribute("llm.model", response.model)


def _patched_create_fn(original: Any) -> Any:
    """Create a sync wrapper around the original create method."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None or kwargs.get("stream"):
            # TODO: streaming support
            return original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="anthropic.messages.create",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "anthropic",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        if "temperature" in kwargs:
            span.set_attribute("llm.temperature", kwargs["temperature"])
        if "max_tokens" in kwargs:
            span.set_attribute("llm.max_tokens", kwargs["max_tokens"])

        try:
            response = original(self, *args, **kwargs)
            _apply_response_attributes(span, response, model)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return response
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _patched_async_create_fn(original: Any) -> Any:
    """Create an async wrapper around the original async create method."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None or kwargs.get("stream"):
            # TODO: streaming support
            return await original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="anthropic.messages.create",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "anthropic",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        if "temperature" in kwargs:
            span.set_attribute("llm.temperature", kwargs["temperature"])
        if "max_tokens" in kwargs:
            span.set_attribute("llm.max_tokens", kwargs["max_tokens"])

        try:
            response = await original(self, *args, **kwargs)
            _apply_response_attributes(span, response, model)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return response
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def patch() -> None:
    """Monkey-patch the Anthropic client to auto-instrument message creation."""
    global _patched, _original_create, _original_async_create

    if _patched:
        return

    try:
        import anthropic.resources.messages as messages_mod
    except ImportError:
        return

    _original_create = messages_mod.Messages.create
    messages_mod.Messages.create = _patched_create_fn(_original_create)

    _original_async_create = messages_mod.AsyncMessages.create
    messages_mod.AsyncMessages.create = _patched_async_create_fn(_original_async_create)

    _patched = True
    logger.debug("Beacon: Anthropic auto-patch applied")


def unpatch() -> None:
    """Restore original Anthropic methods."""
    global _patched, _original_create, _original_async_create

    if not _patched:
        return

    try:
        import anthropic.resources.messages as messages_mod
    except ImportError:
        return

    if _original_create is not None:
        messages_mod.Messages.create = _original_create
    if _original_async_create is not None:
        messages_mod.AsyncMessages.create = _original_async_create

    _original_create = None
    _original_async_create = None
    _patched = False
    logger.debug("Beacon: Anthropic auto-patch removed")
