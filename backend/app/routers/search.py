"""Full-text search endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SearchResponse:
    return search_service.search(db, query=q, limit=limit, offset=offset)
