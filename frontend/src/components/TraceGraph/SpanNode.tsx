import { Handle, Position } from "@xyflow/react";
import type { NodeProps, Node } from "@xyflow/react";
import type { SpanNodeData } from "@/lib/types";
import { SPAN_TYPE_STYLES } from "@/lib/span-colors";
import { useAnalysisStore } from "@/store/analysis";

function formatDuration(ms: number | null): string {
  if (ms === null) return "...";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

type SpanNodeType = Node<SpanNodeData, "spanNode">;

const STATUS_LABEL: Record<string, string> = {
  ok: "OK",
  error: "Error",
  unset: "Running",
};

const FRAMEWORK_BADGE: Record<string, { label: string; color: string }> = {
  langchain: { label: "LC", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  crewai: { label: "Crew", color: "bg-violet-500/20 text-violet-300 border-violet-500/30" },
  autogen: { label: "AG", color: "bg-sky-500/20 text-sky-300 border-sky-500/30" },
  llamaindex: { label: "LI", color: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  ollama: { label: "Oll", color: "bg-zinc-500/20 text-zinc-300 border-zinc-500/30" },
};

export default function SpanNode({ data }: NodeProps<SpanNodeType>) {
  const highlightedSpanIds = useAnalysisStore((s) => s.highlightedSpanIds);
  const isHighlighted = highlightedSpanIds.includes(data.span_id);
  const baseStyle = SPAN_TYPE_STYLES[data.span_type] ?? SPAN_TYPE_STYLES.custom;
  const isDivergent = data.isDivergent === true;
  const ringClass = isHighlighted
    ? "ring-2 ring-amber-400/80 animate-pulse"
    : isDivergent
      ? "ring-2 ring-orange-400/70 animate-pulse"
      : data.status === "error"
        ? "ring-2 ring-red-500/60"
        : "";

  const frameworkBadge = data.framework ? FRAMEWORK_BADGE[data.framework] : null;

  const tooltipLines = [
    data.name,
    `${data.span_type.replace("_", " ")} · ${STATUS_LABEL[data.status] ?? data.status}`,
    ...(data.framework ? [`Framework: ${data.framework}`] : []),
    `Duration: ${formatDuration(data.duration_ms)}`,
    ...(data.cost_usd !== null ? [`Cost: $${data.cost_usd.toFixed(4)}`] : []),
  ].join("\n");

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-zinc-500" />
      <div
        title={tooltipLines}
        className={`group/node relative px-3 py-2 rounded-md border-2 min-w-[160px] max-w-[220px] cursor-pointer transition-shadow hover:shadow-lg hover:shadow-black/30 ${baseStyle} ${ringClass}`}
      >
        <div className="text-[10px] font-medium uppercase tracking-wide opacity-60 flex items-center gap-1">
          <span>
            <span className="opacity-100 tabular-nums">#{data.sequence}</span>
            <span className="mx-1">&middot;</span>
            {data.span_type.replace("_", " ")}
          </span>
          {frameworkBadge && (
            <span
              className={`inline-flex items-center px-1 py-px rounded text-[8px] font-semibold leading-none border ${frameworkBadge.color}`}
            >
              {frameworkBadge.label}
            </span>
          )}
        </div>
        <div className="text-xs font-semibold truncate mt-0.5">{data.name}</div>
        <div className="text-[10px] opacity-70 mt-0.5">
          {formatDuration(data.duration_ms)}
          {data.cost_usd !== null && ` · $${data.cost_usd.toFixed(4)}`}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-zinc-500"
      />
    </>
  );
}
