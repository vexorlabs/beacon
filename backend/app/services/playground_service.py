"""Playground service — orchestrates chat and multi-model comparison.

Creates real traces and spans via the existing span pipeline so
playground interactions are visible in the Debugger tab.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas import (
    CompareResultItem,
    PlaygroundChatMetrics,
    PlaygroundChatRequest,
    PlaygroundChatResponse,
    PlaygroundCompareRequest,
    PlaygroundCompareResponse,
    PlaygroundMessage,
    SpanCreate,
    SpanStatus,
    SpanType,
)
from app.services import settings_service, span_service
from app.services.llm_client import (
    call_anthropic,
    call_openai,
    estimate_cost,
    provider_for_model,
)
from app.ws.manager import ws_manager


async def _broadcast_span(db: Session, span_data: SpanCreate) -> None:
    """Ingest a span into the DB and broadcast via WebSocket."""
    span_service.ingest_spans(db, [span_data])
    orm_span = span_service.get_span_by_id(db, span_data.span_id)
    if orm_span is not None:
        span_dict = span_service.span_to_response(orm_span).model_dump()
        await ws_manager.broadcast_span(span_dict)


async def _broadcast_trace_created(trace_id: str, name: str, start: float) -> None:
    """Notify WS clients of a new trace."""
    await ws_manager.broadcast_trace_created(
        {
            "trace_id": trace_id,
            "name": name,
            "start_time": start,
            "status": "unset",
        }
    )


async def _call_model(
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
) -> tuple[str, int, int, float]:
    """Call a model and return (completion, in_tok, out_tok, latency_ms)."""
    start = time.monotonic()
    if provider == "openai":
        completion, in_tok, out_tok = await call_openai(
            api_key, model, messages
        )
    elif provider == "anthropic":
        completion, in_tok, out_tok = await call_anthropic(
            api_key, model, messages
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    latency_ms = (time.monotonic() - start) * 1000
    return completion, in_tok, out_tok, latency_ms


def _messages_to_dicts(
    messages: list[PlaygroundMessage],
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Convert Pydantic PlaygroundMessage list to plain dicts, prepending system."""
    result: list[dict[str, str]] = []
    if system_prompt:
        result.append({"role": "system", "content": system_prompt})
    for m in messages:
        result.append({"role": m.role, "content": m.content})
    return result


async def chat(
    db: Session,
    request: PlaygroundChatRequest,
) -> PlaygroundChatResponse:
    """Handle a single playground chat turn."""
    provider = provider_for_model(request.model)
    api_key = settings_service.get_api_key(provider)
    if not api_key:
        raise ValueError(
            f"No API key configured for {provider}. "
            "Add one in Settings."
        )

    conversation_id = request.conversation_id or str(uuid4())
    trace_id = conversation_id  # 1 trace per conversation
    now = time.time()

    messages_dicts = _messages_to_dicts(request.messages, request.system_prompt)

    # Create parent agent_step span
    parent_span_id = str(uuid4())
    parent_span = SpanCreate(
        span_id=parent_span_id,
        trace_id=trace_id,
        parent_span_id=None,
        span_type=SpanType.AGENT_STEP,
        name=f"Playground: {request.model}",
        status=SpanStatus.UNSET,
        start_time=now,
        attributes={"playground": True},
    )

    # Broadcast trace_created on first message
    if request.conversation_id is None:
        await _broadcast_trace_created(
            trace_id, f"Playground: {request.model}", now
        )

    await _broadcast_span(db, parent_span)

    # Create llm_call child span (start)
    llm_span_id = str(uuid4())
    llm_span_start = SpanCreate(
        span_id=llm_span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_type=SpanType.LLM_CALL,
        name=f"{request.model}",
        status=SpanStatus.UNSET,
        start_time=now,
        attributes={
            "llm.provider": provider,
            "llm.model": request.model,
            "llm.prompt": json.dumps(messages_dicts),
            "llm.temperature": 1.0,
        },
    )
    await _broadcast_span(db, llm_span_start)

    # Call the LLM
    completion, in_tok, out_tok, latency_ms = await _call_model(
        provider, api_key, request.model, messages_dicts
    )

    cost_usd = estimate_cost(request.model, in_tok, out_tok)
    end_time = time.time()

    # Update llm_call span with response
    llm_span_end = SpanCreate(
        span_id=llm_span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_type=SpanType.LLM_CALL,
        name=f"{request.model}",
        status=SpanStatus.OK,
        start_time=now,
        end_time=end_time,
        attributes={
            "llm.provider": provider,
            "llm.model": request.model,
            "llm.prompt": json.dumps(messages_dicts),
            "llm.completion": completion,
            "llm.tokens.input": in_tok,
            "llm.tokens.output": out_tok,
            "llm.tokens.total": in_tok + out_tok,
            "llm.cost_usd": cost_usd,
            "llm.temperature": 1.0,
            "llm.finish_reason": "stop",
        },
    )
    await _broadcast_span(db, llm_span_end)

    # Close parent span
    parent_end = SpanCreate(
        span_id=parent_span_id,
        trace_id=trace_id,
        parent_span_id=None,
        span_type=SpanType.AGENT_STEP,
        name=f"Playground: {request.model}",
        status=SpanStatus.OK,
        start_time=now,
        end_time=end_time,
        attributes={"playground": True},
    )
    await _broadcast_span(db, parent_end)

    return PlaygroundChatResponse(
        conversation_id=conversation_id,
        trace_id=trace_id,
        message=PlaygroundMessage(role="assistant", content=completion),
        metrics=PlaygroundChatMetrics(
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=cost_usd,
            latency_ms=round(latency_ms, 1),
        ),
    )


async def compare(
    db: Session,
    request: PlaygroundCompareRequest,
) -> PlaygroundCompareResponse:
    """Send the same prompt to multiple models in parallel."""
    if len(request.models) < 2:
        raise ValueError("Comparison requires at least 2 models")

    trace_id = str(uuid4())
    now = time.time()
    messages_dicts = _messages_to_dicts(request.messages, request.system_prompt)

    # Create parent span
    parent_span_id = str(uuid4())
    model_names = " vs ".join(request.models)
    parent_span = SpanCreate(
        span_id=parent_span_id,
        trace_id=trace_id,
        parent_span_id=None,
        span_type=SpanType.AGENT_STEP,
        name=f"Compare: {model_names}",
        status=SpanStatus.UNSET,
        start_time=now,
        attributes={"playground": True, "playground.compare": True},
    )
    await _broadcast_trace_created(trace_id, f"Compare: {model_names}", now)
    await _broadcast_span(db, parent_span)

    # Resolve providers and keys
    model_configs: list[tuple[str, str, str]] = []  # (model, provider, key)
    for model in request.models:
        provider = provider_for_model(model)
        api_key = settings_service.get_api_key(provider)
        if not api_key:
            raise ValueError(
                f"No API key configured for {provider} (needed by {model}). "
                "Add one in Settings."
            )
        model_configs.append((model, provider, api_key))

    # Create start spans for each model
    span_ids: list[str] = []
    for model, provider, _ in model_configs:
        span_id = str(uuid4())
        span_ids.append(span_id)
        start_span = SpanCreate(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=SpanType.LLM_CALL,
            name=model,
            status=SpanStatus.UNSET,
            start_time=now,
            attributes={
                "llm.provider": provider,
                "llm.model": model,
                "llm.prompt": json.dumps(messages_dicts),
                "llm.temperature": 1.0,
            },
        )
        await _broadcast_span(db, start_span)

    # Call all models in parallel
    tasks = [
        _call_model(provider, api_key, model, messages_dicts)
        for model, provider, api_key in model_configs
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and update spans
    results: list[CompareResultItem] = []
    end_time = time.time()

    for i, (model, provider, _) in enumerate(model_configs):
        raw = raw_results[i]
        if isinstance(raw, Exception):
            # Update span with error
            error_span = SpanCreate(
                span_id=span_ids[i],
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                span_type=SpanType.LLM_CALL,
                name=model,
                status=SpanStatus.ERROR,
                error_message=str(raw),
                start_time=now,
                end_time=end_time,
                attributes={
                    "llm.provider": provider,
                    "llm.model": model,
                    "llm.prompt": json.dumps(messages_dicts),
                },
            )
            await _broadcast_span(db, error_span)
            results.append(
                CompareResultItem(
                    model=model,
                    provider=provider,
                    completion=f"Error: {raw}",
                    metrics=PlaygroundChatMetrics(
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0,
                        latency_ms=0,
                    ),
                )
            )
            continue

        completion, in_tok, out_tok, latency_ms = raw
        cost_usd = estimate_cost(model, in_tok, out_tok)

        # Update span with success
        end_span = SpanCreate(
            span_id=span_ids[i],
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=SpanType.LLM_CALL,
            name=model,
            status=SpanStatus.OK,
            start_time=now,
            end_time=end_time,
            attributes={
                "llm.provider": provider,
                "llm.model": model,
                "llm.prompt": json.dumps(messages_dicts),
                "llm.completion": completion,
                "llm.tokens.input": in_tok,
                "llm.tokens.output": out_tok,
                "llm.tokens.total": in_tok + out_tok,
                "llm.cost_usd": cost_usd,
                "llm.temperature": 1.0,
                "llm.finish_reason": "stop",
            },
        )
        await _broadcast_span(db, end_span)

        results.append(
            CompareResultItem(
                model=model,
                provider=provider,
                completion=completion,
                metrics=PlaygroundChatMetrics(
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=cost_usd,
                    latency_ms=round(latency_ms, 1),
                ),
            )
        )

    # Close parent span
    parent_status = (
        SpanStatus.ERROR
        if any(isinstance(r, Exception) for r in raw_results)
        else SpanStatus.OK
    )
    parent_end = SpanCreate(
        span_id=parent_span_id,
        trace_id=trace_id,
        parent_span_id=None,
        span_type=SpanType.AGENT_STEP,
        name=f"Compare: {model_names}",
        status=parent_status,
        start_time=now,
        end_time=end_time,
        attributes={"playground": True, "playground.compare": True},
    )
    await _broadcast_span(db, parent_end)

    return PlaygroundCompareResponse(trace_id=trace_id, results=results)
