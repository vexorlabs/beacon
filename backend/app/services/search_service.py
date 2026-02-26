"""Full-text search across traces and spans."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models
from app.schemas import SearchResponse, SearchResultItem

MAX_RESULTS = 50
CONTEXT_LENGTH = 100


def search(
    db: Session,
    *,
    query: str,
    limit: int = MAX_RESULTS,
    offset: int = 0,
) -> SearchResponse:
    """Search spans by name and attributes, traces by name.

    Uses SQLite LIKE for substring matching.  Returns matching spans
    with a snippet of the matching context.
    """
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"

    # Spans matching by name or attributes
    span_stmt = (
        select(models.Span)
        .where(
            or_(
                models.Span.name.ilike(pattern, escape="\\"),
                models.Span.attributes.ilike(pattern, escape="\\"),
            )
        )
        .order_by(models.Span.start_time.desc())
    )

    # Spans belonging to traces whose name matches
    trace_name_stmt = (
        select(models.Span)
        .join(models.Trace, models.Span.trace_id == models.Trace.trace_id)
        .where(models.Trace.name.ilike(pattern, escape="\\"))
        .order_by(models.Span.start_time.desc())
    )

    span_results = db.execute(span_stmt).scalars().all()
    trace_results = db.execute(trace_name_stmt).scalars().all()

    # Deduplicate by span_id while preserving order
    seen: set[str] = set()
    all_spans: list[models.Span] = []
    for span in [*span_results, *trace_results]:
        if span.span_id not in seen:
            seen.add(span.span_id)
            all_spans.append(span)

    total = len(all_spans)
    page = all_spans[offset : offset + limit]

    results = [
        SearchResultItem(
            trace_id=span.trace_id,
            span_id=span.span_id,
            name=span.name,
            match_context=_extract_context(span, query),
        )
        for span in page
    ]

    return SearchResponse(results=results, total=total)


def _extract_context(span: models.Span, query: str) -> str:
    """Extract a snippet of text surrounding the match."""
    query_lower = query.lower()

    # Check name first
    if query_lower in span.name.lower():
        return span.name[:CONTEXT_LENGTH]

    # Check attributes
    attrs = span.attributes or ""
    idx = attrs.lower().find(query_lower)
    if idx >= 0:
        start = max(0, idx - 30)
        end = min(len(attrs), idx + len(query) + 70)
        snippet = attrs[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(attrs):
            snippet = snippet + "..."
        return snippet

    return span.name[:CONTEXT_LENGTH]
