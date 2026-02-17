import { Badge } from "@/components/ui/badge";
import type { TraceSummary } from "@/lib/types";

interface TraceListItemProps {
  trace: TraceSummary;
  isSelected: boolean;
  onSelect: (traceId: string) => void;
}

const STATUS_VARIANT: Record<string, "default" | "destructive" | "secondary"> =
  {
    ok: "default",
    error: "destructive",
    unset: "secondary",
  };

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "running...";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function TraceListItem({
  trace,
  isSelected,
  onSelect,
}: TraceListItemProps) {
  return (
    <button
      type="button"
      className={`w-full text-left px-3 py-2 border-b border-border hover:bg-accent transition-colors ${
        isSelected ? "bg-accent" : ""
      }`}
      onClick={() => onSelect(trace.trace_id)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-sm truncate">{trace.name}</span>
        <Badge variant={STATUS_VARIANT[trace.status] ?? "secondary"}>
          {trace.status}
        </Badge>
      </div>
      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
        <span>{formatDuration(trace.duration_ms)}</span>
        <span>{trace.span_count} spans</span>
        <span className="ml-auto">{formatRelativeTime(trace.start_time)}</span>
      </div>
    </button>
  );
}
