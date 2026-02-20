"""Database statistics and dashboard analytics endpoints."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, text
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
    empty_bucket = lambda key: TrendBucket(
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
            all_buckets.append(db_buckets.get(key, empty_bucket(key)))
    else:
        for i in range(days):
            ts = now - (days - 1 - i) * 86400
            key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(date_fmt)
            all_buckets.append(db_buckets.get(key, empty_bucket(key)))

    return TrendsResponse(buckets=all_buckets)


@router.get("/top-costs", response_model=TopCostsResponse)
async def get_top_costs(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=100),
) -> TopCostsResponse:
    """Return the most expensive LLM call spans by cost."""
    spans = (
        db.query(models.Span)
        .filter(models.Span.span_type == "llm_call")
        .all()
    )

    items: list[TopCostItem] = []
    for span in spans:
        attrs: dict[str, object] = {}
        if span.attributes:
            try:
                attrs = json.loads(span.attributes)
            except (ValueError, TypeError):
                continue
        cost = float(attrs.get("llm.cost_usd", 0) or 0)
        if cost <= 0:
            continue
        input_tokens = int(attrs.get("llm.tokens.input", 0) or 0)
        output_tokens = int(attrs.get("llm.tokens.output", 0) or 0)
        items.append(
            TopCostItem(
                span_id=span.span_id,
                trace_id=span.trace_id,
                name=span.name,
                model=str(attrs.get("llm.model", "")),
                cost=round(cost, 6),
                tokens=input_tokens + output_tokens,
            )
        )

    items.sort(key=lambda x: x.cost, reverse=True)
    return TopCostsResponse(prompts=items[:limit])


@router.get("/top-duration", response_model=TopDurationResponse)
async def get_top_duration(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=100),
) -> TopDurationResponse:
    """Return the longest-running tool call spans by duration."""
    spans = (
        db.query(models.Span)
        .filter(
            models.Span.span_type == "tool_use",
            models.Span.end_time.isnot(None),
        )
        .all()
    )

    items: list[TopDurationItem] = []
    for span in spans:
        if span.end_time is None or span.start_time is None:
            continue
        duration_ms = round((span.end_time - span.start_time) * 1000, 2)
        items.append(
            TopDurationItem(
                span_id=span.span_id,
                trace_id=span.trace_id,
                name=span.name,
                duration_ms=duration_ms,
            )
        )

    items.sort(key=lambda x: x.duration_ms, reverse=True)
    return TopDurationResponse(tools=items[:limit])
