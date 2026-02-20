# API Contracts

This document defines the HTTP and WebSocket contracts exposed by `beacon-backend`.

Base URL: `http://localhost:7474`

All request/response bodies are JSON. Timestamps are Unix epoch seconds (float).

---

## REST API

### Health

#### `GET /health`

Response `200 OK`:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "db_path": "/Users/you/.beacon/traces.db"
}
```

---

### Spans

#### `POST /v1/spans`

Ingest one or more spans.

Request:

```json
{
  "spans": [
    {
      "span_id": "550e8400-e29b-41d4-a716-446655440000",
      "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "parent_span_id": null,
      "span_type": "llm_call",
      "name": "openai.chat.completions",
      "status": "ok",
      "error_message": null,
      "start_time": 1739800000.123,
      "end_time": 1739800002.456,
      "attributes": {
        "llm.provider": "openai",
        "llm.model": "gpt-4o",
        "llm.prompt": "[{\"role\":\"user\",\"content\":\"What is 2+2?\"}]",
        "llm.completion": "4",
        "llm.tokens.input": 14,
        "llm.tokens.output": 1,
        "llm.tokens.total": 15,
        "llm.cost_usd": 0.000075,
        "llm.finish_reason": "stop"
      }
    }
  ]
}
```

Response `200 OK`:

```json
{
  "accepted": 1,
  "rejected": 0
}
```

Response `422 Unprocessable Entity`: request validation error.

#### `GET /v1/spans/{span_id}`

Get a single span.

Response `200 OK`: `SpanResponse`.

Response `404 Not Found`:

```json
{ "detail": "Span not found" }
```

#### `PUT /v1/spans/{span_id}/annotations`

Set/replace annotations on a span.

Request:

```json
{
  "annotations": [
    {
      "id": "a1b2c3d4-...",
      "text": "This span seems slow — investigate caching",
      "created_at": 1739800000.0
    }
  ]
}
```

Response `200 OK`:

```json
{
  "span_id": "550e8400-e29b-41d4-a716-446655440000",
  "annotations": [
    {
      "id": "a1b2c3d4-...",
      "text": "This span seems slow — investigate caching",
      "created_at": 1739800000.0
    }
  ]
}
```

Response `404 Not Found`:

```json
{ "detail": "Span not found" }
```

---

### Traces

#### `GET /v1/traces`

List traces, newest first.

Query params:
- `limit` (int, default `50`, min `1`, max `200`)
- `offset` (int, default `0`)
- `status` (`ok | error | unset`, optional)

Response `200 OK`:

```json
{
  "traces": [
    {
      "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "name": "Playground: gpt-4.1",
      "start_time": 1739800000.0,
      "end_time": 1739800045.3,
      "duration_ms": 45300.0,
      "span_count": 23,
      "status": "ok",
      "total_cost_usd": 0.042,
      "total_tokens": 12450,
      "tags": {}
    }
  ],
  "total": 147,
  "limit": 50,
  "offset": 0
}
```

#### `GET /v1/traces/{trace_id}`

Get a trace with all spans.

Response `200 OK`: `TraceDetailResponse` (`TraceSummary` + `spans[]`).

Response `404 Not Found`:

```json
{ "detail": "Trace not found" }
```

#### `GET /v1/traces/{trace_id}/graph`

Get trace graph data for React Flow.

Response `200 OK`:

```json
{
  "nodes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "spanNode",
      "data": {
        "span_id": "550e8400-e29b-41d4-a716-446655440000",
        "span_type": "llm_call",
        "name": "gpt-4.1",
        "status": "ok",
        "duration_ms": 2333.0,
        "cost_usd": 0.000075,
        "sequence": 1
      },
      "position": { "x": 0, "y": 0 }
    }
  ],
  "edges": [
    {
      "id": "edge-parent-child",
      "source": "parent-span-id",
      "target": "550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

Response `404 Not Found`:

```json
{ "detail": "Trace not found" }
```

#### `PUT /v1/traces/{trace_id}/tags`

Set/replace tags on a trace.

Request:

```json
{
  "tags": {
    "env": "prod",
    "team": "ml"
  }
}
```

Response `200 OK`:

```json
{
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "tags": {
    "env": "prod",
    "team": "ml"
  }
}
```

Response `404 Not Found`:

```json
{ "detail": "Trace not found" }
```

#### `DELETE /v1/traces/{trace_id}`

Delete one trace (spans/replay rows removed by cascade).

Response `200 OK`:

```json
{ "deleted_count": 1 }
```

Response `404 Not Found`:

```json
{ "detail": "Trace not found" }
```

#### `DELETE /v1/traces`

Batch delete traces.

Request (at least one field required):

```json
{
  "trace_ids": ["uuid-1", "uuid-2"],
  "older_than": 1739800000.0
}
```

Response `200 OK`:

```json
{ "deleted_count": 5 }
```

Response `422 Unprocessable Entity` when both fields are omitted.

#### `GET /v1/traces/{trace_id}/export`

Export a single trace with all spans.

Query params:
- `format` (`json | otel | csv`, default `json`)

Response `200 OK` (format=json):

```json
{
  "version": "1",
  "format": "beacon",
  "exported_at": 1739800000.0,
  "trace": {
    "trace_id": "7c9e6679-...",
    "name": "My Agent Run",
    "start_time": 1739800000.0,
    "end_time": 1739800045.3,
    "duration_ms": 45300.0,
    "span_count": 2,
    "status": "ok",
    "total_cost_usd": 0.005,
    "total_tokens": 500,
    "tags": {}
  },
  "spans": [
    {
      "span_id": "550e8400-...",
      "trace_id": "7c9e6679-...",
      "parent_span_id": null,
      "span_type": "agent_step",
      "name": "root",
      "status": "ok",
      "error_message": null,
      "start_time": 1739800000.0,
      "end_time": 1739800045.3,
      "duration_ms": 45300.0,
      "attributes": {}
    }
  ]
}
```

Response `200 OK` (format=otel): OTLP JSON with `resourceSpans[].scopeSpans[].spans[]` structure.

Response `200 OK` (format=csv): `text/csv` with `Content-Disposition: attachment`. Columns: `trace_id, span_id, parent_span_id, name, span_type, start_time, end_time, duration_ms, status, cost, tokens`.

Response `404 Not Found`:

```json
{ "detail": "Trace not found" }
```

#### `GET /v1/traces/export`

Bulk export multiple traces (JSON format only).

Query params:
- `format` (`json`, default `json`) — only JSON supported for bulk export
- `trace_ids` (required, comma-separated trace IDs)

Response `200 OK`:

```json
{
  "version": "1",
  "format": "beacon",
  "exported_at": 1739800000.0,
  "traces": [
    { "version": "1", "format": "beacon", "exported_at": 1739800000.0, "trace": {}, "spans": [] }
  ]
}
```

Response `400 Bad Request` for non-JSON format.

Response `422 Unprocessable Entity` when `trace_ids` is missing.

#### `POST /v1/traces/import`

Import a trace from Beacon JSON export format.

Request (same shape as single-trace export):

```json
{
  "version": "1",
  "format": "beacon",
  "exported_at": 1739800000.0,
  "trace": {
    "trace_id": "imported-trace-001",
    "name": "Imported Agent Run",
    "start_time": 1739800000.0,
    "end_time": 1739800010.0,
    "duration_ms": 10000.0,
    "span_count": 1,
    "status": "ok",
    "total_cost_usd": 0.0,
    "total_tokens": 0,
    "tags": {}
  },
  "spans": [
    {
      "span_id": "span-001",
      "trace_id": "imported-trace-001",
      "parent_span_id": null,
      "span_type": "agent_step",
      "name": "root",
      "status": "ok",
      "error_message": null,
      "start_time": 1739800000.0,
      "end_time": 1739800010.0,
      "duration_ms": 10000.0,
      "attributes": {}
    }
  ]
}
```

Response `200 OK`:

```json
{
  "trace_id": "imported-trace-001",
  "span_count": 1
}
```

Response `400 Bad Request` for unsupported `format` or `version`.

Response `409 Conflict` when trace_id already exists:

```json
{ "detail": "Trace imported-trace-001 already exists" }
```

Response `422 Unprocessable Entity` for request validation errors.

---

### OTLP Ingestion

#### `POST /v1/otlp/traces`

Accept traces in [OTLP JSON format](https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding) and ingest them as Beacon spans. Enables interoperability with any OpenTelemetry-instrumented application.

Request body (standard OTLP JSON):

```json
{
  "resourceSpans": [
    {
      "resource": {
        "attributes": [
          { "key": "service.name", "value": { "stringValue": "my-service" } }
        ]
      },
      "scopeSpans": [
        {
          "scope": { "name": "my-tracer", "version": "1.0.0" },
          "spans": [
            {
              "traceId": "abc123",
              "spanId": "def456",
              "parentSpanId": "",
              "name": "my-operation",
              "kind": 1,
              "startTimeUnixNano": "1700000000000000000",
              "endTimeUnixNano": "1700000001000000000",
              "attributes": [
                { "key": "span_type", "value": { "stringValue": "llm_call" } },
                { "key": "llm.model", "value": { "stringValue": "gpt-4o" } }
              ],
              "status": { "code": 1 }
            }
          ]
        }
      ]
    }
  ]
}
```

Conversion notes:
- Timestamps: nanoseconds (string) converted to epoch seconds (float)
- Status codes: `0` = unset, `1` = ok, `2` = error
- `span_type` extracted from attributes (defaults to `custom` if missing or unknown)
- `error.message` extracted from attributes into `error_message` field
- OTEL attribute format (`{key, value: {stringValue|intValue|doubleValue|boolValue}}`) flattened to plain dict

Response `200 OK`:

```json
{
  "accepted": 1,
  "rejected": 0
}
```

---

### Prompt Versions

#### `GET /v1/spans/{span_id}/prompt-versions`

List all prompt versions for a span, newest first.

Response `200 OK`:

```json
{
  "versions": [
    {
      "version_id": "uuid-1",
      "span_id": "550e8400-e29b-41d4-a716-446655440000",
      "prompt_text": "[{\"role\": \"user\", \"content\": \"What is 2+2?\"}]",
      "label": "v1-improved",
      "created_at": 1739800050.0
    }
  ]
}
```

Response `404 Not Found`:

```json
{ "detail": "Span not found" }
```

#### `POST /v1/spans/{span_id}/prompt-versions`

Create a new prompt version for an `llm_call` span.

Request:

```json
{
  "prompt_text": "[{\"role\": \"user\", \"content\": \"What is 2+2? Show your work.\"}]",
  "label": "v1-improved"
}
```

`label` is optional (defaults to `null`).

Response `201 Created`:

```json
{
  "version_id": "uuid-1",
  "span_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt_text": "[{\"role\": \"user\", \"content\": \"What is 2+2? Show your work.\"}]",
  "label": "v1-improved",
  "created_at": 1739800050.0
}
```

Response `400 Bad Request` when span is not an `llm_call`:

```json
{ "detail": "Prompt versions only supported for llm_call spans" }
```

Response `404 Not Found`:

```json
{ "detail": "Span not found" }
```

Note: Replaying an LLM call (`POST /v1/replay`) automatically creates a prompt version with label `"Replay"`.

---

### Replay

#### `POST /v1/replay`

Replay a single `llm_call` span with modified attributes.

Request:

```json
{
  "span_id": "550e8400-e29b-41d4-a716-446655440000",
  "modified_attributes": {
    "llm.prompt": "[{\"role\":\"user\",\"content\":\"What is 2+2? Show your work.\"}]"
  }
}
```

Response `200 OK`:

```json
{
  "replay_id": "new-uuid",
  "original_span_id": "550e8400-e29b-41d4-a716-446655440000",
  "new_output": {
    "llm.completion": "2 + 2 = 4. Here's how...",
    "llm.tokens.input": 20,
    "llm.tokens.output": 45,
    "llm.cost_usd": 0.0003
  },
  "diff": {
    "old_completion": "4",
    "new_completion": "2 + 2 = 4. Here's how...",
    "changed": true
  }
}
```

Response `400 Bad Request` (e.g., missing span, unsupported span type, bad provider/model).

Response `502 Bad Gateway` when upstream LLM call fails.

---

### Settings

#### `GET /v1/settings/api-keys`

List API key status for supported providers.

Response `200 OK`:

```json
[
  {
    "provider": "openai",
    "configured": true,
    "masked_key": "••••••••1234"
  },
  {
    "provider": "anthropic",
    "configured": false,
    "masked_key": null
  },
  {
    "provider": "google",
    "configured": false,
    "masked_key": null
  }
]
```

#### `PUT /v1/settings/api-keys`

Set/update a provider API key.

Request:

```json
{
  "provider": "openai",
  "api_key": "sk-..."
}
```

Response `200 OK`:

```json
{
  "provider": "openai",
  "configured": true
}
```

Response `400 Bad Request` for unsupported provider.

#### `DELETE /v1/settings/api-keys/{provider}`

Delete a provider key.

Response `200 OK`:

```json
{
  "provider": "openai",
  "configured": false
}
```

Response `400 Bad Request` for unsupported provider.

---

### Playground

#### `POST /v1/playground/chat`

Run one chat turn on one model.

Request:

```json
{
  "conversation_id": null,
  "model": "gpt-4.1",
  "system_prompt": "You are concise.",
  "messages": [
    { "role": "user", "content": "Explain retries." }
  ]
}
```

Response `200 OK`:

```json
{
  "conversation_id": "f7f43eb8-...",
  "trace_id": "f7f43eb8-...",
  "message": {
    "role": "assistant",
    "content": "..."
  },
  "metrics": {
    "input_tokens": 123,
    "output_tokens": 45,
    "cost_usd": 0.0008,
    "latency_ms": 842.1
  }
}
```

Response `400 Bad Request` for missing/unsupported provider key.

Response `422 Unprocessable Entity` for request validation errors.

Response `502 Bad Gateway` for upstream LLM failure.

#### `POST /v1/playground/compare`

Run one prompt across multiple models.

Request:

```json
{
  "system_prompt": "You are concise.",
  "messages": [
    { "role": "user", "content": "Explain retries." }
  ],
  "models": ["gpt-4.1", "claude-sonnet-4-6"]
}
```

Response `200 OK`:

```json
{
  "trace_id": "4c72c0f1-...",
  "results": [
    {
      "model": "gpt-4.1",
      "provider": "openai",
      "completion": "...",
      "metrics": {
        "input_tokens": 120,
        "output_tokens": 40,
        "cost_usd": 0.0007,
        "latency_ms": 820.5
      }
    }
  ]
}
```

Response `400 Bad Request` if fewer than 2 models or provider config is missing.

Response `422 Unprocessable Entity` for request validation errors.

Response `502 Bad Gateway` for upstream LLM failure.

---

### Demo Agents

#### `GET /v1/demo/scenarios`

List demo scenarios.

Response `200 OK`:

```json
[
  {
    "key": "research_assistant",
    "name": "Research Assistant",
    "description": "Multi-step research with web search tool",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key_configured": true
  }
]
```

#### `POST /v1/demo/run`

Start demo agent in background and return trace id immediately.

Request:

```json
{ "scenario": "research_assistant" }
```

Response `200 OK`:

```json
{ "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7" }
```

Response `400 Bad Request` for unknown scenario or missing API key.

Response `502 Bad Gateway` for upstream LLM failure.

---

### Search

#### `GET /v1/search`

Search span name/attributes and trace names.

Query params:
- `q` (required, min 1, max 500)
- `limit` (default `50`, min `1`, max `200`)
- `offset` (default `0`)

Response `200 OK`:

```json
{
  "results": [
    {
      "trace_id": "7c9e6679-...",
      "span_id": "550e8400-...",
      "name": "openai.chat.completions",
      "match_context": "..."
    }
  ],
  "total": 3
}
```

Response `422 Unprocessable Entity` if `q` is missing.

---

### Stats

#### `GET /v1/stats`

Database stats.

Response `200 OK`:

```json
{
  "database_size_bytes": 1048576,
  "total_traces": 42,
  "total_spans": 523,
  "oldest_trace_timestamp": 1739800000.0
}
```

#### `GET /v1/stats/trends`

Time-bucketed aggregates for dashboard charts. Returns cost, tokens, trace count, error count, and success rate per bucket with gap-filling for empty periods.

Query parameters:
- `days` (int, default 30, range 1–365) — lookback window
- `bucket` (`"day"` | `"hour"`, default `"day"`) — bucket granularity

Response `200 OK`:

```json
{
  "buckets": [
    {
      "date": "2025-06-01",
      "total_cost": 0.0042,
      "total_tokens": 1500,
      "trace_count": 3,
      "error_count": 0,
      "success_rate": 1.0
    },
    {
      "date": "2025-06-02",
      "total_cost": 0.0,
      "total_tokens": 0,
      "trace_count": 0,
      "error_count": 0,
      "success_rate": 1.0
    }
  ]
}
```

#### `GET /v1/stats/top-costs`

Most expensive LLM call spans by cost.

Query parameters:
- `limit` (int, default 10, range 1–100) — number of results

Response `200 OK`:

```json
{
  "prompts": [
    {
      "span_id": "abc-123",
      "trace_id": "def-456",
      "name": "chat_completion",
      "model": "gpt-4o",
      "cost": 0.0315,
      "tokens": 4200
    }
  ]
}
```

#### `GET /v1/stats/top-duration`

Longest-running tool call spans by duration.

Query parameters:
- `limit` (int, default 10, range 1–100) — number of results

Response `200 OK`:

```json
{
  "tools": [
    {
      "span_id": "abc-123",
      "trace_id": "def-456",
      "name": "web_search",
      "duration_ms": 3520.5
    }
  ]
}
```

---

### Analysis (AI-Powered)

All analysis endpoints call a configured LLM (default `gpt-4o-mini`, override with `BEACON_ANALYSIS_MODEL` env var). They return structured JSON validated against Pydantic schemas.

#### `POST /v1/analysis/root-cause`

Identify the root cause of failures in a trace.

Request:

```json
{ "trace_id": "7c9e6679-..." }
```

Response `200 OK`:

```json
{
  "trace_id": "7c9e6679-...",
  "root_cause": "Rate limit exceeded on OpenAI API",
  "affected_spans": ["span-1", "span-2"],
  "confidence": 0.85,
  "suggested_fix": "Add retry logic with exponential backoff"
}
```

Response `400 Bad Request`: trace not found or invalid input.

Response `502 Bad Gateway`: LLM call failed.

#### `POST /v1/analysis/cost-optimization`

Analyze LLM call patterns across multiple traces for cost-saving opportunities.

Request:

```json
{ "trace_ids": ["trace-1", "trace-2"] }
```

Response `200 OK`:

```json
{
  "trace_ids": ["trace-1", "trace-2"],
  "suggestions": [
    {
      "type": "model_downgrade",
      "description": "Use gpt-4o-mini for simple classification",
      "estimated_savings_usd": 0.015,
      "affected_spans": ["span-1"]
    }
  ]
}
```

#### `POST /v1/analysis/prompt-suggestions`

Analyze an LLM call's prompt and suggest improvements.

Request:

```json
{ "span_id": "550e8400-..." }
```

Response `200 OK`:

```json
{
  "span_id": "550e8400-...",
  "original_prompt": "What is 2+2?",
  "suggestions": [
    {
      "category": "clarity",
      "description": "Be more specific about expected output format",
      "improved_prompt_snippet": "Calculate 2+2 and return only the number."
    }
  ]
}
```

#### `POST /v1/analysis/anomalies`

Compare a trace against historical baselines and flag anomalies.

Request:

```json
{ "trace_id": "7c9e6679-..." }
```

Response `200 OK`:

```json
{
  "trace_id": "7c9e6679-...",
  "anomalies": [
    {
      "type": "cost_spike",
      "severity": "high",
      "description": "Cost is 3x the historical mean",
      "trace_id": "7c9e6679-...",
      "span_id": "span-1"
    }
  ]
}
```

#### `POST /v1/analysis/error-patterns`

Cluster similar failures across multiple traces.

Request:

```json
{ "trace_ids": ["trace-1", "trace-2", "trace-3"] }
```

Response `200 OK`:

```json
{
  "patterns": [
    {
      "pattern_name": "Repeated rate limiting",
      "count": 5,
      "example_trace_ids": ["trace-1", "trace-2"],
      "common_root_cause": "No retry logic on API calls",
      "category": "rate_limit"
    }
  ]
}
```

#### `POST /v1/analysis/compare`

Compare two traces and identify structural divergence.

Request:

```json
{
  "trace_id_a": "trace-1",
  "trace_id_b": "trace-2"
}
```

Response `200 OK`:

```json
{
  "trace_id_a": "trace-1",
  "trace_id_b": "trace-2",
  "divergence_points": [
    {
      "span_a": "span-1",
      "span_b": null,
      "description": "Trace A has an extra tool call"
    }
  ],
  "metric_diff": {
    "cost_diff_usd": 0.01,
    "duration_diff_ms": 500.0,
    "token_diff": 200,
    "span_count_diff": 1
  },
  "summary": "Trace A used an additional tool call, increasing cost and duration."
}
```

#### `POST /v1/analysis/summarize`

Generate a natural language summary of what the agent did.

Request:

```json
{ "trace_id": "7c9e6679-..." }
```

Response `200 OK`:

```json
{
  "trace_id": "7c9e6679-...",
  "summary": "The agent called GPT-4o twice and returned results in 1.5s.",
  "key_events": [
    { "span_id": "span-1", "description": "LLM call to GPT-4o" },
    { "span_id": "span-2", "description": "Tool invocation: web_search" }
  ]
}
```

---

## WebSocket API

### `WS /ws/live`

Connection URL: `ws://localhost:7474/ws/live`

Server -> client events:

#### `span_created`

```json
{
  "event": "span_created",
  "span": {
    "span_id": "...",
    "trace_id": "...",
    "parent_span_id": null,
    "span_type": "llm_call",
    "name": "openai.chat.completions",
    "status": "ok",
    "error_message": null,
    "start_time": 1739800000.123,
    "end_time": 1739800002.456,
    "duration_ms": 2333.0,
    "attributes": {}
  }
}
```

#### `trace_created`

```json
{
  "event": "trace_created",
  "trace": {
    "trace_id": "...",
    "name": "...",
    "start_time": 1739800000.0,
    "status": "unset"
  }
}
```

#### `span_updated`

Supported by the WS manager and reserved for partial updates:

```json
{
  "event": "span_updated",
  "span_id": "...",
  "updates": {
    "status": "ok",
    "end_time": 1739800002.456
  }
}
```

Client -> server actions:

#### Subscribe to one trace

```json
{
  "action": "subscribe_trace",
  "trace_id": "..."
}
```

#### Unsubscribe from one trace

```json
{
  "action": "unsubscribe_trace",
  "trace_id": "..."
}
```

---

## Error Format

```json
{ "detail": "Human-readable message" }
```

Validation errors use FastAPI's standard `detail[]` structure.

---

## SDK Transport Notes

- SDK sends span batches to `POST /v1/spans`.
- Default SDK exporter is async batching (`AsyncBatchExporter`), flushing periodically or on batch size threshold.
- SDK can be forced to sync exporter mode (`init(exporter="sync")`).
- Export failures are non-fatal to user code.
