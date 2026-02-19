import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useTraceStore } from "@/store/trace";
import { useCompareStore } from "@/store/compare";
import { importTrace } from "@/lib/api";
import type { TraceExportData } from "@/lib/types";
import TraceListItem from "./TraceListItem";
import TraceFilter from "./TraceFilter";
import SearchBar from "./SearchBar";

export default function TraceList() {
  const navigate = useNavigate();
  const traces = useTraceStore((s) => s.traces);
  const isLoading = useTraceStore((s) => s.isLoadingTraces);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const loadTraces = useTraceStore((s) => s.loadTraces);
  const deleteTrace = useTraceStore((s) => s.deleteTrace);
  const traceFilter = useTraceStore((s) => s.traceFilter);

  const compareMode = useCompareStore((s) => s.compareMode);
  const selectedTraceIds = useCompareStore((s) => s.selectedTraceIds);
  const toggleCompareMode = useCompareStore((s) => s.toggleCompareMode);
  const toggleTraceSelection = useCompareStore((s) => s.toggleTraceSelection);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => {
    void loadTraces();
  }, [loadTraces]);

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (traceFilter.status !== "all" && t.status !== traceFilter.status)
        return false;
      if (
        traceFilter.nameQuery &&
        !t.name.toLowerCase().includes(traceFilter.nameQuery.toLowerCase())
      )
        return false;
      return true;
    });
  }, [traces, traceFilter]);

  const handleImport = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      setImportError(null);
      const file = e.target.files?.[0];
      if (!file) return;

      const MAX_IMPORT_SIZE = 50 * 1024 * 1024; // 50 MB
      if (file.size > MAX_IMPORT_SIZE) {
        setImportError("File too large (max 50 MB)");
        return;
      }

      try {
        const text = await file.text();
        const data = JSON.parse(text) as TraceExportData;
        const result = await importTrace(data);
        await loadTraces();
        navigate(`/traces/${result.trace_id}`);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Import failed";
        setImportError(msg);
      } finally {
        // Reset input so the same file can be re-selected
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [loadTraces, navigate],
  );

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Traces</h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Import trace"
            className="text-muted-foreground hover:text-foreground hover:bg-secondary/50 flex items-center justify-center w-6 h-6 rounded-md transition-colors"
          >
            <Upload size={13} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => void handleImport(e)}
          />
          <button
            type="button"
            onClick={toggleCompareMode}
            className={`text-[11px] font-medium px-2 py-0.5 rounded-md transition-colors ${
              compareMode
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            {compareMode ? "Cancel" : "Compare"}
          </button>
        </div>
      </div>

      {importError && (
        <div className="px-3 py-2 border-b border-border bg-destructive/10 text-destructive text-[11px]">
          Import failed: {importError}
        </div>
      )}

      {/* Compare action bar — visible when in compare mode */}
      {compareMode && (
        <div className="px-3 py-2 border-b border-border bg-card/50">
          {selectedTraceIds.length < 2 ? (
            <p className="text-[11px] text-muted-foreground text-center">
              Select {2 - selectedTraceIds.length} trace
              {selectedTraceIds.length === 0 ? "s" : ""} to compare
            </p>
          ) : (
            <button
              type="button"
              className="group w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-md border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 transition-all"
              onClick={() =>
                navigate(
                  `/compare/${selectedTraceIds[0]}/${selectedTraceIds[1]}`,
                )
              }
            >
              <span>Compare</span>
              <span className="text-primary/60 group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </button>
          )}
        </div>
      )}

      <SearchBar />
      <TraceFilter />
      <ScrollArea className="flex-1 min-h-0">
        {isLoading && traces.length === 0 && (
          <div className="flex flex-col gap-0">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="px-3 py-2 border-b border-border">
                <div className="flex items-center justify-between gap-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-5 w-10" />
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-10 ml-auto" />
                </div>
              </div>
            ))}
          </div>
        )}
        {!isLoading && traces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No traces yet. Run an instrumented agent to see traces here.
          </div>
        )}
        {!isLoading && traces.length > 0 && filteredTraces.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No traces match the current filter.
          </div>
        )}
        {filteredTraces.map((trace) => (
          <TraceListItem
            key={trace.trace_id}
            trace={trace}
            isSelected={trace.trace_id === selectedTraceId}
            onSelect={(id) => navigate(`/traces/${id}`)}
            onDelete={(id) => {
              void deleteTrace(id);
              if (id === selectedTraceId) {
                navigate("/traces");
              }
            }}
            compareMode={compareMode}
            isCompareSelected={selectedTraceIds.includes(trace.trace_id)}
            onCompareToggle={toggleTraceSelection}
          />
        ))}
      </ScrollArea>
    </div>
  );
}
