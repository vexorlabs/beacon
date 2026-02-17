import { useTraceStore } from "@/store/trace";
import type { SpanStatus } from "@/lib/types";

type FilterStatus = "all" | SpanStatus;

export default function TraceFilter() {
  const traceFilter = useTraceStore((s) => s.traceFilter);
  const setTraceFilter = useTraceStore((s) => s.setTraceFilter);

  return (
    <div className="px-3 py-2 border-b border-border flex items-center gap-2">
      <input
        type="search"
        placeholder="Filter traces..."
        value={traceFilter.nameQuery}
        onChange={(e) => setTraceFilter({ nameQuery: e.target.value })}
        className="flex-1 bg-background border border-input rounded-sm px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
      />
      <select
        value={traceFilter.status}
        onChange={(e) =>
          setTraceFilter({ status: e.target.value as FilterStatus })
        }
        className="bg-background border border-input rounded-sm px-1 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="all">All</option>
        <option value="ok">OK</option>
        <option value="error">Error</option>
        <option value="unset">Running</option>
      </select>
    </div>
  );
}
