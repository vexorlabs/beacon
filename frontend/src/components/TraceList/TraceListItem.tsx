import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { TraceSummary } from "@/lib/types";

interface TraceListItemProps {
  trace: TraceSummary;
  isSelected: boolean;
  onSelect: (traceId: string) => void;
  onDelete: (traceId: string) => void;
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
  onDelete,
}: TraceListItemProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <button
      type="button"
      className={`group w-full text-left px-3 py-2 border-b border-border hover:bg-accent transition-colors ${
        isSelected ? "bg-accent" : ""
      }`}
      onClick={() => onSelect(trace.trace_id)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-[13px] truncate">{trace.name}</span>
        <div className="flex items-center gap-1.5">
          {confirming ? (
            <span
              className="flex items-center gap-1"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                className="text-[11px] text-red-400 hover:text-red-300 font-medium"
                onClick={() => {
                  onDelete(trace.trace_id);
                  setConfirming(false);
                }}
              >
                Delete
              </button>
              <button
                type="button"
                className="text-[11px] text-muted-foreground hover:text-foreground"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-opacity p-0.5"
              onClick={(e) => {
                e.stopPropagation();
                setConfirming(true);
              }}
              aria-label="Delete trace"
            >
              <Trash2 size={12} />
            </button>
          )}
          <Badge variant={STATUS_VARIANT[trace.status] ?? "secondary"}>
            {trace.status}
          </Badge>
        </div>
      </div>
      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
        <span>{formatDuration(trace.duration_ms)}</span>
        <span>{trace.span_count} spans</span>
        <span className="ml-auto">{formatRelativeTime(trace.start_time)}</span>
      </div>
    </button>
  );
}
