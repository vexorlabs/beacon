# Architecture Overview

Beacon has four local components:

1. `beacon-sdk` (Python instrumentation)
2. `beacon-sdk` JS/TS (Node.js instrumentation)
3. `beacon-backend` (FastAPI + SQLite)
4. `beacon-ui` (React + Vite)

---

## System Diagram

```text
Developer Agent (Python / JS / TS)
  ├─ manual spans via @observe / observe()
  ├─ tracer API
  └─ auto-patching (openai/anthropic/gemini/crewai/autogen/llamaindex/ollama/playwright/subprocess/file ops)
            |
            | POST /v1/spans  (or POST /v1/otlp/traces for OTEL-instrumented apps)
            v
beacon-backend (FastAPI, port 7474)
  ├─ SQLite persistence (~/.beacon/traces.db)
  ├─ REST API (/v1/*)
  ├─ AI analysis endpoints (/v1/analysis/*)
  └─ WebSocket stream (/ws/live)
            |
            | REST + WS
            v
beacon-ui (React, port 5173)
  ├─ Dashboard (analytics, trends, cost forecasting)
  ├─ Traces debugger (graph + timeline + detail + time-travel + AI analysis)
  ├─ Playground (chat + model compare + A/B prompt testing)
  └─ Settings (API keys + data management)
```

---

## Component Responsibilities

### 1. SDK (`sdk/`)

What it does:
- creates spans via `@observe` and `BeaconTracer`
- tracks trace/span context with `ContextVar`
- exports spans to backend (`/v1/spans`) using sync or async batch exporter
- integrates with OpenAI, Anthropic, Google Gemini, CrewAI, AutoGen, LlamaIndex, Ollama, Playwright, subprocess, and LangChain callback handler
- JS/TS SDK (`sdk-js/`) provides equivalent tracing for Node.js with OpenAI, Anthropic, and Vercel AI SDK integrations

What it does not do:
- persistent storage
- UI rendering
- backend querying

### 2. Backend (`backend/`)

What it does:
- persists traces/spans/replay runs in SQLite
- serves trace APIs (`/v1/traces`, `/v1/spans`, `/v1/search`, `/v1/stats`)
- serves replay API (`/v1/replay`)
- serves settings/playground/demo APIs (`/v1/settings/*`, `/v1/playground/*`, `/v1/demo/*`)
- streams `span_created` and `trace_created` events via WebSocket

What it does not do:
- SDK-side instrumentation
- UI rendering
- auth/session management (intentionally no-auth for local-first MVP)

### 3. Frontend (`frontend/`)

What it does:
- route-driven UI with React Router
- renders trace DAG with React Flow
- displays span detail and replay UI
- drives time-travel + search/filter + trace deletion
- provides Playground for live model calls
- manages API keys and data stats in Settings

What it does not do:
- direct SDK communication
- persistent storage (beyond runtime client state)

---

## Data Flow: Standard Trace Ingestion

```text
1. Agent code executes instrumented function/call.
2. SDK creates a span and ends it with status/attributes.
3. SDK exporter POSTs to /v1/spans.
4. Backend upserts trace summary + span rows in SQLite.
5. Backend broadcasts span_created over /ws/live.
6. Frontend updates trace list/graph state in real time.
```

---

## Data Flow: Replay

```text
1. User selects an llm_call span in SpanDetail.
2. User edits prompt JSON in PromptEditor.
3. Frontend POSTs /v1/replay with { span_id, modified_attributes }.
4. Backend replays with provider/model from original span attributes.
5. Backend stores replay result in replay_runs.
6. Backend returns new output + diff.
7. Frontend renders old/new completion comparison.
```

---

## Data Flow: Playground + Demo

```text
Playground:
  Frontend -> /v1/playground/chat or /v1/playground/compare
  Backend -> calls upstream LLM APIs -> emits spans/trace events -> UI updates

Demo:
  Frontend -> /v1/demo/run
  Backend -> starts background loop -> emits spans incrementally -> UI updates
```

---

## Design Principles

### Local-First
- primary data path is localhost only
- SQLite database on developer machine
- no required cloud control plane

### OTEL-Aligned Span Shape
- canonical span fields align with OTEL-style tracing semantics
- consistent cross-layer shape: backend Pydantic schemas -> frontend TypeScript types

### Simple, Observable Runtime
- FastAPI + SQLite + WebSocket, no queue/broker dependency
- direct APIs for inspect/debug workflows

---

## Ports

| Service | Port |
|---|---|
| backend | `7474` |
| frontend | `5173` |

---

## Source of Truth

- API contracts: `docs/api-contracts.md`
- Data model: `docs/data-model.md`
- Backend behavior: `docs/backend.md`
- Frontend behavior: `docs/frontend.md`
- SDK behavior: `docs/sdk.md`
