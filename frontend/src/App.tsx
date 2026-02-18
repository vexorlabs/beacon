import { useEffect, useRef } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import ErrorBanner from "@/components/ErrorBanner";
import DashboardPage from "@/pages/DashboardPage";
import TracesPage from "@/pages/TracesPage";
import PlaygroundPage from "@/pages/PlaygroundPage";
import SettingsPage from "@/pages/SettingsPage";
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
    <div className="flex h-screen w-screen overflow-hidden bg-sidebar text-foreground">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden bg-background border-[0.5px] border-border rounded-lg my-2 mr-2 shadow-[0_4px_4px_-1px_oklch(0_0_0/0.06),0_1px_1px_0_oklch(0_0_0/0.12)]">
        <ErrorBanner />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/traces" element={<TracesPage />} />
          <Route path="/traces/:traceId" element={<TracesPage />} />
          <Route path="/traces/:traceId/:spanId" element={<TracesPage />} />
          <Route path="/playground" element={<PlaygroundPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
