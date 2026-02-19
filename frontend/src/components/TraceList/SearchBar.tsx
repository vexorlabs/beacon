import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, X } from "lucide-react";
import { searchTraces } from "@/lib/api";
import type { SearchResultItem } from "@/lib/types";

interface SearchBarProps {
  autoFocus?: boolean;
  onResultSelect?: () => void;
  placeholder?: string;
}

export default function SearchBar({
  autoFocus = false,
  onResultSelect,
  placeholder = "Search spans across traces...",
}: SearchBarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const doSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const res = await searchTraces(q, { limit: 10 });
      setResults(res.results);
      setOpen(res.results.length > 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    clearTimeout(timerRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    timerRef.current = setTimeout(() => {
      void doSearch(query);
    }, 300);
    return () => clearTimeout(timerRef.current);
  }, [query, doSearch]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (!autoFocus) return;
    const id = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(id);
  }, [autoFocus]);

  const handleSelect = (item: SearchResultItem) => {
    navigate(`/traces/${item.trace_id}/${item.span_id}`);
    setQuery("");
    setResults([]);
    setOpen(false);
    onResultSelect?.();
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search
          size={12}
          className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          ref={inputRef}
          type="search"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          className="h-8 w-full bg-background border border-input rounded-md pl-7 pr-7 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
        />
        {query && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => {
              setQuery("");
              setResults([]);
              setOpen(false);
            }}
          >
            <X size={12} />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-popover border border-border rounded-md shadow-lg max-h-64 overflow-y-auto">
          {loading && (
            <div className="px-3 py-2 text-xs text-muted-foreground">
              Searching...
            </div>
          )}
          {results.map((item, i) => (
            <button
              key={`${item.trace_id}-${item.span_id}-${i}`}
              type="button"
              className="w-full text-left px-3 py-2 hover:bg-accent transition-colors border-b border-border last:border-b-0"
              onClick={() => handleSelect(item)}
            >
              <div className="text-[12px] font-medium text-foreground truncate">
                {item.name}
              </div>
              <div className="text-[11px] text-muted-foreground truncate mt-0.5">
                {item.match_context}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
