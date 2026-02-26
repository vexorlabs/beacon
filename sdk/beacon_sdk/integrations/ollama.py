"""Ollama auto-instrumentation. Patches ollama.chat() and ollama.generate() for tracing."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_chat: Any = None
_original_generate: Any = None
_original_async_chat: Any = None
_original_async_generate: Any = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_chat_attrs(model: str, messages: Any, kwargs: Any) -> dict[str, Any]:
    """Build span attributes from ollama.chat() arguments."""
    attrs: dict[str, Any] = {
        "llm.provider": "ollama",
        "llm.model": model,
    }
    if messages:
        try:
            attrs["llm.prompt"] = json.dumps(messages, default=str)[:50_000]
        except Exception:
            pass
    return attrs


def _extract_generate_attrs(
    model: str, prompt: str | None, kwargs: Any
) -> dict[str, Any]:
    """Build span attributes from ollama.generate() arguments."""
    attrs: dict[str, Any] = {
        "llm.provider": "ollama",
        "llm.model": model,
    }
    if prompt:
        attrs["llm.prompt"] = prompt[:50_000]
    return attrs


def _apply_response_attrs(span: Any, response: Any) -> None:
    """Extract attributes from an Ollama response dict."""
    if not isinstance(response, dict):
        return

    # Chat response has message.content; generate has response
    message = response.get("message")
    if isinstance(message, dict):
        content = message.get("content", "")
        span.set_attribute("llm.completion", str(content)[:50_000])
    elif "response" in response:
        span.set_attribute("llm.completion", str(response["response"])[:50_000])

    # Token counts
    prompt_tokens = response.get("prompt_eval_count") or 0
    completion_tokens = response.get("eval_count") or 0
    if prompt_tokens > 0:
        span.set_attribute("llm.tokens.input", prompt_tokens)
    if completion_tokens > 0:
        span.set_attribute("llm.tokens.output", completion_tokens)
    if prompt_tokens > 0 or completion_tokens > 0:
        span.set_attribute("llm.tokens.total", prompt_tokens + completion_tokens)

    # Model name from response (may differ from request)
    if "model" in response:
        span.set_attribute("llm.model", response["model"])

    # Duration info
    total_duration = response.get("total_duration")
    if total_duration:
        span.set_attribute("ollama.total_duration_ns", total_duration)


# ---------------------------------------------------------------------------
# Patched function factories
# ---------------------------------------------------------------------------


def _make_chat_wrapper(original: Any) -> Any:
    """Create a sync wrapper around ollama.chat."""

    def wrapper(model: str = "", messages: Any = None, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(model=model, messages=messages, **kwargs)

        # Streaming not instrumented for now — pass through
        if kwargs.get("stream"):
            return original(model=model, messages=messages, **kwargs)

        span, token = tracer.start_span(
            name=f"ollama.chat: {model}",
            span_type=SpanType.LLM_CALL,
            attributes=_extract_chat_attrs(model, messages, kwargs),
        )
        try:
            result = original(model=model, messages=messages, **kwargs)
            _apply_response_attrs(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_generate_wrapper(original: Any) -> Any:
    """Create a sync wrapper around ollama.generate."""

    def wrapper(model: str = "", prompt: str = "", **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(model=model, prompt=prompt, **kwargs)

        if kwargs.get("stream"):
            return original(model=model, prompt=prompt, **kwargs)

        span, token = tracer.start_span(
            name=f"ollama.generate: {model}",
            span_type=SpanType.LLM_CALL,
            attributes=_extract_generate_attrs(model, prompt, kwargs),
        )
        try:
            result = original(model=model, prompt=prompt, **kwargs)
            _apply_response_attrs(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_async_chat_wrapper(original: Any) -> Any:
    """Create an async wrapper around AsyncClient.chat."""

    async def wrapper(
        self: Any, model: str = "", messages: Any = None, **kwargs: Any
    ) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, model=model, messages=messages, **kwargs)

        if kwargs.get("stream"):
            return await original(self, model=model, messages=messages, **kwargs)

        span, token = tracer.start_span(
            name=f"ollama.chat: {model}",
            span_type=SpanType.LLM_CALL,
            attributes=_extract_chat_attrs(model, messages, kwargs),
        )
        try:
            result = await original(self, model=model, messages=messages, **kwargs)
            _apply_response_attrs(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_async_generate_wrapper(original: Any) -> Any:
    """Create an async wrapper around AsyncClient.generate."""

    async def wrapper(
        self: Any, model: str = "", prompt: str = "", **kwargs: Any
    ) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, model=model, prompt=prompt, **kwargs)

        if kwargs.get("stream"):
            return await original(self, model=model, prompt=prompt, **kwargs)

        span, token = tracer.start_span(
            name=f"ollama.generate: {model}",
            span_type=SpanType.LLM_CALL,
            attributes=_extract_generate_attrs(model, prompt, kwargs),
        )
        try:
            result = await original(self, model=model, prompt=prompt, **kwargs)
            _apply_response_attrs(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
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
    """Monkey-patch Ollama's native Python client for auto-instrumentation."""
    global _patched, _original_chat, _original_generate
    global _original_async_chat, _original_async_generate

    if _patched:
        return

    try:
        import ollama as ollama_mod
    except ImportError:
        return

    # Patch module-level functions (ollama.chat, ollama.generate)
    _original_chat = ollama_mod.chat
    ollama_mod.chat = _make_chat_wrapper(_original_chat)

    _original_generate = ollama_mod.generate
    ollama_mod.generate = _make_generate_wrapper(_original_generate)

    # Patch AsyncClient methods if available
    async_client = getattr(ollama_mod, "AsyncClient", None)
    if async_client is not None:
        if hasattr(async_client, "chat"):
            _original_async_chat = async_client.chat
            async_client.chat = _make_async_chat_wrapper(_original_async_chat)
        if hasattr(async_client, "generate"):
            _original_async_generate = async_client.generate
            async_client.generate = _make_async_generate_wrapper(
                _original_async_generate
            )

    _patched = True
    logger.debug("Beacon: Ollama auto-patch applied")


def unpatch() -> None:
    """Restore original Ollama methods."""
    global _patched, _original_chat, _original_generate
    global _original_async_chat, _original_async_generate

    if not _patched:
        return

    try:
        import ollama as ollama_mod
    except ImportError:
        return

    if _original_chat is not None:
        ollama_mod.chat = _original_chat
    if _original_generate is not None:
        ollama_mod.generate = _original_generate

    async_client = getattr(ollama_mod, "AsyncClient", None)
    if async_client is not None:
        if _original_async_chat is not None and hasattr(async_client, "chat"):
            async_client.chat = _original_async_chat
        if _original_async_generate is not None and hasattr(async_client, "generate"):
            async_client.generate = _original_async_generate

    _original_chat = None
    _original_generate = None
    _original_async_chat = None
    _original_async_generate = None
    _patched = False
    logger.debug("Beacon: Ollama auto-patch removed")
