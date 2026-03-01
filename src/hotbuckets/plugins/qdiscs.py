"""Qdisc plugins for traffic control."""

from typing import Any

from hotbuckets.registry import ParamDoc, QdiscPlugin, Registry


@Registry.qdisc("htb")
class HtbQdisc(QdiscPlugin):
    """Hierarchical Token Bucket qdisc."""

    description = "Hierarchical Token Bucket -- classful shaping with rate guarantees and ceiling limits"

    PARAMS = {
        "latency": ParamDoc("Maximum queue latency before packets are dropped", example="200ms"),
        "burst": ParamDoc("Burst size in bytes -- how much data can be sent at once above the rate", example="5000"),
        "rate": ParamDoc("Maximum sustained transmit rate", example="10mbit"),
    }

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

    description = "Token Bucket Filter -- simple classless rate limiter"

    PARAMS = {
        "rate": ParamDoc("Maximum transmit rate", required=True, example="10mbit"),
        "burst": ParamDoc("Bucket size in bytes -- max burst before throttling", required=True, example="5000"),
        "latency": ParamDoc("Maximum time a packet can wait in the queue", example="200ms"),
    }

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

    description = "Stochastic Fairness Queueing -- classless round-robin across flow buckets"

    PARAMS = {
        "quantum": ParamDoc("Bytes dequeued per round-robin turn (typically MTU)", example="1500"),
        "perturb": ParamDoc("Seconds between hash function perturbation (prevents flow starvation)", example="10"),
    }

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

    description = "Network Emulator -- simulate delay, loss, corruption, reordering"

    PARAMS = {
        "delay": ParamDoc("Fixed or variable delay added to packets", example="100ms"),
        "loss": ParamDoc("Random packet loss probability", example="1%"),
        "duplicate": ParamDoc("Packet duplication probability", example="1%"),
        "corrupt": ParamDoc("Random bit-error corruption probability", example="0.1%"),
        "reorder": ParamDoc("Packet reordering probability (with correlation)", example="50% 50%"),
    }

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

    description = "CAKE -- modern all-in-one AQM with shaping, flow isolation, and prioritization"

    PARAMS = {
        "bandwidth": ParamDoc("Shaping rate (required for effective AQM)", example="100mbit"),
        "diffserv4": ParamDoc("4-tier DSCP-based priority (bulk, besteffort, video, voice)"),
        "diffserv3": ParamDoc("3-tier DSCP-based priority (bulk, besteffort, voice)"),
        "diffserv8": ParamDoc("8-tier DSCP-based priority"),
        "besteffort": ParamDoc("Treat all traffic as best-effort (no DSCP differentiation)"),
        "flowblind": ParamDoc("Disable per-flow fairness -- all traffic shares one queue"),
        "srchost": ParamDoc("Per-source-host fairness (instead of per-flow)"),
        "dsthost": ParamDoc("Per-destination-host fairness (instead of per-flow)"),
        "hosts": ParamDoc("Per-host fairness in both directions"),
        "flows": ParamDoc("Per-flow fairness (default)"),
        "dual-srchost": ParamDoc("Per-flow within per-source-host fairness"),
        "dual-dsthost": ParamDoc("Per-flow within per-destination-host fairness"),
        "nat": ParamDoc("Perform NAT address lookup to improve fairness behind NAT"),
        "nonat": ParamDoc("Disable NAT address lookup"),
        "wash": ParamDoc("Clear DSCP bits on egress (prevent priority leaking upstream)"),
        "nowash": ParamDoc("Preserve DSCP bits on egress"),
        "split-gso": ParamDoc("Split GRO/GSO super-packets for better scheduling"),
        "no-split-gso": ParamDoc("Keep GRO/GSO super-packets intact"),
        "ack-filter": ParamDoc("Filter redundant TCP ACKs to reduce overhead"),
        "no-ack-filter": ParamDoc("Disable ACK filtering"),
        "ingress": ParamDoc("Mark this as an ingress shaper (overhead compensation)"),
        "egress": ParamDoc("Mark this as an egress shaper (default)"),
        "raw": ParamDoc("No overhead compensation"),
        "conservative": ParamDoc("Extra-safe overhead compensation"),
    }

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

    description = "Ingress hook -- attach filters to incoming packets (use clsact for ingress+egress)"

    PARAMS = {}

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        # Ingress qdisc takes no additional parameters
        return []


@Registry.qdisc("fq_codel")
class FqCodelQdisc(QdiscPlugin):
    """Fair Queue Controlled Delay (fq_codel) qdisc."""

    description = "Fair Queue CoDel -- per-flow queuing with AQM to fight bufferbloat"

    PARAMS = {
        "limit": ParamDoc("Maximum number of packets in the queue", example="1000"),
        "flows": ParamDoc("Number of flow buckets for hashing", example="1024"),
        "target": ParamDoc("Target sojourn time for CoDel AQM", example="5ms"),
        "interval": ParamDoc("Width of the moving time window for CoDel", example="100ms"),
        "quantum": ParamDoc("Bytes dequeued per round-robin turn", example="1514"),
        "ecn": ParamDoc("Enable ECN marking instead of dropping"),
        "noecn": ParamDoc("Disable ECN marking (drop instead)"),
    }

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


# ── New Tier 1 qdiscs ─────────────────────────────────────────────


@Registry.qdisc("prio")
class PrioQdisc(QdiscPlugin):
    """Priority scheduler qdisc.

    Creates multiple bands (default 3) and always dequeues from the
    lowest-numbered non-empty band first. Bands are auto-created as
    child classes (handle:1, handle:2, ...).
    """

    description = "Priority scheduler -- dequeues from lowest non-empty band first"

    PARAMS = {
        "bands": ParamDoc("Number of priority bands (default 3, range 2-16)", example="3"),
        "priomap": ParamDoc(
            "Space-separated map of 16 Linux priority values to bands (0-indexed)",
            example="1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1",
        ),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if "bands" in params:
            try:
                bands = int(params["bands"])
                if bands < 2 or bands > 16:
                    errors.append(f"prio bands must be 2-16, got {bands}")
            except ValueError:
                errors.append(f"prio bands must be an integer, got '{params['bands']}'")
        if "priomap" in params:
            parts = str(params["priomap"]).split()
            if len(parts) != 16:
                errors.append(f"priomap must have exactly 16 values, got {len(parts)}")
        return errors

    def generate(self, params: dict[str, Any]) -> list[str]:
        args: list[str] = []
        if "bands" in params:
            args.extend(["bands", str(params["bands"])])
        if "priomap" in params:
            args.append("priomap")
            args.extend(str(params["priomap"]).split())
        return args


@Registry.qdisc("hfsc")
class HfscQdisc(QdiscPlugin):
    """Hierarchical Fair Service Curve qdisc.

    HFSC provides real-time latency guarantees with link-sharing
    using service curve specifications (rt, ls, ul).
    """

    description = "Hierarchical Fair Service Curve -- real-time latency guarantees with link sharing"

    PARAMS = {
        "default": ParamDoc("Default class for unclassified traffic (minor number)", example="1"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        # default is handled by script.py's _generate_qdisc (same as htb)
        return []


@Registry.qdisc("clsact")
class ClsactQdisc(QdiscPlugin):
    """Classify-Act qdisc.

    Modern replacement for ingress qdisc. Supports both ingress and
    egress filter attachment points. Always uses handle ffff:.
    Commonly used with flower filters and BPF programs.
    """

    description = "Classify-Act -- modern ingress+egress hook point for filters (replaces ingress)"

    PARAMS = {}

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        return []
