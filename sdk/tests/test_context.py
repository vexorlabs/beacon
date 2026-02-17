from __future__ import annotations

import asyncio

import pytest

from beacon_sdk.context import (
    TraceContext,
    get_context,
    register_span,
    reset_context,
    set_context,
    unregister_span,
    get_active_span,
)
from beacon_sdk.models import Span


def test_get_context_returns_none_when_no_context_set():
    # Reset to clean state
    token = set_context(None)  # type: ignore[arg-type]
    reset_context(token)
    assert get_context() is None


def test_set_context_and_get_context_roundtrip():
    ctx = TraceContext(trace_id="t1", span_id="s1")
    token = set_context(ctx)
    assert get_context() is ctx
    reset_context(token)


def test_reset_context_restores_previous_value():
    ctx1 = TraceContext(trace_id="t1", span_id="s1")
    token1 = set_context(ctx1)
    ctx2 = TraceContext(trace_id="t1", span_id="s2")
    token2 = set_context(ctx2)
    assert get_context() is ctx2
    reset_context(token2)
    assert get_context() is ctx1
    reset_context(token1)


def test_nested_contexts_restore_correctly():
    token_none = set_context(None)  # type: ignore[arg-type]
    reset_context(token_none)

    ctx_a = TraceContext(trace_id="t", span_id="a")
    token_a = set_context(ctx_a)
    ctx_b = TraceContext(trace_id="t", span_id="b")
    token_b = set_context(ctx_b)

    assert get_context().span_id == "b"  # type: ignore[union-attr]
    reset_context(token_b)
    assert get_context().span_id == "a"  # type: ignore[union-attr]
    reset_context(token_a)


def test_register_and_get_active_span():
    span = Span(name="test")
    register_span(span)
    assert get_active_span(span.span_id) is span
    unregister_span(span.span_id)
    assert get_active_span(span.span_id) is None


@pytest.mark.asyncio
async def test_async_context_propagation():
    ctx = TraceContext(trace_id="t1", span_id="s1")
    token = set_context(ctx)

    async def child():
        return get_context()

    result = await child()
    assert result is ctx
    reset_context(token)


@pytest.mark.asyncio
async def test_async_tasks_have_isolated_contexts():
    results = {}

    async def task_a():
        ctx = TraceContext(trace_id="t", span_id="a")
        token = set_context(ctx)
        await asyncio.sleep(0.01)
        results["a"] = get_context()
        reset_context(token)

    async def task_b():
        ctx = TraceContext(trace_id="t", span_id="b")
        token = set_context(ctx)
        await asyncio.sleep(0.01)
        results["b"] = get_context()
        reset_context(token)

    await asyncio.gather(task_a(), task_b())
    assert results["a"].span_id == "a"  # type: ignore[union-attr]
    assert results["b"].span_id == "b"  # type: ignore[union-attr]
