import { Handle, Position } from "@xyflow/react";
import type { NodeProps, Node } from "@xyflow/react";
import type { SpanNodeData, SpanType } from "@/lib/types";

const SPAN_TYPE_STYLES: Record<SpanType, string> = {
  llm_call: "bg-blue-950/40 border-blue-500/40 text-blue-300",
  tool_use: "bg-emerald-950/40 border-emerald-500/40 text-emerald-300",
  browser_action: "bg-orange-950/40 border-orange-500/40 text-orange-300",
  file_operation: "bg-amber-950/40 border-amber-500/40 text-amber-300",
  shell_command: "bg-purple-950/40 border-purple-500/40 text-purple-300",
  agent_step: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
  chain: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
  custom: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "...";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

type SpanNodeType = Node<SpanNodeData, "spanNode">;

export default function SpanNode({ data }: NodeProps<SpanNodeType>) {
  const baseStyle = SPAN_TYPE_STYLES[data.span_type] ?? SPAN_TYPE_STYLES.custom;
  const errorRing = data.status === "error" ? "ring-2 ring-red-500/60" : "";

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-zinc-500" />
      <div
        className={`px-3 py-2 rounded-md border-2 min-w-[160px] max-w-[220px] ${baseStyle} ${errorRing}`}
      >
        <div className="text-[10px] font-medium uppercase tracking-wide opacity-60">
          {data.span_type.replace("_", " ")}
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
