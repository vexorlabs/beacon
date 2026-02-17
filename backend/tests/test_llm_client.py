"""Tests for the shared LLM client module."""

from __future__ import annotations

import pytest

from app.services.llm_client import (
    PRICE_TABLE,
    MODEL_PROVIDER,
    estimate_cost,
    provider_for_model,
)


class TestEstimateCost:
    def test_known_model(self) -> None:
        # gpt-4.1: $2.00/1M input, $8.00/1M output
        cost = estimate_cost("gpt-4.1", 1_000_000, 1_000_000)
        assert cost == pytest.approx(10.0)

    def test_fractional_tokens(self) -> None:
        cost = estimate_cost("gpt-4.1", 500, 100)
        expected = (500 / 1_000_000) * 2.00 + (100 / 1_000_000) * 8.00
        assert cost == pytest.approx(expected)

    def test_unknown_model_returns_zero(self) -> None:
        assert estimate_cost("unknown-model", 1000, 500) == 0.0

    def test_zero_tokens(self) -> None:
        assert estimate_cost("gpt-4.1", 0, 0) == 0.0

    def test_anthropic_model(self) -> None:
        # claude-sonnet-4-6: $3.00/1M input, $15.00/1M output
        cost = estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)


class TestProviderForModel:
    def test_openai_known(self) -> None:
        assert provider_for_model("gpt-4.1") == "openai"
        assert provider_for_model("gpt-4o") == "openai"
        assert provider_for_model("o3") == "openai"
        assert provider_for_model("o4-mini") == "openai"

    def test_anthropic_known(self) -> None:
        assert provider_for_model("claude-sonnet-4-6") == "anthropic"
        assert provider_for_model("claude-opus-4-6") == "anthropic"

    def test_openai_prefix_fallback(self) -> None:
        assert provider_for_model("gpt-5-future") == "openai"
        assert provider_for_model("o3-new-variant") == "openai"

    def test_anthropic_prefix_fallback(self) -> None:
        assert provider_for_model("claude-future-model") == "anthropic"

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown model"):
            provider_for_model("llama-3")


class TestRegistryConsistency:
    def test_price_table_and_provider_have_same_keys(self) -> None:
        """PRICE_TABLE and MODEL_PROVIDER must stay in sync."""
        assert set(PRICE_TABLE.keys()) == set(MODEL_PROVIDER.keys())
