from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import SpanCreate, SpanResponse

logger = logging.getLogger(__name__)


def ingest_spans(
    db: Session,
    spans: list[SpanCreate],
) -> tuple[int, int]:
    """Process a batch of spans. Returns (accepted, rejected)."""
    accepted = 0
    rejected = 0
    for span_data in spans:
        try:
            _upsert_trace(db, span_data)
            db.flush()  # ensure trace exists before inserting span (FK constraint)
            _upsert_span(db, span_data)
            db.commit()
            accepted += 1
        except Exception:
            logger.exception("Failed to ingest span %s", span_data.span_id)
            db.rollback()
            rejected += 1
    return accepted, rejected


def get_span_by_id(db: Session, span_id: str) -> models.Span | None:
    stmt = select(models.Span).where(models.Span.span_id == span_id)
    return db.execute(stmt).scalar_one_or_none()


def span_to_response(span: models.Span) -> SpanResponse:
    """Convert an ORM Span to a SpanResponse with computed fields."""
    attributes: dict[str, Any] = json.loads(span.attributes or "{}")
    end_time: float | None = span.end_time
    start_time: float = span.start_time
    duration_ms: float | None = None
    if end_time is not None:
        duration_ms = (end_time - start_time) * 1000
    annotations_raw: list[dict[str, Any]] = json.loads(span.annotations or "[]")
    return SpanResponse(
        span_id=span.span_id,
        trace_id=span.trace_id,
        parent_span_id=span.parent_span_id,
        span_type=span.span_type,
        name=span.name,
        status=span.status,
        error_message=span.error_message,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        attributes=attributes,
        annotations=annotations_raw,
    )


def update_span_annotations(
    db: Session, span_id: str, annotations: list[dict[str, Any]]
) -> models.Span | None:
    """Set/replace annotations on a span. Returns updated span or None if not found."""
    span = get_span_by_id(db, span_id)
    if span is None:
        return None
    span.annotations = json.dumps(annotations)
    db.commit()
    db.refresh(span)
    return span


def _upsert_trace(db: Session, span: SpanCreate) -> None:
    stmt = select(models.Trace).where(
        models.Trace.trace_id == span.trace_id
    )
    trace = db.execute(stmt).scalar_one_or_none()

    cost = 0.0
    tokens = 0
    if span.span_type.value == "llm_call":
        cost = span.attributes.get("llm.cost_usd", 0) or 0.0
        tokens = span.attributes.get("llm.tokens.total", 0) or 0

    if trace is None:
        trace = models.Trace(
            trace_id=span.trace_id,
            name=span.name,
            start_time=span.start_time,
            end_time=span.end_time,
            span_count=1,
            status="unset",
            total_cost_usd=cost,
            total_tokens=tokens,
            created_at=time.time(),
        )
        db.add(trace)
    else:
        trace.span_count = (trace.span_count or 0) + 1
        trace.start_time = min(trace.start_time, span.start_time)
        if span.end_time is not None:
            trace.end_time = max(trace.end_time or 0, span.end_time)
        if span.parent_span_id is None:
            trace.name = span.name
        trace.total_cost_usd = (trace.total_cost_usd or 0) + cost
        trace.total_tokens = (trace.total_tokens or 0) + tokens
        trace.status = _compute_trace_status(db, span.trace_id, span)


def _upsert_span(db: Session, span: SpanCreate) -> None:
    stmt = select(models.Span).where(models.Span.span_id == span.span_id)
    existing = db.execute(stmt).scalar_one_or_none()
    now = time.time()
    if existing is None:
        db_span = models.Span(
            span_id=span.span_id,
            trace_id=span.trace_id,
            parent_span_id=span.parent_span_id,
            span_type=span.span_type.value,
            name=span.name,
            status=span.status.value,
            error_message=span.error_message,
            start_time=span.start_time,
            end_time=span.end_time,
            attributes=json.dumps(span.attributes),
            created_at=now,
        )
        db.add(db_span)
    else:
        existing.status = span.status.value
        existing.error_message = span.error_message
        existing.end_time = span.end_time
        existing.attributes = json.dumps(span.attributes)



def _compute_trace_status(
    db: Session, trace_id: str, new_span: SpanCreate
) -> str:
    """Derive trace status: error > unset > ok."""
    if new_span.status.value == "error":
        return "error"
    stmt = select(models.Span.status).where(
        models.Span.trace_id == trace_id
    )
    statuses = [row[0] for row in db.execute(stmt).all()]
    statuses.append(new_span.status.value)
    if "error" in statuses:
        return "error"
    if "unset" in statuses:
        return "unset"
    return "ok"
