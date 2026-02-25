"""Tests for the playground service and router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services import settings_service


@pytest.fixture(autouse=True)
def _mock_ws_manager() -> None:
    """Prevent WebSocket broadcast from failing in tests."""
    with patch("app.services.playground_service.ws_manager") as mock_ws:
        mock_ws.broadcast_span = AsyncMock()
        mock_ws.broadcast_trace_created = AsyncMock()
        yield


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Redirect config file to a temp directory."""
    config_path = tmp_path / ".beacon" / "config.json"
    monkeypatch.setattr(settings_service, "_CONFIG_PATH", config_path)


class TestPlaygroundRouter:
    def test_chat_no_api_key(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/playground/chat",
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 400
        assert "No API key configured" in response.json()["detail"]

    def test_chat_invalid_role(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/playground/chat",
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "invalid", "content": "Hello"}],
            },
        )
        assert response.status_code == 422  # Pydantic validation error

    @patch("app.services.playground_service.call_openai", new_callable=AsyncMock)
    def test_chat_success(self, mock_call, client) -> None:  # type: ignore[no-untyped-def]
        # Configure API key
        settings_service.set_api_key("openai", "sk-test-key")

        # Mock LLM response
        mock_call.return_value = ("Hello there!", 10, 5)

        response = client.post(
            "/v1/playground/chat",
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"]["role"] == "assistant"
        assert data["message"]["content"] == "Hello there!"
        assert data["metrics"]["input_tokens"] == 10
        assert data["metrics"]["output_tokens"] == 5
        assert data["trace_id"] is not None
        assert data["conversation_id"] is not None

    @patch("app.services.playground_service.call_openai", new_callable=AsyncMock)
    def test_chat_creates_spans(self, mock_call, client, db_session) -> None:  # type: ignore[no-untyped-def]
        settings_service.set_api_key("openai", "sk-test-key")
        mock_call.return_value = ("Response", 10, 5)

        response = client.post(
            "/v1/playground/chat",
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "user", "content": "Test"}],
            },
        )
        assert response.status_code == 200
        trace_id = response.json()["trace_id"]

        # Verify spans were created in DB
        from app import models

        spans = db_session.query(models.Span).filter_by(trace_id=trace_id).all()
        assert len(spans) >= 2  # parent + llm_call

        span_types = {s.span_type for s in spans}
        assert "agent_step" in span_types
        assert "llm_call" in span_types

    @patch("app.services.playground_service.call_openai", new_callable=AsyncMock)
    def test_chat_error_sets_error_status(self, mock_call, client, db_session) -> None:  # type: ignore[no-untyped-def]
        settings_service.set_api_key("openai", "sk-test-key")
        mock_call.side_effect = ValueError("API Error")

        response = client.post(
            "/v1/playground/chat",
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "user", "content": "Test"}],
            },
        )
        assert response.status_code == 400

        # Verify spans got ERROR status (not stuck at UNSET)
        from app import models

        spans = db_session.query(models.Span).all()
        for span in spans:
            assert span.status == "error"

    def test_compare_requires_two_models(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/playground/compare",
            json={
                "models": ["gpt-4.1"],
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 400
        assert "at least 2 models" in response.json()["detail"]

    @patch("app.services.playground_service.call_anthropic", new_callable=AsyncMock)
    @patch("app.services.playground_service.call_openai", new_callable=AsyncMock)
    def test_compare_success(self, mock_openai, mock_anthropic, client) -> None:  # type: ignore[no-untyped-def]
        settings_service.set_api_key("openai", "sk-test")
        settings_service.set_api_key("anthropic", "sk-ant-test")

        mock_openai.return_value = ("OpenAI response", 10, 20)
        mock_anthropic.return_value = ("Anthropic response", 15, 25)

        response = client.post(
            "/v1/playground/compare",
            json={
                "models": ["gpt-4.1", "claude-sonnet-4-6"],
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["model"] == "gpt-4.1"
        assert data["results"][1]["model"] == "claude-sonnet-4-6"
        assert data["trace_id"] is not None

    # --- Compare prompts (A/B test) ---

    def test_compare_prompts_requires_two_prompts(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/playground/compare-prompts",
            json={
                "model": "gpt-4.1",
                "prompts": ["Only one prompt"],
            },
        )
        assert response.status_code == 422  # Pydantic min_length validation

    def test_compare_prompts_rejects_too_many(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/playground/compare-prompts",
            json={
                "model": "gpt-4.1",
                "prompts": [f"Prompt {i}" for i in range(11)],
            },
        )
        assert response.status_code == 422  # Pydantic max_length validation

    @patch("app.services.playground_service.call_openai", new_callable=AsyncMock)
    def test_compare_prompts_success(self, mock_call, client) -> None:  # type: ignore[no-untyped-def]
        settings_service.set_api_key("openai", "sk-test")
        mock_call.return_value = ("LLM response", 10, 20)

        response = client.post(
            "/v1/playground/compare-prompts",
            json={
                "model": "gpt-4.1",
                "prompts": ["Prompt A", "Prompt B"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["prompt"] == "Prompt A"
        assert data["results"][1]["prompt"] == "Prompt B"
        assert data["trace_id"] is not None
        assert data["test_id"] is not None
        assert data["results"][0]["metrics"]["input_tokens"] == 10
