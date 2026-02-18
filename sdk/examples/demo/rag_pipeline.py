"""Beacon Demo — RAG Pipeline

Simulates a Retrieval-Augmented Generation pipeline: embed query, vector search,
rerank with fan-out scoring, generate answer, and verify. No API keys needed.

Span tree produced:
    RAG Pipeline (chain)
      ├── embed_query (llm_call, openai/text-embedding-3-small)
      ├── vector_search (tool_use)
      ├── rerank_results (agent_step)
      │     ├── score_chunk_1 (llm_call, openai/gpt-4o-mini)
      │     ├── score_chunk_2 (llm_call, openai/gpt-4o-mini)
      │     └── score_chunk_3 (llm_call, openai/gpt-4o-mini)
      ├── build_context (tool_use)
      ├── generate_answer (llm_call, openai/gpt-4o)
      └── verify_answer (llm_call, openai/gpt-4o)

SDK patterns demonstrated:
    - chain span type (top-level container)
    - 3-level nesting (chain → agent_step → llm_call)
    - Fan-out / fan-in pattern in the graph
    - Embedding model LLM calls
    - tracer.span() context manager
"""

from __future__ import annotations

import json
import time

import beacon_sdk
from beacon_sdk import observe
from beacon_sdk.models import SpanType

from . import _fixtures as F


def _set_llm_attrs(
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    completion: str,
    input_tokens: int,
    output_tokens: int,
    *,
    temperature: float = 0.0,
    finish_reason: str = "stop",
    cost_usd: float | None = None,
) -> None:
    """Helper to set standard LLM attributes on the current span."""
    span = beacon_sdk.get_current_span()
    if span is None:
        return
    span.set_attribute("llm.provider", provider)
    span.set_attribute("llm.model", model)
    span.set_attribute("llm.prompt", json.dumps(messages))
    span.set_attribute("llm.completion", completion)
    span.set_attribute("llm.tokens.input", input_tokens)
    span.set_attribute("llm.tokens.output", output_tokens)
    span.set_attribute("llm.tokens.total", input_tokens + output_tokens)
    span.set_attribute("llm.temperature", temperature)
    span.set_attribute("llm.finish_reason", finish_reason)
    if cost_usd is not None:
        span.set_attribute("llm.cost_usd", cost_usd)
    else:
        span.set_attribute("llm.cost_usd", 0.0)


def _set_tool_attrs(name: str, tool_input: str, tool_output: str) -> None:
    """Helper to set tool_use attributes on the current span."""
    span = beacon_sdk.get_current_span()
    if span is None:
        return
    span.set_attribute("tool.name", name)
    span.set_attribute("tool.input", tool_input)
    span.set_attribute("tool.output", tool_output)


# --- Span functions ---


@observe(name="embed_query", span_type="llm_call")
def embed_query(query: str) -> list[float]:
    time.sleep(0.5)
    _set_llm_attrs(
        provider="openai",
        model="text-embedding-3-small",
        messages=[{"role": "user", "content": query}],
        completion="[0.023, -0.041, 0.087, ...]  (1536 dimensions)",
        input_tokens=28,
        output_tokens=0,
        cost_usd=0.000001,
    )
    return [0.023, -0.041, 0.087]  # truncated for demo


@observe(name="vector_search", span_type="tool_use")
def vector_search(embedding: list[float]) -> str:
    time.sleep(0.3)
    _set_tool_attrs(
        name="vector_db_search",
        tool_input=json.dumps({"embedding_dims": len(embedding), "top_k": 3, "collection": "papers"}),
        tool_output=F.RAG_SEARCH_RESULTS,
    )
    return F.RAG_SEARCH_RESULTS


@observe(name="score_chunk", span_type="llm_call")
def score_chunk(chunk_id: str, chunk_text: str, query: str, completion: str, duration: float) -> str:
    time.sleep(duration)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Rate the relevance of this text chunk to the query. Score 0.0-1.0."},
            {"role": "user", "content": f"Query: {query}\n\nChunk ({chunk_id}):\n{chunk_text[:200]}"},
        ],
        completion=completion,
        input_tokens=145,
        output_tokens=42,
        cost_usd=round(145 * 0.15 / 1_000_000 + 42 * 0.60 / 1_000_000, 6),
    )
    return completion


@observe(name="rerank_results", span_type="agent_step")
def rerank_results(search_results: str, query: str) -> list[str]:
    chunks = json.loads(search_results)
    scores = []
    for i, chunk in enumerate(chunks):
        result = score_chunk(
            chunk_id=chunk["chunk_id"],
            chunk_text=chunk["text"],
            query=query,
            completion=F.RAG_SCORE_COMPLETIONS[i],
            duration=[0.6, 0.5, 0.7][i],
        )
        scores.append(result)
    return scores


@observe(name="build_context", span_type="tool_use")
def build_context(search_results: str, scores: list[str]) -> str:
    time.sleep(0.2)
    _set_tool_attrs(
        name="context_builder",
        tool_input=json.dumps({"num_chunks": 3, "strategy": "ranked_concat"}),
        tool_output=F.RAG_CONTEXT_OUTPUT,
    )
    return F.RAG_CONTEXT_OUTPUT


@observe(name="generate_answer", span_type="llm_call")
def generate_answer(query: str, context: str) -> str:
    time.sleep(2.5)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the user's question based on the provided context. "
                    "Cite sources where applicable."
                ),
            },
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        completion=F.RAG_ANSWER_COMPLETION,
        input_tokens=1567,
        output_tokens=487,
        cost_usd=round(1567 * 5 / 1_000_000 + 487 * 15 / 1_000_000, 6),
    )
    return F.RAG_ANSWER_COMPLETION


@observe(name="verify_answer", span_type="llm_call")
def verify_answer(answer: str, context: str) -> str:
    time.sleep(1.2)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Verify this answer against the source context. "
                    "Check for hallucinations and unsupported claims."
                ),
            },
            {"role": "user", "content": f"Answer:\n{answer}\n\nContext:\n{context}"},
        ],
        completion=F.RAG_VERIFICATION_COMPLETION,
        input_tokens=2034,
        output_tokens=156,
        cost_usd=round(2034 * 5 / 1_000_000 + 156 * 15 / 1_000_000, 6),
    )
    return F.RAG_VERIFICATION_COMPLETION


@observe(name="RAG Pipeline", span_type="chain")
def _rag_pipeline() -> str:
    query = F.RAG_USER_QUERY
    embedding = embed_query(query)
    search_results = vector_search(embedding)
    scores = rerank_results(search_results, query)
    context = build_context(search_results, scores)
    answer = generate_answer(query, context)
    verify_answer(answer, context)
    return answer


def run() -> None:
    """Entry point for the orchestrator."""
    beacon_sdk.init(backend_url="http://localhost:7474", auto_patch=False)
    _rag_pipeline()


if __name__ == "__main__":
    run()
    print("RAG Pipeline demo complete.")
