"""Tests for prompt versioning endpoints."""

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
        "span_type": "llm_call",
        "name": "test-llm-call",
        "status": "ok",
        "error_message": None,
        "start_time": 1700000000.0,
        "end_time": 1700000001.0,
        "attributes": {"llm.prompt": '[]', "llm.completion": "hello"},
    }
    defaults.update(overrides)
    return defaults


def _ingest_span(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """Helper: ingest a single span and return its dict."""
    span = _make_span(**overrides)
    client.post("/v1/spans", json={"spans": [span]})
    return span


# --- GET /v1/spans/{span_id}/prompt-versions ---


def test_list_prompt_versions_empty(client: TestClient) -> None:
    span = _ingest_span(client)
    resp = client.get(f"/v1/spans/{span['span_id']}/prompt-versions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["versions"] == []


def test_list_prompt_versions_span_not_found(client: TestClient) -> None:
    resp = client.get("/v1/spans/nonexistent/prompt-versions")
    assert resp.status_code == 404


# --- POST /v1/spans/{span_id}/prompt-versions ---


def test_create_prompt_version(client: TestClient) -> None:
    span = _ingest_span(client)
    resp = client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": '[{"role": "user", "content": "hi"}]'},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["span_id"] == span["span_id"]
    assert data["prompt_text"] == '[{"role": "user", "content": "hi"}]'
    assert data["label"] is None
    assert "version_id" in data
    assert "created_at" in data


def test_create_prompt_version_with_label(client: TestClient) -> None:
    span = _ingest_span(client)
    resp = client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": "test prompt", "label": "v1-improved"},
    )
    assert resp.status_code == 201
    assert resp.json()["label"] == "v1-improved"


def test_list_prompt_versions_returns_versions_in_order(
    client: TestClient,
) -> None:
    span = _ingest_span(client)
    # Create two versions
    client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": "first", "label": "v1"},
    )
    client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": "second", "label": "v2"},
    )

    resp = client.get(f"/v1/spans/{span['span_id']}/prompt-versions")
    assert resp.status_code == 200
    versions = resp.json()["versions"]
    assert len(versions) == 2
    # Newest first
    assert versions[0]["label"] == "v2"
    assert versions[1]["label"] == "v1"


def test_create_prompt_version_span_not_found(client: TestClient) -> None:
    resp = client.post(
        "/v1/spans/nonexistent/prompt-versions",
        json={"prompt_text": "test"},
    )
    assert resp.status_code == 404


def test_create_prompt_version_non_llm_span(client: TestClient) -> None:
    span = _ingest_span(client, span_type="tool_use")
    resp = client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": "test"},
    )
    assert resp.status_code == 400
    assert "only supported" in resp.json()["detail"]


def test_cascade_delete_removes_versions(client: TestClient) -> None:
    span = _ingest_span(client)
    # Create a version
    client.post(
        f"/v1/spans/{span['span_id']}/prompt-versions",
        json={"prompt_text": "test"},
    )
    # Verify it exists
    resp = client.get(f"/v1/spans/{span['span_id']}/prompt-versions")
    assert len(resp.json()["versions"]) == 1

    # Delete the trace (cascades to spans and versions)
    client.delete(f"/v1/traces/{span['trace_id']}")

    # Span is gone, so listing versions should 404
    resp = client.get(f"/v1/spans/{span['span_id']}/prompt-versions")
    assert resp.status_code == 404
