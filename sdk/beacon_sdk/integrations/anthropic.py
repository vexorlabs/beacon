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

    if hasattr(response, "content") and response.content:
        tool_calls = [
            {"id": block.id, "name": block.name, "input": block.input}
            for block in response.content
            if hasattr(block, "type") and block.type == "tool_use"
        ]
        if tool_calls:
            span.set_attribute(
                "llm.tool_calls", json.dumps(tool_calls, default=str)
            )

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


class AnthropicStreamWrapper:
    """Wraps an Anthropic MessageStream to intercept events and finalize the span."""

    def __init__(
        self,
        stream: Any,
        span: Any,
        token: Any,
        tracer: Any,
        model: str,
    ) -> None:
        self._stream = stream
        self._span = span
        self._token = token
        self._tracer = tracer
        self._model = model
        self._text_chunks: list[str] = []
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._finish_reason: str | None = None
        self._finalized = False

    def __iter__(self) -> AnthropicStreamWrapper:
        return self

    def __next__(self) -> Any:
        try:
            event = next(self._stream)
            self._process_event(event)
            return event
        except StopIteration:
            self._finalize(status=SpanStatus.OK)
            raise
        except Exception as exc:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc))
            raise

    def __enter__(self) -> AnthropicStreamWrapper:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc_val))
        else:
            self._finalize(status=SpanStatus.OK)
        if hasattr(self._stream, "close"):
            self._stream.close()

    def __del__(self) -> None:
        self._finalize(status=SpanStatus.OK)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def _process_event(self, event: Any) -> None:
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            message = getattr(event, "message", None)
            if message is not None and hasattr(message, "usage"):
                self._input_tokens = getattr(message.usage, "input_tokens", 0) or 0

        elif event_type == "content_block_delta":
            delta = getattr(event, "delta", None)
            if delta is not None and hasattr(delta, "text"):
                self._text_chunks.append(delta.text)

        elif event_type == "message_delta":
            delta = getattr(event, "delta", None)
            if delta is not None and hasattr(delta, "stop_reason"):
                self._finish_reason = delta.stop_reason
            usage = getattr(event, "usage", None)
            if usage is not None and hasattr(usage, "output_tokens"):
                self._output_tokens = getattr(usage, "output_tokens", 0) or 0

    def _finalize(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        if self._finalized:
            return
        self._finalized = True

        self._span.set_attribute("llm.completion", "".join(self._text_chunks))
        if self._finish_reason:
            self._span.set_attribute("llm.finish_reason", self._finish_reason)

        total_tokens = self._input_tokens + self._output_tokens
        self._span.set_attribute("llm.tokens.input", self._input_tokens)
        self._span.set_attribute("llm.tokens.output", self._output_tokens)
        self._span.set_attribute("llm.tokens.total", total_tokens)
        self._span.set_attribute(
            "llm.cost_usd",
            _estimate_cost(self._model, self._input_tokens, self._output_tokens),
        )

        self._tracer.end_span(
            self._span, self._token, status=status, error_message=error_message
        )


class AnthropicAsyncStreamWrapper:
    """Wraps an Anthropic AsyncMessageStream to intercept events and finalize the span."""

    def __init__(
        self,
        stream: Any,
        span: Any,
        token: Any,
        tracer: Any,
        model: str,
    ) -> None:
        self._stream = stream
        self._span = span
        self._token = token
        self._tracer = tracer
        self._model = model
        self._text_chunks: list[str] = []
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._finish_reason: str | None = None
        self._finalized = False

    def __aiter__(self) -> AnthropicAsyncStreamWrapper:
        return self

    async def __anext__(self) -> Any:
        try:
            event = await self._stream.__anext__()
            self._process_event(event)
            return event
        except StopAsyncIteration:
            self._finalize(status=SpanStatus.OK)
            raise
        except Exception as exc:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc))
            raise

    async def __aenter__(self) -> AnthropicAsyncStreamWrapper:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc_val))
        else:
            self._finalize(status=SpanStatus.OK)
        if hasattr(self._stream, "close"):
            await self._stream.close()

    def __del__(self) -> None:
        self._finalize(status=SpanStatus.OK)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def _process_event(self, event: Any) -> None:
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            message = getattr(event, "message", None)
            if message is not None and hasattr(message, "usage"):
                self._input_tokens = getattr(message.usage, "input_tokens", 0) or 0

        elif event_type == "content_block_delta":
            delta = getattr(event, "delta", None)
            if delta is not None and hasattr(delta, "text"):
                self._text_chunks.append(delta.text)

        elif event_type == "message_delta":
            delta = getattr(event, "delta", None)
            if delta is not None and hasattr(delta, "stop_reason"):
                self._finish_reason = delta.stop_reason
            usage = getattr(event, "usage", None)
            if usage is not None and hasattr(usage, "output_tokens"):
                self._output_tokens = getattr(usage, "output_tokens", 0) or 0

    def _finalize(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        if self._finalized:
            return
        self._finalized = True

        self._span.set_attribute("llm.completion", "".join(self._text_chunks))
        if self._finish_reason:
            self._span.set_attribute("llm.finish_reason", self._finish_reason)

        total_tokens = self._input_tokens + self._output_tokens
        self._span.set_attribute("llm.tokens.input", self._input_tokens)
        self._span.set_attribute("llm.tokens.output", self._output_tokens)
        self._span.set_attribute("llm.tokens.total", total_tokens)
        self._span.set_attribute(
            "llm.cost_usd",
            _estimate_cost(self._model, self._input_tokens, self._output_tokens),
        )

        self._tracer.end_span(
            self._span, self._token, status=status, error_message=error_message
        )


def _patched_create_fn(original: Any) -> Any:
    """Create a sync wrapper around the original create method."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        is_stream = kwargs.get("stream", False)
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
            if is_stream:
                return AnthropicStreamWrapper(response, span, token, tracer, model)
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
        if tracer is None:
            return await original(self, *args, **kwargs)

        is_stream = kwargs.get("stream", False)
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
            if is_stream:
                return AnthropicAsyncStreamWrapper(
                    response, span, token, tracer, model
                )
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
