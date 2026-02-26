from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings as app_settings
from app.database import init_db
from app.routers import (
    analysis,
    demo,
    otlp,
    playground,
    prompt_versions,
    replay,
    search,
    settings,
    spans,
    stats,
    traces,
)
from app.ws.manager import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="Beacon Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:7474"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spans.router, prefix="/v1")
app.include_router(traces.router, prefix="/v1")
app.include_router(replay.router, prefix="/v1")
app.include_router(settings.router, prefix="/v1")
app.include_router(playground.router, prefix="/v1")
app.include_router(demo.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
app.include_router(search.router, prefix="/v1")
app.include_router(prompt_versions.router, prefix="/v1")
app.include_router(otlp.router, prefix="/v1")
app.include_router(analysis.router, prefix="/v1")
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "db_path": str(app_settings.db_path),
    }
