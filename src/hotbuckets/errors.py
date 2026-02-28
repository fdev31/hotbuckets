"""Custom exception hierarchy for hotbuckets."""


class HotbucketsError(Exception):
    """Base exception for all hotbuckets errors."""


class ConfigError(HotbucketsError):
    """Error in configuration file structure or content."""

    def __init__(self, message: str, section: str = "", key: str = "") -> None:
        self.section = section
        self.key = key
        if section and key:
            message = f"[{section}.{key}] {message}"
        elif section:
            message = f"[{section}] {message}"
        super().__init__(message)


class ValidationError(HotbucketsError):
    """Error validating a configuration entry."""

    def __init__(self, message: str, entry_type: str = "", entry_name: str = "") -> None:
        self.entry_type = entry_type
        self.entry_name = entry_name
        if entry_type and entry_name:
            message = f"{entry_type} '{entry_name}': {message}"
        super().__init__(message)


class ResolutionError(HotbucketsError):
    """Error resolving references between configuration entries."""

    def __init__(self, message: str, source: str = "", target: str = "") -> None:
        self.source = source
        self.target = target
        super().__init__(message)


class CyclicDependencyError(ResolutionError):
    """Circular dependency detected in configuration."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {path}")


class PluginError(HotbucketsError):
    """Error related to plugin registration or lookup."""
