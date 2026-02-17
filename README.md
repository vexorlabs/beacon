# Beacon

**The open-source debugger for AI agents.** Beacon gives you a unified, interactive view of your agent's entire execution — from LLM reasoning to browser clicks to file operations — so you can stop guessing and start debugging.

> **Status:** Early development (Phase 2 complete). Under active development. Not yet ready for production use.

---

## The Problem

Debugging AI agents with existing tools means sifting through raw LLM logs and hoping you can piece together what went wrong. Tools like LangSmith show you LLM inputs and outputs but miss the crucial context of *what the agent actually did* — browser interactions, file writes, shell commands.

You're left debugging by guesswork.

## The Solution

Beacon traces everything:

- **LLM calls** — prompt, completion, tokens, cost
- **Tool invocations** — input parameters, output, latency
- **Browser actions** — clicks, navigations, keystrokes (via Playwright)
- **File operations** — reads, writes, deletes
- **Shell commands** — `subprocess` calls with stdout/stderr

All of it appears as a single, interactive execution graph. Click any node to inspect the agent's state at that exact moment. Edit a prompt and replay just that step. Step forward and back through the execution timeline.

**This is Chrome DevTools for AI agents.**

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Unified Execution Graph** | Interactive React Flow graph showing the complete agent run — LLM calls, tool uses, and computer-use actions together |
| **Time-Travel Debugging** | Step through your agent's execution. Inspect state at any point in time |
| **Prompt Editor + Replay** | Edit any LLM prompt and replay that single step without re-running the whole agent |
| **Real-Time Tracing** | Watch spans appear in the UI as your agent runs via WebSocket streaming |
| **Framework-Agnostic SDK** | Works with LangChain, CrewAI, or any custom Python agent via `@observe` decorator |
| **Local-First** | No cloud. No account. Runs entirely on your machine |
| **Free & Open Source** | MIT license |

---

## Quick Start

```bash
# Clone and start the platform
git clone https://github.com/vexorlabs/beacon.git
cd beacon
make install          # Create venv, install all deps
make dev              # Start backend (7474) + frontend (5173)
```

Open **http://localhost:5173** to see the UI.

```python
# Instrument your agent (one line)
from beacon_sdk import observe

@observe
def run_agent(query: str):
    # your agent code here
    ...
```

---

## Architecture

Beacon has three components:

```
beacon-sdk (Python)   →   beacon-backend (FastAPI)   →   beacon-ui (React)
   Captures spans          Stores + serves traces         Visualizes everything
```

See [`docs/architecture.md`](docs/architecture.md) for the full system design.

---

## Comparison

| | Beacon | LangSmith | Braintrust | Helicone |
|---|---|---|---|---|
| LLM call tracing | ✅ | ✅ | ✅ | ✅ |
| Tool use tracing | ✅ | ✅ | ✅ | ❌ |
| Browser action tracing | ✅ | ❌ | ❌ | ❌ |
| File/shell tracing | ✅ | ❌ | ❌ | ❌ |
| Interactive replay | ✅ | ❌ | ❌ | ❌ |
| Time-travel debugging | ✅ | ❌ | ❌ | ❌ |
| Local-first | ✅ | ❌ | ❌ | ❌ |
| Open source | ✅ | ❌ | ❌ | ❌ |

---

## Project Structure

```
beacon/
├── sdk/         # Python instrumentation SDK
├── backend/     # FastAPI backend (trace storage + API)
└── frontend/    # Vite + React UI
```

---

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md) for the detailed implementation plan.

- ~~**Phase 1 (Weeks 1–2):** Backend + SQLite + OTEL schema + basic SDK~~ **Done**
- ~~**Phase 2 (Weeks 3–4):** React UI + trace list + basic graph~~ **Done**
- **Phase 3 (Weeks 5–6):** Interactive graph + prompt editor + replay
- **Phase 4 (Weeks 7–8):** Computer-use tracing + polish + launch

---

## Contributing

Beacon is in active development. Contribution guidelines are coming soon — see [`docs/roadmap.md`](docs/roadmap.md) for current progress.

---

## License

MIT — see [LICENSE](LICENSE).
