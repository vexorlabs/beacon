from __future__ import annotations

import atexit
import logging
import os
from typing import Literal

from beacon_sdk.context import get_active_span, get_context
from beacon_sdk.decorators import observe
from beacon_sdk.exporters import (
    AsyncBatchExporter,
    FlushableExporter,
    HttpSpanExporter,
)
from beacon_sdk.models import Span, SpanStatus, SpanType
from beacon_sdk.tracer import BeaconTracer

__all__ = [
    "init",
    "flush",
    "shutdown",
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
_atexit_registered: bool = False


def init(
    backend_url: str | None = None,
    auto_patch: bool | None = None,
    enabled: bool | None = None,
    exporter: Literal["sync", "async", "auto"] | None = None,
) -> None:
    """Initialize the Beacon SDK. Call once at the top of your script.

    Args:
        backend_url: Beacon backend URL. Defaults to BEACON_BACKEND_URL env var
            or http://localhost:7474.
        auto_patch: Auto-patch supported libraries. Defaults to BEACON_AUTO_PATCH
            env var or True.
        enabled: Enable tracing. Defaults to BEACON_ENABLED env var or True.
        exporter: Exporter mode — "sync" (blocking HTTP per span), "async"
            (batched background thread), or "auto" (default, uses async).
    """
    global _tracer, _atexit_registered  # noqa: PLW0603

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

    # Shut down the previous exporter to avoid leaking background threads
    if _tracer is not None and _tracer._exporter is not None:
        old_exp = _tracer._exporter
        if isinstance(old_exp, FlushableExporter):
            try:
                old_exp.shutdown()
            except Exception:
                pass

    exporter_mode = exporter or "auto"
    if exporter_mode == "sync":
        resolved_exporter = HttpSpanExporter(backend_url=resolved_url)
    elif exporter_mode in ("async", "auto"):
        resolved_exporter = AsyncBatchExporter(backend_url=resolved_url)
    else:
        logger.debug("Beacon: unknown exporter mode %r, using auto", exporter_mode)
        resolved_exporter = AsyncBatchExporter(backend_url=resolved_url)

    _tracer = BeaconTracer(exporter=resolved_exporter, enabled=True)

    if not _atexit_registered:
        atexit.register(_shutdown_exporter)
        _atexit_registered = True

    logger.debug(
        "Beacon: initialized (%s exporter), sending spans to %s",
        exporter_mode,
        resolved_url,
    )

    if auto_patch is None:
        env_auto = os.environ.get("BEACON_AUTO_PATCH", "true").lower()
        auto_patch = env_auto != "false"

    if auto_patch:
        _apply_auto_patches()


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


def flush() -> None:
    """Flush any pending spans to the backend."""
    if _tracer is None:
        return
    exp = _tracer._exporter
    if isinstance(exp, FlushableExporter):
        exp.flush()


def shutdown() -> None:
    """Flush pending spans and shut down the exporter."""
    if _tracer is None:
        return
    exp = _tracer._exporter
    if isinstance(exp, FlushableExporter):
        exp.shutdown()


def _shutdown_exporter() -> None:
    """atexit handler: flush and shut down the exporter if it supports it."""
    if _tracer is None:
        return
    exp = _tracer._exporter
    if isinstance(exp, FlushableExporter):
        try:
            exp.shutdown()
        except Exception:
            pass


def _apply_auto_patches() -> None:
    """Try to monkey-patch all supported libraries. Silently skip if not installed."""
    from beacon_sdk.integrations import anthropic as _anthropic_patch
    from beacon_sdk.integrations import autogen as _autogen_patch
    from beacon_sdk.integrations import crewai as _crewai_patch
    from beacon_sdk.integrations import google_genai as _google_genai_patch
    from beacon_sdk.integrations import livekit as _livekit_patch
    from beacon_sdk.integrations import llamaindex as _llamaindex_patch
    from beacon_sdk.integrations import ollama as _ollama_patch
    from beacon_sdk.integrations import openai as _openai_patch
    from beacon_sdk.integrations import playwright as _playwright_patch
    from beacon_sdk.integrations import subprocess_patch as _subprocess_patch

    for mod in [
        _openai_patch,
        _anthropic_patch,
        _google_genai_patch,
        _crewai_patch,
        _autogen_patch,
        _llamaindex_patch,
        _livekit_patch,
        _ollama_patch,
        _playwright_patch,
        _subprocess_patch,
    ]:
        try:
            mod.patch()
        except Exception:
            logger.debug("Beacon: auto-patch failed for %s", mod.__name__)

    # File operation patch is opt-in due to intrusiveness
    if os.environ.get("BEACON_PATCH_FILE_OPS", "false").lower() == "true":
        try:
            from beacon_sdk.integrations import file_patch as _file_patch

            _file_patch.patch()
        except Exception:
            logger.debug("Beacon: auto-patch failed for file_patch")
