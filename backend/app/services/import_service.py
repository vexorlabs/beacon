"""Import traces from Beacon JSON format."""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.schemas import TraceExportData

logger = logging.getLogger(__name__)


def import_trace(db: Session, data: TraceExportData) -> tuple[str, int]:
    """Create a trace and its spans from exported Beacon JSON data.

    Returns (trace_id, span_count).
    Raises ValueError if the trace_id already exists.
    """
    trace_data = data.trace
    spans_data = data.spans

    # Check for duplicate trace
    existing = db.execute(
        select(models.Trace).where(
            models.Trace.trace_id == trace_data.trace_id
        )
    ).scalar_one_or_none()

    if existing is not None:
        logger.warning("Duplicate trace rejected: %s", trace_data.trace_id)
        raise ValueError(f"Trace {trace_data.trace_id} already exists")

    # Compute aggregates from spans
    total_cost = 0.0
    total_tokens = 0
    has_error = False
    all_ok = True

    for span in spans_data:
        cost = span.attributes.get("llm.cost_usd")
        if isinstance(cost, (int, float)):
            total_cost += cost
        tok = span.attributes.get("llm.tokens.total")
        if isinstance(tok, (int, float)):
            total_tokens += int(tok)
        if span.status == "error":
            has_error = True
        if span.status != "ok":
            all_ok = False

    if has_error:
        status = "error"
    elif all_ok and len(spans_data) > 0:
        status = "ok"
    else:
        status = "unset"

    tags = trace_data.tags if isinstance(trace_data.tags, dict) else {}

    trace = models.Trace(
        trace_id=trace_data.trace_id,
        name=trace_data.name,
        start_time=trace_data.start_time,
        end_time=trace_data.end_time,
        span_count=len(spans_data),
        status=status,
        tags=json.dumps(tags),
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        created_at=time.time(),
    )
    try:
        db.add(trace)
        db.flush()

        now = time.time()
        for span in spans_data:
            db_span = models.Span(
                span_id=span.span_id,
                trace_id=trace_data.trace_id,
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

        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "Imported trace %s with %d spans", trace_data.trace_id, len(spans_data)
    )
    return trace_data.trace_id, len(spans_data)
