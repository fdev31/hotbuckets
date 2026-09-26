"""Script generation — renders resolved configuration into tc shell commands."""

from __future__ import annotations

from hotbuckets.errors import ValidationError
from hotbuckets.model import TrafficConfig
from hotbuckets.registry import Registry
from hotbuckets.resolver import ResolverResult


def generate(config: TrafficConfig, result: ResolverResult) -> str:
    """Generate a complete tc shell script from resolved configuration.

    The output format matches the original hotbuckets output:
    1. #!/bin/bash shebang
    2. # Cleanup: section with qdisc del commands
    3. Device setup commands (for virtual devices like IFB)
    4. set -ex
    5. # Rules: section with sorted tc commands
    """
    lines: list[str] = []

    # Shebang
    lines.append("#!/bin/bash")

    # Cleanup section
    lines.append("# Cleanup:")
    for dev in sorted(result.all_devices):
        lines.append(f"{config.tc} qdisc del dev {dev} root")
        if dev in result.ingress_devices:
            lines.append(f"{config.tc} qdisc del dev {dev} ingress")

    # Virtual device cleanup (IFB etc.) — delete root qdisc for virtual devices
    for dname in result.virtual_devices:
        dobj = config.devices[dname]
        if dobj.dev not in result.all_devices:
            # Virtual device not already covered above
            lines.append(f"{config.tc} qdisc del dev {dobj.dev} root")

    # Device setup commands (modprobe, ip link set, etc.)
    has_setup = False
    seen_setup: set[str] = set()
    for dname in result.virtual_devices:
        dobj = config.devices[dname]
        for cmd in dobj.setup_commands:
            if cmd in seen_setup:
                continue
            seen_setup.add(cmd)
            if not has_setup:
                lines.append("# Device setup:")
                has_setup = True
            lines.append(cmd)

    # set -ex
    lines.append("set -ex")

    # Validate all entries before generating
    _validate_all(config)

    # Rules section
    lines.append("# Rules:")

    # Build index maps for fast lookup
    qdisc_map = {q.name: q for q in config.qdiscs}
    class_map = {c.name: c for c in config.classes}
    filter_map = {f.name: f for f in config.filters}

    for entry in result.entries:
        if entry.entry_type == "qdisc":
            line = _generate_qdisc(entry, qdisc_map[entry.name], config, result)
        elif entry.entry_type == "class":
            line = _generate_class(entry, class_map[entry.name], config, result)
        elif entry.entry_type == "filter":
            line = _generate_filter(entry, filter_map[entry.name], config, result)
        else:
            continue
        lines.append(line)

    return "\n".join(lines) + "\n"


def _validate_all(config: TrafficConfig) -> None:
    """Run plugin validation on all entries. Raises ValidationError on first failure."""
    for q in config.qdiscs:
        plugin = Registry.get_qdisc(q.qdisc_type)
        errors = plugin.validate(q.params)
        if errors:
            raise ValidationError("; ".join(errors), entry_type="qdisc", entry_name=q.name)

    for f in config.filters:
        plugin = Registry.get_filter(f.filter_type)
        plugin_params: dict = {}
        if f.filter_type == "flower":
            plugin_params["match_params"] = f.match_params
        else:
            plugin_params["ip_matches"] = f.ip_matches
            plugin_params["handle"] = f.handle
        plugin_params["hosts"] = config.hosts
        errors = plugin.validate(plugin_params)
        if errors:
            raise ValidationError("; ".join(errors), entry_type="filter", entry_name=f.name)

    for f in config.filters:
        for action in f.actions:
            plugin = Registry.get_action(action.type)
            errors = plugin.validate(action.params)
            if errors:
                raise ValidationError("; ".join(errors), entry_type="action", entry_name=f"{f.name}.action")


def _resolve_speed(value: str, config: TrafficConfig) -> str:
    """Resolve a speed value: handle speed aliases and unit suffix."""
    # Check speed aliases
    if value in config.speeds:
        return config.speeds[value]
    # Check if it's a bare integer that needs the unit suffix
    if config.unit:
        try:
            int(value)
            return f"{value}{config.unit}"
        except ValueError:
            pass
    return value


def _generate_qdisc(
    entry: "ResolverResult.entries",  # type: ignore[name-defined]
    qdisc: "QdiscConfig",  # type: ignore[name-defined]
    config: TrafficConfig,
    result: ResolverResult,
) -> str:
    """Generate a tc qdisc add command."""
    from hotbuckets.resolver import ResolvedEntry

    assert isinstance(entry, ResolvedEntry)

    parts = [config.tc, "qdisc", "add"]

    # Device
    parts.extend(["dev", entry.device])

    # Parent — ingress/clsact qdiscs don't use parent/root
    if qdisc.qdisc_type in ("ingress", "clsact"):
        pass  # No parent clause for ingress/clsact
    elif entry.parent_handle == "root":
        parts.append("root")
    else:
        parts.extend(["parent", entry.parent_handle])

    # Handle
    parts.extend(["handle", entry.handle])

    # Type
    parts.append(qdisc.qdisc_type)

    # Plugin-generated args
    plugin = Registry.get_qdisc(qdisc.qdisc_type)

    # Resolve speed aliases in params
    resolved_params = dict(qdisc.params)
    for key in ("rate", "ceil", "bandwidth"):
        if key in resolved_params:
            resolved_params[key] = _resolve_speed(resolved_params[key], config)

    plugin_args = plugin.generate(resolved_params)
    parts.extend(plugin_args)

    # Default class (for htb and hfsc)
    if qdisc.default:
        default_id = result.class_ids.get(qdisc.default, "")
        if default_id:
            minor = default_id.split(":")[1]
            parts.extend(["default", minor])

    # Comment
    parts.append(f"# {qdisc.name}")

    return " ".join(parts)


def _generate_class(
    entry: "ResolverResult.entries",  # type: ignore[name-defined]
    cls: "ClassConfig",  # type: ignore[name-defined]
    config: TrafficConfig,
    result: ResolverResult,
) -> str:
    """Generate a tc class add command."""
    parts = [config.tc, "class", "add"]

    # Device
    parts.extend(["dev", entry.device])

    # Parent
    parts.extend(["parent", entry.parent_handle])

    # Classid
    parts.extend(["classid", entry.handle])

    # Type
    parts.append(cls.class_type)

    # Type-specific params
    if cls.class_type == "htb":
        params = dict(cls.params)
        # Resolve speeds
        for key in ("rate", "ceil"):
            if key in params:
                params[key] = _resolve_speed(params[key], config)

        # Output in specific order for backward compatibility
        # Only emit burst, rate, ceil — matching original behavior
        if "burst" in params:
            parts.extend(["burst", params["burst"]])
        if "rate" in params:
            parts.extend(["rate", params["rate"]])
        if "ceil" in params:
            parts.extend(["ceil", params["ceil"]])

    elif cls.class_type == "hfsc":
        params = dict(cls.params)
        # HFSC classes use service curves: sc, rt, ls, ul
        # Each is a string containing the full curve spec,
        # e.g. "m1 100mbit d 50ms m2 10mbit" or just "rate 10mbit"
        for key in ("sc", "rt", "ls", "ul"):
            if key in params:
                value = params[key]
                # Resolve speed aliases within the curve string
                # Simple approach: resolve each word that looks like a speed
                words = value.split()
                resolved_words = [_resolve_speed(w, config) for w in words]
                parts.append(key)
                parts.extend(resolved_words)

    elif cls.class_type == "prio":
        # Prio classes have no parameters — they are band identifiers
        pass

    # Comment
    parts.append(f"# {cls.name}")

    return " ".join(parts)


def _generate_filter(
    entry: "ResolverResult.entries",  # type: ignore[name-defined]
    filt: "FilterConfig",  # type: ignore[name-defined]
    config: TrafficConfig,
    result: ResolverResult,
) -> str:
    """Generate a tc filter add command."""
    parts = [config.tc, "filter", "add"]

    # Device
    parts.extend(["dev", entry.device])

    # Protocol
    if filt.protocol:
        parts.extend(["protocol", filt.protocol])

    # Parent
    if entry.parent_handle:
        parts.extend(["parent", entry.parent_handle])

    # Prio
    if filt.prio:
        parts.extend(["prio", filt.prio])

    # Filter type
    parts.append(filt.filter_type)

    # Plugin-generated args (match expressions, handle, etc.)
    plugin = Registry.get_filter(filt.filter_type)

    if filt.filter_type == "flower":
        plugin_params = {
            "match_params": filt.match_params,
            "hosts": config.hosts,
        }
    else:
        plugin_params = {
            "ip_matches": filt.ip_matches,
            "hosts": config.hosts,
            "handle": filt.handle,
        }
    plugin_args = plugin.generate(plugin_params)
    parts.extend(plugin_args)

    # Flowid (sendTo)
    if filt.send_to:
        flowid = ""
        if filt.send_to in result.class_ids:
            flowid = result.class_ids[filt.send_to]
        elif filt.send_to in result.qdisc_handles:
            flowid = result.qdisc_handles[filt.send_to]
        if flowid:
            parts.extend(["flowid", flowid])

    # Actions
    for action in filt.actions:
        action_plugin = Registry.get_action(action.type)
        action_params = dict(action.params)
        # Pass device map for mirred target resolution
        action_params["_devices"] = {name: dev.dev for name, dev in config.devices.items()}
        action_args = action_plugin.generate(action_params)
        parts.extend(action_args)

    # Legacy inline action (string-type action from old format)
    # Already handled above via filt.actions

    # Comment
    parts.append(f"# {filt.name}")

    return " ".join(parts)
