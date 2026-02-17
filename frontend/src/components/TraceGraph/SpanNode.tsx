import { Handle, Position } from "@xyflow/react";
import type { NodeProps, Node } from "@xyflow/react";
import type { SpanNodeData, SpanType } from "@/lib/types";

const SPAN_TYPE_STYLES: Record<SpanType, string> = {
  llm_call: "bg-blue-50 border-blue-400 text-blue-900",
  tool_use: "bg-green-50 border-green-400 text-green-900",
  browser_action: "bg-orange-50 border-orange-400 text-orange-900",
  file_operation: "bg-yellow-50 border-yellow-400 text-yellow-900",
  shell_command: "bg-purple-50 border-purple-400 text-purple-900",
  agent_step: "bg-gray-50 border-gray-400 text-gray-900",
  chain: "bg-gray-50 border-gray-400 text-gray-900",
  custom: "bg-gray-50 border-gray-400 text-gray-900",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "...";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

type SpanNodeType = Node<SpanNodeData, "spanNode">;

export default function SpanNode({ data }: NodeProps<SpanNodeType>) {
  const baseStyle = SPAN_TYPE_STYLES[data.span_type] ?? SPAN_TYPE_STYLES.custom;
  const errorRing = data.status === "error" ? "ring-2 ring-red-500" : "";

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
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
        className="!bg-gray-400"
      />
    </>
  );
}
