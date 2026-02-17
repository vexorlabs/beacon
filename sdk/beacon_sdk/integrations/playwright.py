"""Playwright auto-instrumentation. Patches Page methods to create browser action spans."""

from __future__ import annotations

import base64
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False

# Store originals for both sync and async Page classes
_originals_sync: dict[str, Any] = {}
_originals_async: dict[str, Any] = {}

_METHODS_TO_PATCH = ["goto", "click", "fill", "type", "screenshot", "wait_for_selector"]

_METHOD_ACTION_MAP: dict[str, str] = {
    "goto": "navigate",
    "click": "click",
    "fill": "fill",
    "type": "type",
    "screenshot": "screenshot",
    "wait_for_selector": "wait_for_selector",
}


def _make_sync_wrapper(method_name: str, original: Any) -> Any:
    """Create a sync wrapper for a Playwright Page method."""
    action = _METHOD_ACTION_MAP[method_name]

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        span, token = tracer.start_span(
            name=f"playwright.{action}",
            span_type=SpanType.BROWSER_ACTION,
        )
        span.set_attribute("browser.action", action)

        # Extract URL from the page if available
        try:
            span.set_attribute("browser.url", self.url)
        except Exception:
            pass

        # Method-specific attributes from positional args
        if method_name == "goto" and args:
            span.set_attribute("browser.url", args[0])
        elif method_name in ("click", "wait_for_selector") and args:
            span.set_attribute("browser.selector", args[0])
        elif method_name == "fill" and len(args) >= 2:
            span.set_attribute("browser.selector", args[0])
            span.set_attribute("browser.value", args[1])
        elif method_name == "type" and len(args) >= 2:
            span.set_attribute("browser.selector", args[0])
            span.set_attribute("browser.value", args[1])

        try:
            result = original(self, *args, **kwargs)

            if method_name == "screenshot" and isinstance(result, bytes):
                b64 = base64.b64encode(result).decode("ascii")
                span.set_attribute("browser.screenshot", b64)

            if method_name == "goto":
                try:
                    span.set_attribute("browser.url", self.url)
                except Exception:
                    pass

            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_async_wrapper(method_name: str, original: Any) -> Any:
    """Create an async wrapper for a Playwright async Page method."""
    action = _METHOD_ACTION_MAP[method_name]

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, *args, **kwargs)

        span, token = tracer.start_span(
            name=f"playwright.{action}",
            span_type=SpanType.BROWSER_ACTION,
        )
        span.set_attribute("browser.action", action)

        try:
            span.set_attribute("browser.url", self.url)
        except Exception:
            pass

        if method_name == "goto" and args:
            span.set_attribute("browser.url", args[0])
        elif method_name in ("click", "wait_for_selector") and args:
            span.set_attribute("browser.selector", args[0])
        elif method_name == "fill" and len(args) >= 2:
            span.set_attribute("browser.selector", args[0])
            span.set_attribute("browser.value", args[1])
        elif method_name == "type" and len(args) >= 2:
            span.set_attribute("browser.selector", args[0])
            span.set_attribute("browser.value", args[1])

        try:
            result = await original(self, *args, **kwargs)

            if method_name == "screenshot" and isinstance(result, bytes):
                b64 = base64.b64encode(result).decode("ascii")
                span.set_attribute("browser.screenshot", b64)

            if method_name == "goto":
                try:
                    span.set_attribute("browser.url", self.url)
                except Exception:
                    pass

            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def patch() -> None:
    """Monkey-patch Playwright Page classes to auto-instrument browser actions."""
    global _patched

    if _patched:
        return

    patched_any = False

    # Patch sync Page
    try:
        from playwright.sync_api import Page as SyncPage

        for method_name in _METHODS_TO_PATCH:
            if hasattr(SyncPage, method_name):
                original = getattr(SyncPage, method_name)
                _originals_sync[method_name] = original
                setattr(
                    SyncPage, method_name, _make_sync_wrapper(method_name, original)
                )
        patched_any = True
    except ImportError:
        pass

    # Patch async Page
    try:
        from playwright.async_api import Page as AsyncPage

        for method_name in _METHODS_TO_PATCH:
            if hasattr(AsyncPage, method_name):
                original = getattr(AsyncPage, method_name)
                _originals_async[method_name] = original
                setattr(
                    AsyncPage,
                    method_name,
                    _make_async_wrapper(method_name, original),
                )
        patched_any = True
    except ImportError:
        pass

    if not patched_any:
        return

    _patched = True
    logger.debug("Beacon: Playwright auto-patch applied")


def unpatch() -> None:
    """Restore original Playwright Page methods."""
    global _patched

    if not _patched:
        return

    try:
        from playwright.sync_api import Page as SyncPage

        for method_name, original in _originals_sync.items():
            setattr(SyncPage, method_name, original)
    except ImportError:
        pass

    try:
        from playwright.async_api import Page as AsyncPage

        for method_name, original in _originals_async.items():
            setattr(AsyncPage, method_name, original)
    except ImportError:
        pass

    _originals_sync.clear()
    _originals_async.clear()
    _patched = False
    logger.debug("Beacon: Playwright auto-patch removed")
