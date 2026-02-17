import { useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useTraceStore } from "@/store/trace";
import TraceListItem from "./TraceListItem";

export default function TraceList() {
  const traces = useTraceStore((s) => s.traces);
  const isLoading = useTraceStore((s) => s.isLoadingTraces);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectTrace = useTraceStore((s) => s.selectTrace);
  const loadTraces = useTraceStore((s) => s.loadTraces);

  useEffect(() => {
    void loadTraces();
  }, [loadTraces]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border">
        <h2 className="text-sm font-semibold">Traces</h2>
      </div>
      <ScrollArea className="flex-1">
        {isLoading && traces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">Loading...</div>
        )}
        {!isLoading && traces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No traces yet. Run an instrumented agent to see traces here.
          </div>
        )}
        {traces.map((trace) => (
          <TraceListItem
            key={trace.trace_id}
            trace={trace}
            isSelected={trace.trace_id === selectedTraceId}
            onSelect={selectTrace}
          />
        ))}
      </ScrollArea>
    </div>
  );
}
