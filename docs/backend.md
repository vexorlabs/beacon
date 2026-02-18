# Backend Design

`beacon-backend` is a FastAPI service that stores spans/traces in SQLite, serves debugger APIs, and streams live events over WebSocket.

Location: `backend/`
Runs on: `http://localhost:7474`

---

## Directory Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── spans.py
│   │   ├── traces.py
│   │   ├── replay.py
│   │   ├── settings.py
│   │   ├── playground.py
│   │   ├── demo.py
│   │   ├── stats.py
│   │   └── search.py
│   ├── services/
│   │   ├── span_service.py
│   │   ├── trace_service.py
│   │   ├── replay_service.py
│   │   ├── settings_service.py
│   │   ├── llm_client.py
│   │   ├── playground_service.py
│   │   ├── demo_service.py
│   │   └── search_service.py
│   └── ws/
│       └── manager.py
├── tests/
├── pyproject.toml
└── .env.example
```

---

## App Bootstrap (`main.py`)

Responsibilities:
- initialize DB on startup (`lifespan -> init_db()`)
- register CORS
- include all REST routers under `/v1`
- mount WebSocket router (`/ws/live`)
- expose `/health`

Routers included:
- `spans`, `traces`, `replay`, `settings`, `playground`, `demo`, `stats`, `search`

---

## Configuration (`config.py`)

Settings are loaded via `pydantic-settings` (`BEACON_` prefix):
- `db_path` (default `~/.beacon/traces.db`)
- `backend_port` (default `7474`)
- `log_level` (default `INFO`)

---

## Database (`database.py`, `models.py`)

Engine:
- SQLite with `check_same_thread=False`
- foreign keys explicitly enabled (`PRAGMA foreign_keys=ON`)

ORM tables:
- `traces`
- `spans`
- `replay_runs`

Cascade behavior:
- deleting a trace cascades to spans and replay rows

---

## Router Surface

### Spans
- `POST /v1/spans`
- `GET /v1/spans/{span_id}`

`POST /v1/spans`:
- validates payload
- upserts trace summary + span rows
- broadcasts each persisted span over WebSocket

### Traces
- `GET /v1/traces`
- `GET /v1/traces/{trace_id}`
- `GET /v1/traces/{trace_id}/graph`
- `DELETE /v1/traces/{trace_id}`
- `DELETE /v1/traces` (batch by ids or `older_than`)

### Replay
- `POST /v1/replay`

Behavior:
- accepts only `llm_call` spans
- merges `modified_attributes` onto stored span attributes
- replays upstream LLM request and stores output/diff in `replay_runs`

### Settings
- `GET /v1/settings/api-keys`
- `PUT /v1/settings/api-keys`
- `DELETE /v1/settings/api-keys/{provider}`

Keys are persisted locally in `~/.beacon/config.json` (mode `0600`).

### Playground
- `POST /v1/playground/chat`
- `POST /v1/playground/compare`

Creates real traces/spans so playground activity appears in Traces debugger.

### Demo
- `GET /v1/demo/scenarios`
- `POST /v1/demo/run`

`run` starts a background task and immediately returns `trace_id`.

### Search
- `GET /v1/search?q=...`

SQLite `LIKE` search across:
- span name
- span attributes text
- trace name

### Stats
- `GET /v1/stats`

Returns DB file size + trace/span counts + oldest trace timestamp.

---

## Service Layer

- `span_service.py`: ingestion/upsert logic, span response mapping
- `trace_service.py`: list/detail/graph/delete/stats logic
- `replay_service.py`: replay execution + persistence
- `settings_service.py`: local API-key persistence/masking
- `llm_client.py`: OpenAI/Anthropic HTTP calls + model/provider mapping + cost estimation
- `playground_service.py`: chat/compare orchestration + live span broadcasting
- `demo_service.py`: scenario catalog + async demo loop with tool-calling simulation
- `search_service.py`: query matching + context snippets

---

## WebSocket (`ws/manager.py`)

Endpoint: `WS /ws/live`

Event types:
- `span_created`
- `trace_created`
- `span_updated` (supported by manager API)

Subscription model:
- client starts in global stream (`active_connections`)
- `subscribe_trace` moves client to trace-specific set
- `unsubscribe_trace` returns client to global stream

---

## Error Semantics

Common patterns:
- `400`: invalid business request (unsupported provider, missing API key, etc.)
- `404`: entity not found
- `422`: request validation errors
- `502`: upstream LLM/API failures

Payload shape:

```json
{ "detail": "..." }
```

---

## Run + Test

```bash
# from repo root
make install
make dev-backend

# tests
make test
# or
backend/.venv/bin/pytest backend/tests -v
```

OpenAPI docs: `http://localhost:7474/docs`

---

## Constraints

- SQLite only for current architecture
- no auth layer by design (local-first developer workflow)
- no external infra (queues/brokers) required
- fixed default backend port: `7474`
