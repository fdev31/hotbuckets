"""Action plugins for traffic control filters."""

from typing import Any

from hotbuckets.registry import ActionPlugin, Registry


@Registry.action("mirred")
class MirredAction(ActionPlugin):
    """Mirror/redirect action for forwarding traffic between devices."""

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

    def validate(self, params: dict[str, Any]) -> list[str]:
        return []

    def generate(self, params: dict[str, Any]) -> list[str]:
        return ["action", "drop"]
