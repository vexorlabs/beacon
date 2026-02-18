# Data Model

This document defines Beacon's persisted schema and span attribute conventions.

---

## Core Concepts

### Trace
A trace is one agent run, identified by `trace_id`.

In code, trace summary rows are persisted in `traces` (not purely derived at read-time).

### Span
A span is one unit of work (LLM call, tool use, browser action, etc.).

### Replay Run
A replay run stores output/diff for a replayed `llm_call` span.

---

## Span Schema

```python
class Span:
    span_id: str
    trace_id: str
    parent_span_id: str | None

    span_type: SpanType
    name: str
    status: SpanStatus
    error_message: str | None

    start_time: float
    end_time: float | None

    attributes: dict[str, Any]
```

### `SpanType`

```text
llm_call | tool_use | agent_step | browser_action | file_operation | shell_command | chain | custom
```

### `SpanStatus`

```text
ok | error | unset
```

---

## Attribute Conventions

### `llm_call`

Common keys:
- `llm.provider` (string)
- `llm.model` (string)
- `llm.prompt` (JSON string)
- `llm.completion` (string)
- `llm.tokens.input` / `llm.tokens.output` / `llm.tokens.total` (number)
- `llm.cost_usd` (number)
- `llm.temperature` (number, optional)
- `llm.max_tokens` (number, optional)
- `llm.finish_reason` (string, optional)
- `llm.tool_calls` (JSON string, optional)

### `tool_use`

Common keys:
- `tool.name`
- `tool.input`
- `tool.output`
- `tool.framework` (optional)

### `browser_action`

Common keys:
- `browser.action`
- `browser.url`
- `browser.selector` (optional)
- `browser.value` (optional)
- `browser.page_title` (optional)
- `browser.screenshot` (optional base64 PNG string)

### `file_operation`

Common keys:
- `file.operation`
- `file.path`
- `file.size_bytes` (optional)
- `file.content` (optional/truncated)

### `shell_command`

Common keys:
- `shell.command`
- `shell.returncode`
- `shell.stdout` (optional/truncated)
- `shell.stderr` (optional/truncated)

### `agent_step`

Common keys:
- `agent.framework`
- `agent.step_name`
- `agent.input`
- `agent.output`
- `agent.thought`

### `chain`

Common keys:
- `chain.type`
- `chain.input`
- `chain.output`

---

## SQLite Schema

DB path default: `~/.beacon/traces.db`

### `traces`

Stores per-trace summary fields.

```sql
CREATE TABLE traces (
  trace_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL,
  span_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'unset',
  tags TEXT DEFAULT '{}',
  total_cost_usd REAL DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  created_at REAL NOT NULL
);
```

Indexes:
- `idx_traces_created_at`
- `idx_traces_status`

### `spans`

```sql
CREATE TABLE spans (
  span_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL REFERENCES traces(trace_id) ON DELETE CASCADE,
  parent_span_id TEXT,
  span_type TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'unset',
  error_message TEXT,
  start_time REAL NOT NULL,
  end_time REAL,
  attributes TEXT DEFAULT '{}',
  created_at REAL NOT NULL
);
```

Indexes:
- `idx_spans_trace_id`
- `idx_spans_parent_span_id`
- `idx_spans_span_type`
- `idx_spans_start_time`
- `idx_spans_name`

### `replay_runs`

```sql
CREATE TABLE replay_runs (
  replay_id TEXT PRIMARY KEY,
  original_span_id TEXT NOT NULL REFERENCES spans(span_id) ON DELETE CASCADE,
  trace_id TEXT NOT NULL REFERENCES traces(trace_id) ON DELETE CASCADE,
  modified_input TEXT NOT NULL,
  new_output TEXT NOT NULL,
  diff TEXT NOT NULL,
  created_at REAL NOT NULL
);
```

---

## Derived Fields

Derived on read:
- `duration_ms = (end_time - start_time) * 1000` for spans/traces when `end_time` exists

Trace status logic in service layer:
- `error` dominates
- then `unset`
- else `ok`

---

## Size Guards (SDK)

SDK truncation limits (`beacon_sdk.models`):
- `llm.prompt`: 50,000 chars
- `llm.completion`: 50,000 chars
- `file.content`: 2,000 chars
- `shell.stdout`: 4,000 chars
- `shell.stderr`: 4,000 chars
- `browser.screenshot`: dropped when base64 string exceeds configured max bytes
