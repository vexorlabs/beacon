import { create } from "zustand";
import {
  analyzeRootCause,
  analyzeCostOptimization,
  analyzePromptSuggestions,
  analyzeErrorPatterns,
  summarizeTrace,
} from "@/lib/api";
import type {
  RootCauseAnalysisResponse,
  CostOptimizationResponse,
  PromptSuggestionsResponse,
  ErrorPatternsResponse,
  TraceSummaryAnalysisResponse,
} from "@/lib/types";

export type AnalysisType =
  | "root-cause"
  | "cost-optimization"
  | "prompt-suggestions"
  | "error-patterns"
  | "summarize";

type AnalysisResult =
  | { type: "root-cause"; data: RootCauseAnalysisResponse }
  | { type: "cost-optimization"; data: CostOptimizationResponse }
  | { type: "prompt-suggestions"; data: PromptSuggestionsResponse }
  | { type: "error-patterns"; data: ErrorPatternsResponse }
  | { type: "summarize"; data: TraceSummaryAnalysisResponse };

interface AnalysisStore {
  analysisResult: AnalysisResult | null;
  isAnalyzing: boolean;
  analysisType: AnalysisType | null;
  analysisError: string | null;
  highlightedSpanIds: string[];
  showAnalysisPanel: boolean;

  runAnalysis: (
    type: AnalysisType,
    params: { traceId?: string; traceIds?: string[]; spanId?: string },
  ) => Promise<void>;
  clearAnalysis: () => void;
  closeAnalysisPanel: () => void;
  openAnalysisPanel: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  analysisResult: null,
  isAnalyzing: false,
  analysisType: null,
  analysisError: null,
  highlightedSpanIds: [],
  showAnalysisPanel: false,

  runAnalysis: async (type, params) => {
    set({
      isAnalyzing: true,
      analysisType: type,
      analysisError: null,
      analysisResult: null,
      highlightedSpanIds: [],
      showAnalysisPanel: true,
    });
    try {
      let result: AnalysisResult;
      switch (type) {
        case "root-cause": {
          const data = await analyzeRootCause(params.traceId!);
          result = { type: "root-cause", data };
          set({ highlightedSpanIds: data.affected_spans });
          break;
        }
        case "cost-optimization": {
          const data = await analyzeCostOptimization(
            params.traceIds ?? [params.traceId!],
          );
          result = { type: "cost-optimization", data };
          break;
        }
        case "prompt-suggestions": {
          const data = await analyzePromptSuggestions(params.spanId!);
          result = { type: "prompt-suggestions", data };
          break;
        }
        case "error-patterns": {
          const data = await analyzeErrorPatterns(
            params.traceIds ?? [params.traceId!],
          );
          result = { type: "error-patterns", data };
          break;
        }
        case "summarize": {
          const data = await summarizeTrace(params.traceId!);
          result = { type: "summarize", data };
          break;
        }
      }
      set({ analysisResult: result });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Analysis failed";
      set({ analysisError: message });
    } finally {
      set({ isAnalyzing: false });
    }
  },

  clearAnalysis: () => {
    set({
      analysisResult: null,
      isAnalyzing: false,
      analysisType: null,
      analysisError: null,
      highlightedSpanIds: [],
      showAnalysisPanel: false,
    });
  },

  closeAnalysisPanel: () => {
    set({ showAnalysisPanel: false });
  },

  openAnalysisPanel: () => {
    set({ showAnalysisPanel: true });
  },
}));
