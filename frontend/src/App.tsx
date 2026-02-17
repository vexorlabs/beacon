import { useEffect, useRef } from "react";
import TraceList from "@/components/TraceList";
import TraceGraph from "@/components/TraceGraph";
import SpanDetail from "@/components/SpanDetail";
import TimeTravel from "@/components/TimeTravel";
import ErrorBanner from "@/components/ErrorBanner";
import CostSummaryBar from "@/components/CostSummaryBar";
import { BeaconWebSocket } from "@/lib/ws";
import { useTraceStore } from "@/store/trace";
import { useResizablePanels } from "@/lib/useResizablePanels";

export default function App() {
  const appendSpan = useTraceStore((s) => s.appendSpan);
  const prependTrace = useTraceStore((s) => s.prependTrace);
  const wsRef = useRef<BeaconWebSocket | null>(null);
  const { leftWidth, rightWidth, leftHandleProps, rightHandleProps } =
    useResizablePanels(280, 380);

  useEffect(() => {
    const ws = new BeaconWebSocket();
    wsRef.current = ws;
    ws.connect();

    const unsubSpan = ws.onSpanCreated((event) => {
      appendSpan(event.span);
    });
    const unsubTrace = ws.onTraceCreated((event) => {
      prependTrace({
        ...event.trace,
        end_time: null,
        duration_ms: null,
        span_count: 0,
        total_cost_usd: 0,
        total_tokens: 0,
        tags: {},
      });
    });

    return () => {
      unsubSpan();
      unsubTrace();
      ws.disconnect();
    };
  }, [appendSpan, prependTrace]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground">
      <ErrorBanner />
      <div className="flex flex-1 min-h-0 overflow-hidden">
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
        <div className="flex-1 min-w-0 flex flex-col">
          <CostSummaryBar />
          <div className="flex-1 min-h-0">
            <TraceGraph />
          </div>
          <TimeTravel />
        </div>
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
      </div>
    </div>
  );
}
