import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTraceStore } from "@/store/trace";
import {
  Bug,
  Calendar,
  Check,
  ChevronDown,
  Copy,
  Radar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import DemoAgents from "@/components/DemoAgents";
import TrendCharts from "@/components/Dashboard/TrendCharts";
import TopTables from "@/components/Dashboard/TopTables";
import AnomalyAlerts from "@/components/Dashboard/AnomalyAlerts";
import {
  getTrends,
  getTopCosts,
  getTopDuration,
  detectAnomalies,
} from "@/lib/api";
import type {
  TraceSummary,
  Anomaly,
  TrendsResponse,
  TopCostsResponse,
  TopDurationResponse,
} from "@/lib/types";

/* ------------------------------------------------------------------ */
/*  Dashboard entry point                                             */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const navigate = useNavigate();
  const traces = useTraceStore((s) => s.traces);
  const hasTraces = traces.length > 0;

  if (!hasTraces) {
    return <GettingStarted onNavigate={navigate} />;
  }

  return <Overview traces={traces} onNavigate={navigate} />;
}

/* ------------------------------------------------------------------ */
/*  Empty state                                                       */
/* ------------------------------------------------------------------ */

function GettingStarted({
  onNavigate,
}: {
  onNavigate: (path: string) => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="min-h-full flex items-center justify-center p-8">
        <div className="max-w-2xl w-full space-y-10">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
              <Radar size={22} className="text-primary" />
            </div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">
              Welcome to Beacon
            </h1>
            <p className="text-muted-foreground text-[13px] max-w-lg leading-relaxed">
              Debug your AI agents with interactive execution graphs,
              time-travel, and prompt replay.
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
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step card (empty state)                                           */
/* ------------------------------------------------------------------ */

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
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [code]);

  return (
    <div className="bg-card border-[0.5px] border-border border-l-2 border-l-primary/30 rounded-lg p-4 space-y-2.5 shadow-[0_2px_8px_oklch(0_0_0/0.2)]">
      <div className="flex items-center gap-2.5">
        <span className="flex items-center justify-center w-5 h-5 rounded-md bg-primary/15 text-primary text-[11px] font-semibold">
          {number}
        </span>
        <span className="text-[13px] font-medium text-foreground">{title}</span>
      </div>
      <div className="relative group">
        <pre className="bg-background/80 rounded-md px-3 py-2 pr-9 text-xs font-mono text-muted-foreground overflow-x-auto border-[0.5px] border-border">
          {code}
        </pre>
        <button
          type="button"
          onClick={handleCopy}
          className="absolute top-1.5 right-1.5 p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
          aria-label="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Populated dashboard                                               */
/* ------------------------------------------------------------------ */

type TimeRange = 7 | 14 | 30;

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
  const errorCount = traces.filter((t) => t.status === "error").length;
  const successRate =
    traces.length > 0
      ? ((traces.length - errorCount) / traces.length) * 100
      : 100;

  const recentTraces = traces.slice(0, 5);

  const [timeRange, setTimeRange] = useState<TimeRange>(7);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [trendsLoading, setTrendsLoading] = useState(true);
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

  /* Fetch trends, top costs, top duration — re-run when timeRange changes */
  useEffect(() => {
    setTrendsLoading(true);
    Promise.all([
      getTrends({ days: timeRange, bucket: "day" }),
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
      })
      .finally(() => setTrendsLoading(false));
  }, [timeRange]);

  /* Anomaly detection — run once on mount, separate lifecycle */
  useEffect(() => {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl space-y-8">
        {/* Header with time range selector */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground tracking-tight">
              Dashboard
            </h1>
            <p className="text-muted-foreground text-[13px] mt-1">
              Overview of your agent traces.
            </p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Calendar size={14} />
                Last {timeRange}d
                <ChevronDown size={12} className="ml-0.5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {([7, 14, 30] as const).map((d) => (
                <DropdownMenuItem
                  key={d}
                  onClick={() => setTimeRange(d)}
                  className={timeRange === d ? "text-foreground font-medium" : ""}
                >
                  Last {d} days
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
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
          <StatCard
            label="Success Rate"
            value={`${successRate.toFixed(1)}%`}
            valueClassName={
              successRate >= 95
                ? "text-emerald-400"
                : successRate >= 80
                  ? "text-amber-400"
                  : "text-red-400"
            }
          />
        </div>

        {/* Trend Charts */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-foreground">Trends</h2>
          {trendsLoading ? (
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-[230px] rounded-lg" />
              <Skeleton className="h-[230px] rounded-lg" />
              <Skeleton className="h-[230px] rounded-lg" />
              <Skeleton className="h-[230px] rounded-lg" />
            </div>
          ) : (
            trends && <TrendCharts buckets={trends.buckets} />
          )}
        </div>

        {/* Top Tables */}
        {topCosts && topDuration && (
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-foreground">Performance</h2>
            <TopTables
              topCosts={topCosts.prompts}
              topDuration={topDuration.tools}
              onNavigate={onNavigate}
            />
          </div>
        )}

        {/* Anomaly Alerts */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-foreground">Anomalies</h2>
          <AnomalyAlerts
            anomalies={anomalies}
            isLoading={anomalyLoading}
            error={anomalyError}
            onNavigate={onNavigate}
          />
        </div>

        {/* Recent Traces */}
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
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat card                                                         */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <div className="text-xs text-muted-foreground font-medium">{label}</div>
      <div
        className={`text-xl font-semibold mt-1 tracking-tight ${valueClassName ?? "text-foreground"}`}
      >
        {value}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
