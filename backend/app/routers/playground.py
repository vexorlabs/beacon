from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PlaygroundChatRequest,
    PlaygroundChatResponse,
    PlaygroundCompareRequest,
    PlaygroundCompareResponse,
)
from app.services import playground_service

router = APIRouter(prefix="/playground", tags=["playground"])


@router.post("/chat", response_model=PlaygroundChatResponse)
async def playground_chat(
    request: PlaygroundChatRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PlaygroundChatResponse:
    try:
        return await playground_service.chat(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM API call failed: {e}")


@router.post("/compare", response_model=PlaygroundCompareResponse)
async def playground_compare(
    request: PlaygroundCompareRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PlaygroundCompareResponse:
    try:
        return await playground_service.compare(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM API call failed: {e}")
