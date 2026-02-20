"""Tests for the Google Gemini auto-instrumentation integration."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations.google_genai import (
    GoogleAsyncStreamWrapper,
    GoogleStreamWrapper,
    _patched_async_generate_fn,
    _patched_async_generate_stream_fn,
    _patched_generate_fn,
    _patched_generate_stream_fn,
)
from beacon_sdk.models import SpanStatus, SpanType
from beacon_sdk.pricing import estimate_cost as _estimate_cost
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None


# ---------------------------------------------------------------------------
# Mock response factories
# ---------------------------------------------------------------------------


def _make_mock_response(
    text: str = "Hello!",
    model: str = "gemini-2.5-flash",
    prompt_token_count: int = 10,
    candidates_token_count: int = 5,
    total_token_count: int = 15,
    finish_reason: str = "STOP",
) -> SimpleNamespace:
    """Create a mock Gemini generate_content response."""
    return SimpleNamespace(
        text=text,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text=text)],
                ),
                finish_reason=finish_reason,
            )
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_token_count,
            candidates_token_count=candidates_token_count,
            total_token_count=total_token_count,
        ),
        function_calls=None,
    )


def _make_google_chunk(
    text: str | None = None,
    finish_reason: str | None = None,
    usage_metadata: SimpleNamespace | None = None,
) -> SimpleNamespace:
    """Create a mock Gemini streaming chunk."""
    parts = [SimpleNamespace(text=text)] if text else []
    candidates = [
        SimpleNamespace(
            content=SimpleNamespace(parts=parts),
            finish_reason=finish_reason,
        )
    ]
    return SimpleNamespace(
        text=text or "",
        candidates=candidates,
        usage_metadata=usage_metadata,
        function_calls=None,
    )


# ---------------------------------------------------------------------------
# Mock streams
# ---------------------------------------------------------------------------


class MockGoogleStream:
    """Mock Gemini stream that yields chunks."""

    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = iter(chunks)

    def __iter__(self) -> MockGoogleStream:
        return self

    def __next__(self) -> SimpleNamespace:
        return next(self._chunks)

    def __enter__(self) -> MockGoogleStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class MockGoogleErrorStream:
    """Mock stream that raises an error after yielding some chunks."""

    def __init__(
        self, chunks: list[SimpleNamespace], error: Exception
    ) -> None:
        self._chunks = iter(chunks)
        self._error = error

    def __iter__(self) -> MockGoogleErrorStream:
        return self

    def __next__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise self._error from None

    def __enter__(self) -> MockGoogleErrorStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class MockAsyncGoogleStream:
    """Mock async Gemini stream that yields chunks."""

    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = iter(chunks)

    def __aiter__(self) -> MockAsyncGoogleStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise StopAsyncIteration from None

    async def __aenter__(self) -> MockAsyncGoogleStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class MockAsyncGoogleErrorStream:
    """Mock async stream that raises an error after yielding some chunks."""

    def __init__(
        self, chunks: list[SimpleNamespace], error: Exception
    ) -> None:
        self._chunks = iter(chunks)
        self._error = error

    def __aiter__(self) -> MockAsyncGoogleErrorStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise self._error from None

    async def __aenter__(self) -> MockAsyncGoogleErrorStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Fake original functions
# ---------------------------------------------------------------------------


def _make_fake_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original generate_content function."""

    def fake_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        return response or _make_mock_response(model=kwargs.get("model", "gemini-2.5-flash"))

    return fake_generate


def _make_fake_stream_original(
    stream: MockGoogleStream | MockGoogleErrorStream | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original generate_content_stream function."""

    def fake_generate_stream(self: Any, *args: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        return stream or MockGoogleStream([])

    return fake_generate_stream


def _make_fake_async_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original async generate_content function."""

    async def fake_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        return response or _make_mock_response(model=kwargs.get("model", "gemini-2.5-flash"))

    return fake_generate


def _make_fake_async_stream_original(
    stream: MockAsyncGoogleStream | MockAsyncGoogleErrorStream | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original async generate_content_stream function."""

    async def fake_generate_stream(self: Any, *args: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        return stream or MockAsyncGoogleStream([])

    return fake_generate_stream


# ---------------------------------------------------------------------------
# Non-streaming tests
# ---------------------------------------------------------------------------


def test_google_creates_llm_call_span(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "google.models.generate_content"
    assert span.attributes["llm.provider"] == "google"
    assert span.attributes["llm.model"] == "gemini-2.5-flash"
    assert span.status == SpanStatus.OK


def test_google_records_token_usage(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 10
    assert span.attributes["llm.tokens.output"] == 5
    assert span.attributes["llm.tokens.total"] == 15


def test_google_records_cost(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    span = exporter.spans[0]
    expected = _estimate_cost("gemini-2.5-flash", 10, 5)
    assert span.attributes["llm.cost_usd"] == expected
    assert expected > 0


def test_google_records_prompt(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hello world")

    span = exporter.spans[0]
    prompt = json.loads(span.attributes["llm.prompt"])
    assert any("Hello world" in str(p) for p in prompt)


def test_google_records_completion(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    span = exporter.spans[0]
    assert span.attributes["llm.completion"] == "Hello!"


def test_google_records_finish_reason(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    span = exporter.spans[0]
    assert span.attributes["llm.finish_reason"] == "STOP"


def test_google_records_error_status(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(
        _make_fake_original(error=RuntimeError("API connection failed"))
    )

    with pytest.raises(RuntimeError, match="API connection failed"):
        wrapper(None, model="gemini-2.5-flash", contents="Hi")

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "API connection failed"


def test_google_captures_config_attrs(exporter: InMemoryExporter) -> None:
    config = SimpleNamespace(temperature=0.7, max_output_tokens=100, system_instruction=None)
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi", config=config)

    span = exporter.spans[0]
    assert span.attributes["llm.temperature"] == 0.7
    assert span.attributes["llm.max_tokens"] == 100


def test_google_captures_system_instruction(exporter: InMemoryExporter) -> None:
    config = SimpleNamespace(
        temperature=None, max_output_tokens=None,
        system_instruction="You are a helpful assistant",
    )
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi", config=config)

    span = exporter.spans[0]
    prompt = json.loads(span.attributes["llm.prompt"])
    assert prompt[0]["role"] == "system"
    assert "helpful assistant" in prompt[0]["content"]


def test_google_captures_function_calls(exporter: InMemoryExporter) -> None:
    response = SimpleNamespace(
        text=None,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[]),
                finish_reason="STOP",
            )
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=20,
            candidates_token_count=10,
            total_token_count=30,
        ),
        function_calls=[
            SimpleNamespace(name="get_weather", args={"location": "San Francisco"}),
        ],
    )
    wrapper = _patched_generate_fn(_make_fake_original(response=response))
    wrapper(None, model="gemini-2.5-flash", contents="What's the weather?")

    span = exporter.spans[0]
    tool_calls = json.loads(span.attributes["llm.tool_calls"])
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_weather"
    assert tool_calls[0]["args"]["location"] == "San Francisco"


def test_google_no_tool_calls_when_text_only(exporter: InMemoryExporter) -> None:
    wrapper = _patched_generate_fn(_make_fake_original())
    wrapper(None, model="gemini-2.5-flash", contents="Hi")

    span = exporter.spans[0]
    assert "llm.tool_calls" not in span.attributes


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------


def test_google_stream_creates_span(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_google_chunk(text="Hello"),
        _make_google_chunk(text=" world"),
        _make_google_chunk(text="!"),
        _make_google_chunk(finish_reason="STOP"),
    ]
    mock_stream = MockGoogleStream(chunks)
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=mock_stream))

    result = wrapper(None, model="gemini-2.5-flash", contents="Hi")
    assert isinstance(result, GoogleStreamWrapper)

    collected = list(result)
    assert len(collected) == 4

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "google.models.generate_content_stream"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello world!"
    assert span.attributes["llm.finish_reason"] == "STOP"


def test_google_stream_captures_usage(exporter: InMemoryExporter) -> None:
    usage = SimpleNamespace(prompt_token_count=20, candidates_token_count=10, total_token_count=30)
    chunks = [
        _make_google_chunk(text="Hi"),
        _make_google_chunk(finish_reason="STOP", usage_metadata=usage),
    ]
    mock_stream = MockGoogleStream(chunks)
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=mock_stream))

    result = wrapper(None, model="gemini-2.5-flash", contents="Hi")
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 20
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 30
    assert span.attributes["llm.cost_usd"] == _estimate_cost("gemini-2.5-flash", 20, 10)


def test_google_stream_no_usage(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_google_chunk(text="Hi"),
        _make_google_chunk(finish_reason="STOP"),
    ]
    mock_stream = MockGoogleStream(chunks)
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=mock_stream))

    result = wrapper(None, model="gemini-2.5-flash", contents="Hi")
    list(result)

    span = exporter.spans[0]
    assert "llm.tokens.input" not in span.attributes
    assert "llm.cost_usd" not in span.attributes


def test_google_stream_error_midstream(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_google_chunk(text="Hello"),
        _make_google_chunk(text=" world"),
    ]
    error_stream = MockGoogleErrorStream(chunks, RuntimeError("Connection lost"))
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=error_stream))

    result = wrapper(None, model="gemini-2.5-flash", contents="Hi")

    collected: list[SimpleNamespace] = []
    with pytest.raises(RuntimeError, match="Connection lost"):
        for chunk in result:
            collected.append(chunk)

    assert len(collected) == 2
    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "Connection lost"
    assert span.attributes["llm.completion"] == "Hello world"


def test_google_stream_context_manager(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_google_chunk(text="one"),
        _make_google_chunk(text="two"),
        _make_google_chunk(text="three"),
    ]
    mock_stream = MockGoogleStream(chunks)
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=mock_stream))

    result = wrapper(None, model="gemini-2.5-flash", contents="Hi")
    with result:
        first = next(result)
        assert first.text == "one"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "one"


def test_google_stream_records_prompt_and_model(
    exporter: InMemoryExporter,
) -> None:
    chunks = [_make_google_chunk(text="Hi", finish_reason="STOP")]
    mock_stream = MockGoogleStream(chunks)
    wrapper = _patched_generate_stream_fn(_make_fake_stream_original(stream=mock_stream))

    result = wrapper(None, model="gemini-2.5-pro", contents="test prompt")
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.provider"] == "google"
    assert span.attributes["llm.model"] == "gemini-2.5-pro"
    assert "test prompt" in span.attributes["llm.prompt"]


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


async def test_google_async_creates_span(exporter: InMemoryExporter) -> None:
    wrapper = _patched_async_generate_fn(_make_fake_async_original())
    await wrapper(None, model="gemini-2.5-flash", contents="Hi")

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "google.models.generate_content"
    assert span.attributes["llm.provider"] == "google"
    assert span.status == SpanStatus.OK


async def test_google_async_stream_creates_span(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_google_chunk(text="Hello"),
        _make_google_chunk(text=" async"),
        _make_google_chunk(text="!"),
        _make_google_chunk(finish_reason="STOP"),
    ]
    mock_stream = MockAsyncGoogleStream(chunks)
    wrapper = _patched_async_generate_stream_fn(
        _make_fake_async_stream_original(stream=mock_stream)
    )

    result = await wrapper(None, model="gemini-2.5-flash", contents="Hi")
    assert isinstance(result, GoogleAsyncStreamWrapper)

    collected = [chunk async for chunk in result]
    assert len(collected) == 4

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "google.models.generate_content_stream"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello async!"
    assert span.attributes["llm.finish_reason"] == "STOP"


async def test_google_async_stream_captures_usage(
    exporter: InMemoryExporter,
) -> None:
    usage = SimpleNamespace(prompt_token_count=20, candidates_token_count=10, total_token_count=30)
    chunks = [
        _make_google_chunk(text="Hi"),
        _make_google_chunk(finish_reason="STOP", usage_metadata=usage),
    ]
    mock_stream = MockAsyncGoogleStream(chunks)
    wrapper = _patched_async_generate_stream_fn(
        _make_fake_async_stream_original(stream=mock_stream)
    )

    result = await wrapper(None, model="gemini-2.5-flash", contents="Hi")
    async for _ in result:
        pass

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 20
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 30
    assert span.attributes["llm.cost_usd"] == _estimate_cost("gemini-2.5-flash", 20, 10)


async def test_google_async_stream_error_midstream(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_google_chunk(text="Hello"),
        _make_google_chunk(text=" world"),
    ]
    error_stream = MockAsyncGoogleErrorStream(
        chunks, RuntimeError("Async connection lost")
    )
    wrapper = _patched_async_generate_stream_fn(
        _make_fake_async_stream_original(stream=error_stream)
    )

    result = await wrapper(None, model="gemini-2.5-flash", contents="Hi")

    collected: list[SimpleNamespace] = []
    with pytest.raises(RuntimeError, match="Async connection lost"):
        async for chunk in result:
            collected.append(chunk)

    assert len(collected) == 2
    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "Async connection lost"
    assert span.attributes["llm.completion"] == "Hello world"


async def test_google_async_stream_context_manager(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_google_chunk(text="one"),
        _make_google_chunk(text="two"),
        _make_google_chunk(text="three"),
    ]
    mock_stream = MockAsyncGoogleStream(chunks)
    wrapper = _patched_async_generate_stream_fn(
        _make_fake_async_stream_original(stream=mock_stream)
    )

    result = await wrapper(None, model="gemini-2.5-flash", contents="Hi")
    async with result:
        first = await result.__anext__()
        assert first.text == "one"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "one"


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def test_google_cost_estimation() -> None:
    assert _estimate_cost("gemini-2.5-flash", 1000, 1000) > 0
    assert _estimate_cost("gemini-2.5-pro", 1000, 1000) > 0
    assert _estimate_cost("gemini-2.0-flash", 1000, 1000) > 0
    assert _estimate_cost("gemini-2.0-flash-lite", 1000, 1000) > 0
    assert _estimate_cost("gemini-1.5-pro", 1000, 1000) > 0
    assert _estimate_cost("gemini-1.5-flash", 1000, 1000) > 0
