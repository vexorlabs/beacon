# SDK Design

The `beacon-sdk` Python package is the instrumentation layer. It intercepts agent actions and sends them to the backend as OTEL-formatted spans.

**Package name:** `beacon-sdk`
**Import name:** `beacon_sdk` (or `from beacon import observe` via top-level re-exports)
**Location in repo:** `sdk/`

---

## Design Goals

1. **Zero-friction integration:** A developer should be able to add basic tracing with one import and one decorator.
2. **Automatic instrumentation:** For supported libraries (OpenAI, Anthropic, LangChain, Playwright), instrumentation happens automatically at import time.
3. **Correct context propagation:** The trace ID and parent span ID must be correctly threaded through async code and concurrent operations.
4. **Non-intrusive:** The SDK must never raise an exception that crashes the developer's agent. All SDK errors are swallowed and logged.
5. **OTEL-conformant:** All spans conform to the OpenTelemetry data model.

---

## Package Structure

```
sdk/
├── beacon_sdk/
│   ├── __init__.py          # Public API: observe, init, get_tracer
│   ├── tracer.py            # BeaconTracer: span creation, context management
│   ├── decorators.py        # @observe decorator
│   ├── context.py           # ContextVar-based trace context
│   ├── exporters.py         # HTTP exporter to backend
│   ├── models.py            # Span dataclasses (mirrors data-model.md)
│   └── integrations/
│       ├── __init__.py
│       ├── langchain.py     # BeaconCallbackHandler for LangChain
│       ├── openai.py        # Monkey-patch openai SDK
│       ├── anthropic.py     # Monkey-patch anthropic SDK
│       └── playwright.py    # Monkey-patch playwright
├── tests/
│   ├── test_tracer.py
│   ├── test_decorators.py
│   ├── test_exporters.py
│   └── integrations/
│       ├── test_langchain.py
│       └── test_openai.py
├── pyproject.toml
└── README.md
```

---

## Public API

### Initialization

```python
import beacon_sdk

# Option 1: Auto-init on first use (reads BEACON_BACKEND_URL from env)
beacon_sdk.init()

# Option 2: Explicit init with config
beacon_sdk.init(
    backend_url="http://localhost:7474",
    auto_patch=True,   # Enable monkey-patching (default: True)
    enabled=True,      # Set to False to disable all tracing
    exporter="auto",   # "auto"/"async" (batched, default) or "sync" (blocking)
)
```

Call `init()` once at the top of your script, before any imports of instrumented libraries. If you never call `init()`, the SDK does nothing (no-op mode).

### `@observe` Decorator

```python
from beacon_sdk import observe

@observe
def my_agent_step(query: str) -> str:
    # This function creates a span of type 'custom'
    return "result"

# With options:
@observe(name="my custom step", span_type="agent_step")
def my_agent_step(query: str) -> str:
    return "result"

# Works on async functions too:
@observe
async def my_async_step(query: str) -> str:
    return "result"
```

The decorator:
1. Creates a span when the function is entered
2. Sets `start_time`
3. Executes the function
4. Sets `end_time` and `status = ok` on success
5. Sets `status = error` and `error_message` on exception (re-raises the exception)
6. Exports the span to the backend

### Context Manager

```python
from beacon_sdk import tracer

with tracer.span("my operation", span_type="custom") as span:
    # Do work
    span.set_attribute("my.key", "my.value")
```

### Setting Attributes on the Current Span

```python
from beacon_sdk import get_current_span

span = get_current_span()
if span:
    span.set_attribute("agent.thought", "I should search for this...")
```

---

## Automatic Instrumentation

When `auto_patch=True` (default), calling `beacon_sdk.init()` monkey-patches the following libraries if they are installed:

### OpenAI SDK (`openai`)

Patches `openai.chat.completions.create` and the async variant.

Captured attributes:
- `llm.provider = "openai"`
- `llm.model` from request params
- `llm.prompt` from `messages` array (serialized to JSON string)
- `llm.completion` from response
- `llm.tokens.input`, `llm.tokens.output`, `llm.tokens.total` from `usage`
- `llm.cost_usd` computed from model pricing table
- `llm.finish_reason` from response

### Anthropic SDK (`anthropic`)

Patches `anthropic.messages.create` and async variant.

Captured attributes: same structure as OpenAI, mapped from Anthropic's response format.

### LangChain (`langchain_core`)

**Option A: Callback Handler (preferred)**

```python
from beacon_sdk.integrations.langchain import BeaconCallbackHandler

chain.invoke(input, config={"callbacks": [BeaconCallbackHandler()]})
```

**Option B: Auto-patch (less reliable, not recommended for LangChain)**

The callback handler approach is more reliable because LangChain has a well-defined callback interface.

`BeaconCallbackHandler` implements:
- `on_chain_start` → creates `chain` span
- `on_chain_end` → closes `chain` span
- `on_llm_start` → creates `llm_call` span
- `on_llm_end` → closes `llm_call` span with completion data
- `on_tool_start` → creates `tool_use` span
- `on_tool_end` → closes `tool_use` span
- `on_agent_action` → creates `agent_step` span
- `on_agent_finish` → closes `agent_step` span
- `on_chain_error` / `on_llm_error` / `on_tool_error` → sets `status = error`

### Playwright (`playwright`)

Patches `Page.goto`, `Page.click`, `Page.fill`, `Page.type`, `Page.screenshot`, `Page.wait_for_selector`.

Captured attributes:
- `browser.action` = method name ("navigate", "click", etc.)
- `browser.url` = `page.url` at time of action
- `browser.selector` = selector argument if present
- `browser.value` = text if action == "fill" or "type"
- `browser.screenshot` = base64 PNG if action == "screenshot"

---

## Trace Context Propagation

The SDK uses Python's `contextvars.ContextVar` to store the current trace context. This works correctly with:
- `asyncio` (context is automatically propagated to tasks created with `asyncio.create_task`)
- `threading` (each thread has its own context — you must manually copy context for multi-threaded agents)

```python
# Internal implementation sketch:
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass
class TraceContext:
    trace_id: str
    current_span_id: str | None

_trace_context: ContextVar[TraceContext | None] = ContextVar(
    "beacon_trace_context", default=None
)
```

When a new root span is started (no active context), the SDK generates a new `trace_id`. When a child span is started, it inherits the `trace_id` and sets `parent_span_id = current_span_id`.

---

## Exporter

The SDK ships two exporters, selectable via the `exporter` parameter on `init()`:

| Mode | Class | Behavior |
|------|-------|----------|
| `"async"` (default) | `AsyncBatchExporter` | Queues spans in memory, flushes on a background daemon thread every 1 s or when 50 spans accumulate — whichever comes first. Non-blocking. |
| `"sync"` | `HttpSpanExporter` | Sends each span immediately via a blocking HTTP POST. Useful for debugging the SDK itself. |
| `"auto"` | same as `"async"` | Alias — always selects the async batch exporter. |

```python
# Default — async batch exporter (recommended)
beacon_sdk.init()

# Explicit sync for debugging
beacon_sdk.init(exporter="sync")
```

Both exporters POST to `{backend_url}/v1/spans` and silently drop spans on connection/timeout errors (logged at `DEBUG`).

### Lifecycle

```python
beacon_sdk.flush()     # Force-flush any queued spans
beacon_sdk.shutdown()  # Flush + stop the background thread
```

An `atexit` handler calls `shutdown()` automatically when the process exits, so spans are never silently lost.

---

## Error Handling Philosophy

**The SDK must never break the developer's agent.** All SDK code is wrapped in try/except. Errors are logged at `DEBUG` level. If the backend is unreachable, spans are silently dropped.

```python
try:
    self.exporter.export([span])
except Exception as e:
    logger.debug(f"Beacon: span export failed (non-fatal): {e}")
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEACON_BACKEND_URL` | `http://localhost:7474` | Backend URL |
| `BEACON_ENABLED` | `true` | Set to `false` to disable all tracing |
| `BEACON_AUTO_PATCH` | `true` | Set to `false` to skip monkey-patching |
| `BEACON_LOG_LEVEL` | `WARNING` | SDK internal log level |

---

## Installation

```bash
# Basic
pip install beacon-sdk

# With LangChain support
pip install beacon-sdk[langchain]

# With Playwright support
pip install beacon-sdk[playwright]

# All extras
pip install beacon-sdk[all]
```

---

## Minimal Working Example

```python
import beacon_sdk
from openai import OpenAI

# 1. Init (auto-patches OpenAI)
beacon_sdk.init()

client = OpenAI()

# 2. Decorate your agent function
@beacon_sdk.observe
def run_agent(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# 3. Run
result = run_agent("What is the capital of France?")
print(result)

# Beacon UI at http://localhost:7474 will show the trace
```
