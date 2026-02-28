import type { Node } from "@xyflow/react";

// ── Qdisc type definitions ──────────────────────────────────────

export const QDISC_TYPES = [
  "htb",
  "tbf",
  "sfq",
  "netem",
  "cake",
  "ingress",
  "fq_codel",
] as const;
export type QdiscType = (typeof QDISC_TYPES)[number];

export const FILTER_TYPES = ["u32", "fw", "matchall"] as const;
export type FilterType = (typeof FILTER_TYPES)[number];

export const ACTION_TYPES = ["mirred", "police", "drop"] as const;
export type ActionType = (typeof ACTION_TYPES)[number];

// ── Per-qdisc param definitions (for dynamic forms) ─────────────

export interface ParamDef {
  key: string;
  label: string;
  type: "text" | "toggle";
  placeholder?: string;
}

export const QDISC_PARAMS: Record<QdiscType, ParamDef[]> = {
  htb: [
    { key: "default", label: "default", type: "text", placeholder: "class name" },
  ],
  tbf: [
    { key: "rate", label: "rate", type: "text", placeholder: "10mbit" },
    { key: "burst", label: "burst", type: "text", placeholder: "5000" },
    { key: "latency", label: "latency", type: "text", placeholder: "200ms" },
  ],
  sfq: [
    { key: "perturb", label: "perturb", type: "text", placeholder: "10" },
    { key: "quantum", label: "quantum", type: "text", placeholder: "1500" },
  ],
  netem: [
    { key: "delay", label: "delay", type: "text", placeholder: "100ms" },
    { key: "loss", label: "loss", type: "text", placeholder: "1%" },
    { key: "corrupt", label: "corrupt", type: "text", placeholder: "0.1%" },
    { key: "reorder", label: "reorder", type: "text", placeholder: "50% 50%" },
    { key: "duplicate", label: "dup", type: "text", placeholder: "1%" },
  ],
  cake: [
    { key: "bandwidth", label: "bandwidth", type: "text", placeholder: "100mbit" },
    { key: "diffserv4", label: "diffserv4", type: "toggle" },
    { key: "diffserv3", label: "diffserv3", type: "toggle" },
    { key: "wash", label: "wash", type: "toggle" },
    { key: "nat", label: "nat", type: "toggle" },
    { key: "ingress", label: "ingress", type: "toggle" },
  ],
  ingress: [],
  fq_codel: [
    { key: "limit", label: "limit", type: "text", placeholder: "1000" },
    { key: "flows", label: "flows", type: "text", placeholder: "1024" },
    { key: "target", label: "target", type: "text", placeholder: "5ms" },
    { key: "interval", label: "interval", type: "text", placeholder: "100ms" },
  ],
};

// ── Node data types ─────────────────────────────────────────────

export type DeviceData = {
  label: string;
  dev: string;
  virtual: boolean;
  devType: string; // "ifb", etc.
  [key: string]: unknown;
};

export type QdiscData = {
  label: string;
  qdiscType: QdiscType;
  handle: string; // explicit handle, e.g. "ffff:" for ingress
  params: Record<string, string>;
  [key: string]: unknown;
};

export type ClassData = {
  label: string;
  rate: string;
  ceil: string;
  burst: string;
  prio: string;
  [key: string]: unknown;
};

export type FilterData = {
  label: string;
  filterType: FilterType;
  protocol: string;
  prio: string;
  handle: string; // for fw filters
  ipMatches: Record<string, string>; // dst, src, dport, sport
  [key: string]: unknown;
};

export type ActionData = {
  label: string;
  actionType: ActionType;
  direction: string; // mirred
  mode: string; // mirred
  target: string; // mirred
  rate: string; // police
  burst: string; // police
  [key: string]: unknown;
};

// ── Union node types ────────────────────────────────────────────

export type DeviceNode = Node<DeviceData, "device">;
export type QdiscNode = Node<QdiscData, "qdisc">;
export type ClassNode = Node<ClassData, "class">;
export type FilterNode = Node<FilterData, "filter">;
export type ActionNode = Node<ActionData, "action">;

export type AppNode = DeviceNode | QdiscNode | ClassNode | FilterNode | ActionNode;

// ── Edge types ──────────────────────────────────────────────────

export type EdgeType =
  | "device-to-qdisc"    // device → qdisc (dev = ...)
  | "parent-child"       // qdisc → class, class → class, class → qdisc
  | "filter-parent"      // qdisc → filter (parent = ...)
  | "filter-target"      // filter → class (sendTo = ...)
  | "filter-action"      // filter → action
  | "filter-device";     // device → filter (dev = ...)

// ── Global config (variables, speeds, hosts) ────────────────────

export interface KeyValueEntry {
  key: string;
  value: string;
}

// ── Workspace persistence ────────────────────────────────────────

export interface WorkspaceMeta {
  id: string;
  name: string;
  savedAt: number;
}

export interface Workspace extends WorkspaceMeta {
  nodes: AppNode[];
  edges: import("@xyflow/react").Edge[];
  variables: KeyValueEntry[];
  speeds: KeyValueEntry[];
  hosts: KeyValueEntry[];
  tc: string;
  unit: string;
}

// ── Node colors ─────────────────────────────────────────────────

export const NODE_COLORS: Record<string, string> = {
  device: "#3b82f6",
  qdisc: "#22c55e",
  class: "#f59e0b",
  filter: "#a855f7",
  action: "#ef4444",
};
