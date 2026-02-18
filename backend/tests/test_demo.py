"""Tests for the demo agent router and service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services import settings_service


@pytest.fixture(autouse=True)
def _mock_ws_manager() -> None:
    """Prevent WebSocket broadcast from failing in tests."""
    with patch("app.services.demo_service.ws_manager") as mock_ws:
        mock_ws.broadcast_span = AsyncMock()
        mock_ws.broadcast_trace_created = AsyncMock()
        yield


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Redirect config file to a temp directory."""
    config_path = tmp_path / ".beacon" / "config.json"
    monkeypatch.setattr(settings_service, "_CONFIG_PATH", config_path)


class TestDemoScenarios:
    def test_list_scenarios_returns_three(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/v1/demo/scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) == 3
        keys = {s["key"] for s in scenarios}
        assert keys == {"research_assistant", "code_reviewer", "trip_planner"}

    def test_list_scenarios_has_required_fields(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/v1/demo/scenarios")
        for s in response.json():
            assert "key" in s
            assert "name" in s
            assert "description" in s
            assert "provider" in s
            assert "model" in s
            assert "api_key_configured" in s

    def test_list_scenarios_no_api_key_shows_unconfigured(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/v1/demo/scenarios")
        for s in response.json():
            assert s["api_key_configured"] is False

    def test_list_scenarios_with_api_key_shows_configured(self, client) -> None:  # type: ignore[no-untyped-def]
        settings_service.set_api_key("openai", "sk-test-key")
        response = client.get("/v1/demo/scenarios")
        for s in response.json():
            if s["provider"] == "openai":
                assert s["api_key_configured"] is True
            else:
                assert s["api_key_configured"] is False


class TestDemoRun:
    def test_run_invalid_scenario_returns_400(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/demo/run", json={"scenario": "nonexistent"}
        )
        assert response.status_code == 400
        assert "Unknown scenario" in response.json()["detail"]

    def test_run_without_api_key_returns_400(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post(
            "/v1/demo/run", json={"scenario": "research_assistant"}
        )
        assert response.status_code == 400
        assert "No API key configured" in response.json()["detail"]

    @patch("app.services.demo_service._run_agent_loop", new_callable=AsyncMock)
    def test_run_valid_scenario_returns_trace_id(
        self, mock_loop, client, db_session  # type: ignore[no-untyped-def]
    ) -> None:
        settings_service.set_api_key("openai", "sk-test-key")
        response = client.post(
            "/v1/demo/run", json={"scenario": "research_assistant"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert len(data["trace_id"]) == 36  # UUID format

    @patch("app.services.demo_service._run_agent_loop", new_callable=AsyncMock)
    def test_run_creates_root_span_in_db(
        self, mock_loop, client, db_session  # type: ignore[no-untyped-def]
    ) -> None:
        settings_service.set_api_key("openai", "sk-test-key")
        response = client.post(
            "/v1/demo/run", json={"scenario": "research_assistant"}
        )
        trace_id = response.json()["trace_id"]

        from app import models

        spans = (
            db_session.query(models.Span)
            .filter_by(trace_id=trace_id)
            .all()
        )
        assert len(spans) == 1
        assert spans[0].span_type == "agent_step"
        assert spans[0].name == "Research Assistant"

    @patch("app.services.demo_service._run_agent_loop", new_callable=AsyncMock)
    def test_run_fires_background_task(
        self, mock_loop, client  # type: ignore[no-untyped-def]
    ) -> None:
        settings_service.set_api_key("anthropic", "sk-ant-test")
        response = client.post(
            "/v1/demo/run", json={"scenario": "code_reviewer"}
        )
        assert response.status_code == 200
        mock_loop.assert_called_once()

    def test_run_missing_body_returns_422(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.post("/v1/demo/run", json={})
        assert response.status_code == 422
