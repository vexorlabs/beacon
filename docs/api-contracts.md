# API Contracts

This document defines all HTTP and WebSocket APIs exposed by `beacon-backend`. It is the contract between the backend and:
- The **SDK** (which sends spans to the backend)
- The **UI** (which reads traces from the backend)

**Base URL:** `http://localhost:7474`

All request/response bodies are JSON. All timestamps are Unix float (seconds since epoch).

---

## REST API

### Span Ingestion (Used by SDK)

#### `POST /v1/spans`

Ingest one or more spans from the SDK.

**Request body:**
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
        "llm.prompt": "[{\"role\": \"user\", \"content\": \"What is 2+2?\"}]",
        "llm.completion": "4",
        "llm.tokens.input": 14,
        "llm.tokens.output": 1,
        "llm.tokens.total": 15,
        "llm.cost_usd": 0.000075,
        "llm.finish_reason": "tool_calls",
        "llm.tool_calls": "[{\"id\": \"call_abc123\", \"function\": {\"name\": \"get_weather\", \"arguments\": \"{\\\"location\\\": \\\"San Francisco\\\"}\"}}]"
      }
    }
  ]
}
```

**Response `200 OK`:**
```json
{
  "accepted": 1,
  "rejected": 0
}
```

**Response `422 Unprocessable Entity`:** Validation error (malformed span).

---

### Trace List (Used by UI)

#### `GET /v1/traces`

List all traces, newest first.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |
| `status` | string | (all) | Filter: `ok`, `error`, `unset` |

**Response `200 OK`:**
```json
{
  "traces": [
    {
      "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "name": "Travel booking agent",
      "start_time": 1739800000.0,
      "end_time": 1739800045.3,
      "duration_ms": 45300,
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

---

#### `GET /v1/traces/{trace_id}`

Get a single trace with all its spans.

**Response `200 OK`:**
```json
{
  "trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Travel booking agent",
  "start_time": 1739800000.0,
  "end_time": 1739800045.3,
  "duration_ms": 45300,
  "span_count": 23,
  "status": "ok",
  "total_cost_usd": 0.042,
  "total_tokens": 12450,
  "tags": {},
  "spans": [
    {
      "span_id": "550e8400-...",
      "parent_span_id": null,
      "span_type": "agent_step",
      "name": "root",
      "status": "ok",
      "start_time": 1739800000.0,
      "end_time": 1739800045.3,
      "duration_ms": 45300,
      "attributes": {}
    }
    // ... more spans
  ]
}
```

**Response `404 Not Found`:**
```json
{ "detail": "Trace not found" }
```

---

#### `GET /v1/traces/{trace_id}/graph`

Get a trace formatted as a graph (nodes + edges) for direct use by React Flow.

**Response `200 OK`:**
```json
{
  "nodes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "spanNode",
      "data": {
        "span_id": "550e8400-...",
        "span_type": "llm_call",
        "name": "openai.chat.completions",
        "status": "ok",
        "duration_ms": 2333,
        "cost_usd": 0.000075
      },
      "position": { "x": 0, "y": 0 }
    }
  ],
  "edges": [
    {
      "id": "edge-parent-child",
      "source": "parent-span-id",
      "target": "550e8400-..."
    }
  ]
}
```

Note: `position` is initialized to `{x: 0, y: 0}`. Layout is computed client-side by React Flow using the `dagre` layout algorithm.

---

### Span Detail (Used by UI)

#### `GET /v1/spans/{span_id}`

Get full detail for a single span, including all attributes.

**Response `200 OK`:** Full span object (same structure as in the trace spans array, but with all attributes included).

**Response `404 Not Found`:**
```json
{ "detail": "Span not found" }
```

---

### Replay (Used by UI — Time-Travel Feature)

#### `POST /v1/replay`

Re-execute a span (currently only supported for `llm_call` spans) with modified input.

**Request body:**
```json
{
  "span_id": "550e8400-e29b-41d4-a716-446655440000",
  "modified_attributes": {
    "llm.prompt": "[{\"role\": \"user\", \"content\": \"What is 2+2? Show your work.\"}]"
  }
}
```

**Response `200 OK`:**
```json
{
  "replay_id": "new-uuid",
  "original_span_id": "550e8400-...",
  "new_output": {
    "llm.completion": "2 + 2 = 4. Here's how: ...",
    "llm.tokens.input": 20,
    "llm.tokens.output": 45,
    "llm.cost_usd": 0.0003
  },
  "diff": {
    "old_completion": "4",
    "new_completion": "2 + 2 = 4. Here's how: ...",
    "changed": true
  }
}
```

**Response `400 Bad Request`:**
```json
{ "detail": "Replay only supported for span_type=llm_call" }
```

**Response `500 Internal Server Error`:**
```json
{ "detail": "LLM API call failed: ..." }
```

---

### Health Check

#### `GET /health`

Simple health check for the UI to verify the backend is running.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "db_path": "/Users/you/.beacon/traces.db"
}
```

---

## WebSocket API

### `WS /ws/live`

Real-time span streaming. The UI connects to this WebSocket when it loads. The backend pushes new spans as they arrive from the SDK.

**Connection:** `ws://localhost:7474/ws/live`

**Server → Client messages:**

All messages are JSON with an `event` field.

#### `span_created` event

Sent when a new span is received from the SDK.

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
    "start_time": 1739800000.123,
    "end_time": 1739800002.456,
    "duration_ms": 2333,
    "attributes": { ... }
  }
}
```

#### `span_updated` event

Sent when a span's end_time or status is updated (e.g., when an in-progress span completes).

```json
{
  "event": "span_updated",
  "span_id": "...",
  "updates": {
    "end_time": 1739800002.456,
    "status": "ok"
  }
}
```

#### `trace_created` event

Sent when a brand-new trace is seen for the first time.

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

**Client → Server messages:**

#### Subscribe to a specific trace

```json
{
  "action": "subscribe_trace",
  "trace_id": "..."
}
```

After this, the client only receives `span_created` and `span_updated` events for that trace.

#### Unsubscribe

```json
{
  "action": "unsubscribe_trace",
  "trace_id": "..."
}
```

---

## Error Response Format

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "spans", 0, "span_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## SDK Transport

The SDK sends spans to `POST /v1/spans` in batches. Batching strategy:
- Send immediately when a span ends (low-latency mode, default for MVP)
- Future: configurable batch size and flush interval

The SDK does not retry on failure in MVP. Failures are logged to stderr but do not crash the agent.

The SDK reads the backend URL from:
1. `BEACON_BACKEND_URL` environment variable
2. Default: `http://localhost:7474`
