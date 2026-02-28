import { create } from "zustand";
import {
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Connection,
} from "@xyflow/react";
import type {
  AppNode,
  DeviceData,
  QdiscData,
  ClassData,
  FilterData,
  ActionData,
  KeyValueEntry,
} from "./types";

let nextId = 1;
function genId() {
  return `node-${nextId++}`;
}

export interface AppState {
  nodes: AppNode[];
  edges: Edge[];
  variables: KeyValueEntry[];
  speeds: KeyValueEntry[];
  hosts: KeyValueEntry[];
  tc: string;
  unit: string;

  // Node/edge mutations
  onNodesChange: OnNodesChange<AppNode>;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  updateNodeData: (id: string, data: Record<string, any>) => void;
  deleteNode: (id: string) => void;

  // Add nodes
  addDeviceNode: (position: { x: number; y: number }) => void;
  addQdiscNode: (position: { x: number; y: number }) => void;
  addClassNode: (position: { x: number; y: number }) => void;
  addFilterNode: (position: { x: number; y: number }) => void;
  addActionNode: (position: { x: number; y: number }) => void;

  // Global config
  setVariables: (entries: KeyValueEntry[]) => void;
  setSpeeds: (entries: KeyValueEntry[]) => void;
  setHosts: (entries: KeyValueEntry[]) => void;
  setTc: (tc: string) => void;
  setUnit: (unit: string) => void;
}

export const useStore = create<AppState>((set, get) => ({
  nodes: [],
  edges: [],
  variables: [],
  speeds: [],
  hosts: [],
  tc: "tc",
  unit: "",

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection: Connection) => {
    set({ edges: addEdge(connection, get().edges) });
  },

  updateNodeData: (id, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === id
          ? ({ ...node, data: { ...node.data, ...data } } as AppNode)
          : node,
      ),
    });
  },

  deleteNode: (id) => {
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
    });
  },

  addDeviceNode: (position) => {
    const id = genId();
    const data: DeviceData = {
      label: `dev${get().nodes.filter((n) => n.type === "device").length + 1}`,
      dev: "eth0",
      virtual: false,
      devType: "",
    };
    set({
      nodes: [
        ...get().nodes,
        { id, type: "device", position, data } as AppNode,
      ],
    });
  },

  addQdiscNode: (position) => {
    const id = genId();
    const data: QdiscData = {
      label: `qdisc${get().nodes.filter((n) => n.type === "qdisc").length + 1}`,
      qdiscType: "htb",
      handle: "",
      params: {},
    };
    set({
      nodes: [
        ...get().nodes,
        { id, type: "qdisc", position, data } as AppNode,
      ],
    });
  },

  addClassNode: (position) => {
    const id = genId();
    const data: ClassData = {
      label: `class${get().nodes.filter((n) => n.type === "class").length + 1}`,
      rate: "",
      ceil: "",
      burst: "",
      prio: "",
    };
    set({
      nodes: [
        ...get().nodes,
        { id, type: "class", position, data } as AppNode,
      ],
    });
  },

  addFilterNode: (position) => {
    const id = genId();
    const data: FilterData = {
      label: `filter${get().nodes.filter((n) => n.type === "filter").length + 1}`,
      filterType: "u32",
      protocol: "ip",
      prio: "",
      handle: "",
      ipMatches: {},
    };
    set({
      nodes: [
        ...get().nodes,
        { id, type: "filter", position, data } as AppNode,
      ],
    });
  },

  addActionNode: (position) => {
    const id = genId();
    const data: ActionData = {
      label: `action${get().nodes.filter((n) => n.type === "action").length + 1}`,
      actionType: "mirred",
      direction: "egress",
      mode: "redirect",
      target: "",
      rate: "",
      burst: "",
    };
    set({
      nodes: [
        ...get().nodes,
        { id, type: "action", position, data } as AppNode,
      ],
    });
  },

  setVariables: (entries) => set({ variables: entries }),
  setSpeeds: (entries) => set({ speeds: entries }),
  setHosts: (entries) => set({ hosts: entries }),
  setTc: (tc) => set({ tc }),
  setUnit: (unit) => set({ unit }),
}));
