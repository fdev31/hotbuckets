"""Qdisc plugins for traffic control."""

from typing import Any

from hotbuckets.registry import QdiscPlugin, Registry


@Registry.qdisc("htb")
class HtbQdisc(QdiscPlugin):
    """Hierarchical Token Bucket qdisc."""

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for key in ("latency", "burst", "rate"):
            if key in params:
                args.extend([key, str(params[key])])
        return args


@Registry.qdisc("tbf")
class TbfQdisc(QdiscPlugin):
    """Token Bucket Filter qdisc."""

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if "rate" not in params:
            errors.append("TBF requires 'rate' parameter")
        return errors

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for key in ("latency", "burst", "rate"):
            if key in params:
                args.extend([key, str(params[key])])
        return args


@Registry.qdisc("sfq")
class SfqQdisc(QdiscPlugin):
    """Stochastic Fairness Queueing qdisc."""

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        # Default perturb to 10 if not set
        if "perturb" not in params:
            params["perturb"] = "10"
        if "quantum" in params:
            args.extend(["quantum", str(params["quantum"])])
        args.extend(["perturb", str(params["perturb"])])
        return args


@Registry.qdisc("netem")
class NetemQdisc(QdiscPlugin):
    """Network Emulator qdisc for simulating network conditions."""

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for key in ("delay", "loss", "duplicate", "corrupt", "reorder"):
            if key in params:
                args.extend([key, str(params[key])])
        return args


@Registry.qdisc("cake")
class CakeQdisc(QdiscPlugin):
    """Common Applications Kept Enhanced (CAKE) qdisc.

    CAKE is a modern, comprehensive qdisc that combines shaping,
    AQM, flow isolation, and prioritization.
    """

    # Boolean flags that don't take a value
    BOOLEAN_PARAMS = {
        "diffserv4",
        "diffserv3",
        "diffserv8",
        "besteffort",
        "flowblind",
        "srchost",
        "dsthost",
        "hosts",
        "flows",
        "dual-srchost",
        "dual-dsthost",
        "nat",
        "nonat",
        "wash",
        "nowash",
        "split-gso",
        "no-split-gso",
        "ack-filter",
        "no-ack-filter",
        "ingress",
        "egress",
        "raw",
        "conservative",
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        # Handle bandwidth first (most common param)
        if "bandwidth" in params:
            args.extend(["bandwidth", str(params["bandwidth"])])

        # Handle remaining params
        for key, value in params.items():
            if key == "bandwidth":
                continue
            if key in self.BOOLEAN_PARAMS:
                # Boolean flags: only emit the key if truthy
                if str(value).lower() not in ("false", "0", "no", ""):
                    args.append(key)
            else:
                args.extend([key, str(value)])
        return args


@Registry.qdisc("ingress")
class IngressQdisc(QdiscPlugin):
    """Ingress qdisc for incoming traffic processing.

    The ingress qdisc is a special qdisc used to attach filters
    to incoming traffic. It always uses handle ffff:.
    """

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        # Ingress qdisc takes no additional parameters
        return []


@Registry.qdisc("fq_codel")
class FqCodelQdisc(QdiscPlugin):
    """Fair Queue Controlled Delay (fq_codel) qdisc."""

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for key in ("limit", "flows", "target", "interval", "quantum", "ecn", "noecn"):
            if key in params:
                val = str(params[key])
                if key in ("ecn", "noecn") and val.lower() not in ("false", "0", "no", ""):
                    args.append(key)
                else:
                    args.extend([key, val])
        return args
