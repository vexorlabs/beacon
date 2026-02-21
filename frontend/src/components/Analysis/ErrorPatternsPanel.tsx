import { AlertCircle, CheckCircle, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ErrorPatternsResponse } from "@/lib/types";

const CATEGORY_STYLES: Record<string, string> = {
  timeout: "text-amber-400 bg-amber-500/10",
  rate_limit: "text-orange-400 bg-orange-500/10",
  auth: "text-red-400 bg-red-500/10",
  validation: "text-purple-400 bg-purple-500/10",
  network: "text-cyan-400 bg-cyan-500/10",
};

export default function ErrorPatternsPanel({
  data,
  isLoading,
  error,
  onTraceClick,
}: {
  data: ErrorPatternsResponse | null;
  isLoading: boolean;
  error: string | null;
  onTraceClick?: (traceId: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
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

  return (
    <div className="space-y-4">
      <h3 className="text-xs text-muted-foreground font-medium">
        Error Patterns
      </h3>

      {data.patterns.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <CheckCircle size={14} />
          No error patterns detected
        </div>
      )}

      <div className="space-y-2">
        {data.patterns.map((pattern, i) => (
          <div
            key={i}
            className="bg-card border-[0.5px] border-border rounded-md p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Layers size={12} className="text-muted-foreground" />
                <span className="text-[13px] font-medium text-foreground">
                  {pattern.pattern_name}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${CATEGORY_STYLES[pattern.category] ?? "text-muted-foreground bg-muted"}`}
                >
                  {pattern.category}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {pattern.count}x
                </span>
              </div>
            </div>
            <p className="text-[13px] text-muted-foreground leading-relaxed mb-2">
              {pattern.common_root_cause}
            </p>
            {pattern.example_trace_ids.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {pattern.example_trace_ids.slice(0, 3).map((traceId) => (
                  <Badge
                    key={traceId}
                    variant="secondary"
                    className="cursor-pointer hover:bg-secondary/80 text-[11px]"
                    onClick={() => onTraceClick?.(traceId)}
                  >
                    {traceId.slice(0, 8)}
                  </Badge>
                ))}
                {pattern.example_trace_ids.length > 3 && (
                  <span className="text-[11px] text-muted-foreground self-center">
                    +{pattern.example_trace_ids.length - 3} more
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
