import type { Edge } from "@xyflow/react";
import type {
  AppNode,
  DeviceData,
  QdiscData,
  ClassData,
  FilterData,
  ActionData,
  KeyValueEntry,
} from "../types";

// ── Helpers ─────────────────────────────────────────────────────

function quoteIfNeeded(v: string): string {
  // Numbers, booleans, and already-quoted strings stay as-is
  if (/^-?\d+(\.\d+)?$/.test(v)) return v;
  if (v === "true" || v === "false") return v;
  if (/^".*"$/.test(v)) return v;
  return `"${v}"`;
}

function findNode(nodes: AppNode[], id: string): AppNode | undefined {
  return nodes.find((n) => n.id === id);
}

/** Find the source node connected to a target node's target handle. */
function findParent(
  nodes: AppNode[],
  edges: Edge[],
  targetId: string,
): AppNode | undefined {
  const edge = edges.find((e) => e.target === targetId);
  if (!edge) return undefined;
  return findNode(nodes, edge.source);
}

/** Find all target nodes connected from a source node's source handle. */
function findChildren(
  nodes: AppNode[],
  edges: Edge[],
  sourceId: string,
): AppNode[] {
  return edges
    .filter((e) => e.source === sourceId)
    .map((e) => findNode(nodes, e.target))
    .filter((n): n is AppNode => n !== undefined);
}

/** Walk up parent edges to find the device ancestor. */
function findDeviceAncestor(
  nodes: AppNode[],
  edges: Edge[],
  nodeId: string,
  visited = new Set<string>(),
): AppNode | undefined {
  if (visited.has(nodeId)) return undefined;
  visited.add(nodeId);
  const node = findNode(nodes, nodeId);
  if (!node) return undefined;
  if (node.type === "device") return node;
  const parent = findParent(nodes, edges, nodeId);
  if (!parent) return undefined;
  return findDeviceAncestor(nodes, edges, parent.id, visited);
}

/** Find the device a qdisc/filter is on, either directly connected or via ancestors. */
function resolveDeviceLabel(
  nodes: AppNode[],
  edges: Edge[],
  nodeId: string,
): string | undefined {
  const dev = findDeviceAncestor(nodes, edges, nodeId);
  return dev ? (dev.data as DeviceData).label : undefined;
}

/** Find what a filter's source handle connects to (sendTo target). */
function findFilterTargets(
  nodes: AppNode[],
  edges: Edge[],
  filterId: string,
): { classes: AppNode[]; actions: AppNode[] } {
  const children = findChildren(nodes, edges, filterId);
  return {
    classes: children.filter((n) => n.type === "class"),
    actions: children.filter((n) => n.type === "action"),
  };
}

// ── TOML generation ─────────────────────────────────────────────

interface ExportContext {
  nodes: AppNode[];
  edges: Edge[];
  variables: KeyValueEntry[];
  speeds: KeyValueEntry[];
  hosts: KeyValueEntry[];
  tc: string;
  unit: string;
}

export function exportToml(ctx: ExportContext): string {
  const lines: string[] = [];

  // ── tc path
  if (ctx.tc && ctx.tc !== "tc") {
    lines.push(`tc = ${quoteIfNeeded(ctx.tc)}`);
    lines.push("");
  }

  // ── unit
  if (ctx.unit) {
    lines.push(`unit = ${quoteIfNeeded(ctx.unit)}`);
    lines.push("");
  }

  // ── [vars]
  if (ctx.variables.length > 0) {
    lines.push("[vars]");
    for (const { key, value } of ctx.variables) {
      if (key) lines.push(`${key} = ${quoteIfNeeded(value)}`);
    }
    lines.push("");
  }

  // ── [speeds]
  if (ctx.speeds.length > 0) {
    lines.push("[speeds]");
    for (const { key, value } of ctx.speeds) {
      if (key) lines.push(`${key} = ${quoteIfNeeded(value)}`);
    }
    lines.push("");
  }

  // ── [hosts]
  if (ctx.hosts.length > 0) {
    lines.push("[hosts]");
    for (const { key, value } of ctx.hosts) {
      if (key) lines.push(`${key} = ${quoteIfNeeded(value)}`);
    }
    lines.push("");
  }

  // ── Devices
  const devices = ctx.nodes.filter((n) => n.type === "device");
  for (const node of devices) {
    const d = node.data as DeviceData;
    lines.push(`[devices.${d.label}]`);
    lines.push(`dev = ${quoteIfNeeded(d.dev)}`);
    if (d.virtual) {
      lines.push("virtual = true");
      if (d.devType) lines.push(`type = ${quoteIfNeeded(d.devType)}`);
    }
    lines.push("");
  }

  // ── Qdiscs (shapers)
  const qdiscs = ctx.nodes.filter((n) => n.type === "qdisc");
  for (const node of qdiscs) {
    const q = node.data as QdiscData;
    lines.push(`[shaper.${q.label}]`);

    // dev: find device ancestor
    const devLabel = resolveDeviceLabel(ctx.nodes, ctx.edges, node.id);
    if (devLabel) lines.push(`dev = ${quoteIfNeeded(devLabel)}`);

    // parent: if parent is a class, reference its label
    const parent = findParent(ctx.nodes, ctx.edges, node.id);
    if (parent && parent.type === "class") {
      lines.push(`parent = ${quoteIfNeeded((parent.data as ClassData).label)}`);
    }

    lines.push(`type = ${quoteIfNeeded(q.qdiscType)}`);
    if (q.handle) lines.push(`handle = ${quoteIfNeeded(q.handle)}`);

    // Qdisc-specific params
    for (const [key, value] of Object.entries(q.params)) {
      if (value && value !== "") {
        lines.push(`${key} = ${quoteIfNeeded(value)}`);
      }
    }
    lines.push("");
  }

  // ── Classes
  const classes = ctx.nodes.filter((n) => n.type === "class");
  for (const node of classes) {
    const c = node.data as ClassData;
    const classType = c.classType || "htb";
    lines.push(`[class.${c.label}]`);

    // parent: whoever connects to this class (qdisc or another class)
    const parent = findParent(ctx.nodes, ctx.edges, node.id);
    if (parent && (parent.type === "qdisc" || parent.type === "class")) {
      const parentLabel =
        parent.type === "qdisc"
          ? (parent.data as QdiscData).label
          : (parent.data as ClassData).label;
      lines.push(`parent = ${quoteIfNeeded(parentLabel)}`);
    }

    // Emit class type if not htb (htb is default)
    if (classType !== "htb") {
      lines.push(`type = ${quoteIfNeeded(classType)}`);
    }

    if (classType === "htb") {
      if (c.rate) lines.push(`rate = ${quoteIfNeeded(c.rate)}`);
      if (c.ceil) lines.push(`ceil = ${quoteIfNeeded(c.ceil)}`);
      if (c.burst) lines.push(`burst = ${quoteIfNeeded(c.burst)}`);
      if (c.prio) lines.push(`prio = ${quoteIfNeeded(c.prio)}`);
    } else if (classType === "hfsc") {
      if (c.sc) lines.push(`sc = ${quoteIfNeeded(c.sc)}`);
      if (c.rt) lines.push(`rt = ${quoteIfNeeded(c.rt)}`);
      if (c.ls) lines.push(`ls = ${quoteIfNeeded(c.ls)}`);
      if (c.ul) lines.push(`ul = ${quoteIfNeeded(c.ul)}`);
    }
    // prio classes: no params
    lines.push("");
  }

  // ── Filters (matches)
  const filters = ctx.nodes.filter((n) => n.type === "filter");
  for (const node of filters) {
    const f = node.data as FilterData;
    lines.push(`[match.${f.label}]`);

    // dev: if directly connected to a device
    const devLabel = resolveDeviceLabel(ctx.nodes, ctx.edges, node.id);

    // parent: the qdisc this filter is on
    const parent = findParent(ctx.nodes, ctx.edges, node.id);
    if (parent) {
      if (parent.type === "device") {
        lines.push(`dev = ${quoteIfNeeded((parent.data as DeviceData).label)}`);
      } else if (parent.type === "qdisc") {
        if (devLabel) lines.push(`dev = ${quoteIfNeeded(devLabel)}`);
        lines.push(
          `parent = ${quoteIfNeeded((parent.data as QdiscData).label)}`,
        );
      }
    }

    if (f.filterType !== "u32") {
      lines.push(`type = ${quoteIfNeeded(f.filterType)}`);
    }
    if (f.protocol) lines.push(`protocol = ${quoteIfNeeded(f.protocol)}`);
    if (f.prio) lines.push(`prio = ${quoteIfNeeded(f.prio)}`);

    // sendTo: class target
    const { classes: targetClasses, actions } = findFilterTargets(
      ctx.nodes,
      ctx.edges,
      node.id,
    );
    if (targetClasses.length > 0) {
      lines.push(
        `sendTo = ${quoteIfNeeded((targetClasses[0].data as ClassData).label)}`,
      );
    }

    // fw handle
    if (f.filterType === "fw" && f.handle) {
      lines.push(`handle = ${quoteIfNeeded(f.handle)}`);
    }

    // u32 ip matches as inline table
    if (f.filterType === "u32") {
      const ipParts: string[] = [];
      for (const [key, value] of Object.entries(f.ipMatches)) {
        if (value) ipParts.push(`${key}=${quoteIfNeeded(value)}`);
      }
      if (ipParts.length > 0) {
        lines.push(`ip = {${ipParts.join(", ")}}`);
      }
    }

    // flower match params as sub-table
    if (f.filterType === "flower" && f.matchParams) {
      const hasParams = Object.values(f.matchParams).some((v) => v);
      if (hasParams) {
        lines.push("");
        lines.push(`[match.${f.label}.flower]`);
        for (const [key, value] of Object.entries(f.matchParams)) {
          if (value) lines.push(`${key} = ${quoteIfNeeded(value)}`);
        }
      }
    }

    // Actions as sub-table
    if (actions.length > 0) {
      const a = actions[0].data as ActionData;
      lines.push("");
      lines.push(`[match.${f.label}.action]`);
      lines.push(`type = ${quoteIfNeeded(a.actionType)}`);
      if (a.actionType === "mirred") {
        if (a.direction) lines.push(`direction = ${quoteIfNeeded(a.direction)}`);
        if (a.mode) lines.push(`mode = ${quoteIfNeeded(a.mode)}`);
        if (a.target) lines.push(`target = ${quoteIfNeeded(a.target)}`);
      } else if (a.actionType === "police") {
        if (a.rate) lines.push(`rate = ${quoteIfNeeded(a.rate)}`);
        if (a.burst) lines.push(`burst = ${quoteIfNeeded(a.burst)}`);
      } else if (a.actionType === "skbedit") {
        if (a.mark) lines.push(`mark = ${quoteIfNeeded(a.mark)}`);
        if (a.priority) lines.push(`priority = ${quoteIfNeeded(a.priority)}`);
        if (a.queueMapping) lines.push(`queue_mapping = ${quoteIfNeeded(a.queueMapping)}`);
      }
      // "drop" has no extra params
    }
    lines.push("");
  }

  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}
