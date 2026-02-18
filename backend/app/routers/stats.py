"""Database statistics endpoint."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.schemas import StatsResponse
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
