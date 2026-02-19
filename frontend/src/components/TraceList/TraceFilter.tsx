import { useTraceStore } from "@/store/trace";
import type { SpanStatus } from "@/lib/types";

type FilterStatus = "all" | SpanStatus;

export default function TraceFilter() {
  const traceFilter = useTraceStore((s) => s.traceFilter);
  const setTraceFilter = useTraceStore((s) => s.setTraceFilter);

  return (
    <div className="flex items-center gap-2">
      <input
        type="search"
        placeholder="Filter trace names..."
        value={traceFilter.nameQuery}
        onChange={(e) => setTraceFilter({ nameQuery: e.target.value })}
        className="h-8 min-w-0 flex-1 bg-background border border-input rounded-md px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
      />
      <select
        value={traceFilter.status}
        onChange={(e) =>
          // Safe: values come from hardcoded <option> elements below
          setTraceFilter({ status: e.target.value as FilterStatus })
        }
        className="h-8 w-24 shrink-0 bg-background border border-input rounded-md px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="all">All</option>
        <option value="ok">OK</option>
        <option value="error">Error</option>
        <option value="unset">Running</option>
      </select>
    </div>
  );
}
