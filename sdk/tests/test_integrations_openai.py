"""Tests for the OpenAI auto-instrumentation integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations.openai import (
    OpenAIAsyncStreamWrapper,
    OpenAIStreamWrapper,
    _estimate_cost,
    _patched_async_create_fn,
    _patched_create_fn,
)
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None


def _make_mock_response(
    content: str = "Hello!",
    model: str = "gpt-4o",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    total_tokens: int = 15,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    """Create a mock OpenAI chat completion response."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
        model=model,
    )


def _make_openai_chunk(
    content: str | None = None,
    finish_reason: str | None = None,
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    """Create a mock OpenAI streaming chunk."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=usage,
    )


class MockOpenAIStream:
    """Mock OpenAI stream that yields chunks."""

    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = iter(chunks)

    def __iter__(self) -> MockOpenAIStream:
        return self

    def __next__(self) -> SimpleNamespace:
        return next(self._chunks)

    def __enter__(self) -> MockOpenAIStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class MockErrorStream:
    """Mock stream that raises an error after yielding some chunks."""

    def __init__(
        self, chunks: list[SimpleNamespace], error: Exception
    ) -> None:
        self._chunks = iter(chunks)
        self._error = error

    def __iter__(self) -> MockErrorStream:
        return self

    def __next__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise self._error from None

    def __enter__(self) -> MockErrorStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def _make_fake_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
    stream: MockOpenAIStream | MockErrorStream | None = None,
) -> Any:
    """Create a fake original create function."""

    def fake_create(self: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        if kwargs.get("stream"):
            if stream is not None:
                return stream
            return MockOpenAIStream([])
        return response or _make_mock_response(model=kwargs.get("model", "gpt-4o"))

    return fake_create


# --- Non-streaming tests (existing) ---


def test_openai_creates_llm_call_span(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[{"role": "user", "content": "Hi"}])

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "openai.chat.completions"
    assert span.attributes["llm.provider"] == "openai"
    assert span.attributes["llm.model"] == "gpt-4o"
    assert span.status == SpanStatus.OK


def test_openai_records_token_usage(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[])

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 10
    assert span.attributes["llm.tokens.output"] == 5
    assert span.attributes["llm.tokens.total"] == 15


def test_openai_records_cost(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[])

    span = exporter.spans[0]
    expected = _estimate_cost("gpt-4o", 10, 5)
    assert span.attributes["llm.cost_usd"] == expected
    assert expected > 0


def test_openai_records_prompt(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(
        None,
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )

    span = exporter.spans[0]
    assert '"role": "user"' in span.attributes["llm.prompt"]
    assert '"content": "Hello"' in span.attributes["llm.prompt"]


def test_openai_records_completion(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[])

    span = exporter.spans[0]
    assert span.attributes["llm.completion"] == "Hello!"


def test_openai_records_finish_reason(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[])

    span = exporter.spans[0]
    assert span.attributes["llm.finish_reason"] == "stop"


def test_openai_records_error_status(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(
        _make_fake_original(error=RuntimeError("API connection failed"))
    )

    with pytest.raises(RuntimeError, match="API connection failed"):
        wrapper(None, model="gpt-4o", messages=[])

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "API connection failed"


def test_openai_captures_temperature_and_max_tokens(
    exporter: InMemoryExporter,
) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[], temperature=0.7, max_tokens=100)

    span = exporter.spans[0]
    assert span.attributes["llm.temperature"] == 0.7
    assert span.attributes["llm.max_tokens"] == 100


# --- Streaming tests ---


def test_openai_stream_creates_span(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_openai_chunk(content="Hello"),
        _make_openai_chunk(content=" world"),
        _make_openai_chunk(content="!"),
        _make_openai_chunk(finish_reason="stop"),
    ]
    mock_stream = MockOpenAIStream(chunks)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(None, model="gpt-4o", messages=[], stream=True)
    assert isinstance(result, OpenAIStreamWrapper)

    collected = list(result)
    assert len(collected) == 4

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "openai.chat.completions"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello world!"
    assert span.attributes["llm.finish_reason"] == "stop"


def test_openai_stream_captures_usage(exporter: InMemoryExporter) -> None:
    usage = SimpleNamespace(prompt_tokens=20, completion_tokens=10, total_tokens=30)
    chunks = [
        _make_openai_chunk(content="Hi"),
        _make_openai_chunk(finish_reason="stop", usage=usage),
    ]
    mock_stream = MockOpenAIStream(chunks)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(None, model="gpt-4o", messages=[], stream=True)
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 20
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 30
    assert span.attributes["llm.cost_usd"] == _estimate_cost("gpt-4o", 20, 10)


def test_openai_stream_no_usage(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_openai_chunk(content="Hi"),
        _make_openai_chunk(finish_reason="stop"),
    ]
    mock_stream = MockOpenAIStream(chunks)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(None, model="gpt-4o", messages=[], stream=True)
    list(result)

    span = exporter.spans[0]
    assert "llm.tokens.input" not in span.attributes
    assert "llm.tokens.output" not in span.attributes
    assert "llm.cost_usd" not in span.attributes


def test_openai_stream_error_midstream(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_openai_chunk(content="Hello"),
        _make_openai_chunk(content=" world"),
    ]
    error_stream = MockErrorStream(chunks, RuntimeError("Connection lost"))
    wrapper = _patched_create_fn(_make_fake_original(stream=error_stream))

    result = wrapper(None, model="gpt-4o", messages=[], stream=True)

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


def test_openai_stream_context_manager(exporter: InMemoryExporter) -> None:
    chunks = [
        _make_openai_chunk(content="one"),
        _make_openai_chunk(content="two"),
        _make_openai_chunk(content="three"),
    ]
    mock_stream = MockOpenAIStream(chunks)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(None, model="gpt-4o", messages=[], stream=True)
    with result:
        first = next(result)
        assert first.choices[0].delta.content == "one"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "one"


def test_openai_stream_records_prompt_and_model(
    exporter: InMemoryExporter,
) -> None:
    chunks = [_make_openai_chunk(content="Hi", finish_reason="stop")]
    mock_stream = MockOpenAIStream(chunks)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        stream=True,
    )
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.provider"] == "openai"
    assert span.attributes["llm.model"] == "gpt-4o-mini"
    assert '"role": "user"' in span.attributes["llm.prompt"]


def test_openai_cost_estimation() -> None:
    assert _estimate_cost("gpt-4o", 1000, 1000) > 0
    assert _estimate_cost("gpt-4o-mini", 1000, 1000) > 0
    assert _estimate_cost("unknown-model", 1000, 1000) == 0.0


# --- Async streaming tests ---


class MockAsyncOpenAIStream:
    """Mock async OpenAI stream that yields chunks."""

    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = iter(chunks)

    def __aiter__(self) -> MockAsyncOpenAIStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise StopAsyncIteration from None

    async def __aenter__(self) -> MockAsyncOpenAIStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class MockAsyncErrorStream:
    """Mock async stream that raises an error after yielding some chunks."""

    def __init__(
        self, chunks: list[SimpleNamespace], error: Exception
    ) -> None:
        self._chunks = iter(chunks)
        self._error = error

    def __aiter__(self) -> MockAsyncErrorStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._chunks)
        except StopIteration:
            raise self._error from None

    async def __aenter__(self) -> MockAsyncErrorStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


def _make_fake_async_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
    stream: MockAsyncOpenAIStream | MockAsyncErrorStream | None = None,
) -> Any:
    """Create a fake original async create function."""

    async def fake_create(self: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        if kwargs.get("stream"):
            if stream is not None:
                return stream
            return MockAsyncOpenAIStream([])
        return response or _make_mock_response(model=kwargs.get("model", "gpt-4o"))

    return fake_create


async def test_openai_async_stream_creates_span(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_openai_chunk(content="Hello"),
        _make_openai_chunk(content=" async"),
        _make_openai_chunk(content="!"),
        _make_openai_chunk(finish_reason="stop"),
    ]
    mock_stream = MockAsyncOpenAIStream(chunks)
    wrapper = _patched_async_create_fn(_make_fake_async_original(stream=mock_stream))

    result = await wrapper(None, model="gpt-4o", messages=[], stream=True)
    assert isinstance(result, OpenAIAsyncStreamWrapper)

    collected = [chunk async for chunk in result]
    assert len(collected) == 4

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "openai.chat.completions"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello async!"
    assert span.attributes["llm.finish_reason"] == "stop"


async def test_openai_async_stream_captures_usage(
    exporter: InMemoryExporter,
) -> None:
    usage = SimpleNamespace(prompt_tokens=20, completion_tokens=10, total_tokens=30)
    chunks = [
        _make_openai_chunk(content="Hi"),
        _make_openai_chunk(finish_reason="stop", usage=usage),
    ]
    mock_stream = MockAsyncOpenAIStream(chunks)
    wrapper = _patched_async_create_fn(_make_fake_async_original(stream=mock_stream))

    result = await wrapper(None, model="gpt-4o", messages=[], stream=True)
    async for _ in result:
        pass

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 20
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 30
    assert span.attributes["llm.cost_usd"] == _estimate_cost("gpt-4o", 20, 10)


async def test_openai_async_stream_error_midstream(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_openai_chunk(content="Hello"),
        _make_openai_chunk(content=" world"),
    ]
    error_stream = MockAsyncErrorStream(chunks, RuntimeError("Async connection lost"))
    wrapper = _patched_async_create_fn(
        _make_fake_async_original(stream=error_stream)
    )

    result = await wrapper(None, model="gpt-4o", messages=[], stream=True)

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


async def test_openai_async_stream_context_manager(
    exporter: InMemoryExporter,
) -> None:
    chunks = [
        _make_openai_chunk(content="one"),
        _make_openai_chunk(content="two"),
        _make_openai_chunk(content="three"),
    ]
    mock_stream = MockAsyncOpenAIStream(chunks)
    wrapper = _patched_async_create_fn(_make_fake_async_original(stream=mock_stream))

    result = await wrapper(None, model="gpt-4o", messages=[], stream=True)
    async with result:
        first = await result.__anext__()
        assert first.choices[0].delta.content == "one"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "one"
