# Backend Design

The `beacon-backend` is a FastAPI service that receives spans from the SDK, stores them in SQLite, and serves them to the UI via REST and WebSocket.

**Location in repo:** `backend/`
**Runs on:** `http://localhost:7474`

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI app instance + router registration + lifespan
│   ├── config.py          # Settings via pydantic-settings
│   ├── database.py        # SQLAlchemy engine, session factory, Base
│   ├── models.py          # SQLAlchemy ORM models (Trace, Span, ReplayRun)
│   ├── schemas.py         # Pydantic v2 request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── spans.py       # POST /v1/spans, GET /v1/spans/{span_id}
│   │   ├── traces.py      # GET /v1/traces, GET /v1/traces/{id}, GET /v1/traces/{id}/graph
│   │   └── replay.py      # POST /v1/replay
│   ├── ws/
│   │   ├── __init__.py
│   │   └── manager.py     # WebSocket connection manager + broadcaster
│   └── services/
│       ├── __init__.py
│       ├── span_service.py    # Business logic for span ingestion
│       ├── trace_service.py   # Business logic for trace queries
│       └── replay_service.py  # Business logic for LLM replay
├── tests/
│   ├── conftest.py        # pytest fixtures (test db, test client)
│   ├── test_spans.py
│   ├── test_traces.py
│   └── test_replay.py
├── pyproject.toml
└── .env.example
```

---

## `main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import spans, traces, replay
from app.ws.manager import ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # Create tables if they don't exist
    yield

app = FastAPI(
    title="Beacon Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: Allow the Vite dev server (localhost:5173) and any localhost port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:7474"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spans.router, prefix="/v1")
app.include_router(traces.router, prefix="/v1")
app.include_router(replay.router, prefix="/v1")
app.include_router(ws_router)

@app.get("/health")
def health():
    from app.config import settings
    return {"status": "ok", "version": "0.1.0", "db_path": str(settings.db_path)}
```

---

## `config.py`

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_path: Path = Path.home() / ".beacon" / "traces.db"
    backend_port: int = 7474
    log_level: str = "INFO"

    class Config:
        env_prefix = "BEACON_"
        env_file = ".env"

settings = Settings()
```

The database lives at `~/.beacon/traces.db` by default. This keeps it out of the project directory and persists across repo clones.

---

## `database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

settings.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def init_db():
    from app import models  # noqa: import triggers model registration
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## `models.py`

SQLAlchemy ORM models. See `docs/data-model.md` for the full schema.

```python
from sqlalchemy import Column, Text, Float, Integer, ForeignKey
from app.database import Base

class Trace(Base):
    __tablename__ = "traces"
    trace_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float)
    span_count = Column(Integer, default=0)
    status = Column(Text, default="unset")
    tags = Column(Text, default="{}")
    total_cost_usd = Column(Float, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(Float, nullable=False)

class Span(Base):
    __tablename__ = "spans"
    span_id = Column(Text, primary_key=True)
    trace_id = Column(Text, ForeignKey("traces.trace_id", ondelete="CASCADE"), nullable=False)
    parent_span_id = Column(Text)
    span_type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    status = Column(Text, default="unset")
    error_message = Column(Text)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float)
    attributes = Column(Text, default="{}")
    created_at = Column(Float, nullable=False)

class ReplayRun(Base):
    __tablename__ = "replay_runs"
    replay_id = Column(Text, primary_key=True)
    original_span_id = Column(Text, ForeignKey("spans.span_id"), nullable=False)
    trace_id = Column(Text, ForeignKey("traces.trace_id"), nullable=False)
    modified_input = Column(Text, nullable=False)
    new_output = Column(Text, nullable=False)
    diff = Column(Text, nullable=False)
    created_at = Column(Float, nullable=False)
```

---

## `schemas.py`

Pydantic v2 schemas for all API request/response shapes. See `docs/api-contracts.md` for the full API spec.

Key principle: **schemas are the single source of truth for the API shape.** The frontend's `types.ts` must mirror these exactly.

---

## Routers

### `routers/spans.py`

Handles span ingestion (`POST /v1/spans`) and span detail (`GET /v1/spans/{span_id}`).

On span ingestion:
1. Validate the incoming spans with Pydantic
2. Upsert the parent `Trace` row (create if new, update `end_time` / `span_count` if existing)
3. Insert the `Span` rows
4. Update `Trace.total_cost_usd` and `Trace.total_tokens` if the span has LLM attributes
5. Broadcast each span to connected WebSocket clients via `ws_manager.broadcast()`

### `routers/traces.py`

Handles trace list (`GET /v1/traces`) and trace detail + graph endpoints.

The `/graph` endpoint transforms the flat span list into React Flow nodes and edges. Node positions are all `{x: 0, y: 0}` — layout is done client-side.

### `routers/replay.py`

Handles `POST /v1/replay`.

1. Fetch the original span
2. Validate it's a `llm_call` span
3. Parse the original `llm.prompt` and `llm.provider` / `llm.model` from attributes
4. Merge `modified_attributes` over original attributes
5. Call the appropriate LLM API (OpenAI or Anthropic) using the developer's API key from environment
6. Build a diff of old vs. new completion
7. Store the replay result in `replay_runs`
8. Return the result

**Security note:** The replay endpoint uses `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` from the server's environment. It does not accept API keys from the HTTP request.

---

## WebSocket Manager

```
ws/manager.py
```

Manages active WebSocket connections. Uses a simple in-memory set.

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.trace_subscriptions: dict[str, set[WebSocket]] = {}  # trace_id → set of sockets

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.discard(ws)
        for sockets in self.trace_subscriptions.values():
            sockets.discard(ws)

    async def broadcast_span(self, span_dict: dict):
        """Broadcast to all connections watching this trace."""
        trace_id = span_dict["trace_id"]
        targets = self.trace_subscriptions.get(trace_id, set()) | self.active_connections
        for ws in list(targets):
            try:
                await ws.send_json({"event": "span_created", "span": span_dict})
            except Exception:
                self.disconnect(ws)

ws_manager = ConnectionManager()  # Singleton
```

---

## Running the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Development (with hot reload)
uvicorn app.main:app --reload --port 7474

# Production (MVP local)
uvicorn app.main:app --port 7474
```

Auto-generated API docs: `http://localhost:7474/docs`

---

## Testing

```bash
cd backend
pytest tests/ -v
```

Tests use an in-memory SQLite database via a `conftest.py` fixture that overrides the database dependency. Never use the real `~/.beacon/traces.db` in tests.

---

## Key Constraints

- **SQLite only:** Do not introduce any other database. SQLite handles concurrent reads well. Concurrent writes are serialized by SQLite automatically.
- **No authentication:** No JWT, no sessions, no API keys required. The backend trusts all local connections.
- **No external services except LLM replay:** The backend only calls external APIs during `/v1/replay`, and only uses keys from the server environment.
- **Port 7474:** Do not change the default port. It is used throughout the codebase and documentation.
