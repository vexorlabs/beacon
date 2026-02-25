import { create } from "zustand";
import { getTrace, getTraceGraph, compareAnalysis } from "@/lib/api";
import type { DivergencePoint, GraphData, TraceDetail } from "@/lib/types";

interface CompareStore {
  compareMode: boolean;
  selectedTraceIds: string[];

  traceA: TraceDetail | null;
  traceB: TraceDetail | null;
  graphDataA: GraphData | null;
  graphDataB: GraphData | null;
  isLoading: boolean;
  error: string | null;

  // AI comparison
  divergencePoints: DivergencePoint[];
  compareSummary: string | null;
  isAnalyzingComparison: boolean;
  analysisError: string | null;

  toggleCompareMode: () => void;
  toggleTraceSelection: (traceId: string) => void;
  clearSelection: () => void;
  loadComparison: (traceIdA: string, traceIdB: string) => Promise<void>;
  runCompareAnalysis: (traceIdA: string, traceIdB: string) => Promise<void>;
  reset: () => void;
}

export const useCompareStore = create<CompareStore>((set) => ({
  compareMode: false,
  selectedTraceIds: [],

  traceA: null,
  traceB: null,
  graphDataA: null,
  graphDataB: null,
  isLoading: false,
  error: null,

  divergencePoints: [],
  compareSummary: null,
  isAnalyzingComparison: false,
  analysisError: null,

  toggleCompareMode: () => {
    set((state) => ({
      compareMode: !state.compareMode,
      selectedTraceIds: [],
    }));
  },

  toggleTraceSelection: (traceId: string) => {
    set((state) => {
      if (state.selectedTraceIds.includes(traceId)) {
        return { selectedTraceIds: state.selectedTraceIds.filter((id) => id !== traceId) };
      } else if (state.selectedTraceIds.length < 2) {
        return { selectedTraceIds: [...state.selectedTraceIds, traceId] };
      }
      return state;
    });
  },

  clearSelection: () => {
    set({ selectedTraceIds: [], compareMode: false });
  },

  loadComparison: async (traceIdA: string, traceIdB: string) => {
    if (traceIdA === traceIdB) {
      set({ error: "Select two different traces to compare" });
      return;
    }
    set({
      isLoading: true,
      error: null,
      traceA: null,
      traceB: null,
      graphDataA: null,
      graphDataB: null,
      divergencePoints: [],
      compareSummary: null,
      analysisError: null,
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

  runCompareAnalysis: async (traceIdA: string, traceIdB: string) => {
    set({
      isAnalyzingComparison: true,
      analysisError: null,
      divergencePoints: [],
      compareSummary: null,
    });
    try {
      const result = await compareAnalysis(traceIdA, traceIdB);
      set({
        divergencePoints: result.divergence_points,
        compareSummary: result.summary,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Analysis failed";
      set({ analysisError: message });
    } finally {
      set({ isAnalyzingComparison: false });
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
      divergencePoints: [],
      compareSummary: null,
      isAnalyzingComparison: false,
      analysisError: null,
    });
  },
}));
