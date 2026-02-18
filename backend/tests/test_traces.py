"""Tests for Phase 2 trace endpoints: list, detail, and graph."""

from __future__ import annotations

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


# --- GET /v1/traces ---


def test_list_traces_returns_empty_when_no_data(client):
    response = client.get("/v1/traces")
    assert response.status_code == 200
    data = response.json()
    assert data["traces"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_list_traces_returns_ingested_traces(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, name="my-agent")

    response = client.get("/v1/traces")
    data = response.json()
    assert data["total"] == 1
    assert len(data["traces"]) == 1
    assert data["traces"][0]["trace_id"] == trace_id
    assert data["traces"][0]["name"] == "my-agent"
    assert data["traces"][0]["span_count"] == 1


def test_list_traces_respects_limit_and_offset(client):
    for _ in range(5):
        _ingest_span(client, trace_id=str(uuid.uuid4()))

    response = client.get("/v1/traces?limit=2&offset=1")
    data = response.json()
    assert data["total"] == 5
    assert len(data["traces"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1


def test_list_traces_filters_by_status(client):
    ok_trace = str(uuid.uuid4())
    error_trace = str(uuid.uuid4())
    # First span creates trace with status="unset"; second triggers recompute
    _ingest_span(client, trace_id=ok_trace, status="ok")
    _ingest_span(client, trace_id=ok_trace, status="ok")
    _ingest_span(client, trace_id=error_trace, status="ok")
    _ingest_span(client, trace_id=error_trace, status="error")

    response = client.get("/v1/traces?status=error")
    data = response.json()
    assert data["total"] == 1
    assert data["traces"][0]["trace_id"] == error_trace


# --- GET /v1/traces/{trace_id} ---


def test_get_trace_detail_returns_trace_with_spans(client):
    trace_id = str(uuid.uuid4())
    root_span_id = str(uuid.uuid4())
    child_span_id = str(uuid.uuid4())

    _ingest_span(
        client,
        span_id=root_span_id,
        trace_id=trace_id,
        name="root",
        parent_span_id=None,
    )
    _ingest_span(
        client,
        span_id=child_span_id,
        trace_id=trace_id,
        name="child",
        parent_span_id=root_span_id,
    )

    response = client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == trace_id
    assert len(data["spans"]) == 2
    span_ids = {s["span_id"] for s in data["spans"]}
    assert root_span_id in span_ids
    assert child_span_id in span_ids


def test_get_trace_detail_not_found_returns_404(client):
    response = client.get(f"/v1/traces/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trace not found"


def test_get_trace_detail_includes_duration(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(
        client,
        trace_id=trace_id,
        start_time=1700000000.0,
        end_time=1700000002.5,
    )

    response = client.get(f"/v1/traces/{trace_id}")
    data = response.json()
    assert data["duration_ms"] == 2500.0


# --- GET /v1/traces/{trace_id}/graph ---


def test_get_trace_graph_returns_nodes_and_edges(client):
    trace_id = str(uuid.uuid4())
    root_id = str(uuid.uuid4())
    child_id = str(uuid.uuid4())

    _ingest_span(
        client,
        span_id=root_id,
        trace_id=trace_id,
        name="root",
        span_type="chain",
    )
    _ingest_span(
        client,
        span_id=child_id,
        trace_id=trace_id,
        name="llm-call",
        span_type="llm_call",
        parent_span_id=root_id,
    )

    response = client.get(f"/v1/traces/{trace_id}/graph")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Verify node structure
    node = next(n for n in data["nodes"] if n["id"] == child_id)
    assert node["type"] == "spanNode"
    assert node["data"]["span_type"] == "llm_call"
    assert node["data"]["name"] == "llm-call"
    assert node["position"] == {"x": 0, "y": 0}

    # Verify edge
    edge = data["edges"][0]
    assert edge["source"] == root_id
    assert edge["target"] == child_id


def test_get_trace_graph_not_found_returns_404(client):
    response = client.get(f"/v1/traces/{uuid.uuid4()}/graph")
    assert response.status_code == 404


def test_get_trace_graph_extracts_llm_cost(client):
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(
        client,
        span_id=span_id,
        trace_id=trace_id,
        span_type="llm_call",
        attributes={"llm.cost_usd": 0.0042},
    )

    response = client.get(f"/v1/traces/{trace_id}/graph")
    data = response.json()
    node = data["nodes"][0]
    assert node["data"]["cost_usd"] == 0.0042


def test_get_trace_graph_root_node_has_no_incoming_edge(client):
    trace_id = str(uuid.uuid4())
    root_id = str(uuid.uuid4())
    _ingest_span(
        client,
        span_id=root_id,
        trace_id=trace_id,
        parent_span_id=None,
    )

    response = client.get(f"/v1/traces/{trace_id}/graph")
    data = response.json()
    assert len(data["edges"]) == 0


# --- DELETE /v1/traces/{trace_id} ---


def test_delete_trace_removes_trace_and_spans(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, name="span-a")
    _ingest_span(client, trace_id=trace_id, name="span-b")

    response = client.delete(f"/v1/traces/{trace_id}")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    # Verify trace is gone
    response = client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 404


def test_delete_trace_not_found_returns_404(client):
    response = client.delete(f"/v1/traces/{uuid.uuid4()}")
    assert response.status_code == 404


# --- DELETE /v1/traces (batch) ---


def test_delete_traces_batch_by_ids(client):
    trace_ids = [str(uuid.uuid4()) for _ in range(3)]
    for tid in trace_ids:
        _ingest_span(client, trace_id=tid)

    response = client.request(
        "DELETE", "/v1/traces", json={"trace_ids": trace_ids[:2]}
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    # Third trace still exists
    remaining = client.get("/v1/traces")
    assert remaining.json()["total"] == 1


def test_delete_traces_batch_by_older_than(client):
    trace_a = str(uuid.uuid4())
    trace_b = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_a)
    _ingest_span(client, trace_id=trace_b)

    # Both traces have created_at ~ now; delete all with a future threshold
    import time

    response = client.request(
        "DELETE", "/v1/traces", json={"older_than": time.time() + 100}
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    remaining = client.get("/v1/traces")
    assert remaining.json()["total"] == 0


def test_delete_traces_batch_requires_criteria(client):
    response = client.request("DELETE", "/v1/traces", json={})
    assert response.status_code == 422
