import { useNavigationStore } from "@/store/navigation";
import { useTraceStore } from "@/store/trace";
import { Bug, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { TraceSummary } from "@/lib/types";

export default function DashboardPage() {
  const navigate = useNavigationStore((s) => s.navigate);
  const traces = useTraceStore((s) => s.traces);
  const hasTraces = traces.length > 0;

  if (!hasTraces) {
    return <GettingStarted onNavigate={navigate} />;
  }

  return <Overview traces={traces} onNavigate={navigate} />;
}

function GettingStarted({
  onNavigate,
}: {
  onNavigate: (page: "traces" | "playground") => void;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-lg w-full space-y-8">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold text-foreground">
            Welcome to Beacon
          </h1>
          <p className="text-muted-foreground text-sm">
            Debug your AI agents with interactive execution graphs, time-travel,
            and prompt replay.
          </p>
        </div>

        <div className="space-y-4">
          <Step
            number={1}
            title="Install the SDK"
            code="pip install beacon-sdk"
          />
          <Step
            number={2}
            title="Instrument your agent"
            code={`from beacon_sdk import observe\n\n@observe()\ndef my_agent():\n    # your agent code\n    ...`}
          />
          <Step
            number={3}
            title="Run your agent"
            code="python my_agent.py"
            description="Traces appear here automatically via WebSocket."
          />
        </div>

        <div className="flex gap-3 pt-2">
          <Button onClick={() => onNavigate("playground")}>
            <FlaskConical size={14} />
            Try the Playground
          </Button>
          <Button variant="outline" onClick={() => onNavigate("traces")}>
            <Bug size={14} />
            View Traces
          </Button>
        </div>
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  code,
  description,
}: {
  number: number;
  title: string;
  code: string;
  description?: string;
}) {
  return (
    <div className="border border-border rounded-lg p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary text-primary-foreground text-[11px] font-medium">
          {number}
        </span>
        <span className="text-sm font-medium text-foreground">{title}</span>
      </div>
      <pre className="bg-background rounded-md px-3 py-2 text-xs font-mono text-muted-foreground overflow-x-auto">
        {code}
      </pre>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

function Overview({
  traces,
  onNavigate,
}: {
  traces: TraceSummary[];
  onNavigate: (page: "traces" | "playground") => void;
}) {
  const totalCost = traces.reduce((sum, t) => sum + (t.total_cost_usd ?? 0), 0);
  const totalTokens = traces.reduce((sum, t) => sum + (t.total_tokens ?? 0), 0);
  const avgDuration =
    traces.length > 0
      ? traces.reduce((sum, t) => sum + (t.duration_ms ?? 0), 0) / traces.length
      : 0;

  const recentTraces = traces.slice(0, 5);

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl space-y-8">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Overview of your agent traces.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Traces" value={String(traces.length)} />
          <StatCard
            label="Total Cost"
            value={`$${totalCost.toFixed(4)}`}
          />
          <StatCard
            label="Total Tokens"
            value={totalTokens.toLocaleString()}
          />
          <StatCard
            label="Avg Duration"
            value={formatDuration(avgDuration)}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">
              Recent Traces
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate("traces")}
            >
              View All
            </Button>
          </div>
          <div className="space-y-2">
            {recentTraces.map((trace) => (
              <button
                key={trace.trace_id}
                type="button"
                onClick={() => onNavigate("traces")}
                className="w-full text-left border border-border rounded-lg p-3 hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-medium text-foreground truncate">
                    {trace.name}
                  </span>
                  <span
                    className={`text-[11px] font-medium ${
                      trace.status === "error"
                        ? "text-red-400"
                        : trace.status === "ok"
                          ? "text-emerald-400"
                          : "text-muted-foreground"
                    }`}
                  >
                    {trace.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                  <span>{trace.span_count} spans</span>
                  {trace.duration_ms !== null && (
                    <span>{formatDuration(trace.duration_ms)}</span>
                  )}
                  {trace.total_cost_usd > 0 && (
                    <span>${trace.total_cost_usd.toFixed(4)}</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <Button onClick={() => onNavigate("playground")}>
            <FlaskConical size={14} />
            Open Playground
          </Button>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border rounded-lg p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold text-foreground mt-0.5">
        {value}
      </div>
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
