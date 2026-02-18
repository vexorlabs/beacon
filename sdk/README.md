# beacon-sdk

Instrumentation SDK for Beacon.

Add tracing to Python agents with minimal changes and inspect traces in Beacon UI.

## Quickstart

```bash
pip install beacon-sdk[openai]
```

```python
import beacon_sdk
from openai import OpenAI

beacon_sdk.init()
client = OpenAI()

@beacon_sdk.observe
def run_agent(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content or ""

run_agent("What is the capital of France?")
```

Start Beacon (`make dev`) and open `http://localhost:5173`.

## Integrations

| Integration | Behavior |
|---|---|
| OpenAI | auto-patched chat completions (sync/async + streaming) |
| Anthropic | auto-patched messages (sync/async + streaming) |
| Playwright | auto-patched page actions |
| subprocess | auto-patched `run` and `check_output` |
| LangChain | callback handler (`BeaconCallbackHandler`) |

File operation patching (`builtins.open`) is opt-in via `BEACON_PATCH_FILE_OPS=true`.

## Install Extras

```bash
pip install beacon-sdk
pip install beacon-sdk[openai]
pip install beacon-sdk[anthropic]
pip install beacon-sdk[playwright]
pip install beacon-sdk[all]
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `BEACON_BACKEND_URL` | `http://localhost:7474` | backend ingestion URL |
| `BEACON_ENABLED` | `true` | enable/disable tracing |
| `BEACON_AUTO_PATCH` | `true` | enable/disable auto-patching |
| `BEACON_LOG_LEVEL` | `WARNING` | SDK logging level |
| `BEACON_PATCH_FILE_OPS` | `false` | enable file operation patch |

`init()` options:

```python
beacon_sdk.init(
    backend_url="http://localhost:7474",
    auto_patch=True,
    enabled=True,
    exporter="auto",  # auto | async | sync
)
```

## Public API

- `init()`
- `observe`
- `get_current_span()`
- `get_tracer()`
- `flush()`
- `shutdown()`
- `Span`, `SpanType`, `SpanStatus`, `BeaconTracer`
