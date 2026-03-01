"""Dependency resolution, handle assignment, and device inheritance.

This module replaces the old 10-iteration retry loop with a proper
topological sort and single-pass handle assignment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hotbuckets.errors import CyclicDependencyError, ResolutionError
from hotbuckets.model import TrafficConfig


@dataclass
class ResolvedEntry:
    """A resolved configuration entry with assigned handles and device."""

    name: str
    entry_type: str  # "qdisc", "class", "filter"
    device: str  # Resolved real device name
    handle: str  # Assigned handle (e.g., "1:", "1:2")
    parent_handle: str  # Resolved parent handle (e.g., "root", "1:", "1:1")
    order: int  # Global ordering index for output


@dataclass
class ResolverResult:
    """Complete resolution result with all assigned handles and mappings."""

    qdisc_handles: dict[str, str] = field(default_factory=dict)  # name -> "N:"
    class_ids: dict[str, str] = field(default_factory=dict)  # name -> "major:minor"
    device_map: dict[str, str] = field(default_factory=dict)  # entry name -> real device
    all_devices: set[str] = field(default_factory=set)  # All real device names
    entries: list[ResolvedEntry] = field(default_factory=list)  # Ordered entries
    ingress_devices: set[str] = field(default_factory=set)  # Devices with ingress qdiscs
    virtual_devices: list[str] = field(default_factory=list)  # Virtual device names (ordered)


def resolve(config: TrafficConfig) -> ResolverResult:
    """Resolve all references, assign handles, and determine ordering.

    This mimics the original hotbuckets behavior for backward compatibility:
    - Qdisc handles are assigned sequentially: 1:, 2:, 3:, ...
    - Class IDs use parent's major number with a global sequential minor
    - Output is sorted by (major, minor) from handles/classids
    - Filters get (999, 999) sort key (appear last)
    """
    result = ResolverResult()

    # Build lookup maps for all entries
    qdisc_map = {q.name: q for q in config.qdiscs}
    class_map = {c.name: c for c in config.classes}
    filter_map = {f.name: f for f in config.filters}

    # All names (check uniqueness across types for parent lookups)
    all_names = set(qdisc_map) | set(class_map) | set(filter_map)

    # Build dependency graph for topological sort
    # Each entry depends on its parent being resolved first
    deps: dict[str, set[str]] = {}

    for q in config.qdiscs:
        parent = q.parent
        if parent == "root":
            deps[q.name] = set()
        else:
            if parent in all_names:
                deps[q.name] = {parent}
            else:
                deps[q.name] = set()

    for c in config.classes:
        parent = c.parent
        if parent and parent in all_names:
            deps[c.name] = {parent}
        else:
            deps[c.name] = set()

    for f in config.filters:
        dep_set: set[str] = set()
        if f.parent and f.parent in all_names:
            dep_set.add(f.parent)
        if f.send_to and f.send_to in all_names:
            dep_set.add(f.send_to)
        deps[f.name] = dep_set

    # Topological sort
    order = _topological_sort(deps)

    # Device resolution helper
    def resolve_device(name: str) -> str:
        """Resolve device name for an entry, walking up the parent chain."""
        visited: set[str] = set()

        def _walk(n: str) -> str:
            if n in visited:
                return ""
            visited.add(n)

            # Check if this entry has an explicit device
            if n in qdisc_map:
                dev = qdisc_map[n].device
                if dev:
                    return _resolve_dev_alias(dev, config)
                parent = qdisc_map[n].parent
                if parent and parent != "root":
                    return _walk(parent)
            elif n in class_map:
                # Classes don't have a direct device; inherit from parent
                parent = class_map[n].parent
                if parent:
                    return _walk(parent)
            elif n in filter_map:
                dev = filter_map[n].device
                if dev:
                    return _resolve_dev_alias(dev, config)
                parent = filter_map[n].parent
                if parent:
                    return _walk(parent)
            return ""

        return _walk(name)

    # Assign handles and resolve devices in topological order
    next_qdisc_major = 1
    next_class_minor = 1

    for name in order:
        if name in qdisc_map:
            q = qdisc_map[name]

            # Handle assignment
            if q.handle:
                # Explicit handle (e.g., "ffff:" for ingress)
                handle = q.handle
            else:
                handle = f"{next_qdisc_major}:"
                next_qdisc_major += 1

            result.qdisc_handles[name] = handle

            # Track ingress/clsact qdiscs
            if q.qdisc_type in ("ingress", "clsact"):
                dev = resolve_device(name)
                result.ingress_devices.add(dev)

            # Resolve device
            dev = resolve_device(name)
            if dev:
                result.device_map[name] = dev
                result.all_devices.add(dev)

            # Parent handle
            if q.parent == "root":
                parent_handle = "root"
            else:
                parent_handle = _find_handle(q.parent, result)

            result.entries.append(
                ResolvedEntry(
                    name=name,
                    entry_type="qdisc",
                    device=dev,
                    handle=handle,
                    parent_handle=parent_handle,
                    order=0,  # Assigned after sorting
                )
            )

        elif name in class_map:
            c = class_map[name]

            # Find parent handle to get the major number
            parent_handle = _find_handle(c.parent, result)
            major = parent_handle.split(":")[0]

            class_id = f"{major}:{next_class_minor}"
            next_class_minor += 1
            result.class_ids[name] = class_id

            # Resolve device (inherit from parent)
            dev = resolve_device(name)
            if dev:
                result.device_map[name] = dev
                result.all_devices.add(dev)

            result.entries.append(
                ResolvedEntry(
                    name=name,
                    entry_type="class",
                    device=dev,
                    handle=class_id,
                    parent_handle=parent_handle,
                    order=0,
                )
            )

        elif name in filter_map:
            f = filter_map[name]

            # Resolve device
            dev = ""
            if f.device:
                dev = _resolve_dev_alias(f.device, config)
            else:
                dev = resolve_device(name)
            if dev:
                result.device_map[name] = dev
                result.all_devices.add(dev)

            # Parent handle for filter
            parent_handle = ""
            if f.parent:
                parent_handle = _find_handle(f.parent, result)

            result.entries.append(
                ResolvedEntry(
                    name=name,
                    entry_type="filter",
                    device=dev,
                    handle="",
                    parent_handle=parent_handle,
                    order=0,
                )
            )

    # Sort entries by (major, minor) to match original behavior.
    # The old code scans the rendered command for "handle" or "classid" tokens.
    # For fw filters with a handle (e.g., "handle 42"), the handle value is used
    # as the sort key, placing them before u32 filters that have no handle.
    def sort_key(entry: ResolvedEntry) -> tuple[int, int]:
        if entry.entry_type == "filter":
            # Check if this filter has a handle (fw filters)
            if entry.name in filter_map:
                filt = filter_map[entry.name]
                if filt.handle:
                    try:
                        return (int(filt.handle), 0)
                    except ValueError:
                        pass
            return (999, 999)
        handle = entry.handle
        try:
            parts = handle.split(":")
            major = int(parts[0]) if parts[0] else 0
            minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
            return (major, minor)
        except (ValueError, IndexError):
            return (999, 999)

    result.entries.sort(key=sort_key)
    for i, entry in enumerate(result.entries):
        entry.order = i

    # Collect virtual devices (ordered by first appearance)
    seen_virtual: set[str] = set()
    for entry in result.entries:
        dev_name = entry.device
        for dname, dobj in config.devices.items():
            if dobj.dev == dev_name and dobj.virtual and dev_name not in seen_virtual:
                result.virtual_devices.append(dname)
                seen_virtual.add(dev_name)

    return result


def _resolve_dev_alias(dev: str, config: TrafficConfig) -> str:
    """Resolve a device alias to its real device name."""
    if dev in config.devices:
        return config.devices[dev].dev
    return dev


def _find_handle(name: str, result: ResolverResult) -> str:
    """Find the resolved handle/classid for a named entry."""
    if name in result.qdisc_handles:
        return result.qdisc_handles[name]
    if name in result.class_ids:
        return result.class_ids[name]
    raise ResolutionError(f"Cannot find handle for '{name}'", source="resolver", target=name)


def _topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """Kahn's algorithm for topological sort.

    Returns entries in dependency order (parents before children).
    Preserves insertion order for entries at the same dependency level
    (important for backward compatibility with handle numbering).
    """
    # Compute in-degree for each node
    in_degree: dict[str, int] = {name: 0 for name in deps}
    for name, dep_set in deps.items():
        for dep in dep_set:
            if dep in in_degree:
                in_degree[name] = in_degree.get(name, 0)

    # Recompute properly
    in_degree = {name: 0 for name in deps}
    for name, dep_set in deps.items():
        for dep in dep_set:
            if dep in deps:  # Only count deps that are actual entries
                in_degree[name] += 1

    # Start with nodes that have no dependencies
    queue: list[str] = [name for name in deps if in_degree[name] == 0]
    result: list[str] = []

    while queue:
        # Process in insertion order (stable sort)
        node = queue.pop(0)
        result.append(node)

        # Reduce in-degree for dependents
        for name, dep_set in deps.items():
            if node in dep_set:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)

    if len(result) != len(deps):
        # Cycle detected — find which nodes are involved
        remaining = set(deps) - set(result)
        raise CyclicDependencyError(sorted(remaining))

    return result
