import { ArrowLeft, X } from "lucide-react";
import { useTraceStore } from "@/store/trace";
import { useAnalysisStore } from "@/store/analysis";
import RootCausePanel from "@/components/Analysis/RootCausePanel";
import CostOptimizationPanel from "@/components/Analysis/CostOptimizationPanel";
import PromptSuggestionsPanel from "@/components/Analysis/PromptSuggestionsPanel";
import TraceSummaryCard from "@/components/Analysis/TraceSummaryCard";
import ErrorPatternsPanel from "@/components/Analysis/ErrorPatternsPanel";

const ANALYSIS_TITLES: Record<string, string> = {
  "root-cause": "Root Cause Analysis",
  "cost-optimization": "Cost Optimization",
  "prompt-suggestions": "Prompt Suggestions",
  "error-patterns": "Error Patterns",
  summarize: "Trace Summary",
};

export default function AnalysisView() {
  const selectSpan = useTraceStore((s) => s.selectSpan);
  const analysisResult = useAnalysisStore((s) => s.analysisResult);
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const analysisType = useAnalysisStore((s) => s.analysisType);
  const analysisError = useAnalysisStore((s) => s.analysisError);
  const closeAnalysisPanel = useAnalysisStore((s) => s.closeAnalysisPanel);
  const clearAnalysis = useAnalysisStore((s) => s.clearAnalysis);

  const displayType = analysisResult?.type ?? analysisType;
  const title =
    displayType ? (ANALYSIS_TITLES[displayType] ?? "AI Analysis") : "AI Analysis";

  const handleSpanClick = (spanId: string) => {
    selectSpan(spanId);
    closeAnalysisPanel();
  };

  return (
    <div className="flex h-full min-h-0 flex-col animate-in fade-in-0 slide-in-from-right-2 duration-200">
      <div className="h-11 border-b border-border bg-card/50 px-3 flex items-center gap-2">
        <button
          type="button"
          onClick={closeAnalysisPanel}
          className="flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
          title="Back to span details"
        >
          <ArrowLeft size={14} />
        </button>
        <h3 className="text-[13px] font-semibold flex-1 truncate">{title}</h3>
        <button
          type="button"
          onClick={clearAnalysis}
          className="flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
          title="Close analysis"
        >
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {displayType === "root-cause" && (
          <RootCausePanel
            data={
              analysisResult?.type === "root-cause"
                ? analysisResult.data
                : null
            }
            isLoading={isAnalyzing && analysisType === "root-cause"}
            error={analysisType === "root-cause" ? analysisError : null}
            onSpanClick={handleSpanClick}
          />
        )}
        {displayType === "cost-optimization" && (
          <CostOptimizationPanel
            data={
              analysisResult?.type === "cost-optimization"
                ? analysisResult.data
                : null
            }
            isLoading={isAnalyzing && analysisType === "cost-optimization"}
            error={
              analysisType === "cost-optimization" ? analysisError : null
            }
            onSpanClick={handleSpanClick}
          />
        )}
        {displayType === "prompt-suggestions" && (
          <PromptSuggestionsPanel
            data={
              analysisResult?.type === "prompt-suggestions"
                ? analysisResult.data
                : null
            }
            isLoading={isAnalyzing && analysisType === "prompt-suggestions"}
            error={
              analysisType === "prompt-suggestions" ? analysisError : null
            }
          />
        )}
        {displayType === "summarize" && (
          <TraceSummaryCard
            data={
              analysisResult?.type === "summarize"
                ? analysisResult.data
                : null
            }
            isLoading={isAnalyzing && analysisType === "summarize"}
            error={analysisType === "summarize" ? analysisError : null}
            onSpanClick={handleSpanClick}
          />
        )}
        {displayType === "error-patterns" && (
          <ErrorPatternsPanel
            data={
              analysisResult?.type === "error-patterns"
                ? analysisResult.data
                : null
            }
            isLoading={isAnalyzing && analysisType === "error-patterns"}
            error={analysisType === "error-patterns" ? analysisError : null}
          />
        )}
      </div>
    </div>
  );
}
