"""Tests for the Anthropic auto-instrumentation integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations.anthropic import (
    AnthropicAsyncStreamWrapper,
    AnthropicStreamWrapper,
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
    text: str = "Hello!",
    model: str = "claude-sonnet-4-6-20250514",
    input_tokens: int = 10,
    output_tokens: int = 5,
    stop_reason: str = "end_turn",
) -> SimpleNamespace:
    """Create a mock Anthropic message response."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        model=model,
        stop_reason=stop_reason,
    )


def _make_anthropic_events(
    text_chunks: list[str],
    input_tokens: int = 25,
    output_tokens: int = 10,
    stop_reason: str = "end_turn",
) -> list[SimpleNamespace]:
    """Build a full Anthropic streaming event sequence."""
    events: list[SimpleNamespace] = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=input_tokens),
            ),
        ),
        SimpleNamespace(type="content_block_start", index=0),
    ]
    for text in text_chunks:
        events.append(
            SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(type="text_delta", text=text),
            )
        )
    events.append(SimpleNamespace(type="content_block_stop", index=0))
    events.append(
        SimpleNamespace(
            type="message_delta",
            delta=SimpleNamespace(stop_reason=stop_reason),
            usage=SimpleNamespace(output_tokens=output_tokens),
        )
    )
    events.append(SimpleNamespace(type="message_stop"))
    return events


class MockAnthropicStream:
    """Mock Anthropic stream that yields events."""

    def __init__(self, events: list[SimpleNamespace]) -> None:
        self._events = iter(events)

    def __iter__(self) -> MockAnthropicStream:
        return self

    def __next__(self) -> SimpleNamespace:
        return next(self._events)

    def __enter__(self) -> MockAnthropicStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class MockErrorAnthropicStream:
    """Mock stream that raises an error after yielding some events."""

    def __init__(
        self, events: list[SimpleNamespace], error: Exception
    ) -> None:
        self._events = iter(events)
        self._error = error

    def __iter__(self) -> MockErrorAnthropicStream:
        return self

    def __next__(self) -> SimpleNamespace:
        try:
            return next(self._events)
        except StopIteration:
            raise self._error from None

    def __enter__(self) -> MockErrorAnthropicStream:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def _make_fake_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
    stream: MockAnthropicStream | MockErrorAnthropicStream | None = None,
) -> Any:
    """Create a fake original create function."""

    def fake_create(self: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        if kwargs.get("stream"):
            if stream is not None:
                return stream
            return MockAnthropicStream([])
        return response or _make_mock_response(
            model=kwargs.get("model", "claude-sonnet-4-6-20250514")
        )

    return fake_create


# --- Non-streaming tests ---


def test_anthropic_creates_llm_call_span(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "anthropic.messages.create"
    assert span.attributes["llm.provider"] == "anthropic"
    assert span.status == SpanStatus.OK


def test_anthropic_records_token_usage(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 10
    assert span.attributes["llm.tokens.output"] == 5
    assert span.attributes["llm.tokens.total"] == 15


def test_anthropic_records_cost(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    expected = _estimate_cost("claude-sonnet-4-6-20250514", 10, 5)
    assert span.attributes["llm.cost_usd"] == expected
    assert expected > 0


def test_anthropic_records_completion(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    assert span.attributes["llm.completion"] == "Hello!"


def test_anthropic_includes_system_in_prompt(
    exporter: InMemoryExporter,
) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        system="You are helpful.",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=100,
    )

    span = exporter.spans[0]
    assert '"role": "system"' in span.attributes["llm.prompt"]
    assert "You are helpful." in span.attributes["llm.prompt"]


def test_anthropic_records_error_status(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original(error=RuntimeError("API error")))

    with pytest.raises(RuntimeError, match="API error"):
        wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "API error"


def test_anthropic_records_finish_reason(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    assert span.attributes["llm.finish_reason"] == "end_turn"


# --- Streaming tests ---


def test_anthropic_stream_creates_span(exporter: InMemoryExporter) -> None:
    events = _make_anthropic_events(["Hello", " world", "!"])
    mock_stream = MockAnthropicStream(events)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    assert isinstance(result, AnthropicStreamWrapper)

    collected = list(result)
    assert len(collected) == len(events)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "anthropic.messages.create"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello world!"


def test_anthropic_stream_captures_tokens(exporter: InMemoryExporter) -> None:
    events = _make_anthropic_events(
        ["Hi"], input_tokens=25, output_tokens=10
    )
    mock_stream = MockAnthropicStream(events)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 25
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 35
    expected_cost = _estimate_cost("claude-sonnet-4-6-20250514", 25, 10)
    assert span.attributes["llm.cost_usd"] == expected_cost
    assert expected_cost > 0


def test_anthropic_stream_captures_finish_reason(
    exporter: InMemoryExporter,
) -> None:
    events = _make_anthropic_events(["Hi"], stop_reason="end_turn")
    mock_stream = MockAnthropicStream(events)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.finish_reason"] == "end_turn"


def test_anthropic_stream_error_midstream(exporter: InMemoryExporter) -> None:
    partial_events = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=10),
            ),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="partial"),
        ),
    ]
    error_stream = MockErrorAnthropicStream(
        partial_events, RuntimeError("Stream interrupted")
    )
    wrapper = _patched_create_fn(_make_fake_original(stream=error_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )

    collected: list[SimpleNamespace] = []
    with pytest.raises(RuntimeError, match="Stream interrupted"):
        for event in result:
            collected.append(event)

    assert len(collected) == 2
    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "Stream interrupted"
    assert span.attributes["llm.completion"] == "partial"


def test_anthropic_stream_context_manager(exporter: InMemoryExporter) -> None:
    events = _make_anthropic_events(["one", "two", "three"])
    mock_stream = MockAnthropicStream(events)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    with result:
        first = next(result)
        assert first.type == "message_start"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK


def test_anthropic_stream_records_prompt_and_model(
    exporter: InMemoryExporter,
) -> None:
    events = _make_anthropic_events(["Hi"])
    mock_stream = MockAnthropicStream(events)
    wrapper = _patched_create_fn(_make_fake_original(stream=mock_stream))

    result = wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100,
        stream=True,
    )
    list(result)

    span = exporter.spans[0]
    assert span.attributes["llm.provider"] == "anthropic"
    assert span.attributes["llm.model"] == "claude-sonnet-4-6-20250514"
    assert '"role": "user"' in span.attributes["llm.prompt"]


def test_anthropic_captures_tool_use_blocks(exporter: InMemoryExporter) -> None:
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="I'll check the weather."),
            SimpleNamespace(
                type="tool_use",
                id="toolu_abc123",
                name="get_weather",
                input={"location": "San Francisco"},
            ),
        ],
        usage=SimpleNamespace(input_tokens=20, output_tokens=15),
        model="claude-sonnet-4-6-20250514",
        stop_reason="tool_use",
    )
    wrapper = _patched_create_fn(_make_fake_original(response=response))
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    import json

    tool_calls = json.loads(span.attributes["llm.tool_calls"])
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_weather"
    assert tool_calls[0]["id"] == "toolu_abc123"
    assert tool_calls[0]["input"] == {"location": "San Francisco"}
    assert span.attributes["llm.completion"] == "I'll check the weather."


def test_anthropic_no_tool_calls_when_text_only(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], max_tokens=100)

    span = exporter.spans[0]
    assert "llm.tool_calls" not in span.attributes


def test_anthropic_cost_estimation() -> None:
    assert _estimate_cost("claude-sonnet-4-6-20250514", 1000, 1000) > 0
    assert _estimate_cost("claude-opus-4-6-20250514", 1000, 1000) > 0
    assert _estimate_cost("unknown-model", 1000, 1000) == 0.0


# --- Async streaming tests ---


class MockAsyncAnthropicStream:
    """Mock async Anthropic stream that yields events."""

    def __init__(self, events: list[SimpleNamespace]) -> None:
        self._events = iter(events)

    def __aiter__(self) -> MockAsyncAnthropicStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._events)
        except StopIteration:
            raise StopAsyncIteration from None

    async def __aenter__(self) -> MockAsyncAnthropicStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class MockAsyncErrorAnthropicStream:
    """Mock async stream that raises an error after yielding some events."""

    def __init__(
        self, events: list[SimpleNamespace], error: Exception
    ) -> None:
        self._events = iter(events)
        self._error = error

    def __aiter__(self) -> MockAsyncErrorAnthropicStream:
        return self

    async def __anext__(self) -> SimpleNamespace:
        try:
            return next(self._events)
        except StopIteration:
            raise self._error from None

    async def __aenter__(self) -> MockAsyncErrorAnthropicStream:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


def _make_fake_async_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
    stream: MockAsyncAnthropicStream | MockAsyncErrorAnthropicStream | None = None,
) -> Any:
    """Create a fake original async create function."""

    async def fake_create(self: Any, **kwargs: Any) -> Any:
        if error is not None:
            raise error
        if kwargs.get("stream"):
            if stream is not None:
                return stream
            return MockAsyncAnthropicStream([])
        return response or _make_mock_response(
            model=kwargs.get("model", "claude-sonnet-4-6-20250514")
        )

    return fake_create


async def test_anthropic_async_stream_creates_span(
    exporter: InMemoryExporter,
) -> None:
    events = _make_anthropic_events(["Hello", " async", "!"])
    mock_stream = MockAsyncAnthropicStream(events)
    wrapper = _patched_async_create_fn(
        _make_fake_async_original(stream=mock_stream)
    )

    result = await wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    assert isinstance(result, AnthropicAsyncStreamWrapper)

    collected = [event async for event in result]
    assert len(collected) == len(events)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "anthropic.messages.create"
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "Hello async!"


async def test_anthropic_async_stream_captures_tokens(
    exporter: InMemoryExporter,
) -> None:
    events = _make_anthropic_events(
        ["Hi"], input_tokens=25, output_tokens=10
    )
    mock_stream = MockAsyncAnthropicStream(events)
    wrapper = _patched_async_create_fn(
        _make_fake_async_original(stream=mock_stream)
    )

    result = await wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    async for _ in result:
        pass

    span = exporter.spans[0]
    assert span.attributes["llm.tokens.input"] == 25
    assert span.attributes["llm.tokens.output"] == 10
    assert span.attributes["llm.tokens.total"] == 35
    expected_cost = _estimate_cost("claude-sonnet-4-6-20250514", 25, 10)
    assert span.attributes["llm.cost_usd"] == expected_cost
    assert expected_cost > 0


async def test_anthropic_async_stream_error_midstream(
    exporter: InMemoryExporter,
) -> None:
    partial_events = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=10),
            ),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="partial"),
        ),
    ]
    error_stream = MockAsyncErrorAnthropicStream(
        partial_events, RuntimeError("Async stream interrupted")
    )
    wrapper = _patched_async_create_fn(
        _make_fake_async_original(stream=error_stream)
    )

    result = await wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )

    collected: list[SimpleNamespace] = []
    with pytest.raises(RuntimeError, match="Async stream interrupted"):
        async for event in result:
            collected.append(event)

    assert len(collected) == 2
    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "Async stream interrupted"
    assert span.attributes["llm.completion"] == "partial"


async def test_anthropic_async_stream_context_manager(
    exporter: InMemoryExporter,
) -> None:
    events = _make_anthropic_events(["one", "two", "three"])
    mock_stream = MockAsyncAnthropicStream(events)
    wrapper = _patched_async_create_fn(
        _make_fake_async_original(stream=mock_stream)
    )

    result = await wrapper(
        None,
        model="claude-sonnet-4-6-20250514",
        messages=[],
        max_tokens=100,
        stream=True,
    )
    async with result:
        first = await result.__anext__()
        assert first.type == "message_start"

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
