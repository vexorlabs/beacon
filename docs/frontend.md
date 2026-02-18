# Frontend Design

The `beacon-ui` is a Vite + React + TypeScript application. It is the developer's primary interface for viewing and debugging agent traces.

**Location in repo:** `frontend/`
**Runs on:** `http://localhost:5173` (Vite default)
**Communicates with:** `beacon-backend` at `http://localhost:7474`

---

## Directory Structure

```
frontend/
├── src/
│   ├── main.tsx                    # React entry point
│   ├── App.tsx                     # Root layout: Sidebar + page routing
│   ├── index.css                   # Design system tokens (oklch colors, typography, spacing)
│   │
│   ├── components/
│   │   ├── ui/                     # shadcn/ui copy-pasted components (DO NOT edit)
│   │   │   ├── button.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── separator.tsx
│   │   │   └── ...
│   │   │
│   │   ├── Sidebar/                # Persistent left sidebar navigation
│   │   │   └── index.tsx
│   │   │
│   │   ├── TraceList/              # Trace list panel (used in TracesPage)
│   │   │   ├── index.tsx
│   │   │   ├── TraceListItem.tsx
│   │   │   └── TraceFilter.tsx
│   │   │
│   │   ├── TraceGraph/             # Graph panel (used in TracesPage)
│   │   │   ├── index.tsx
│   │   │   ├── SpanNode.tsx
│   │   │   └── useGraphLayout.ts
│   │   │
│   │   ├── SpanDetail/             # Span detail panel (used in TracesPage)
│   │   │   ├── index.tsx
│   │   │   ├── LlmCallDetail.tsx
│   │   │   ├── ToolUseDetail.tsx
│   │   │   ├── BrowserDetail.tsx
│   │   │   ├── PromptEditor.tsx
│   │   │   └── ReplayPanel.tsx
│   │   │
│   │   ├── Playground/             # Chat + Compare mode components
│   │   │   ├── index.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── CompareView.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── ModelSelector.tsx
│   │   │
│   │   └── TimeTravel/             # Time-travel slider
│   │       └── index.tsx
│   │
│   ├── pages/                      # Page-level components
│   │   ├── DashboardPage.tsx       # Getting-started guide + stats overview
│   │   ├── TracesPage.tsx          # 3-panel debugger layout
│   │   ├── PlaygroundPage.tsx      # Playground wrapper
│   │   └── SettingsPage.tsx        # API key management
│   │
│   ├── lib/
│   │   ├── api.ts                  # REST API client (fetch wrappers)
│   │   ├── ws.ts                   # WebSocket client + reconnect logic
│   │   ├── types.ts                # TypeScript interfaces mirroring backend schemas
│   │   ├── utils.ts                # Utility functions (cn for classname merging)
│   │   └── useResizablePanels.ts   # Custom hook for resizable panel state
│   │
│   └── store/
│       ├── trace.ts                # Zustand store (traces, spans, graph, time-travel, replay)
│       ├── playground.ts           # Zustand store (chat, compare, messages)
│       └── navigation.ts          # Zustand store (page routing)
│
├── index.html
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## Layout

The UI uses a sidebar + content panel layout inspired by Linear:

```
┌── Sidebar ──┬── Main Content ─────────────────────────┐
│             │                                          │
│  Beacon     │  ┌─ Page Content ─────────────────────┐  │
│             │  │                                     │  │
│  Dashboard  │  │  (varies by page)                   │  │
│  Traces  *  │  │                                     │  │
│  Playground │  │  Traces page uses 3-panel layout:   │  │
│  Settings   │  │  TraceList | TraceGraph | SpanDetail │  │
│             │  │                                     │  │
│             │  └─────────────────────────────────────┘  │
│   220px     │           bordered, rounded panel         │
└─────────────┴──────────────────────────────────────────┘
```

The main content area is a bordered, rounded container with a subtle shadow (Linear-style inset panel). The sidebar has no border — the contrast between sidebar background and content panel provides visual separation.

### Traces Page (3-panel debugger)

```
┌──────────────┬──────────────────────────┬──────────────┐
│              │                          │              │
│  TraceList   │      TraceGraph          │  SpanDetail  │
│  (left)      │      (center)            │  (right)     │
│  ~280px      │      flex-grow           │  ~380px      │
│              │                          │              │
│              │                          │              │
├──────────────┴──────────────────────────┴──────────────┤
│                    TimeTravel (bottom)  ~48px           │
└────────────────────────────────────────────────────────┘
```

All three panels are resizable via drag handles.

### Navigation

Page routing uses a Zustand store (`store/navigation.ts`) — no React Router. Four pages: `dashboard`, `traces`, `playground`, `settings`.

---

## Design System

See `docs/design-system.md` for the full reference. Key points:

- **Dark-first** — oklch color tokens with blue-purple hue (272)
- **Inter Variable** font at 13px base
- **Linear-inspired** — subtle borders, muted backgrounds, accent blue-purple for CTAs
- All colors are CSS custom properties consumed by Tailwind and shadcn/ui components

---

## State Management (Zustand)

Three Zustand stores:

- `store/trace.ts` — Trace, span, graph, time-travel, and replay state
- `store/playground.ts` — Chat messages, model selection, compare mode
- `store/navigation.ts` — Page routing (`currentPage`, `navigate()`)

`store/trace.ts` holds:

```typescript
interface TraceStore {
  // Trace list
  traces: TraceSummary[];
  isLoadingTraces: boolean;

  // Selected trace
  selectedTraceId: string | null;
  selectedTrace: TraceDetail | null;
  isLoadingTrace: boolean;

  // Selected span (for SpanDetail panel)
  selectedSpanId: string | null;
  selectedSpan: Span | null;

  // Time-travel
  timeTravelIndex: number | null;  // null = latest (live)

  // Actions
  selectTrace: (traceId: string) => Promise<void>;
  selectSpan: (spanId: string) => void;
  setTimeTravelIndex: (index: number | null) => void;

  // WebSocket-driven updates
  appendSpan: (span: Span) => void;
}
```

---

## Component Responsibilities

### `TraceList`

Left panel. Shows all traces sorted newest-first.

Each row shows:
- Trace name
- Start time (relative: "2 min ago")
- Duration
- Span count
- Status badge (green = ok, red = error, gray = in progress)
- Total cost (if LLM calls present)

Click a row → calls `store.selectTrace(traceId)`.

Receives real-time updates via WebSocket: when a new trace appears, it is prepended to the list without a full re-fetch.

### `TraceGraph`

Center panel. Renders the selected trace as an interactive React Flow graph.

**Node types:**
- `spanNode` — The only custom node type. Renders differently based on `span_type`.
  - `llm_call` → blue, shows model name + token count
  - `tool_use` → green, shows tool name
  - `browser_action` → orange, shows action + URL
  - `file_operation` → yellow, shows operation + path
  - `shell_command` → purple, shows command snippet
  - `agent_step` / `chain` → gray, shows step name
  - Error status → red border on any node type

**Layout:** Uses `dagre` (via `@dagrejs/dagre`) for automatic top-to-bottom tree layout. The layout is computed once when the trace loads (via `useGraphLayout` hook) and not recomputed on node click.

**Interactions:**
- Click a node → `store.selectSpan(spanId)`
- Zoom / pan natively via React Flow
- Minimap (React Flow built-in) in bottom-right corner

**Time-travel:** When `store.timeTravelIndex` is set, only spans with `start_time <= trace.spans[timeTravelIndex].start_time` are shown. Nodes that are "in the future" are grayed out.

### `SpanDetail`

Right panel. Shows detail for `store.selectedSpan`.

Renders a different sub-component based on `span_type`:

| span_type | Component |
|-----------|-----------|
| `llm_call` | `LlmCallDetail` |
| `tool_use` | `ToolUseDetail` |
| `browser_action` | `BrowserDetail` |
| `file_operation` | Generic key-value attributes |
| `shell_command` | Generic + stdout/stderr code block |
| `custom` | Generic key-value attributes |

**`LlmCallDetail`** is the most important:
- Shows prompt (formatted JSON messages)
- Shows completion
- Shows tokens, cost, model, finish reason
- Has an "Edit & Replay" button that opens `PromptEditor`

**`PromptEditor`** (inside SpanDetail for `llm_call` spans):
- Monaco Editor with `json` language mode for the prompt messages
- "Replay" button → calls `POST /v1/replay` via API client
- Shows a diff view of old vs. new completion on success
- Shows error toast on failure

**`BrowserDetail`:**
- Shows action type, URL, selector
- If `browser.screenshot` is present: shows the screenshot image inline

### `TimeTravel`

Bottom panel. Only visible when a trace is selected.

Shows:
- A horizontal slider across the full width
- Number of steps: `1` to `trace.spans.length` (ordered by `start_time`)
- Current step label: span name + type
- Keyboard shortcuts: Left/Right arrow keys step backward/forward

When the slider moves, `store.setTimeTravelIndex(index)` is called. `TraceGraph` reacts and grays out future nodes.

---

## API Client (`lib/api.ts`)

All requests go through a thin wrapper around `fetch`. No axios.

```typescript
const BASE_URL = "http://localhost:7474";

export async function getTraces(params?: { limit?: number; offset?: number }): Promise<TracesResponse> {
  const url = new URL(`${BASE_URL}/v1/traces`);
  if (params?.limit) url.searchParams.set("limit", String(params.limit));
  if (params?.offset) url.searchParams.set("offset", String(params.offset));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GET /v1/traces failed: ${res.status}`);
  return res.json();
}

export async function getTrace(traceId: string): Promise<TraceDetail> { ... }
export async function getTraceGraph(traceId: string): Promise<GraphData> { ... }
export async function getSpan(spanId: string): Promise<Span> { ... }
export async function replaySpan(spanId: string, modifiedAttributes: Record<string, unknown>): Promise<ReplayResult> { ... }
```

---

## WebSocket Client (`lib/ws.ts`)

Connects to `ws://localhost:7474/ws/live`. Implements:
- Auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
- Dispatches events to the Zustand store

```typescript
class BeaconWebSocket {
  connect(): void { ... }
  subscribeToTrace(traceId: string): void { ... }
  onSpanCreated(handler: (span: Span) => void): void { ... }
  onTraceCreated(handler: (trace: TraceSummary) => void): void { ... }
}
```

---

## TypeScript Types (`lib/types.ts`)

Must mirror the backend Pydantic schemas exactly. When the backend schemas change, update this file too.

```typescript
export type SpanType =
  | "llm_call" | "tool_use" | "agent_step"
  | "browser_action" | "file_operation" | "shell_command"
  | "chain" | "custom";

export type SpanStatus = "ok" | "error" | "unset";

export interface Span {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  span_type: SpanType;
  name: string;
  status: SpanStatus;
  error_message: string | null;
  start_time: number;
  end_time: number | null;
  duration_ms: number | null;
  attributes: Record<string, unknown>;
}

export interface TraceSummary {
  trace_id: string;
  name: string;
  start_time: number;
  end_time: number | null;
  duration_ms: number | null;
  span_count: number;
  status: SpanStatus;
  total_cost_usd: number;
  total_tokens: number;
  tags: Record<string, string>;
}

// ... more types
```

---

## shadcn/ui Policy

- **Never `npm install` a component library.** Use shadcn/ui copy-paste instead.
- Run `npx shadcn@latest add button` to add a component.
- All shadcn components live in `src/components/ui/`. Do not edit them.
- For custom components, create them outside `src/components/ui/`.

---

## Setup

```bash
cd frontend
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # Production build
npm run typecheck # tsc --noEmit
npm run lint      # eslint
```

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | 19.x | UI framework |
| `@xyflow/react` | latest | Graph visualization (React Flow) |
| `@monaco-editor/react` | latest | Code editor for prompt editing |
| `zustand` | 5.x | Global state management |
| `@dagrejs/dagre` | latest | Graph layout algorithm |
| `tailwindcss` | 4.x | Utility CSS |
| `typescript` | 5.x | Type safety |
| `vite` | 7.x | Dev server + build |
| `lucide-react` | latest | Icon library |

---

## Performance Notes

- **Never fetch all spans on load.** Use `/v1/traces/{id}/graph` which returns a pre-computed graph structure.
- **Virtualize the TraceList** if it exceeds 100 items (use `@tanstack/react-virtual`).
- **Don't re-render the entire graph on every WebSocket message.** React Flow handles this via memoized node/edge arrays.
- **Lazy-load Monaco Editor.** It's large. Use `React.lazy` + `Suspense` for the `PromptEditor` component.
