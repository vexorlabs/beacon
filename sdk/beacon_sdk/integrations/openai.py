"""OpenAI auto-instrumentation. Patches chat completions to create LLM spans."""

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
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4": (0.03, 0.06),
    "gpt-3.5-turbo": (0.001, 0.002),
    "o1": (0.015, 0.06),
    "o1-mini": (0.003, 0.012),
    "o3-mini": (0.0011, 0.0044),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model and token counts."""
    for prefix, (inp, out) in _COST_PER_1K.items():
        if model.startswith(prefix):
            return (input_tokens / 1000 * inp) + (output_tokens / 1000 * out)
    return 0.0


def _apply_response_attributes(span: Any, response: Any, model: str) -> None:
    """Extract attributes from an OpenAI chat completion response."""
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            span.set_attribute("llm.completion", choice.message.content or "")
        if hasattr(choice, "finish_reason"):
            span.set_attribute("llm.finish_reason", choice.finish_reason)

    if hasattr(response, "usage") and response.usage is not None:
        input_tokens = response.usage.prompt_tokens or 0
        output_tokens = response.usage.completion_tokens or 0
        total_tokens = response.usage.total_tokens or 0
        span.set_attribute("llm.tokens.input", input_tokens)
        span.set_attribute("llm.tokens.output", output_tokens)
        span.set_attribute("llm.tokens.total", total_tokens)
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
            name="openai.chat.completions",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "openai",
                "llm.model": model,
            },
        )
        span.set_attribute(
            "llm.prompt", json.dumps(kwargs.get("messages", []), default=str)
        )
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
            name="openai.chat.completions",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "openai",
                "llm.model": model,
            },
        )
        span.set_attribute(
            "llm.prompt", json.dumps(kwargs.get("messages", []), default=str)
        )
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
    """Monkey-patch the OpenAI client to auto-instrument chat completions."""
    global _patched, _original_create, _original_async_create

    if _patched:
        return

    try:
        import openai.resources.chat.completions as completions_mod
    except ImportError:
        return

    _original_create = completions_mod.Completions.create
    completions_mod.Completions.create = _patched_create_fn(_original_create)

    _original_async_create = completions_mod.AsyncCompletions.create
    completions_mod.AsyncCompletions.create = _patched_async_create_fn(
        _original_async_create
    )

    _patched = True
    logger.debug("Beacon: OpenAI auto-patch applied")


def unpatch() -> None:
    """Restore original OpenAI methods."""
    global _patched, _original_create, _original_async_create

    if not _patched:
        return

    try:
        import openai.resources.chat.completions as completions_mod
    except ImportError:
        return

    if _original_create is not None:
        completions_mod.Completions.create = _original_create
    if _original_async_create is not None:
        completions_mod.AsyncCompletions.create = _original_async_create

    _original_create = None
    _original_async_create = None
    _patched = False
    logger.debug("Beacon: OpenAI auto-patch removed")
