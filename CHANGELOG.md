# Changelog

All notable changes to Beacon will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Beacon uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [0.1.0] - 2026-02-25

Initial open-source release. Phases 1-9 of the roadmap: foundation, visualization, interactive debugging, computer-use instrumentation, UI redesign, production readiness, deep debugging, ecosystem expansion, and AI-powered debugging.

### Added

**Python SDK (`beacon-sdk`)**
- `@observe` decorator (sync + async) with `BeaconTracer`, `HttpSpanExporter`, and ContextVar-based trace context propagation
- `AsyncBatchExporter` — background daemon thread flushing every 1s or 50 spans, with `flush()`, `shutdown()`, and `atexit` handler
- Auto-instrumentation for OpenAI, Anthropic, Google Gemini (sync/async + streaming + tool calls/tool use)
- Auto-instrumentation for CrewAI (`Crew.kickoff()`), AutoGen (`ConversableAgent.generate_reply()`, `GroupChat.run()`), LlamaIndex (`BaseQueryEngine.query()`, `BaseRetriever.retrieve()`), Ollama (`chat()`, `generate()`)
- Auto-instrumentation for Playwright page actions, `subprocess.run`/`check_output`, and opt-in `builtins.open` file operations
- LangChain callback handler (`BeaconCallbackHandler`) mapping chain/llm/tool/agent callbacks to Beacon spans
- Unified pricing table (`beacon_sdk.pricing`) with per-1M-token cost estimation across all providers
- Configuration via `init()` or env vars: `BEACON_BACKEND_URL`, `BEACON_ENABLED`, `BEACON_AUTO_PATCH`, `BEACON_LOG_LEVEL`, `BEACON_PATCH_FILE_OPS`

**JS/TS SDK (`beacon-sdk` npm)**
- Full tracing SDK for Node.js 18+ with zero runtime dependencies, mirroring the Python SDK architecture
- `BeaconTracer` with `AsyncLocalStorage` context propagation, `BatchExporter`, and `observe()` wrapper
- Auto-patching for OpenAI (`chat.completions.create`), Anthropic (`messages.create`), and Vercel AI SDK (`generateText`/`streamText`) with streaming and tool call support
- LLM cost estimation table covering OpenAI, Anthropic, and Google models

**Backend**
- FastAPI backend with span ingestion (`POST /v1/spans`), trace listing/detail/graph endpoints, and WebSocket live streaming (`WS /ws/live`)
- Prompt replay (`POST /v1/replay`) via OpenAI, Anthropic, and Google APIs with diff generation and result persistence
- AI-powered analysis endpoints: root cause analysis, cost optimization, prompt suggestions, anomaly detection, error pattern recognition, AI trace comparison, and trace summarization (`POST /v1/analysis/*`)
- A/B prompt testing (`POST /v1/playground/compare-prompts`)
- Full-text search (`GET /v1/search`), trace deletion (single + batch), trace tags (`PUT /v1/traces/{id}/tags`), span annotations (`PUT /v1/spans/{id}/annotations`)
- Trace export (`GET /v1/traces/{id}/export`) in JSON, OTEL JSON, and CSV formats with bulk export support
- Trace import (`POST /v1/traces/import`) from Beacon JSON format with duplicate detection
- OTLP-compatible ingestion (`POST /v1/otlp/traces`) for OpenTelemetry interoperability
- Prompt versioning (`GET/POST /v1/spans/{id}/prompt-versions`) with auto-save on replay
- Dashboard analytics: `GET /v1/stats/trends` (time-bucketed aggregates), `GET /v1/stats/top-costs`, `GET /v1/stats/top-duration`
- Playground chat (`POST /v1/playground/chat`) and multi-model comparison (`POST /v1/playground/compare`)
- API key management (`GET/PUT/DELETE /v1/settings/api-keys`)
- Demo agent scenarios (Research Assistant, Code Reviewer, Trip Planner) with real LLM tool-calling
- Database statistics (`GET /v1/stats`), baseline trace retrieval (`GET /v1/traces/baseline`)

**Frontend**
- Three-panel Traces debugger: trace list, React Flow graph with dagre auto-layout, and type-specific span detail (LLM calls, tool use, browser actions, generic attributes)
- Timeline/waterfall view with wall-clock positioning, parallel span detection, critical path highlighting, and slowest spans summary
- Prompt editor (Monaco) with replay, side-by-side diff, live token count preview (js-tiktoken), and prompt version history
- Time-travel debugging slider with keyboard support
- AI analysis integration: Analyze dropdown with root cause, cost optimization, prompt suggestions, error patterns, summarization, and anomaly detection — with affected span highlighting
- Trace comparison page with side-by-side graphs, AI divergence detection (orange pulse markers), baseline support
- A/B prompt testing in Playground (Compare Prompts mode)
- Dashboard with recharts trend charts (cost, tokens, traces, error rate), cost forecasting, ranked tables, and anomaly alerts
- Full-text search bar with debounced results, tag-based filtering, inline tag editor, span annotations
- Trace import/export UI, trace deletion with confirmation
- URL-based routing (`/traces/:traceId/:spanId`) with React Router
- Linear-inspired design system: dark-first oklch color palette, Inter Variable font, 220px sidebar navigation
- Framework badges (LangChain, CrewAI, AutoGen, LlamaIndex, Ollama) and SDK language badges (PY/JS) in trace list and graph
- Resizable panels, collapsible sidebar (Cmd+\), fullscreen canvas, draggable graph nodes, zoom controls, minimap
- Loading skeletons, error banners, keyboard shortcuts (Cmd+0 fit, Cmd+/- zoom, Space pan)
- Vitest + React Testing Library test infrastructure with 37 tests

**Docs and Tooling**
- Architecture, API contracts, data model, SDK design, and design system documentation
- Example traces for import (`docs/example-traces/`)
- Root Makefile for dev workflow (install, dev, stop, test, lint, format, demo, clean, db-reset)
- GitHub issue templates (bug report, feature request) and PR template
- Pre-commit hooks, VS Code settings, and editor extension recommendations
- `AGENTS.md` for AI agent instructions, `VISION.md` for project philosophy
- `SECURITY.md` with vulnerability reporting policy

---

[Unreleased]: https://github.com/vexorlabs/beacon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vexorlabs/beacon/releases/tag/v0.1.0
