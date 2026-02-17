import { Separator } from "@/components/ui/separator";
import { useTraceStore } from "@/store/trace";

export default function CostSummaryBar() {
  const selectedTrace = useTraceStore((s) => s.selectedTrace);

  if (!selectedTrace) return null;

  const cost = selectedTrace.total_cost_usd;
  const tokens = selectedTrace.total_tokens;
  const duration = selectedTrace.duration_ms;

  return (
    <div className="flex items-center gap-4 px-4 py-1.5 border-b border-border text-xs text-muted-foreground bg-muted/30">
      <span className="font-medium text-foreground truncate max-w-xs">
        {selectedTrace.name}
      </span>
      <Separator orientation="vertical" className="h-4" />
      <span>{tokens.toLocaleString()} tokens</span>
      <Separator orientation="vertical" className="h-4" />
      <span>${cost.toFixed(4)}</span>
      {duration !== null && (
        <>
          <Separator orientation="vertical" className="h-4" />
          <span>{(duration / 1000).toFixed(1)}s</span>
        </>
      )}
      <Separator orientation="vertical" className="h-4" />
      <span>{selectedTrace.span_count} spans</span>
    </div>
  );
}
