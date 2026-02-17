"""Tests for the OpenAI auto-instrumentation integration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations.openai import (
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


def _make_fake_original(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> Any:
    """Create a fake original create function."""

    def fake_create(self: Any, **kwargs: Any) -> SimpleNamespace:
        if error is not None:
            raise error
        return response or _make_mock_response(model=kwargs.get("model", "gpt-4o"))

    return fake_create


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


def test_openai_skips_stream(exporter: InMemoryExporter) -> None:
    wrapper = _patched_create_fn(_make_fake_original())
    wrapper(None, model="gpt-4o", messages=[], stream=True)

    assert len(exporter.spans) == 0


def test_openai_cost_estimation() -> None:
    assert _estimate_cost("gpt-4o", 1000, 1000) > 0
    assert _estimate_cost("gpt-4o-mini", 1000, 1000) > 0
    assert _estimate_cost("unknown-model", 1000, 1000) == 0.0
