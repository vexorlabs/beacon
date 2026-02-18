"""Tests for GET /v1/search endpoint."""

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


def test_search_by_span_name(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, name="openai.chat.completions")

    response = client.get("/v1/search?q=openai")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(r["name"] == "openai.chat.completions" for r in data["results"])


def test_search_by_attributes(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(
        client,
        trace_id=trace_id,
        name="llm-call",
        attributes={"llm.model": "gpt-4o", "error": "rate_limit_exceeded"},
    )

    response = client.get("/v1/search?q=rate_limit")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_search_no_results(client):
    response = client.get("/v1/search?q=nonexistent_query_xyz")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["results"] == []


def test_search_requires_query(client):
    response = client.get("/v1/search")
    assert response.status_code == 422


def test_search_respects_limit(client):
    trace_id = str(uuid.uuid4())
    for i in range(5):
        _ingest_span(
            client,
            trace_id=trace_id,
            name=f"span-match-{i}",
        )

    response = client.get("/v1/search?q=span-match&limit=2")
    data = response.json()
    assert len(data["results"]) == 2
    assert data["total"] == 5


def test_search_case_insensitive(client):
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, name="OpenAI.Chat")

    response = client.get("/v1/search?q=openai")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
