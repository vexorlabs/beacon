import { useTraceStore } from "@/store/trace";

export default function SpanDetail() {
  const selectedSpan = useTraceStore((s) => s.selectedSpan);

  if (!selectedSpan) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground p-4 text-center">
        Select a span to see details
      </div>
    );
  }

  return (
    <div className="p-4 overflow-auto h-full">
      <h3 className="font-semibold text-sm">{selectedSpan.name}</h3>
      <div className="mt-2 text-xs text-muted-foreground space-y-1">
        <div>Type: {selectedSpan.span_type}</div>
        <div>Status: {selectedSpan.status}</div>
        {selectedSpan.error_message && (
          <div className="text-red-500">Error: {selectedSpan.error_message}</div>
        )}
        <div>
          Duration:{" "}
          {selectedSpan.end_time !== null
            ? `${((selectedSpan.end_time - selectedSpan.start_time) * 1000).toFixed(0)}ms`
            : "running..."}
        </div>
      </div>
      <div className="mt-4">
        <h4 className="text-xs font-semibold mb-1">Attributes</h4>
        <pre className="text-xs bg-muted rounded p-2 overflow-auto max-h-[400px]">
          {JSON.stringify(selectedSpan.attributes, null, 2)}
        </pre>
      </div>
    </div>
  );
}
