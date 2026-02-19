"""Export traces in Beacon JSON, OTEL JSON, and CSV formats."""

from __future__ import annotations

import csv
import io
import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import (
    SpanResponse,
    TraceSummary,
    TraceExportData,
)
from app.services.span_service import span_to_response
from app.services.trace_service import _trace_to_summary


def export_trace_json(db: Session, trace_id: str) -> TraceExportData | None:
    """Export a single trace in Beacon JSON format."""
    trace = db.execute(
        select(models.Trace).where(models.Trace.trace_id == trace_id)
    ).scalar_one_or_none()

    if trace is None:
        return None

    spans = (
        db.execute(
            select(models.Span)
            .where(models.Span.trace_id == trace_id)
            .order_by(models.Span.start_time)
        )
        .scalars()
        .all()
    )

    summary = _trace_to_summary(trace)
    span_responses = [span_to_response(s) for s in spans]

    return TraceExportData(
        exported_at=time.time(),
        trace=summary,
        spans=span_responses,
    )


def export_trace_otel(db: Session, trace_id: str) -> dict[str, object] | None:
    """Export a single trace in OTEL-compatible JSON format.

    Produces the standard OTLP JSON structure:
    { resourceSpans: [{ scopeSpans: [{ spans: [...] }] }] }
    """
    trace = db.execute(
        select(models.Trace).where(models.Trace.trace_id == trace_id)
    ).scalar_one_or_none()

    if trace is None:
        return None

    spans = (
        db.execute(
            select(models.Span)
            .where(models.Span.trace_id == trace_id)
            .order_by(models.Span.start_time)
        )
        .scalars()
        .all()
    )

    otel_spans = [_span_to_otel(s) for s in spans]

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "beacon"}},
                        {"key": "trace.name", "value": {"stringValue": trace.name}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "beacon", "version": "0.1.0"},
                        "spans": otel_spans,
                    }
                ],
            }
        ]
    }


def export_trace_csv(db: Session, trace_id: str) -> str | None:
    """Export a single trace as flat CSV with one row per span."""
    trace = db.execute(
        select(models.Trace).where(models.Trace.trace_id == trace_id)
    ).scalar_one_or_none()

    if trace is None:
        return None

    spans = (
        db.execute(
            select(models.Span)
            .where(models.Span.trace_id == trace_id)
            .order_by(models.Span.start_time)
        )
        .scalars()
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "trace_id",
        "span_id",
        "parent_span_id",
        "name",
        "span_type",
        "start_time",
        "end_time",
        "duration_ms",
        "status",
        "cost",
        "tokens",
    ])

    for span in spans:
        attrs = json.loads(span.attributes or "{}")
        duration_ms = (
            (span.end_time - span.start_time) * 1000
            if span.end_time is not None
            else ""
        )
        cost = attrs.get("llm.cost_usd", "")
        tokens = attrs.get("llm.tokens.total", "")

        writer.writerow([
            span.trace_id,
            span.span_id,
            span.parent_span_id or "",
            span.name,
            span.span_type,
            span.start_time,
            span.end_time or "",
            duration_ms,
            span.status,
            cost,
            tokens,
        ])

    return output.getvalue()


def _span_to_otel(span: models.Span) -> dict[str, object]:
    """Convert a DB span to OTEL JSON span format."""
    attrs = json.loads(span.attributes or "{}")

    # Convert epoch seconds to nanoseconds
    start_ns = int(span.start_time * 1_000_000_000)
    end_ns = int(span.end_time * 1_000_000_000) if span.end_time else 0

    # OTEL status codes: 0=UNSET, 1=OK, 2=ERROR
    status_map = {"unset": 0, "ok": 1, "error": 2}
    status_code = status_map.get(span.status, 0)

    otel_attrs = [
        {"key": "span_type", "value": {"stringValue": span.span_type}},
    ]
    for key, value in attrs.items():
        otel_attrs.append(_to_otel_attribute(key, value))

    if span.error_message:
        otel_attrs.append(
            {"key": "error.message", "value": {"stringValue": span.error_message}}
        )

    result: dict[str, object] = {
        "traceId": span.trace_id,
        "spanId": span.span_id,
        "name": span.name,
        "kind": 1,  # SPAN_KIND_INTERNAL
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(end_ns),
        "attributes": otel_attrs,
        "status": {"code": status_code},
    }

    if span.parent_span_id:
        result["parentSpanId"] = span.parent_span_id

    return result


def _to_otel_attribute(key: str, value: object) -> dict[str, object]:
    """Convert a key-value pair to OTEL attribute format."""
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}
