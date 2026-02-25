"""Tests for the LlamaIndex auto-instrumentation integration."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import llamaindex as llamaindex_patch
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
# Fake LlamaIndex classes
# ---------------------------------------------------------------------------


class FakeNodeWithScore:
    def __init__(self, node_id: str = "node_1", score: float = 0.95) -> None:
        self.node_id = node_id
        self.score = score
        self.node = SimpleNamespace(node_id=node_id)


class FakeResponse:
    def __init__(
        self,
        response: str = "The answer is 42.",
        source_nodes: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.response = response
        self.source_nodes = source_nodes or [
            FakeNodeWithScore("node_1", 0.95),
            FakeNodeWithScore("node_2", 0.82),
        ]
        self.metadata = metadata or {"query_engine": "vector"}


class FakeBaseQueryEngine:
    """Simulates llama_index.core.base.base_query_engine.BaseQueryEngine."""

    should_error: bool = False

    def query(self, str_or_query_bundle: Any, **kwargs: Any) -> FakeResponse:
        if self.should_error:
            raise RuntimeError("Query engine failed")
        return FakeResponse()

    async def aquery(self, str_or_query_bundle: Any, **kwargs: Any) -> FakeResponse:
        if self.should_error:
            raise RuntimeError("Async query failed")
        return FakeResponse(response="Async answer is 42.")


class FakeBaseRetriever:
    """Simulates llama_index.core.base.base_retriever.BaseRetriever."""

    should_error: bool = False

    def retrieve(self, str_or_query_bundle: Any, **kwargs: Any) -> list[FakeNodeWithScore]:
        if self.should_error:
            raise RuntimeError("Retriever failed")
        return [
            FakeNodeWithScore("doc_1", 0.98),
            FakeNodeWithScore("doc_2", 0.91),
            FakeNodeWithScore("doc_3", 0.85),
        ]

    async def aretrieve(self, str_or_query_bundle: Any, **kwargs: Any) -> list[FakeNodeWithScore]:
        if self.should_error:
            raise RuntimeError("Async retrieval failed")
        return [FakeNodeWithScore("async_doc", 0.93)]


def _build_mock_modules() -> dict[str, Any]:
    """Build the fake llama_index module hierarchy."""
    base_query_engine = SimpleNamespace(BaseQueryEngine=FakeBaseQueryEngine)
    base_retriever = SimpleNamespace(BaseRetriever=FakeBaseRetriever)
    base_mod = SimpleNamespace(
        base_query_engine=base_query_engine,
        base_retriever=base_retriever,
    )
    core_mod = SimpleNamespace(base=base_mod)
    llama_index = SimpleNamespace(core=core_mod)
    return {
        "llama_index": llama_index,
        "llama_index.core": core_mod,
        "llama_index.core.base": base_mod,
        "llama_index.core.base.base_query_engine": base_query_engine,
        "llama_index.core.base.base_retriever": base_retriever,
    }


@pytest.fixture()
def _mock_llamaindex() -> Any:
    modules = _build_mock_modules()
    with mock_patch.dict("sys.modules", modules):
        llamaindex_patch._patched = False
        llamaindex_patch._original_query = None
        llamaindex_patch._original_aquery = None
        llamaindex_patch._original_retrieve = None
        llamaindex_patch._original_aretrieve = None
        yield modules
        llamaindex_patch.unpatch()
        llamaindex_patch._patched = False


# ---------------------------------------------------------------------------
# Patch / unpatch mechanics
# ---------------------------------------------------------------------------


class TestPatchMechanics:
    def test_patch_is_idempotent(self, _mock_llamaindex: Any) -> None:
        llamaindex_patch.patch()
        first_fn = FakeBaseQueryEngine.query
        llamaindex_patch.patch()
        assert FakeBaseQueryEngine.query is first_fn

    def test_unpatch_restores_original(self, _mock_llamaindex: Any) -> None:
        original_query = FakeBaseQueryEngine.query
        original_retrieve = FakeBaseRetriever.retrieve
        llamaindex_patch.patch()
        assert FakeBaseQueryEngine.query is not original_query
        assert FakeBaseRetriever.retrieve is not original_retrieve
        llamaindex_patch.unpatch()
        assert FakeBaseQueryEngine.query is original_query
        assert FakeBaseRetriever.retrieve is original_retrieve

    def test_patch_skips_when_not_installed(self) -> None:
        llamaindex_patch._patched = False
        with mock_patch.dict("sys.modules", {}, clear=False):
            import sys

            sys.modules.pop("llama_index", None)
            sys.modules.pop("llama_index.core", None)
            sys.modules.pop("llama_index.core.base", None)
            sys.modules.pop("llama_index.core.base.base_query_engine", None)
            sys.modules.pop("llama_index.core.base.base_retriever", None)
            llamaindex_patch.patch()
            assert llamaindex_patch._patched is False


# ---------------------------------------------------------------------------
# Query spans
# ---------------------------------------------------------------------------


class TestQuery:
    def test_query_creates_chain_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        engine = FakeBaseQueryEngine()
        result = engine.query("What is the meaning of life?")

        assert result.response == "The answer is 42."
        spans = [s for s in exporter.spans if s.name.startswith("query:")]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.CHAIN
        assert span.attributes["agent.framework"] == "llamaindex"
        assert span.attributes["agent.input"] == "What is the meaning of life?"
        assert span.attributes["llamaindex.engine"] == "FakeBaseQueryEngine"
        assert span.status == SpanStatus.OK

    def test_query_extracts_response(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        engine = FakeBaseQueryEngine()
        engine.query("test query")

        span = next(s for s in exporter.spans if s.name.startswith("query:"))
        assert span.attributes["agent.output"] == "The answer is 42."
        assert span.attributes["llamaindex.source_node_count"] == 2
        sources = json.loads(span.attributes["llamaindex.sources"])
        assert len(sources) == 2
        assert sources[0]["node_id"] == "node_1"
        assert sources[0]["score"] == 0.95

    def test_query_error_creates_error_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        engine = FakeBaseQueryEngine()
        engine.should_error = True

        with pytest.raises(RuntimeError, match="Query engine failed"):
            engine.query("will fail")

        error_spans = [
            s for s in exporter.spans if s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1
        assert "Query engine failed" in (error_spans[0].error_message or "")

    def test_query_without_tracer(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        beacon_sdk._tracer = None
        engine = FakeBaseQueryEngine()
        result = engine.query("test")
        assert result.response == "The answer is 42."
        assert len(exporter.spans) == 0


# ---------------------------------------------------------------------------
# Retrieve spans
# ---------------------------------------------------------------------------


class TestRetrieve:
    def test_retrieve_creates_tool_use_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        retriever = FakeBaseRetriever()
        result = retriever.retrieve("search for docs")

        assert len(result) == 3
        spans = [s for s in exporter.spans if s.name.startswith("retrieve:")]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.TOOL_USE
        assert span.attributes["agent.framework"] == "llamaindex"
        assert span.attributes["tool.name"] == "FakeBaseRetriever"
        assert span.attributes["tool.input"] == "search for docs"
        assert span.attributes["llamaindex.retrieved_count"] == 3
        assert span.status == SpanStatus.OK

    def test_retrieve_error_creates_error_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        retriever = FakeBaseRetriever()
        retriever.should_error = True

        with pytest.raises(RuntimeError, match="Retriever failed"):
            retriever.retrieve("will fail")

        error_spans = [s for s in exporter.spans if s.status == SpanStatus.ERROR]
        assert len(error_spans) == 1


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


class TestAsync:
    def test_aquery_creates_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        engine = FakeBaseQueryEngine()

        result = asyncio.run(engine.aquery("async question"))

        assert result.response == "Async answer is 42."
        spans = [s for s in exporter.spans if s.name.startswith("query:")]
        assert len(spans) == 1
        assert spans[0].status == SpanStatus.OK
        assert spans[0].attributes["agent.output"] == "Async answer is 42."

    def test_aretrieve_creates_span(
        self, _mock_llamaindex: Any, exporter: InMemoryExporter
    ) -> None:
        llamaindex_patch.patch()
        retriever = FakeBaseRetriever()

        result = asyncio.run(retriever.aretrieve("async search"))

        assert len(result) == 1
        spans = [s for s in exporter.spans if s.name.startswith("retrieve:")]
        assert len(spans) == 1
        assert spans[0].attributes["llamaindex.retrieved_count"] == 1
