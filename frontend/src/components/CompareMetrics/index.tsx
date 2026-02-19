import type { TraceDetail } from "@/lib/types";

interface CompareMetricsProps {
  traceA: TraceDetail;
  traceB: TraceDetail;
}

interface MetricRow {
  label: string;
  valueA: string;
  valueB: string;
  delta: string;
  direction: "better" | "worse" | "neutral";
}

function computeErrorRate(trace: TraceDetail): number {
  if (trace.spans.length === 0) return 0;
  const errorCount = trace.spans.filter((s) => s.status === "error").length;
  return errorCount / trace.spans.length;
}

function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`;
}

function formatTokens(n: number): string {
  return n.toLocaleString();
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "running";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function formatDelta(a: number, b: number, formatter: (n: number) => string): string {
  const diff = b - a;
  const sign = diff > 0 ? "+" : "";
  if (a === 0 && b === 0) return "-";
  const pct = a !== 0 ? ` (${sign}${((diff / a) * 100).toFixed(0)}%)` : "";
  return `${sign}${formatter(diff)}${pct}`;
}

function buildMetrics(traceA: TraceDetail, traceB: TraceDetail): MetricRow[] {
  const errorRateA = computeErrorRate(traceA);
  const errorRateB = computeErrorRate(traceB);

  return [
    {
      label: "Cost",
      valueA: formatCost(traceA.total_cost_usd),
      valueB: formatCost(traceB.total_cost_usd),
      delta: formatDelta(traceA.total_cost_usd, traceB.total_cost_usd, formatCost),
      direction: traceB.total_cost_usd <= traceA.total_cost_usd ? "better" : "worse",
    },
    {
      label: "Tokens",
      valueA: formatTokens(traceA.total_tokens),
      valueB: formatTokens(traceB.total_tokens),
      delta: formatDelta(traceA.total_tokens, traceB.total_tokens, formatTokens),
      direction: traceB.total_tokens <= traceA.total_tokens ? "better" : "worse",
    },
    {
      label: "Duration",
      valueA: formatDuration(traceA.duration_ms),
      valueB: formatDuration(traceB.duration_ms),
      delta:
        traceA.duration_ms !== null && traceB.duration_ms !== null
          ? formatDelta(traceA.duration_ms, traceB.duration_ms, formatDuration)
          : "-",
      direction:
        traceA.duration_ms !== null && traceB.duration_ms !== null
          ? traceB.duration_ms <= traceA.duration_ms
            ? "better"
            : "worse"
          : "neutral",
    },
    {
      label: "Spans",
      valueA: String(traceA.span_count),
      valueB: String(traceB.span_count),
      delta: formatDelta(traceA.span_count, traceB.span_count, String),
      direction: "neutral",
    },
    {
      label: "Error Rate",
      valueA: formatPercent(errorRateA),
      valueB: formatPercent(errorRateB),
      delta:
        errorRateA === errorRateB
          ? "-"
          : `${errorRateB > errorRateA ? "+" : ""}${((errorRateB - errorRateA) * 100).toFixed(1)}pp`,
      direction: errorRateB <= errorRateA ? "better" : "worse",
    },
  ];
}

const DIRECTION_COLORS = {
  better: "text-emerald-400",
  worse: "text-red-400",
  neutral: "text-muted-foreground",
} as const;

export default function CompareMetrics({ traceA, traceB }: CompareMetricsProps) {
  const metrics = buildMetrics(traceA, traceB);

  return (
    <div className="flex items-center gap-6 px-4 py-3 border-b border-border bg-card/30 overflow-x-auto">
      {metrics.map((m) => (
        <div key={m.label} className="flex flex-col gap-0.5 min-w-0">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
            {m.label}
          </span>
          <div className="flex items-baseline gap-2 text-xs">
            <span className="text-blue-300">{m.valueA}</span>
            <span className="text-muted-foreground/50">vs</span>
            <span className="text-purple-300">{m.valueB}</span>
            {m.delta !== "-" && (
              <span className={`text-[10px] ${DIRECTION_COLORS[m.direction]}`}>
                {m.delta}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
