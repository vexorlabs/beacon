# Frontend Design

`beacon-ui` is a React + TypeScript app (Vite) for interactive trace debugging.

Location: `frontend/`
Runs on: `http://localhost:5173`
Backend: proxied to `http://localhost:7474`

---

## Tech Snapshot

- React 19
- React Router 7
- Zustand 5
- React Flow (`@xyflow/react`)
- Monaco (`@monaco-editor/react`)
- Tailwind CSS 4 + shadcn/ui

---

## Directory Structure

```text
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── TracesPage.tsx
│   │   ├── PlaygroundPage.tsx
│   │   └── SettingsPage.tsx
│   ├── components/
│   │   ├── Sidebar/
│   │   ├── TraceList/
│   │   ├── TraceGraph/
│   │   ├── SpanDetail/
│   │   ├── TimeTravel/
│   │   ├── Playground/
│   │   ├── CostSummaryBar.tsx
│   │   ├── DemoAgents.tsx
│   │   └── ErrorBanner.tsx
│   ├── store/
│   │   ├── trace.ts
│   │   ├── playground.ts
│   │   └── navigation.ts
│   └── lib/
│       ├── api.ts
│       ├── ws.ts
│       ├── types.ts
│       ├── useResizablePanels.ts
│       └── utils.ts
├── package.json
└── vite.config.ts
```

---

## Routing

Routing is handled by React Router (not Zustand page routing).

Defined routes:
- `/` -> Dashboard
- `/traces`
- `/traces/:traceId`
- `/traces/:traceId/:spanId`
- `/playground`
- `/settings`

`Sidebar` handles primary navigation and collapse state.

---

## Page Responsibilities

### Dashboard
- empty-state onboarding when no traces exist
- overview cards when traces exist (cost/tokens/duration)
- demo scenario launcher (`DemoAgents`)

### Traces
- three-panel debugger layout:
  - Trace list (left)
  - graph canvas (center)
  - span detail (right)
- draggable resize handles (`useResizablePanels`)
- optional fullscreen graph mode
- time-travel slider at bottom

### Playground
- chat mode (single model, conversation trace)
- compare mode (multi-model side-by-side)
- optional system prompt
- “View in Debugger” navigation for generated trace

### Settings
- API key management (`openai`, `anthropic`)
- stats card (`/v1/stats`)
- clear-all traces action (`DELETE /v1/traces` with `older_than`)

---

## State Management (Zustand)

### `store/trace.ts`
Owns:
- trace list + loading state
- selected trace/span
- graph data
- replay state
- backend connectivity error message
- local list filter (`status`, `nameQuery`)

Actions include:
- `loadTraces()`
- `selectTrace(traceId)`
- `selectSpan(spanId)`
- `runReplay(spanId, modifiedAttributes)`
- `appendSpan(span)` for WS events
- `deleteTrace(traceId)`

### `store/playground.ts`
Owns:
- message list + conversation state
- selected model + system prompt
- compare mode models/results
- sending/comparing/error states

### `store/navigation.ts`
Owns only sidebar collapsed state.

---

## Live Updates (WebSocket)

`App.tsx` creates one `BeaconWebSocket` client and subscribes to:
- `span_created` -> `traceStore.appendSpan`
- `trace_created` -> `traceStore.prependTrace`

WS client behavior:
- endpoint: `/ws/live` (via Vite WS proxy)
- exponential reconnect (1s -> 30s max)
- optional trace subscribe/unsubscribe actions

---

## Graph + Time Travel

`TraceGraph`:
- uses React Flow with custom node renderer (`SpanNode`)
- dagre layout via `useGraphLayout`
- node click selects span and updates URL
- node double-click focuses viewport
- minimap + controls enabled

`TimeTravel`:
- slider range `0..nodes.length`
- dims future nodes based on selected step
- keyboard step controls: left/right arrows

---

## Span Detail + Replay

`SpanDetail` dispatches by `span_type`:
- `llm_call` -> `LlmCallDetail`
- `tool_use` -> `ToolUseDetail`
- `browser_action` -> `BrowserDetail`
- fallback -> `GenericDetail`

`LlmCallDetail` includes:
- provider/model badges
- token and cost metrics
- prompt/completion display
- tool call inspection (`llm.tool_calls`)
- replay panel with Monaco editor (`PromptEditor`)

Replay call:
- `POST /v1/replay`
- request uses `modified_attributes`

---

## API Layer (`src/lib/api.ts`)

- base URL is relative: `BASE_URL = "/v1"`
- Vite proxies `/v1` -> backend in dev
- all requests use shared `apiFetch<T>()` error normalization

Available functions include:
- traces/spans/replay
- settings key CRUD
- playground chat/compare
- demo scenario list/run
- stats/search
- delete single/all traces

---

## Vite Proxy

From `vite.config.ts`:
- `/v1` -> `http://localhost:7474`
- `/ws` -> `ws://localhost:7474`

This keeps frontend code environment-agnostic in dev.

---

## Design System

Tokens and styling live in:
- `src/index.css`
- `docs/design-system.md`

Current UI is dark-first with oklch tokens and thin-border density.

---

## Setup

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
```
