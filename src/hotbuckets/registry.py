"""Plugin registry for qdisc, filter, and action plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hotbuckets.errors import PluginError


class ResolverContext:
    """Context passed to plugins during command generation.

    Provides resolved handles, device names, and ID mappings
    that plugins need to generate correct tc commands.
    """

    def __init__(self) -> None:
        self.qdisc_handles: dict[str, str] = {}  # name -> "N:"
        self.class_ids: dict[str, str] = {}  # name -> "major:minor"
        self.device_map: dict[str, str] = {}  # entry name -> resolved device name
        self.all_devices: set[str] = set()  # all real device names encountered


class QdiscPlugin(ABC):
    """Base class for qdisc plugins."""

    @abstractmethod
    def validate(self, params: dict[str, Any]) -> list[str]:
        """Validate qdisc parameters. Return list of error messages (empty = valid)."""

    @abstractmethod
    def generate(self, params: dict[str, Any]) -> list[str]:
        """Generate tc command arguments for this qdisc type (after 'handle N: <type>')."""


class FilterPlugin(ABC):
    """Base class for filter plugins."""

    @abstractmethod
    def validate(self, params: dict[str, Any]) -> list[str]:
        """Validate filter parameters. Return list of error messages (empty = valid)."""

    @abstractmethod
    def generate(self, params: dict[str, Any]) -> list[str]:
        """Generate tc command arguments for this filter type."""


class ActionPlugin(ABC):
    """Base class for action plugins."""

    @abstractmethod
    def validate(self, params: dict[str, Any]) -> list[str]:
        """Validate action parameters. Return list of error messages (empty = valid)."""

    @abstractmethod
    def generate(self, params: dict[str, Any]) -> list[str]:
        """Generate tc action arguments."""


class Registry:
    """Central registry for all plugin types."""

    _qdiscs: dict[str, type[QdiscPlugin]] = {}
    _filters: dict[str, type[FilterPlugin]] = {}
    _actions: dict[str, type[ActionPlugin]] = {}

    @classmethod
    def qdisc(cls, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a qdisc plugin."""

        def decorator(plugin_cls: type[QdiscPlugin]) -> type[QdiscPlugin]:
            if name in cls._qdiscs:
                raise PluginError(f"Qdisc plugin '{name}' is already registered")
            cls._qdiscs[name] = plugin_cls
            return plugin_cls

        return decorator

    @classmethod
    def filter(cls, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a filter plugin."""

        def decorator(plugin_cls: type[FilterPlugin]) -> type[FilterPlugin]:
            if name in cls._filters:
                raise PluginError(f"Filter plugin '{name}' is already registered")
            cls._filters[name] = plugin_cls
            return plugin_cls

        return decorator

    @classmethod
    def action(cls, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register an action plugin."""

        def decorator(plugin_cls: type[ActionPlugin]) -> type[ActionPlugin]:
            if name in cls._actions:
                raise PluginError(f"Action plugin '{name}' is already registered")
            cls._actions[name] = plugin_cls
            return plugin_cls

        return decorator

    @classmethod
    def get_qdisc(cls, name: str) -> QdiscPlugin:
        """Get a qdisc plugin instance by type name."""
        if name not in cls._qdiscs:
            raise PluginError(f"Unknown qdisc type '{name}'. Available: {', '.join(sorted(cls._qdiscs))}")
        return cls._qdiscs[name]()

    @classmethod
    def get_filter(cls, name: str) -> FilterPlugin:
        """Get a filter plugin instance by type name."""
        if name not in cls._filters:
            raise PluginError(f"Unknown filter type '{name}'. Available: {', '.join(sorted(cls._filters))}")
        return cls._filters[name]()

    @classmethod
    def get_action(cls, name: str) -> ActionPlugin:
        """Get an action plugin instance by type name."""
        if name not in cls._actions:
            raise PluginError(f"Unknown action type '{name}'. Available: {', '.join(sorted(cls._actions))}")
        return cls._actions[name]()

    @classmethod
    def available_qdiscs(cls) -> list[str]:
        return sorted(cls._qdiscs.keys())

    @classmethod
    def available_filters(cls) -> list[str]:
        return sorted(cls._filters.keys())

    @classmethod
    def available_actions(cls) -> list[str]:
        return sorted(cls._actions.keys())

    @classmethod
    def _reset(cls) -> None:
        """Reset all registries. For testing only."""
        cls._qdiscs.clear()
        cls._filters.clear()
        cls._actions.clear()
