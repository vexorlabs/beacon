# Architecture Overview

This document describes Beacon's system architecture. It is the authoritative reference for understanding how the three main components fit together.

---

## System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                  Developer's Application                  │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  LangChain  │  │   CrewAI    │  │  Custom Agent   │  │
│  │    Agent    │  │    Agent    │  │  (any Python)   │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │           │
│         └────────────────┴───────────────────┘           │
│                          │                               │
│              ┌───────────▼──────────┐                   │
│              │    beacon-sdk        │                   │
│              │  (auto-instrument)   │                   │
│              │                      │                   │
│              │  @observe decorator  │                   │
│              │  monkey-patching     │                   │
│              │  LangChain handler   │                   │
│              └───────────┬──────────┘                   │
└──────────────────────────┼──────────────────────────────┘
                           │
                           │  HTTP POST /v1/spans
                           │  (OTEL span format, JSON)
                           │
              ┌────────────▼───────────┐
              │    beacon-backend      │
              │    (FastAPI)           │
              │                        │
              │  ┌──────────────────┐  │
              │  │    SQLite DB     │  │
              │  │  (traces.db)     │  │
              │  └──────────────────┘  │
              │                        │
              │  REST API  WebSocket   │
              └────────────┬───────────┘
                           │
                           │  REST + WebSocket
                           │  (localhost:7474)
                           │
              ┌────────────▼───────────┐
              │    beacon-ui           │
              │    (React + Vite)      │
              │                        │
              │  TraceList   (left)    │
              │  TraceGraph  (center)  │
              │  SpanDetail  (right)   │
              │  TimeTravel  (bottom)  │
              └────────────────────────┘
```

---

## Component Responsibilities

### 1. beacon-sdk (Python)

**What it does:** Intercepts agent actions and converts them into OTEL spans, then sends those spans to the backend.

**Key responsibilities:**
- Provide `@observe` decorator for manual instrumentation
- Monkey-patch `openai`, `anthropic`, `playwright`, `subprocess`, `os.open` at import time
- Provide `BeaconCallbackHandler` for LangChain auto-instrumentation
- Manage trace context (trace ID, parent span ID) across async boundaries
- Batch and export spans to the backend HTTP endpoint

**Does NOT:**
- Store any data permanently
- Know anything about the UI
- Handle authentication or network security

**Lives in:** `sdk/`

---

### 2. beacon-backend (FastAPI)

**What it does:** Receives spans from the SDK, stores them in SQLite, serves them to the UI via REST and WebSocket.

**Key responsibilities:**
- Accept OTEL span payloads via `POST /v1/spans`
- Store spans and traces in SQLite
- Serve trace list and trace detail via REST API
- Push new spans to the UI in real-time via WebSocket
- Execute LLM replay requests (`POST /replay`) for time-travel debugging

**Does NOT:**
- Instrument any agent code
- Render any UI
- Communicate with external services (except for replay: calls OpenAI/Anthropic API)

**Lives in:** `backend/`

---

### 3. beacon-ui (React)

**What it does:** Provides the interactive debugging interface. Fetches trace data from the backend and renders it as an interactive graph.

**Key responsibilities:**
- Display list of all captured traces
- Render a trace as an interactive React Flow graph
- Show span detail in a side panel when a node is clicked
- Allow prompt editing via Monaco Editor and trigger replays
- Stream new spans in real-time via WebSocket
- Provide a time-travel timeline scrubber

**Does NOT:**
- Communicate with the SDK directly
- Store any persistent data
- Execute any agent code

**Lives in:** `frontend/`

---

## Data Flow: Happy Path

```
1. Developer starts agent:
   python my_agent.py

2. SDK auto-patches libraries on import.
   Every intercepted call creates a Span object.

3. SDK exports Span to backend:
   POST http://localhost:7474/v1/spans
   Content-Type: application/json
   { "span_id": "...", "trace_id": "...", "span_type": "llm_call", ... }

4. Backend writes span to SQLite:
   INSERT INTO spans (span_id, trace_id, ...) VALUES (...)

5. Backend broadcasts span to UI via WebSocket:
   ws://localhost:7474/ws/live
   → { "event": "span_created", "span": { ... } }

6. UI receives WebSocket event, adds node to React Flow graph.

7. Developer sees the graph update in real-time.
```

## Data Flow: Time-Travel Replay

```
1. Developer clicks an LLM call node in the graph.

2. UI fetches full span detail:
   GET /spans/{span_id}
   → Returns span with full prompt + completion

3. Developer edits the prompt in Monaco Editor.

4. Developer clicks "Replay":
   POST /replay
   { "span_id": "...", "new_input": { "prompt": "..." } }

5. Backend re-executes the LLM call using the original model/params
   but with the new prompt.

6. Backend creates a new "replay" span linked to the original.

7. Backend returns the new completion + diff from old completion.

8. UI shows diff view: old completion vs. new completion.
```

---

## Design Principles

### Local-First
Everything runs on the developer's machine. No cloud account, no network call outside localhost. The backend talks to external LLM APIs only during replay, using the developer's own API keys from their environment.

### OTEL-Conformant
All spans follow the [OpenTelemetry specification](https://opentelemetry.io/docs/specs/otel/). The backend accepts standard OTEL JSON export format. This ensures future interoperability with the OTEL ecosystem.

### Schema-First API
The backend defines all API contracts with Pydantic models. The frontend mirrors these as TypeScript interfaces in `frontend/src/lib/types.ts`. The two must stay in sync.

### Simple Over Clever
For the MVP, prefer the simplest solution that works. No Celery, no Redis, no message queues. SQLite handles concurrency fine for local development. FastAPI WebSockets handle real-time without an external broker.

---

## Port Assignments

| Service | Port | Notes |
|---------|------|-------|
| beacon-backend | 7474 | Chosen to avoid conflicts with common dev ports |
| beacon-ui | 5173 | Vite default |

---

## File Organization Rules

- All backend code lives in `backend/app/`
- All SDK code lives in `sdk/beacon_sdk/`
- All frontend source lives in `frontend/src/`
- Shared types between backend and frontend are defined in backend Pydantic schemas (source of truth) and manually mirrored in `frontend/src/lib/types.ts`
- No code in the root of the repo (only config files and docs)
