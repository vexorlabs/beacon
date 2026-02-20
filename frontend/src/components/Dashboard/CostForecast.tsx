import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { TrendBucket } from "@/lib/types";

function linearRegression(
  data: { x: number; y: number }[],
): { slope: number; intercept: number } {
  const n = data.length;
  if (n === 0) return { slope: 0, intercept: 0 };
  const sumX = data.reduce((s, d) => s + d.x, 0);
  const sumY = data.reduce((s, d) => s + d.y, 0);
  const sumXY = data.reduce((s, d) => s + d.x * d.y, 0);
  const sumXX = data.reduce((s, d) => s + d.x * d.x, 0);
  const denom = n * sumXX - sumX * sumX;
  if (denom === 0) return { slope: 0, intercept: sumY / n };
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return { slope, intercept };
}

export default function CostForecast({
  buckets,
}: {
  buckets: TrendBucket[];
}) {
  const hasCostData = buckets.some((b) => b.total_cost > 0);

  if (!hasCostData) {
    return (
      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <div className="text-xs text-muted-foreground font-medium">
          30-Day Cost Forecast
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xl font-semibold text-foreground tracking-tight">
            $0.00
          </span>
          <span className="text-xs text-muted-foreground">No cost data</span>
        </div>
      </div>
    );
  }

  const points = buckets.map((b, i) => ({ x: i, y: b.total_cost }));
  const { slope, intercept } = linearRegression(points);

  // Project 30 days ahead from the end of the data
  const startDay = buckets.length;
  let projected = 0;
  for (let d = 0; d < 30; d++) {
    const daily = slope * (startDay + d) + intercept;
    projected += Math.max(0, daily);
  }

  const isIncreasing = slope > 0.0001;
  const isDecreasing = slope < -0.0001;

  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <div className="text-xs text-muted-foreground font-medium">
        Projected 30-Day Cost
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xl font-semibold text-foreground tracking-tight">
          ${projected.toFixed(2)}
        </span>
        {isIncreasing ? (
          <span className="flex items-center gap-1 text-xs text-amber-400">
            <TrendingUp size={14} />
            increasing
          </span>
        ) : isDecreasing ? (
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <TrendingDown size={14} />
            decreasing
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Minus size={14} />
            stable
          </span>
        )}
      </div>
    </div>
  );
}
