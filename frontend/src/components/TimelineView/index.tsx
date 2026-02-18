import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useTraceStore } from "@/store/trace";
import TimelineBar from "./TimelineBar";
import TimelineHeader from "./TimelineHeader";
import SlowestSpans from "./SlowestSpans";
import { useTimelineLayout, ROW_HEIGHT } from "./useTimelineLayout";

export default function TimelineView() {
  const navigate = useNavigate();
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectedTrace = useTraceStore((s) => s.selectedTrace);
  const selectedSpanId = useTraceStore((s) => s.selectedSpanId);
  const selectSpan = useTraceStore((s) => s.selectSpan);
  const timeTravelIndex = useTraceStore((s) => s.timeTravelIndex);
  const isLoading = useTraceStore((s) => s.isLoadingTrace);
  const graphData = useTraceStore((s) => s.graphData);

  // Measure container width for pixel calculations
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const layout = useTimelineLayout(selectedTrace?.spans, containerWidth);

  // Build chronological index for time-travel (matching graph view behavior)
  const chronoIndex = useMemo(() => {
    const map = new Map<string, number>();
    const nodes = graphData?.nodes;
    if (nodes) {
      nodes.forEach((n, i) => map.set(n.id, i));
    }
    return map;
  }, [graphData?.nodes]);

  const handleSelect = useCallback(
    (spanId: string) => {
      selectSpan(spanId);
      if (selectedTraceId) {
        navigate(`/traces/${selectedTraceId}/${spanId}`, { replace: true });
      }
    },
    [selectSpan, selectedTraceId, navigate],
  );

  if (!selectedTraceId) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Select a trace to view its timeline
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <Skeleton className="h-4 w-64 rounded" />
          <Skeleton className="h-5 w-80 rounded" />
          <Skeleton className="h-5 w-72 rounded" />
          <Skeleton className="h-5 w-60 rounded" />
        </div>
      </div>
    );
  }

  if (layout.spans.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No spans in this trace
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" ref={containerRef}>
      <TimelineHeader
        traceStartTime={layout.traceStartTime}
        traceEndTime={layout.traceEndTime}
        containerWidth={containerWidth}
      />
      <ScrollArea className="flex-1">
        <div
          className="relative"
          style={{
            height: layout.totalRows * ROW_HEIGHT,
            minHeight: "100%",
          }}
        >
          {layout.spans.map((ts) => {
            const idx = chronoIndex.get(ts.span.span_id) ?? 0;
            const isFuture =
              timeTravelIndex !== null && idx >= timeTravelIndex;

            return (
              <TimelineBar
                key={ts.span.span_id}
                item={ts}
                isSelected={ts.span.span_id === selectedSpanId}
                isFuture={isFuture}
                onSelect={handleSelect}
              />
            );
          })}
        </div>
      </ScrollArea>
      <SlowestSpans spans={layout.slowestSpans} onSelect={handleSelect} />
    </div>
  );
}
