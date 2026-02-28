import type { Edge } from "@xyflow/react";
import type { AppNode, Workspace } from "./types";

// ── Helper to build workspace objects ───────────────────────────

function ws(
  id: string,
  name: string,
  desc: string,
  nodes: AppNode[],
  edges: Edge[],
  opts: Partial<Pick<Workspace, "variables" | "speeds" | "hosts" | "tc" | "unit">> = {},
): Workspace & { description: string } {
  return {
    id: `builtin:${id}`,
    name,
    description: desc,
    savedAt: 0,
    nodes,
    edges,
    variables: opts.variables ?? [],
    speeds: opts.speeds ?? [],
    hosts: opts.hosts ?? [],
    tc: opts.tc ?? "tc",
    unit: opts.unit ?? "",
  };
}

// Node/edge ID counters per workspace (reset for each)
function n(id: string, type: string, x: number, y: number, data: Record<string, unknown>): AppNode {
  return { id, type, position: { x, y }, data } as AppNode;
}
function e(source: string, target: string): Edge {
  return { id: `e-${source}-${target}`, source, target };
}

// ── 1. Basic: single TBF qdisc ─────────────────────────────────

const basic = ws(
  "basic",
  "Basic (TBF)",
  "Simplest config: a single TBF rate limiter on one interface",
  [
    n("n1", "device", 50, 100, { label: "wlo1", dev: "wlo1", virtual: false, devType: "" }),
    n("n2", "qdisc", 300, 100, { label: "simpleroot", qdiscType: "tbf", handle: "", params: { rate: "10mbit", burst: "5000", latency: "200ms" } }),
  ],
  [e("n1", "n2")],
);

// ── 2. Desktop: HTB tree with SFQ leaves + u32 filters ──────────

const desktop = ws(
  "desktop",
  "Desktop (HTB + SFQ)",
  "HTB class hierarchy with SFQ fairness and HTTP/HTTPS filters",
  [
    // Device
    n("n1", "device", 50, 180, { label: "nic", dev: "wlo1", virtual: false, devType: "" }),
    // Root HTB qdisc
    n("n2", "qdisc", 280, 180, { label: "base", qdiscType: "htb", handle: "", params: { default: "baseline" } }),
    // Classes
    n("n3", "class", 500, 80, { label: "unlimited", rate: "full", ceil: "", burst: "", prio: "" }),
    n("n4", "class", 720, 30, { label: "baseline", rate: "half", ceil: "full", burst: "", prio: "" }),
    n("n5", "class", 720, 180, { label: "web", rate: "half", ceil: "full", burst: "", prio: "" }),
    // SFQ leaves
    n("n6", "qdisc", 940, 30, { label: "fairness", qdiscType: "sfq", handle: "", params: { perturb: "10" } }),
    n("n7", "qdisc", 940, 180, { label: "fairness-web", qdiscType: "sfq", handle: "", params: { perturb: "10" } }),
    // Filters
    n("n8", "filter", 500, 280, { label: "filtHttp", filterType: "u32", protocol: "ip", prio: "", handle: "", ipMatches: { dport: "80" } }),
    n("n9", "filter", 500, 420, { label: "filtHttps", filterType: "u32", protocol: "ip", prio: "", handle: "", ipMatches: { dport: "443" } }),
  ],
  [
    e("n1", "n2"), // device → qdisc
    e("n2", "n3"), // qdisc → unlimited class
    e("n3", "n4"), // unlimited → baseline
    e("n3", "n5"), // unlimited → web
    e("n4", "n6"), // baseline → sfq
    e("n5", "n7"), // web → sfq
    e("n2", "n8"), // qdisc → filter (parent)
    e("n8", "n5"), // filter → web (sendTo)
    e("n2", "n9"), // qdisc → filter (parent)
    e("n9", "n5"), // filter → web (sendTo)
  ],
  {
    unit: "mbit",
    speeds: [
      { key: "full", value: "32mbit" },
      { key: "half", value: "15mbit" },
      { key: "almost", value: "25mbit" },
      { key: "slow", value: "2mbit" },
    ],
  },
);

// ── 3. Desktop Modern: CAKE + IFB ──────────────────────────────

const desktopModern = ws(
  "desktop-modern",
  "Desktop Modern (CAKE + IFB)",
  "Bufferbloat-fighting setup: CAKE on egress + ingress via IFB redirect",
  [
    // Devices
    n("n1", "device", 50, 80, { label: "main", dev: "{iface}", virtual: false, devType: "" }),
    n("n2", "device", 50, 350, { label: "ifb0", dev: "ifb0", virtual: true, devType: "ifb" }),
    // Ingress qdisc on main
    n("n3", "qdisc", 300, 30, { label: "ingress", qdiscType: "ingress", handle: "ffff:", params: {} }),
    // matchall filter + mirred action
    n("n4", "filter", 550, 30, { label: "redirect_to_ifb", filterType: "matchall", protocol: "", prio: "", handle: "", ipMatches: {} }),
    n("n5", "action", 800, 30, { label: "mirred_to_ifb", actionType: "mirred", direction: "egress", mode: "redirect", target: "ifb0", rate: "", burst: "" }),
    // CAKE download on ifb0
    n("n6", "qdisc", 300, 350, { label: "download", qdiscType: "cake", handle: "", params: { bandwidth: "{download}", diffserv4: "true", wash: "true" } }),
    // CAKE upload on main
    n("n7", "qdisc", 300, 180, { label: "upload", qdiscType: "cake", handle: "", params: { bandwidth: "{upload}", diffserv4: "true" } }),
  ],
  [
    e("n1", "n3"), // main → ingress qdisc
    e("n3", "n4"), // ingress → matchall filter
    e("n4", "n5"), // filter → mirred action
    e("n2", "n6"), // ifb0 → cake download
    e("n1", "n7"), // main → cake upload
  ],
  {
    variables: [
      { key: "iface", value: "enp12s0" },
      { key: "download", value: "450mbit" },
      { key: "upload", value: "45mbit" },
    ],
  },
);

// ── 4. Gate: server gateway with web traffic class ──────────────

const gate = ws(
  "gate",
  "Gateway (HTB + SFQ)",
  "Server gateway shaping with a web server traffic class and SFQ fairness",
  [
    // Device
    n("n1", "device", 50, 150, { label: "nic", dev: "eth0", virtual: false, devType: "" }),
    // Root HTB
    n("n2", "qdisc", 270, 150, { label: "shaper", qdiscType: "htb", handle: "", params: {} }),
    // Classes
    n("n3", "class", 480, 80, { label: "rootQ", rate: "full", ceil: "", burst: "", prio: "" }),
    n("n4", "class", 680, 30, { label: "base", rate: "full", ceil: "full", burst: "", prio: "" }),
    n("n5", "class", 680, 180, { label: "webserver", rate: "100kbps", ceil: "almost", burst: "", prio: "1" }),
    // SFQ leaves
    n("n6", "qdisc", 900, 30, { label: "makefair1", qdiscType: "sfq", handle: "", params: { perturb: "10" } }),
    n("n7", "qdisc", 900, 180, { label: "makefair2", qdiscType: "sfq", handle: "", params: { perturb: "10" } }),
    // Filter
    n("n8", "filter", 480, 280, { label: "filt1", filterType: "u32", protocol: "ip", prio: "2", handle: "", ipMatches: { sport: "80" } }),
  ],
  [
    e("n1", "n2"),
    e("n2", "n3"), // shaper → rootQ
    e("n3", "n4"), // rootQ → base
    e("n3", "n5"), // rootQ → webserver
    e("n4", "n6"), // base → sfq
    e("n5", "n7"), // webserver → sfq
    e("n2", "n8"), // shaper → filter
    e("n8", "n5"), // filter → webserver (sendTo)
  ],
  {
    unit: "mbit",
    tc: "/sbin/tc",
    speeds: [
      { key: "full", value: "30mbit" },
      { key: "almost", value: "25mbit" },
      { key: "slow", value: "5mbit" },
    ],
    hosts: [{ key: "lan", value: "192.168.2.0/24" }],
  },
);

// ── 5. HQLQ: netem degradation with fw filter ──────────────────

const hqlq = ws(
  "hqlq",
  "HQ/LQ (netem + fw)",
  "Simulate degraded network for specific hosts using netem, with fw and u32 filters",
  [
    // Device
    n("n1", "device", 50, 200, { label: "nic", dev: "enp1s0u1u2", virtual: false, devType: "" }),
    // Root HTB
    n("n2", "qdisc", 270, 200, { label: "shaper", qdiscType: "htb", handle: "", params: {} }),
    // Classes
    n("n3", "class", 480, 120, { label: "base", rate: "full", ceil: "", burst: "", prio: "" }),
    n("n4", "class", 680, 50, { label: "baseline", rate: "slow", ceil: "full", burst: "", prio: "" }),
    n("n5", "class", 680, 200, { label: "degraded", rate: "slow", ceil: "slow", burst: "", prio: "" }),
    // SFQ on baseline
    n("n6", "qdisc", 900, 50, { label: "fairness", qdiscType: "sfq", handle: "", params: { perturb: "10" } }),
    // netem on degraded
    n("n7", "qdisc", 900, 200, { label: "badnetwork", qdiscType: "netem", handle: "", params: { delay: "60ms 20ms", loss: "1% 1%", corrupt: "0.1%", reorder: "50% 50%" } }),
    // Filters
    n("n8", "filter", 480, 310, { label: "filt1", filterType: "u32", protocol: "ip", prio: "1", handle: "", ipMatches: { dst: "stb", sport: "80" } }),
    n("n9", "filter", 480, 440, { label: "filt2", filterType: "u32", protocol: "ip", prio: "1", handle: "", ipMatches: { sport: "443", dst: "stb" } }),
    n("n10", "filter", 480, 570, { label: "filt3", filterType: "fw", protocol: "ip", prio: "1", handle: "42", ipMatches: {} }),
  ],
  [
    e("n1", "n2"),
    e("n2", "n3"), // shaper → base
    e("n3", "n4"), // base → baseline
    e("n3", "n5"), // base → degraded
    e("n4", "n6"), // baseline → sfq
    e("n5", "n7"), // degraded → netem
    e("n2", "n8"), // shaper → filt1
    e("n8", "n5"), // filt1 → degraded
    e("n2", "n9"), // shaper → filt2
    e("n9", "n5"), // filt2 → degraded
    e("n2", "n10"), // shaper → filt3
    e("n10", "n5"), // filt3 → degraded
  ],
  {
    unit: "mbit",
    tc: "/sbin/tc",
    speeds: [
      { key: "full", value: "30mbit" },
      { key: "slow", value: "2mbit" },
      { key: "almost", value: "25mbit" },
    ],
    hosts: [{ key: "stb", value: "192.168.100.42" }],
  },
);

// ── Exports ─────────────────────────────────────────────────────

export type BuiltinWorkspace = Workspace & { description: string };

export const BUILTIN_WORKSPACES: BuiltinWorkspace[] = [
  basic,
  desktopModern,
  desktop,
  gate,
  hqlq,
];
