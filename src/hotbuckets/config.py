"""TOML configuration loading, validation, and variable resolution."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from hotbuckets.errors import ConfigError
from hotbuckets.model import (
    ActionConfig,
    ClassConfig,
    Device,
    FilterConfig,
    QdiscConfig,
    TrafficConfig,
)

# Keys at the TOML top level that are not sections
_SCALAR_KEYS = {"tc", "unit"}

# Known top-level sections
_KNOWN_SECTIONS = {
    "vars",
    "speeds",
    "hosts",
    "devices",
    "interfaces",  # Legacy alias for devices
    "shaper",
    "class",
    "match",
}

# Variable interpolation pattern: {varname}
_VAR_PATTERN = re.compile(r"\{(\w+)\}")


def load_file(path: Path) -> TrafficConfig:
    """Load a TOML configuration file and return a TrafficConfig."""
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return _parse_raw(raw)


def load_string(text: str) -> TrafficConfig:
    """Load a TOML configuration from a string and return a TrafficConfig."""
    raw = tomllib.loads(text)
    return _parse_raw(raw)


def _parse_raw(raw: dict[str, Any]) -> TrafficConfig:
    """Parse a raw TOML dictionary into a TrafficConfig."""
    config = TrafficConfig()

    # Scalars
    config.tc = str(raw.get("tc", "tc"))
    config.unit = str(raw.get("unit", ""))

    # Variables
    config.variables = {k: str(v) for k, v in raw.get("vars", {}).items()}

    # Speeds
    config.speeds = {k: str(v) for k, v in raw.get("speeds", {}).items()}

    # Hosts (flatten: {name: {ip: "..."}} -> {name: "..."})
    raw_hosts = raw.get("hosts", {})
    for name, val in raw_hosts.items():
        if isinstance(val, dict):
            config.hosts[name] = str(val.get("ip", ""))
        else:
            config.hosts[name] = str(val)

    # Devices (with legacy "interfaces" fallback)
    raw_devices = raw.get("devices", raw.get("interfaces", {}))
    for name, val in raw_devices.items():
        if isinstance(val, dict):
            dev_name = str(val.get("dev", name))
            virtual = bool(val.get("virtual", False))
            dev_type = str(val.get("type", ""))
            setup: list[str] = []
            if virtual and dev_type == "ifb":
                setup = [
                    f"modprobe ifb numifbs=1",
                    f"ip link set dev {dev_name} up",
                ]
            config.devices[name] = Device(
                name=name,
                dev=dev_name,
                virtual=virtual,
                dev_type=dev_type,
                setup_commands=tuple(setup),
            )
        else:
            config.devices[name] = Device(name=name, dev=str(val))

    # Qdiscs (shapers)
    for name, data in raw.get("shaper", {}).items():
        if not isinstance(data, dict):
            raise ConfigError(f"Expected a table for shaper entry", "shaper", name)
        config.qdiscs.append(_parse_qdisc(name, data))

    # Classes
    for name, data in raw.get("class", {}).items():
        if not isinstance(data, dict):
            raise ConfigError(f"Expected a table for class entry", "class", name)
        config.classes.append(_parse_class(name, data))

    # Auto-generate prio band classes
    _auto_generate_prio_classes(config)

    # Filters (matches)
    for name, data in raw.get("match", {}).items():
        if not isinstance(data, dict):
            raise ConfigError(f"Expected a table for match entry", "match", name)
        config.filters.append(_parse_filter(name, data))

    # Interpolate variables across all string values
    _interpolate_variables(config)

    return config


def _parse_qdisc(name: str, data: dict[str, Any]) -> QdiscConfig:
    """Parse a single [shaper.*] entry."""
    # Extract known keys, everything else goes into params
    known_keys = {"dev", "type", "parent", "handle", "default"}
    params = {k: str(v) for k, v in data.items() if k not in known_keys}

    return QdiscConfig(
        name=name,
        qdisc_type=str(data.get("type", "htb")),
        device=str(data.get("dev", "")),
        parent=str(data.get("parent", "root")),
        handle=str(data.get("handle", "")),
        default=str(data.get("default", "")),
        params=params,
    )


def _parse_class(name: str, data: dict[str, Any]) -> ClassConfig:
    """Parse a single [class.*] entry."""
    known_keys = {"type", "parent"}
    params = {k: str(v) for k, v in data.items() if k not in known_keys}

    return ClassConfig(
        name=name,
        class_type=str(data.get("type", "htb")),
        parent=str(data.get("parent", "")),
        params=params,
    )


def _auto_generate_prio_classes(config: TrafficConfig) -> None:
    """Auto-generate band classes for prio qdiscs.

    For each prio qdisc, creates N band classes (default 3) named
    '<qdisc_name>:band<i>' unless the user already defined classes
    parented to that qdisc.
    """
    existing_parents: set[str] = {c.parent for c in config.classes}
    generated: list[ClassConfig] = []

    for q in config.qdiscs:
        if q.qdisc_type != "prio":
            continue
        # Skip if user already defined classes for this qdisc
        if q.name in existing_parents:
            continue
        bands = 3
        if "bands" in q.params:
            try:
                bands = int(q.params["bands"])
            except ValueError:
                pass
        for i in range(bands):
            generated.append(
                ClassConfig(
                    name=f"{q.name}:band{i}",
                    class_type="prio",
                    parent=q.name,
                    params={},
                )
            )

    config.classes.extend(generated)


def _parse_filter(name: str, data: dict[str, Any]) -> FilterConfig:
    """Parse a single [match.*] entry."""
    known_keys = {"dev", "type", "parent", "sendTo", "protocol", "prio", "handle", "ip", "action", "flower"}

    # Parse IP matches (for u32)
    ip_matches: dict[str, str] = {}
    raw_ip = data.get("ip", {})
    if isinstance(raw_ip, dict):
        ip_matches = {k: str(v) for k, v in raw_ip.items()}

    # Parse flower match params (sub-table)
    match_params: dict[str, str] = {}
    raw_flower = data.get("flower", {})
    if isinstance(raw_flower, dict):
        match_params = {k: str(v) for k, v in raw_flower.items()}

    # Parse actions
    actions: list[ActionConfig] = []
    raw_action = data.get("action")
    if isinstance(raw_action, dict):
        # Sub-table: [match.name.action]
        action_type = str(raw_action.get("type", ""))
        action_params = {k: str(v) for k, v in raw_action.items() if k != "type"}
        actions.append(ActionConfig(type=action_type, params=action_params))
    elif isinstance(raw_action, str):
        # Simple inline action string (legacy: action = "drop")
        actions.append(ActionConfig(type=raw_action))

    # Collect remaining params
    extra_params = {k: str(v) for k, v in data.items() if k not in known_keys}

    return FilterConfig(
        name=name,
        filter_type=str(data.get("type", "u32")),
        device=str(data.get("dev", "")),
        parent=str(data.get("parent", "")),
        send_to=str(data.get("sendTo", "")),
        protocol=str(data.get("protocol", "")),
        prio=str(data.get("prio", "")),
        handle=str(data.get("handle", "")),
        ip_matches=ip_matches,
        match_params=match_params,
        actions=tuple(actions),
    )


def _interpolate_variables(config: TrafficConfig) -> None:
    """Replace {varname} placeholders with values from [vars] section.

    Interpolation is applied to:
    - Device dev names
    - Speed values
    - Qdisc, class, filter params
    - Host values
    """
    variables = config.variables
    if not variables:
        return

    def _sub(text: str) -> str:
        def replacer(m: re.Match[str]) -> str:
            var_name = m.group(1)
            if var_name in variables:
                return variables[var_name]
            return m.group(0)  # Leave unresolved vars as-is

        return _VAR_PATTERN.sub(replacer, text)

    # Interpolate devices
    new_devices: dict[str, Device] = {}
    for name, dev in config.devices.items():
        new_devices[name] = Device(
            name=dev.name,
            dev=_sub(dev.dev),
            virtual=dev.virtual,
            dev_type=dev.dev_type,
            setup_commands=tuple(_sub(cmd) for cmd in dev.setup_commands),
        )
    config.devices = new_devices

    # Interpolate speeds
    config.speeds = {k: _sub(v) for k, v in config.speeds.items()}

    # Interpolate hosts
    config.hosts = {k: _sub(v) for k, v in config.hosts.items()}

    # Interpolate qdisc params
    new_qdiscs: list[QdiscConfig] = []
    for q in config.qdiscs:
        new_qdiscs.append(
            QdiscConfig(
                name=q.name,
                qdisc_type=q.qdisc_type,
                device=q.device,
                parent=q.parent,
                handle=q.handle,
                default=q.default,
                params={k: _sub(v) for k, v in q.params.items()},
            )
        )
    config.qdiscs = new_qdiscs

    # Interpolate class params
    new_classes: list[ClassConfig] = []
    for c in config.classes:
        new_classes.append(
            ClassConfig(
                name=c.name,
                class_type=c.class_type,
                parent=c.parent,
                params={k: _sub(v) for k, v in c.params.items()},
            )
        )
    config.classes = new_classes

    # Interpolate filter params
    new_filters: list[FilterConfig] = []
    for f in config.filters:
        new_filters.append(
            FilterConfig(
                name=f.name,
                filter_type=f.filter_type,
                device=f.device,
                parent=f.parent,
                send_to=f.send_to,
                protocol=f.protocol,
                prio=f.prio,
                handle=f.handle,
                ip_matches={k: _sub(v) for k, v in f.ip_matches.items()},
                match_params={k: _sub(v) for k, v in f.match_params.items()},
                actions=f.actions,
            )
        )
    config.filters = new_filters
