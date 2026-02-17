from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SpanIngestRequest, SpanIngestResponse, SpanResponse
from app.services import span_service
from app.ws.manager import ws_manager

router = APIRouter(prefix="/spans", tags=["spans"])


@router.post("", response_model=SpanIngestResponse)
async def ingest_spans(
    request: SpanIngestRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SpanIngestResponse:
    accepted, rejected = span_service.ingest_spans(db, request.spans)

    for span_data in request.spans:
        response = span_service.get_span_by_id(db, span_data.span_id)
        if response is not None:
            span_dict = span_service.span_to_response(response).model_dump()
            await ws_manager.broadcast_span(span_dict)

    return SpanIngestResponse(accepted=accepted, rejected=rejected)


@router.get("/{span_id}", response_model=SpanResponse)
async def get_span(
    span_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> SpanResponse:
    span = span_service.get_span_by_id(db, span_id)
    if span is None:
        raise HTTPException(status_code=404, detail="Span not found")
    return span_service.span_to_response(span)
