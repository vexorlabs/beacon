import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  MiniMap,
  Controls,
  type NodeTypes,
  type OnNodesChange,
  type Node,
  type Viewport,
  applyNodeChanges,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Skeleton } from "@/components/ui/skeleton";
import SpanNode from "@/components/TraceGraph/SpanNode";
import { useGraphLayout } from "@/components/TraceGraph/useGraphLayout";
import type { GraphData, SpanNodeData } from "@/lib/types";
import { SPAN_TYPE_COLORS } from "@/lib/span-colors";

interface CompareGraphProps {
  graphData: GraphData | null;
  isLoading: boolean;
  label: string;
  onViewportChange?: (viewport: Viewport) => void;
  externalViewport?: Viewport | null;
  divergenceSpanIds?: string[];
}

function CompareGraphInner({
  graphData,
  isLoading,
  label,
  onViewportChange,
  externalViewport,
  divergenceSpanIds,
}: CompareGraphProps) {
  const { setViewport } = useReactFlow();
  const isSyncingRef = useRef(false);

  const nodeTypes: NodeTypes = useMemo(() => ({ spanNode: SpanNode }), []);

  const rawNodes = useMemo(() => graphData?.nodes ?? [], [graphData?.nodes]);
  const rawEdges = useMemo(() => graphData?.edges ?? [], [graphData?.edges]);
  const { nodes: laidOutNodes, edges: layoutEdges } = useGraphLayout(
    rawNodes,
    rawEdges,
  );

  const enrichedNodes = useMemo(() => {
    if (!divergenceSpanIds || divergenceSpanIds.length === 0) return laidOutNodes;
    const idSet = new Set(divergenceSpanIds);
    return laidOutNodes.map((node) => {
      const data = node.data as SpanNodeData;
      if (idSet.has(data.span_id)) {
        return { ...node, data: { ...data, isDivergent: true } };
      }
      return node;
    });
  }, [laidOutNodes, divergenceSpanIds]);

  const styledEdges = useMemo(() => {
    return layoutEdges.map((edge) => ({
      ...edge,
      animated: true,
      style: { stroke: "#525252", strokeWidth: 1.5 },
    }));
  }, [layoutEdges]);

  const [localNodes, setLocalNodes] = useState<Node[]>([]);

  useEffect(() => {
    setLocalNodes(enrichedNodes);
  }, [enrichedNodes]);

  const onNodesChange: OnNodesChange = useCallback((changes) => {
    setLocalNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  // Apply external viewport (follower mode)
  useEffect(() => {
    if (externalViewport && !isSyncingRef.current) {
      isSyncingRef.current = true;
      setViewport(externalViewport, { duration: 0 });
      requestAnimationFrame(() => {
        isSyncingRef.current = false;
      });
    }
  }, [externalViewport, setViewport]);

  // Report viewport changes (leader mode)
  const handleViewportChange = useCallback(
    (viewport: Viewport) => {
      if (!isSyncingRef.current) {
        onViewportChange?.(viewport);
      }
    },
    [onViewportChange],
  );

  const miniMapNodeColor = useCallback((node: Node<SpanNodeData>) => {
    return SPAN_TYPE_COLORS[node.data.span_type] ?? "#71717a";
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="h-12 w-40 rounded-md" />
          <div className="flex gap-8">
            <Skeleton className="h-12 w-36 rounded-md" />
            <Skeleton className="h-12 w-36 rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No spans in trace {label}
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={localNodes}
      edges={styledEdges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onViewportChange={handleViewportChange}
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
        style={{ width: 100, height: 60, background: "#1a1a1e" }}
      />
    </ReactFlow>
  );
}

export default function CompareGraph(props: CompareGraphProps) {
  return (
    <ReactFlowProvider>
      <CompareGraphInner {...props} />
    </ReactFlowProvider>
  );
}
