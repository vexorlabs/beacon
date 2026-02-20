import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MoreHorizontal, Search, X } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTraceStore } from "@/store/trace";
import { useCompareStore } from "@/store/compare";
import { importTrace } from "@/lib/api";
import type { SpanStatus } from "@/lib/types";
import type { TraceExportData } from "@/lib/types";
import TraceListItem from "./TraceListItem";
import SearchBar from "./SearchBar";

export default function TraceList() {
  const navigate = useNavigate();
  const traces = useTraceStore((s) => s.traces);
  const isLoading = useTraceStore((s) => s.isLoadingTraces);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const loadTraces = useTraceStore((s) => s.loadTraces);
  const deleteTrace = useTraceStore((s) => s.deleteTrace);
  const traceFilter = useTraceStore((s) => s.traceFilter);
  const setTraceFilter = useTraceStore((s) => s.setTraceFilter);

  const compareMode = useCompareStore((s) => s.compareMode);
  const selectedTraceIds = useCompareStore((s) => s.selectedTraceIds);
  const toggleCompareMode = useCompareStore((s) => s.toggleCompareMode);
  const toggleTraceSelection = useCompareStore((s) => s.toggleTraceSelection);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [showSearchModal, setShowSearchModal] = useState(false);

  useEffect(() => {
    void loadTraces();
  }, [loadTraces]);

  const [tagFilterInput, setTagFilterInput] = useState("");

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (traceFilter.status !== "all" && t.status !== traceFilter.status)
        return false;
      if (traceFilter.tags.length > 0) {
        const traceTagEntries = Object.entries(t.tags).map(
          ([k, v]) => `${k}:${v}`,
        );
        if (
          !traceFilter.tags.every((ft) =>
            traceTagEntries.some((te) =>
              te.toLowerCase().includes(ft.toLowerCase()),
            ),
          )
        ) {
          return false;
        }
      }
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

  const hasActiveFilter = traceFilter.status !== "all" || traceFilter.tags.length > 0;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      const isEditable =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        target?.isContentEditable;

      if (
        (event.metaKey || event.ctrlKey) &&
        event.key.toLowerCase() === "k" &&
        !isEditable
      ) {
        event.preventDefault();
        setShowSearchModal(true);
        return;
      }

      if (event.key === "Escape") {
        setShowSearchModal(false);
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleStatusFilterChange = (value: string) => {
    setTraceFilter({ status: value as "all" | SpanStatus });
  };

  return (
    <div className="relative flex h-full flex-col">
      <div className="relative border-b border-border bg-card/30">
        <div className="h-11 px-3 flex items-center justify-between gap-2">
          <div className="min-w-0 flex items-center gap-2">
            <h2 className="text-[13px] font-semibold">Traces</h2>
            <Badge variant="secondary" className="text-[10px]">
              {filteredTraces.length}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              title="Search spans (Cmd/Ctrl+K)"
              onClick={() => setShowSearchModal(true)}
              className={`flex items-center justify-center w-7 h-7 rounded-md transition-colors ${
                showSearchModal || hasActiveFilter
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
              }`}
            >
              <Search size={14} />
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  title="Trace actions"
                  className="text-muted-foreground hover:text-foreground hover:bg-secondary/60 flex items-center justify-center w-7 h-7 rounded-md transition-colors"
                >
                  <MoreHorizontal size={14} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={toggleCompareMode}>
                  {compareMode ? `Exit compare (${selectedTraceIds.length}/2)` : "Compare"}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => fileInputRef.current?.click()}>
                  Import
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => void handleImport(e)}
          />
        </div>
      </div>

      {showSearchModal && (
        <div
          className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[1px] p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowSearchModal(false);
            }
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Search spans"
        >
          <div className="mx-auto mt-16 w-full max-w-xl rounded-xl border border-border bg-popover shadow-2xl">
            <div className="flex h-11 items-center justify-between border-b border-border px-3">
              <div className="flex items-center gap-2">
                <Search size={13} className="text-muted-foreground" />
                <span className="text-xs font-semibold">Search spans</span>
              </div>
              <button
                type="button"
                aria-label="Close search"
                onClick={() => setShowSearchModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={14} />
              </button>
            </div>
            <div className="p-3 space-y-3">
              <SearchBar
                autoFocus
                onResultSelect={() => setShowSearchModal(false)}
                placeholder="Search spans and jump to a result..."
              />
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-muted-foreground shrink-0">
                  Trace status
                </span>
                <select
                  value={traceFilter.status}
                  onChange={(e) => handleStatusFilterChange(e.target.value)}
                  className="h-8 w-28 shrink-0 bg-background border border-input rounded-md px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">All</option>
                  <option value="ok">OK</option>
                  <option value="error">Error</option>
                  <option value="unset">Running</option>
                </select>
                {traceFilter.status !== "all" && (
                  <button
                    type="button"
                    onClick={() => setTraceFilter({ status: "all" })}
                    className="text-[11px] text-muted-foreground hover:text-foreground"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-muted-foreground shrink-0">
                  Tags
                </span>
                <input
                  type="text"
                  placeholder="Filter by tag (e.g. env:prod)"
                  value={tagFilterInput}
                  onChange={(e) => setTagFilterInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && tagFilterInput.trim()) {
                      setTraceFilter({
                        tags: [...traceFilter.tags, tagFilterInput.trim()],
                      });
                      setTagFilterInput("");
                    }
                  }}
                  className="h-8 flex-1 bg-background border border-input rounded-md px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              {traceFilter.tags.length > 0 && (
                <div className="flex items-center gap-1 flex-wrap">
                  {traceFilter.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-0.5 rounded-full bg-primary/10 border border-primary/20 px-1.5 py-0 text-[11px] text-primary"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() =>
                          setTraceFilter({
                            tags: traceFilter.tags.filter((t) => t !== tag),
                          })
                        }
                      >
                        <X size={10} />
                      </button>
                    </span>
                  ))}
                  <button
                    type="button"
                    onClick={() => setTraceFilter({ tags: [] })}
                    className="text-[11px] text-muted-foreground hover:text-foreground"
                  >
                    Clear tags
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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

      <ScrollArea className="flex-1 min-h-0">
        {isLoading && traces.length === 0 && (
          <div className="flex flex-col gap-0">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="px-3 py-2 border-b border-border">
                <div className="flex items-center justify-between gap-2">
                  <Skeleton className="h-4 w-32" />
                  <div className="flex items-center gap-1.5">
                    <Skeleton className="h-3 w-10" />
                    <Skeleton className="h-3.5 w-3.5 rounded-full" />
                  </div>
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
