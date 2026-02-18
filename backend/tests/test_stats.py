"""Tests for GET /v1/stats endpoint."""

from __future__ import annotations

import uuid
from typing import Any

from starlette.testclient import TestClient


def _make_span(**overrides: Any) -> dict[str, Any]:
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
    span = _make_span(**overrides)
    client.post("/v1/spans", json={"spans": [span]})
    return span


def test_get_stats_empty_database(client):
    response = client.get("/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_traces"] == 0
    assert data["total_spans"] == 0
    assert data["oldest_trace_timestamp"] is None
    assert "database_size_bytes" in data


def test_get_stats_with_data(client):
    _ingest_span(client, trace_id=str(uuid.uuid4()))
    _ingest_span(client, trace_id=str(uuid.uuid4()))

    response = client.get("/v1/stats")
    data = response.json()
    assert data["total_traces"] == 2
    assert data["total_spans"] == 2
    assert data["oldest_trace_timestamp"] is not None
