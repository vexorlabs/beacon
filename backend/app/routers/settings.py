from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import ApiKeySetRequest, ApiKeySetResponse, ApiKeyStatus
from app.services import settings_service

_SUPPORTED_PROVIDERS = ("openai", "anthropic")

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-keys", response_model=list[ApiKeyStatus])
async def list_api_keys() -> list[ApiKeyStatus]:
    return [ApiKeyStatus(**p) for p in settings_service.list_providers()]


@router.put("/api-keys", response_model=ApiKeySetResponse)
async def set_api_key(request: ApiKeySetRequest) -> ApiKeySetResponse:
    try:
        settings_service.set_api_key(request.provider, request.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiKeySetResponse(provider=request.provider, configured=True)


@router.delete("/api-keys/{provider}", response_model=ApiKeySetResponse)
async def delete_api_key(provider: str) -> ApiKeySetResponse:
    if provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    settings_service.delete_api_key(provider)
    return ApiKeySetResponse(provider=provider, configured=False)
