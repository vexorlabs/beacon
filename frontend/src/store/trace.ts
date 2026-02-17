import { create } from "zustand";
import { getTrace, getTraceGraph, getTraces, postReplay } from "@/lib/api";
import type {
  GraphData,
  GraphEdge,
  GraphNode,
  ReplayResult,
  Span,
  TraceSummary,
  TraceDetail,
} from "@/lib/types";

interface TraceStore {
  traces: TraceSummary[];
  isLoadingTraces: boolean;
  selectedTraceId: string | null;
  selectedTrace: TraceDetail | null;
  isLoadingTrace: boolean;
  graphData: GraphData | null;
  selectedSpanId: string | null;
  selectedSpan: Span | null;
  timeTravelIndex: number | null;
  replayResult: ReplayResult | null;
  isReplaying: boolean;
  replayError: string | null;

  loadTraces: () => Promise<void>;
  selectTrace: (traceId: string) => Promise<void>;
  selectSpan: (spanId: string) => void;
  setTimeTravelIndex: (index: number | null) => void;
  runReplay: (
    spanId: string,
    modifiedAttributes: Record<string, unknown>,
  ) => Promise<void>;
  clearReplay: () => void;
  appendSpan: (span: Span) => void;
  prependTrace: (trace: TraceSummary) => void;
}

export const useTraceStore = create<TraceStore>((set, get) => ({
  traces: [],
  isLoadingTraces: false,
  selectedTraceId: null,
  selectedTrace: null,
  isLoadingTrace: false,
  graphData: null,
  selectedSpanId: null,
  selectedSpan: null,
  timeTravelIndex: null,
  replayResult: null,
  isReplaying: false,
  replayError: null,

  loadTraces: async () => {
    set({ isLoadingTraces: true });
    try {
      const res = await getTraces({ limit: 50 });
      set({ traces: res.traces });
    } catch {
      // API error — keep stale traces so the UI doesn't flash empty
    } finally {
      set({ isLoadingTraces: false });
    }
  },

  selectTrace: async (traceId: string) => {
    set({
      selectedTraceId: traceId,
      isLoadingTrace: true,
      selectedSpanId: null,
      selectedSpan: null,
      timeTravelIndex: null,
    });
    try {
      const [traceDetail, graphData] = await Promise.all([
        getTrace(traceId),
        getTraceGraph(traceId),
      ]);
      set({ selectedTrace: traceDetail, graphData });
    } catch {
      set({ selectedTrace: null, graphData: null });
    } finally {
      set({ isLoadingTrace: false });
    }
  },

  selectSpan: (spanId: string) => {
    const { selectedTrace } = get();
    const span =
      selectedTrace?.spans.find((s) => s.span_id === spanId) ?? null;
    set({ selectedSpanId: spanId, selectedSpan: span });
  },

  setTimeTravelIndex: (index: number | null) => {
    set({ timeTravelIndex: index });
    const { graphData, selectedTrace } = get();
    if (index !== null && graphData && index < graphData.nodes.length) {
      const nodeAtIndex = graphData.nodes[index];
      const span =
        selectedTrace?.spans.find((s) => s.span_id === nodeAtIndex.id) ?? null;
      set({ selectedSpanId: nodeAtIndex.id, selectedSpan: span });
    }
  },

  runReplay: async (spanId, modifiedAttributes) => {
    set({ isReplaying: true, replayResult: null, replayError: null });
    try {
      const result = await postReplay({
        span_id: spanId,
        modified_attributes: modifiedAttributes,
      });
      set({ replayResult: result });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Replay failed";
      set({ replayResult: null, replayError: message });
    } finally {
      set({ isReplaying: false });
    }
  },

  clearReplay: () => {
    set({ replayResult: null, replayError: null });
  },

  appendSpan: (span: Span) => {
    const { selectedTraceId, selectedTrace, graphData } = get();

    // Update span count in trace list
    set({
      traces: get().traces.map((t) =>
        t.trace_id === span.trace_id
          ? { ...t, span_count: t.span_count + 1 }
          : t,
      ),
    });

    // If this span belongs to the selected trace, update graph and detail
    if (span.trace_id === selectedTraceId && selectedTrace && graphData) {
      const newNode: GraphNode = {
        id: span.span_id,
        type: "spanNode",
        data: {
          span_id: span.span_id,
          span_type: span.span_type,
          name: span.name,
          status: span.status,
          duration_ms:
            span.end_time !== null
              ? (span.end_time - span.start_time) * 1000
              : null,
          cost_usd:
            typeof span.attributes["llm.cost_usd"] === "number"
              ? span.attributes["llm.cost_usd"]
              : null,
        },
        position: { x: 0, y: 0 },
      };

      const newEdges: GraphEdge[] = span.parent_span_id
        ? [
            {
              id: `edge-${span.parent_span_id}-${span.span_id}`,
              source: span.parent_span_id,
              target: span.span_id,
            },
          ]
        : [];

      set({
        selectedTrace: {
          ...selectedTrace,
          spans: [...selectedTrace.spans, span],
        },
        graphData: {
          nodes: [...graphData.nodes, newNode],
          edges: [...graphData.edges, ...newEdges],
        },
      });
    }
  },

  prependTrace: (trace: TraceSummary) => {
    set({ traces: [trace, ...get().traces] });
  },
}));
