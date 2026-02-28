"""Tests for hotbuckets.resolver — topological sort, handle assignment, device inheritance."""

import pytest

from hotbuckets.config import load_string
from hotbuckets.errors import CyclicDependencyError, ResolutionError
from hotbuckets.resolver import ResolverResult, resolve, _topological_sort


class TestTopologicalSort:
    """Test the Kahn's algorithm implementation."""

    def test_empty_graph(self):
        assert _topological_sort({}) == []

    def test_single_node(self):
        assert _topological_sort({"a": set()}) == ["a"]

    def test_linear_chain(self):
        deps = {"a": set(), "b": {"a"}, "c": {"b"}}
        result = _topological_sort(deps)
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_diamond_graph(self):
        deps = {"a": set(), "b": {"a"}, "c": {"a"}, "d": {"b", "c"}}
        result = _topological_sort(deps)
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_preserves_insertion_order(self):
        """Nodes at the same level should preserve their insertion order."""
        deps = {"x": set(), "y": set(), "z": set()}
        result = _topological_sort(deps)
        assert result == ["x", "y", "z"]

    def test_cyclic_dependency_raises(self):
        deps = {"a": {"b"}, "b": {"a"}}
        with pytest.raises(CyclicDependencyError) as exc_info:
            _topological_sort(deps)
        assert "a" in exc_info.value.cycle
        assert "b" in exc_info.value.cycle

    def test_three_node_cycle(self):
        deps = {"a": {"c"}, "b": {"a"}, "c": {"b"}}
        with pytest.raises(CyclicDependencyError):
            _topological_sort(deps)

    def test_deps_referencing_external_nodes(self):
        """Dependencies on nodes not in the graph are ignored."""
        deps = {"a": {"external"}, "b": set()}
        result = _topological_sort(deps)
        assert set(result) == {"a", "b"}


class TestQdiscHandleAssignment:
    """Test sequential handle assignment for qdiscs."""

    def test_single_qdisc_gets_handle_1(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        assert result.qdisc_handles["root"] == "1:"

    def test_multiple_qdiscs_sequential(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
default = "c1"

[class.c1]
parent = "root"
rate = "10mbit"

[shaper.child]
parent = "c1"
type = "sfq"
""")
        result = resolve(config)
        assert result.qdisc_handles["root"] == "1:"
        assert result.qdisc_handles["child"] == "2:"

    def test_explicit_handle_not_incremented(self):
        """Explicit handles (like ffff: for ingress) skip the auto-counter."""
        config = load_string("""
[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"

[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        assert result.qdisc_handles["ingress"] == "ffff:"
        assert result.qdisc_handles["root"] == "1:"


class TestClassIdAssignment:
    """Test class ID assignment with global minor counter."""

    def test_class_gets_parent_major(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"
""")
        result = resolve(config)
        assert result.class_ids["c1"] == "1:1"

    def test_global_minor_counter(self):
        """Minor IDs are global, not per-qdisc."""
        config = load_string("""
[shaper.root]
dev = "eth0"
default = "c1"

[class.c1]
parent = "root"
rate = "10mbit"

[class.c2]
parent = "root"
rate = "20mbit"

[class.c3]
parent = "c1"
rate = "5mbit"
""")
        result = resolve(config)
        assert result.class_ids["c1"] == "1:1"
        assert result.class_ids["c2"] == "1:2"
        # c3's parent is c1 which has major 1
        assert result.class_ids["c3"] == "1:3"


class TestDeviceResolution:
    """Test device name resolution and inheritance."""

    def test_qdisc_direct_device(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        assert result.device_map["root"] == "eth0"

    def test_class_inherits_device_from_parent_qdisc(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"
""")
        result = resolve(config)
        assert result.device_map["c1"] == "eth0"

    def test_filter_inherits_device_from_parent(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[match.f1]
protocol = "ip"
parent = "root"
sendTo = "root"
ip = {dport = "80"}
""")
        result = resolve(config)
        assert result.device_map["f1"] == "eth0"

    def test_device_alias_resolution(self):
        """Named devices (from [devices] section) are resolved to real dev names."""
        config = load_string("""
[devices.nic]
dev = "wlo1"

[shaper.root]
dev = "nic"
""")
        result = resolve(config)
        assert result.device_map["root"] == "wlo1"

    def test_all_devices_collected(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        assert "eth0" in result.all_devices


class TestEntrySorting:
    """Test that resolved entries are sorted correctly."""

    def test_sort_by_handle(self):
        """Entries are sorted by (major, minor) of their handle."""
        config = load_string("""
[shaper.root]
dev = "eth0"
default = "c1"

[class.c1]
parent = "root"
rate = "10mbit"

[shaper.child]
parent = "c1"
type = "sfq"
""")
        result = resolve(config)
        names = [e.name for e in result.entries]
        # qdisc root (1:), class c1 (1:1), qdisc child (2:)
        assert names.index("root") < names.index("c1")
        assert names.index("c1") < names.index("child")

    def test_fw_filter_sorts_by_handle_value(self):
        """fw filters with numeric handles sort before u32 filters."""
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"

[match.u32_filter]
protocol = "ip"
parent = "root"
sendTo = "c1"
ip = {dport = "80"}

[match.fw_filter]
protocol = "ip"
type = "fw"
parent = "root"
sendTo = "c1"
handle = "42"
""")
        result = resolve(config)
        names = [e.name for e in result.entries]
        # fw_filter (handle=42 -> sort key (42,0)) before u32_filter (sort key (999,999))
        assert names.index("fw_filter") < names.index("u32_filter")

    def test_filters_sort_after_qdiscs_and_classes(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"

[match.f1]
protocol = "ip"
parent = "root"
sendTo = "c1"
ip = {dport = "80"}
""")
        result = resolve(config)
        names = [e.name for e in result.entries]
        assert names.index("root") < names.index("f1")
        assert names.index("c1") < names.index("f1")


class TestIngressDevices:
    """Test ingress device tracking."""

    def test_ingress_qdisc_tracked(self):
        config = load_string("""
[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"
""")
        result = resolve(config)
        assert "eth0" in result.ingress_devices

    def test_non_ingress_not_tracked(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        assert len(result.ingress_devices) == 0


class TestVirtualDevices:
    """Test virtual device collection."""

    def test_virtual_device_collected(self):
        config = load_string("""
[devices.ifb0]
dev = "ifb0"
virtual = true
type = "ifb"

[shaper.root]
dev = "ifb0"
type = "cake"
bandwidth = "100mbit"
""")
        result = resolve(config)
        assert "ifb0" in result.virtual_devices
