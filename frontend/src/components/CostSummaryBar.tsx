import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Download,
  Flag,
  GitCompareArrows,
  Maximize2,
  Minimize2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTraceStore } from "@/store/trace";
import { exportTrace, findBaselineTrace } from "@/lib/api";
import type { TraceSummary } from "@/lib/types";

export type ViewMode = "graph" | "timeline";

interface CostSummaryBarProps {
  expanded: boolean;
  onToggleExpand: () => void;
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function CostSummaryBar({
  expanded,
  onToggleExpand,
}: CostSummaryBarProps) {
  const navigate = useNavigate();
  const selectedTrace = useTraceStore((s) => s.selectedTrace);
  const updateTraceTags = useTraceStore((s) => s.updateTraceTags);
  const [baselineTrace, setBaselineTrace] = useState<TraceSummary | null>(null);

  const isBaseline = selectedTrace?.tags?.baseline === "true";
  const traceId = selectedTrace?.trace_id ?? null;
  const lookupKey = traceId && !isBaseline ? traceId : null;

  // Look up the baseline trace when the selected trace changes.
  useEffect(() => {
    if (!lookupKey) {
      return;
    }
    let cancelled = false;
    void findBaselineTrace(lookupKey).then((result) => {
      if (!cancelled) setBaselineTrace(result);
    });
    return () => { cancelled = true; };
  }, [lookupKey]);

  // Only show baseline if lookup is still relevant
  const effectiveBaseline = lookupKey ? baselineTrace : null;

  const handleToggleBaseline = useCallback(() => {
    if (!selectedTrace) return;
    const newTags = { ...selectedTrace.tags };
    if (isBaseline) {
      delete newTags.baseline;
    } else {
      newTags.baseline = "true";
    }
    void updateTraceTags(selectedTrace.trace_id, newTags);
  }, [selectedTrace, isBaseline, updateTraceTags]);

  const handleCompareBaseline = useCallback(() => {
    if (!selectedTrace || !effectiveBaseline) return;
    navigate(`/compare/${effectiveBaseline.trace_id}/${selectedTrace.trace_id}`);
  }, [selectedTrace, effectiveBaseline, navigate]);

  const handleExport = useCallback(
    async (format: "json" | "otel" | "csv") => {
      if (!selectedTrace) return;
      const blob = await exportTrace(selectedTrace.trace_id, format);
      const prefix = selectedTrace.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .slice(0, 30);
      const idShort = selectedTrace.trace_id.slice(0, 8);
      const ext = format === "otel" ? "otel.json" : format === "csv" ? "csv" : "json";
      triggerDownload(blob, `${prefix}-${idShort}.${ext}`);
    },
    [selectedTrace],
  );

  return (
    <div className="h-11 flex items-center gap-2 px-3 border-b border-border text-xs text-muted-foreground bg-card/50">
      {selectedTrace ? (
        <div className="min-w-0 flex flex-1 items-center gap-2">
          <span
            className="font-medium text-foreground truncate max-w-[170px] sm:max-w-[240px] lg:max-w-[340px]"
            title={selectedTrace.name}
          >
            {selectedTrace.name}
          </span>
          <span className="inline-flex shrink-0 items-center rounded-md border border-border bg-background/50 px-1.5 py-0.5 text-[11px]">
            {selectedTrace.span_count} spans
          </span>
          {selectedTrace.duration_ms !== null && (
            <span className="hidden sm:inline-flex shrink-0 items-center rounded-md border border-border bg-background/50 px-1.5 py-0.5 text-[11px]">
              {(selectedTrace.duration_ms / 1000).toFixed(1)}s
            </span>
          )}
          <span className="hidden md:inline-flex shrink-0 items-center rounded-md border border-border bg-background/50 px-1.5 py-0.5 text-[11px]">
            {selectedTrace.total_tokens.toLocaleString()} tokens
          </span>
          <span className="hidden lg:inline-flex shrink-0 items-center rounded-md border border-border bg-background/50 px-1.5 py-0.5 text-[11px]">
            ${selectedTrace.total_cost_usd.toFixed(4)}
          </span>
        </div>
      ) : (
        <span className="text-muted-foreground flex-1">No trace selected</span>
      )}

      <div className="ml-auto flex shrink-0 items-center gap-1">
        {selectedTrace && (
          <>
            {/* Baseline toggle */}
            <button
              type="button"
              onClick={handleToggleBaseline}
              title={isBaseline ? "Remove baseline tag" : "Mark as baseline"}
              className={`flex items-center justify-center gap-1 h-7 rounded-md px-2 text-[11px] transition-colors ${
                isBaseline
                  ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              }`}
            >
              <Flag size={12} />
              {isBaseline ? "Baseline" : ""}
            </button>

            {/* Compare vs baseline */}
            {!isBaseline && effectiveBaseline && (
              <button
                type="button"
                onClick={handleCompareBaseline}
                title={`Compare against baseline: ${effectiveBaseline.name}`}
                className="flex items-center justify-center gap-1 h-7 rounded-md px-2 text-[11px] text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
              >
                <GitCompareArrows size={12} />
                <span className="hidden xl:inline">vs Baseline</span>
              </button>
            )}

            {/* Export dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  title="Export trace"
                  className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
                >
                  <Download size={14} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={() => void handleExport("json")}>
                  <Download size={13} className="mr-2" />
                  Export JSON
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => void handleExport("otel")}>
                  <Download size={13} className="mr-2" />
                  Export OTEL JSON
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => void handleExport("csv")}>
                  <Download size={13} className="mr-2" />
                  Export CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
        <button
          type="button"
          onClick={onToggleExpand}
          title={expanded ? "Exit fullscreen" : "Fullscreen canvas"}
          className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
        >
          {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>
    </div>
  );
}
