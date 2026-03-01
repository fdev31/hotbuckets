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

    def test_get_qdisc_prio(self):
        plugin = Registry.get_qdisc("prio")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_hfsc(self):
        plugin = Registry.get_qdisc("hfsc")
        assert isinstance(plugin, QdiscPlugin)

    def test_get_qdisc_clsact(self):
        plugin = Registry.get_qdisc("clsact")
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

    def test_get_filter_flower(self):
        plugin = Registry.get_filter("flower")
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

    def test_get_action_skbedit(self):
        plugin = Registry.get_action("skbedit")
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
        assert "prio" in available
        assert "hfsc" in available
        assert "clsact" in available
        assert available == sorted(available)

    def test_available_filters(self):
        available = Registry.available_filters()
        assert "u32" in available
        assert "fw" in available
        assert "matchall" in available
        assert "flower" in available

    def test_available_actions(self):
        available = Registry.available_actions()
        assert "mirred" in available
        assert "police" in available
        assert "drop" in available
        assert "skbedit" in available


class TestRegistryListAll:
    """Test the list_all() structured info method."""

    def test_list_all_has_all_sections(self):
        info = Registry.list_all()
        assert "qdiscs" in info
        assert "filters" in info
        assert "actions" in info

    def test_list_all_qdisc_count(self):
        info = Registry.list_all()
        names = [e["name"] for e in info["qdiscs"]]
        assert "htb" in names
        assert "prio" in names
        assert "hfsc" in names
        assert "clsact" in names
        assert len(names) == 10  # htb, tbf, sfq, netem, cake, ingress, fq_codel, prio, hfsc, clsact

    def test_list_all_filter_count(self):
        info = Registry.list_all()
        names = [e["name"] for e in info["filters"]]
        assert "flower" in names
        assert len(names) == 4  # u32, fw, matchall, flower

    def test_list_all_action_count(self):
        info = Registry.list_all()
        names = [e["name"] for e in info["actions"]]
        assert "skbedit" in names
        assert len(names) == 4  # mirred, police, drop, skbedit

    def test_list_all_entry_has_description_and_params(self):
        info = Registry.list_all()
        htb = next(e for e in info["qdiscs"] if e["name"] == "htb")
        assert htb["description"]
        assert "rate" in htb["params"]
        assert htb["params"]["rate"]["description"]

    def test_list_all_sorted(self):
        info = Registry.list_all()
        qdisc_names = [e["name"] for e in info["qdiscs"]]
        assert qdisc_names == sorted(qdisc_names)
