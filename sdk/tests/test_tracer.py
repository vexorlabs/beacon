from __future__ import annotations

import pytest

from beacon_sdk.context import get_context
from beacon_sdk.models import SpanStatus, SpanType
from beacon_sdk.tracer import BeaconTracer


def test_start_span_creates_root_span_with_new_trace_id(tracer):
    span, token = tracer.start_span("root")
    assert span.trace_id != ""
    assert span.parent_span_id is None
    tracer.end_span(span, token)


def test_start_span_creates_child_span_with_parent_id(tracer):
    parent, token_p = tracer.start_span("parent")
    child, token_c = tracer.start_span("child")
    assert child.trace_id == parent.trace_id
    assert child.parent_span_id == parent.span_id
    tracer.end_span(child, token_c)
    tracer.end_span(parent, token_p)


def test_end_span_exports_span_to_exporter(tracer, exporter):
    span, token = tracer.start_span("test")
    tracer.end_span(span, token)
    assert len(exporter.spans) == 1
    assert exporter.spans[0] is span


def test_end_span_restores_parent_context(tracer):
    parent, token_p = tracer.start_span("parent")
    child, token_c = tracer.start_span("child")

    ctx_during_child = get_context()
    assert ctx_during_child.span_id == child.span_id

    tracer.end_span(child, token_c)

    ctx_after_child = get_context()
    assert ctx_after_child.span_id == parent.span_id

    tracer.end_span(parent, token_p)


def test_nested_spans_form_correct_tree(tracer, exporter):
    a, tok_a = tracer.start_span("a")
    b, tok_b = tracer.start_span("b")
    tracer.end_span(b, tok_b)
    tracer.end_span(a, tok_a)

    assert exporter.spans[0].name == "b"
    assert exporter.spans[0].parent_span_id == a.span_id
    assert exporter.spans[1].name == "a"
    assert exporter.spans[1].parent_span_id is None


def test_disabled_tracer_does_not_export(exporter):
    disabled = BeaconTracer(exporter=exporter, enabled=False)
    span, token = disabled.start_span("test")
    disabled.end_span(span, token)
    assert len(exporter.spans) == 0


def test_context_manager_span_ok_on_success(tracer, exporter):
    with tracer.span("cm-test") as s:
        s.set_attribute("key", "val")
    assert exporter.spans[0].status == SpanStatus.OK
    assert exporter.spans[0].attributes["key"] == "val"


def test_context_manager_span_error_on_exception(tracer, exporter):
    with pytest.raises(ValueError, match="fail"):
        with tracer.span("cm-error"):
            raise ValueError("fail")
    assert exporter.spans[0].status == SpanStatus.ERROR
    assert exporter.spans[0].error_message == "fail"


def test_context_manager_reraises_exception(tracer):
    with pytest.raises(RuntimeError, match="boom"):
        with tracer.span("test"):
            raise RuntimeError("boom")
