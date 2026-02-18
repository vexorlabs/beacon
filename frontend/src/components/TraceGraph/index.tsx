import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  MiniMap,
  Controls,
  type NodeTypes,
  type NodeMouseHandler,
  type OnNodesChange,
  type Node,
  applyNodeChanges,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Skeleton } from "@/components/ui/skeleton";
import { useTraceStore } from "@/store/trace";
import SpanNode from "./SpanNode";
import { useGraphLayout } from "./useGraphLayout";
import type { SpanNodeData, SpanType } from "@/lib/types";

const SPAN_TYPE_COLORS: Record<SpanType, string> = {
  llm_call: "#3b82f6",
  tool_use: "#10b981",
  browser_action: "#f97316",
  file_operation: "#f59e0b",
  shell_command: "#a855f7",
  agent_step: "#71717a",
  chain: "#71717a",
  custom: "#71717a",
};

function TraceGraphInner() {
  const navigate = useNavigate();
  const graphData = useTraceStore((s) => s.graphData);
  const isLoading = useTraceStore((s) => s.isLoadingTrace);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectedSpanId = useTraceStore((s) => s.selectedSpanId);
  const selectSpan = useTraceStore((s) => s.selectSpan);
  const timeTravelIndex = useTraceStore((s) => s.timeTravelIndex);

  const { fitView } = useReactFlow();

  const nodeTypes: NodeTypes = useMemo(() => ({ spanNode: SpanNode }), []);

  const rawNodes = useMemo(() => graphData?.nodes ?? [], [graphData?.nodes]);
  const rawEdges = useMemo(() => graphData?.edges ?? [], [graphData?.edges]);
  const { nodes: laidOutNodes, edges: layoutEdges } = useGraphLayout(
    rawNodes,
    rawEdges,
  );

  // Map from span_id to chronological index (rawNodes preserve backend start_time order)
  const chronoIndex = useMemo(() => {
    const map = new Map<string, number>();
    rawNodes.forEach((n, i) => map.set(n.id, i));
    return map;
  }, [rawNodes]);

  // Apply time-travel dimming, selection highlighting, and animated edges
  const styledNodes = useMemo(() => {
    return laidOutNodes.map((node) => {
      const idx = chronoIndex.get(node.id) ?? 0;
      const isFuture = timeTravelIndex !== null && idx >= timeTravelIndex;
      const isSelected = node.id === selectedSpanId;
      return {
        ...node,
        style: {
          opacity: isFuture ? 0.3 : 1,
          ...(isSelected
            ? { boxShadow: "0 0 0 2px hsl(var(--ring))" }
            : {}),
        },
      };
    });
  }, [laidOutNodes, chronoIndex, timeTravelIndex, selectedSpanId]);

  const styledEdges = useMemo(() => {
    return layoutEdges.map((edge) => ({
      ...edge,
      animated: true,
      style: { stroke: "#525252", strokeWidth: 1.5 },
    }));
  }, [layoutEdges]);

  // Local node state so React Flow can handle dragging
  const [localNodes, setLocalNodes] = useState<Node[]>([]);

  // Sync store-derived nodes into local state when layout/styling changes
  useEffect(() => {
    setLocalNodes(styledNodes);
  }, [styledNodes]);

  const onNodesChange: OnNodesChange = useCallback((changes) => {
    setLocalNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      selectSpan(node.id);
      if (selectedTraceId) {
        navigate(`/traces/${selectedTraceId}/${node.id}`, { replace: true });
      }
    },
    [selectSpan, selectedTraceId, navigate],
  );

  // Center + zoom on a node when double-clicked
  const onNodeDoubleClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      fitView({ nodes: [{ id: node.id }], duration: 300, padding: 0.5 });
    },
    [fitView],
  );

  const miniMapNodeColor = useCallback((node: Node<SpanNodeData>) => {
    return SPAN_TYPE_COLORS[node.data.span_type] ?? "#71717a";
  }, []);

  if (!selectedTraceId) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Select a trace to view its graph
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="h-12 w-40 rounded-md" />
          <div className="flex gap-8">
            <Skeleton className="h-12 w-36 rounded-md" />
            <Skeleton className="h-12 w-36 rounded-md" />
          </div>
          <div className="flex gap-8">
            <Skeleton className="h-12 w-32 rounded-md" />
            <Skeleton className="h-12 w-32 rounded-md" />
            <Skeleton className="h-12 w-32 rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={localNodes}
      edges={styledEdges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onNodeClick={onNodeClick}
      onNodeDoubleClick={onNodeDoubleClick}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={2}
      colorMode="dark"
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls
        showInteractive={false}
        position="bottom-left"
        className="!bg-zinc-900 !border-zinc-700 !rounded-md !shadow-lg [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!fill-zinc-300 [&>button:hover]:!bg-zinc-700"
      />
      <MiniMap
        nodeStrokeWidth={3}
        nodeColor={miniMapNodeColor}
        maskColor="oklch(0.13 0.004 272 / 0.7)"
        position="bottom-right"
        style={{ width: 120, height: 80, background: "#1a1a1e" }}
      />
    </ReactFlow>
  );
}

export default function TraceGraph() {
  return (
    <ReactFlowProvider>
      <TraceGraphInner />
    </ReactFlowProvider>
  );
}
