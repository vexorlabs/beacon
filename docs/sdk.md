# SDK Design

`beacon-sdk` is the Python instrumentation package used by agent code.

Package name: `beacon-sdk`
Import name: `beacon_sdk`
Location: `sdk/`

---

## Design Goals

1. Minimal integration friction (`init()` + `@observe`)
2. Safe, non-fatal instrumentation
3. Correct trace context propagation across nested/async calls
4. Usable automatic instrumentation for common agent libraries
5. Consistent span schema for backend/frontend consumption

---

## Package Structure

```text
sdk/
├── beacon_sdk/
│   ├── __init__.py
│   ├── tracer.py
│   ├── decorators.py
│   ├── context.py
│   ├── exporters.py
│   ├── models.py
│   ├── pricing.py
│   └── integrations/
│       ├── openai.py
│       ├── anthropic.py
│       ├── playwright.py
│       ├── livekit.py
│       ├── subprocess_patch.py
│       ├── file_patch.py
│       └── langchain.py
├── examples/
└── tests/
```

---

## Public API

### Initialization

```python
import beacon_sdk

beacon_sdk.init()

# explicit options
beacon_sdk.init(
    backend_url="http://localhost:7474",
    auto_patch=True,
    enabled=True,
    exporter="auto",  # "auto" | "async" | "sync"
)
```

`init()` behavior:
- `enabled=false` disables tracing (no-op tracer)
- default exporter is async batching (`auto` -> async)
- registers shutdown handler for queued spans

### Decorator

```python
from beacon_sdk import observe

@observe
def fn():
    ...

@observe(name="step", span_type="agent_step")
def step():
    ...
```

Works for sync and async functions.

### Accessing Current Span

```python
import beacon_sdk

span = beacon_sdk.get_current_span()
if span:
    span.set_attribute("agent.note", "thinking")
```

### Low-Level Tracer Access

```python
import beacon_sdk

tracer = beacon_sdk.get_tracer()
if tracer:
    with tracer.span("custom", span_type=beacon_sdk.SpanType.CUSTOM):
        ...
```

### Exporter Lifecycle

```python
beacon_sdk.flush()
beacon_sdk.shutdown()
```

---

## Auto Instrumentation

When `auto_patch=True`, SDK attempts to patch installed libraries.

### OpenAI
- patches chat completions sync + async
- supports streaming wrappers
- captures provider/model/prompt/completion/tokens/cost/tool_calls

### Anthropic
- patches messages create sync + async
- supports streaming wrappers
- captures provider/model/prompt/completion/tokens/cost/tool_calls

### Playwright
- patches sync/async `Page` actions (`goto`, `click`, `fill`, `type`, `screenshot`, `wait_for_selector`)
- emits `browser_action` spans

### LiveKit Agents
- patches `livekit.agents.AgentSession` lifecycle methods: `start`, `run`, `say`, `generate_reply`, `interrupt`
- records key voice events from `AgentSession.emit`: `user_input_transcribed`, `speech_created`, `function_tools_executed`, `error`, `close`
- emits `agent_step`/`tool_use`/`custom` spans with `agent.framework: "livekit"`

### subprocess
- patches `subprocess.run` and `subprocess.check_output`
- emits `shell_command` spans (`shell.command`, `shell.returncode`, stdout/stderr)

### File operations (opt-in)
- `builtins.open` patch lives in `integrations/file_patch.py`
- only enabled when `BEACON_PATCH_FILE_OPS=true`

### LangChain
- callback-based integration via `BeaconCallbackHandler`
- no auto monkey-patch path; caller passes callback explicitly

---

## Trace Context

Context is stored using `contextvars`:
- root span starts a new `trace_id`
- nested spans inherit `trace_id` and set `parent_span_id`

`register_span` / `get_active_span` supports `get_current_span()` lookups.

---

## Exporters

### `HttpSpanExporter`
- synchronous HTTP POST per export call
- useful for debugging SDK behavior

### `AsyncBatchExporter` (default)
- queue + background flush thread
- flushes by interval and batch-size threshold
- non-fatal on connection errors

Transport endpoint:
- `{backend_url}/v1/spans`

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `BEACON_BACKEND_URL` | `http://localhost:7474` | ingestion base URL |
| `BEACON_ENABLED` | `true` | disable/enable instrumentation |
| `BEACON_AUTO_PATCH` | `true` | toggle auto monkey-patching |
| `BEACON_LOG_LEVEL` | `WARNING` | SDK logger verbosity |
| `BEACON_PATCH_FILE_OPS` | `false` | opt-in file operation patch |

---

## Installation

```bash
pip install beacon-sdk
pip install beacon-sdk[openai]
pip install beacon-sdk[anthropic]
pip install beacon-sdk[playwright]
pip install beacon-sdk[livekit]
pip install beacon-sdk[all]
```

For LangChain integration, install LangChain packages separately and use `BeaconCallbackHandler`.

---

## Minimal Example

```python
import beacon_sdk
from beacon_sdk import observe

beacon_sdk.init()

@observe(name="run_agent", span_type="agent_step")
def run_agent() -> str:
    return "ok"

run_agent()
```
