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
  Workspace,
  WorkspaceMeta,
} from "./types";
import { BUILTIN_WORKSPACES } from "./builtins";

let nextId = 1;
function genId() {
  return `node-${nextId++}`;
}

/** Reset nextId to be above the highest existing node id number. */
function syncNextId(nodes: AppNode[]) {
  let max = 0;
  for (const n of nodes) {
    const m = n.id.match(/^node-(\d+)$/);
    if (m) max = Math.max(max, Number(m[1]));
  }
  nextId = max + 1;
}

// ── localStorage helpers ────────────────────────────────────────

const STORAGE_KEY = "hotbuckets-workspaces";

function readAllWorkspaces(): Workspace[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAllWorkspaces(workspaces: Workspace[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workspaces));
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

  // Workspace persistence
  activeWorkspaceId: string | null;
  activeWorkspaceName: string;
  setActiveWorkspaceName: (name: string) => void;
  saveWorkspace: () => void;
  loadWorkspace: (id: string) => void;
  deleteWorkspace: (id: string) => void;
  newWorkspace: () => void;
  listWorkspaces: () => WorkspaceMeta[];
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
      classType: "htb",
      rate: "",
      ceil: "",
      burst: "",
      prio: "",
      sc: "",
      rt: "",
      ls: "",
      ul: "",
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
      matchParams: {},
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
      mark: "",
      priority: "",
      queueMapping: "",
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

  // ── Workspace persistence ───────────────────────────────────

  activeWorkspaceId: null,
  activeWorkspaceName: "Untitled",

  setActiveWorkspaceName: (name) => set({ activeWorkspaceName: name }),

  saveWorkspace: () => {
    const state = get();
    const workspaces = readAllWorkspaces();
    const now = Date.now();

    if (state.activeWorkspaceId) {
      // Update existing
      const idx = workspaces.findIndex(
        (w) => w.id === state.activeWorkspaceId,
      );
      const ws: Workspace = {
        id: state.activeWorkspaceId,
        name: state.activeWorkspaceName,
        savedAt: now,
        nodes: state.nodes,
        edges: state.edges,
        variables: state.variables,
        speeds: state.speeds,
        hosts: state.hosts,
        tc: state.tc,
        unit: state.unit,
      };
      if (idx >= 0) {
        workspaces[idx] = ws;
      } else {
        workspaces.push(ws);
      }
      writeAllWorkspaces(workspaces);
    } else {
      // Create new
      const id = crypto.randomUUID();
      const ws: Workspace = {
        id,
        name: state.activeWorkspaceName,
        savedAt: now,
        nodes: state.nodes,
        edges: state.edges,
        variables: state.variables,
        speeds: state.speeds,
        hosts: state.hosts,
        tc: state.tc,
        unit: state.unit,
      };
      workspaces.push(ws);
      writeAllWorkspaces(workspaces);
      set({ activeWorkspaceId: id });
    }
  },

  loadWorkspace: (id) => {
    // Check builtins first
    const builtin = BUILTIN_WORKSPACES.find((w) => w.id === id);
    if (builtin) {
      // Deep-clone so edits don't mutate the builtin
      const clone = JSON.parse(JSON.stringify(builtin)) as Workspace;
      syncNextId(clone.nodes);
      set({
        nodes: clone.nodes,
        edges: clone.edges,
        variables: clone.variables,
        speeds: clone.speeds,
        hosts: clone.hosts,
        tc: clone.tc,
        unit: clone.unit,
        activeWorkspaceId: null, // not saved yet — user can Save to create their own copy
        activeWorkspaceName: clone.name,
      });
      return;
    }

    // Then check user workspaces
    const workspaces = readAllWorkspaces();
    const ws = workspaces.find((w) => w.id === id);
    if (!ws) return;
    syncNextId(ws.nodes);
    set({
      nodes: ws.nodes,
      edges: ws.edges,
      variables: ws.variables,
      speeds: ws.speeds,
      hosts: ws.hosts,
      tc: ws.tc,
      unit: ws.unit,
      activeWorkspaceId: ws.id,
      activeWorkspaceName: ws.name,
    });
  },

  deleteWorkspace: (id) => {
    const workspaces = readAllWorkspaces().filter((w) => w.id !== id);
    writeAllWorkspaces(workspaces);
    // If we deleted the active workspace, detach
    if (get().activeWorkspaceId === id) {
      set({ activeWorkspaceId: null });
    }
  },

  newWorkspace: () => {
    nextId = 1;
    set({
      nodes: [],
      edges: [],
      variables: [],
      speeds: [],
      hosts: [],
      tc: "tc",
      unit: "",
      activeWorkspaceId: null,
      activeWorkspaceName: "Untitled",
    });
  },

  listWorkspaces: () => {
    return readAllWorkspaces()
      .map(({ id, name, savedAt }) => ({ id, name, savedAt }))
      .sort((a, b) => b.savedAt - a.savedAt);
  },
}));
