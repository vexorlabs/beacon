from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PromptVersionCreate,
    PromptVersionListResponse,
    PromptVersionResponse,
)
from app.services import prompt_version_service

router = APIRouter(prefix="/spans/{span_id}/prompt-versions", tags=["prompt-versions"])


@router.get("", response_model=PromptVersionListResponse)
def list_prompt_versions(
    span_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> PromptVersionListResponse:
    try:
        versions = prompt_version_service.list_versions(db, span_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PromptVersionListResponse(versions=versions)


@router.post("", response_model=PromptVersionResponse, status_code=201)
def create_prompt_version(
    span_id: str,
    body: PromptVersionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PromptVersionResponse:
    try:
        return prompt_version_service.create_version(
            db, span_id, body.prompt_text, body.label
        )
    except ValueError as exc:
        status = 400 if "only supported" in str(exc) else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc
