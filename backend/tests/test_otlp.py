"""Tests for the OTLP-compatible ingestion endpoint."""

from __future__ import annotations

import uuid


def _make_otlp_payload(
    spans: list[dict] | None = None,
    trace_id: str | None = None,
) -> dict:
    """Build a valid OTLP JSON payload."""
    if trace_id is None:
        trace_id = str(uuid.uuid4())

    if spans is None:
        spans = [_make_otel_span(trace_id=trace_id)]

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "test-service"},
                        }
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "test", "version": "0.1.0"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def _make_otel_span(
    *,
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    name: str = "test-span",
    start_ns: int = 1700000000_000_000_000,
    end_ns: int = 1700000001_000_000_000,
    status_code: int = 1,
    attributes: list[dict] | None = None,
) -> dict:
    """Build a single OTEL span dict."""
    result: dict = {
        "traceId": trace_id or str(uuid.uuid4()),
        "spanId": span_id or str(uuid.uuid4()),
        "name": name,
        "kind": 1,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(end_ns),
        "attributes": attributes or [],
        "status": {"code": status_code},
    }
    if parent_span_id:
        result["parentSpanId"] = parent_span_id
    return result


def test_otlp_ingest_single_span(client):
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    payload = _make_otlp_payload(
        spans=[_make_otel_span(trace_id=trace_id, span_id=span_id)]
    )

    response = client.post("/v1/otlp/traces", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 0

    # Verify span was persisted
    span_resp = client.get(f"/v1/spans/{span_id}")
    assert span_resp.status_code == 200
    assert span_resp.json()["name"] == "test-span"


def test_otlp_timestamp_conversion(client):
    span_id = str(uuid.uuid4())
    # 1700000000.5 seconds = 1700000000_500_000_000 ns
    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                span_id=span_id,
                start_ns=1700000000_500_000_000,
                end_ns=1700000002_750_000_000,
            )
        ]
    )

    client.post("/v1/otlp/traces", json=payload)
    span_resp = client.get(f"/v1/spans/{span_id}")
    data = span_resp.json()

    assert abs(data["start_time"] - 1700000000.5) < 0.001
    assert abs(data["end_time"] - 1700000002.75) < 0.001


def test_otlp_attribute_mapping(client):
    span_id = str(uuid.uuid4())
    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                span_id=span_id,
                attributes=[
                    {
                        "key": "llm.model",
                        "value": {"stringValue": "gpt-4o"},
                    },
                    {
                        "key": "llm.tokens.total",
                        "value": {"intValue": "1500"},
                    },
                    {
                        "key": "llm.cost_usd",
                        "value": {"doubleValue": 0.05},
                    },
                    {
                        "key": "is_streaming",
                        "value": {"boolValue": True},
                    },
                ],
            )
        ]
    )

    client.post("/v1/otlp/traces", json=payload)
    span_resp = client.get(f"/v1/spans/{span_id}")
    attrs = span_resp.json()["attributes"]

    assert attrs["llm.model"] == "gpt-4o"
    assert attrs["llm.tokens.total"] == 1500
    assert attrs["llm.cost_usd"] == 0.05
    assert attrs["is_streaming"] is True


def test_otlp_span_type_extraction(client):
    span_id = str(uuid.uuid4())
    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                span_id=span_id,
                attributes=[
                    {
                        "key": "span_type",
                        "value": {"stringValue": "llm_call"},
                    }
                ],
            )
        ]
    )

    client.post("/v1/otlp/traces", json=payload)
    span_resp = client.get(f"/v1/spans/{span_id}")
    data = span_resp.json()
    assert data["span_type"] == "llm_call"
    # span_type should not be in attributes (it was extracted)
    assert "span_type" not in data["attributes"]


def test_otlp_unknown_span_type_defaults_to_custom(client):
    span_id = str(uuid.uuid4())
    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                span_id=span_id,
                attributes=[
                    {
                        "key": "span_type",
                        "value": {"stringValue": "not_a_real_type"},
                    }
                ],
            )
        ]
    )

    client.post("/v1/otlp/traces", json=payload)
    span_resp = client.get(f"/v1/spans/{span_id}")
    assert span_resp.json()["span_type"] == "custom"


def test_otlp_error_status(client):
    span_id = str(uuid.uuid4())
    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                span_id=span_id,
                status_code=2,
                attributes=[
                    {
                        "key": "error.message",
                        "value": {"stringValue": "something broke"},
                    }
                ],
            )
        ]
    )

    client.post("/v1/otlp/traces", json=payload)
    span_resp = client.get(f"/v1/spans/{span_id}")
    data = span_resp.json()
    assert data["status"] == "error"
    assert data["error_message"] == "something broke"


def test_otlp_parent_span_linking(client, db_session):
    trace_id = str(uuid.uuid4())
    parent_id = str(uuid.uuid4())
    child_id = str(uuid.uuid4())

    payload = _make_otlp_payload(
        spans=[
            _make_otel_span(
                trace_id=trace_id, span_id=parent_id, name="parent"
            ),
            _make_otel_span(
                trace_id=trace_id,
                span_id=child_id,
                parent_span_id=parent_id,
                name="child",
            ),
        ]
    )

    client.post("/v1/otlp/traces", json=payload)

    child_resp = client.get(f"/v1/spans/{child_id}")
    data = child_resp.json()
    assert data["parent_span_id"] == parent_id
    assert data["trace_id"] == trace_id


def test_otlp_multiple_spans_batch(client):
    trace_id = str(uuid.uuid4())
    spans = [
        _make_otel_span(trace_id=trace_id, name=f"span-{i}")
        for i in range(5)
    ]
    payload = _make_otlp_payload(spans=spans)

    response = client.post("/v1/otlp/traces", json=payload)
    data = response.json()
    assert data["accepted"] == 5


def test_otlp_empty_payload(client):
    response = client.post("/v1/otlp/traces", json={"resourceSpans": []})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 0
    assert data["rejected"] == 0


def test_otlp_roundtrip_with_export(client):
    """Export a trace as OTEL, then re-import via OTLP. Verify data survives."""
    # First ingest a span normally
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    normal_span = {
        "span_id": span_id,
        "trace_id": trace_id,
        "parent_span_id": None,
        "span_type": "llm_call",
        "name": "roundtrip-test",
        "status": "ok",
        "error_message": None,
        "start_time": 1700000000.0,
        "end_time": 1700000001.0,
        "attributes": {"llm.model": "gpt-4o", "llm.cost_usd": 0.05},
    }
    client.post("/v1/spans", json={"spans": [normal_span]})

    # Export as OTEL
    export_resp = client.get(f"/v1/traces/{trace_id}/export?format=otel")
    assert export_resp.status_code == 200
    otel_data = export_resp.json()

    # Re-import via OTLP (use a new span_id to avoid duplicate)
    new_span_id = str(uuid.uuid4())
    new_trace_id = str(uuid.uuid4())
    otel_spans = otel_data["resourceSpans"][0]["scopeSpans"][0]["spans"]
    otel_spans[0]["spanId"] = new_span_id
    otel_spans[0]["traceId"] = new_trace_id

    import_resp = client.post("/v1/otlp/traces", json=otel_data)
    assert import_resp.status_code == 200
    assert import_resp.json()["accepted"] == 1

    # Verify the re-imported span
    span_resp = client.get(f"/v1/spans/{new_span_id}")
    data = span_resp.json()
    assert data["name"] == "roundtrip-test"
    assert data["span_type"] == "llm_call"
    assert data["status"] == "ok"
    assert data["attributes"]["llm.model"] == "gpt-4o"
