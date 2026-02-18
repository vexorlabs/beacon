import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { SPAN_TYPE_DOT_COLORS } from "@/lib/span-colors";
import type { TimelineSpan } from "./useTimelineLayout";

function formatDuration(ms: number | null): string {
  if (ms === null) return "...";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

interface SlowestSpansProps {
  spans: TimelineSpan[];
  onSelect: (spanId: string) => void;
}

export default function SlowestSpans({ spans, onSelect }: SlowestSpansProps) {
  const [open, setOpen] = useState(false);

  if (spans.length === 0) return null;

  return (
    <div className="border-t border-border/60 bg-card/50 flex-none">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-1.5 w-full text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronRight
          size={12}
          className={cn(
            "transition-transform duration-150",
            open && "rotate-90",
          )}
        />
        Slowest Spans
      </button>
      {open && (
        <div className="px-3 pb-2 space-y-0.5">
          {spans.map((ts) => (
            <button
              key={ts.span.span_id}
              type="button"
              onClick={() => onSelect(ts.span.span_id)}
              className="flex items-center gap-2 w-full px-2 py-1 rounded-md hover:bg-secondary/50 text-xs transition-colors"
            >
              <div
                className={cn(
                  "w-2 h-2 rounded-full flex-none",
                  SPAN_TYPE_DOT_COLORS[ts.span.span_type] ??
                    SPAN_TYPE_DOT_COLORS.custom,
                )}
              />
              <span className="truncate flex-1 text-left text-foreground">
                {ts.span.name}
              </span>
              <span className="text-muted-foreground flex-none">
                {formatDuration(ts.durationMs)}
              </span>
              {ts.costUsd !== null && (
                <span className="text-muted-foreground flex-none">
                  ${ts.costUsd.toFixed(4)}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
