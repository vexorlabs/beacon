"""Tests for analysis infrastructure and /v1/analysis/* endpoints."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.services.analysis_service import build_trace_context, parse_structured_response
from app.schemas import (
    RootCauseAnalysisResponse,
    CostOptimizationResponse,
    TraceSummaryAnalysisResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_span(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "span_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "parent_span_id": None,
        "span_type": "llm_call",
        "name": "openai.chat.completions",
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
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_root_cause_analysis_response(self):
        data = {
            "trace_id": "abc-123",
            "root_cause": "Rate limit exceeded on OpenAI API",
            "affected_spans": ["span-1", "span-2"],
            "confidence": 0.85,
            "suggested_fix": "Add retry logic with exponential backoff",
        }
        result = RootCauseAnalysisResponse.model_validate(data)
        assert result.root_cause == "Rate limit exceeded on OpenAI API"
        assert result.confidence == 0.85
        assert len(result.affected_spans) == 2

    def test_cost_optimization_response(self):
        data = {
            "trace_ids": ["t1"],
            "suggestions": [
                {
                    "type": "model_downgrade",
                    "description": "Use gpt-4o-mini instead of gpt-4o for classification",
                    "estimated_savings_usd": 0.015,
                    "affected_spans": ["span-1"],
                }
            ],
        }
        result = CostOptimizationResponse.model_validate(data)
        assert len(result.suggestions) == 1
        assert result.suggestions[0].estimated_savings_usd == 0.015

    def test_trace_summary_analysis_response(self):
        data = {
            "trace_id": "abc-123",
            "summary": "The agent called GPT-4o twice and returned results.",
            "key_events": [
                {"span_id": "s1", "description": "Initial LLM call"},
                {"span_id": "s2", "description": "Tool invocation"},
            ],
        }
        result = TraceSummaryAnalysisResponse.model_validate(data)
        assert "GPT-4o" in result.summary
        assert len(result.key_events) == 2


# ---------------------------------------------------------------------------
# build_trace_context tests
# ---------------------------------------------------------------------------


class TestBuildTraceContext:
    def test_empty_spans(self):
        result = build_trace_context([])
        assert result == "No spans in this trace."

    def test_formats_basic_span(self):
        """Verify build_trace_context using a mock span object."""

        class MockSpan:
            span_id = "span-001"
            name = "openai.chat.completions"
            span_type = "llm_call"
            status = "ok"
            parent_span_id = None
            start_time = 1700000000.0
            end_time = 1700000001.5
            error_message = None
            attributes = json.dumps({
                "llm.model": "gpt-4o",
                "llm.tokens.input": 100,
                "llm.tokens.output": 50,
            })

        result = build_trace_context([MockSpan()])
        assert "span-001" in result
        assert "openai.chat.completions" in result
        assert "llm_call" in result
        assert "1500.0" in result  # duration_ms
        assert "gpt-4o" in result

    def test_formats_error_span(self):
        class MockSpan:
            span_id = "span-err"
            name = "failing-tool"
            span_type = "tool_use"
            status = "error"
            parent_span_id = "span-parent"
            start_time = 1700000000.0
            end_time = 1700000002.0
            error_message = "Connection timeout"
            attributes = "{}"

        result = build_trace_context([MockSpan()])
        assert "error" in result
        assert "Connection timeout" in result
        assert "span-parent" in result


# ---------------------------------------------------------------------------
# parse_structured_response tests
# ---------------------------------------------------------------------------


class TestParseStructuredResponse:
    def test_parses_clean_json(self):
        raw = json.dumps({
            "trace_id": "t1",
            "summary": "Agent completed successfully.",
            "key_events": [],
        })
        result = parse_structured_response(raw, TraceSummaryAnalysisResponse)
        assert result.summary == "Agent completed successfully."

    def test_parses_json_with_code_fences(self):
        raw = '```json\n{"trace_id": "t1", "summary": "Done.", "key_events": []}\n```'
        result = parse_structured_response(raw, TraceSummaryAnalysisResponse)
        assert result.summary == "Done."

    def test_parses_json_with_leading_text(self):
        raw = 'Here is the analysis:\n{"trace_id": "t1", "summary": "OK.", "key_events": []}'
        result = parse_structured_response(raw, TraceSummaryAnalysisResponse)
        assert result.summary == "OK."

    def test_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_structured_response("not json at all", TraceSummaryAnalysisResponse)

    def test_raises_on_schema_mismatch(self):
        raw = json.dumps({"wrong_field": "value"})
        with pytest.raises(ValueError, match="does not match expected schema"):
            parse_structured_response(raw, TraceSummaryAnalysisResponse)


# ---------------------------------------------------------------------------
# Router integration tests (with mocked LLM)
# ---------------------------------------------------------------------------


MOCK_ROOT_CAUSE_RESPONSE = json.dumps({
    "trace_id": "placeholder",
    "root_cause": "The OpenAI API returned a rate limit error",
    "affected_spans": ["span-1"],
    "confidence": 0.9,
    "suggested_fix": "Add retry logic with backoff",
})

MOCK_SUMMARY_RESPONSE = json.dumps({
    "trace_id": "placeholder",
    "summary": "The agent called GPT-4o and completed successfully in 1.5s.",
    "key_events": [
        {"span_id": "span-1", "description": "LLM call to GPT-4o"},
    ],
})


class TestAnalysisRouter:
    def _setup_trace(self, client: TestClient) -> tuple[str, str]:
        """Ingest a trace with two spans and return (trace_id, span_id)."""
        trace_id = str(uuid.uuid4())
        span_id_1 = str(uuid.uuid4())
        span_id_2 = str(uuid.uuid4())

        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=span_id_1,
            name="agent-step",
            span_type="agent_step",
        )
        _ingest_span(
            client,
            trace_id=trace_id,
            span_id=span_id_2,
            parent_span_id=span_id_1,
            name="openai.chat",
            span_type="llm_call",
            status="error",
            error_message="Rate limit exceeded",
            attributes={"llm.model": "gpt-4o", "llm.prompt": "Hello"},
        )
        return trace_id, span_id_2

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=MOCK_ROOT_CAUSE_RESPONSE,
    )
    def test_root_cause_analysis(self, mock_llm, client):
        trace_id, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/root-cause",
            json={"trace_id": trace_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id"] == trace_id
        assert "rate limit" in data["root_cause"].lower()
        assert data["confidence"] == 0.9
        mock_llm.assert_called_once()

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=MOCK_SUMMARY_RESPONSE,
    )
    def test_summarize_trace(self, mock_llm, client):
        trace_id, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/summarize",
            json={"trace_id": trace_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id"] == trace_id
        assert "GPT-4o" in data["summary"]
        assert len(data["key_events"]) >= 1
        mock_llm.assert_called_once()

    def test_root_cause_analysis_trace_not_found(self, client):
        resp = client.post(
            "/v1/analysis/root-cause",
            json={"trace_id": "nonexistent-trace"},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=json.dumps({
            "trace_ids": ["placeholder"],
            "suggestions": [
                {
                    "type": "model_downgrade",
                    "description": "Use gpt-4o-mini for simple tasks",
                    "estimated_savings_usd": 0.02,
                    "affected_spans": ["s1"],
                }
            ],
        }),
    )
    def test_cost_optimization(self, mock_llm, client):
        trace_id, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/cost-optimization",
            json={"trace_ids": [trace_id]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["type"] == "model_downgrade"

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=json.dumps({
            "span_id": "placeholder",
            "original_prompt": "Hello",
            "suggestions": [
                {
                    "category": "clarity",
                    "description": "Be more specific",
                    "improved_prompt_snippet": "You are a helpful assistant. Hello.",
                }
            ],
        }),
    )
    def test_prompt_suggestions(self, mock_llm, client):
        trace_id, span_id = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/prompt-suggestions",
            json={"span_id": span_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["span_id"] == span_id
        assert len(data["suggestions"]) == 1

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=json.dumps({
            "trace_id": "placeholder",
            "anomalies": [],
        }),
    )
    def test_anomaly_detection_no_anomalies(self, mock_llm, client):
        trace_id, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/anomalies",
            json={"trace_id": trace_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["anomalies"] == []

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=json.dumps({
            "patterns": [],
        }),
    )
    def test_error_patterns_empty(self, mock_llm, client):
        trace_id, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/error-patterns",
            json={"trace_ids": [trace_id]},
        )
        assert resp.status_code == 200
        assert resp.json()["patterns"] == []

    @patch(
        "app.services.analysis_service.call_analysis_llm",
        new_callable=AsyncMock,
        return_value=json.dumps({
            "trace_id_a": "a",
            "trace_id_b": "b",
            "divergence_points": [],
            "metric_diff": {
                "cost_diff_usd": 0.01,
                "duration_diff_ms": 500.0,
                "token_diff": 200,
                "span_count_diff": 1,
            },
            "summary": "Traces are structurally similar.",
        }),
    )
    def test_compare_traces(self, mock_llm, client):
        trace_id_a, _ = self._setup_trace(client)
        trace_id_b, _ = self._setup_trace(client)

        resp = client.post(
            "/v1/analysis/compare",
            json={"trace_id_a": trace_id_a, "trace_id_b": trace_id_b},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id_a"] == trace_id_a
        assert data["trace_id_b"] == trace_id_b
        assert "similar" in data["summary"].lower()
