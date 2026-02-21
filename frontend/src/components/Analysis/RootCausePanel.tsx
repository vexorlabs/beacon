import { AlertCircle, Loader2, Target, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { RootCauseAnalysisResponse } from "@/lib/types";

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "text-emerald-400 bg-emerald-500/10",
  medium: "text-amber-400 bg-amber-500/10",
  low: "text-muted-foreground bg-muted",
};

function confidenceLabel(value: number): { label: string; level: string } {
  if (value >= 0.8) return { label: "High", level: "high" };
  if (value >= 0.5) return { label: "Medium", level: "medium" };
  return { label: "Low", level: "low" };
}

export default function RootCausePanel({
  data,
  isLoading,
  error,
  onSpanClick,
}: {
  data: RootCauseAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  onSpanClick?: (spanId: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-20 w-full" />
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

  const conf = confidenceLabel(data.confidence);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs text-muted-foreground font-medium">
          Root Cause Analysis
        </h3>
        <span
          className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${CONFIDENCE_STYLES[conf.level]}`}
        >
          {conf.label} confidence ({Math.round(data.confidence * 100)}%)
        </span>
      </div>

      <div className="bg-red-500/5 border-[0.5px] border-red-500/20 rounded-md p-3">
        <div className="flex items-start gap-2">
          <Target size={14} className="text-red-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] text-red-400 font-medium mb-1">
              Root Cause
            </div>
            <p className="text-[13px] text-foreground leading-relaxed">
              {data.root_cause}
            </p>
          </div>
        </div>
      </div>

      {data.affected_spans.length > 0 && (
        <div>
          <div className="text-[11px] text-muted-foreground font-medium mb-2">
            Affected Spans
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.affected_spans.map((spanId) => (
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
        </div>
      )}

      <div className="bg-emerald-500/5 border-[0.5px] border-emerald-500/20 rounded-md p-3">
        <div className="flex items-start gap-2">
          <Wrench size={14} className="text-emerald-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] text-emerald-400 font-medium mb-1">
              Suggested Fix
            </div>
            <p className="text-[13px] text-foreground leading-relaxed">
              {data.suggested_fix}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
