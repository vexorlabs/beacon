"""Demo agent router — list and run pre-built agent scenarios."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DemoRunRequest, DemoRunResponse, DemoScenarioResponse
from app.services import demo_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/scenarios", response_model=list[DemoScenarioResponse])
def get_scenarios() -> list[DemoScenarioResponse]:
    """List available demo scenarios with API key status."""
    return demo_service.list_scenarios()


@router.post("/run", response_model=DemoRunResponse)
async def run_demo(
    request: DemoRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DemoRunResponse:
    """Start a demo agent. Returns trace_id immediately; agent runs in background."""
    try:
        return await demo_service.run_agent(db, request.scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM API call failed: {e}")
