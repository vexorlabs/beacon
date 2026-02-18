import { Maximize2, Minimize2 } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { useTraceStore } from "@/store/trace";

interface CostSummaryBarProps {
  expanded: boolean;
  onToggleExpand: () => void;
}

export default function CostSummaryBar({
  expanded,
  onToggleExpand,
}: CostSummaryBarProps) {
  const selectedTrace = useTraceStore((s) => s.selectedTrace);

  return (
    <div className="flex items-center gap-4 px-3 py-2 border-b border-border text-xs text-muted-foreground bg-muted/30">
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
      <button
        type="button"
        onClick={onToggleExpand}
        title={expanded ? "Exit fullscreen" : "Fullscreen canvas"}
        className="ml-auto flex items-center justify-center w-6 h-6 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
      >
        {expanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
      </button>
    </div>
  );
}
