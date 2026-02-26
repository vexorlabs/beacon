<p align="center">
  <h1 align="center">Beacon</h1>
  <p align="center">
    <strong>Chrome DevTools for AI Agents</strong><br>
    Open-source, local-first debugging platform for AI agents.<br>
    Unified traces. Prompt replay. Time-travel debugging. AI-powered analysis.
  </p>
</p>

<p align="center">
  <a href="https://github.com/vexorlabs/beacon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vexorlabs/beacon" alt="License"></a>
  <a href="https://github.com/vexorlabs/beacon/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/vexorlabs/beacon/ci.yml?label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11+-3776ab" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-18+-339933" alt="Node.js 18+">
  <a href="https://github.com/vexorlabs/beacon/stargazers"><img src="https://img.shields.io/github/stars/vexorlabs/beacon" alt="GitHub Stars"></a>
  <a href="https://github.com/vexorlabs/beacon/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome"></a>
</p>

---

## Why Beacon

Most observability tools stop at LLM input/output. Beacon traces the **full execution** — LLM calls, tool use, browser actions, file operations, shell commands — in one interactive DAG.

| Feature | Description |
|---------|-------------|
| **Unified Trace Graph** | LLM + tools + computer-use spans in one DAG with React Flow |
| **Prompt Replay** | Edit and re-run any LLM call without re-running the agent |
| **Time-Travel Debugging** | Step through execution order, inspect state at any point |
| **Timeline / Waterfall** | Gantt-chart view with critical path highlighting |
| **AI-Powered Analysis** | Root cause, cost optimization, prompt suggestions, anomaly detection |
| **A/B Prompt Testing** | Compare prompts side-by-side with the same model |
| **Trace Comparison** | Side-by-side diff with AI divergence detection and baseline support |
| **Full-Text Search** | Search across span names, attributes, and trace names |
| **Tags & Annotations** | Categorize traces and annotate individual spans |
| **Import / Export** | JSON, OTEL JSON, and CSV export; JSON import |
| **Dashboard Analytics** | Trend charts, cost forecasting, most expensive prompts/tools |
| **Real-Time Updates** | WebSocket streaming of new spans as they arrive |
| **Local-First** | SQLite, no cloud dependency, no account required |

---

## Quick Start

### 1. Run Beacon

```bash
git clone https://github.com/vexorlabs/beacon.git
cd beacon
make install
make dev
```

Open **http://localhost:5173**.

Try it without API keys — generate sample traces with:

```bash
make demo
```

### 2. Instrument Your Python Agent

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

### 3. Instrument Your JS/TS Agent

```bash
npm install beacon-sdk
```

```typescript
import { init, observe } from "beacon-sdk";

init(); // Auto-patches OpenAI, Anthropic, Vercel AI SDK

const myAgent = observe({ name: "my-agent", spanType: "agent_step" }, async () => {
  // Your agent logic — LLM calls are traced automatically
});

await myAgent();
```

---

## Integrations

### Python SDK (`beacon-sdk`)

| Integration | What Gets Traced | Auto-Patched |
|-------------|-----------------|:------------:|
| OpenAI | Chat completions (sync/async + streaming + tool calls) | Yes |
| Anthropic | Messages (sync/async + streaming + tool use) | Yes |
| Google Gemini | Generate content (sync/async + streaming) | Yes |
| LangChain | Chains, LLM calls, tool use, agent steps | Callback |
| CrewAI | Crew kickoff, agent steps, task execution | Yes |
| AutoGen | Agent replies, group chat runs | Yes |
| LlamaIndex | Query engine, retriever, LLM calls | Yes |
| Ollama | Chat and generate (native client) | Yes |
| Playwright | Page actions (goto, click, fill, screenshot) | Yes |
| subprocess | `run()` and `check_output()` | Yes |
| File I/O | `open()` read/write/append | Opt-in |

### JS/TS SDK (`beacon-sdk` npm)

| Integration | What Gets Traced | Auto-Patched |
|-------------|-----------------|:------------:|
| OpenAI | Chat completions (streaming + tool calls) | Yes |
| Anthropic | Messages (streaming + tool use) | Yes |
| Vercel AI SDK | `generateText()` and `streamText()` | Yes |

### OTLP Ingestion

Any OpenTelemetry-instrumented application can send traces to Beacon via `POST /v1/otlp/traces` — no SDK required. See the [SDK README](sdk/README.md#otlp-ingestion-sdk-free) for details.

---

## Architecture

```
Your Agent (Python / JS / TS)
   |
   |  beacon-sdk: @observe decorator + auto-patching
   |
   v
POST /v1/spans  (or POST /v1/otlp/traces)
   |
   v
Beacon Backend  (FastAPI + SQLite — port 7474)
   |  REST API + WebSocket (/ws/live)
   v
Beacon UI  (React + Vite — port 5173)
   |-- Dashboard   (analytics, trends, cost forecasting)
   |-- Traces      (graph + timeline + span detail + time-travel)
   |-- Playground   (chat, model compare, A/B prompt testing)
   |-- Settings     (API keys, data management)
```

```
beacon/
├── backend/    # FastAPI + SQLite (Python)
├── frontend/   # React + Vite + TypeScript
├── sdk/        # beacon-sdk Python package
├── sdk-js/     # beacon-sdk JS/TS package
└── docs/       # Architecture, API contracts, data model, roadmap
```

See [docs/architecture.md](docs/architecture.md), [docs/api-contracts.md](docs/api-contracts.md), [docs/data-model.md](docs/data-model.md).

---

## Development

```bash
make dev            # Start backend (7474) + frontend (5173)
make dev-backend    # Backend only
make dev-frontend   # Frontend only
make test           # All tests (backend + SDK + JS SDK + frontend)
make lint           # All linters
make format         # All formatters
make demo           # Generate sample traces
make stop           # Stop dev servers
```

Backend API docs: **http://localhost:7474/docs**

---

## Contributing

We welcome contributions! Please read the [Contributing Guide](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

See our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Community

- [GitHub Discussions](https://github.com/vexorlabs/beacon/discussions) — questions, ideas, show & tell
- [GitHub Issues](https://github.com/vexorlabs/beacon/issues) — bug reports and feature requests
- Security issues — see [SECURITY.md](SECURITY.md)

---

## License

MIT — see [LICENSE](LICENSE).
