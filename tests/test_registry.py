"""Tests for hotbuckets.registry — plugin registration, lookup, and error handling."""

import pytest

from hotbuckets.errors import PluginError
from hotbuckets.registry import (
    ActionPlugin,
    FilterPlugin,
    QdiscPlugin,
    Registry,
    ResolverContext,
)


class TestResolverContext:
    """Test the ResolverContext data holder."""

    def test_default_empty(self):
        ctx = ResolverContext()
        assert ctx.qdisc_handles == {}
        assert ctx.class_ids == {}
        assert ctx.device_map == {}
        assert ctx.all_devices == set()


class TestRegistryLookup:
    """Test looking up registered plugins."""

    def test_get_qdisc_htb(self):
        plugin = Registry.get_qdisc("htb")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_tbf(self):
        plugin = Registry.get_qdisc("tbf")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_sfq(self):
        plugin = Registry.get_qdisc("sfq")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_netem(self):
        plugin = Registry.get_qdisc("netem")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_cake(self):
        plugin = Registry.get_qdisc("cake")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_ingress(self):
        plugin = Registry.get_qdisc("ingress")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_fq_codel(self):
        plugin = Registry.get_qdisc("fq_codel")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_filter_u32(self):
        plugin = Registry.get_filter("u32")
        assert isinstance(plugin, FilterPlugin)

    def test_get_filter_fw(self):
        plugin = Registry.get_filter("fw")
        assert isinstance(plugin, FilterPlugin)

    def test_get_filter_matchall(self):
        plugin = Registry.get_filter("matchall")
        assert isinstance(plugin, FilterPlugin)

    def test_get_action_mirred(self):
        plugin = Registry.get_action("mirred")
        assert isinstance(plugin, ActionPlugin)

    def test_get_action_police(self):
        plugin = Registry.get_action("police")
        assert isinstance(plugin, ActionPlugin)

    def test_get_action_drop(self):
        plugin = Registry.get_action("drop")
        assert isinstance(plugin, ActionPlugin)


class TestRegistryErrors:
    """Test error handling for unknown plugins."""

    def test_unknown_qdisc(self):
        with pytest.raises(PluginError, match="Unknown qdisc type 'nonexistent'"):
            Registry.get_qdisc("nonexistent")

    def test_unknown_filter(self):
        with pytest.raises(PluginError, match="Unknown filter type 'nonexistent'"):
            Registry.get_filter("nonexistent")

    def test_unknown_action(self):
        with pytest.raises(PluginError, match="Unknown action type 'nonexistent'"):
            Registry.get_action("nonexistent")


class TestRegistryAvailable:
    """Test listing available plugins."""

    def test_available_qdiscs(self):
        available = Registry.available_qdiscs()
        assert "htb" in available
        assert "tbf" in available
        assert "sfq" in available
        assert "netem" in available
        assert "cake" in available
        assert "ingress" in available
        assert "fq_codel" in available
        assert available == sorted(available)

    def test_available_filters(self):
        available = Registry.available_filters()
        assert "u32" in available
        assert "fw" in available
        assert "matchall" in available

    def test_available_actions(self):
        available = Registry.available_actions()
        assert "mirred" in available
        assert "police" in available
        assert "drop" in available
