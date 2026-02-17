import { useEffect, useRef } from "react";
import { Separator } from "@/components/ui/separator";
import TraceList from "@/components/TraceList";
import TraceGraph from "@/components/TraceGraph";
import SpanDetail from "@/components/SpanDetail";
import { BeaconWebSocket } from "@/lib/ws";
import { useTraceStore } from "@/store/trace";

export default function App() {
  const appendSpan = useTraceStore((s) => s.appendSpan);
  const prependTrace = useTraceStore((s) => s.prependTrace);
  const wsRef = useRef<BeaconWebSocket | null>(null);

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
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <div className="w-[280px] flex-none border-r border-border">
        <TraceList />
      </div>
      <Separator orientation="vertical" />
      <div className="flex-1 min-w-0">
        <TraceGraph />
      </div>
      <Separator orientation="vertical" />
      <div className="w-[380px] flex-none border-l border-border">
        <SpanDetail />
      </div>
    </div>
  );
}
