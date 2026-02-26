"""OpenAI auto-instrumentation. Patches chat completions to create LLM spans."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType
from beacon_sdk.pricing import estimate_cost as _estimate_cost

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_create: Any = None
_original_async_create: Any = None


def _apply_response_attributes(span: Any, response: Any, model: str) -> None:
    """Extract attributes from an OpenAI chat completion response."""
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            span.set_attribute("llm.completion", choice.message.content or "")
        if hasattr(choice, "finish_reason"):
            span.set_attribute("llm.finish_reason", choice.finish_reason)
        if (
            hasattr(choice, "message")
            and hasattr(choice.message, "tool_calls")
            and choice.message.tool_calls
        ):
            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
            span.set_attribute("llm.tool_calls", json.dumps(tool_calls))

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


class OpenAIStreamWrapper:
    """Wraps an OpenAI Stream to intercept chunks and finalize the span."""

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
        self._chunks: list[str] = []
        self._finish_reason: str | None = None
        self._usage: Any = None
        self._finalized = False

    def __iter__(self) -> OpenAIStreamWrapper:
        return self

    def __next__(self) -> Any:
        try:
            chunk = next(self._stream)
            self._process_chunk(chunk)
            return chunk
        except StopIteration:
            self._finalize(status=SpanStatus.OK)
            raise
        except Exception as exc:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc))
            raise

    def __enter__(self) -> OpenAIStreamWrapper:
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

    def _process_chunk(self, chunk: Any) -> None:
        if hasattr(chunk, "choices") and chunk.choices:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)
            if (
                delta is not None
                and hasattr(delta, "content")
                and delta.content is not None
            ):
                self._chunks.append(delta.content)
            finish_reason = getattr(choice, "finish_reason", None)
            if finish_reason is not None:
                self._finish_reason = finish_reason
        if hasattr(chunk, "usage") and chunk.usage is not None:
            self._usage = chunk.usage

    def _finalize(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        if self._finalized:
            return
        self._finalized = True

        self._span.set_attribute("llm.completion", "".join(self._chunks))
        if self._finish_reason:
            self._span.set_attribute("llm.finish_reason", self._finish_reason)

        if self._usage is not None:
            input_tokens = getattr(self._usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(self._usage, "completion_tokens", 0) or 0
            total_tokens = getattr(self._usage, "total_tokens", 0) or 0
            self._span.set_attribute("llm.tokens.input", input_tokens)
            self._span.set_attribute("llm.tokens.output", output_tokens)
            self._span.set_attribute("llm.tokens.total", total_tokens)
            self._span.set_attribute(
                "llm.cost_usd",
                _estimate_cost(self._model, input_tokens, output_tokens),
            )

        self._tracer.end_span(
            self._span, self._token, status=status, error_message=error_message
        )


class OpenAIAsyncStreamWrapper:
    """Wraps an OpenAI AsyncStream to intercept chunks and finalize the span."""

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
        self._chunks: list[str] = []
        self._finish_reason: str | None = None
        self._usage: Any = None
        self._finalized = False

    def __aiter__(self) -> OpenAIAsyncStreamWrapper:
        return self

    async def __anext__(self) -> Any:
        try:
            chunk = await self._stream.__anext__()
            self._process_chunk(chunk)
            return chunk
        except StopAsyncIteration:
            self._finalize(status=SpanStatus.OK)
            raise
        except Exception as exc:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc))
            raise

    async def __aenter__(self) -> OpenAIAsyncStreamWrapper:
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

    def _process_chunk(self, chunk: Any) -> None:
        if hasattr(chunk, "choices") and chunk.choices:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)
            if (
                delta is not None
                and hasattr(delta, "content")
                and delta.content is not None
            ):
                self._chunks.append(delta.content)
            finish_reason = getattr(choice, "finish_reason", None)
            if finish_reason is not None:
                self._finish_reason = finish_reason
        if hasattr(chunk, "usage") and chunk.usage is not None:
            self._usage = chunk.usage

    def _finalize(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        if self._finalized:
            return
        self._finalized = True

        self._span.set_attribute("llm.completion", "".join(self._chunks))
        if self._finish_reason:
            self._span.set_attribute("llm.finish_reason", self._finish_reason)

        if self._usage is not None:
            input_tokens = getattr(self._usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(self._usage, "completion_tokens", 0) or 0
            total_tokens = getattr(self._usage, "total_tokens", 0) or 0
            self._span.set_attribute("llm.tokens.input", input_tokens)
            self._span.set_attribute("llm.tokens.output", output_tokens)
            self._span.set_attribute("llm.tokens.total", total_tokens)
            self._span.set_attribute(
                "llm.cost_usd",
                _estimate_cost(self._model, input_tokens, output_tokens),
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
            if is_stream:
                return OpenAIStreamWrapper(response, span, token, tracer, model)
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
            if is_stream:
                return OpenAIAsyncStreamWrapper(response, span, token, tracer, model)
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
