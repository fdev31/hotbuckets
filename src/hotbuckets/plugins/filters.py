"""Filter plugins for traffic control."""

from typing import Any

from hotbuckets.registry import FilterPlugin, ParamDoc, Registry


@Registry.filter("u32")
class U32Filter(FilterPlugin):
    """Universal 32-bit filter for matching packet headers."""

    description = "Universal 32-bit classifier -- match on IP header fields with byte offsets"

    PARAMS = {
        "src": ParamDoc("Source IP address or CIDR", example="192.168.1.0/24"),
        "dst": ParamDoc("Destination IP address or CIDR", example="10.0.0.1"),
        "sport": ParamDoc("Source port number", example="80"),
        "dport": ParamDoc("Destination port number", example="443"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        ip_matches: dict[str, str] = params.get("ip_matches", {})
        hosts: dict[str, str] = params.get("hosts", {})

        for key, value in ip_matches.items():
            args.extend(["match", "ip"])
            # Resolve host aliases
            if value in hosts:
                value = hosts[value]
            args.extend([key, str(value)])
            # Ports need a mask
            if key.endswith("port"):
                args.append("0xffff")

        return args


@Registry.filter("fw")
class FwFilter(FilterPlugin):
    """Firewall mark filter (matches iptables/nftables marks)."""

    description = "Firewall mark classifier -- match packets by iptables/nftables fwmark"

    PARAMS = {
        "handle": ParamDoc("Firewall mark value to match", required=True, example="42"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        handle = params.get("handle", "")
        if handle:
            args.extend(["handle", str(handle)])
        return args


@Registry.filter("matchall")
class MatchallFilter(FilterPlugin):
    """Match-all filter that matches every packet."""

    description = "Match-all -- matches every packet unconditionally (use with actions)"

    PARAMS = {}

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        # matchall takes no match parameters
        return []


# ── New Tier 1 filters ────────────────────────────────────────────


@Registry.filter("flower")
class FlowerFilter(FilterPlugin):
    """Modern L2-L4 packet classifier.

    Flower matches on many header fields simultaneously using a
    clean key-value syntax instead of u32 byte offsets.
    Commonly used with clsact qdisc and actions.
    """

    description = "Modern L2-L4 classifier -- match on IP, port, protocol, MAC, VLAN, and more"

    PARAMS = {
        "src_ip": ParamDoc("Source IP address with optional /mask", example="192.168.1.0/24"),
        "dst_ip": ParamDoc("Destination IP address with optional /mask", example="10.0.0.1/32"),
        "ip_proto": ParamDoc("IP protocol (tcp, udp, icmp, or number)", example="tcp"),
        "src_port": ParamDoc("Source port number", example="8080"),
        "dst_port": ParamDoc("Destination port number", example="80"),
        "src_mac": ParamDoc("Source MAC address", example="aa:bb:cc:dd:ee:ff"),
        "dst_mac": ParamDoc("Destination MAC address", example="aa:bb:cc:dd:ee:ff"),
        "vlan_id": ParamDoc("VLAN tag ID", example="100"),
        "vlan_prio": ParamDoc("VLAN priority (0-7)", example="3"),
        "indev": ParamDoc("Ingress device name", example="eth0"),
    }

    # Fields that support host alias resolution
    _HOST_FIELDS = {"src_ip", "dst_ip"}

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        match_params = params.get("match_params", {})
        if not match_params:
            errors.append("flower filter requires at least one match field")
        return errors

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        match_params: dict[str, str] = params.get("match_params", {})
        hosts: dict[str, str] = params.get("hosts", {})

        # Emit match fields in a stable order
        ordered_keys = [
            "src_ip",
            "dst_ip",
            "ip_proto",
            "src_port",
            "dst_port",
            "src_mac",
            "dst_mac",
            "vlan_id",
            "vlan_prio",
            "indev",
        ]
        for key in ordered_keys:
            if key in match_params:
                value = match_params[key]
                # Resolve host aliases for IP fields
                if key in self._HOST_FIELDS and value in hosts:
                    value = hosts[value]
                args.extend([key, str(value)])

        # Any remaining keys not in our ordered list
        for key, value in match_params.items():
            if key not in ordered_keys:
                if key in self._HOST_FIELDS and value in hosts:
                    value = hosts[value]
                args.extend([key, str(value)])

        return args
