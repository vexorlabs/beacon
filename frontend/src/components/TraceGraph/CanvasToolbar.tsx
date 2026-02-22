import { useCallback } from "react";
import {
  DollarSign,
  FileText,
  GanttChart,
  GitGraph,
  Layers,
  Loader2,
  Scan,
  Target,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTraceStore } from "@/store/trace";
import { useAnalysisStore, type AnalysisType } from "@/store/analysis";
import type { ViewMode } from "@/components/CostSummaryBar";

interface CanvasToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export default function CanvasToolbar({
  viewMode,
  onViewModeChange,
}: CanvasToolbarProps) {
  const selectedTrace = useTraceStore((s) => s.selectedTrace);
  const isAnalyzing = useAnalysisStore((s) => s.isAnalyzing);
  const runAnalysis = useAnalysisStore((s) => s.runAnalysis);

  const handleAnalysis = useCallback(
    (type: AnalysisType) => {
      if (!selectedTrace) return;
      void runAnalysis(type, { traceId: selectedTrace.trace_id });
    },
    [selectedTrace, runAnalysis],
  );

  if (!selectedTrace) return null;

  return (
    <div className="flex items-center gap-0.5 rounded-full border border-border bg-card/90 px-1.5 py-1 shadow-[0_4px_16px_oklch(0_0_0/0.5)] backdrop-blur-md">
      {/* View mode toggle */}
      <button
        type="button"
        onClick={() => onViewModeChange("graph")}
        className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
          viewMode === "graph"
            ? "bg-secondary text-foreground"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
        }`}
      >
        <GitGraph size={13} />
        <span>Graph</span>
      </button>
      <button
        type="button"
        onClick={() => onViewModeChange("timeline")}
        className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
          viewMode === "timeline"
            ? "bg-secondary text-foreground"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
        }`}
      >
        <GanttChart size={13} />
        <span>Timeline</span>
      </button>

      {/* Divider */}
      <div className="h-4 w-px bg-border/60 mx-0.5" />

      {/* AI Analysis dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            title="AI Analysis"
            disabled={isAnalyzing}
            className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors disabled:opacity-50"
          >
            {isAnalyzing ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Scan size={14} />
            )}
            <span>Analyze</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side="top"
          align="center"
          sideOffset={8}
          className="w-52"
        >
          <DropdownMenuItem onClick={() => handleAnalysis("root-cause")}>
            <Target size={13} className="mr-2" />
            Root Cause Analysis
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => handleAnalysis("cost-optimization")}
          >
            <DollarSign size={13} className="mr-2" />
            Cost Optimization
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleAnalysis("summarize")}>
            <FileText size={13} className="mr-2" />
            Summarize
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleAnalysis("error-patterns")}>
            <Layers size={13} className="mr-2" />
            Error Patterns
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
