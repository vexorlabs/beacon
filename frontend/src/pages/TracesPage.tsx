import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import TraceList from "@/components/TraceList";
import TraceGraph from "@/components/TraceGraph";
import TimelineView from "@/components/TimelineView";
import SpanDetail from "@/components/SpanDetail";
import TimeTravel from "@/components/TimeTravel";
import CostSummaryBar from "@/components/CostSummaryBar";
import type { ViewMode } from "@/components/CostSummaryBar";
import CanvasToolbar from "@/components/TraceGraph/CanvasToolbar";
import { useResizablePanels } from "@/lib/useResizablePanels";
import { useTraceStore } from "@/store/trace";

export default function TracesPage() {
  const { traceId, spanId } = useParams<{
    traceId?: string;
    spanId?: string;
  }>();

  const { leftWidth, rightWidth, leftHandleProps, rightHandleProps } =
    useResizablePanels(350, 330);

  const [expanded, setExpanded] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("graph");
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectTrace = useTraceStore((s) => s.selectTrace);
  const selectSpan = useTraceStore((s) => s.selectSpan);

  // Auto-select trace from URL params
  useEffect(() => {
    if (traceId && traceId !== selectedTraceId) {
      void selectTrace(traceId);
    }
  }, [traceId, selectTrace, selectedTraceId]);

  // Auto-select span from URL params after trace is loaded
  useEffect(() => {
    if (spanId && traceId === selectedTraceId) {
      selectSpan(spanId);
    }
  }, [spanId, traceId, selectedTraceId, selectSpan]);

  // When a span is clicked while in fullscreen, reveal the detail panel
  useEffect(() => {
    if (!expanded) return;
    let prevSpanId: string | null = useTraceStore.getState().selectedSpanId;
    const unsub = useTraceStore.subscribe((state) => {
      if (state.selectedSpanId !== null && state.selectedSpanId !== prevSpanId) {
        setExpanded(false);
      }
      prevSpanId = state.selectedSpanId;
    });
    return unsub;
  }, [expanded]);

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      {/* Left panel — Trace list */}
      {!expanded && (
        <>
          <div
            style={{ width: leftWidth, flexShrink: 0 }}
            className="border-r border-border flex flex-col"
          >
            <TraceList />
          </div>
          <div
            {...leftHandleProps}
            className="w-1 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 transition-colors flex-none"
            role="separator"
            aria-label="Resize trace list"
          />
        </>
      )}

      {/* Center — Graph or Timeline canvas */}
      <div className="flex-1 min-w-0 flex flex-col">
        <CostSummaryBar
          expanded={expanded}
          onToggleExpand={() => setExpanded((e) => !e)}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
        <div className="relative flex-1 min-h-0">
          {viewMode === "graph" ? <TraceGraph /> : <TimelineView />}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10">
            <CanvasToolbar viewMode={viewMode} onViewModeChange={setViewMode} />
          </div>
        </div>
        <TimeTravel />
      </div>

      {/* Right panel — Span detail */}
      {!expanded && (
        <>
          <div
            {...rightHandleProps}
            className="w-1 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 transition-colors flex-none"
            role="separator"
            aria-label="Resize span detail"
          />
          <div
            style={{ width: rightWidth, flexShrink: 0 }}
            className="border-l border-border flex flex-col min-h-0"
          >
            <SpanDetail />
          </div>
        </>
      )}
    </div>
  );
}
