"""LlamaIndex auto-instrumentation. Patches core query/retrieval/LLM methods for tracing."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_query: Any = None
_original_aquery: Any = None
_original_retrieve: Any = None
_original_aretrieve: Any = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_str(obj: Any, max_len: int = 50_000) -> str:
    """Convert an object to a truncated string."""
    try:
        if isinstance(obj, str):
            return obj[:max_len]
        return json.dumps(obj, default=str)[:max_len]
    except Exception:
        return str(obj)[:max_len]


def _extract_response_attrs(response: Any) -> dict[str, Any]:
    """Extract useful attributes from a LlamaIndex response object."""
    attrs: dict[str, Any] = {}

    # Response text
    text = getattr(response, "response", None) or getattr(response, "text", None)
    if text is not None:
        attrs["agent.output"] = _safe_str(text)

    # Source nodes (retrieval results)
    source_nodes = getattr(response, "source_nodes", None)
    if source_nodes:
        attrs["llamaindex.source_node_count"] = len(source_nodes)
        sources = []
        for node in source_nodes[:10]:  # Cap at 10 to avoid huge attributes
            score = getattr(node, "score", None)
            node_id = getattr(node, "node_id", None) or getattr(
                getattr(node, "node", None), "node_id", None
            )
            sources.append({"node_id": node_id, "score": score})
        attrs["llamaindex.sources"] = json.dumps(sources, default=str)

    # Metadata
    metadata = getattr(response, "metadata", None)
    if metadata and isinstance(metadata, dict):
        attrs["llamaindex.metadata"] = json.dumps(metadata, default=str)[:10_000]

    return attrs


# ---------------------------------------------------------------------------
# Patched function factories
# ---------------------------------------------------------------------------


def _make_query_wrapper(original: Any) -> Any:
    """Create a sync wrapper around BaseQueryEngine.query."""

    def wrapper(self: Any, str_or_query_bundle: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, str_or_query_bundle, **kwargs)

        query_str = str(str_or_query_bundle)
        engine_name = type(self).__name__

        span, token = tracer.start_span(
            name=f"query: {engine_name}",
            span_type=SpanType.CHAIN,
            attributes={
                "agent.framework": "llamaindex",
                "agent.input": query_str[:50_000],
                "llamaindex.engine": engine_name,
            },
        )
        try:
            result = original(self, str_or_query_bundle, **kwargs)
            for k, v in _extract_response_attrs(result).items():
                span.set_attribute(k, v)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_aquery_wrapper(original: Any) -> Any:
    """Create an async wrapper around BaseQueryEngine.aquery."""

    async def wrapper(self: Any, str_or_query_bundle: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, str_or_query_bundle, **kwargs)

        query_str = str(str_or_query_bundle)
        engine_name = type(self).__name__

        span, token = tracer.start_span(
            name=f"query: {engine_name}",
            span_type=SpanType.CHAIN,
            attributes={
                "agent.framework": "llamaindex",
                "agent.input": query_str[:50_000],
                "llamaindex.engine": engine_name,
            },
        )
        try:
            result = await original(self, str_or_query_bundle, **kwargs)
            for k, v in _extract_response_attrs(result).items():
                span.set_attribute(k, v)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_retrieve_wrapper(original: Any) -> Any:
    """Create a sync wrapper around BaseRetriever.retrieve."""

    def wrapper(self: Any, str_or_query_bundle: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, str_or_query_bundle, **kwargs)

        query_str = str(str_or_query_bundle)
        retriever_name = type(self).__name__

        span, token = tracer.start_span(
            name=f"retrieve: {retriever_name}",
            span_type=SpanType.TOOL_USE,
            attributes={
                "agent.framework": "llamaindex",
                "tool.name": retriever_name,
                "tool.input": query_str[:50_000],
            },
        )
        try:
            result = original(self, str_or_query_bundle, **kwargs)
            if result is not None:
                span.set_attribute("llamaindex.retrieved_count", len(result))
                nodes_summary = []
                for node in result[:10]:
                    score = getattr(node, "score", None)
                    node_id = getattr(node, "node_id", None) or getattr(
                        getattr(node, "node", None), "node_id", None
                    )
                    nodes_summary.append({"node_id": node_id, "score": score})
                span.set_attribute(
                    "tool.output", json.dumps(nodes_summary, default=str)[:50_000]
                )
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_aretrieve_wrapper(original: Any) -> Any:
    """Create an async wrapper around BaseRetriever.aretrieve."""

    async def wrapper(self: Any, str_or_query_bundle: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, str_or_query_bundle, **kwargs)

        query_str = str(str_or_query_bundle)
        retriever_name = type(self).__name__

        span, token = tracer.start_span(
            name=f"retrieve: {retriever_name}",
            span_type=SpanType.TOOL_USE,
            attributes={
                "agent.framework": "llamaindex",
                "tool.name": retriever_name,
                "tool.input": query_str[:50_000],
            },
        )
        try:
            result = await original(self, str_or_query_bundle, **kwargs)
            if result is not None:
                span.set_attribute("llamaindex.retrieved_count", len(result))
                nodes_summary = []
                for node in result[:10]:
                    score = getattr(node, "score", None)
                    node_id = getattr(node, "node_id", None) or getattr(
                        getattr(node, "node", None), "node_id", None
                    )
                    nodes_summary.append({"node_id": node_id, "score": score})
                span.set_attribute(
                    "tool.output", json.dumps(nodes_summary, default=str)[:50_000]
                )
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def patch() -> None:
    """Monkey-patch LlamaIndex classes to auto-instrument queries and retrieval."""
    global _patched, _original_query, _original_aquery
    global _original_retrieve, _original_aretrieve

    if _patched:
        return

    try:
        from llama_index.core.base.base_query_engine import BaseQueryEngine
        from llama_index.core.base.base_retriever import BaseRetriever
    except ImportError:
        return

    _original_query = BaseQueryEngine.query
    BaseQueryEngine.query = _make_query_wrapper(_original_query)

    if hasattr(BaseQueryEngine, "aquery"):
        _original_aquery = BaseQueryEngine.aquery
        BaseQueryEngine.aquery = _make_aquery_wrapper(_original_aquery)

    _original_retrieve = BaseRetriever.retrieve
    BaseRetriever.retrieve = _make_retrieve_wrapper(_original_retrieve)

    if hasattr(BaseRetriever, "aretrieve"):
        _original_aretrieve = BaseRetriever.aretrieve
        BaseRetriever.aretrieve = _make_aretrieve_wrapper(_original_aretrieve)

    _patched = True
    logger.debug("Beacon: LlamaIndex auto-patch applied")


def unpatch() -> None:
    """Restore original LlamaIndex methods."""
    global _patched, _original_query, _original_aquery
    global _original_retrieve, _original_aretrieve

    if not _patched:
        return

    try:
        from llama_index.core.base.base_query_engine import BaseQueryEngine
        from llama_index.core.base.base_retriever import BaseRetriever
    except ImportError:
        return

    if _original_query is not None:
        BaseQueryEngine.query = _original_query
    if _original_aquery is not None and hasattr(BaseQueryEngine, "aquery"):
        BaseQueryEngine.aquery = _original_aquery
    if _original_retrieve is not None:
        BaseRetriever.retrieve = _original_retrieve
    if _original_aretrieve is not None and hasattr(BaseRetriever, "aretrieve"):
        BaseRetriever.aretrieve = _original_aretrieve

    _original_query = None
    _original_aquery = None
    _original_retrieve = None
    _original_aretrieve = None
    _patched = False
    logger.debug("Beacon: LlamaIndex auto-patch removed")
