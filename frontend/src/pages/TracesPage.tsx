import { useEffect, useRef, useState } from "react";
import TraceList from "@/components/TraceList";
import TraceGraph from "@/components/TraceGraph";
import SpanDetail from "@/components/SpanDetail";
import TimeTravel from "@/components/TimeTravel";
import CostSummaryBar from "@/components/CostSummaryBar";
import { useResizablePanels } from "@/lib/useResizablePanels";
import { useTraceStore } from "@/store/trace";

export default function TracesPage() {
  const { leftWidth, rightWidth, leftHandleProps, rightHandleProps } =
    useResizablePanels(280, 380);

  const [expanded, setExpanded] = useState(false);
  const selectedSpanId = useTraceStore((s) => s.selectedSpanId);
  const prevSpanId = useRef(selectedSpanId);

  // When a span is clicked while in fullscreen, reveal the detail panel
  useEffect(() => {
    if (
      expanded &&
      selectedSpanId !== null &&
      selectedSpanId !== prevSpanId.current
    ) {
      setExpanded(false);
    }
    prevSpanId.current = selectedSpanId;
  }, [expanded, selectedSpanId]);

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

      {/* Center — Graph canvas */}
      <div className="flex-1 min-w-0 flex flex-col">
        <CostSummaryBar
          expanded={expanded}
          onToggleExpand={() => setExpanded((e) => !e)}
        />
        <div className="flex-1 min-h-0">
          <TraceGraph />
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
            className="border-l border-border"
          >
            <SpanDetail />
          </div>
        </>
      )}
    </div>
  );
}
