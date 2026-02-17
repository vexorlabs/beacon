// TypeScript interfaces mirroring backend Pydantic schemas.
// Source of truth: docs/api-contracts.md + docs/data-model.md

export type SpanType =
  | "llm_call"
  | "tool_use"
  | "agent_step"
  | "browser_action"
  | "file_operation"
  | "shell_command"
  | "chain"
  | "custom";

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

export interface TraceDetail extends TraceSummary {
  spans: Span[];
}

export interface SpanNodeData {
  [key: string]: unknown; // Required by React Flow's Record<string, unknown> constraint
  span_id: string;
  span_type: SpanType;
  name: string;
  status: SpanStatus;
  duration_ms: number | null;
  cost_usd: number | null;
}

export interface GraphNode {
  id: string;
  type: "spanNode";
  data: SpanNodeData;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface TracesResponse {
  traces: TraceSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReplayResult {
  replay_id: string;
  original_span_id: string;
  new_output: {
    "llm.completion": string;
    "llm.tokens.input": number;
    "llm.tokens.output": number;
    "llm.cost_usd": number;
  };
  diff: {
    old_completion: string;
    new_completion: string;
    changed: boolean;
  };
}

// --- Settings types ---

export interface ApiKeyStatus {
  provider: string;
  configured: boolean;
  masked_key: string | null;
}

// --- Playground types ---

export interface PlaygroundMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface PlaygroundChatMetrics {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface PlaygroundChatResponse {
  conversation_id: string;
  trace_id: string;
  message: PlaygroundMessage;
  metrics: PlaygroundChatMetrics;
}

export interface CompareResultItem {
  model: string;
  provider: string;
  completion: string;
  metrics: PlaygroundChatMetrics;
}

export interface PlaygroundCompareResponse {
  trace_id: string;
  results: CompareResultItem[];
}

// --- WebSocket types ---

export type WsEvent =
  | { event: "span_created"; span: Span }
  | {
      event: "span_updated";
      span_id: string;
      updates: Partial<Pick<Span, "end_time" | "status">>;
    }
  | {
      event: "trace_created";
      trace: Pick<TraceSummary, "trace_id" | "name" | "start_time" | "status">;
    };
