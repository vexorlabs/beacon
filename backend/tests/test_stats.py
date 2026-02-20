"""Tests for /v1/stats endpoints including trends, top-costs, and top-duration."""

from __future__ import annotations

import time
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
    resp = client.post("/v1/spans", json={"spans": [span]})
    assert resp.status_code == 200
    return span


# ---------------------------------------------------------------------------
# GET /v1/stats (existing)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# GET /v1/stats/trends
# ---------------------------------------------------------------------------


class TestTrends:
    def test_trends_empty_database(self, client):
        resp = client.get("/v1/stats/trends", params={"days": 7})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["buckets"]) == 7
        for bucket in data["buckets"]:
            assert bucket["total_cost"] == 0.0
            assert bucket["total_tokens"] == 0
            assert bucket["trace_count"] == 0
            assert bucket["error_count"] == 0
            assert bucket["success_rate"] == 1.0

    def test_trends_with_traces(self, client):
        now = time.time()
        trace_id = str(uuid.uuid4())
        _ingest_span(
            client,
            trace_id=trace_id,
            span_type="llm_call",
            name="openai.chat",
            start_time=now - 10,
            end_time=now,
            attributes={
                "llm.model": "gpt-4o",
                "llm.cost_usd": 0.05,
                "llm.tokens.input": 100,
                "llm.tokens.output": 50,
            },
        )

        resp = client.get("/v1/stats/trends", params={"days": 7})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["buckets"]) == 7

        # At least one bucket should have data
        non_empty = [b for b in data["buckets"] if b["trace_count"] > 0]
        assert len(non_empty) >= 1
        b = non_empty[0]
        assert b["trace_count"] == 1
        assert b["error_count"] == 0
        assert b["success_rate"] == 1.0

    def test_trends_with_errors(self, client):
        now = time.time()
        # OK trace
        _ingest_span(
            client,
            trace_id=str(uuid.uuid4()),
            span_type="agent_step",
            name="ok-step",
            start_time=now - 5,
            end_time=now,
            status="ok",
        )
        # Error trace
        _ingest_span(
            client,
            trace_id=str(uuid.uuid4()),
            span_type="agent_step",
            name="bad-step",
            start_time=now - 5,
            end_time=now,
            status="error",
            error_message="Something failed",
        )

        resp = client.get("/v1/stats/trends", params={"days": 7})
        data = resp.json()
        non_empty = [b for b in data["buckets"] if b["trace_count"] > 0]
        assert len(non_empty) >= 1
        b = non_empty[0]
        assert b["trace_count"] == 2
        assert b["error_count"] == 1
        assert b["success_rate"] == 0.5

    def test_trends_hourly_buckets(self, client):
        resp = client.get(
            "/v1/stats/trends", params={"days": 1, "bucket": "hour"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["buckets"]) == 24
        # All buckets should have the hour format
        for bucket in data["buckets"]:
            assert "T" in bucket["date"]
            assert bucket["date"].endswith(":00")

    def test_trends_no_gaps(self, client):
        """Empty days must be included with zero values."""
        resp = client.get("/v1/stats/trends", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["buckets"]) == 30
        dates = [b["date"] for b in data["buckets"]]
        # No duplicate dates
        assert len(dates) == len(set(dates))


# ---------------------------------------------------------------------------
# GET /v1/stats/top-costs
# ---------------------------------------------------------------------------


class TestTopCosts:
    def test_top_costs_empty(self, client):
        resp = client.get("/v1/stats/top-costs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["prompts"] == []

    def test_top_costs_returns_sorted(self, client):
        trace_id = str(uuid.uuid4())
        now = time.time()

        # Cheap LLM call
        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            span_type="llm_call",
            name="cheap-call",
            start_time=now - 2,
            end_time=now - 1,
            attributes={
                "llm.model": "gpt-4o-mini",
                "llm.cost_usd": 0.001,
                "llm.tokens.input": 50,
                "llm.tokens.output": 20,
            },
        )
        # Expensive LLM call
        expensive_span_id = str(uuid.uuid4())
        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=expensive_span_id,
            span_type="llm_call",
            name="expensive-call",
            start_time=now - 1,
            end_time=now,
            attributes={
                "llm.model": "gpt-4o",
                "llm.cost_usd": 0.10,
                "llm.tokens.input": 500,
                "llm.tokens.output": 200,
            },
        )

        resp = client.get("/v1/stats/top-costs")
        data = resp.json()
        assert len(data["prompts"]) == 2
        # Most expensive first
        assert data["prompts"][0]["cost"] > data["prompts"][1]["cost"]
        assert data["prompts"][0]["span_id"] == expensive_span_id
        assert data["prompts"][0]["model"] == "gpt-4o"
        assert data["prompts"][0]["tokens"] == 700

    def test_top_costs_skips_non_llm(self, client):
        """Tool spans should not appear in top-costs."""
        _ingest_span(
            client,
            span_type="tool_use",
            name="some-tool",
            attributes={"tool.name": "search"},
        )
        resp = client.get("/v1/stats/top-costs")
        assert resp.json()["prompts"] == []

    def test_top_costs_respects_limit(self, client):
        trace_id = str(uuid.uuid4())
        now = time.time()
        for i in range(5):
            _ingest_span(
                client,
                trace_id=trace_id,
                span_id=str(uuid.uuid4()),
                span_type="llm_call",
                name=f"call-{i}",
                start_time=now - i - 1,
                end_time=now - i,
                attributes={
                    "llm.model": "gpt-4o",
                    "llm.cost_usd": 0.01 * (i + 1),
                    "llm.tokens.input": 100,
                    "llm.tokens.output": 50,
                },
            )

        resp = client.get("/v1/stats/top-costs", params={"limit": 3})
        assert len(resp.json()["prompts"]) == 3


# ---------------------------------------------------------------------------
# GET /v1/stats/top-duration
# ---------------------------------------------------------------------------


class TestTopDuration:
    def test_top_duration_empty(self, client):
        resp = client.get("/v1/stats/top-duration")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tools"] == []

    def test_top_duration_returns_sorted(self, client):
        trace_id = str(uuid.uuid4())
        now = time.time()

        # Fast tool
        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            span_type="tool_use",
            name="fast-tool",
            start_time=now - 0.5,
            end_time=now,
        )
        # Slow tool
        slow_span_id = str(uuid.uuid4())
        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=slow_span_id,
            span_type="tool_use",
            name="slow-tool",
            start_time=now - 5.0,
            end_time=now,
        )

        resp = client.get("/v1/stats/top-duration")
        data = resp.json()
        assert len(data["tools"]) == 2
        # Slowest first
        assert data["tools"][0]["duration_ms"] > data["tools"][1]["duration_ms"]
        assert data["tools"][0]["span_id"] == slow_span_id
        assert data["tools"][0]["name"] == "slow-tool"

    def test_top_duration_skips_llm_calls(self, client):
        """LLM call spans should not appear in top-duration."""
        _ingest_span(
            client,
            span_type="llm_call",
            name="openai.chat",
            attributes={"llm.model": "gpt-4o"},
        )
        resp = client.get("/v1/stats/top-duration")
        assert resp.json()["tools"] == []

    def test_top_duration_respects_limit(self, client):
        trace_id = str(uuid.uuid4())
        now = time.time()
        for i in range(5):
            _ingest_span(
                client,
                trace_id=trace_id,
                span_id=str(uuid.uuid4()),
                span_type="tool_use",
                name=f"tool-{i}",
                start_time=now - (i + 1),
                end_time=now,
            )

        resp = client.get("/v1/stats/top-duration", params={"limit": 2})
        assert len(resp.json()["tools"]) == 2
