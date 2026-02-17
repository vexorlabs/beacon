# Beacon — AI Agent Instructions

This file is the primary context document for AI coding assistants (Claude, Codex, etc.) working on this codebase. Read this before doing anything else.

---

## What Is Beacon?

Beacon is an **open-source, local-first observability and debugging platform for AI agents**. Think "Chrome DevTools for AI Agents."

The core problem it solves: debugging AI agents is a nightmare because existing tools only trace LLM calls, missing the full picture of what the agent does (browser clicks, file writes, shell commands). Beacon provides a **unified trace** that captures both LLM reasoning and computer-use actions in a single interactive view.

**Key differentiators:**
- Unified trace: LLM calls + browser actions + file ops + shell commands in one graph
- Time-travel debugging: click any node, inspect state, edit the prompt, replay that single step
- Local-first: zero cloud dependency, developer's machine only (for now)
- Framework-agnostic: works with LangChain, CrewAI, custom agents via monkey-patching

Full project vision: `docs/vision.md`

---

## Repo Structure

```
beacon/
├── CLAUDE.md                  # You are here
├── README.md                  # Public-facing project description
├── LICENSE
│
├── docs/                      # Architecture and design documentation
│   ├── architecture.md        # System design overview (start here for big-picture)
│   ├── data-model.md          # OTEL trace schema + SQLite database schema
│   ├── api-contracts.md       # REST API + WebSocket API specifications
│   ├── sdk.md                 # Python SDK design and instrumentation patterns
│   ├── backend.md             # FastAPI backend design
│   ├── frontend.md            # React frontend design
│   ├── roadmap.md             # Phased implementation plan (8 weeks to MVP)
│   └── conventions.md        # Coding conventions, patterns, naming rules
│
├── sdk/                       # Python instrumentation SDK (pip package)
│   ├── beacon_sdk/
│   │   ├── __init__.py
│   │   ├── tracer.py          # Core tracer + span management
│   │   ├── decorators.py      # @observe, @trace_llm decorators
│   │   ├── context.py         # Context propagation
│   │   ├── exporters.py       # Sends spans to backend
│   │   └── integrations/
│   │       ├── langchain.py   # LangChain callback handler
│   │       ├── openai.py      # OpenAI SDK monkey-patch
│   │       ├── anthropic.py   # Anthropic SDK monkey-patch
│   │       └── playwright.py  # Playwright monkey-patch
│   ├── tests/
│   └── pyproject.toml
│
├── backend/                   # FastAPI backend service
│   ├── app/
│   │   ├── main.py            # FastAPI app + router registration
│   │   ├── config.py          # Settings (env vars, defaults)
│   │   ├── database.py        # SQLite connection + migrations
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── traces.py      # GET /traces, GET /traces/{id}
│   │   │   ├── spans.py       # GET /spans, POST /spans (OTEL ingestion)
│   │   │   └── replay.py      # POST /replay (time-travel)
│   │   └── ws/
│   │       └── live.py        # WebSocket for real-time span streaming
│   ├── tests/
│   └── pyproject.toml
│
└── frontend/                  # Vite + React UI
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── components/
    │   │   ├── ui/            # shadcn/ui copy-pasted components (DO NOT edit)
    │   │   ├── TraceList/     # Left panel: list of all traces
    │   │   ├── TraceGraph/    # Center: React Flow graph visualizer
    │   │   ├── SpanDetail/    # Right panel: span metadata + prompt editor
    │   │   └── TimeTravel/    # Bottom: timeline scrubber
    │   ├── lib/
    │   │   ├── api.ts         # API client (fetch wrappers)
    │   │   ├── ws.ts          # WebSocket client
    │   │   └── types.ts       # Shared TypeScript types (mirrors backend schemas)
    │   └── store/
    │       └── trace.ts       # Zustand store for selected trace state
    ├── package.json
    └── vite.config.ts
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| SDK | Python 3.11+ | Matches the AI/ML ecosystem |
| Backend | FastAPI + Uvicorn | Async-native, fast, auto-docs |
| Database | SQLite (via SQLAlchemy) | Zero-config, local-first |
| Real-time | WebSockets (FastAPI native) | Live span streaming to UI |
| Frontend | Vite + React 18 + TypeScript | Fast dev server, type safety |
| Graph viz | React Flow (`@xyflow/react`) | React-native, interactive graphs |
| Code editor | Monaco Editor (`@monaco-editor/react`) | VS Code quality in the browser |
| UI components | shadcn/ui + Tailwind CSS | Copy-paste, no npm bloat |
| State | Zustand | Simpler than Redux |
| Trace standard | OpenTelemetry (OTEL) | Industry standard, future-proof |

---

## Core Concepts

### Span
A single unit of work in a trace. Every action the agent takes generates a span. Spans have:
- A unique `span_id`
- A `trace_id` (groups all spans in one agent run)
- A `parent_span_id` (forms the execution tree)
- A `span_type` (what kind of action: llm_call, tool_use, browser_action, etc.)
- A `start_time` and `end_time`
- Arbitrary `attributes` (key-value metadata specific to the span type)

### Trace
A complete agent execution run. A collection of spans with the same `trace_id`, forming a directed acyclic graph (DAG) that represents everything the agent did.

### Span Types
```
llm_call         — An LLM API call (prompt in, completion out)
tool_use         — A tool invocation (name, input, output)
agent_step       — A logical step in the agent loop
browser_action   — A Playwright/Selenium action (click, navigate, type)
file_operation   — A file read/write/delete
shell_command    — A subprocess/shell invocation
custom           — Developer-defined custom span
```

Full schema: `docs/data-model.md`

---

## Development Conventions

Full conventions: `docs/conventions.md`

**Quick rules:**
- Python: Black formatter, type hints everywhere, no implicit `Any`
- TypeScript: strict mode, no `any`, interfaces over types for object shapes
- Backend: one router file per resource, Pydantic schemas for all I/O
- Frontend: one folder per component (e.g., `TraceGraph/index.tsx` + `TraceGraph.types.ts`)
- Tests: pytest for backend, Vitest for frontend
- Never commit `.env` files, API keys, or credentials
- Never install npm packages for UI components — use shadcn/ui copy-paste instead

---

## Key Decisions (Do Not Revisit Without Strong Reason)

These are locked-in architectural choices. Do not change them in code without updating this file and `docs/architecture.md`:

1. **SQLite only (for now):** Do not introduce PostgreSQL or any other database. SQLite is intentional for local-first UX.
2. **No authentication:** MVP has no auth. Do not add login screens, JWT, or sessions.
3. **OTEL span format:** All trace data must conform to the OTEL spec. Do not invent a custom format.
4. **React Flow for graphs:** Do not use D3.js directly. React Flow is the graph renderer.
5. **Monaco for code editing:** Do not use CodeMirror or textarea for prompt editing.
6. **Zustand for state:** Do not introduce Redux or Context API for global state.
7. **shadcn/ui components:** Copy components from shadcn, do not `npm install` component libraries.

---

## How the Data Flows

```
Agent code runs
    → SDK intercepts calls (monkey-patch / decorator)
    → SDK creates OTEL spans
    → SDK exports spans to backend via HTTP POST /v1/spans
    → Backend stores spans in SQLite
    → Backend pushes span to connected UI via WebSocket
    → UI updates trace graph in real-time
    → Developer clicks a span node
    → UI fetches span details from GET /spans/{span_id}
    → Developer edits prompt, clicks "Replay"
    → UI posts to POST /replay with modified span input
    → Backend re-executes the LLM call with new prompt
    → Backend returns new completion + diff
```

---

## Where to Start When Working on a Feature

1. Check `docs/roadmap.md` for the current phase and priorities
2. Read the relevant design doc (`docs/backend.md`, `docs/frontend.md`, `docs/sdk.md`)
3. Check `docs/api-contracts.md` if your feature touches the API boundary
4. Check `docs/data-model.md` if your feature touches the database
5. Follow `docs/conventions.md` for code style

---

## Running the Project (Once Set Up)

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 7474

# Frontend
cd frontend
npm run dev   # runs on http://localhost:5173

# SDK (development)
cd sdk
pip install -e ".[dev]"
```

Default backend port: **7474** (to avoid conflicts with common dev ports)
Default frontend port: **5173** (Vite default)

---

## File Naming Conventions

```
backend/app/routers/traces.py      # snake_case for Python
frontend/src/components/TraceGraph/index.tsx  # PascalCase for React components
frontend/src/lib/api.ts            # camelCase for TS utilities
docs/api-contracts.md              # kebab-case for docs
```
