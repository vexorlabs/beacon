import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Link, Unlink, Sparkles, Loader2, AlertCircle } from "lucide-react";
import type { Viewport } from "@xyflow/react";
import CompareGraph from "@/components/CompareGraph";
import CompareMetrics from "@/components/CompareMetrics";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompareStore } from "@/store/compare";

export default function ComparePage() {
  const { traceIdA, traceIdB } = useParams<{
    traceIdA: string;
    traceIdB: string;
  }>();
  const navigate = useNavigate();

  const traceA = useCompareStore((s) => s.traceA);
  const traceB = useCompareStore((s) => s.traceB);
  const graphDataA = useCompareStore((s) => s.graphDataA);
  const graphDataB = useCompareStore((s) => s.graphDataB);
  const isLoading = useCompareStore((s) => s.isLoading);
  const error = useCompareStore((s) => s.error);
  const loadComparison = useCompareStore((s) => s.loadComparison);
  const reset = useCompareStore((s) => s.reset);
  const clearSelection = useCompareStore((s) => s.clearSelection);

  // AI comparison state
  const divergencePoints = useCompareStore((s) => s.divergencePoints);
  const compareSummary = useCompareStore((s) => s.compareSummary);
  const isAnalyzingComparison = useCompareStore((s) => s.isAnalyzingComparison);
  const analysisError = useCompareStore((s) => s.analysisError);
  const runCompareAnalysis = useCompareStore((s) => s.runCompareAnalysis);

  // Viewport sync — off by default
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [syncViewport, setSyncViewport] = useState<Viewport | null>(null);
  const [lastSource, setLastSource] = useState<"A" | "B" | null>(null);

  const handleViewportChangeA = useCallback(
    (v: Viewport) => {
      if (!syncEnabled) return;
      setLastSource("A");
      setSyncViewport(v);
    },
    [syncEnabled],
  );

  const handleViewportChangeB = useCallback(
    (v: Viewport) => {
      if (!syncEnabled) return;
      setLastSource("B");
      setSyncViewport(v);
    },
    [syncEnabled],
  );

  useEffect(() => {
    if (traceIdA && traceIdB) {
      void loadComparison(traceIdA, traceIdB);
      clearSelection();
    }
    return () => reset();
  }, [traceIdA, traceIdB, loadComparison, reset, clearSelection]);

  // Compute divergence span IDs per side
  const divergenceSpanIdsA = useMemo(
    () =>
      divergencePoints
        .map((dp) => dp.span_a)
        .filter((id): id is string => id !== null),
    [divergencePoints],
  );
  const divergenceSpanIdsB = useMemo(
    () =>
      divergencePoints
        .map((dp) => dp.span_b)
        .filter((id): id is string => id !== null),
    [divergencePoints],
  );

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-red-400">{error}</p>
        <button
          type="button"
          onClick={() => navigate("/traces")}
          className="text-sm text-primary hover:underline"
        >
          Back to traces
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border shrink-0">
        <button
          type="button"
          onClick={() => navigate("/traces")}
          className="text-muted-foreground hover:text-foreground transition-colors p-0.5"
          aria-label="Back to traces"
        >
          <ArrowLeft size={16} />
        </button>
        <h1 className="text-[13px] font-semibold text-foreground">
          Compare Traces
        </h1>
        <div className="flex items-center gap-2 text-xs ml-auto">
          {isLoading ? (
            <Skeleton className="h-5 w-48" />
          ) : (
            <>
              <span className="px-2 py-0.5 rounded bg-blue-950/40 text-blue-300 border border-blue-500/30 truncate max-w-[200px]">
                A: {traceA?.name ?? "Unknown"}
              </span>
              <span className="text-muted-foreground">vs</span>
              <span className="px-2 py-0.5 rounded bg-purple-950/40 text-purple-300 border border-purple-500/30 truncate max-w-[200px]">
                B: {traceB?.name ?? "Unknown"}
              </span>
            </>
          )}

          {/* AI Compare button */}
          {traceIdA && traceIdB && !isLoading && (
            <button
              type="button"
              onClick={() => void runCompareAnalysis(traceIdA, traceIdB)}
              disabled={isAnalyzingComparison}
              title="AI-powered comparison analysis"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors disabled:opacity-50"
            >
              {isAnalyzingComparison ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Sparkles size={12} />
              )}
              AI Compare
            </button>
          )}
        </div>
      </div>

      {/* AI analysis summary */}
      {compareSummary && (
        <div className="px-4 py-3 border-b border-border bg-orange-950/20">
          <div className="flex items-start gap-2">
            <Sparkles size={14} className="text-orange-400 mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-[13px] text-foreground leading-relaxed">
                {compareSummary}
              </p>
              {divergencePoints.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-[11px] font-medium text-orange-300 uppercase tracking-wide">
                    Divergence Points
                  </p>
                  {divergencePoints.map((dp, i) => (
                    <p key={i} className="text-xs text-muted-foreground">
                      {dp.description}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Analysis error */}
      {analysisError && (
        <div className="px-4 py-2 border-b border-border bg-red-950/20 flex items-center gap-2 text-xs text-red-400">
          <AlertCircle size={12} />
          {analysisError}
        </div>
      )}

      {/* Metrics diff */}
      {traceA && traceB && <CompareMetrics traceA={traceA} traceB={traceB} />}

      {/* Side-by-side graphs */}
      <div className="flex flex-1 min-h-0 relative">
        {/* Graph A */}
        <div className="flex-1 min-w-0 border-r border-border flex flex-col">
          <div className="px-3 py-1.5 border-b border-border/60 text-xs text-muted-foreground bg-card/30 shrink-0">
            <span className="text-blue-300 font-medium">A</span>
            {traceA && (
              <span className="ml-2 truncate">{traceA.name}</span>
            )}
          </div>
          <div className="flex-1 min-h-0">
            <CompareGraph
              graphData={graphDataA}
              isLoading={isLoading}
              label="A"
              onViewportChange={handleViewportChangeA}
              externalViewport={
                syncEnabled && lastSource === "B" ? syncViewport : null
              }
              divergenceSpanIds={divergenceSpanIdsA}
            />
          </div>
        </div>

        {/* Sync toggle — centered on the divider */}
        <button
          type="button"
          onClick={() => setSyncEnabled((v) => !v)}
          title={syncEnabled ? "Unsync pan & zoom" : "Sync pan & zoom"}
          className={`absolute top-12 left-1/2 -translate-x-1/2 z-10 flex items-center justify-center w-7 h-7 rounded-full border transition-colors ${
            syncEnabled
              ? "bg-primary/20 border-primary/40 text-primary"
              : "bg-card border-border text-muted-foreground hover:text-foreground hover:border-foreground/20"
          }`}
        >
          {syncEnabled ? <Link size={12} /> : <Unlink size={12} />}
        </button>

        {/* Graph B */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="px-3 py-1.5 border-b border-border/60 text-xs text-muted-foreground bg-card/30 shrink-0">
            <span className="text-purple-300 font-medium">B</span>
            {traceB && (
              <span className="ml-2 truncate">{traceB.name}</span>
            )}
          </div>
          <div className="flex-1 min-h-0">
            <CompareGraph
              graphData={graphDataB}
              isLoading={isLoading}
              label="B"
              onViewportChange={handleViewportChangeB}
              externalViewport={
                syncEnabled && lastSource === "A" ? syncViewport : null
              }
              divergenceSpanIds={divergenceSpanIdsB}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
