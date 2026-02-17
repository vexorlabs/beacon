import { useTraceStore } from "@/store/trace";
import { Badge } from "@/components/ui/badge";
import LlmCallDetail from "./LlmCallDetail";
import ToolUseDetail from "./ToolUseDetail";
import BrowserDetail from "./BrowserDetail";
import GenericDetail from "./GenericDetail";

export default function SpanDetail() {
  const selectedSpan = useTraceStore((s) => s.selectedSpan);

  if (!selectedSpan) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground p-4 text-center">
        Select a span to see details
      </div>
    );
  }

  const duration =
    selectedSpan.end_time !== null
      ? `${((selectedSpan.end_time - selectedSpan.start_time) * 1000).toFixed(0)}ms`
      : "running...";

  return (
    <div className="p-4 overflow-auto h-full">
      {/* Header — shared across all span types */}
      <h3 className="font-semibold text-sm">{selectedSpan.name}</h3>
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
        <div className="mt-2 text-xs text-red-500">
          Error: {selectedSpan.error_message}
        </div>
      )}

      {/* Type-specific detail */}
      <div className="mt-4">
        {selectedSpan.span_type === "llm_call" && (
          <LlmCallDetail span={selectedSpan} />
        )}
        {selectedSpan.span_type === "tool_use" && (
          <ToolUseDetail span={selectedSpan} />
        )}
        {selectedSpan.span_type === "browser_action" && (
          <BrowserDetail span={selectedSpan} />
        )}
        {selectedSpan.span_type !== "llm_call" &&
          selectedSpan.span_type !== "tool_use" &&
          selectedSpan.span_type !== "browser_action" && (
            <GenericDetail span={selectedSpan} />
          )}
      </div>
    </div>
  );
}
