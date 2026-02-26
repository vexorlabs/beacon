import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTraceStore } from "@/store/trace";
import { Bug, Radar } from "lucide-react";
import { Button } from "@/components/ui/button";
import DemoAgents from "@/components/DemoAgents";
import TrendCharts from "@/components/Dashboard/TrendCharts";
import CostForecast from "@/components/Dashboard/CostForecast";
import TopTables from "@/components/Dashboard/TopTables";
import AnomalyAlerts from "@/components/Dashboard/AnomalyAlerts";
import {
  getTrends,
  getTopCosts,
  getTopDuration,
  detectAnomalies,
} from "@/lib/api";
import type { TraceSummary, Anomaly, TrendsResponse, TopCostsResponse, TopDurationResponse } from "@/lib/types";

export default function DashboardPage() {
  const navigate = useNavigate();
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
  onNavigate: (path: string) => void;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-10">
        <div className="space-y-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Radar size={20} className="text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            Welcome to Beacon
          </h1>
          <p className="text-muted-foreground text-[13px] max-w-md leading-relaxed">
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

        <DemoAgents />

        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            onClick={() => onNavigate("/traces")}
          >
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
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 space-y-2.5 shadow-[0_2px_8px_oklch(0_0_0/0.2)]">
      <div className="flex items-center gap-2.5">
        <span className="flex items-center justify-center w-5 h-5 rounded-md bg-primary/15 text-primary text-[11px] font-semibold">
          {number}
        </span>
        <span className="text-[13px] font-medium text-foreground">{title}</span>
      </div>
      <pre className="bg-background/80 rounded-md px-3 py-2 text-xs font-mono text-muted-foreground overflow-x-auto border-[0.5px] border-border">
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
  onNavigate: (path: string) => void;
}) {
  const totalCost = traces.reduce((sum, t) => sum + (t.total_cost_usd ?? 0), 0);
  const totalTokens = traces.reduce((sum, t) => sum + (t.total_tokens ?? 0), 0);
  const avgDuration =
    traces.length > 0
      ? traces.reduce((sum, t) => sum + (t.duration_ms ?? 0), 0) / traces.length
      : 0;

  const recentTraces = traces.slice(0, 5);

  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [topCosts, setTopCosts] = useState<TopCostsResponse | null>(null);
  const [topDuration, setTopDuration] = useState<TopDurationResponse | null>(null);
  const getCachedAnomalies = useTraceStore((s) => s.getCachedAnomalies);
  const setCachedAnomalies = useTraceStore((s) => s.setCachedAnomalies);
  const initialTraceId = traces.length > 0 ? traces[0].trace_id : null;
  const initialCachedAnomalies = initialTraceId ? getCachedAnomalies(initialTraceId) : null;
  const [anomalies, setAnomalies] = useState<Anomaly[]>(initialCachedAnomalies ?? []);
  const needsAnomalyFetch = initialTraceId !== null && initialCachedAnomalies === null;
  const [anomalyLoading, setAnomalyLoading] = useState(needsAnomalyFetch);
  const [anomalyError, setAnomalyError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getTrends({ days: 30, bucket: "day" }),
      getTopCosts(10),
      getTopDuration(10),
    ])
      .then(([trendsRes, costsRes, durationRes]) => {
        setTrends(trendsRes);
        setTopCosts(costsRes);
        setTopDuration(durationRes);
      })
      .catch(() => {
        // Trends/tables fail silently — stat cards still work
      });

    if (initialTraceId && needsAnomalyFetch) {
      detectAnomalies(initialTraceId)
        .then((res) => {
          setAnomalies(res.anomalies);
          setCachedAnomalies(initialTraceId, res.anomalies);
        })
        .catch((err: unknown) =>
          setAnomalyError(
            err instanceof Error ? err.message : "Anomaly detection unavailable",
          ),
        )
        .finally(() => setAnomalyLoading(false));
    }
    // Fetch once on mount. Intentionally excludes `traces` to avoid
    // re-calling the LLM anomaly endpoint on every WebSocket update.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl space-y-8">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-[13px] mt-1">
            Overview of your agent traces.
          </p>
        </div>

        <div className="grid grid-cols-5 gap-4">
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
          {trends && <CostForecast buckets={trends.buckets} />}
        </div>

        {trends && <TrendCharts buckets={trends.buckets} />}

        {topCosts && topDuration && (
          <TopTables
            topCosts={topCosts.prompts}
            topDuration={topDuration.tools}
            onNavigate={onNavigate}
          />
        )}

        <AnomalyAlerts
          anomalies={anomalies}
          isLoading={anomalyLoading}
          error={anomalyError}
          onNavigate={onNavigate}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">
              Recent Traces
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate("/traces")}
            >
              View All
            </Button>
          </div>
          <div className="space-y-2">
            {recentTraces.map((trace) => (
              <button
                key={trace.trace_id}
                type="button"
                onClick={() => onNavigate(`/traces/${trace.trace_id}`)}
                className="w-full text-left cursor-pointer bg-card border-[0.5px] border-border rounded-lg p-3.5 hover:bg-secondary/50 transition-colors shadow-[0_1px_3px_oklch(0_0_0/0.1)]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-medium text-foreground truncate">
                    {trace.name}
                  </span>
                  <span
                    className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${
                      trace.status === "error"
                        ? "text-red-400 bg-red-500/10"
                        : trace.status === "ok"
                          ? "text-emerald-400 bg-emerald-500/10"
                          : "text-muted-foreground bg-muted"
                    }`}
                  >
                    {trace.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
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

        <DemoAgents />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <div className="text-xs text-muted-foreground font-medium">{label}</div>
      <div className="text-xl font-semibold text-foreground mt-1 tracking-tight">
        {value}
      </div>
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
