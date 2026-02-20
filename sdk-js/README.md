# Beacon JS/TS SDK

JavaScript/TypeScript SDK for [Beacon](https://github.com/your-org/beacon) — the open-source, local-first debugging platform for AI agents.

## Quickstart

```bash
npm install beacon-sdk
```

```typescript
import { init, observe } from "beacon-sdk";

// Initialize — connects to Beacon backend at localhost:7474
init();

// Auto-patches OpenAI, Anthropic, and Vercel AI SDK
// All LLM calls are traced automatically

// Wrap your own functions with observe()
const myAgent = observe({ name: "my-agent", spanType: "agent_step" }, async () => {
  // Your agent logic here
  // Any OpenAI/Anthropic calls inside are automatically traced
});

await myAgent();
```

## Configuration

`init()` accepts options or reads from environment variables:

```typescript
init({
  backendUrl: "http://localhost:7474",  // BEACON_BACKEND_URL
  enabled: true,                        // BEACON_ENABLED
  autoPatch: true,                      // BEACON_AUTO_PATCH
});
```

| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `backendUrl` | `BEACON_BACKEND_URL` | `http://localhost:7474` | Beacon backend URL |
| `enabled` | `BEACON_ENABLED` | `true` | Enable/disable tracing |
| `autoPatch` | `BEACON_AUTO_PATCH` | `true` | Auto-patch LLM provider SDKs |

## Auto-Patching

When `autoPatch` is enabled (default), the SDK automatically instruments:

- **OpenAI** (`openai` npm package) — `chat.completions.create()` with streaming and tool calls
- **Anthropic** (`@anthropic-ai/sdk`) — `messages.create()` with streaming and tool use
- **Vercel AI SDK** (`ai`) — `generateText()` and `streamText()`

Each call creates an `llm_call` span with attributes:
- `llm.provider` — openai, anthropic, etc.
- `llm.model` — gpt-4o, claude-sonnet-4-20250514, etc.
- `llm.prompt` — input messages as JSON
- `llm.completion` — output text
- `llm.tokens.input`, `llm.tokens.output`, `llm.tokens.total`
- `llm.cost_usd` — estimated cost
- `llm.tool_calls` — tool calls as JSON (if any)

## `observe()` — Manual Instrumentation

Wrap functions to create spans:

```typescript
import { observe } from "beacon-sdk";

// Simple: uses function name
const traced = observe(myFunction);

// With options
const traced = observe({ name: "custom-name", spanType: "agent_step" }, async () => {
  // ...
});
```

Span types: `llm_call`, `tool_use`, `agent_step`, `browser_action`, `file_operation`, `shell_command`, `chain`, `custom`

## Flushing and Shutdown

The SDK batches spans and flushes every second. For scripts that exit quickly:

```typescript
import { flush, shutdown } from "beacon-sdk";

// Flush pending spans (returns a promise)
await flush();

// Shutdown: flush + stop background timer
await shutdown();
```

## Requirements

- Node.js 18+ (uses built-in `fetch`, `crypto.randomUUID`, `AsyncLocalStorage`)
- Zero runtime dependencies
- Optional peer dependencies: `openai`, `@anthropic-ai/sdk`, `ai`

## Development

```bash
# Install
npm install

# Run tests
npm test

# Type-check
npm run typecheck
```

## Architecture

The SDK mirrors the Python SDK (`sdk/beacon_sdk/`) architecture:

| Module | Description |
|--------|-------------|
| `models.ts` | `Span` class, `SpanType`/`SpanStatus` constants |
| `tracer.ts` | `BeaconTracer` — span lifecycle management |
| `exporter.ts` | `BatchExporter` — batches and POSTs spans to backend |
| `context.ts` | `AsyncLocalStorage`-based context propagation |
| `pricing.ts` | LLM cost estimation table |
| `decorators.ts` | `observe()` higher-order function |
| `integrations/` | Auto-patching for OpenAI, Anthropic, Vercel AI |

All spans include `sdk_language: "javascript"` so the Beacon UI can display language badges.
