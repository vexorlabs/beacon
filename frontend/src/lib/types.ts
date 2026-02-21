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

export interface Annotation {
  id: string;
  text: string;
  created_at: number;
}

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
  annotations: Annotation[];
  sdk_language?: string | null;
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
  sdk_language?: string | null;
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
  sequence: number;
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

// --- Demo agent types ---

export interface DemoScenario {
  key: string;
  name: string;
  description: string;
  provider: string;
  model: string;
  api_key_configured: boolean;
}

export interface DemoRunResponse {
  trace_id: string;
}

// --- Stats types ---

export interface StatsResponse {
  database_size_bytes: number;
  total_traces: number;
  total_spans: number;
  oldest_trace_timestamp: number | null;
}

// --- Dashboard analytics types ---

export interface TrendBucket {
  date: string;
  total_cost: number;
  total_tokens: number;
  trace_count: number;
  error_count: number;
  success_rate: number;
}

export interface TrendsResponse {
  buckets: TrendBucket[];
}

export interface TopCostItem {
  span_id: string;
  trace_id: string;
  name: string;
  model: string;
  cost: number;
  tokens: number;
}

export interface TopCostsResponse {
  prompts: TopCostItem[];
}

export interface TopDurationItem {
  span_id: string;
  trace_id: string;
  name: string;
  duration_ms: number;
}

export interface TopDurationResponse {
  tools: TopDurationItem[];
}

export interface Anomaly {
  type: string;
  severity: string;
  description: string;
  trace_id: string;
  span_id: string | null;
}

export interface AnomalyDetectionResponse {
  trace_id: string;
  anomalies: Anomaly[];
}

// --- Analysis types ---

export interface RootCauseAnalysisResponse {
  trace_id: string;
  root_cause: string;
  affected_spans: string[];
  confidence: number;
  suggested_fix: string;
}

export interface CostSuggestion {
  type: string;
  description: string;
  estimated_savings_usd: number;
  affected_spans: string[];
}

export interface CostOptimizationResponse {
  trace_ids: string[];
  suggestions: CostSuggestion[];
}

export interface PromptImprovement {
  category: string;
  description: string;
  improved_prompt_snippet: string;
}

export interface PromptSuggestionsResponse {
  span_id: string;
  original_prompt: string;
  suggestions: PromptImprovement[];
}

export interface ErrorPattern {
  pattern_name: string;
  count: number;
  example_trace_ids: string[];
  common_root_cause: string;
  category: string;
}

export interface ErrorPatternsResponse {
  patterns: ErrorPattern[];
}

export interface KeyEvent {
  span_id: string;
  description: string;
}

export interface TraceSummaryAnalysisResponse {
  trace_id: string;
  summary: string;
  key_events: KeyEvent[];
}

// --- Search types ---

export interface SearchResultItem {
  trace_id: string;
  span_id: string;
  name: string;
  match_context: string;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
}

// --- Export / Import types ---

export interface TraceExportData {
  version: string;
  format: string;
  exported_at: number;
  trace: TraceSummary;
  spans: SpanResponse[];
}

export interface SpanResponse {
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
  sdk_language?: string | null;
}

export interface TraceImportResponse {
  trace_id: string;
  span_count: number;
}

// --- Prompt version types ---

export interface PromptVersion {
  version_id: string;
  span_id: string;
  prompt_text: string;
  label: string | null;
  created_at: number;
}

export interface PromptVersionListResponse {
  versions: PromptVersion[];
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
