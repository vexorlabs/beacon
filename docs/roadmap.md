# Implementation Roadmap

Product roadmap from MVP through enterprise. Each phase has a clear goal, specific tasks, and a done condition. Phases 1–5 (MVP) are complete. Phases 6–11 define the path from open-source adoption to enterprise offering and developer workflow integration.

**North Star:** Every decision should answer — "Does this make it easier and faster for a developer to debug their AI agent?"

---

## Phase 1: Foundation (Weeks 1–2)

**Goal:** Working data pipeline. An agent runs, spans are captured, stored in SQLite. No UI yet.

### Tasks

**Backend**
- [x] Initialize `backend/` with `pyproject.toml`, FastAPI, SQLAlchemy, pydantic-settings
- [x] Implement `database.py` (SQLite engine, session factory, `init_db()`)
- [x] Implement `models.py` (Trace, Span, ReplayRun ORM models)
- [x] Implement `schemas.py` (Pydantic v2 schemas for all API shapes)
- [x] Implement `POST /v1/spans` endpoint (span ingestion + trace upsert)
- [x] Implement `GET /health` endpoint
- [x] Write pytest tests for span ingestion (using in-memory SQLite)

**SDK**
- [x] Initialize `sdk/` with `pyproject.toml`
- [x] Implement `models.py` (Span dataclass, SpanType enum)
- [x] Implement `context.py` (ContextVar-based trace context)
- [x] Implement `tracer.py` (BeaconTracer: `start_span()`, `end_span()`)
- [x] Implement `exporters.py` (HttpSpanExporter with graceful failure)
- [x] Implement `decorators.py` (`@observe` decorator, sync + async)
- [x] Implement `__init__.py` (public API: `init()`, `observe`, `get_current_span`)

**Validation**
- [x] Write a test script (`sdk/examples/hello_world.py`) that:
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
- [x] Implement `GET /v1/traces` (trace list with pagination)
- [x] Implement `GET /v1/traces/{trace_id}` (trace detail with all spans)
- [x] Implement `GET /v1/traces/{trace_id}/graph` (React Flow nodes + edges)
- [x] Implement `GET /v1/spans/{span_id}` (single span detail)
- [x] Implement WebSocket endpoint `WS /ws/live` with `ConnectionManager`
- [x] Broadcast new spans to WebSocket clients in `POST /v1/spans` handler

**SDK: LangChain Integration**
- [x] Implement `integrations/langchain.py` (`BeaconCallbackHandler`)
- [x] Implement all LangChain callbacks: chain, llm, tool, agent events
- [x] Write example: `sdk/examples/langchain_agent.py`

**Frontend**
- [x] Initialize `frontend/` with Vite, React 19, TypeScript
- [x] Configure Tailwind CSS + shadcn/ui (`init`)
- [x] Add required shadcn components: Button, Badge, Separator, ScrollArea
- [x] Implement `lib/types.ts` (all TypeScript interfaces)
- [x] Implement `lib/api.ts` (getTraces, getTrace, getTraceGraph, getSpan)
- [x] Implement `lib/ws.ts` (WebSocket client with auto-reconnect)
- [x] Implement `store/trace.ts` (Zustand store)
- [x] Implement `TraceList` component (list view)
- [x] Implement `TraceGraph` component (React Flow graph, basic layout with dagre)
- [x] Implement `SpanNode` custom React Flow node (color by span_type)
- [x] Implement `App.tsx` with the three-panel layout (TraceList + TraceGraph + placeholder SpanDetail)

### Done Condition
Run a LangChain agent → open `http://localhost:5173` → see the trace appear in the list → click it → see a graph of spans with colored nodes.

---

## Phase 3: Interactive Debugging (Weeks 5–6)

**Goal:** The killer features. Click nodes, edit prompts, replay steps, time-travel.

### Tasks

**Backend**
- [x] Implement `POST /v1/replay` (re-run an LLM call with modified prompt)
- [x] Implement `replay_service.py` (call OpenAI/Anthropic API, build diff)
- [x] Store replay result in `replay_runs` table

**Frontend: SpanDetail Panel**
- [x] Implement `SpanDetail/index.tsx` (right panel, dispatch to sub-components)
- [x] Implement `LlmCallDetail.tsx` (show prompt, completion, tokens, cost, model)
- [x] Implement `ToolUseDetail.tsx` (show tool name, input JSON, output JSON)
- [x] Implement `BrowserDetail.tsx` (show action, URL, selector, screenshot)
- [x] Implement generic attributes view for other span types
- [x] Wire: clicking a node in `TraceGraph` sets `store.selectedSpanId` → `SpanDetail` shows

**Frontend: Prompt Editor + Replay**
- [x] Add `@monaco-editor/react` dependency
- [x] Implement `PromptEditor.tsx` with Monaco Editor (json mode)
- [x] Implement `ReplayPanel.tsx` (Replay button + diff view)
- [x] Wire replay: edit prompt → POST /v1/replay → show diff in `ReplayPanel`

**Frontend: Time-Travel**
- [x] Implement `TimeTravel/index.tsx` (horizontal slider + step counter)
- [x] Add keyboard support: Left/Right arrows to step through
- [x] Wire: slider moves → `store.setTimeTravelIndex(n)` → `TraceGraph` grays out future nodes

### Done Condition
1. Click an LLM call node → see prompt + completion in right panel
2. Edit the prompt → click Replay → see new completion + diff
3. Use the time-travel slider to step through the execution

---

## Phase 4: Computer-Use + Polish (Weeks 7–8)

**Goal:** Playwright tracing, docs, and open-source launch.

### Tasks

**SDK: Computer-Use Instrumentation**
- [x] Implement `integrations/playwright.py` (monkey-patch Page methods)
- [x] Implement OpenAI auto-patch (`integrations/openai.py`)
- [x] Implement Anthropic auto-patch (`integrations/anthropic.py`)
- [x] Implement `os`/`subprocess` auto-patch for file/shell tracing
- [x] Write example: `sdk/examples/browser_agent.py` (Playwright agent end-to-end)

**Frontend: Polish**
- [x] Add loading skeletons to TraceList and TraceGraph
- [x] Add error states (backend unreachable banner)
- [x] Add screenshot display in `BrowserDetail`
- [x] Add cost + token summary bar at top of TraceGraph
- [x] Add trace search/filter in TraceList (by status, date range)
- [x] Make the three panels resizable (drag to resize)

**Docs + Launch**
- [x] Write `sdk/README.md` (quickstart in 5 minutes)
- [x] Write `docs/contributing.md` (development setup, PR guidelines)
- [x] Create `sdk/examples/` folder with 3 working examples
- [ ] Record a 2-minute demo video (screen recording)
- [ ] Publish `beacon-sdk` to PyPI
- [ ] Push everything to GitHub with a proper Release tag
- [ ] Post on Hacker News (Show HN), Reddit (r/LangChain, r/AI_Agents), Twitter

### Done Condition
A developer can `pip install beacon-sdk`, follow the README, and have a working trace in the UI within 5 minutes.

---

## Phase 5: UI Redesign + Design System

**Goal:** Intuitive UX for new developers, consistent design language, proper navigation.

### Tasks

**Design System**
- [x] Replace generic shadcn color tokens with Linear-inspired blue-hued oklch palette (dark-first)
- [x] Add Inter Variable font (13px base, feature settings)
- [x] Create `docs/design-system.md` as a living reference for developers and AI agents
- [x] Define typography scale, spacing conventions, component patterns

**Layout & Navigation**
- [x] Replace tab-bar navigation with persistent 220px sidebar (Dashboard, Traces, Playground, Settings)
- [x] Add route-driven navigation (React Router) and keep Zustand state for sidebar/UI controls
- [x] Linear-style inset content panel (bordered, rounded, shadowed)

**Pages**
- [x] Create `DashboardPage` — getting-started guide (empty state) + stats overview (returning user)
- [x] Extract `TracesPage` — the existing 3-panel debugger
- [x] Create `PlaygroundPage` — wrapper around existing Playground
- [x] Create `SettingsPage` — full page replacing the modal ApiKeyDialog

**Dark Mode Fixes**
- [x] Fix SpanNode graph colors (was light-mode-only, now dark-friendly)
- [x] Set React Flow to dark color mode
- [x] Consistent typography across all components (13px base)

### Done Condition
New developer opens `localhost:5173` → sees a welcoming Dashboard → can navigate via sidebar to Traces, Playground, and Settings → all views are visually consistent with the design system.

---

## Phase 6: Production Readiness

**Goal:** Fix the gaps that make Beacon unreliable with real-world agents. After this phase, any Python agent using OpenAI or Anthropic — including streaming, tool-calling, and async patterns — produces complete, accurate traces.

### Tasks

**SDK: Streaming Support**
- [x] In `sdk/beacon_sdk/integrations/openai.py`, implement streaming in `_patched_create_fn`: when `kwargs.get("stream")` is `True`, wrap the returned iterator to accumulate chunks, extract the final completion text and token usage, and emit a completed span when the stream is exhausted
- [x] Implement the same streaming logic in `_patched_async_create_fn` for the async path, wrapping the `AsyncStream` object
- [x] In `sdk/beacon_sdk/integrations/anthropic.py`, implement streaming in `_patched_create_fn`: wrap the Anthropic `MessageStream` to accumulate `content_block_delta` events, extract final `message_stop` usage data, and emit a completed span
- [x] Implement the same streaming logic in `_patched_async_create_fn` for the async Anthropic path
- [x] Add tests in `sdk/tests/test_integrations_openai.py` for streaming: mock a chunked response iterator, assert the span captures the full accumulated completion, correct token counts, and cost
- [x] Add tests in `sdk/tests/test_integrations_anthropic.py` for streaming: mock Anthropic's event-based streaming, assert span correctness

**SDK: Tool Calls Capture**
- [x] In `sdk/beacon_sdk/integrations/openai.py`, extend `_apply_response_attributes` to check `choice.message.tool_calls` — if present, serialize the tool calls list (name + arguments) as JSON into `llm.tool_calls` attribute and set `llm.finish_reason` to `"tool_calls"`
- [x] In `sdk/beacon_sdk/integrations/anthropic.py`, extend response handling to detect `tool_use` content blocks in `response.content`, serialize them as JSON into `llm.tool_calls`
- [x] In `frontend/src/components/SpanDetail/LlmCallDetail.tsx`, add a "Tool Calls" section that renders `llm.tool_calls` when present — display each tool call's name and arguments in a collapsible JSON view
- [x] Add tests for tool_calls capture in both `sdk/tests/test_integrations_openai.py` and `sdk/tests/test_integrations_anthropic.py`

**SDK: Fix LangChain Integration**
- [x] In `sdk/beacon_sdk/integrations/langchain.py`, update `BeaconCallbackHandler` to use the `(span, token)` tuple return from `tracer.start_span()` instead of the old single-span return API
- [x] Update all `on_*_end` and `on_*_error` methods to use the `end_span(span, token, ...)` signature
- [x] Store `(span, token)` tuples in the `_run_to_span` dict instead of just span_id strings
- [x] Add `sdk/tests/test_integrations_langchain.py` with mock LangChain runs testing the full callback lifecycle

**SDK: Async Batch Exporter**
- [x] In `sdk/beacon_sdk/exporters.py`, create `AsyncBatchExporter` class: thread-safe queue, background daemon thread that flushes every N ms or when batch_size is reached, uses `requests` in the background thread to avoid blocking the caller's event loop
- [x] Add `flush()` method for manual flushing and `shutdown()` method that flushes remaining spans and stops the background thread
- [x] In `sdk/beacon_sdk/__init__.py`, update `init()` to accept an `exporter` parameter (`"sync"` | `"async"` | `"auto"` default) — `"auto"` selects async exporter when an asyncio event loop is running
- [x] Add `atexit` handler in `init()` to call `shutdown()` on the exporter, ensuring no spans are lost on process exit
- [x] Add tests in `sdk/tests/test_exporters.py` for batching, flush-on-shutdown, and thread safety

**SDK: Consolidate Price Tables**
- [x] Create `sdk/beacon_sdk/pricing.py` with a unified `PRICE_TABLE: dict[str, tuple[float, float]]` using per-1M-token pricing and a shared `estimate_cost(model, input_tokens, output_tokens)` function
- [x] In `sdk/beacon_sdk/integrations/openai.py`, remove the local `_COST_PER_1K` dict and `_estimate_cost` function; import from `beacon_sdk.pricing`
- [x] In `sdk/beacon_sdk/integrations/anthropic.py`, do the same
- [x] Ensure the canonical price table includes all models from `backend/app/services/llm_client.py` (gpt-4.1, o4-mini, claude-opus-4-6, claude-sonnet-4-6, etc.)

**SDK: File Operation Auto-Patch**
- [x] Create `sdk/beacon_sdk/integrations/file_patch.py` that patches `builtins.open` to create `file_operation` spans with attributes: `file.operation`, `file.path`, `file.size_bytes`, `file.content` (truncated to 2000 chars)
- [x] In `sdk/beacon_sdk/__init__.py`, add `file_patch` to `_apply_auto_patches()` — only when `BEACON_PATCH_FILE_OPS=true` (default `false`) since patching `open()` is intrusive
- [x] Add `sdk/tests/test_integrations_file.py` with tests for read, write, and append operations

### Done Condition
Run a Python agent that uses OpenAI streaming with tool calls, Anthropic streaming, and LangChain chains — all spans appear correctly in the UI with complete data (full completion text, token counts, cost, tool calls). The exporter does not block the event loop.

---

## Phase 7: Deep Debugging

**Goal:** Strengthen the core "Chrome DevTools for AI Agents" differentiator. Add timeline views, search, trace comparison, URL routing, export, and frontend test infrastructure.

### Tasks

**Frontend: URL-Based Routing**
- [x] Add `react-router-dom` to `frontend/package.json`
- [x] In `frontend/src/App.tsx`, replace the Zustand-based `currentPage` routing with React Router: `/` (dashboard), `/traces` (trace list), `/traces/:traceId` (trace with selected trace), `/traces/:traceId/:spanId` (specific span), `/playground`, `/settings`
- [x] Update `frontend/src/store/navigation.ts` to sync with React Router or replace entirely with `useNavigate`/`useParams`
- [x] In `frontend/src/store/trace.ts`, read `traceId` and `spanId` from URL params on mount, auto-selecting the trace/span
- [x] In `frontend/src/components/Sidebar/index.tsx`, replace `navigate()` calls with React Router `<Link>` or `useNavigate()`
- [x] In `frontend/vite.config.ts`, add history fallback so all routes resolve to `index.html`

**Backend: Trace Deletion and Cleanup**
- [x] Add `DELETE /v1/traces/{trace_id}` endpoint — cascading delete of spans and replay_runs via the existing `ON DELETE CASCADE` FK
- [x] Add `DELETE /v1/traces` (batch) endpoint accepting `{ trace_ids: string[] }` or `{ older_than: float }` for bulk cleanup
- [x] Add `GET /v1/stats` endpoint returning database size, total traces, total spans, oldest trace timestamp
- [x] Add tests in `backend/tests/test_traces.py` for delete endpoints

**Frontend: Trace Deletion**
- [x] Add delete button (trash icon) to trace list items with confirmation dialog
- [x] Add "Clear All Traces" button to the Settings page
- [x] Add `deleteTrace()` and `deleteAllTraces()` functions to `frontend/src/lib/api.ts`

**Frontend: Timeline/Waterfall View**
- [x] Create `frontend/src/components/TimelineView/index.tsx` — Gantt-chart view showing each span as a horizontal bar positioned by `start_time`/`end_time`, color-coded by `span_type`, with parent-child indentation
- [x] Create `TimelineBar.tsx` sub-component with hover tooltip showing name, duration, cost
- [x] Add a toggle in `TracesPage` to switch between "Graph" and "Timeline" views
- [x] Highlight parallelism: overlapping spans at the same depth appear on separate rows
- [x] Highlight the critical path (longest chain of sequential spans determining total trace duration) with a distinct color/border
- [x] Add a "Slowest Spans" summary panel below the timeline showing the top 5 spans by duration

**Backend: Full-Text Search**
- [x] Add `GET /v1/search` endpoint accepting `q` (search string), searching across `spans.name`, `spans.attributes` (JSON text), and `traces.name` using SQLite `LIKE`
- [x] Return `{ results: [{ trace_id, span_id, name, match_context }], total }` with matching text snippets
- [x] Add index `idx_spans_name` on `spans.name`

**Frontend: Full-Text Search**
- [x] Add a search bar at the top of the Traces page that calls `GET /v1/search` with debounced input
- [x] Display search results as a list linking to specific traces/spans via URL routing

**Frontend: Trace Comparison**
- [ ] Create `frontend/src/pages/ComparePage.tsx` — side-by-side view of two traces
- [ ] Add "Compare" action: user selects two traces via checkboxes in TraceList, clicks "Compare"
- [ ] Render two React Flow graphs side by side with synchronized zoom/pan
- [ ] Show diff table: metrics comparison (total cost, tokens, duration, span count, error rate)

**Backend: Trace Export**
- [ ] Add `GET /v1/traces/{trace_id}/export?format=json` — full trace with all spans in Beacon's JSON format
- [ ] Add `format=otel` option converting spans to OTEL-compatible export format
- [ ] Add `format=csv` option — flat CSV with one row per span (columns: trace_id, span_id, parent_span_id, name, span_type, start_time, end_time, duration_ms, status, cost, tokens)
- [ ] Add `GET /v1/traces/export` for bulk export with optional `trace_ids` query param

**Backend: Trace Import**
- [ ] Add `POST /v1/traces/import` endpoint accepting Beacon JSON format (symmetric with export) — creates trace and spans from the imported file
- [ ] Ship `docs/example-traces/` directory with 2–3 curated example trace JSON files (e.g., a LangChain RAG agent, a tool-calling agent with errors) so new users can import and explore a populated UI immediately

**Frontend: Trace Export**
- [ ] Add "Export" button to trace detail view (top bar of TraceGraph) with dropdown: "JSON", "OTEL JSON", "CSV"
- [ ] Trigger browser download of the exported file

**Frontend: Trace Import**
- [ ] Add "Import Trace" button in Traces page header that opens a file picker for JSON files
- [ ] Call `POST /v1/traces/import` with the selected file and navigate to the imported trace

**Backend: Tags and Annotations**
- [ ] Add `PUT /v1/traces/{trace_id}/tags` endpoint to set/update trace tags (the `tags` column already exists in the schema)
- [ ] Add `PUT /v1/spans/{span_id}/annotations` endpoint (new `annotations TEXT DEFAULT '[]'` column in spans table)
- [ ] Add migration logic in `database.py` `init_db()` to add the `annotations` column if it doesn't exist

**Frontend: Tags and Annotations**
- [ ] Add tag pills to `TraceListItem` showing existing tags
- [ ] Add inline tag editor (click to add/edit tags) in the trace detail header
- [ ] Add annotation input in `SpanDetail` — text area to add notes to any span
- [ ] Add tag-based filtering in `TraceFilter`

**Frontend: Token Count Preview**
- [ ] In the Monaco prompt editor (`ReplayPanel.tsx`), show a live estimated token count as the user edits using `js-tiktoken` or a similar tokenizer
- [ ] Display token count badge next to the Replay button

**Backend: Prompt Versioning**
- [ ] Add `prompt_versions` table: `version_id`, `span_id`, `prompt_text`, `created_at`, `label` (optional)
- [ ] Add `GET /v1/spans/{span_id}/prompt-versions` and `POST /v1/spans/{span_id}/prompt-versions` endpoints
- [ ] Each replay automatically saves a prompt version; users can also manually save with an optional label

**Frontend: Prompt Versioning**
- [ ] Add version history dropdown in the prompt editor to browse and restore previous prompt versions

**Frontend: Test Infrastructure**
- [ ] Add Vitest + React Testing Library to `frontend/package.json` dev dependencies
- [ ] Add `vitest.config.ts` in the frontend root
- [ ] Write tests for `TraceList` component (renders traces, handles empty state, filter interaction)
- [ ] Write tests for `SpanDetail/LlmCallDetail.tsx` (renders attributes correctly, handles missing data)
- [ ] Write tests for the Zustand `trace` store (loadTraces, selectTrace, appendSpan)
- [ ] Write tests for `api.ts` utility functions (mock fetch, verify URL construction)
- [ ] Add `npm run test` script and integrate into `make test`

### Done Condition
A developer can: (1) deep-link to `localhost:5173/traces/abc-123/span-456` and land on the correct trace and span, (2) search for "error" and find all spans with errors, (3) compare two traces side by side, (4) view a timeline/waterfall of span execution with critical path highlighted, (5) export a trace as JSON, OTEL, or CSV, (6) tag traces and annotate spans, (7) delete old traces, (8) import an example trace JSON file and explore it in the UI, (9) see token count update live while editing a prompt, (10) browse and restore previous prompt versions. Frontend has test coverage for critical components.

---

## Phase 8: Ecosystem Expansion

**Goal:** Widen the funnel beyond Python/OpenAI/Anthropic. Support the major AI frameworks and ship a JavaScript SDK.

### Tasks

**SDK: Google Gemini Support**
- [ ] Create `sdk/beacon_sdk/integrations/google_genai.py` — patch `google.generativeai.GenerativeModel.generate_content` (sync + async), creating `llm_call` spans with `llm.provider: "google"`, prompt, completion, tokens, cost
- [ ] Add Gemini models to `sdk/beacon_sdk/pricing.py` (gemini-2.0-flash, gemini-2.5-pro, etc.)
- [ ] Add Gemini to `_apply_auto_patches()` in `sdk/beacon_sdk/__init__.py`
- [ ] In `backend/app/services/llm_client.py`, add Google/Gemini models to `PRICE_TABLE` and add `call_google()` for replay support
- [ ] Add `sdk/tests/test_integrations_google.py` with mocked responses
- [ ] Create `sdk/examples/google_agent.py`

**SDK: CrewAI Integration**
- [ ] Create `sdk/beacon_sdk/integrations/crewai.py` — patch `Crew.kickoff()` to create a root `agent_step` span, hook into CrewAI's callback system for individual agent steps and tool uses
- [ ] Set `agent.framework: "crewai"` in span attributes
- [ ] Create `sdk/examples/crewai_agent.py`
- [ ] Add `sdk/tests/test_integrations_crewai.py`

**SDK: AutoGen Integration**
- [ ] Create `sdk/beacon_sdk/integrations/autogen.py` — patch `ConversableAgent.generate_reply()` and `GroupChat.run()` to create spans capturing multi-agent conversation turns
- [ ] Map each AutoGen agent message exchange to an `agent_step` span with `agent.framework: "autogen"`
- [ ] Create `sdk/examples/autogen_agent.py`
- [ ] Add `sdk/tests/test_integrations_autogen.py`

**SDK: LlamaIndex Integration**
- [ ] Create `sdk/beacon_sdk/integrations/llamaindex.py` — implement `BeaconCallbackHandler` for LlamaIndex that traces query engine calls, retrieval steps, and LLM calls
- [ ] Map LlamaIndex events to appropriate span types: `llm_call` for LLM, `tool_use` for retrieval
- [ ] Create `sdk/examples/llamaindex_agent.py`
- [ ] Add `sdk/tests/test_integrations_llamaindex.py`

**SDK: Local Model Support**
- [ ] Verify that Ollama and vLLM (OpenAI-compatible APIs) are automatically traced via the existing OpenAI patch; document this in SDK README
- [ ] For Ollama's native Python client, create `sdk/beacon_sdk/integrations/ollama.py` patching `ollama.chat()` and `ollama.generate()`
- [ ] Add `sdk/tests/test_integrations_ollama.py`

**JavaScript/TypeScript SDK (New Package)**
- [ ] Create `sdk-js/` directory with `package.json`, `tsconfig.json`, project structure mirroring the Python SDK
- [ ] Implement `sdk-js/src/tracer.ts` — `BeaconTracer` class using `AsyncLocalStorage` for context propagation
- [ ] Implement `sdk-js/src/exporter.ts` — HTTP exporter posting to `POST /v1/spans` (same backend)
- [ ] Implement `sdk-js/src/integrations/openai.ts` — monkey-patch the `openai` npm package's `chat.completions.create()`
- [ ] Implement `sdk-js/src/integrations/anthropic.ts` — monkey-patch the `@anthropic-ai/sdk` npm package
- [ ] Implement `sdk-js/src/integrations/vercel-ai.ts` — instrument Vercel AI SDK's `generateText()` and `streamText()`
- [ ] Implement `sdk-js/src/index.ts` — public API: `init()`, `observe()` decorator, auto-patching
- [ ] Write `sdk-js/README.md` with quickstart guide
- [ ] Add `sdk-js/tests/` with tests for tracer, exporter, and integrations
- [ ] Add `sdk-js/examples/` with a basic Node.js agent example

**Backend: OTLP-Compatible Ingestion**
- [ ] Add `POST /v1/otlp/traces` endpoint accepting standard OpenTelemetry Protocol (OTLP) JSON format, mapping OTEL resource/scope/span fields to Beacon's span model — this allows existing OTEL-instrumented applications to send traces to Beacon without the Beacon SDK
- [ ] Document the OTLP ingestion endpoint in `sdk/README.md`
- [ ] Add tests in `backend/tests/test_otlp.py` with sample OTLP payloads

**Backend: Multi-SDK Support**
- [ ] In `backend/app/schemas.py`, add optional `sdk_language` field to `SpanCreate` (`"python"` | `"javascript"` | `"unknown"`) for analytics
- [ ] In `backend/app/services/llm_client.py`, add Gemini models to the replay service

**Frontend: Framework Badges**
- [ ] In `frontend/src/components/TraceGraph/SpanNode.tsx`, add framework icon/badge (LangChain, CrewAI, AutoGen, LlamaIndex) based on `agent.framework` attribute
- [ ] In `frontend/src/components/TraceList/TraceListItem.tsx`, show SDK language badge (Python/JS) if `sdk_language` is present

### Done Condition
A developer using CrewAI, AutoGen, LlamaIndex, Google Gemini, Ollama, or the JS/TS SDK can `init()` Beacon and see complete, correctly structured traces. Framework badges appear in the graph view. An existing OTEL-instrumented application can send traces to Beacon via the OTLP endpoint without using the Beacon SDK.

---

## Phase 9: AI-Powered Debugging

**Goal:** The viral "wow" features. AI analyzes traces and provides actionable debugging insights. This is the screenshot-worthy moment that gets shared on social media.

### Tasks

**Backend: Analysis Infrastructure**
- [ ] Create `backend/app/services/analysis_service.py` — shared infrastructure for AI-powered analysis: accepts trace span data, constructs a prompt, calls an LLM via `llm_client.py`, returns structured analysis
- [ ] Add Pydantic schemas: `AnalysisRequest`, `AnalysisResponse`, `RootCauseAnalysis`, `CostOptimization`, `PromptSuggestion`, `AnomalyReport`, `TraceSummary`
- [ ] Create `backend/app/routers/analysis.py` with router prefix `/v1/analysis`
- [ ] Register the analysis router in `backend/app/main.py`

**Backend: Root Cause Analysis**
- [ ] Add `POST /v1/analysis/root-cause` accepting `{ trace_id }` — retrieves all spans, constructs a prompt with the execution graph and error context, asks the LLM to identify root cause, affected components, and suggested fix
- [ ] Return `{ trace_id, root_cause, affected_spans, confidence, suggested_fix }`
- [ ] Add tests with a mock trace containing a known error pattern

**Backend: Cost Optimization Analysis**
- [ ] Add `POST /v1/analysis/cost-optimization` accepting `{ trace_ids }` — analyzes LLM call patterns and identifies: redundant calls (same prompt repeated), expensive models used for simple tasks, cacheable calls, token waste from overly long prompts
- [ ] Return `{ suggestions: [{ type, description, estimated_savings_usd, affected_spans }] }`

**Backend: Prompt Improvement Suggestions**
- [ ] Add `POST /v1/analysis/prompt-suggestions` accepting `{ span_id }` — analyzes a single LLM call's prompt and suggests improvements (clarity, specificity, format instructions, few-shot examples)
- [ ] Return `{ original_prompt, suggestions: [{ category, description, improved_prompt_snippet }] }`

**Backend: Anomaly Detection**
- [ ] Add `POST /v1/analysis/anomalies` accepting `{ trace_id }` — compares trace against historical baselines (last 50 traces of the same name) and flags: cost spikes (>2x mean), latency spikes, unusual error patterns, missing expected spans
- [ ] Return `{ anomalies: [{ type, severity, description, trace_id, span_id }] }`

**Backend: Error Pattern Recognition**
- [ ] Add `POST /v1/analysis/error-patterns` accepting `{ trace_ids }` (or defaults to last 50 error traces) — clusters similar failures by error message, failing span name, and execution structure
- [ ] Return `{ patterns: [{ pattern_name, count, example_trace_ids, common_root_cause, category }] }`
- [ ] Detect common anti-patterns: infinite loops (repeated identical spans), repeated tool failures (same tool failing 3+ times), context window overflow (token count approaching model limit)
- [ ] Auto-tag traces with failure categories (timeout, rate_limit, context_overflow, tool_failure, hallucination) via `PUT /v1/traces/{trace_id}/tags`

**Backend: AI-Powered Trace Comparison**
- [ ] Add `POST /v1/analysis/compare` accepting `{ trace_id_a, trace_id_b }` — uses AI to identify structural divergence points (where execution paths differ), semantic differences in prompts/completions, and metric deltas
- [ ] Return `{ divergence_points: [{ span_a, span_b, description }], metric_diff, summary }`
- [ ] Support "Golden Baseline" concept: compare a trace against the most recent trace tagged `baseline`

**Backend: Trace Summarization**
- [ ] Add `POST /v1/analysis/summarize` accepting `{ trace_id }` — generates a natural language summary of what the agent did (e.g., "The agent received a request to book a flight. It called GPT-4o 3 times, searched for flights, encountered a rate limit, retried, and returned results in 12.4s at $0.023.")
- [ ] Return `{ trace_id, summary, key_events }`

**Frontend: Analysis Panel**
- [ ] Create `frontend/src/components/Analysis/RootCausePanel.tsx` — shows root cause, affected spans (highlighted in graph), and suggested fix
- [ ] Create `CostOptimizationPanel.tsx` — shows suggestions with estimated savings, links to affected spans
- [ ] Create `PromptSuggestionsPanel.tsx` — shows prompt improvements with before/after diffs
- [ ] Create `AnomalyBanner.tsx` — dismissible banner at top of trace detail when anomalies are detected
- [ ] Create `TraceSummaryCard.tsx` — natural language summary at top of trace detail, generated on demand

**Frontend: Analysis Integration**
- [ ] Add "Analyze" button (sparkle icon) to trace detail header — dropdown with: "Root Cause Analysis", "Cost Optimization", "Prompt Suggestions", "Summarize"
- [ ] Add analysis API functions to `frontend/src/lib/api.ts`
- [ ] Create `frontend/src/store/analysis.ts` Zustand store for analysis state
- [ ] When root cause analysis highlights affected spans, pulse/highlight those nodes in the React Flow graph

**Frontend: Error Pattern Recognition**
- [ ] Create `ErrorPatternsPanel.tsx` showing clustered failure groups with counts and links to example traces
- [ ] Add "Error Patterns" option to the "Analyze" dropdown
- [ ] When viewing a pattern, highlight all matching traces in the trace list

**Frontend: Trace Comparison Enhancements**
- [ ] In `ComparePage.tsx`, highlight AI-detected divergence points in the side-by-side graph view with distinct markers
- [ ] Add "Mark as Baseline" button in trace detail header (stores `baseline` tag)
- [ ] Add "Compare Against Baseline" action in trace detail that auto-selects the most recent baseline trace

**Frontend: A/B Prompt Testing**
- [ ] In the Playground's CompareView, add mode toggle: "Compare Models" (existing) vs "Compare Prompts" (new)
- [ ] "Compare Prompts" mode: two prompt editors side by side, same model, run both and show results with diff
- [ ] Track A/B test results in a simple `ab_tests` table for historical comparison

**Dashboard: Analytics Upgrade**
- [ ] In `frontend/src/pages/DashboardPage.tsx`, replace 4-stat-card layout with: trend charts (cost over time, tokens over time, trace count, error rate, success/failure rate) using recharts, most expensive traces table, anomaly alerts section
- [ ] Add `GET /v1/stats/trends` backend endpoint returning time-bucketed aggregates (daily cost, tokens, traces, errors) for the last 30 days
- [ ] Add "Most Expensive Prompts" table (top 10 LLM calls by cost across all traces)
- [ ] Add "Most Expensive Tools" table (top 10 tool calls by duration)
- [ ] Add cost forecasting widget: project next 30 days cost based on trailing 30-day trend
- [ ] Add trace clustering visualization: group traces by structural similarity, render as a scatter plot or treemap

### Done Condition
A developer clicks "Analyze" on a failed trace and receives: (1) a plain-English root cause explanation with highlighted spans, (2) cost optimization suggestions, (3) prompt improvement recommendations, (4) error pattern clusters showing similar failures across traces. The developer can mark a trace as "baseline" and compare new traces against it with AI-detected divergence points. The Playground supports A/B prompt testing. The dashboard shows trend charts, cost forecasting, most expensive prompts/tools, and trace clustering.

---

## Phase 10: Enterprise Foundation

**Goal:** Build the foundation for multi-user, team-based, and self-hosted deployment. Transition Beacon from a solo local tool toward a product that can sustain a business. The zero-auth local SQLite experience remains the default for individual developers.

### Tasks

**Backend: Authentication System**
- [ ] Create `backend/app/auth/` with `models.py`, `schemas.py`, `service.py`, `middleware.py`
- [ ] Implement API key authentication: `X-Beacon-API-Key` header, keys stored hashed in a new `api_keys` table
- [ ] Add auth middleware to `backend/app/main.py` — only active when `BEACON_AUTH_ENABLED=true` (default `false`)
- [ ] Add `POST /v1/auth/api-keys` (create), `DELETE /v1/auth/api-keys/{key_id}` (revoke), `GET /v1/auth/api-keys` (list)
- [ ] Add tests for auth middleware (enabled and disabled paths)

**Backend: OAuth/SSO Support**
- [ ] Implement OAuth 2.0 authorization code flow with support for Google, GitHub, and generic OIDC providers
- [ ] Add SAML support for enterprise SSO
- [ ] Add `GET /v1/auth/login`, `GET /v1/auth/callback`, `POST /v1/auth/logout`
- [ ] Configuration via env vars: `BEACON_OAUTH_PROVIDER`, `BEACON_OAUTH_CLIENT_ID`, `BEACON_OAUTH_CLIENT_SECRET`

**Backend: Multi-Tenancy**
- [ ] Add `workspaces` table: `workspace_id`, `name`, `created_at`, `settings` (JSON)
- [ ] Add `workspace_members` table: `workspace_id`, `user_id`, `role` (owner/admin/member/viewer)
- [ ] Add `workspace_id` column to `traces` and `spans` tables (nullable for backward compatibility)
- [ ] Add workspace-scoped query filtering to all trace/span service functions
- [ ] Add CRUD endpoints for workspaces and workspace members

**Backend: Role-Based Access Control**
- [ ] Implement RBAC middleware: owner (full access), admin (manage members, delete traces), member (create/read), viewer (read-only)
- [ ] Add `@require_role("admin")` decorator for protected endpoints

**Backend: PostgreSQL Support**
- [ ] Refactor `backend/app/database.py` to support both SQLite and PostgreSQL via `BEACON_DB_TYPE` env var (`"sqlite"` default, `"postgresql"`)
- [ ] For PostgreSQL, read `BEACON_DATABASE_URL` connection string
- [ ] Ensure all queries are dialect-compatible; use PostgreSQL `tsvector`/`tsquery` for full-text search when available
- [ ] Add test fixture that can run the suite against both databases

**Backend: Trace Retention Policies**
- [ ] Add `retention_policies` table: `policy_id`, `workspace_id`, `max_age_days`, `max_traces`, `max_storage_mb`
- [ ] Create `backend/app/services/retention_service.py` running as a background task every hour, deleting traces exceeding the policy
- [ ] Add `GET/PUT /v1/settings/retention` endpoints

**Frontend: Authentication UI**
- [ ] Create `LoginPage.tsx` with API key input and OAuth provider buttons
- [ ] Add auth state to Zustand store: `user`, `isAuthenticated`, `token`
- [ ] Add protected route wrapper that redirects to login when auth is enabled

**Frontend: Workspace Switcher**
- [ ] Add workspace selector dropdown in sidebar header
- [ ] Create `WorkspaceSettingsPage.tsx` for managing members and workspace settings
- [ ] All trace/span queries pass `workspace_id` when workspaces are enabled

**Deployment: Docker and Kubernetes**
- [ ] Create `Dockerfile` for backend (Python/FastAPI + Uvicorn)
- [ ] Create `Dockerfile` for frontend (Node build + Nginx serve)
- [ ] Create `docker-compose.yml` with backend, frontend, and optional PostgreSQL
- [ ] Create `k8s/` directory with Kubernetes manifests (Deployment, Service, ConfigMap, Secret, Ingress)
- [ ] Create `k8s/helm/` with a Helm chart for parameterized deployment
- [ ] Add `make docker-build` and `make docker-up` targets
- [ ] Write `docs/deployment.md` deployment guide

### Done Condition
Beacon can be deployed via `docker-compose up` with PostgreSQL, API key authentication, workspace isolation, and RBAC. An organization can self-host with SSO, create team workspaces, and configure trace retention. The zero-auth local SQLite experience remains the default.

---

## Phase 11: Developer Workflow Integration

**Goal:** Meet developers where they work. Integrate Beacon into CI/CD pipelines and IDEs so debugging is part of the development workflow, not a separate step.

### Tasks

**CI/CD: GitHub Action**
- [ ] Create `beacon-action/` directory with a reusable GitHub Action that starts Beacon backend, runs a user-specified test command with SDK instrumentation, and uploads trace artifacts
- [ ] The action should output trace summary (total cost, duration, error count) as a PR comment
- [ ] Support configurable thresholds: fail the build if cost exceeds $X or error rate exceeds Y%

**CI/CD: pytest Plugin**
- [ ] Create `beacon-pytest/` package (or add to `sdk/`) with a pytest plugin that auto-initializes Beacon SDK for test sessions
- [ ] Automatically capture traces for each test function decorated with `@observe`
- [ ] Generate a test report with trace links and cost summary
- [ ] Support `--beacon-export` flag to save traces as JSON fixtures

**CI/CD: Trace-as-Test-Fixture**
- [ ] Add `beacon_sdk.testing.load_trace(path)` utility to load exported trace JSON files as test fixtures
- [ ] Add `beacon_sdk.testing.assert_trace_matches(baseline, current, tolerances)` to compare a new trace against a baseline with configurable tolerances (cost +-10%, duration +-20%, same span structure)
- [ ] Document the "golden trace" testing workflow in SDK README

**CI/CD: Regression Detection**
- [ ] Add `POST /v1/analysis/regression` accepting `{ baseline_trace_id, current_trace_id }` — compares metrics and structure, returns pass/fail with details
- [ ] Integrate with the GitHub Action: compare traces from PR branch against main branch baseline

**CI/CD: Performance Benchmarking**
- [ ] Add `GET /v1/stats/benchmarks` endpoint returning trace metrics grouped by git commit hash (requires `git_commit` attribute in spans)
- [ ] Add `git_commit` as an optional auto-detected attribute in `sdk/beacon_sdk/__init__.py` (read from `GIT_COMMIT` env var or `git rev-parse HEAD`)
- [ ] Frontend: benchmarks page showing cost/duration/error trends across commits

**VS Code Extension**
- [ ] Create `vscode-beacon/` directory with VS Code extension scaffolding (TypeScript, vscode API)
- [ ] Implement trace explorer sidebar: connect to running Beacon backend, list recent traces
- [ ] Implement inline trace decorations: show cost/duration/error badges inline next to `@observe`-decorated functions
- [ ] Implement "Quick Replay" command: right-click an `@observe` function → replay the most recent span for that function
- [ ] Implement trace webview panel: embed a simplified version of the trace graph inside VS Code
- [ ] Implement "Trace from Cursor" command: find the most recent trace containing a span for the function at cursor position

### Done Condition
A developer can: (1) add the Beacon GitHub Action to their CI pipeline and see trace summaries on PRs, (2) run `pytest --beacon-export` to capture and save traces as test fixtures, (3) compare traces across commits for regression detection, (4) install the VS Code extension and view traces inline while coding.

---

## Strategic Notes

**Phase ordering rationale:**

1. **Phase 6 first** — streaming and tool_calls gaps make real developers bounce. If `stream=True` calls are invisible (the default for most agents in 2026), developers try Beacon once and leave.

2. **Phase 7 next** — deepens the core differentiator into a daily-driver tool. URL routing alone unlocks sharing traces with teammates. Timeline view and search make the "Chrome DevTools" metaphor real.

3. **Phase 8 third** — widening the funnel only matters after the core product is robust. A JS/TS SDK opens the Vercel AI SDK / Next.js ecosystem. Framework integrations serve vocal communities.

4. **Phase 9 fourth** — the viral "wow" feature positioned after ecosystem expansion for maximum impact. When a developer clicks "Analyze" and gets a plain-English explanation of why their agent failed, that's the screenshot moment that drives social sharing.

5. **Phase 10 fifth** — highest-effort, lowest-individual-developer-value work. Auth, multi-tenancy, and PostgreSQL add zero value for solo developers. Build this when community traction (Phases 6-9) justifies it and enterprise design partners are ready.

6. **Phase 11 last** — developer workflow integration (CI/CD, VS Code) requires a mature product with stable APIs. The GitHub Action depends on Phase 7's export and Phase 9's analysis. The VS Code extension benefits from Phase 7's URL routing for deep links. These are adoption accelerators built on top of a complete product.

**How each phase builds on the previous:**
- Phase 6 fixes the data pipeline so traces are complete → all subsequent phases depend on this
- Phase 7 adds navigation/search/export infrastructure that Phase 8's multi-framework traces need
- Phase 8 expands the user base that Phase 9's AI features will delight
- Phase 9's analytics and anomaly detection naturally lead to Phase 10's retention policies
- Phase 10's PostgreSQL support is needed at scale but not before
- Phase 11's GitHub Action uses Phase 7's export format and Phase 9's regression analysis
- Phase 11's VS Code extension connects to the same backend APIs built in Phases 6-10

---

## Definition of Done (Per Task)

A task is done when:
1. The feature works as described
2. Tests pass (`pytest` for backend, `npm run typecheck` + `npm run lint` for frontend)
3. No debug `print()` / `console.log()` statements left in the code
4. The relevant doc file is updated if the implementation diverged from the design
