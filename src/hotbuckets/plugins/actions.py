"""Action plugins for traffic control filters."""

from typing import Any

from hotbuckets.registry import ActionPlugin, ParamDoc, Registry


@Registry.action("mirred")
class MirredAction(ActionPlugin):
    """Mirror/redirect action for forwarding traffic between devices."""

    description = "Mirror or redirect packets to another network device"

    PARAMS = {
        "direction": ParamDoc("Traffic direction to act on", example="egress"),
        "mode": ParamDoc("redirect (move) or mirror (copy) packets", example="redirect"),
        "target": ParamDoc("Target device to send packets to", required=True, example="ifb0"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if "target" not in params:
            errors.append("mirred action requires 'target' parameter")
        return errors

    def generate(self, params: dict[str, Any]) -> list[str]:
        direction = params.get("direction", "egress")
        mode = params.get("mode", "redirect")
        target = params.get("target", "")

        # Resolve target device alias
        devices: dict[str, str] = params.get("_devices", {})
        if target in devices:
            target = devices[target]

        return ["action", "mirred", direction, mode, "dev", target]


@Registry.action("police")
class PoliceAction(ActionPlugin):
    """Police action for rate limiting."""

    description = "Rate-limit traffic -- exceed rate triggers conform-exceed policy"

    PARAMS = {
        "rate": ParamDoc("Maximum allowed rate", required=True, example="1mbit"),
        "burst": ParamDoc("Burst allowance in bytes", example="10k"),
        "conform-exceed": ParamDoc("Action on conform/exceed (e.g. drop/pipe)", example="drop"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        args = ["action", "police"]
        for key in ("rate", "burst", "conform-exceed"):
            if key in params:
                args.extend([key, str(params[key])])
        return args


@Registry.action("drop")
class DropAction(ActionPlugin):
    """Drop action to discard matching packets."""

    description = "Silently discard matching packets"

    PARAMS = {}

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        return ["action", "drop"]


# ── New Tier 1 actions ────────────────────────────────────────────


@Registry.action("skbedit")
class SkbeditAction(ActionPlugin):
    """Set packet metadata fields on the skb (socket buffer).

    Allows modifying the packet's mark, priority, or hardware
    queue mapping. Commonly used with flower filters for
    advanced classification.
    """

    description = "Set packet metadata -- mark, priority, or hardware queue mapping"

    PARAMS = {
        "mark": ParamDoc("Set the skb mark (for later fw filter matching or routing)", example="42"),
        "priority": ParamDoc("Set the skb priority (maps to tc prio bands)", example="7"),
        "queue_mapping": ParamDoc("Set the hardware TX queue index", example="3"),
    }

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        has_param = any(k in params for k in ("mark", "priority", "queue_mapping"))
        if not has_param:
            errors.append("skbedit requires at least one of: mark, priority, queue_mapping")
        return errors

    def generate(self, params: dict[str, Any]) -> list[str]:
        args = ["action", "skbedit"]
        for key in ("mark", "priority", "queue_mapping"):
            if key in params:
                args.extend([key, str(params[key])])
        return args
