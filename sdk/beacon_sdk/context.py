from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

from beacon_sdk.models import Span


@dataclass
class TraceContext:
    """Holds the current trace_id and active span_id."""

    trace_id: str
    span_id: str | None = None


_trace_context: ContextVar[TraceContext | None] = ContextVar(
    "beacon_trace_context", default=None
)

# Active span registry — needed for get_current_span()
_active_spans: dict[str, Span] = {}


def get_context() -> TraceContext | None:
    return _trace_context.get()


def set_context(ctx: TraceContext) -> Token[TraceContext | None]:
    return _trace_context.set(ctx)


def reset_context(token: Token[TraceContext | None]) -> None:
    _trace_context.reset(token)


def register_span(span: Span) -> None:
    _active_spans[span.span_id] = span


def unregister_span(span_id: str) -> None:
    _active_spans.pop(span_id, None)


def get_active_span(span_id: str) -> Span | None:
    return _active_spans.get(span_id)
