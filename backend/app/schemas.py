from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class SpanType(str, enum.Enum):
    LLM_CALL = "llm_call"
    TOOL_USE = "tool_use"
    AGENT_STEP = "agent_step"
    BROWSER_ACTION = "browser_action"
    FILE_OPERATION = "file_operation"
    SHELL_COMMAND = "shell_command"
    CHAIN = "chain"
    CUSTOM = "custom"


class SpanStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


# --- Span schemas ---


class SpanCreate(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    span_type: SpanType
    name: str
    status: SpanStatus = SpanStatus.UNSET
    error_message: str | None = None
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = {}


class SpanIngestRequest(BaseModel):
    spans: list[SpanCreate]


class SpanIngestResponse(BaseModel):
    accepted: int
    rejected: int


class SpanResponse(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None
    span_type: SpanType
    name: str
    status: SpanStatus
    error_message: str | None
    start_time: float
    end_time: float | None
    duration_ms: float | None
    attributes: dict[str, Any]


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    version: str
    db_path: str
