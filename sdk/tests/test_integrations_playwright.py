"""Tests for the Playwright auto-instrumentation integration."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import playwright as playwright_patch
from beacon_sdk.models import SCREENSHOT_MAX_BYTES, SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None


class FakeSyncPage:
    """Fake Playwright sync Page for testing."""

    url: str = "about:blank"

    def goto(self, url: str, **kwargs: Any) -> None:
        self.url = url

    def click(self, selector: str, **kwargs: Any) -> None:
        pass

    def fill(self, selector: str, value: str, **kwargs: Any) -> None:
        pass

    def type(self, selector: str, text: str, **kwargs: Any) -> None:
        pass

    def screenshot(self, **kwargs: Any) -> bytes:
        return b"\x89PNG\r\n\x1a\nfake_screenshot_data"

    def wait_for_selector(self, selector: str, **kwargs: Any) -> None:
        pass


@pytest.fixture()
def _mock_playwright() -> Any:
    """Mock the playwright modules with fake Page classes."""
    sync_mod = SimpleNamespace(Page=FakeSyncPage)

    with mock_patch.dict(
        "sys.modules",
        {
            "playwright": SimpleNamespace(),
            "playwright.sync_api": sync_mod,
        },
    ):
        playwright_patch._patched = False
        playwright_patch._originals_sync.clear()
        playwright_patch._originals_async.clear()
        yield sync_mod
        playwright_patch.unpatch()
        playwright_patch._patched = False


def test_playwright_goto_creates_browser_action_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    page.goto("https://example.com")

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.BROWSER_ACTION
    assert span.name == "playwright.navigate"
    assert span.attributes["browser.action"] == "navigate"
    assert span.attributes["browser.url"] == "https://example.com"
    assert span.status == SpanStatus.OK


def test_playwright_click_creates_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    page.click("#submit-btn")

    span = exporter.spans[0]
    assert span.attributes["browser.action"] == "click"
    assert span.attributes["browser.selector"] == "#submit-btn"


def test_playwright_fill_creates_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    page.fill("#name-input", "John Doe")

    span = exporter.spans[0]
    assert span.attributes["browser.action"] == "fill"
    assert span.attributes["browser.selector"] == "#name-input"
    assert span.attributes["browser.value"] == "John Doe"


def test_playwright_type_creates_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    page.type("#search", "hello")

    span = exporter.spans[0]
    assert span.attributes["browser.action"] == "type"
    assert span.attributes["browser.selector"] == "#search"
    assert span.attributes["browser.value"] == "hello"


def test_playwright_screenshot_encodes_to_base64(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    result = page.screenshot()

    assert isinstance(result, bytes)
    span = exporter.spans[0]
    assert span.attributes["browser.action"] == "screenshot"
    expected_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake_screenshot_data").decode(
        "ascii"
    )
    assert span.attributes["browser.screenshot"] == expected_b64


def test_playwright_screenshot_over_limit_sets_none(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    # Create large screenshot data before patching
    large_data = b"x" * (SCREENSHOT_MAX_BYTES + 1)
    original_screenshot = FakeSyncPage.screenshot
    FakeSyncPage.screenshot = lambda self, **kwargs: large_data  # type: ignore[assignment]

    playwright_patch.unpatch()
    playwright_patch._patched = False
    playwright_patch._originals_sync.clear()
    playwright_patch.patch()

    page = FakeSyncPage()
    page.screenshot()

    # Restore original
    FakeSyncPage.screenshot = original_screenshot  # type: ignore[assignment]

    span = exporter.spans[0]
    # The base64 of large_data exceeds SCREENSHOT_MAX_BYTES, so set_attribute sets None
    assert span.attributes["browser.screenshot"] is None


def test_playwright_wait_for_selector_creates_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    playwright_patch.patch()
    page = FakeSyncPage()
    page.wait_for_selector(".loading-done")

    span = exporter.spans[0]
    assert span.attributes["browser.action"] == "wait_for_selector"
    assert span.attributes["browser.selector"] == ".loading-done"


def test_playwright_error_creates_error_span(
    _mock_playwright: Any, exporter: InMemoryExporter
) -> None:
    # Set up the erroring method before patching
    original_click = FakeSyncPage.click

    def error_click(self: Any, selector: str, **kwargs: Any) -> None:
        raise TimeoutError("Element not found")

    FakeSyncPage.click = error_click  # type: ignore[assignment]

    playwright_patch.unpatch()
    playwright_patch._patched = False
    playwright_patch._originals_sync.clear()
    playwright_patch.patch()

    page = FakeSyncPage()
    with pytest.raises(TimeoutError, match="Element not found"):
        page.click("#missing")

    FakeSyncPage.click = original_click  # type: ignore[assignment]

    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "Element not found"


def test_playwright_patch_is_idempotent(_mock_playwright: Any) -> None:
    playwright_patch.patch()
    first_goto = FakeSyncPage.goto
    playwright_patch.patch()
    assert FakeSyncPage.goto is first_goto


def test_playwright_unpatch_restores_original(_mock_playwright: Any) -> None:
    original_goto = FakeSyncPage.goto
    playwright_patch.patch()
    assert FakeSyncPage.goto is not original_goto
    playwright_patch.unpatch()
    assert FakeSyncPage.goto is original_goto
