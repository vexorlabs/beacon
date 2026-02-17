from __future__ import annotations

import responses

from beacon_sdk.exporters import HttpSpanExporter
from beacon_sdk.models import Span, SpanType


def _make_span() -> Span:
    return Span(trace_id="t1", name="test", span_type=SpanType.CUSTOM)


@responses.activate
def test_export_sends_post_to_correct_endpoint():
    responses.add(
        responses.POST,
        "http://localhost:7474/v1/spans",
        json={"accepted": 1, "rejected": 0},
        status=200,
    )
    exporter = HttpSpanExporter("http://localhost:7474")
    exporter.export([_make_span()])
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == "http://localhost:7474/v1/spans"


@responses.activate
def test_export_sends_correct_json_payload():
    responses.add(
        responses.POST,
        "http://localhost:7474/v1/spans",
        json={"accepted": 1, "rejected": 0},
        status=200,
    )
    span = _make_span()
    exporter = HttpSpanExporter("http://localhost:7474")
    exporter.export([span])

    import json

    body = json.loads(responses.calls[0].request.body)
    assert "spans" in body
    assert body["spans"][0]["span_id"] == span.span_id
    assert body["spans"][0]["trace_id"] == "t1"


@responses.activate
def test_export_handles_connection_error_gracefully():
    responses.add(
        responses.POST,
        "http://localhost:7474/v1/spans",
        body=ConnectionError("refused"),
    )
    exporter = HttpSpanExporter("http://localhost:7474")
    exporter.export([_make_span()])  # Should not raise


@responses.activate
def test_export_handles_server_error_gracefully():
    responses.add(
        responses.POST,
        "http://localhost:7474/v1/spans",
        json={"detail": "Internal Server Error"},
        status=500,
    )
    exporter = HttpSpanExporter("http://localhost:7474")
    exporter.export([_make_span()])  # Should not raise


def test_endpoint_strips_trailing_slash():
    exporter = HttpSpanExporter("http://localhost:7474/")
    assert exporter._endpoint == "http://localhost:7474/v1/spans"
