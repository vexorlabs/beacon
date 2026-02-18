import { GitGraph, GanttChart, Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { useTraceStore } from "@/store/trace";

export type ViewMode = "graph" | "timeline";

interface CostSummaryBarProps {
  expanded: boolean;
  onToggleExpand: () => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export default function CostSummaryBar({
  expanded,
  onToggleExpand,
  viewMode,
  onViewModeChange,
}: CostSummaryBarProps) {
  const selectedTrace = useTraceStore((s) => s.selectedTrace);

  return (
    <div className="flex items-center gap-4 px-3 py-2 border-b border-border/60 text-xs text-muted-foreground bg-card/50">
      {selectedTrace ? (
        <>
          <span className="font-medium text-foreground truncate max-w-xs">
            {selectedTrace.name}
          </span>
          <Separator orientation="vertical" className="h-4" />
          <span>{selectedTrace.total_tokens.toLocaleString()} tokens</span>
          <Separator orientation="vertical" className="h-4" />
          <span>${selectedTrace.total_cost_usd.toFixed(4)}</span>
          {selectedTrace.duration_ms !== null && (
            <>
              <Separator orientation="vertical" className="h-4" />
              <span>{(selectedTrace.duration_ms / 1000).toFixed(1)}s</span>
            </>
          )}
          <Separator orientation="vertical" className="h-4" />
          <span>{selectedTrace.span_count} spans</span>
        </>
      ) : (
        <span className="text-muted-foreground">No trace selected</span>
      )}

      {/* View toggle + fullscreen */}
      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={() => onViewModeChange("graph")}
          title="Graph view"
          className={cn(
            "flex items-center justify-center w-6 h-6 rounded-md transition-colors",
            viewMode === "graph"
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50",
          )}
        >
          <GitGraph size={13} />
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange("timeline")}
          title="Timeline view"
          className={cn(
            "flex items-center justify-center w-6 h-6 rounded-md transition-colors",
            viewMode === "timeline"
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-secondary/50",
          )}
        >
          <GanttChart size={13} />
        </button>
        <button
          type="button"
          onClick={onToggleExpand}
          title={expanded ? "Exit fullscreen" : "Fullscreen canvas"}
          className="flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          {expanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        </button>
      </div>
    </div>
  );
}
