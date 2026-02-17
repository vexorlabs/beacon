from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ReplayRequest, ReplayResponse
from app.services import replay_service

router = APIRouter(prefix="/replay", tags=["replay"])


@router.post("", response_model=ReplayResponse)
async def replay_span(
    request: ReplayRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ReplayResponse:
    try:
        return await replay_service.replay_llm_call(
            db, request.span_id, request.modified_attributes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM API call failed: {e}")
