import { AlertCircle, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { TraceSummaryAnalysisResponse } from "@/lib/types";

export default function TraceSummaryCard({
  data,
  isLoading,
  error,
  onGenerate,
  onSpanClick,
}: {
  data: TraceSummaryAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  onGenerate?: () => void;
  onSpanClick?: (spanId: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
          <Loader2 size={14} className="animate-spin" />
          Generating summary...
        </div>
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <div className="flex items-center gap-2 text-xs text-red-400">
          <AlertCircle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!data) {
    if (!onGenerate) return null;
    return (
      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <button
          type="button"
          onClick={onGenerate}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <FileText size={14} />
          Generate AI summary
        </button>
      </div>
    );
  }

  return (
    <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
      <h3 className="text-xs text-muted-foreground font-medium mb-2">
        Trace Summary
      </h3>
      <p className="text-[13px] text-foreground leading-relaxed mb-3">
        {data.summary}
      </p>

      {data.key_events.length > 0 && (
        <div>
          <div className="text-[11px] text-muted-foreground font-medium mb-2">
            Key Events
          </div>
          <div className="space-y-1.5">
            {data.key_events.map((event, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-[11px] text-muted-foreground mt-0.5 shrink-0">
                  {i + 1}.
                </span>
                <span className="text-[13px] text-foreground leading-relaxed">
                  {event.description}
                </span>
                <Badge
                  variant="secondary"
                  className="cursor-pointer hover:bg-secondary/80 text-[11px] shrink-0"
                  onClick={() => onSpanClick?.(event.span_id)}
                >
                  {event.span_id.slice(0, 8)}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
