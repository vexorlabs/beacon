"""Google Gemini auto-instrumentation. Patches generate_content to create LLM spans."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType
from beacon_sdk.pricing import estimate_cost as _estimate_cost

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_generate: Any = None
_original_generate_stream: Any = None
_original_async_generate: Any = None
_original_async_generate_stream: Any = None


def _build_prompt_json(kwargs: dict[str, Any]) -> str:
    """Build a JSON string of the prompt including system instruction and contents."""
    prompt_parts: list[Any] = []

    # Extract system instruction from config if present
    config = kwargs.get("config")
    if config is not None:
        system_instruction = getattr(config, "system_instruction", None)
        if system_instruction is not None:
            prompt_parts.append({"role": "system", "content": str(system_instruction)})

    contents = kwargs.get("contents", "")
    if isinstance(contents, str):
        prompt_parts.append({"role": "user", "content": contents})
    elif isinstance(contents, list):
        for item in contents:
            prompt_parts.append(item)
    else:
        # Single Content object or other type
        prompt_parts.append(contents)

    return json.dumps(prompt_parts, default=str)


def _extract_completion(response: Any) -> str:
    """Extract text completion from a Gemini response."""
    # Try the convenience .text property first
    text = getattr(response, "text", None)
    if text is not None:
        return text

    # Fall back to parsing candidates
    candidates = getattr(response, "candidates", None)
    if candidates:
        content = getattr(candidates[0], "content", None)
        if content is not None:
            parts = getattr(content, "parts", [])
            texts = [getattr(p, "text", "") for p in parts if hasattr(p, "text")]
            return "".join(texts)
    return ""


def _apply_response_attributes(span: Any, response: Any, model: str) -> None:
    """Extract attributes from a Gemini response."""
    span.set_attribute("llm.completion", _extract_completion(response))

    # Finish reason
    candidates = getattr(response, "candidates", None)
    if candidates:
        finish_reason = getattr(candidates[0], "finish_reason", None)
        if finish_reason is not None:
            span.set_attribute("llm.finish_reason", str(finish_reason))

    # Function/tool calls
    function_calls = getattr(response, "function_calls", None)
    if function_calls:
        tool_calls = [
            {"name": getattr(fc, "name", ""), "args": getattr(fc, "args", {})}
            for fc in function_calls
        ]
        span.set_attribute("llm.tool_calls", json.dumps(tool_calls, default=str))

    # Token usage
    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or 0
        span.set_attribute("llm.tokens.input", input_tokens)
        span.set_attribute("llm.tokens.output", output_tokens)
        span.set_attribute("llm.tokens.total", total_tokens)
        span.set_attribute(
            "llm.cost_usd", _estimate_cost(model, input_tokens, output_tokens)
        )


def _extract_config_attrs(span: Any, kwargs: dict[str, Any]) -> None:
    """Extract temperature and max_tokens from the Gemini config object."""
    config = kwargs.get("config")
    if config is None:
        return
    temperature = getattr(config, "temperature", None)
    if temperature is not None:
        span.set_attribute("llm.temperature", temperature)
    max_output_tokens = getattr(config, "max_output_tokens", None)
    if max_output_tokens is not None:
        span.set_attribute("llm.max_tokens", max_output_tokens)


# ---------------------------------------------------------------------------
# Stream wrappers
# ---------------------------------------------------------------------------


class GoogleStreamWrapper:
    """Wraps a Gemini sync stream to intercept chunks and finalize the span."""

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

    def __iter__(self) -> GoogleStreamWrapper:
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

    def __enter__(self) -> GoogleStreamWrapper:
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
        text = getattr(chunk, "text", None)
        if text:
            self._chunks.append(text)

        candidates = getattr(chunk, "candidates", None)
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            if finish_reason is not None:
                self._finish_reason = str(finish_reason)

        usage = getattr(chunk, "usage_metadata", None)
        if usage is not None:
            self._usage = usage

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
            input_tokens = getattr(self._usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(self._usage, "candidates_token_count", 0) or 0
            total_tokens = getattr(self._usage, "total_token_count", 0) or 0
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


class GoogleAsyncStreamWrapper:
    """Wraps a Gemini async stream to intercept chunks and finalize the span."""

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

    def __aiter__(self) -> GoogleAsyncStreamWrapper:
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

    async def __aenter__(self) -> GoogleAsyncStreamWrapper:
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
        text = getattr(chunk, "text", None)
        if text:
            self._chunks.append(text)

        candidates = getattr(chunk, "candidates", None)
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            if finish_reason is not None:
                self._finish_reason = str(finish_reason)

        usage = getattr(chunk, "usage_metadata", None)
        if usage is not None:
            self._usage = usage

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
            input_tokens = getattr(self._usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(self._usage, "candidates_token_count", 0) or 0
            total_tokens = getattr(self._usage, "total_token_count", 0) or 0
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


# ---------------------------------------------------------------------------
# Patched function factories
# ---------------------------------------------------------------------------


def _patched_generate_fn(original: Any) -> Any:
    """Create a sync wrapper for generate_content (non-streaming)."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="google.models.generate_content",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "google",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        _extract_config_attrs(span, kwargs)

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


def _patched_generate_stream_fn(original: Any) -> Any:
    """Create a sync wrapper for generate_content_stream (streaming)."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="google.models.generate_content_stream",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "google",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        _extract_config_attrs(span, kwargs)

        try:
            stream = original(self, *args, **kwargs)
            return GoogleStreamWrapper(stream, span, token, tracer, model)
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _patched_async_generate_fn(original: Any) -> Any:
    """Create an async wrapper for generate_content (non-streaming)."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="google.models.generate_content",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "google",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        _extract_config_attrs(span, kwargs)

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


def _patched_async_generate_stream_fn(original: Any) -> Any:
    """Create an async wrapper for generate_content_stream (streaming)."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, *args, **kwargs)

        model = kwargs.get("model", "unknown")
        span, token = tracer.start_span(
            name="google.models.generate_content_stream",
            span_type=SpanType.LLM_CALL,
            attributes={
                "llm.provider": "google",
                "llm.model": model,
            },
        )
        span.set_attribute("llm.prompt", _build_prompt_json(kwargs))
        _extract_config_attrs(span, kwargs)

        try:
            stream = await original(self, *args, **kwargs)
            return GoogleAsyncStreamWrapper(stream, span, token, tracer, model)
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def patch() -> None:
    """Monkey-patch the Google GenAI client to auto-instrument generate_content."""
    global _patched, _original_generate, _original_generate_stream
    global _original_async_generate, _original_async_generate_stream

    if _patched:
        return

    try:
        from google.genai import models as models_mod
    except ImportError:
        return

    # Sync methods
    _original_generate = models_mod.Models.generate_content
    models_mod.Models.generate_content = _patched_generate_fn(_original_generate)

    if hasattr(models_mod.Models, "generate_content_stream"):
        _original_generate_stream = models_mod.Models.generate_content_stream
        models_mod.Models.generate_content_stream = _patched_generate_stream_fn(
            _original_generate_stream
        )

    # Async methods
    if hasattr(models_mod, "AsyncModels"):
        _original_async_generate = models_mod.AsyncModels.generate_content
        models_mod.AsyncModels.generate_content = _patched_async_generate_fn(
            _original_async_generate
        )

        if hasattr(models_mod.AsyncModels, "generate_content_stream"):
            _original_async_generate_stream = (
                models_mod.AsyncModels.generate_content_stream
            )
            models_mod.AsyncModels.generate_content_stream = (
                _patched_async_generate_stream_fn(_original_async_generate_stream)
            )

    _patched = True
    logger.debug("Beacon: Google GenAI auto-patch applied")


def unpatch() -> None:
    """Restore original Google GenAI methods."""
    global _patched, _original_generate, _original_generate_stream
    global _original_async_generate, _original_async_generate_stream

    if not _patched:
        return

    try:
        from google.genai import models as models_mod
    except ImportError:
        return

    if _original_generate is not None:
        models_mod.Models.generate_content = _original_generate
    if _original_generate_stream is not None:
        models_mod.Models.generate_content_stream = _original_generate_stream
    if _original_async_generate is not None and hasattr(models_mod, "AsyncModels"):
        models_mod.AsyncModels.generate_content = _original_async_generate
    if _original_async_generate_stream is not None and hasattr(
        models_mod, "AsyncModels"
    ):
        models_mod.AsyncModels.generate_content_stream = (
            _original_async_generate_stream
        )

    _original_generate = None
    _original_generate_stream = None
    _original_async_generate = None
    _original_async_generate_stream = None
    _patched = False
    logger.debug("Beacon: Google GenAI auto-patch removed")
