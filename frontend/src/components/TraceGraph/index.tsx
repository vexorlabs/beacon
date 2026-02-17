import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  MiniMap,
  type NodeTypes,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
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

  const rawNodes = graphData?.nodes ?? [];
  const rawEdges = graphData?.edges ?? [];
  const { nodes: laidOutNodes, edges } = useGraphLayout(rawNodes, rawEdges);

  // Apply time-travel dimming and selection highlighting
  const styledNodes = useMemo(() => {
    return laidOutNodes.map((node, index) => {
      const isFuture =
        timeTravelIndex !== null && index >= timeTravelIndex;
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
  }, [laidOutNodes, timeTravelIndex, selectedSpanId]);

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
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Loading graph...
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
