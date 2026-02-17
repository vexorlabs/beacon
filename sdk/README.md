# beacon-sdk

Instrumentation SDK for [Beacon](https://github.com/vexorlabs/beacon) — Chrome DevTools for AI Agents.

Add tracing to your AI agent in 2 lines of code. See every LLM call, tool use, and browser action in an interactive graph UI.

## Quickstart

```bash
pip install beacon-sdk[openai]
```

Add two lines to your existing code:

```python
import beacon_sdk
from openai import OpenAI

beacon_sdk.init()  # <-- line 1

client = OpenAI()

@beacon_sdk.observe  # <-- line 2
def run_agent(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content

run_agent("What is the capital of France?")
```

Start the Beacon backend and UI, then open [http://localhost:5173](http://localhost:5173):

```bash
git clone https://github.com/vexorlabs/beacon && cd beacon
make install && make dev
```

Your trace appears in the UI with a full graph of spans, token counts, costs, and timing.

## Integrations

| Integration | Setup | What's traced |
|---|---|---|
| **OpenAI** | Automatic — just call `init()` | Chat completions, tokens, cost |
| **Anthropic** | Automatic — just call `init()` | Messages, tokens, cost |
| **Playwright** | Automatic — just call `init()` | Page navigation, clicks, screenshots |
| **subprocess** | Automatic — just call `init()` | Shell commands, stdout, stderr |
| **LangChain** | Pass `BeaconCallbackHandler()` to your chain | Chains, LLM calls, tool use, agent steps |

LangChain example:

```python
from beacon_sdk.integrations.langchain import BeaconCallbackHandler

chain.invoke(input, config={"callbacks": [BeaconCallbackHandler()]})
```

Install extras for specific integrations:

```bash
pip install beacon-sdk[openai]       # OpenAI
pip install beacon-sdk[anthropic]    # Anthropic
pip install beacon-sdk[playwright]   # Playwright
pip install beacon-sdk[all]          # Everything
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `BEACON_BACKEND_URL` | `http://localhost:7474` | Backend URL for span ingestion |
| `BEACON_ENABLED` | `true` | Set to `false` to disable all tracing |
| `BEACON_AUTO_PATCH` | `true` | Set to `false` to disable auto-patching |
| `BEACON_LOG_LEVEL` | `WARNING` | SDK log level (`DEBUG` for troubleshooting) |

All options can also be passed to `init()`:

```python
beacon_sdk.init(backend_url="http://custom:7474", auto_patch=False, enabled=True)
```

## Examples

See [`examples/`](./examples/) for runnable scripts:

- **[hello_world.py](./examples/hello_world.py)** — Core SDK with `@observe` decorator
- **[langchain_agent.py](./examples/langchain_agent.py)** — LangChain agent with callback handler
- **[browser_agent.py](./examples/browser_agent.py)** — Playwright browser automation

## API

| Export | Description |
|---|---|
| `init()` | Initialize the SDK. Call once at startup. |
| `@observe` | Decorator to wrap functions as spans (sync + async) |
| `get_current_span()` | Get the active span from context |
| `get_tracer()` | Get the global `BeaconTracer` instance |
| `Span` | Span data model |
| `SpanType` | Enum: `LLM_CALL`, `TOOL_USE`, `AGENT_STEP`, `BROWSER_ACTION`, `FILE_OPERATION`, `SHELL_COMMAND`, `CHAIN`, `CUSTOM` |
| `SpanStatus` | Enum: `OK`, `ERROR`, `UNSET` |
| `BeaconTracer` | Low-level tracer (use `@observe` instead for most cases) |

## License

MIT
