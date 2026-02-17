# Implementation Roadmap

8-week plan to MVP v1.0. Each phase has a clear goal, specific tasks, and a done condition.

**North Star:** Every decision should answer — "Does this make it easier and faster for a developer to debug their AI agent?"

---

## Phase 1: Foundation (Weeks 1–2)

**Goal:** Working data pipeline. An agent runs, spans are captured, stored in SQLite. No UI yet.

### Tasks

**Backend**
- [ ] Initialize `backend/` with `pyproject.toml`, FastAPI, SQLAlchemy, pydantic-settings
- [ ] Implement `database.py` (SQLite engine, session factory, `init_db()`)
- [ ] Implement `models.py` (Trace, Span, ReplayRun ORM models)
- [ ] Implement `schemas.py` (Pydantic v2 schemas for all API shapes)
- [ ] Implement `POST /v1/spans` endpoint (span ingestion + trace upsert)
- [ ] Implement `GET /health` endpoint
- [ ] Write pytest tests for span ingestion (using in-memory SQLite)

**SDK**
- [ ] Initialize `sdk/` with `pyproject.toml`
- [ ] Implement `models.py` (Span dataclass, SpanType enum)
- [ ] Implement `context.py` (ContextVar-based trace context)
- [ ] Implement `tracer.py` (BeaconTracer: `start_span()`, `end_span()`)
- [ ] Implement `exporters.py` (HttpSpanExporter with graceful failure)
- [ ] Implement `decorators.py` (`@observe` decorator, sync + async)
- [ ] Implement `__init__.py` (public API: `init()`, `observe`, `get_current_span`)

**Validation**
- [ ] Write a test script (`sdk/examples/hello_world.py`) that:
  1. Calls `beacon_sdk.init()`
  2. Decorates a simple function with `@observe`
  3. Runs the function
  4. Confirms a span appears in the SQLite database

### Done Condition
Running `python sdk/examples/hello_world.py` with the backend running produces a span in `~/.beacon/traces.db`.

---

## Phase 2: Basic Visualization (Weeks 3–4)

**Goal:** Traces appear in a UI. Developer can see a list of traces and a basic graph.

### Tasks

**Backend**
- [ ] Implement `GET /v1/traces` (trace list with pagination)
- [ ] Implement `GET /v1/traces/{trace_id}` (trace detail with all spans)
- [ ] Implement `GET /v1/traces/{trace_id}/graph` (React Flow nodes + edges)
- [ ] Implement `GET /v1/spans/{span_id}` (single span detail)
- [ ] Implement WebSocket endpoint `WS /ws/live` with `ConnectionManager`
- [ ] Broadcast new spans to WebSocket clients in `POST /v1/spans` handler

**SDK: LangChain Integration**
- [ ] Implement `integrations/langchain.py` (`BeaconCallbackHandler`)
- [ ] Implement all LangChain callbacks: chain, llm, tool, agent events
- [ ] Write example: `sdk/examples/langchain_agent.py`

**Frontend**
- [ ] Initialize `frontend/` with Vite, React 18, TypeScript
- [ ] Configure Tailwind CSS + shadcn/ui (`init`)
- [ ] Add required shadcn components: Button, Badge, Separator, ScrollArea
- [ ] Implement `lib/types.ts` (all TypeScript interfaces)
- [ ] Implement `lib/api.ts` (getTraces, getTrace, getTraceGraph, getSpan)
- [ ] Implement `lib/ws.ts` (WebSocket client with auto-reconnect)
- [ ] Implement `store/trace.ts` (Zustand store)
- [ ] Implement `TraceList` component (list view)
- [ ] Implement `TraceGraph` component (React Flow graph, basic layout with dagre)
- [ ] Implement `SpanNode` custom React Flow node (color by span_type)
- [ ] Implement `App.tsx` with the three-panel layout (TraceList + TraceGraph + placeholder SpanDetail)

### Done Condition
Run a LangChain agent → open `http://localhost:5173` → see the trace appear in the list → click it → see a graph of spans with colored nodes.

---

## Phase 3: Interactive Debugging (Weeks 5–6)

**Goal:** The killer features. Click nodes, edit prompts, replay steps, time-travel.

### Tasks

**Backend**
- [ ] Implement `POST /v1/replay` (re-run an LLM call with modified prompt)
- [ ] Implement `replay_service.py` (call OpenAI/Anthropic API, build diff)
- [ ] Store replay result in `replay_runs` table

**Frontend: SpanDetail Panel**
- [ ] Implement `SpanDetail/index.tsx` (right panel, dispatch to sub-components)
- [ ] Implement `LlmCallDetail.tsx` (show prompt, completion, tokens, cost, model)
- [ ] Implement `ToolUseDetail.tsx` (show tool name, input JSON, output JSON)
- [ ] Implement `BrowserDetail.tsx` (show action, URL, selector, screenshot)
- [ ] Implement generic attributes view for other span types
- [ ] Wire: clicking a node in `TraceGraph` sets `store.selectedSpanId` → `SpanDetail` shows

**Frontend: Prompt Editor + Replay**
- [ ] Add `@monaco-editor/react` dependency
- [ ] Implement `PromptEditor.tsx` with Monaco Editor (json mode)
- [ ] Implement `ReplayPanel.tsx` (Replay button + diff view)
- [ ] Wire replay: edit prompt → POST /v1/replay → show diff in `ReplayPanel`

**Frontend: Time-Travel**
- [ ] Implement `TimeTravel/index.tsx` (horizontal slider + step counter)
- [ ] Add keyboard support: Left/Right arrows to step through
- [ ] Wire: slider moves → `store.setTimeTravelIndex(n)` → `TraceGraph` grays out future nodes

### Done Condition
1. Click an LLM call node → see prompt + completion in right panel
2. Edit the prompt → click Replay → see new completion + diff
3. Use the time-travel slider to step through the execution

---

## Phase 4: Computer-Use + Polish (Weeks 7–8)

**Goal:** Playwright tracing, docs, and open-source launch.

### Tasks

**SDK: Computer-Use Instrumentation**
- [ ] Implement `integrations/playwright.py` (monkey-patch Page methods)
- [ ] Implement OpenAI auto-patch (`integrations/openai.py`)
- [ ] Implement Anthropic auto-patch (`integrations/anthropic.py`)
- [ ] Implement `os`/`subprocess` auto-patch for file/shell tracing
- [ ] Write example: `sdk/examples/browser_agent.py` (Playwright agent end-to-end)

**Frontend: Polish**
- [ ] Add loading skeletons to TraceList and TraceGraph
- [ ] Add error states (backend unreachable banner)
- [ ] Add screenshot display in `BrowserDetail`
- [ ] Add cost + token summary bar at top of TraceGraph
- [ ] Add trace search/filter in TraceList (by status, date range)
- [ ] Make the three panels resizable (drag to resize)

**Docs + Launch**
- [ ] Write `sdk/README.md` (quickstart in 5 minutes)
- [ ] Write `docs/contributing.md` (development setup, PR guidelines)
- [ ] Create `sdk/examples/` folder with 3 working examples
- [ ] Record a 2-minute demo video (screen recording)
- [ ] Publish `beacon-sdk` to PyPI
- [ ] Push everything to GitHub with a proper Release tag
- [ ] Post on Hacker News (Show HN), Reddit (r/LangChain, r/AI_Agents), Twitter

### Done Condition
A developer can `pip install beacon-sdk`, follow the README, and have a working trace in the UI within 5 minutes.

---

## Post-MVP Backlog (Do Not Build Yet)

These are explicitly out of scope for v1.0. Add them after the launch:

| Feature | Why Deferred |
|---------|-------------|
| Authentication / user accounts | Not needed for local-first tool |
| PostgreSQL support | SQLite is sufficient for local dev |
| LLM evaluation / scoring | Different product surface; build after core debugging is solid |
| Production monitoring | Cloud product — Phase 2 of the business |
| CrewAI / AutoGen integrations | High value but needs community feedback on priority |
| Export traces (JSON, CSV) | Nice to have |
| AI-powered root cause analysis | Phase 3 feature |
| VS Code extension | Post-launch based on community demand |

---

## Definition of Done (Per Task)

A task is done when:
1. The feature works as described
2. Tests pass (`pytest` for backend, `npm run typecheck` + `npm run lint` for frontend)
3. No debug `print()` / `console.log()` statements left in the code
4. The relevant doc file is updated if the implementation diverged from the design
