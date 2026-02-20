from __future__ import annotations

import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app import models
from app.schemas import PromptVersionResponse


def list_versions(db: Session, span_id: str) -> list[PromptVersionResponse]:
    """Return all prompt versions for a span, newest first."""
    span = db.get(models.Span, span_id)
    if span is None:
        raise ValueError("Span not found")

    rows = (
        db.query(models.PromptVersion)
        .filter(models.PromptVersion.span_id == span_id)
        .order_by(models.PromptVersion.created_at.desc())
        .all()
    )
    return [PromptVersionResponse.model_validate(r) for r in rows]


def create_version(
    db: Session,
    span_id: str,
    prompt_text: str,
    label: str | None = None,
) -> PromptVersionResponse:
    """Create a new prompt version for a span."""
    span = db.get(models.Span, span_id)
    if span is None:
        raise ValueError("Span not found")
    if span.span_type != "llm_call":
        raise ValueError("Prompt versions only supported for llm_call spans")

    version = models.PromptVersion(
        version_id=str(uuid4()),
        span_id=span_id,
        prompt_text=prompt_text,
        label=label,
        created_at=time.time(),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return PromptVersionResponse.model_validate(version)
