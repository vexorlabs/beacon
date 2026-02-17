import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  MiniMap,
  type NodeTypes,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Skeleton } from "@/components/ui/skeleton";
import { useTraceStore } from "@/store/trace";
import SpanNode from "./SpanNode";
import { useGraphLayout } from "./useGraphLayout";

export default function TraceGraph() {
  const graphData = useTraceStore((s) => s.graphData);
  const isLoading = useTraceStore((s) => s.isLoadingTrace);
  const selectedTraceId = useTraceStore((s) => s.selectedTraceId);
  const selectedSpanId = useTraceStore((s) => s.selectedSpanId);
  const selectSpan = useTraceStore((s) => s.selectSpan);
  const timeTravelIndex = useTraceStore((s) => s.timeTravelIndex);

  const nodeTypes: NodeTypes = useMemo(() => ({ spanNode: SpanNode }), []);

  const rawNodes = useMemo(() => graphData?.nodes ?? [], [graphData?.nodes]);
  const rawEdges = useMemo(() => graphData?.edges ?? [], [graphData?.edges]);
  const { nodes: laidOutNodes, edges } = useGraphLayout(rawNodes, rawEdges);

  // Map from span_id to chronological index (rawNodes preserve backend start_time order)
  const chronoIndex = useMemo(() => {
    const map = new Map<string, number>();
    rawNodes.forEach((n, i) => map.set(n.id, i));
    return map;
  }, [rawNodes]);

  // Apply time-travel dimming and selection highlighting
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

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      selectSpan(node.id);
    },
    [selectSpan],
  );

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
      nodes={styledNodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={onNodeClick}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <MiniMap
        nodeStrokeWidth={3}
        position="bottom-right"
        style={{ width: 120, height: 80 }}
      />
    </ReactFlow>
  );
}
