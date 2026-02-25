import type {
  AnomalyDetectionResponse,
  Annotation,
  ApiKeyStatus,
  CompareAnalysisResponse,
  CostOptimizationResponse,
  DemoRunResponse,
  DemoScenario,
  ErrorPatternsResponse,
  GraphData,
  PlaygroundChatResponse,
  PlaygroundComparePromptsResponse,
  PlaygroundCompareResponse,
  PlaygroundMessage,
  PromptSuggestionsResponse,
  PromptVersion,
  PromptVersionListResponse,
  ReplayResult,
  RootCauseAnalysisResponse,
  SearchResponse,
  Span,
  StatsResponse,
  TopCostsResponse,
  TopDurationResponse,
  TraceDetail,
  TraceExportData,
  TraceImportResponse,
  TraceSummary,
  TraceSummaryAnalysisResponse,
  TracesResponse,
  TrendsResponse,
} from "./types";

const BASE_URL = "/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String(body.detail)
        : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function getTraces(params?: {
  limit?: number;
  offset?: number;
  status?: string;
}): Promise<TracesResponse> {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined)
    search.set("offset", String(params.offset));
  if (params?.status !== undefined) search.set("status", params.status);
  const qs = search.toString();
  return apiFetch<TracesResponse>(`/traces${qs ? `?${qs}` : ""}`);
}

export function getTrace(traceId: string): Promise<TraceDetail> {
  return apiFetch<TraceDetail>(`/traces/${traceId}`);
}

export function getTraceGraph(traceId: string): Promise<GraphData> {
  return apiFetch<GraphData>(`/traces/${traceId}/graph`);
}

export function getSpan(spanId: string): Promise<Span> {
  return apiFetch<Span>(`/spans/${spanId}`);
}

export function postReplay(request: {
  span_id: string;
  modified_attributes: Record<string, unknown>;
}): Promise<ReplayResult> {
  return apiFetch<ReplayResult>("/replay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

// --- Settings ---

export function getApiKeys(): Promise<ApiKeyStatus[]> {
  return apiFetch<ApiKeyStatus[]>("/settings/api-keys");
}

export function setApiKey(
  provider: string,
  apiKey: string,
): Promise<{ provider: string; configured: boolean }> {
  return apiFetch("/settings/api-keys", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
}

export function deleteApiKey(
  provider: string,
): Promise<{ provider: string; configured: boolean }> {
  return apiFetch(`/settings/api-keys/${provider}`, { method: "DELETE" });
}

// --- Playground ---

export function playgroundChat(request: {
  conversation_id: string | null;
  model: string;
  system_prompt?: string;
  messages: PlaygroundMessage[];
}): Promise<PlaygroundChatResponse> {
  return apiFetch<PlaygroundChatResponse>("/playground/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function playgroundCompare(request: {
  messages: PlaygroundMessage[];
  system_prompt?: string;
  models: string[];
}): Promise<PlaygroundCompareResponse> {
  return apiFetch<PlaygroundCompareResponse>("/playground/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function playgroundComparePrompts(request: {
  model: string;
  system_prompt?: string;
  prompts: string[];
}): Promise<PlaygroundComparePromptsResponse> {
  return apiFetch<PlaygroundComparePromptsResponse>("/playground/compare-prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

// --- Demo agents ---

export function getDemoScenarios(): Promise<DemoScenario[]> {
  return apiFetch<DemoScenario[]>("/demo/scenarios");
}

export function runDemoAgent(scenario: string): Promise<DemoRunResponse> {
  return apiFetch<DemoRunResponse>("/demo/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
}

// --- Trace deletion ---

export function deleteTrace(traceId: string): Promise<{ deleted_count: number }> {
  return apiFetch(`/traces/${traceId}`, { method: "DELETE" });
}

export function deleteAllTraces(): Promise<{ deleted_count: number }> {
  // Use a far-future timestamp to match all existing traces
  const farFuture = Math.floor(Date.now() / 1000) + 999999;
  return apiFetch("/traces", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ older_than: farFuture }),
  });
}

// --- Stats ---

export function getStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>("/stats");
}

// --- Dashboard analytics ---

export function getTrends(params?: {
  days?: number;
  bucket?: "day" | "hour";
}): Promise<TrendsResponse> {
  const search = new URLSearchParams();
  if (params?.days !== undefined) search.set("days", String(params.days));
  if (params?.bucket !== undefined) search.set("bucket", params.bucket);
  const qs = search.toString();
  return apiFetch<TrendsResponse>(`/stats/trends${qs ? `?${qs}` : ""}`);
}

export function getTopCosts(limit?: number): Promise<TopCostsResponse> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch<TopCostsResponse>(`/stats/top-costs${qs}`);
}

export function getTopDuration(limit?: number): Promise<TopDurationResponse> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch<TopDurationResponse>(`/stats/top-duration${qs}`);
}

export function detectAnomalies(
  traceId: string,
): Promise<AnomalyDetectionResponse> {
  return apiFetch<AnomalyDetectionResponse>("/analysis/anomalies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId }),
  });
}

// --- Analysis ---

export function analyzeRootCause(
  traceId: string,
): Promise<RootCauseAnalysisResponse> {
  return apiFetch<RootCauseAnalysisResponse>("/analysis/root-cause", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId }),
  });
}

export function analyzeCostOptimization(
  traceIds: string[],
): Promise<CostOptimizationResponse> {
  return apiFetch<CostOptimizationResponse>("/analysis/cost-optimization", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_ids: traceIds }),
  });
}

export function analyzePromptSuggestions(
  spanId: string,
): Promise<PromptSuggestionsResponse> {
  return apiFetch<PromptSuggestionsResponse>("/analysis/prompt-suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ span_id: spanId }),
  });
}

export function analyzeErrorPatterns(
  traceIds: string[],
): Promise<ErrorPatternsResponse> {
  return apiFetch<ErrorPatternsResponse>("/analysis/error-patterns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_ids: traceIds }),
  });
}

export function summarizeTrace(
  traceId: string,
): Promise<TraceSummaryAnalysisResponse> {
  return apiFetch<TraceSummaryAnalysisResponse>("/analysis/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId }),
  });
}

export function compareAnalysis(
  traceIdA: string,
  traceIdB: string,
): Promise<CompareAnalysisResponse> {
  return apiFetch<CompareAnalysisResponse>("/analysis/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id_a: traceIdA, trace_id_b: traceIdB }),
  });
}

// --- Baseline ---

export function findBaselineTrace(
  excludeTraceId?: string,
): Promise<TraceSummary | null> {
  const qs = excludeTraceId ? `?exclude=${excludeTraceId}` : "";
  return apiFetch<TraceSummary | null>(`/traces/baseline${qs}`);
}

// --- Export / Import ---

export async function exportTrace(
  traceId: string,
  format: "json" | "otel" | "csv",
): Promise<Blob> {
  const res = await fetch(
    `${BASE_URL}/traces/${traceId}/export?format=${format}`,
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String(body.detail)
        : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.blob();
}

export function importTrace(
  data: TraceExportData,
): Promise<TraceImportResponse> {
  return apiFetch<TraceImportResponse>("/traces/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// --- Tags & Annotations ---

export function updateTraceTags(
  traceId: string,
  tags: Record<string, string>,
): Promise<{ trace_id: string; tags: Record<string, string> }> {
  return apiFetch(`/traces/${traceId}/tags`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tags }),
  });
}

export function updateSpanAnnotations(
  spanId: string,
  annotations: Annotation[],
): Promise<{ span_id: string; annotations: Annotation[] }> {
  return apiFetch(`/spans/${spanId}/annotations`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ annotations }),
  });
}

// --- Search ---

export function searchTraces(
  query: string,
  params?: { limit?: number; offset?: number },
): Promise<SearchResponse> {
  const search = new URLSearchParams({ q: query });
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined) search.set("offset", String(params.offset));
  return apiFetch<SearchResponse>(`/search?${search.toString()}`);
}

// --- Prompt versions ---

export function getPromptVersions(
  spanId: string,
): Promise<PromptVersionListResponse> {
  return apiFetch<PromptVersionListResponse>(
    `/spans/${spanId}/prompt-versions`,
  );
}

export function createPromptVersion(
  spanId: string,
  promptText: string,
  label?: string,
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(`/spans/${spanId}/prompt-versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt_text: promptText, label }),
  });
}
