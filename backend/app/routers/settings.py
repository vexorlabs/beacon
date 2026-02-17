from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import ApiKeySetRequest, ApiKeySetResponse, ApiKeyStatus
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-keys", response_model=list[ApiKeyStatus])
async def list_api_keys() -> list[dict[str, Any]]:
    return settings_service.list_providers()


@router.put("/api-keys", response_model=ApiKeySetResponse)
async def set_api_key(request: ApiKeySetRequest) -> ApiKeySetResponse:
    try:
        settings_service.set_api_key(request.provider, request.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiKeySetResponse(provider=request.provider, configured=True)


@router.delete("/api-keys/{provider}", response_model=ApiKeySetResponse)
async def delete_api_key(provider: str) -> ApiKeySetResponse:
    settings_service.delete_api_key(provider)
    return ApiKeySetResponse(provider=provider, configured=False)
