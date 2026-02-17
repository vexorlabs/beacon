from __future__ import annotations

import pytest

import beacon_sdk
from beacon_sdk.decorators import observe
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer, exporter):
    """Wire up the global tracer for decorator tests."""
    beacon_sdk._tracer = tracer
    yield
    beacon_sdk._tracer = None


def test_observe_sync_function_creates_span(exporter):
    @observe
    def my_func():
        return 42

    result = my_func()
    assert result == 42
    assert len(exporter.spans) == 1
    assert exporter.spans[0].status == SpanStatus.OK


def test_observe_preserves_return_value(exporter):
    @observe
    def add(a, b):
        return a + b

    assert add(1, 2) == 3


def test_observe_preserves_function_metadata():
    @observe
    def documented_func():
        """My docstring."""

    assert documented_func.__name__ == "documented_func"
    assert documented_func.__doc__ == "My docstring."


def test_observe_with_custom_name_and_type(exporter):
    @observe(name="custom-name", span_type="agent_step")
    def my_func():
        pass

    my_func()
    assert exporter.spans[0].name == "custom-name"
    assert exporter.spans[0].span_type == SpanType.AGENT_STEP


def test_observe_records_error_on_exception(exporter):
    @observe
    def failing_func():
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        failing_func()
    assert exporter.spans[0].status == SpanStatus.ERROR
    assert exporter.spans[0].error_message == "oops"


def test_observe_reraises_exception():
    @observe
    def failing_func():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        failing_func()


def test_observe_nested_creates_parent_child(exporter):
    @observe
    def outer():
        return inner()

    @observe
    def inner():
        return "done"

    outer()
    assert len(exporter.spans) == 2
    inner_span = exporter.spans[0]
    outer_span = exporter.spans[1]
    assert inner_span.parent_span_id == outer_span.span_id
    assert inner_span.trace_id == outer_span.trace_id


def test_observe_without_init_is_noop():
    beacon_sdk._tracer = None

    @observe
    def my_func():
        return "ok"

    assert my_func() == "ok"


@pytest.mark.asyncio
async def test_observe_async_function_creates_span(exporter):
    @observe
    async def async_func():
        return "async_result"

    result = await async_func()
    assert result == "async_result"
    assert len(exporter.spans) == 1
    assert exporter.spans[0].status == SpanStatus.OK


@pytest.mark.asyncio
async def test_observe_async_records_error(exporter):
    @observe
    async def failing_async():
        raise ValueError("async fail")

    with pytest.raises(ValueError, match="async fail"):
        await failing_async()
    assert exporter.spans[0].status == SpanStatus.ERROR
