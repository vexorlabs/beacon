import { create } from "zustand";
import { getTrace, getTraceGraph } from "@/lib/api";
import type { GraphData, TraceDetail } from "@/lib/types";

interface CompareStore {
  compareMode: boolean;
  selectedTraceIds: string[];

  traceA: TraceDetail | null;
  traceB: TraceDetail | null;
  graphDataA: GraphData | null;
  graphDataB: GraphData | null;
  isLoading: boolean;
  error: string | null;

  toggleCompareMode: () => void;
  toggleTraceSelection: (traceId: string) => void;
  clearSelection: () => void;
  loadComparison: (traceIdA: string, traceIdB: string) => Promise<void>;
  reset: () => void;
}

export const useCompareStore = create<CompareStore>((set, get) => ({
  compareMode: false,
  selectedTraceIds: [],

  traceA: null,
  traceB: null,
  graphDataA: null,
  graphDataB: null,
  isLoading: false,
  error: null,

  toggleCompareMode: () => {
    const { compareMode } = get();
    set({
      compareMode: !compareMode,
      selectedTraceIds: [],
    });
  },

  toggleTraceSelection: (traceId: string) => {
    const { selectedTraceIds } = get();
    if (selectedTraceIds.includes(traceId)) {
      set({ selectedTraceIds: selectedTraceIds.filter((id) => id !== traceId) });
    } else if (selectedTraceIds.length < 2) {
      set({ selectedTraceIds: [...selectedTraceIds, traceId] });
    }
  },

  clearSelection: () => {
    set({ selectedTraceIds: [], compareMode: false });
  },

  loadComparison: async (traceIdA: string, traceIdB: string) => {
    set({
      isLoading: true,
      error: null,
      traceA: null,
      traceB: null,
      graphDataA: null,
      graphDataB: null,
    });
    try {
      const [traceA, traceB, graphDataA, graphDataB] = await Promise.all([
        getTrace(traceIdA),
        getTrace(traceIdB),
        getTraceGraph(traceIdA),
        getTraceGraph(traceIdB),
      ]);
      set({ traceA, traceB, graphDataA, graphDataB });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load traces";
      set({ error: message });
    } finally {
      set({ isLoading: false });
    }
  },

  reset: () => {
    set({
      traceA: null,
      traceB: null,
      graphDataA: null,
      graphDataB: null,
      isLoading: false,
      error: null,
    });
  },
}));
