from __future__ import annotations

import enum
from typing import Any, Literal

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


class Annotation(BaseModel):
    id: str
    text: str
    created_at: float


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
    annotations: list[Annotation] = []


# --- Trace schemas (Phase 2) ---


class TraceSummary(BaseModel):
    trace_id: str
    name: str
    start_time: float
    end_time: float | None
    duration_ms: float | None
    span_count: int
    status: SpanStatus
    total_cost_usd: float
    total_tokens: int
    tags: dict[str, str]


class TraceDetailResponse(TraceSummary):
    spans: list[SpanResponse]


class GraphNodeData(BaseModel):
    span_id: str
    span_type: SpanType
    name: str
    status: SpanStatus
    duration_ms: float | None
    cost_usd: float | None
    sequence: int


class GraphNode(BaseModel):
    id: str
    type: str
    data: GraphNodeData
    position: dict[str, float]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# --- Replay schemas ---


class ReplayRequest(BaseModel):
    span_id: str
    modified_attributes: dict[str, Any]


class ReplayDiff(BaseModel):
    old_completion: str
    new_completion: str
    changed: bool


class ReplayResponse(BaseModel):
    replay_id: str
    original_span_id: str
    new_output: dict[str, Any]
    diff: ReplayDiff


# --- Prompt version schemas ---


class PromptVersionCreate(BaseModel):
    prompt_text: str
    label: str | None = None


class PromptVersionResponse(BaseModel):
    version_id: str
    span_id: str
    prompt_text: str
    label: str | None
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class PromptVersionListResponse(BaseModel):
    versions: list[PromptVersionResponse]


class TracesResponse(BaseModel):
    traces: list[TraceSummary]
    total: int
    limit: int
    offset: int


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    version: str
    db_path: str


# --- Settings schemas ---


class ApiKeySetRequest(BaseModel):
    provider: str  # "openai" | "anthropic"
    api_key: str


class ApiKeySetResponse(BaseModel):
    provider: str
    configured: bool


class ApiKeyStatus(BaseModel):
    provider: str
    configured: bool
    masked_key: str | None


# --- Playground schemas ---


class PlaygroundMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class PlaygroundChatMetrics(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class PlaygroundChatRequest(BaseModel):
    conversation_id: str | None = None
    model: str
    system_prompt: str | None = None
    messages: list[PlaygroundMessage]


class PlaygroundChatResponse(BaseModel):
    conversation_id: str
    trace_id: str
    message: PlaygroundMessage
    metrics: PlaygroundChatMetrics


class PlaygroundCompareRequest(BaseModel):
    messages: list[PlaygroundMessage]
    system_prompt: str | None = None
    models: list[str]


class CompareResultItem(BaseModel):
    model: str
    provider: str
    completion: str
    metrics: PlaygroundChatMetrics


class PlaygroundCompareResponse(BaseModel):
    trace_id: str
    results: list[CompareResultItem]


# --- Demo agent schemas ---


class DemoScenarioResponse(BaseModel):
    key: str
    name: str
    description: str
    provider: str
    model: str
    api_key_configured: bool


class DemoRunRequest(BaseModel):
    scenario: str


class DemoRunResponse(BaseModel):
    trace_id: str


# --- Deletion schemas ---


class DeleteTracesRequest(BaseModel):
    trace_ids: list[str] | None = None
    older_than: float | None = None


class DeleteTracesResponse(BaseModel):
    deleted_count: int


# --- Stats schemas ---


class StatsResponse(BaseModel):
    database_size_bytes: int
    total_traces: int
    total_spans: int
    oldest_trace_timestamp: float | None


# --- Search schemas ---


class SearchResultItem(BaseModel):
    trace_id: str
    span_id: str
    name: str
    match_context: str


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int


# --- Export / Import schemas ---


class ExportFormat(str, enum.Enum):
    JSON = "json"
    OTEL = "otel"
    CSV = "csv"


class TraceExportData(BaseModel):
    version: str = "1"
    format: str = "beacon"
    exported_at: float
    trace: TraceSummary
    spans: list[SpanResponse]


class BulkTraceExportData(BaseModel):
    version: str = "1"
    format: str = "beacon"
    exported_at: float
    traces: list[TraceExportData]


class TraceImportResponse(BaseModel):
    trace_id: str
    span_count: int


# --- Tags & Annotations schemas ---


class TagsUpdateRequest(BaseModel):
    tags: dict[str, str]


class TagsUpdateResponse(BaseModel):
    trace_id: str
    tags: dict[str, str]


class AnnotationsUpdateRequest(BaseModel):
    annotations: list[Annotation]


class AnnotationsUpdateResponse(BaseModel):
    span_id: str
    annotations: list[Annotation]
