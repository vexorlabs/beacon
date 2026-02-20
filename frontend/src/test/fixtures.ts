import type {
  GraphData,
  GraphNode,
  Span,
  SpanStatus,
  SpanType,
  TraceSummary,
  TraceDetail,
} from "@/lib/types";

let idCounter = 0;

function nextId(): string {
  idCounter += 1;
  return `test-${idCounter}`;
}

export function makeSpan(overrides: Partial<Span> = {}): Span {
  const id = nextId();
  return {
    span_id: `span-${id}`,
    trace_id: `trace-${id}`,
    parent_span_id: null,
    span_type: "llm_call" as SpanType,
    name: `test-span-${id}`,
    status: "ok" as SpanStatus,
    error_message: null,
    start_time: 1700000000,
    end_time: 1700000001,
    attributes: {},
    ...overrides,
  };
}

export function makeTrace(overrides: Partial<TraceSummary> = {}): TraceSummary {
  const id = nextId();
  return {
    trace_id: `trace-${id}`,
    name: `test-trace-${id}`,
    start_time: 1700000000,
    end_time: 1700000005,
    duration_ms: 5000,
    span_count: 3,
    status: "ok" as SpanStatus,
    total_cost_usd: 0.005,
    total_tokens: 500,
    tags: {},
    ...overrides,
  };
}

export function makeTraceDetail(
  overrides: Partial<TraceDetail> = {},
): TraceDetail {
  const base = makeTrace(overrides);
  return {
    ...base,
    spans: overrides.spans ?? [makeSpan({ trace_id: base.trace_id })],
  };
}

export function makeGraphData(nodeCount = 2): GraphData {
  const nodes: GraphNode[] = Array.from({ length: nodeCount }, (_, i) => ({
    id: `span-node-${i}`,
    type: "spanNode" as const,
    data: {
      span_id: `span-node-${i}`,
      span_type: "llm_call" as SpanType,
      name: `node-${i}`,
      status: "ok" as SpanStatus,
      duration_ms: 100,
      cost_usd: 0.001,
      sequence: i + 1,
    },
    position: { x: 0, y: i * 100 },
  }));

  const edges =
    nodeCount > 1
      ? [{ id: "edge-0-1", source: nodes[0].id, target: nodes[1].id }]
      : [];

  return { nodes, edges };
}

/** Reset the ID counter between tests */
export function resetFixtures(): void {
  idCounter = 0;
}
