from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from contextvars import Token
from typing import Any, Generator

from beacon_sdk.context import (
    TraceContext,
    get_context,
    register_span,
    reset_context,
    set_context,
    unregister_span,
)
from beacon_sdk.exporters import SpanExporter
from beacon_sdk.models import Span, SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")


class BeaconTracer:
    """Creates and manages spans within a trace context."""

    def __init__(
        self,
        exporter: SpanExporter | None = None,
        enabled: bool = True,
    ) -> None:
        self._exporter = exporter
        self._enabled = enabled

    def start_span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        attributes: dict[str, Any] | None = None,
    ) -> tuple[Span, Token[TraceContext | None]]:
        """Start a new span. Returns (span, context_token)."""
        current_ctx = get_context()

        if current_ctx is not None:
            trace_id = current_ctx.trace_id
            parent_span_id = current_ctx.span_id
        else:
            trace_id = str(uuid.uuid4())
            parent_span_id = None

        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            span_type=span_type,
            name=name,
            attributes=attributes or {},
        )

        new_ctx = TraceContext(trace_id=trace_id, span_id=span.span_id)
        token = set_context(new_ctx)
        register_span(span)

        return span, token

    def end_span(
        self,
        span: Span,
        token: Token[TraceContext | None],
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        """End a span, restore context, and export."""
        try:
            span.end(status=status, error_message=error_message)
        except Exception as exc:
            logger.debug("Beacon: failed to finalize span: %s", exc)
        finally:
            reset_context(token)
            unregister_span(span.span_id)

        if self._enabled and self._exporter is not None:
            try:
                self._exporter.export([span])
            except Exception as exc:
                logger.debug(
                    "Beacon: span export failed (non-fatal): %s", exc
                )

    @contextmanager
    def span(
        self,
        name: str,
        span_type: SpanType = SpanType.CUSTOM,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """Context manager for spans."""
        span, token = self.start_span(
            name, span_type=span_type, attributes=attributes
        )
        try:
            yield span
            self.end_span(span, token, status=SpanStatus.OK)
        except Exception as exc:
            self.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise
