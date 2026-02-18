from __future__ import annotations

import json
import threading
import time

import responses

from beacon_sdk.exporters import AsyncBatchExporter, HttpSpanExporter
from beacon_sdk.models import Span, SpanType

ENDPOINT = "http://localhost:7474/v1/spans"


def _make_span(name: str = "test") -> Span:
    return Span(trace_id="t1", name=name, span_type=SpanType.CUSTOM)


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


# --- AsyncBatchExporter tests ---


@responses.activate
def test_batch_exporter_batches_spans_into_single_post():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 3}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=10, flush_interval_ms=60000)
    try:
        exp.export([_make_span("a")])
        exp.export([_make_span("b")])
        exp.export([_make_span("c")])
        exp.flush()
        assert len(responses.calls) == 1
        body = json.loads(responses.calls[0].request.body)
        assert len(body["spans"]) == 3
    finally:
        exp.shutdown()


@responses.activate
def test_batch_exporter_flushes_on_interval():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 2}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=100)
    try:
        exp.export([_make_span("a")])
        exp.export([_make_span("b")])
        time.sleep(0.3)
        assert len(responses.calls) >= 1
        total_spans = sum(
            len(json.loads(c.request.body)["spans"]) for c in responses.calls
        )
        assert total_spans == 2
    finally:
        exp.shutdown()


@responses.activate
def test_batch_exporter_flushes_on_batch_size():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 2}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=2, flush_interval_ms=60000)
    try:
        exp.export([_make_span("a")])
        exp.export([_make_span("b")])
        time.sleep(0.15)
        assert len(responses.calls) >= 1
        body = json.loads(responses.calls[0].request.body)
        assert len(body["spans"]) == 2
    finally:
        exp.shutdown()


@responses.activate
def test_batch_exporter_flush_sends_pending():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 1}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=60000)
    try:
        exp.export([_make_span()])
        exp.flush()
        assert len(responses.calls) == 1
    finally:
        exp.shutdown()


@responses.activate
def test_batch_exporter_shutdown_flushes_remaining():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 5}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=60000)
    for i in range(5):
        exp.export([_make_span(f"span-{i}")])
    exp.shutdown()
    total_spans = sum(
        len(json.loads(c.request.body)["spans"]) for c in responses.calls
    )
    assert total_spans == 5
    assert not exp._worker.is_alive()


@responses.activate
def test_batch_exporter_shutdown_is_idempotent():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 1}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=60000)
    exp.export([_make_span()])
    exp.shutdown()
    exp.shutdown()  # Second call should not raise


@responses.activate
def test_batch_exporter_export_after_shutdown_is_noop():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 0}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=60000)
    exp.shutdown()
    call_count_before = len(responses.calls)
    exp.export([_make_span()])
    time.sleep(0.05)
    assert len(responses.calls) == call_count_before


@responses.activate
def test_batch_exporter_handles_connection_error():
    responses.add(responses.POST, ENDPOINT, body=ConnectionError("refused"))
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=1000, flush_interval_ms=60000)
    try:
        exp.export([_make_span()])
        exp.flush()  # Should not raise
    finally:
        exp.shutdown()


@responses.activate
def test_batch_exporter_thread_safety():
    responses.add(responses.POST, ENDPOINT, json={"accepted": 0}, status=200)
    exp = AsyncBatchExporter("http://localhost:7474", batch_size=100, flush_interval_ms=50)

    def produce(n: int) -> None:
        for i in range(n):
            exp.export([_make_span(f"span-{threading.current_thread().name}-{i}")])

    threads = [threading.Thread(target=produce, args=(50,)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    exp.shutdown()

    total_spans = sum(
        len(json.loads(c.request.body)["spans"]) for c in responses.calls
    )
    assert total_spans == 500


def test_batch_exporter_endpoint_strips_trailing_slash():
    exp = AsyncBatchExporter("http://localhost:7474/", batch_size=1000, flush_interval_ms=60000)
    try:
        assert exp._endpoint == "http://localhost:7474/v1/spans"
    finally:
        exp.shutdown()
