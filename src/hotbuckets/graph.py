"""Graphviz rendering of the resolved traffic control configuration.

Produces a DOT digraph (``TC.gv``) mirroring the legacy ``--show`` output:
queueing disciplines and classes as nodes, hierarchy edges from parent to
child, and dotted filter edges pointing at the class a filter sends traffic
to.
"""

from __future__ import annotations

from graphviz import Digraph

from hotbuckets.model import ClassConfig, FilterConfig, QdiscConfig, TrafficConfig
from hotbuckets.resolver import ResolverResult


def _node_id(handle: str) -> str:
    """Build a graphviz node id from a tc handle/classid (``1:1`` -> ``h1_1``)."""
    return "h" + handle.replace(":", "_")


def _speed(value: str, speeds: dict[str, str]) -> str:
    """Resolve a speed alias (e.g. ``full``) to its concrete value."""
    return speeds.get(value, value)


def _qdisc_extra(q: QdiscConfig, speeds: dict[str, str]) -> str:
    """Build the secondary label lines for a qdisc node."""
    t = q.qdisc_type
    p = q.params
    extra: list[str] = []
    if t == "sfq":
        extra.append(f"perturb: {p.get('perturb', '10')}")
    elif t == "netem":
        if p.get("delay"):
            extra.append(f"delay: {p['delay']}")
        if p.get("loss"):
            extra.append(f"loss: {p['loss']}")
        if p.get("duplicate"):
            extra.append(f"dups: {p['duplicate']}")
        if p.get("corrupt"):
            extra.append(f"corrupt: {p['corrupt']}")
    elif t in ("htb", "tbf"):
        if p.get("latency"):
            extra.append(f"latency: {p['latency']}")
        if p.get("burst"):
            extra.append(f"burst: {p['burst']}")
        if p.get("rate"):
            extra.append(f"rate : {_speed(p['rate'], speeds)}")
    return "\n".join(extra)


def _class_rate_ceil(c: ClassConfig, speeds: dict[str, str]) -> str:
    """Build the ``rate=.../ceil`` line for a class node."""
    rate = c.params.get("rate")
    ceil = c.params.get("ceil")
    rate_s = _speed(rate, speeds) if rate else None
    ceil_s = _speed(ceil, speeds) if ceil else None
    return f"rate={rate_s}/{ceil_s}"


def _filter_extra(f: FilterConfig) -> str:
    """Build the match-detail lines for a filter node."""
    extra = ""
    if f.filter_type == "u32":
        for k, v in f.ip_matches.items():
            if k in ("src", "dst", "sport", "dport"):
                extra += f"\n{k}={v}"
    elif f.filter_type == "flower":
        for k, v in f.match_params.items():
            extra += f"\n{k}={v}"
    return extra


def render_graph(config: TrafficConfig, result: ResolverResult) -> None:
    """Render the resolved configuration to ``TC.gv`` and open it."""
    gr = Digraph("TC")
    speeds = config.speeds

    # Map every qdisc/class name to its graphviz node id.
    id_by_name: dict[str, str] = {}
    for q in config.qdiscs:
        id_by_name[q.name] = _node_id(result.qdisc_handles[q.name])
    for c in config.classes:
        id_by_name[c.name] = _node_id(result.class_ids[c.name])

    # Qdisc nodes
    for q in config.qdiscs:
        nid = id_by_name[q.name]
        label = f"Queue[{q.qdisc_type}] {q.name} ({result.qdisc_handles[q.name]})\n{_qdisc_extra(q, speeds)}"
        gr.node(nid, label=label)

    # Class nodes
    defaults = {q.default for q in config.qdiscs if q.default}
    for c in config.classes:
        nid = id_by_name[c.name]
        label = f"{c.class_type} class {c.name} ({result.class_ids[c.name]})\n{_class_rate_ceil(c, speeds)}"
        attrs = {"color": "orange"} if c.name in defaults else {}
        gr.node(nid, label=label, **attrs)

    # Hierarchy edges: parent -> child
    for q in config.qdiscs:
        parent = q.parent
        if parent and parent != "root" and parent in id_by_name:
            gr.edge(id_by_name[parent], id_by_name[q.name])
    for c in config.classes:
        parent = c.parent
        if parent and parent in id_by_name:
            gr.edge(id_by_name[parent], id_by_name[c.name])

    # Filter nodes and edges: filter -> send_to (dotted)
    for f in config.filters:
        fid = "h" + f.name
        gr.node(fid, label=f"{f.name}{_filter_extra(f)}", shape="plain", fontsize="8")
        if f.send_to and f.send_to in id_by_name:
            gr.edge(fid, id_by_name[f.send_to], arrowhead="dot")

    gr.render(filename="TC.gv", cleanup=True)
    gr.view()
