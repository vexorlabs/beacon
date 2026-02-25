"""Tests for the Ollama auto-instrumentation integration."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import ollama as ollama_patch
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None
    from beacon_sdk.context import _trace_context

    _trace_context.set(None)


# ---------------------------------------------------------------------------
# Fake Ollama functions / classes
# ---------------------------------------------------------------------------


def fake_chat(model: str = "", messages: Any = None, **kwargs: Any) -> dict[str, Any]:
    if kwargs.get("_should_error"):
        raise RuntimeError("Ollama chat failed")
    return {
        "model": model or "llama3.2",
        "message": {"role": "assistant", "content": "Hello from Ollama!"},
        "prompt_eval_count": 25,
        "eval_count": 15,
        "total_duration": 1_500_000_000,
    }


def fake_generate(model: str = "", prompt: str = "", **kwargs: Any) -> dict[str, Any]:
    if kwargs.get("_should_error"):
        raise RuntimeError("Ollama generate failed")
    return {
        "model": model or "llama3.2",
        "response": "Generated text from Ollama.",
        "prompt_eval_count": 10,
        "eval_count": 20,
        "total_duration": 2_000_000_000,
    }


class FakeAsyncClient:
    async def chat(self, model: str = "", messages: Any = None, **kwargs: Any) -> dict[str, Any]:
        return {
            "model": model or "llama3.2",
            "message": {"role": "assistant", "content": "Async hello!"},
            "prompt_eval_count": 30,
            "eval_count": 10,
        }

    async def generate(self, model: str = "", prompt: str = "", **kwargs: Any) -> dict[str, Any]:
        return {
            "model": model or "llama3.2",
            "response": "Async generated text.",
            "prompt_eval_count": 15,
            "eval_count": 25,
        }


@pytest.fixture()
def _mock_ollama() -> Any:
    ollama_mod = SimpleNamespace(
        chat=fake_chat,
        generate=fake_generate,
        AsyncClient=FakeAsyncClient,
    )
    with mock_patch.dict("sys.modules", {"ollama": ollama_mod}):
        ollama_patch._patched = False
        ollama_patch._original_chat = None
        ollama_patch._original_generate = None
        ollama_patch._original_async_chat = None
        ollama_patch._original_async_generate = None
        yield ollama_mod
        ollama_patch.unpatch()
        ollama_patch._patched = False


# ---------------------------------------------------------------------------
# Patch / unpatch mechanics
# ---------------------------------------------------------------------------


class TestPatchMechanics:
    def test_patch_is_idempotent(self, _mock_ollama: Any) -> None:
        ollama_patch.patch()
        first_fn = _mock_ollama.chat
        ollama_patch.patch()
        assert _mock_ollama.chat is first_fn

    def test_unpatch_restores_original(self, _mock_ollama: Any) -> None:
        ollama_patch.patch()
        assert _mock_ollama.chat is not fake_chat
        ollama_patch.unpatch()
        assert _mock_ollama.chat is fake_chat

    def test_patch_skips_when_not_installed(self) -> None:
        ollama_patch._patched = False
        with mock_patch.dict("sys.modules", {}, clear=False):
            import sys

            sys.modules.pop("ollama", None)
            ollama_patch.patch()
            assert ollama_patch._patched is False


# ---------------------------------------------------------------------------
# ollama.chat spans
# ---------------------------------------------------------------------------


class TestChat:
    def test_chat_creates_llm_call_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        result = _mock_ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result["message"]["content"] == "Hello from Ollama!"
        spans = [s for s in exporter.spans if s.name.startswith("ollama.chat")]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.LLM_CALL
        assert span.attributes["llm.provider"] == "ollama"
        assert span.attributes["llm.model"] == "llama3.2"
        assert span.attributes["llm.completion"] == "Hello from Ollama!"
        assert span.attributes["llm.tokens.input"] == 25
        assert span.attributes["llm.tokens.output"] == 15
        assert span.attributes["llm.tokens.total"] == 40
        assert span.status == SpanStatus.OK

    def test_chat_records_prompt(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        messages = [{"role": "user", "content": "What is AI?"}]
        _mock_ollama.chat(model="llama3.2", messages=messages)

        span = next(s for s in exporter.spans if s.name.startswith("ollama.chat"))
        assert "What is AI?" in span.attributes["llm.prompt"]

    def test_chat_stream_passthrough(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        """Streaming calls should pass through without instrumentation."""
        ollama_patch.patch()
        result = _mock_ollama.chat(model="llama3.2", stream=True)
        # Still returns the fake response (our fake doesn't actually stream)
        assert result["message"]["content"] == "Hello from Ollama!"
        assert len(exporter.spans) == 0

    def test_chat_without_tracer(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        beacon_sdk._tracer = None
        result = _mock_ollama.chat(model="llama3.2")
        assert result["message"]["content"] == "Hello from Ollama!"
        assert len(exporter.spans) == 0


# ---------------------------------------------------------------------------
# ollama.generate spans
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_generate_creates_llm_call_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        result = _mock_ollama.generate(model="llama3.2", prompt="Tell me a joke")

        assert result["response"] == "Generated text from Ollama."
        spans = [s for s in exporter.spans if s.name.startswith("ollama.generate")]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.LLM_CALL
        assert span.attributes["llm.provider"] == "ollama"
        assert span.attributes["llm.prompt"] == "Tell me a joke"
        assert span.attributes["llm.completion"] == "Generated text from Ollama."
        assert span.attributes["llm.tokens.input"] == 10
        assert span.attributes["llm.tokens.output"] == 20
        assert span.attributes["llm.tokens.total"] == 30
        assert span.status == SpanStatus.OK

    def test_generate_records_duration(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        _mock_ollama.generate(model="llama3.2", prompt="test")

        span = next(s for s in exporter.spans if s.name.startswith("ollama.generate"))
        assert span.attributes["ollama.total_duration_ns"] == 2_000_000_000


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrors:
    def test_chat_error_creates_error_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        with pytest.raises(RuntimeError, match="Ollama chat failed"):
            _mock_ollama.chat(model="llama3.2", _should_error=True)

        error_spans = [
            s
            for s in exporter.spans
            if s.name.startswith("ollama.chat") and s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1
        assert "Ollama chat failed" in (error_spans[0].error_message or "")

    def test_generate_error_creates_error_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        with pytest.raises(RuntimeError, match="Ollama generate failed"):
            _mock_ollama.generate(model="llama3.2", _should_error=True)

        error_spans = [
            s
            for s in exporter.spans
            if s.name.startswith("ollama.generate") and s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1
        assert "Ollama generate failed" in (error_spans[0].error_message or "")


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class TestAsyncClient:
    def test_async_chat_creates_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        client = FakeAsyncClient()

        result = asyncio.run(client.chat(model="llama3.2", messages=[]))

        assert result["message"]["content"] == "Async hello!"
        spans = [s for s in exporter.spans if s.name.startswith("ollama.chat")]
        assert len(spans) == 1
        assert spans[0].attributes["llm.completion"] == "Async hello!"

    def test_async_generate_creates_span(
        self, _mock_ollama: Any, exporter: InMemoryExporter
    ) -> None:
        ollama_patch.patch()
        client = FakeAsyncClient()

        result = asyncio.run(client.generate(model="llama3.2", prompt="test"))

        assert result["response"] == "Async generated text."
        spans = [s for s in exporter.spans if s.name.startswith("ollama.generate")]
        assert len(spans) == 1
        assert spans[0].attributes["llm.completion"] == "Async generated text."
