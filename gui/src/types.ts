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
  "prio",
  "hfsc",
  "clsact",
] as const;
export type QdiscType = (typeof QDISC_TYPES)[number];

export const FILTER_TYPES = ["u32", "fw", "matchall", "flower"] as const;
export type FilterType = (typeof FILTER_TYPES)[number];

export const ACTION_TYPES = ["mirred", "police", "drop", "skbedit"] as const;
export type ActionType = (typeof ACTION_TYPES)[number];

// ── Per-qdisc param definitions (for dynamic forms) ─────────────

export interface ParamDef {
  key: string;
  label: string;
  type: "text" | "toggle" | "speed";
  placeholder?: string;
  description?: string;
}

export const QDISC_PARAMS: Record<QdiscType, ParamDef[]> = {
  htb: [
    { key: "default", label: "default", type: "text", placeholder: "class name" },
  ],
  tbf: [
    { key: "rate", label: "rate", type: "speed", placeholder: "10mbit" },
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
    { key: "bandwidth", label: "bandwidth", type: "speed", placeholder: "100mbit" },
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
  prio: [
    { key: "bands", label: "bands", type: "text", placeholder: "3", description: "Number of priority bands (2-16, default 3)" },
    { key: "priomap", label: "priomap", type: "text", placeholder: "1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1", description: "16 space-separated band mappings for TOS values" },
  ],
  hfsc: [
    { key: "default", label: "default", type: "text", placeholder: "class name", description: "Default class for unclassified traffic" },
  ],
  clsact: [],
};

// ── Plugin descriptions ──────────────────────────────────────────

export const QDISC_DESCRIPTIONS: Record<QdiscType, string> = {
  htb: "Hierarchical Token Bucket -- classful shaping with rate guarantees and ceiling limits",
  tbf: "Token Bucket Filter -- simple classless rate limiter",
  sfq: "Stochastic Fairness Queueing -- classless round-robin across flow buckets",
  netem: "Network Emulator -- simulate delay, loss, corruption, reordering",
  cake: "CAKE -- modern all-in-one AQM with shaping, flow isolation, and prioritization",
  ingress: "Ingress hook -- attach filters to incoming packets (use clsact for ingress+egress)",
  fq_codel: "Fair Queue CoDel -- per-flow queuing with AQM to fight bufferbloat",
  prio: "Priority scheduler -- dequeues from lowest non-empty band first",
  hfsc: "Hierarchical Fair Service Curve -- real-time latency guarantees with link sharing",
  clsact: "Classify-Act -- modern ingress+egress hook point for filters (replaces ingress)",
};

export const FILTER_DESCRIPTIONS: Record<FilterType, string> = {
  u32: "Universal 32-bit classifier -- match on IP header fields with byte offsets",
  fw: "Firewall mark classifier -- match packets by iptables/nftables fwmark",
  matchall: "Match-all -- matches every packet unconditionally (use with actions)",
  flower: "Modern L2-L4 classifier -- match on IP, port, protocol, MAC, VLAN, and more",
};

export const ACTION_DESCRIPTIONS: Record<ActionType, string> = {
  mirred: "Mirror or redirect packets to another network device",
  police: "Rate-limit traffic -- exceed rate triggers conform-exceed policy",
  drop: "Silently discard matching packets",
  skbedit: "Set packet metadata -- mark, priority, or hardware queue mapping",
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

export type ClassType = "htb" | "hfsc" | "prio";

export type ClassData = {
  label: string;
  classType: ClassType;
  rate: string;
  ceil: string;
  burst: string;
  prio: string;
  // hfsc service curves
  sc: string;
  rt: string;
  ls: string;
  ul: string;
  [key: string]: unknown;
};

export type FilterData = {
  label: string;
  filterType: FilterType;
  protocol: string;
  prio: string;
  handle: string; // for fw filters
  ipMatches: Record<string, string>; // dst, src, dport, sport
  matchParams: Record<string, string>; // for flower
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
  mark: string; // skbedit
  priority: string; // skbedit
  queueMapping: string; // skbedit
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
