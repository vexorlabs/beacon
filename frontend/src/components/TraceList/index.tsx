import { useEffect, useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useTraceStore } from "@/store/trace";
import TraceListItem from "./TraceListItem";
import TraceFilter from "./TraceFilter";

export default function TraceList() {
  const traces = useTraceStore((s) => s.traces);
  const isLoading = useTraceStore((s) => s.isLoadingTraces);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectTrace = useTraceStore((s) => s.selectTrace);
  const loadTraces = useTraceStore((s) => s.loadTraces);
  const traceFilter = useTraceStore((s) => s.traceFilter);

  useEffect(() => {
    void loadTraces();
  }, [loadTraces]);

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (traceFilter.status !== "all" && t.status !== traceFilter.status)
        return false;
      if (
        traceFilter.nameQuery &&
        !t.name.toLowerCase().includes(traceFilter.nameQuery.toLowerCase())
      )
        return false;
      return true;
    });
  }, [traces, traceFilter]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border">
        <h2 className="text-[13px] font-semibold">Traces</h2>
      </div>
      <TraceFilter />
      <ScrollArea className="flex-1">
        {isLoading && traces.length === 0 && (
          <div className="flex flex-col gap-0">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="px-3 py-2 border-b border-border">
                <div className="flex items-center justify-between gap-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-5 w-10" />
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-10 ml-auto" />
                </div>
              </div>
            ))}
          </div>
        )}
        {!isLoading && traces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No traces yet. Run an instrumented agent to see traces here.
          </div>
        )}
        {!isLoading && traces.length > 0 && filteredTraces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No traces match the current filter.
          </div>
        )}
        {filteredTraces.map((trace) => (
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
