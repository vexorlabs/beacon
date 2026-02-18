import { cn } from "@/lib/utils";
import { SPAN_TYPE_BAR_STYLES } from "@/lib/span-colors";
import type { TimelineSpan } from "./useTimelineLayout";
import { ROW_HEIGHT, BAR_HEIGHT } from "./useTimelineLayout";

function formatDuration(ms: number | null): string {
  if (ms === null) return "running\u2026";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

interface TimelineBarProps {
  item: TimelineSpan;
  isSelected: boolean;
  isFuture: boolean;
  onSelect: (spanId: string) => void;
}

export default function TimelineBar({
  item,
  isSelected,
  isFuture,
  onSelect,
}: TimelineBarProps) {
  const { span, row, leftPx, widthPx, isOnCriticalPath, durationMs, costUsd } =
    item;
  const barStyle = SPAN_TYPE_BAR_STYLES[span.span_type] ?? SPAN_TYPE_BAR_STYLES.custom;
  const isRunning = span.end_time === null;

  // Pick a single ring style with explicit priority: error > selected > critical path
  const ringStyle =
    span.status === "error"
      ? "ring-2 ring-red-500/60"
      : isSelected
        ? "ring-2 ring-ring"
        : isOnCriticalPath
          ? "ring-1 ring-yellow-400/60"
          : "";

  return (
    <div
      role="button"
      tabIndex={0}
      className="absolute group cursor-pointer"
      style={{
        top: row * ROW_HEIGHT + (ROW_HEIGHT - BAR_HEIGHT) / 2,
        left: leftPx,
        width: widthPx,
        height: BAR_HEIGHT,
        opacity: isFuture ? 0.3 : 1,
      }}
      onClick={() => onSelect(span.span_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect(span.span_id);
      }}
    >
      {/* Bar */}
      <div
        className={cn(
          "h-full rounded-sm border transition-colors overflow-hidden flex items-center",
          barStyle,
          ringStyle,
        )}
      >
        {/* Pulse indicator for running spans */}
        {isRunning && (
          <div className="absolute right-0 top-0 bottom-0 w-1 bg-current animate-pulse rounded-r-sm" />
        )}
        {/* Label inside bar (only if wide enough) */}
        {widthPx > 60 && (
          <span className="text-[10px] truncate px-1.5 leading-none">
            {span.name}
          </span>
        )}
      </div>

      {/* Hover tooltip — positioned above bar to avoid ScrollArea clipping */}
      <div className="absolute z-50 hidden group-hover:block left-0 bottom-full mb-1 px-2.5 py-1.5 rounded-md bg-zinc-900 border border-border/60 text-xs text-foreground shadow-lg whitespace-nowrap pointer-events-none">
        <div className="font-medium">{span.name}</div>
        <div className="text-muted-foreground mt-0.5">
          {span.span_type.replace("_", " ")}
        </div>
        <div className="text-muted-foreground">
          {formatDuration(durationMs)}
          {costUsd !== null && ` \u00b7 $${costUsd.toFixed(4)}`}
        </div>
        {span.status === "error" && span.error_message && (
          <div className="text-red-400 mt-0.5 max-w-[240px] truncate">
            {span.error_message}
          </div>
        )}
      </div>
    </div>
  );
}
