import { useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  Position,
  MarkerType,
  ConnectionLineType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphNode, GraphEdge } from "@/lib/types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const nodeColors: Record<string, string> = {
  UserClaim: "#6366f1",
  Claim: "#3b82f6",
  VerifiedFact: "#22c55e",
  ClaimedFact: "#f59e0b",
  Entity: "#64748b",
  Verdict: "#8b5cf6",
};

const nodeTypeLabels: Record<string, string> = {
  UserClaim: "Afirmația ta",
  Claim: "Afirmație stocată",
  VerifiedFact: "Fapt verificat",
  ClaimedFact: "Fapt revendicat",
  Entity: "Entitate",
  Verdict: "Verdict",
};

function truncate(text: string, max: number): string {
  if (!text) return "";
  if (text.length <= max) return text;
  return text.slice(0, max - 1).trim() + "…";
}

function formatRelation(label: string): string {
  if (!label) return "";
  const cleaned = label.replace(/_/g, " ").toLowerCase();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function KGGraphPreview({ nodes: graphNodes, edges: graphEdges }: Props) {
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    // Hierarchical layout: separate by node type into columns
    const typeOrder = ["UserClaim", "Claim", "VerifiedFact", "ClaimedFact", "Entity", "Verdict"];
    const nodesByType: Record<string, GraphNode[]> = {};
    graphNodes.forEach((n) => {
      if (!nodesByType[n.type]) nodesByType[n.type] = [];
      nodesByType[n.type].push(n);
    });

    const COLUMN_WIDTH = 320;
    const ROW_HEIGHT = 140;
    const positions = new Map<string, { x: number; y: number }>();

    let colIdx = 0;
    typeOrder.forEach((type) => {
      const list = nodesByType[type];
      if (!list || list.length === 0) return;
      list.forEach((n, i) => {
        positions.set(n.id, {
          x: colIdx * COLUMN_WIDTH + 40,
          y: i * ROW_HEIGHT + 40,
        });
      });
      colIdx++;
    });

    graphNodes.forEach((n) => {
      if (!positions.has(n.id)) {
        positions.set(n.id, { x: colIdx * COLUMN_WIDTH + 40, y: 40 });
      }
    });

    const flowNodes: Node[] = graphNodes.map((n) => {
      const pos = positions.get(n.id)!;
      const typeLabel = nodeTypeLabels[n.type] || n.type;
      const displayLabel = truncate(n.label || "", 90);

      return {
        id: n.id,
        position: pos,
        data: {
          label: (
            <div style={{ textAlign: "center", lineHeight: 1.3 }} title={n.label}>
              <div
                style={{
                  fontSize: "9px",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  opacity: 0.85,
                  marginBottom: "4px",
                  fontWeight: 700,
                }}
              >
                {typeLabel}
              </div>
              <div style={{ fontSize: "12px", fontWeight: 500, whiteSpace: "normal" }}>
                {displayLabel}
              </div>
            </div>
          ),
        },
        style: {
          background: nodeColors[n.type] || "#64748b",
          color: "#fff",
          border: "2px solid rgba(255,255,255,0.25)",
          borderRadius: "12px",
          padding: "10px 14px",
          width: 240,
          minHeight: 60,
          boxShadow: "0 4px 12px rgba(0,0,0,0.18)",
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      } as Node;
    });

    const flowEdges: Edge[] = graphEdges.map((e) => {
      const fullLabel = formatRelation(e.label || "");
      const isHovered = hoveredEdge === e.id;
      const shortLabel = truncate(fullLabel, 22);

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: isHovered ? fullLabel : shortLabel,
        type: "smoothstep",
        animated: true,
        style: {
          stroke: isHovered ? "#3b82f6" : "#94a3b8",
          strokeWidth: isHovered ? 2.5 : 1.8,
        },
        labelStyle: {
          fontSize: 11,
          fill: "#1e293b",
          fontWeight: 600,
        },
        labelBgStyle: {
          fill: "#ffffff",
          fillOpacity: 0.95,
        },
        labelBgPadding: [6, 4] as [number, number],
        labelBgBorderRadius: 6,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHovered ? "#3b82f6" : "#94a3b8",
          width: 18,
          height: 18,
        },
      } as Edge;
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [graphNodes, graphEdges, hoveredEdge]);

  const maxNodesInColumn = useMemo(() => {
    const counts: Record<string, number> = {};
    graphNodes.forEach((n) => {
      counts[n.type] = (counts[n.type] || 0) + 1;
    });
    return Math.max(1, ...Object.values(counts));
  }, [graphNodes]);

  const height = Math.max(420, maxNodesInColumn * 140 + 100);

  const presentTypes = useMemo(() => {
    const set = new Set(graphNodes.map((n) => n.type));
    return Array.from(set);
  }, [graphNodes]);

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 border-b border-border bg-muted/30">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Legendă:
        </span>
        {presentTypes.map((type) => (
          <div key={type} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded"
              style={{ background: nodeColors[type] || "#64748b" }}
            />
            <span className="text-xs text-foreground">
              {nodeTypeLabels[type] || type}
            </span>
          </div>
        ))}
        <span className="text-xs text-muted-foreground ml-auto italic hidden md:inline">
          Scroll = zoom · drag = navigare · hover pe muchie = nume complet
        </span>
      </div>

      <div style={{ height }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={true}
          zoomOnScroll={true}
          zoomOnPinch={true}
          zoomOnDoubleClick={true}
          minZoom={0.2}
          maxZoom={2.5}
          defaultEdgeOptions={{ type: "smoothstep" }}
          connectionLineType={ConnectionLineType.SmoothStep}
          onEdgeMouseEnter={(_, edge) => setHoveredEdge(edge.id)}
          onEdgeMouseLeave={() => setHoveredEdge(null)}
        >
          <Background color="#e2e8f0" gap={24} size={1.2} />
          <Controls showInteractive={false} position="bottom-right" />
          <MiniMap
            nodeColor={(node) => {
              const type = graphNodes.find((n) => n.id === node.id)?.type;
              return nodeColors[type || ""] || "#64748b";
            }}
            maskColor="rgba(248, 250, 252, 0.7)"
            pannable
            zoomable
            position="bottom-left"
            style={{ width: 140, height: 90 }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
