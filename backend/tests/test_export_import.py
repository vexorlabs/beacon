"""Tests for trace export and import endpoints."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from starlette.testclient import TestClient


def _make_span(**overrides: Any) -> dict[str, Any]:
    """Build a valid span dict with sensible defaults."""
    defaults: dict[str, Any] = {
        "span_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "parent_span_id": None,
        "span_type": "custom",
        "name": "test-span",
        "status": "ok",
        "error_message": None,
        "start_time": 1700000000.0,
        "end_time": 1700000001.0,
        "attributes": {},
    }
    defaults.update(overrides)
    return defaults


def _ingest_span(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """Helper: ingest a single span and return its dict."""
    span = _make_span(**overrides)
    client.post("/v1/spans", json={"spans": [span]})
    return span


def _ingest_trace(client: TestClient, trace_id: str) -> list[dict[str, Any]]:
    """Ingest a multi-span trace and return spans."""
    root = _ingest_span(
        client,
        trace_id=trace_id,
        span_id="root-span",
        name="root-agent",
        span_type="agent_step",
        start_time=1700000000.0,
        end_time=1700000005.0,
    )
    child = _ingest_span(
        client,
        trace_id=trace_id,
        span_id="child-span",
        parent_span_id="root-span",
        name="llm-call",
        span_type="llm_call",
        start_time=1700000001.0,
        end_time=1700000003.0,
        attributes={
            "llm.provider": "openai",
            "llm.model": "gpt-4o",
            "llm.cost_usd": 0.005,
            "llm.tokens.total": 500,
        },
    )
    return [root, child]


# --- GET /v1/traces/{trace_id}/export?format=json ---


def test_export_json_returns_beacon_envelope(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_trace(client, trace_id)

    resp = client.get(f"/v1/traces/{trace_id}/export?format=json")
    assert resp.status_code == 200

    data = resp.json()
    assert data["version"] == "1"
    assert data["format"] == "beacon"
    assert "exported_at" in data
    assert data["trace"]["trace_id"] == trace_id
    assert len(data["spans"]) == 2


def test_export_json_not_found(client: TestClient) -> None:
    resp = client.get("/v1/traces/nonexistent/export?format=json")
    assert resp.status_code == 404


def test_export_json_default_format(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_trace(client, trace_id)

    resp = client.get(f"/v1/traces/{trace_id}/export")
    assert resp.status_code == 200
    assert resp.json()["format"] == "beacon"


# --- GET /v1/traces/{trace_id}/export?format=otel ---


def test_export_otel_returns_resource_spans(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_trace(client, trace_id)

    resp = client.get(f"/v1/traces/{trace_id}/export?format=otel")
    assert resp.status_code == 200

    data = resp.json()
    assert "resourceSpans" in data
    resource_spans = data["resourceSpans"]
    assert len(resource_spans) == 1

    scope_spans = resource_spans[0]["scopeSpans"]
    assert len(scope_spans) == 1

    spans = scope_spans[0]["spans"]
    assert len(spans) == 2

    span = spans[0]
    assert "traceId" in span
    assert "spanId" in span
    assert "startTimeUnixNano" in span
    assert "endTimeUnixNano" in span
    assert "status" in span


def test_export_otel_not_found(client: TestClient) -> None:
    resp = client.get("/v1/traces/nonexistent/export?format=otel")
    assert resp.status_code == 404


# --- GET /v1/traces/{trace_id}/export?format=csv ---


def test_export_csv_returns_valid_csv(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_trace(client, trace_id)

    resp = client.get(f"/v1/traces/{trace_id}/export?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)

    # Header + 2 data rows
    assert len(rows) == 3
    header = rows[0]
    assert "trace_id" in header
    assert "span_id" in header
    assert "duration_ms" in header
    assert "cost" in header
    assert "tokens" in header


def test_export_csv_not_found(client: TestClient) -> None:
    resp = client.get("/v1/traces/nonexistent/export?format=csv")
    assert resp.status_code == 404


# --- GET /v1/traces/export (bulk) ---


def test_bulk_export_returns_multiple_traces(client: TestClient) -> None:
    tid1 = str(uuid.uuid4())
    tid2 = str(uuid.uuid4())
    _ingest_span(client, trace_id=tid1, name="trace-1")
    _ingest_span(client, trace_id=tid2, name="trace-2")

    resp = client.get(f"/v1/traces/export?trace_ids={tid1},{tid2}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["version"] == "1"
    assert len(data["traces"]) == 2


def test_bulk_export_requires_trace_ids(client: TestClient) -> None:
    resp = client.get("/v1/traces/export")
    assert resp.status_code == 422


def test_bulk_export_skips_missing_traces(client: TestClient) -> None:
    tid = str(uuid.uuid4())
    _ingest_span(client, trace_id=tid, name="real")

    resp = client.get(f"/v1/traces/export?trace_ids={tid},nonexistent")
    assert resp.status_code == 200
    assert len(resp.json()["traces"]) == 1


def test_bulk_export_rejects_non_json_format(client: TestClient) -> None:
    resp = client.get("/v1/traces/export?format=csv&trace_ids=a")
    assert resp.status_code == 400


# --- POST /v1/traces/import ---


def _make_export_data(
    trace_id: str | None = None,
    span_count: int = 1,
    **trace_overrides: Any,
) -> dict[str, Any]:
    """Build a valid TraceExportData dict for import."""
    tid = trace_id or str(uuid.uuid4())
    spans = []
    for i in range(span_count):
        spans.append({
            "span_id": f"{tid}-span-{i}",
            "trace_id": tid,
            "parent_span_id": None if i == 0 else f"{tid}-span-0",
            "span_type": "llm_call" if i > 0 else "agent_step",
            "name": f"span-{i}",
            "status": "ok",
            "error_message": None,
            "start_time": 1700000000.0 + i,
            "end_time": 1700000001.0 + i,
            "duration_ms": 1000.0,
            "attributes": {},
        })

    trace_data: dict[str, Any] = {
        "trace_id": tid,
        "name": "imported-trace",
        "start_time": 1700000000.0,
        "end_time": 1700000001.0 + span_count,
        "duration_ms": 1000.0 + span_count * 1000,
        "span_count": span_count,
        "status": "ok",
        "total_cost_usd": 0.0,
        "total_tokens": 0,
        "tags": {},
    }
    trace_data.update(trace_overrides)

    return {
        "version": "1",
        "format": "beacon",
        "exported_at": 1700000000.0,
        "trace": trace_data,
        "spans": spans,
    }


def test_import_creates_trace_and_spans(client: TestClient) -> None:
    data = _make_export_data(span_count=3)
    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 200

    result = resp.json()
    assert result["trace_id"] == data["trace"]["trace_id"]
    assert result["span_count"] == 3

    # Verify trace is queryable
    trace_resp = client.get(f"/v1/traces/{result['trace_id']}")
    assert trace_resp.status_code == 200
    assert trace_resp.json()["span_count"] == 3
    assert len(trace_resp.json()["spans"]) == 3


def test_import_duplicate_returns_409(client: TestClient) -> None:
    tid = str(uuid.uuid4())
    data = _make_export_data(trace_id=tid)

    resp1 = client.post("/v1/traces/import", json=data)
    assert resp1.status_code == 200

    resp2 = client.post("/v1/traces/import", json=data)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_import_rejects_unsupported_format(client: TestClient) -> None:
    data = _make_export_data()
    data["format"] = "otlp"

    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 400
    assert "Unsupported export format" in resp.json()["detail"]


def test_import_rejects_unsupported_version(client: TestClient) -> None:
    data = _make_export_data()
    data["version"] = "99"

    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 400
    assert "Unsupported export version" in resp.json()["detail"]


def test_import_invalid_span_type_returns_422(client: TestClient) -> None:
    data = _make_export_data()
    data["spans"][0]["span_type"] = "invalid_type"

    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 422


# --- Roundtrip: export then import ---


def test_export_import_roundtrip(client: TestClient) -> None:
    """Export a trace, modify IDs, re-import — verify spans match."""
    trace_id = str(uuid.uuid4())
    _ingest_trace(client, trace_id)

    # Export
    export_resp = client.get(f"/v1/traces/{trace_id}/export?format=json")
    assert export_resp.status_code == 200
    exported = export_resp.json()

    # Change all IDs for re-import
    new_trace_id = str(uuid.uuid4())
    exported["trace"]["trace_id"] = new_trace_id
    for span in exported["spans"]:
        old_id = span["span_id"]
        new_id = f"rt-{old_id}"
        span["span_id"] = new_id
        span["trace_id"] = new_trace_id
        # Update parent references
        for other in exported["spans"]:
            if other.get("parent_span_id") == old_id:
                other["parent_span_id"] = new_id

    # Import
    import_resp = client.post("/v1/traces/import", json=exported)
    assert import_resp.status_code == 200
    assert import_resp.json()["trace_id"] == new_trace_id

    # Verify
    detail_resp = client.get(f"/v1/traces/{new_trace_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["span_count"] == 2
    assert len(detail["spans"]) == 2

    original = client.get(f"/v1/traces/{trace_id}").json()
    assert detail["spans"][0]["name"] == original["spans"][0]["name"]


# --- Import from example files ---


def test_import_example_rag_agent(client: TestClient) -> None:
    with open("docs/example-traces/rag-agent.json") as f:
        data = json.load(f)

    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 200
    assert resp.json()["span_count"] == 5


def test_import_example_tool_agent(client: TestClient) -> None:
    with open("docs/example-traces/tool-calling-agent-with-errors.json") as f:
        data = json.load(f)

    resp = client.post("/v1/traces/import", json=data)
    assert resp.status_code == 200
    assert resp.json()["span_count"] == 6
