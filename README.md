# Beacon

**Beacon is an open-source, local-first debugger for AI agents.**

Beacon gives you one unified trace for what your agent *thought* and what it *did*:
- LLM calls (prompt, completion, tokens, cost)
- tool calls
- browser actions
- file operations
- shell commands

You can inspect spans live, replay LLM calls with edited prompts, and step through runs with time-travel controls.

> **Status:** Active development. Current codebase includes Dashboard, Traces debugger, Playground (chat + compare), Settings (API keys + trace data management), and demo agent scenarios.

---

## Why Beacon

Most agent tooling stops at LLM I/O. Beacon focuses on full execution debugging:
- **Unified graph:** LLM + tools + computer-use spans in one DAG
- **Replay:** edit prompt attributes and replay a single `llm_call`
- **Time-travel:** scrub through execution order and inspect state
- **Real-time updates:** WebSocket events stream new spans as they arrive
- **Local-first:** SQLite + FastAPI + Vite on your machine

---

## Quick Start

```bash
git clone https://github.com/vexorlabs/beacon.git
cd beacon
make install
make dev
```

Open **http://localhost:5173**.

Optional: generate sample traces (no external API keys required):

```bash
make demo
```

---

## Instrument Your Agent

```python
import beacon_sdk
from beacon_sdk import observe

beacon_sdk.init()

@observe(name="run_agent", span_type="agent_step")
def run_agent(prompt: str) -> str:
    # your agent code
    return "done"
```

Run your agent and inspect the trace in Beacon.

---

## Architecture

```text
beacon-sdk (Python) -> beacon-backend (FastAPI + SQLite) -> beacon-ui (React + Vite)
```

- **SDK (`sdk/`)** captures spans via decorators, tracer context, and integrations.
- **Backend (`backend/`)** stores/query traces and serves REST + WebSocket APIs.
- **Frontend (`frontend/`)** provides Dashboard, Traces, Playground, and Settings.

See:
- `docs/architecture.md`
- `docs/api-contracts.md`
- `docs/data-model.md`

---

## Developer Workflow

```bash
make dev           # backend + frontend
make dev-backend   # backend only (7474)
make dev-frontend  # frontend only (5173)
make test          # backend + sdk tests
make lint
make format
make stop
```

Backend docs: **http://localhost:7474/docs**

---

## Repo Layout

```text
beacon/
├── backend/    # FastAPI + SQLite
├── frontend/   # React + Vite + TypeScript
├── sdk/        # beacon-sdk Python package
└── docs/       # architecture, API, data model, conventions, roadmap
```

---

## Contributing

See `docs/contributing.md` and `docs/conventions.md`.

---

## License

MIT — see `LICENSE`.
