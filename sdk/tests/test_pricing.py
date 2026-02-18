"""Tests for the unified pricing module."""

from __future__ import annotations

import pytest

from beacon_sdk.pricing import PRICE_TABLE, estimate_cost


class TestEstimateCost:
    def test_known_openai_model(self) -> None:
        cost = estimate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == pytest.approx(12.50)  # 2.50 + 10.00

    def test_known_anthropic_model(self) -> None:
        cost = estimate_cost("claude-sonnet-4", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.00)  # 3.00 + 15.00

    def test_prefix_matching_anthropic_dated(self) -> None:
        """API responses include date suffixes; prefix matching handles them."""
        cost = estimate_cost("claude-sonnet-4-6-20250514", 1000, 500)
        assert cost > 0

    def test_prefix_matching_openai_dated(self) -> None:
        cost = estimate_cost("gpt-4o-2024-11-20", 1000, 500)
        assert cost > 0

    def test_unknown_model_returns_zero(self) -> None:
        assert estimate_cost("unknown-model", 1000, 500) == 0.0

    def test_zero_tokens(self) -> None:
        assert estimate_cost("gpt-4o", 0, 0) == 0.0

    def test_fractional_tokens(self) -> None:
        cost = estimate_cost("gpt-4.1", 500, 100)
        expected = (500 / 1_000_000) * 2.00 + (100 / 1_000_000) * 8.00
        assert cost == pytest.approx(expected)

    def test_all_entries_produce_nonzero(self) -> None:
        """Every entry in PRICE_TABLE should estimate > 0."""
        for model in PRICE_TABLE:
            cost = estimate_cost(model, 1000, 1000)
            assert cost > 0, f"Model {model} returned zero cost"


class TestPrefixOrdering:
    """Verify that more-specific prefixes match before less-specific ones."""

    def test_gpt4o_mini_cheaper_than_gpt4o(self) -> None:
        cost_mini = estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        cost_full = estimate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost_mini < cost_full

    def test_gpt41_mini_cheaper_than_gpt41(self) -> None:
        cost_mini = estimate_cost("gpt-4.1-mini", 1_000_000, 1_000_000)
        cost_full = estimate_cost("gpt-4.1", 1_000_000, 1_000_000)
        assert cost_mini < cost_full

    def test_gpt41_nano_cheaper_than_gpt41_mini(self) -> None:
        cost_nano = estimate_cost("gpt-4.1-nano", 1_000_000, 1_000_000)
        cost_mini = estimate_cost("gpt-4.1-mini", 1_000_000, 1_000_000)
        assert cost_nano < cost_mini

    def test_o3_mini_cheaper_than_o3(self) -> None:
        cost_mini = estimate_cost("o3-mini", 1_000_000, 1_000_000)
        cost_full = estimate_cost("o3", 1_000_000, 1_000_000)
        assert cost_mini < cost_full

    def test_o1_mini_cheaper_than_o1(self) -> None:
        cost_mini = estimate_cost("o1-mini", 1_000_000, 1_000_000)
        cost_full = estimate_cost("o1", 1_000_000, 1_000_000)
        assert cost_mini < cost_full
