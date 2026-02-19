import { useCallback } from "react";
import {
  GitGraph,
  GanttChart,
  Maximize2,
  Minimize2,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTraceStore } from "@/store/trace";
import { exportTrace } from "@/lib/api";

export type ViewMode = "graph" | "timeline";

interface CostSummaryBarProps {
  expanded: boolean;
  onToggleExpand: () => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function CostSummaryBar({
  expanded,
  onToggleExpand,
  viewMode,
  onViewModeChange,
}: CostSummaryBarProps) {
  const selectedTrace = useTraceStore((s) => s.selectedTrace);

  const handleExport = useCallback(
    async (format: "json" | "otel" | "csv") => {
      if (!selectedTrace) return;
      const blob = await exportTrace(selectedTrace.trace_id, format);
      const prefix = selectedTrace.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .slice(0, 30);
      const idShort = selectedTrace.trace_id.slice(0, 8);
      const ext = format === "otel" ? "otel.json" : format === "csv" ? "csv" : "json";
      triggerDownload(blob, `${prefix}-${idShort}.${ext}`);
    },
    [selectedTrace],
  );

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

      {/* Export + View toggle + fullscreen */}
      <div className="ml-auto flex items-center gap-1">
        {selectedTrace && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                title="Export trace"
                className="flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
              >
                <Download size={13} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => void handleExport("json")}>
                JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void handleExport("otel")}>
                OTEL JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => void handleExport("csv")}>
                CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
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
