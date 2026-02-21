import { AlertCircle, DollarSign } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { CostOptimizationResponse } from "@/lib/types";

const TYPE_STYLES: Record<string, string> = {
  redundant_call: "text-amber-400 bg-amber-500/10",
  model_downgrade: "text-blue-400 bg-blue-500/10",
  cacheable: "text-emerald-400 bg-emerald-500/10",
  token_reduction: "text-purple-400 bg-purple-500/10",
};

function formatUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

export default function CostOptimizationPanel({
  data,
  isLoading,
  error,
  onSpanClick,
}: {
  data: CostOptimizationResponse | null;
  isLoading: boolean;
  error: string | null;
  onSpanClick?: (spanId: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-red-400">
        <AlertCircle size={14} className="shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  if (!data) return null;

  const totalSavings = data.suggestions.reduce(
    (sum, s) => sum + s.estimated_savings_usd,
    0,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs text-muted-foreground font-medium">
          Cost Optimization
        </h3>
        {totalSavings > 0 && (
          <span className="text-[11px] font-medium text-emerald-400">
            Est. savings: {formatUsd(totalSavings)}
          </span>
        )}
      </div>

      {data.suggestions.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <DollarSign size={14} />
          No optimization opportunities found
        </div>
      )}

      <div className="space-y-2">
        {data.suggestions.map((suggestion, i) => (
          <div
            key={i}
            className="bg-card border-[0.5px] border-border rounded-md p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <span
                className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${TYPE_STYLES[suggestion.type] ?? "text-muted-foreground bg-muted"}`}
              >
                {suggestion.type.replace(/_/g, " ")}
              </span>
              <span className="text-[11px] font-medium text-emerald-400">
                save {formatUsd(suggestion.estimated_savings_usd)}
              </span>
            </div>
            <p className="text-[13px] text-foreground leading-relaxed">
              {suggestion.description}
            </p>
            {suggestion.affected_spans.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {suggestion.affected_spans.map((spanId) => (
                  <Badge
                    key={spanId}
                    variant="secondary"
                    className="cursor-pointer hover:bg-secondary/80 text-[11px]"
                    onClick={() => onSpanClick?.(spanId)}
                  >
                    {spanId.slice(0, 8)}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
