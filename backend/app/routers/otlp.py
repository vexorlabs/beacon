"""OTLP-compatible trace ingestion endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import span_service
from app.services.otlp_service import convert_otlp_to_spans
from app.ws.manager import ws_manager

router = APIRouter(prefix="/otlp", tags=["otlp"])


class OtlpIngestResponse(BaseModel):
    accepted: int
    rejected: int


@router.post("/traces", response_model=OtlpIngestResponse)
async def ingest_otlp_traces(
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
) -> OtlpIngestResponse:
    """Accept traces in OTLP JSON format and ingest them as Beacon spans."""
    spans = convert_otlp_to_spans(payload)
    accepted, rejected = span_service.ingest_spans(db, spans)

    for span_create in spans:
        response = span_service.get_span_by_id(db, span_create.span_id)
        if response is not None:
            span_dict = span_service.span_to_response(response).model_dump()
            await ws_manager.broadcast_span(span_dict)

    return OtlpIngestResponse(accepted=accepted, rejected=rejected)
