# Data Model

This document defines the trace schema (OTEL-based) and the SQLite database schema. This is the source of truth for how trace data is structured throughout the system.

---

## Core Concepts

### Trace
A complete agent execution run. All spans from one agent run share the same `trace_id`. A trace is derived, not stored directly — it is the set of all spans with a given `trace_id`.

### Span
A single unit of work. Every observable action the agent takes — an LLM call, a tool invocation, a browser click — produces one span. Spans are the atomic unit of storage.

### Span Tree
Spans have a `parent_span_id` that forms a tree (technically a DAG when replay spans are included). The root span has no parent. The graph visualizer renders this tree.

---

## Span Schema

### Core Fields (Required on All Spans)

```python
class Span:
    # Identity
    span_id: str          # UUID v4, unique per span
    trace_id: str         # UUID v4, same for all spans in one agent run
    parent_span_id: str | None  # UUID v4 of parent span, None for root

    # Timing
    start_time: float     # Unix timestamp (seconds, float for sub-second precision)
    end_time: float | None  # None while span is in progress

    # Classification
    span_type: SpanType   # Enum (see below)
    name: str             # Human-readable label (e.g., "openai.chat.completions")
    status: SpanStatus    # Enum: ok | error | unset

    # Optional
    error_message: str | None  # Set when status == error
    attributes: dict[str, Any]  # Type-specific metadata (see below)
```

### SpanType Enum

```python
class SpanType(str, Enum):
    LLM_CALL        = "llm_call"        # LLM API call
    TOOL_USE        = "tool_use"        # Tool/function invocation
    AGENT_STEP      = "agent_step"      # Logical agent reasoning step
    BROWSER_ACTION  = "browser_action"  # Playwright/Selenium action
    FILE_OPERATION  = "file_operation"  # File read/write/delete
    SHELL_COMMAND   = "shell_command"   # subprocess call
    CHAIN           = "chain"           # LangChain chain execution
    CUSTOM          = "custom"          # Developer-defined
```

### SpanStatus Enum

```python
class SpanStatus(str, Enum):
    OK      = "ok"       # Completed successfully
    ERROR   = "error"    # Threw an exception
    UNSET   = "unset"    # In progress (span not yet ended)
```

---

## Span Attributes by Type

Attributes are stored as JSON in the `attributes` column. The structure depends on `span_type`.

### `llm_call` Attributes

```python
{
    "llm.provider":        str,          # "openai" | "anthropic" | "google" | ...
    "llm.model":           str,          # "gpt-4o" | "claude-3-7-sonnet" | ...
    "llm.prompt":          str,          # Full prompt text (system + user messages as JSON string)
    "llm.completion":      str,          # Full completion text
    "llm.tokens.input":    int,          # Input token count
    "llm.tokens.output":   int,          # Output token count
    "llm.tokens.total":    int,          # Sum of above
    "llm.cost_usd":        float,        # Estimated cost in USD
    "llm.temperature":     float | None, # Temperature if set
    "llm.max_tokens":      int | None,   # Max tokens if set
    "llm.stop_sequences":  list[str] | None,
    "llm.finish_reason":   str,          # "stop" | "length" | "tool_calls" | ...
    "llm.tool_calls":      list | None,  # If model called tools
}
```

### `tool_use` Attributes

```python
{
    "tool.name":        str,   # Name of the tool (e.g., "search_web", "read_file")
    "tool.input":       str,   # JSON string of tool input parameters
    "tool.output":      str,   # JSON string of tool output
    "tool.framework":   str,   # "langchain" | "crewai" | "custom"
}
```

### `browser_action` Attributes

```python
{
    "browser.action":       str,          # "navigate" | "click" | "type" | "screenshot" | "wait" | ...
    "browser.url":          str,          # Current page URL at time of action
    "browser.selector":     str | None,   # CSS selector or XPath if applicable
    "browser.value":        str | None,   # Text typed, if action == "type"
    "browser.screenshot":   str | None,   # Base64-encoded PNG screenshot (optional, can be large)
    "browser.page_title":   str | None,
}
```

### `file_operation` Attributes

```python
{
    "file.operation":   str,          # "read" | "write" | "append" | "delete" | "exists"
    "file.path":        str,          # Absolute or relative file path
    "file.size_bytes":  int | None,
    "file.content":     str | None,   # File content snippet (truncated to 2000 chars)
}
```

### `shell_command` Attributes

```python
{
    "shell.command":     str,          # The full command string
    "shell.args":        list[str],    # Parsed argument list
    "shell.cwd":         str | None,   # Working directory
    "shell.exit_code":   int | None,   # Return code
    "shell.stdout":      str | None,   # Stdout (truncated to 4000 chars)
    "shell.stderr":      str | None,   # Stderr (truncated to 4000 chars)
    "shell.env":         dict | None,  # Environment variable overrides
}
```

### `agent_step` Attributes

```python
{
    "agent.framework":  str,          # "langchain" | "crewai" | "autogen" | "custom"
    "agent.step_name":  str,          # Human-readable step name
    "agent.input":      str | None,   # Step input (JSON string)
    "agent.output":     str | None,   # Step output (JSON string)
    "agent.thought":    str | None,   # Agent's reasoning/thought (if available)
}
```

### `chain` Attributes (LangChain-specific)

```python
{
    "chain.type":       str,   # LangChain chain class name
    "chain.input":      str,   # JSON string
    "chain.output":     str,   # JSON string
}
```

---

## SQLite Database Schema

Database file: `~/.beacon/traces.db` (created automatically on first run)

### `traces` Table

Stores one row per unique trace (agent run).

```sql
CREATE TABLE traces (
    trace_id        TEXT PRIMARY KEY,     -- UUID v4
    name            TEXT NOT NULL,        -- Human-readable label (first span's name or agent name)
    start_time      REAL NOT NULL,        -- Unix timestamp of first span
    end_time        REAL,                 -- Unix timestamp of last span (NULL if in progress)
    span_count      INTEGER DEFAULT 0,    -- Total number of spans in this trace
    status          TEXT DEFAULT 'unset', -- 'ok' | 'error' | 'unset'
    tags            TEXT DEFAULT '{}',    -- JSON object of user-defined tags
    total_cost_usd  REAL DEFAULT 0,       -- Sum of all llm.cost_usd in trace
    total_tokens    INTEGER DEFAULT 0,    -- Sum of all llm.tokens.total in trace
    created_at      REAL NOT NULL         -- Insert timestamp (for sorting)
);

CREATE INDEX idx_traces_created_at ON traces (created_at DESC);
CREATE INDEX idx_traces_status ON traces (status);
```

### `spans` Table

Stores one row per span.

```sql
CREATE TABLE spans (
    span_id         TEXT PRIMARY KEY,     -- UUID v4
    trace_id        TEXT NOT NULL,        -- References traces.trace_id
    parent_span_id  TEXT,                 -- References spans.span_id (NULL for root)
    span_type       TEXT NOT NULL,        -- SpanType enum value
    name            TEXT NOT NULL,        -- Human-readable label
    status          TEXT DEFAULT 'unset', -- SpanStatus enum value
    error_message   TEXT,                 -- NULL unless status == 'error'
    start_time      REAL NOT NULL,        -- Unix timestamp (float)
    end_time        REAL,                 -- NULL while in progress
    attributes      TEXT DEFAULT '{}',    -- JSON object of type-specific attributes
    created_at      REAL NOT NULL,        -- Insert timestamp

    FOREIGN KEY (trace_id) REFERENCES traces (trace_id) ON DELETE CASCADE
);

CREATE INDEX idx_spans_trace_id ON spans (trace_id);
CREATE INDEX idx_spans_parent_span_id ON spans (parent_span_id);
CREATE INDEX idx_spans_span_type ON spans (span_type);
CREATE INDEX idx_spans_start_time ON spans (start_time);
CREATE INDEX idx_spans_name ON spans (name);
```

### `replay_runs` Table

Stores the result of replay operations (when a developer edits a prompt and re-runs a step).

```sql
CREATE TABLE replay_runs (
    replay_id           TEXT PRIMARY KEY,  -- UUID v4
    original_span_id    TEXT NOT NULL,     -- References spans.span_id
    trace_id            TEXT NOT NULL,     -- References traces.trace_id
    modified_input      TEXT NOT NULL,     -- JSON: what was changed
    new_output          TEXT NOT NULL,     -- JSON: what the new output was
    diff                TEXT NOT NULL,     -- JSON: diff between old and new output
    created_at          REAL NOT NULL,

    FOREIGN KEY (original_span_id) REFERENCES spans (span_id) ON DELETE CASCADE,
    FOREIGN KEY (trace_id) REFERENCES traces (trace_id) ON DELETE CASCADE
);
```

---

## Computed / Derived Fields

These are not stored but are computed on read:

| Field | Computed From | Used In |
|-------|--------------|---------|
| `duration_ms` | `(end_time - start_time) * 1000` | API responses, UI |
| `child_spans` | `SELECT * FROM spans WHERE parent_span_id = ?` | Graph building |
| `trace.status` | Worst status of all spans (error > unset > ok) | Trace list |

---

## Trace ID Generation

The SDK generates a `trace_id` at the start of each agent run using `uuid.uuid4()`. Spans within that run share the same `trace_id`. The SDK stores the active `trace_id` in Python's `contextvars.ContextVar` to propagate it across async boundaries.

---

## Size Limits

To prevent the database from growing unboundedly, the SDK enforces these limits before sending:

| Field | Limit | Behavior on Exceed |
|-------|-------|-------------------|
| `llm.prompt` | 50,000 chars | Truncated with `[TRUNCATED]` suffix |
| `llm.completion` | 50,000 chars | Truncated |
| `file.content` | 2,000 chars | Truncated |
| `shell.stdout` | 4,000 chars | Truncated |
| `shell.stderr` | 4,000 chars | Truncated |
| `browser.screenshot` | 500 KB (base64) | Dropped (attribute set to null) |
