import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { TrendBucket } from "@/lib/types";

const COLORS = {
  cost: "#7c6dfc",
  tokens: "#34d399",
  traces: "#60a5fa",
  errors: "#f87171",
  grid: "rgba(255,255,255,0.06)",
  axis: "rgba(255,255,255,0.35)",
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
  formatter: (v: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-popover border border-border rounded-md px-2.5 py-1.5 text-xs shadow-md">
      <div className="text-muted-foreground mb-0.5">
        {label ? formatDate(label) : ""}
      </div>
      <div className="text-foreground font-medium">
        {formatter(payload[0].value)}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <h3 className="text-xs text-muted-foreground font-medium mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function TrendCharts({
  buckets,
}: {
  buckets: TrendBucket[];
}) {
  const errorRateData = buckets.map((b) => ({
    ...b,
    error_rate: Math.round((1 - b.success_rate) * 100),
  }));

  return (
    <div className="grid grid-cols-2 gap-4">
      <ChartCard title="Cost Over Time">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={buckets}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={COLORS.grid}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              cursor={{ stroke: "rgba(255,255,255,0.08)" }}
              content={
                <ChartTooltip
                  formatter={(v: number) => `$${v.toFixed(4)}`}
                />
              }
            />
            <Line
              type="monotone"
              dataKey="total_cost"
              stroke={COLORS.cost}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, fill: COLORS.cost }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Token Usage">
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={buckets}>
            <defs>
              <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COLORS.tokens} stopOpacity={0.3} />
                <stop
                  offset="100%"
                  stopColor={COLORS.tokens}
                  stopOpacity={0.02}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={COLORS.grid}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v: number) => v.toLocaleString()}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              cursor={{ stroke: "rgba(255,255,255,0.08)" }}
              content={
                <ChartTooltip
                  formatter={(v: number) => v.toLocaleString() + " tokens"}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="total_tokens"
              stroke={COLORS.tokens}
              strokeWidth={2}
              fill="url(#tokenGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Trace Count">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={buckets}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={COLORS.grid}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              content={
                <ChartTooltip
                  formatter={(v: number) => `${v} traces`}
                />
              }
            />
            <Bar
              dataKey="trace_count"
              fill={COLORS.traces}
              radius={[3, 3, 0, 0]}
              maxBarSize={24}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Error Rate">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={errorRateData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={COLORS.grid}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v: number) => `${v}%`}
              tick={{ fontSize: 11, fill: COLORS.axis }}
              axisLine={false}
              tickLine={false}
              width={35}
              domain={[0, "auto"]}
            />
            <Tooltip
              cursor={{ stroke: "rgba(255,255,255,0.08)" }}
              content={
                <ChartTooltip
                  formatter={(v: number) => `${v}%`}
                />
              }
            />
            <Line
              type="monotone"
              dataKey="error_rate"
              stroke={COLORS.errors}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, fill: COLORS.errors }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
