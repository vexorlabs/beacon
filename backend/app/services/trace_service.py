"""Service layer for trace queries and graph construction."""

from __future__ import annotations

import json

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app import models
from app.schemas import (
    GraphData,
    GraphEdge,
    GraphNode,
    GraphNodeData,
    SpanStatus,
    TraceSummary,
    TraceDetailResponse,
    TracesResponse,
)
from app.services.span_service import span_to_response


def list_traces(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> TracesResponse:
    """Return paginated trace list, newest first."""
    query = select(models.Trace).order_by(models.Trace.created_at.desc())

    if status:
        query = query.where(models.Trace.status == status)

    total_query = select(func.count()).select_from(query.subquery())
    total: int = db.execute(total_query).scalar_one()

    traces = db.execute(query.offset(offset).limit(limit)).scalars().all()

    return TracesResponse(
        traces=[_trace_to_summary(t) for t in traces],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_trace_detail(
    db: Session, trace_id: str
) -> TraceDetailResponse | None:
    """Return trace with all its spans, or None if not found."""
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
    return TraceDetailResponse(
        **summary.model_dump(),
        spans=[span_to_response(s) for s in spans],
    )


def get_trace_graph(db: Session, trace_id: str) -> GraphData | None:
    """Build React Flow graph data from a trace's spans.

    Returns { nodes, edges } with all positions set to {x: 0, y: 0}
    (layout is computed client-side by dagre).
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

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for span in spans:
        attrs = json.loads(span.attributes or "{}")
        duration_ms = (
            (span.end_time - span.start_time) * 1000
            if span.end_time is not None
            else None
        )
        cost_usd = attrs.get("llm.cost_usd")

        nodes.append(GraphNode(
            id=span.span_id,
            type="spanNode",
            data=GraphNodeData(
                span_id=span.span_id,
                span_type=span.span_type,
                name=span.name,
                status=span.status,
                duration_ms=duration_ms,
                cost_usd=cost_usd,
            ),
            position={"x": 0, "y": 0},
        ))

        if span.parent_span_id:
            edges.append(GraphEdge(
                id=f"edge-{span.parent_span_id}-{span.span_id}",
                source=span.parent_span_id,
                target=span.span_id,
            ))

    return GraphData(nodes=nodes, edges=edges)


def _trace_to_summary(trace: models.Trace) -> TraceSummary:
    duration_ms = (
        (trace.end_time - trace.start_time) * 1000
        if trace.end_time is not None
        else None
    )
    tags: dict[str, str] = {}
    if isinstance(trace.tags, str):
        tags = json.loads(trace.tags)
    elif isinstance(trace.tags, dict):
        tags = trace.tags

    return TraceSummary(
        trace_id=trace.trace_id,
        name=trace.name,
        start_time=trace.start_time,
        end_time=trace.end_time,
        duration_ms=duration_ms,
        span_count=trace.span_count or 0,
        status=trace.status or SpanStatus.UNSET,
        total_cost_usd=trace.total_cost_usd or 0,
        total_tokens=trace.total_tokens or 0,
        tags=tags,
    )
