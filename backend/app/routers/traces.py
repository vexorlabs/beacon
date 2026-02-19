"""Trace listing, detail, graph, export, and import endpoints."""

from __future__ import annotations

import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BulkTraceExportData,
    DeleteTracesRequest,
    DeleteTracesResponse,
    ExportFormat,
    GraphData,
    SpanStatus,
    TraceDetailResponse,
    TraceExportData,
    TraceImportResponse,
    TracesResponse,
)
from app.services import export_service, import_service, trace_service

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


# --- Export / Import (must come before /{trace_id} catch-all) ---


@router.get("/export", response_model=BulkTraceExportData)
async def bulk_export_traces(
    db: Annotated[Session, Depends(get_db)],
    format: ExportFormat = Query(default=ExportFormat.JSON),
    trace_ids: str | None = Query(default=None),
) -> BulkTraceExportData:
    if format != ExportFormat.JSON:
        raise HTTPException(
            status_code=400,
            detail="Bulk export only supports JSON format",
        )

    ids: list[str] = []
    if trace_ids:
        ids = [tid.strip() for tid in trace_ids.split(",") if tid.strip()]

    if not ids:
        raise HTTPException(
            status_code=422,
            detail="Provide trace_ids query parameter (comma-separated)",
        )

    exports: list[TraceExportData] = []
    for tid in ids:
        result = export_service.export_trace_json(db, tid)
        if result is not None:
            exports.append(result)

    return BulkTraceExportData(
        exported_at=time.time(),
        traces=exports,
    )


@router.post("/import", response_model=TraceImportResponse)
async def import_trace(
    data: TraceExportData,
    db: Annotated[Session, Depends(get_db)],
) -> TraceImportResponse:
    if data.format != "beacon":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format: {data.format!r} (expected 'beacon')",
        )
    if data.version != "1":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export version: {data.version!r} (expected '1')",
        )
    try:
        trace_id, span_count = import_service.import_trace(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Import failed: {exc}"
        ) from exc
    return TraceImportResponse(trace_id=trace_id, span_count=span_count)


# --- Single-trace endpoints ---


@router.delete("/{trace_id}", response_model=DeleteTracesResponse)
async def delete_trace(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> DeleteTracesResponse:
    deleted = trace_service.delete_trace(db, trace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trace not found")
    return DeleteTracesResponse(deleted_count=1)


@router.get("/{trace_id}/export", response_model=None)
async def export_trace(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
    format: ExportFormat = Query(default=ExportFormat.JSON),
) -> Response | TraceExportData:
    if format == ExportFormat.CSV:
        result = export_service.export_trace_csv(db, trace_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return Response(
            content=result,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="trace-{trace_id[:8]}.csv"'
            },
        )

    if format == ExportFormat.OTEL:
        result = export_service.export_trace_otel(db, trace_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return Response(
            content=json.dumps(result, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="trace-{trace_id[:8]}-otel.json"'
            },
        )

    # Default: Beacon JSON
    result = export_service.export_trace_json(db, trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


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
