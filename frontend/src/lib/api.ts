import type { GraphData, Span, TraceDetail, TracesResponse } from "./types";

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
