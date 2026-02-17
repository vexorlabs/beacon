"""Manage API keys stored in ~/.beacon/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path.home() / ".beacon" / "config.json"

_SUPPORTED_PROVIDERS = ("openai", "anthropic")


def _read_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    return json.loads(_CONFIG_PATH.read_text())  # type: ignore[no-any-return]


def _write_config(config: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_api_key(provider: str) -> str | None:
    """Return the stored API key for a provider, or None."""
    config = _read_config()
    keys: dict[str, str] = config.get("api_keys", {})
    return keys.get(provider)


def set_api_key(provider: str, api_key: str) -> None:
    """Store an API key for a provider."""
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    config = _read_config()
    if "api_keys" not in config:
        config["api_keys"] = {}
    config["api_keys"][provider] = api_key
    _write_config(config)


def delete_api_key(provider: str) -> None:
    """Remove an API key for a provider."""
    config = _read_config()
    keys: dict[str, str] = config.get("api_keys", {})
    keys.pop(provider, None)
    _write_config(config)


def _mask_key(key: str) -> str:
    """Mask all but the last 4 characters."""
    if len(key) <= 4:
        return "****"
    return "•" * (len(key) - 4) + key[-4:]


def list_providers() -> list[dict[str, Any]]:
    """Return status of all supported providers."""
    config = _read_config()
    keys: dict[str, str] = config.get("api_keys", {})
    result: list[dict[str, Any]] = []
    for provider in _SUPPORTED_PROVIDERS:
        key = keys.get(provider)
        result.append(
            {
                "provider": provider,
                "configured": key is not None and len(key) > 0,
                "masked_key": _mask_key(key) if key else None,
            }
        )
    return result
