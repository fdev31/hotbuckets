"""Filter plugins for traffic control."""

from typing import Any

from hotbuckets.registry import FilterPlugin, Registry


@Registry.filter("u32")
class U32Filter(FilterPlugin):
    """Universal 32-bit filter for matching packet headers."""

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

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        # matchall takes no match parameters
        return []
