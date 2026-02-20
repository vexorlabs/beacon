import { useTraceStore } from "@/store/trace";
import { Badge } from "@/components/ui/badge";
import { MousePointerClick } from "lucide-react";
import LlmCallDetail from "./LlmCallDetail";
import ToolUseDetail from "./ToolUseDetail";
import BrowserDetail from "./BrowserDetail";
import GenericDetail from "./GenericDetail";
import AnnotationPanel from "./AnnotationPanel";

export default function SpanDetail() {
  const selectedSpan = useTraceStore((s) => s.selectedSpan);

  const duration =
    selectedSpan && selectedSpan.end_time !== null
      ? `${((selectedSpan.end_time - selectedSpan.start_time) * 1000).toFixed(0)}ms`
      : "running...";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="h-11 border-b border-border bg-card/50 px-3 flex items-center justify-between gap-2">
        <h3 className="text-[13px] font-semibold">Span Details</h3>
        {selectedSpan ? (
          <Badge
            variant={selectedSpan.status === "error" ? "destructive" : "secondary"}
            className="shrink-0"
          >
            {selectedSpan.status}
          </Badge>
        ) : (
          <span className="text-[11px] text-muted-foreground">No selection</span>
        )}
      </div>

      {!selectedSpan ? (
        <div className="flex flex-1 flex-col items-center justify-center text-center p-6 gap-3">
          <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center">
            <MousePointerClick size={18} className="text-muted-foreground" />
          </div>
          <div>
            <p className="text-[13px] text-muted-foreground">
              Select a span to see details
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Click any node in the graph
            </p>
          </div>
        </div>
      ) : (
        <div className="h-full overflow-auto p-4">
          {/* Header — shared across all span types */}
          <h3 className="font-semibold text-[13px] leading-tight">
            {selectedSpan.name}
          </h3>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <Badge variant="outline">{selectedSpan.span_type}</Badge>
            <Badge
              variant={selectedSpan.status === "error" ? "destructive" : "secondary"}
            >
              {selectedSpan.status}
            </Badge>
            <span className="text-xs text-muted-foreground">{duration}</span>
          </div>
          {selectedSpan.error_message && (
            <div className="mt-2 text-xs text-red-400 bg-red-500/10 rounded-md px-2 py-1.5">
              Error: {selectedSpan.error_message}
            </div>
          )}

          <div className="border-b border-border my-4" />

          {/* Type-specific detail */}
          <div>
            {(() => {
              switch (selectedSpan.span_type) {
                case "llm_call":
                  return <LlmCallDetail span={selectedSpan} />;
                case "tool_use":
                  return <ToolUseDetail span={selectedSpan} />;
                case "browser_action":
                  return <BrowserDetail span={selectedSpan} />;
                default:
                  return <GenericDetail span={selectedSpan} />;
              }
            })()}
          </div>
          <AnnotationPanel
            spanId={selectedSpan.span_id}
            annotations={selectedSpan.annotations ?? []}
          />
        </div>
      )}
    </div>
  );
}
