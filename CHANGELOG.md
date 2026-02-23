# Changelog

All notable changes to Beacon will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Beacon uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- feat(sdk): CrewAI auto-instrumentation — zero-config tracing via `Crew.kickoff()` patching with callback injection for task and agent step spans (VL-44)
- feat(sdk-js): Add JS SDK examples — `basic-agent.ts` (OpenAI + observe) and `vercel-ai-agent.ts` (generateText + streamText) (VL-50)
- docs(sdk): Document OTLP ingestion endpoint (`POST /v1/otlp/traces`) in SDK README with payload format, curl example, and attribute reference (VL-49)
- feat(frontend): AI analysis panel components — RootCausePanel, CostOptimizationPanel, PromptSuggestionsPanel, ErrorPatternsPanel, TraceSummaryCard, AnomalyBanner (VL-60)
- feat(frontend): Analysis integration — Zustand analysis store, Analyze dropdown in CostSummaryBar, analysis panel rendering in SpanDetail, span highlighting with amber pulse on graph nodes (VL-61)
- feat(backend): `GET /v1/stats/trends` — time-bucketed trend aggregates (cost, tokens, trace count, error rate) with day/hour granularity and gap-filling
- feat(backend): `GET /v1/stats/top-costs` — top N most expensive LLM call spans by cost via SQL-level JSON extraction
- feat(backend): `GET /v1/stats/top-duration` — top N longest-running tool call spans by duration via SQL-level sorting
- feat(frontend): Dashboard analytics upgrade — recharts trend charts (cost, tokens, traces, error rate), cost forecast with linear regression, ranked tables (most expensive prompts, slowest tools), AI anomaly alerts with graceful degradation
- feat(frontend): Add `cursor-pointer` to all `<Button>` components and trace list items
- feat(frontend): Anomaly detection results cached in Zustand store to avoid redundant LLM calls on page navigation

### Fixed
- fix(sdk-js): ESM auto-patching — use dynamic `import()` instead of `require()` for CJS/ESM compatibility, make `init()` async to await patches (VL-66)
- fix(backend): trace status now set from first ingested span instead of hardcoded `"unset"`
- fix(backend): `get_baseline_stats` computed duration from `start_time`/`end_time` instead of non-existent `duration_ms` attribute
- fix(backend): anomaly detection endpoint now overrides `trace_id` on each anomaly object so navigation links resolve correctly
- fix(frontend): anomaly error state shows actual backend error message instead of hardcoded "configure API key" text

### Changed
- feat(frontend): Darken sidebar to near-black (`oklch(0.070)`) for Linear-style contrast with content area
- feat(frontend): Simplify trace list items to single row — name, duration, and status icon (removed tags, span count, relative time, SDK badge)
- feat(frontend): Move TagEditor from canvas header bar to SpanDetail panel under "Trace Tags" section
- feat(frontend): Canvas UX — Figma-style keyboard shortcuts (Cmd+0 fit, Cmd+/- zoom, Space pan), zoom percentage indicator, node hover tooltips, pointer cursor on clickable nodes
- feat(frontend): Increase default trace list panel width to 350px

### Added
- feat(backend): AI-powered trace analysis endpoints (`POST /v1/analysis/{root-cause,cost-optimization,prompt-suggestions,anomalies,error-patterns,compare,summarize}`) with shared analysis service infrastructure, structured JSON response parsing, and Google/OpenAI/Anthropic LLM support
- feat(sdk): Google Gemini (`google-genai`) auto-instrumentation — patches `Models.generate_content`, `generate_content_stream`, and async equivalents with token usage, cost estimation, tool-call capture, and streaming support
- feat(backend): Google Gemini backend replay support — `call_google()` REST API client, Gemini models in pricing/provider tables, `google` added to supported settings providers
- feat(sdk-js): JS/TS SDK (`sdk-js/`) — full tracing SDK for Node.js 18+ with zero runtime dependencies, mirroring the Python SDK architecture (tracer, batch exporter, AsyncLocalStorage context, `observe()` wrapper, LLM cost estimation)
- feat(sdk-js): OpenAI integration — auto-patches `chat.completions.create` with streaming and tool call support
- feat(sdk-js): Anthropic integration — auto-patches `messages.create` with event-based streaming and tool use
- feat(sdk-js): Vercel AI SDK integration — patches `generateText()` and `streamText()` with span finalization
- feat(backend): `POST /v1/otlp/traces` — OTLP-compatible JSON ingestion endpoint for OpenTelemetry interoperability
- feat(backend): `sdk_language` field on spans and traces schema with SQLite migration — tracks which SDK produced each trace
- feat(frontend): SDK language badges (`PY`/`JS`) on trace list items
- feat(sdk): Python SDK now emits `sdk_language: "python"` in span output
- feat(frontend): Vitest + React Testing Library test infrastructure — 37 tests across 5 files covering trace store, API utilities, TraceList, LlmCallDetail, and tokenizer
- feat(frontend): Live token count preview in prompt editor using `js-tiktoken` with debounced updates
- feat(backend): `GET/POST /v1/spans/{span_id}/prompt-versions` — prompt versioning with auto-save on replay and manual save with optional labels
- feat(frontend): Prompt version history dropdown — browse and restore previous prompt versions in the replay editor
- feat(backend): `PUT /v1/traces/{id}/tags` — set/replace tags on a trace for categorization and filtering
- feat(backend): `PUT /v1/spans/{id}/annotations` — set/replace developer notes on individual spans
- feat(backend): SQLite migration adds `annotations` column to `spans` table (backward-compatible `ALTER TABLE ADD COLUMN`)
- feat(frontend): Tag pills on trace list items — display up to 3 tags with "+N" overflow indicator
- feat(frontend): Inline tag editor in trace detail bar — add/remove `key:value` tags with instant persistence
- feat(frontend): Span annotation panel — add, view, and delete developer notes on any span (Cmd/Ctrl+Enter shortcut)
- feat(frontend): Tag-based trace filtering in search modal — enter-to-add filter pills with substring matching
- test(backend): 12 new tests for tags and annotations endpoints (happy path, 404, persistence, replace, clear)
- feat(backend): `GET /v1/traces/{id}/export?format=json|otel|csv` — single trace export in Beacon JSON, OTEL JSON, or CSV formats
- feat(backend): `GET /v1/traces/export?trace_ids=...` — bulk trace export (JSON)
- feat(backend): `POST /v1/traces/import` — import traces from Beacon JSON export format with duplicate detection
- feat(frontend): Export dropdown on trace detail bar — download trace as JSON, OTEL JSON, or CSV
- feat(frontend): Import button in trace list header — file picker for JSON import with auto-navigation
- docs: two curated example trace files (`docs/example-traces/`) — RAG agent and tool-calling agent with errors
- feat: chronological sequence numbers (`#1`, `#2`, `#3`...) on canvas span nodes, computed by `start_time` order
- feat(frontend): Timeline/Waterfall View — Gantt-chart visualization of trace spans with wall-clock positioning, parallel span detection (separate swim-lane rows), critical path highlighting (gold ring), hover tooltips (name/duration/cost), collapsible "Slowest Spans" summary panel, and Graph/Timeline toggle in CostSummaryBar
- refactor(frontend): extract shared span-type color constants into `lib/span-colors.ts` (reused by TraceGraph, SpanNode, and TimelineView)
- feat(frontend): URL-based routing with React Router — deep-link to `/traces/:traceId/:spanId` with full browser history support
- feat(backend): `DELETE /v1/traces/{trace_id}` — single trace deletion with CASCADE cleanup of spans and replay runs
- feat(backend): `DELETE /v1/traces` — batch delete traces by IDs or `older_than` timestamp
- feat(backend): `GET /v1/stats` — database statistics (trace/span counts, DB size, oldest trace)
- feat(backend): `GET /v1/search?q=` — full-text search across span names, attributes, and trace names
- feat(frontend): Trace deletion UI — trash icon with inline confirm on trace list items, "Clear All Traces" in Settings
- feat(frontend): Search bar with debounced dropdown results navigating to matched trace/span
- feat(frontend): Data Management section in Settings — stats display and bulk trace cleanup
- feat(backend): SQLite `PRAGMA foreign_keys=ON` enforcement for CASCADE deletes
- feat(sdk): file operation auto-patch (`integrations/file_patch.py`) — patches `builtins.open` to create `file_operation` spans with `file.path`, `file.operation`, `file.size_bytes`, and `file.content` (truncated to 2000 chars); opt-in via `BEACON_PATCH_FILE_OPS=true` env var

### Changed
- feat(frontend): Linear-inspired UI polish — dark-themed thin scrollbars, hairline `0.5px` borders, card elevation shadows, refined typography (`text-[13px]` body, `text-[11px] uppercase` section headers), auto-resizing textarea composers, polished empty states with icons
- refactor(sdk): consolidate duplicated price tables into unified `sdk/beacon_sdk/pricing.py` with per-1M-token pricing and prefix matching for dated model names; adds missing models (gpt-4.1 family, o3, o4-mini, claude-haiku-4, o1/o1-mini)

### Added
- feat(sdk): `AsyncBatchExporter` — queues spans in memory and flushes on a background daemon thread (every 1s or 50 spans), replacing blocking per-span HTTP as the default exporter
- feat(sdk): `init(exporter=...)` parameter accepting `"sync"`, `"async"`, or `"auto"` (default, selects async)
- feat(sdk): `beacon_sdk.flush()` and `beacon_sdk.shutdown()` public helpers for manual exporter lifecycle control
- feat(sdk): `atexit` handler to flush remaining spans on process exit
- feat(sdk): `FlushableExporter` protocol for exporters with lifecycle management

### Fixed
- fix(sdk): LangChain `BeaconCallbackHandler` — update to `(span, token)` tuple API from `tracer.start_span()`, fix `end_span()` signature, add `tool.framework` and `llm.finish_reason` attributes, remove hard `langchain_core` import dependency
- test(sdk): 19 new tests for LangChain callback handler covering chain/llm/tool/agent lifecycle, parent-child nesting, and error handling

### Added
- feat(backend): Demo agents — clickable Dashboard cards that trigger real LLM calls (OpenAI/Anthropic), producing genuine traces with tool calling; 3 scenarios: Research Assistant, Code Reviewer, Trip Planner
- feat(backend): `GET /v1/demo/scenarios` — list demo scenarios with API key status
- feat(backend): `POST /v1/demo/run` — start a demo agent in background, returns trace_id immediately
- feat(backend): `call_openai_with_tools()` and `call_anthropic_with_tools()` in `llm_client.py` — tool-calling support for LLM API calls
- feat(frontend): `DemoAgents` component — demo agent cards on Dashboard with run/loading/disabled states
- feat(sdk): tool calls capture — serialize OpenAI `tool_calls` and Anthropic `tool_use` blocks into `llm.tool_calls` span attribute; render in frontend LLM detail panel
- feat(sdk): Streaming support for OpenAI and Anthropic integrations — `OpenAIStreamWrapper`, `OpenAIAsyncStreamWrapper`, `AnthropicStreamWrapper`, `AnthropicAsyncStreamWrapper` intercept streaming chunks/events to create LLM spans with accumulated completion text, token usage, cost estimation, and finish reason
- docs: expand roadmap with advisor-informed features (Phases 7–11) — trace import/export, critical path analysis, prompt versioning, OTLP ingestion, error pattern recognition, A/B prompt testing, CI/CD integration, VS Code extension
- docs: post-MVP roadmap (Phases 6–10) — production readiness, deep debugging, ecosystem expansion, AI-powered debugging, enterprise foundation
- feat(frontend): Collapsible sidebar with icon-only collapsed state and `Cmd+\` keyboard shortcut
- feat(frontend): Fullscreen canvas toggle in CostSummaryBar — hides side panels, auto-reveals span detail on node click
- feat(frontend): Draggable graph nodes, animated edges, zoom controls, double-click-to-focus, color-coded MiniMap

- feat(frontend): Linear-inspired design system — dark-first oklch color tokens with blue-purple hue, Inter Variable font at 13px base
- feat(frontend): Sidebar navigation — persistent 220px sidebar replacing tab bar (Dashboard, Traces, Playground, Settings)
- feat(frontend): DashboardPage — getting-started guide (empty state) + stats overview with recent traces (returning user)
- feat(frontend): TracesPage — extracted 3-panel debugger layout from App.tsx
- feat(frontend): PlaygroundPage — wrapper around Playground component with sidebar integration
- feat(frontend): SettingsPage — full-page API key management replacing modal dialog
- feat(frontend): Zustand navigation store for page routing (`store/navigation.ts`)
- docs: `docs/design-system.md` — living reference for colors, typography, spacing, component patterns, layout conventions

- feat(frontend): Playground tab — multi-turn chat interface with model selector, system prompt, inline cost/token/latency metrics
- feat(frontend): Multi-model comparison view — send one prompt to 2+ models, see side-by-side results with metrics
- feat(frontend): API Key management dialog — store/update/delete keys per provider with masked display
- feat(backend): `POST /v1/playground/chat` — chat with any OpenAI/Anthropic model, auto-creates traces visible in Debugger
- feat(backend): `POST /v1/playground/compare` — parallel multi-model comparison with per-model spans
- feat(backend): `GET/PUT/DELETE /v1/settings/api-keys` — API key management stored in `~/.beacon/config.json`
- feat(backend): `llm_client.py` — shared LLM calling logic with price table for cost estimation
- test(backend): 22 new tests for llm_client, settings service/router, and playground service/router
- docs(sdk): `sdk/README.md` with quickstart, integrations table, configuration, and API reference
- docs: `docs/contributing.md` with prerequisites, dev setup, code style, and PR guidelines

### Changed
- refactor(frontend): replace tab-bar navigation with sidebar + page-based routing
- refactor(frontend): remove `ApiKeyDialog` modal in favor of full `SettingsPage`
- refactor(frontend): remove `onOpenSettings` prop from Playground component
- refactor(sdk): simplify `langchain_agent.py` example from 99 to 47 lines using `create_tool_calling_agent`
- docs: update roadmap, README, AGENTS.md, frontend.md, CLAUDE.md for Phase 5
- docs: mark sdk/README.md, contributing.md, and examples as complete in roadmap

### Fixed
- fix(frontend): SpanNode graph colors — replaced light-mode-only styles with dark-friendly alternatives
- fix(frontend): React Flow graph background set to dark color mode
- fix(frontend): Settings page API key overflow — masked key and buttons stay within card boundaries
- fix(frontend): surface replay errors to user instead of silently swallowing them
- fix(frontend): key ReplayPanel by span_id to prevent stale content when switching spans
- fix(frontend): guard `.toFixed()` on potentially undefined cost value in ReplayPanel
- fix(frontend): validate URL protocol in BrowserDetail to prevent javascript: XSS
- fix(frontend): use switch statement in SpanDetail dispatcher for maintainability
- fix(backend): document OPENAI_API_KEY and ANTHROPIC_API_KEY in .env.example

### Changed
- docs: mark Phase 1, Phase 2, and Phase 3 as complete in roadmap
- docs: update README status banner and roadmap summary
- test(backend): add Anthropic provider replay test

### Added
- feat(sdk): OpenAI auto-instrumentation (`integrations/openai.py`) — patches `Completions.create` to create LLM spans with token/cost tracking
- feat(sdk): Anthropic auto-instrumentation (`integrations/anthropic.py`) — patches `Messages.create` with prefix-based cost estimation
- feat(sdk): Playwright auto-instrumentation (`integrations/playwright.py`) — patches Page methods (goto, click, fill, type, screenshot, wait_for_selector) to create browser_action spans
- feat(sdk): Subprocess auto-instrumentation (`integrations/subprocess_patch.py`) — patches `subprocess.run` and `check_output` to create shell_command spans
- feat(sdk): `auto_patch` parameter on `beacon_sdk.init()` with `BEACON_AUTO_PATCH` env var support
- feat(sdk): Optional dependency extras in pyproject.toml (`beacon-sdk[openai]`, `[anthropic]`, `[playwright]`, `[all]`)
- feat(sdk): `browser_agent.py` example demonstrating Playwright auto-instrumentation end-to-end
- test(sdk): 40 new integration tests across OpenAI, Anthropic, Playwright, and subprocess integrations
- feat(frontend): Loading skeletons for TraceList and TraceGraph during data fetch
- feat(frontend): Backend-unreachable error banner with dismiss button
- feat(frontend): Screenshot display in BrowserDetail (base64 PNG rendering)
- feat(frontend): Cost/token summary bar above TraceGraph (name, tokens, cost, duration, span count)
- feat(frontend): Trace search/filter by name and status (all/ok/error/running)
- feat(frontend): Resizable three-panel layout with drag handles (`useResizablePanels` hook)
- feat(frontend): Type-specific SpanDetail panel — `LlmCallDetail` (prompt/completion/tokens/cost), `ToolUseDetail` (input/output JSON), `BrowserDetail` (action/URL/selector), `GenericDetail` (grouped attributes)
- feat(frontend): Prompt Editor with Monaco Editor (`@monaco-editor/react`) for editing LLM prompts in JSON mode
- feat(frontend): Replay UI — edit prompt, click Replay, see side-by-side diff of original vs replayed completion with token/cost comparison
- feat(frontend): Time-Travel debugging slider with keyboard support (Left/Right arrows), auto-selects span at current step
- feat(backend): `POST /v1/replay` endpoint — replays LLM calls via OpenAI/Anthropic HTTP APIs with modified prompts
- feat(backend): `replay_service.py` with cost estimation price table, diff generation, and replay result persistence
- test(backend): 4 pytest tests for replay (validation, mock LLM call, DB persistence)
- feat: root Makefile for dev workflow (install, dev, stop, test, lint, format, clean, db-reset)
- feat(frontend): Vite + React 19 + TypeScript frontend with three-panel layout (TraceList, TraceGraph, SpanDetail)
- feat(frontend): React Flow graph visualization with dagre auto-layout, color-coded span nodes by type, time-travel dimming
- feat(frontend): Zustand store for trace/span state management, WebSocket client with exponential-backoff reconnect
- feat(backend): Trace listing (`GET /v1/traces`), detail (`GET /v1/traces/{id}`), and graph (`GET /v1/traces/{id}/graph`) endpoints
- feat(backend): WebSocket subscription filtering (`subscribe_trace`/`unsubscribe_trace`), `broadcast_span_updated` event
- feat(sdk): LangChain `BeaconCallbackHandler` integration mapping chain/llm/tool/agent callbacks to Beacon spans
- feat(sdk): `langchain_agent.py` example demonstrating ReAct agent instrumentation
- feat(backend): Standalone mock server (`backend/mock_server.py`) for frontend development without backend dependencies
- test(backend): 11 pytest tests for trace listing, detail, graph, status filtering
- feat(backend): FastAPI backend with span ingestion (`POST /v1/spans`), span detail (`GET /v1/spans/{id}`), health check, SQLAlchemy models (Trace, Span, ReplayRun), WebSocket manager for real-time broadcasting
- feat(sdk): `beacon-sdk` Python package with `@observe` decorator (sync + async), `BeaconTracer`, `HttpSpanExporter`, ContextVar-based trace context propagation
- feat(sdk): `hello_world.py` example for end-to-end validation
- test(backend): 14 pytest tests for span ingestion, trace upsert, error handling
- test(sdk): 40 pytest tests covering models, context, tracer, decorators, exporters
- Initial project documentation: architecture, data model, API contracts, SDK design, backend design, frontend design, roadmap, conventions
- `AGENTS.md` — primary AI agent instruction file (Codex/Claude/Gemini compatible)
- `CLAUDE.md` — Claude Code session bootstrap (points to AGENTS.md)
- `VISION.md` — project philosophy and north-star question
- `SECURITY.md` — vulnerability reporting policy
- `.gitignore` — Python, Node, macOS, secrets
- `.env.example` — documented environment variables
- GitHub issue templates (bug report, feature request)
- GitHub PR template
- `.agents/skills/` — three-phase PR workflow (review → prepare → merge)
- `.claude/commands/` — Claude Code slash commands for PR workflow
- Pre-commit hooks (`.pre-commit-config.yaml` + `git-hooks/pre-commit`)
- `.vscode/` — shared editor settings and extension recommendations

---

<!-- Versions will be added here as they are released -->
