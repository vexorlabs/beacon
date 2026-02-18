import type { SpanType } from "./types";

/** Hex colors for programmatic use (minimap, canvas drawing). */
export const SPAN_TYPE_COLORS: Record<SpanType, string> = {
  llm_call: "#3b82f6",
  tool_use: "#10b981",
  browser_action: "#f97316",
  file_operation: "#f59e0b",
  shell_command: "#a855f7",
  agent_step: "#71717a",
  chain: "#71717a",
  custom: "#71717a",
};

/** Tailwind classes for SpanNode graph nodes (dark bg, colored border + text). */
export const SPAN_TYPE_STYLES: Record<SpanType, string> = {
  llm_call: "bg-blue-950/40 border-blue-500/40 text-blue-300",
  tool_use: "bg-emerald-950/40 border-emerald-500/40 text-emerald-300",
  browser_action: "bg-orange-950/40 border-orange-500/40 text-orange-300",
  file_operation: "bg-amber-950/40 border-amber-500/40 text-amber-300",
  shell_command: "bg-purple-950/40 border-purple-500/40 text-purple-300",
  agent_step: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
  chain: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
  custom: "bg-zinc-800/40 border-zinc-500/40 text-zinc-300",
};

/** Tailwind classes for timeline bars (higher opacity fills for Gantt chart). */
export const SPAN_TYPE_BAR_STYLES: Record<SpanType, string> = {
  llm_call: "bg-blue-500/30 border-blue-500/50 text-blue-200",
  tool_use: "bg-emerald-500/30 border-emerald-500/50 text-emerald-200",
  browser_action: "bg-orange-500/30 border-orange-500/50 text-orange-200",
  file_operation: "bg-amber-500/30 border-amber-500/50 text-amber-200",
  shell_command: "bg-purple-500/30 border-purple-500/50 text-purple-200",
  agent_step: "bg-zinc-500/30 border-zinc-500/50 text-zinc-200",
  chain: "bg-zinc-500/30 border-zinc-500/50 text-zinc-200",
  custom: "bg-zinc-500/30 border-zinc-500/50 text-zinc-200",
};

/** Dot color classes for small indicators (e.g. slowest spans list). */
export const SPAN_TYPE_DOT_COLORS: Record<SpanType, string> = {
  llm_call: "bg-blue-500",
  tool_use: "bg-emerald-500",
  browser_action: "bg-orange-500",
  file_operation: "bg-amber-500",
  shell_command: "bg-purple-500",
  agent_step: "bg-zinc-500",
  chain: "bg-zinc-500",
  custom: "bg-zinc-500",
};
