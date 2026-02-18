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
        "cost_usd": 0.000075
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
