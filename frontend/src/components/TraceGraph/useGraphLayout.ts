import { useMemo } from "react";
import dagre from "@dagrejs/dagre";
import type { GraphNode, GraphEdge } from "@/lib/types";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 60;

export function useGraphLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  return useMemo(() => {
    if (nodes.length === 0) return { nodes: [], edges: [] };

    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 60 });

    for (const node of nodes) {
      g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    }
    for (const edge of edges) {
      g.setEdge(edge.source, edge.target);
    }

    dagre.layout(g);

    const laidOutNodes = nodes.map((node) => {
      const pos = g.node(node.id);
      return {
        ...node,
        position: {
          x: pos.x - NODE_WIDTH / 2,
          y: pos.y - NODE_HEIGHT / 2,
        },
      };
    });

    return { nodes: laidOutNodes, edges };
  }, [nodes, edges]);
}
