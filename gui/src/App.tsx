import {
  type DragEvent,
  type DragEventHandler,
  useCallback,
  useRef,
} from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type NodeTypes,
  type IsValidConnection,
  useReactFlow,
} from "@xyflow/react";
import { useStore } from "./store";
import type { AppNode } from "./types";
import { NODE_COLORS } from "./types";
import { Sidebar } from "./panels/Sidebar";
import { TomlPreview } from "./panels/TomlPreview";
import { DeviceNode } from "./nodes/DeviceNode";
import { QdiscNode } from "./nodes/QdiscNode";
import { ClassNode } from "./nodes/ClassNode";
import { FilterNode } from "./nodes/FilterNode";
import { ActionNode } from "./nodes/ActionNode";

// ── Custom node type registry ───────────────────────────────────

const nodeTypes: NodeTypes = {
  device: DeviceNode,
  qdisc: QdiscNode,
  class: ClassNode,
  filter: FilterNode,
  action: ActionNode,
};

// ── Valid connection rules ──────────────────────────────────────
//
// device → qdisc      (device as dev for qdisc)
// device → filter     (device as dev for filter, e.g. ingress matchall)
// qdisc  → class      (qdisc as parent for class)
// qdisc  → filter     (qdisc as parent for filter)
// class  → class      (class as parent for sub-class)
// class  → qdisc      (class as parent for leaf qdisc)
// filter → class      (filter sendTo target)
// filter → action     (filter action attachment)

const VALID_CONNECTIONS: Record<string, Set<string>> = {
  device: new Set(["qdisc", "filter"]),
  qdisc: new Set(["class", "filter"]),
  class: new Set(["class", "qdisc"]),
  filter: new Set(["class", "action"]),
};

// ── App ─────────────────────────────────────────────────────────

export default function App() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const onNodesChange = useStore((s) => s.onNodesChange);
  const onEdgesChange = useStore((s) => s.onEdgesChange);
  const onConnect = useStore((s) => s.onConnect);
  const addDeviceNode = useStore((s) => s.addDeviceNode);
  const addQdiscNode = useStore((s) => s.addQdiscNode);
  const addClassNode = useStore((s) => s.addClassNode);
  const addFilterNode = useStore((s) => s.addFilterNode);
  const addActionNode = useStore((s) => s.addActionNode);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // ── Connection validation ───────────────────────────────────

  const isValidConnection: IsValidConnection = useCallback(
    (connection) => {
      const sourceNode = nodes.find(
        (n) => n.id === connection.source,
      ) as AppNode | undefined;
      const targetNode = nodes.find(
        (n) => n.id === connection.target,
      ) as AppNode | undefined;

      if (!sourceNode?.type || !targetNode?.type) return false;

      const allowed = VALID_CONNECTIONS[sourceNode.type];
      return allowed ? allowed.has(targetNode.type) : false;
    },
    [nodes],
  );

  // ── Drag-and-drop from sidebar ──────────────────────────────

  const onDragOver: DragEventHandler = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop: DragEventHandler = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData(
        "application/hotbuckets-node",
      );
      if (!nodeType) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      switch (nodeType) {
        case "device":
          addDeviceNode(position);
          break;
        case "qdisc":
          addQdiscNode(position);
          break;
        case "class":
          addClassNode(position);
          break;
        case "filter":
          addFilterNode(position);
          break;
        case "action":
          addActionNode(position);
          break;
      }
    },
    [
      screenToFlowPosition,
      addDeviceNode,
      addQdiscNode,
      addClassNode,
      addFilterNode,
      addActionNode,
    ],
  );

  // ── Render ──────────────────────────────────────────────────

  return (
    <div className="flex h-full w-full">
      <Sidebar />
      <div className="flex-1 h-full" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          isValidConnection={isValidConnection}
          onDragOver={onDragOver}
          onDrop={onDrop}
          fitView
          deleteKeyCode={["Backspace", "Delete"]}
          className="bg-gray-100"
        >
          <Background gap={16} size={1} />
          <Controls position="bottom-left" />
          <MiniMap
            nodeColor={(node) => NODE_COLORS[node.type ?? ""] ?? "#888"}
            maskColor="rgba(0,0,0,0.08)"
            position="bottom-right"
          />
        </ReactFlow>
      </div>
      <TomlPreview />
    </div>
  );
}
