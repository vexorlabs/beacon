"""Tests for the settings service and router."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import settings_service


@pytest.fixture(autouse=True)
def _tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect config file to a temp directory for each test."""
    config_path = tmp_path / ".beacon" / "config.json"
    monkeypatch.setattr(settings_service, "_CONFIG_PATH", config_path)


class TestSettingsService:
    def test_get_api_key_no_config(self) -> None:
        assert settings_service.get_api_key("openai") is None

    def test_set_and_get_api_key(self) -> None:
        settings_service.set_api_key("openai", "sk-test-123")
        assert settings_service.get_api_key("openai") == "sk-test-123"

    def test_set_unsupported_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported provider"):
            settings_service.set_api_key("cohere", "key-123")

    def test_delete_api_key(self) -> None:
        settings_service.set_api_key("openai", "sk-test-123")
        settings_service.delete_api_key("openai")
        assert settings_service.get_api_key("openai") is None

    def test_delete_nonexistent_key_is_noop(self) -> None:
        # Should not raise
        settings_service.delete_api_key("openai")

    def test_list_providers(self) -> None:
        providers = settings_service.list_providers()
        assert len(providers) == 3
        names = [p["provider"] for p in providers]
        assert "openai" in names
        assert "anthropic" in names
        assert "google" in names
        # Nothing configured yet
        assert all(not p["configured"] for p in providers)

    def test_list_providers_after_set(self) -> None:
        settings_service.set_api_key("openai", "sk-test-key-1234")
        providers = settings_service.list_providers()
        openai_status = next(p for p in providers if p["provider"] == "openai")
        assert openai_status["configured"] is True
        assert openai_status["masked_key"] is not None
        assert openai_status["masked_key"].endswith("1234")

    def test_file_permissions(self) -> None:
        settings_service.set_api_key("openai", "sk-test")
        config_path = settings_service._CONFIG_PATH
        mode = oct(os.stat(config_path).st_mode & 0o777)
        assert mode == "0o600"

    def test_corrupt_config_returns_empty(self, tmp_path: Path) -> None:
        config_path = settings_service._CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("not valid json {{{")
        assert settings_service.get_api_key("openai") is None

    def test_mask_key(self) -> None:
        # "sk-abcdefghij" = 13 chars, mask first 9
        assert settings_service._mask_key("sk-abcdefghij") == "•••••••••ghij"
        assert settings_service._mask_key("ab") == "****"
        assert settings_service._mask_key("abcd") == "****"
        assert settings_service._mask_key("abcde") == "•bcde"


class TestSettingsRouter:
    def test_list_api_keys(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.get("/v1/settings/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_set_api_key(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.put(
            "/v1/settings/api-keys",
            json={"provider": "openai", "api_key": "sk-test-123"},
        )
        assert response.status_code == 200
        assert response.json()["configured"] is True

    def test_set_unsupported_provider(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.put(
            "/v1/settings/api-keys",
            json={"provider": "cohere", "api_key": "key-123"},
        )
        assert response.status_code == 400

    def test_delete_api_key(self, client) -> None:  # type: ignore[no-untyped-def]
        # Set then delete
        client.put(
            "/v1/settings/api-keys",
            json={"provider": "openai", "api_key": "sk-test-123"},
        )
        response = client.delete("/v1/settings/api-keys/openai")
        assert response.status_code == 200
        assert response.json()["configured"] is False

    def test_delete_unsupported_provider(self, client) -> None:  # type: ignore[no-untyped-def]
        response = client.delete("/v1/settings/api-keys/cohere")
        assert response.status_code == 400
