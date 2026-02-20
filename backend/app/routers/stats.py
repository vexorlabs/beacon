"""Database statistics and dashboard analytics endpoints."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, case, cast, func, text
from sqlalchemy.orm import Session

from app import models
from app.config import settings as app_settings
from app.database import get_db
from app.schemas import (
    StatsResponse,
    TopCostItem,
    TopCostsResponse,
    TopDurationItem,
    TopDurationResponse,
    TrendBucket,
    TrendsResponse,
)
from app.services import trace_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    db: Annotated[Session, Depends(get_db)],
) -> StatsResponse:
    stats = trace_service.get_stats(db)
    try:
        db_size = os.path.getsize(app_settings.db_path)
    except OSError:
        db_size = 0
    return StatsResponse(database_size_bytes=db_size, **stats)


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
    bucket: Literal["day", "hour"] = Query(default="day"),
) -> TrendsResponse:
    """Return time-bucketed aggregates for dashboard charts."""
    now = time.time()
    cutoff = now - (days * 86400)

    if bucket == "hour":
        date_fmt = "%Y-%m-%dT%H:00"
    else:
        date_fmt = "%Y-%m-%d"

    rows = (
        db.query(
            func.strftime(date_fmt, models.Trace.created_at, "unixepoch").label(
                "bucket_date"
            ),
            func.coalesce(func.sum(models.Trace.total_cost_usd), 0.0).label(
                "total_cost"
            ),
            func.coalesce(func.sum(models.Trace.total_tokens), 0).label(
                "total_tokens"
            ),
            func.count(models.Trace.trace_id).label("trace_count"),
            func.sum(
                case((models.Trace.status == "error", 1), else_=0)
            ).label("error_count"),
        )
        .filter(models.Trace.created_at >= cutoff)
        .group_by("bucket_date")
        .order_by(text("bucket_date"))
        .all()
    )

    db_buckets: dict[str, TrendBucket] = {}
    for row in rows:
        trace_count = int(row.trace_count)
        error_count = int(row.error_count)
        success_rate = (
            round((trace_count - error_count) / trace_count, 4)
            if trace_count > 0
            else 1.0
        )
        db_buckets[row.bucket_date] = TrendBucket(
            date=row.bucket_date,
            total_cost=round(float(row.total_cost), 6),
            total_tokens=int(row.total_tokens),
            trace_count=trace_count,
            error_count=error_count,
            success_rate=success_rate,
        )

    # Fill empty periods with zero values (from oldest to today/now)
    def _empty_bucket(key: str) -> TrendBucket:
        return TrendBucket(
            date=key,
            total_cost=0.0,
            total_tokens=0,
            trace_count=0,
            error_count=0,
            success_rate=1.0,
        )
    all_buckets: list[TrendBucket] = []
    if bucket == "hour":
        for i in range(days * 24):
            ts = now - ((days * 24) - 1 - i) * 3600
            key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(date_fmt)
            all_buckets.append(db_buckets.get(key, _empty_bucket(key)))
    else:
        for i in range(days):
            ts = now - (days - 1 - i) * 86400
            key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(date_fmt)
            all_buckets.append(db_buckets.get(key, _empty_bucket(key)))

    return TrendsResponse(buckets=all_buckets)


@router.get("/top-costs", response_model=TopCostsResponse)
async def get_top_costs(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=100),
) -> TopCostsResponse:
    """Return the most expensive LLM call spans by cost."""
    cost_expr = cast(
        func.json_extract(models.Span.attributes, '$."llm.cost_usd"'),
        Float,
    )
    rows = (
        db.query(
            models.Span.span_id,
            models.Span.trace_id,
            models.Span.name,
            func.json_extract(
                models.Span.attributes, '$."llm.model"'
            ).label("model"),
            cost_expr.label("cost"),
            func.coalesce(
                cast(
                    func.json_extract(
                        models.Span.attributes, '$."llm.tokens.input"'
                    ),
                    Float,
                ),
                0,
            ).label("input_tokens"),
            func.coalesce(
                cast(
                    func.json_extract(
                        models.Span.attributes, '$."llm.tokens.output"'
                    ),
                    Float,
                ),
                0,
            ).label("output_tokens"),
        )
        .filter(
            models.Span.span_type == "llm_call",
            cost_expr > 0,
        )
        .order_by(cost_expr.desc())
        .limit(limit)
        .all()
    )

    items = [
        TopCostItem(
            span_id=row.span_id,
            trace_id=row.trace_id,
            name=row.name,
            model=str(row.model or ""),
            cost=round(float(row.cost), 6),
            tokens=int(row.input_tokens) + int(row.output_tokens),
        )
        for row in rows
    ]
    return TopCostsResponse(prompts=items)


@router.get("/top-duration", response_model=TopDurationResponse)
async def get_top_duration(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=100),
) -> TopDurationResponse:
    """Return the longest-running tool call spans by duration."""
    duration_expr = (models.Span.end_time - models.Span.start_time) * 1000
    rows = (
        db.query(
            models.Span.span_id,
            models.Span.trace_id,
            models.Span.name,
            duration_expr.label("duration_ms"),
        )
        .filter(
            models.Span.span_type == "tool_use",
            models.Span.end_time.isnot(None),
            models.Span.start_time.isnot(None),
        )
        .order_by(duration_expr.desc())
        .limit(limit)
        .all()
    )

    items = [
        TopDurationItem(
            span_id=row.span_id,
            trace_id=row.trace_id,
            name=row.name,
            duration_ms=round(float(row.duration_ms), 2),
        )
        for row in rows
    ]
    return TopDurationResponse(tools=items)
