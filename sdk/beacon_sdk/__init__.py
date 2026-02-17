from __future__ import annotations

import logging
import os

from beacon_sdk.context import get_active_span, get_context
from beacon_sdk.decorators import observe
from beacon_sdk.exporters import HttpSpanExporter
from beacon_sdk.models import Span, SpanStatus, SpanType
from beacon_sdk.tracer import BeaconTracer

__all__ = [
    "init",
    "observe",
    "get_current_span",
    "get_tracer",
    "Span",
    "SpanType",
    "SpanStatus",
    "BeaconTracer",
]

DEFAULT_BACKEND_URL: str = "http://localhost:7474"

logger = logging.getLogger("beacon_sdk")

_tracer: BeaconTracer | None = None


def init(
    backend_url: str | None = None,
    enabled: bool | None = None,
) -> None:
    """Initialize the Beacon SDK. Call once at the top of your script."""
    global _tracer  # noqa: PLW0603

    if enabled is None:
        env_enabled = os.environ.get("BEACON_ENABLED", "true").lower()
        enabled = env_enabled != "false"

    if not enabled:
        _tracer = BeaconTracer(exporter=None, enabled=False)
        logger.debug("Beacon: tracing disabled")
        return

    resolved_url = backend_url or os.environ.get(
        "BEACON_BACKEND_URL", DEFAULT_BACKEND_URL
    )

    log_level = os.environ.get("BEACON_LOG_LEVEL", "WARNING").upper()
    logging.getLogger("beacon_sdk").setLevel(
        getattr(logging, log_level, logging.WARNING)
    )

    exporter = HttpSpanExporter(backend_url=resolved_url)
    _tracer = BeaconTracer(exporter=exporter, enabled=True)

    logger.debug("Beacon: initialized, sending spans to %s", resolved_url)


def get_tracer() -> BeaconTracer | None:
    """Get the global BeaconTracer instance."""
    return _tracer


def _get_tracer() -> BeaconTracer | None:
    """Internal helper for decorators."""
    return _tracer


def get_current_span() -> Span | None:
    """Get the currently active span from context."""
    ctx = get_context()
    if ctx is None or ctx.span_id is None:
        return None
    return get_active_span(ctx.span_id)
