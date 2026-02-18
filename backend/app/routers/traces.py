"""Trace listing, detail, and graph endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DeleteTracesRequest,
    DeleteTracesResponse,
    GraphData,
    SpanStatus,
    TraceDetailResponse,
    TracesResponse,
)
from app.services import trace_service

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=TracesResponse)
async def list_traces(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: SpanStatus | None = Query(default=None),
) -> TracesResponse:
    return trace_service.list_traces(
        db, limit=limit, offset=offset, status=status
    )


@router.delete("", response_model=DeleteTracesResponse)
async def delete_traces_batch(
    request: DeleteTracesRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DeleteTracesResponse:
    if request.trace_ids is None and request.older_than is None:
        raise HTTPException(
            status_code=422,
            detail="Provide trace_ids or older_than",
        )
    count = trace_service.delete_traces_batch(
        db, trace_ids=request.trace_ids, older_than=request.older_than
    )
    return DeleteTracesResponse(deleted_count=count)


@router.delete("/{trace_id}", response_model=DeleteTracesResponse)
async def delete_trace(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> DeleteTracesResponse:
    deleted = trace_service.delete_trace(db, trace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trace not found")
    return DeleteTracesResponse(deleted_count=1)


@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> TraceDetailResponse:
    result = trace_service.get_trace_detail(db, trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


@router.get("/{trace_id}/graph", response_model=GraphData)
async def get_trace_graph(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> GraphData:
    result = trace_service.get_trace_graph(db, trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result
