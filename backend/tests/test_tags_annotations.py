"""Tests for tags and annotations endpoints."""

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


# --- PUT /v1/traces/{trace_id}/tags ---


def test_update_trace_tags_returns_updated_tags(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id)

    response = client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"env": "prod", "team": "ml"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == trace_id
    assert data["tags"] == {"env": "prod", "team": "ml"}


def test_update_trace_tags_not_found_returns_404(client: TestClient) -> None:
    response = client.put(
        f"/v1/traces/{uuid.uuid4()}/tags",
        json={"tags": {"env": "prod"}},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Trace not found"


def test_update_trace_tags_persists_in_trace_list(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id)

    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"env": "staging"}},
    )

    response = client.get("/v1/traces")
    traces = response.json()["traces"]
    trace = next(t for t in traces if t["trace_id"] == trace_id)
    assert trace["tags"] == {"env": "staging"}


def test_update_trace_tags_persists_in_trace_detail(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id)

    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"version": "2.0"}},
    )

    response = client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 200
    assert response.json()["tags"] == {"version": "2.0"}


def test_update_trace_tags_replaces_existing_tags(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id)

    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"old": "value"}},
    )
    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"new": "value"}},
    )

    response = client.get(f"/v1/traces/{trace_id}")
    assert response.json()["tags"] == {"new": "value"}


def test_update_trace_tags_empty_clears_tags(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id)

    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {"env": "prod"}},
    )
    client.put(
        f"/v1/traces/{trace_id}/tags",
        json={"tags": {}},
    )

    response = client.get(f"/v1/traces/{trace_id}")
    assert response.json()["tags"] == {}


# --- PUT /v1/spans/{span_id}/annotations ---


def test_update_span_annotations_returns_annotations(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, span_id=span_id)

    annotations = [
        {"id": "ann-1", "text": "This span is slow", "created_at": 1700000000.0}
    ]
    response = client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": annotations},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["span_id"] == span_id
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["text"] == "This span is slow"


def test_update_span_annotations_not_found_returns_404(client: TestClient) -> None:
    response = client.put(
        f"/v1/spans/{uuid.uuid4()}/annotations",
        json={"annotations": [{"id": "a", "text": "note", "created_at": 0}]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Span not found"


def test_update_span_annotations_persists_in_span_response(
    client: TestClient,
) -> None:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, span_id=span_id)

    annotations = [
        {"id": "ann-1", "text": "Needs investigation", "created_at": 1700000000.0}
    ]
    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": annotations},
    )

    response = client.get(f"/v1/spans/{span_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["text"] == "Needs investigation"


def test_update_span_annotations_persists_in_trace_detail(
    client: TestClient,
) -> None:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, span_id=span_id)

    annotations = [
        {"id": "ann-1", "text": "Debug note", "created_at": 1700000000.0}
    ]
    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": annotations},
    )

    response = client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 200
    spans = response.json()["spans"]
    span = next(s for s in spans if s["span_id"] == span_id)
    assert len(span["annotations"]) == 1
    assert span["annotations"][0]["text"] == "Debug note"


def test_update_span_annotations_replaces_existing(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, span_id=span_id)

    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": [{"id": "a1", "text": "first", "created_at": 1.0}]},
    )
    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={
            "annotations": [
                {"id": "a2", "text": "second", "created_at": 2.0},
                {"id": "a3", "text": "third", "created_at": 3.0},
            ]
        },
    )

    response = client.get(f"/v1/spans/{span_id}")
    data = response.json()
    assert len(data["annotations"]) == 2
    texts = {a["text"] for a in data["annotations"]}
    assert texts == {"second", "third"}


def test_update_span_annotations_empty_clears(client: TestClient) -> None:
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    _ingest_span(client, trace_id=trace_id, span_id=span_id)

    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": [{"id": "a1", "text": "note", "created_at": 1.0}]},
    )
    client.put(
        f"/v1/spans/{span_id}/annotations",
        json={"annotations": []},
    )

    response = client.get(f"/v1/spans/{span_id}")
    assert response.json()["annotations"] == []
