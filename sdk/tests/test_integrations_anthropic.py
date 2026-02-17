"""Tests for the Anthropic auto-instrumentation integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations.anthropic import (
    _estimate_cost,
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


def _make_fake_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original create function."""

    def fake_create(self: Any, **kwargs: Any) -> SimpleNamespace:
        if error is not None:
            raise error
        return response or _make_mock_response(
            model=kwargs.get("model", "claude-sonnet-4-6-20250514")
        )

    return fake_create


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


def test_anthropic_skips_stream(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="claude-sonnet-4-6-20250514", messages=[], stream=True)

    assert len(exporter.spans) == 0


def test_anthropic_cost_estimation() -> None:
    assert _estimate_cost("claude-sonnet-4-6-20250514", 1000, 1000) > 0
    assert _estimate_cost("claude-opus-4-6-20250514", 1000, 1000) > 0
    assert _estimate_cost("unknown-model", 1000, 1000) == 0.0
