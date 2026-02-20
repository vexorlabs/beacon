import { useState } from "react";
import { Check, CheckCircle2, CircleDot, Trash2, XCircle } from "lucide-react";
import type { TraceSummary } from "@/lib/types";

interface TraceListItemProps {
  trace: TraceSummary;
  isSelected: boolean;
  onSelect: (traceId: string) => void;
  onDelete: (traceId: string) => void;
  compareMode?: boolean;
  isCompareSelected?: boolean;
  onCompareToggle?: (traceId: string) => void;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "ok":
      return <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />;
    case "error":
      return <XCircle size={14} className="text-red-400 shrink-0" />;
    default:
      return <CircleDot size={14} className="text-muted-foreground shrink-0" />;
  }
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
  compareMode,
  isCompareSelected,
  onCompareToggle,
}: TraceListItemProps) {
  const [confirming, setConfirming] = useState(false);

  const handleClick = () => {
    if (compareMode && onCompareToggle) {
      onCompareToggle(trace.trace_id);
    } else {
      onSelect(trace.trace_id);
    }
  };

  return (
    <button
      type="button"
      className={`group w-full text-left px-3 py-2 border-b border-border/60 hover:bg-accent transition-colors ${
        isSelected && !compareMode ? "bg-accent" : ""
      } ${isCompareSelected ? "border-l-2 border-l-primary bg-primary/5" : ""}`}
      onClick={handleClick}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {compareMode && (
            <div
              className={`w-3.5 h-3.5 rounded-sm border flex items-center justify-center flex-shrink-0 transition-colors ${
                isCompareSelected
                  ? "bg-primary border-primary"
                  : "border-muted-foreground/40"
              }`}
            >
              {isCompareSelected && (
                <Check size={10} className="text-primary-foreground" />
              )}
            </div>
          )}
          <span
            className="font-medium text-[13px] truncate max-w-[150px] sm:max-w-[220px]"
            title={trace.name}
          >
            {trace.name}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {!compareMode && confirming ? (
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
          ) : !compareMode ? (
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
          ) : null}
          <span className="text-xs text-muted-foreground shrink-0">
            {formatDuration(trace.duration_ms)}
          </span>
          <StatusIcon status={trace.status} />
        </div>
      </div>
    </button>
  );
}
