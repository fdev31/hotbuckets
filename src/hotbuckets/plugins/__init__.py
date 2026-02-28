"""Auto-import all plugin modules to trigger registration."""

from hotbuckets.plugins import actions, filters, qdiscs

__all__ = ["qdiscs", "filters", "actions"]
