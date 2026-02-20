import type { TopCostItem, TopDurationItem } from "@/lib/types";

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function TopTables({
  topCosts,
  topDuration,
  onNavigate,
}: {
  topCosts: TopCostItem[];
  topDuration: TopDurationItem[];
  onNavigate: (path: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <h3 className="text-xs text-muted-foreground font-medium mb-3">
          Most Expensive Prompts
        </h3>
        {topCosts.length === 0 ? (
          <p className="text-xs text-muted-foreground">No LLM calls yet.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-xs text-muted-foreground font-medium">
                <th className="text-left pb-2">Name</th>
                <th className="text-left pb-2">Model</th>
                <th className="text-right pb-2">Cost</th>
                <th className="text-right pb-2">Tokens</th>
              </tr>
            </thead>
            <tbody>
              {topCosts.map((item) => (
                <tr
                  key={item.span_id}
                  onClick={() => onNavigate(`/traces/${item.trace_id}`)}
                  className="text-[13px] text-foreground hover:bg-secondary/50 cursor-pointer transition-colors"
                >
                  <td className="py-1.5 pr-2 truncate max-w-[160px]">
                    {item.name}
                  </td>
                  <td className="py-1.5 pr-2 text-muted-foreground text-xs">
                    {item.model}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">
                    ${item.cost.toFixed(4)}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {item.tokens.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-card border-[0.5px] border-border rounded-lg p-4 shadow-[0_2px_8px_oklch(0_0_0/0.15)]">
        <h3 className="text-xs text-muted-foreground font-medium mb-3">
          Slowest Tools
        </h3>
        {topDuration.length === 0 ? (
          <p className="text-xs text-muted-foreground">No tool calls yet.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-xs text-muted-foreground font-medium">
                <th className="text-left pb-2">Name</th>
                <th className="text-right pb-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {topDuration.map((item) => (
                <tr
                  key={item.span_id}
                  onClick={() => onNavigate(`/traces/${item.trace_id}`)}
                  className="text-[13px] text-foreground hover:bg-secondary/50 cursor-pointer transition-colors"
                >
                  <td className="py-1.5 pr-2 truncate max-w-[200px]">
                    {item.name}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {formatDuration(item.duration_ms)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
