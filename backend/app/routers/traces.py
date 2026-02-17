"""Trace listing, detail, and graph endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import GraphData, TraceDetailResponse, TracesResponse
from app.services import trace_service

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=TracesResponse)
async def list_traces(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
) -> TracesResponse:
    return trace_service.list_traces(
        db, limit=limit, offset=offset, status=status
    )


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
