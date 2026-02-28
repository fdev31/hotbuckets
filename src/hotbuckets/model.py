"""Domain model dataclasses for hotbuckets traffic control configuration."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    """A network device (physical or virtual like IFB)."""

    name: str
    dev: str
    virtual: bool = False
    dev_type: str = ""  # "ifb", "veth", etc. Only relevant for virtual devices.
    setup_commands: tuple[str, ...] = ()  # Pre-tc commands (modprobe, ip link set, etc.)


@dataclass(frozen=True)
class ActionConfig:
    """An action attached to a filter (e.g., mirred redirect, police, drop)."""

    type: str  # "mirred", "police", "drop"
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class QdiscConfig:
    """A queueing discipline (qdisc) configuration entry."""

    name: str
    qdisc_type: str  # "htb", "tbf", "sfq", "netem", "cake", "ingress", "fq_codel"
    device: str  # Reference to a device name
    parent: str = "root"  # "root", "ingress", or name of a class/qdisc
    handle: str = ""  # Auto-assigned if empty; explicit for special cases like "ffff:"
    default: str = ""  # Name of the default class (htb)
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassConfig:
    """A traffic class configuration entry."""

    name: str
    class_type: str = "htb"
    parent: str = ""  # Name of a qdisc or another class
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FilterConfig:
    """A traffic filter configuration entry."""

    name: str
    filter_type: str = "u32"  # "u32", "fw", "matchall"
    device: str = ""  # Optional; inherited from parent if empty
    parent: str = ""  # Name of a qdisc
    send_to: str = ""  # Name of a class or qdisc to direct matching traffic to
    protocol: str = ""  # e.g., "ip"
    prio: str = ""  # Filter priority
    handle: str = ""  # For fw filters: firewall mark handle
    ip_matches: dict[str, str] = field(default_factory=dict)  # e.g., {"dport": "80", "dst": "192.168.1.1"}
    actions: tuple[ActionConfig, ...] = ()


@dataclass
class TrafficConfig:
    """Complete parsed traffic control configuration."""

    tc: str = "tc"  # Path to the tc binary
    unit: str = ""  # Default speed unit suffix (e.g., "mbit")
    variables: dict[str, str] = field(default_factory=dict)
    speeds: dict[str, str] = field(default_factory=dict)
    hosts: dict[str, str] = field(default_factory=dict)
    devices: dict[str, Device] = field(default_factory=dict)
    qdiscs: list[QdiscConfig] = field(default_factory=list)
    classes: list[ClassConfig] = field(default_factory=list)
    filters: list[FilterConfig] = field(default_factory=list)
