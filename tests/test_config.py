"""Tests for hotbuckets.config — TOML loading, validation, variable resolution."""

import pytest

from hotbuckets.config import load_string
from hotbuckets.errors import ConfigError


class TestLoadBasic:
    """Test basic TOML loading."""

    def test_empty_config(self):
        config = load_string("")
        assert config.tc == "tc"
        assert config.unit == ""
        assert config.variables == {}
        assert config.speeds == {}
        assert config.hosts == {}
        assert config.devices == {}
        assert config.qdiscs == []
        assert config.classes == []
        assert config.filters == []

    def test_custom_tc_path(self):
        config = load_string('tc = "/sbin/tc"')
        assert config.tc == "/sbin/tc"

    def test_unit(self):
        config = load_string('unit = "mbit"')
        assert config.unit == "mbit"

    def test_speeds(self):
        config = load_string("""
[speeds]
full = "32mbit"
half = "15mbit"
""")
        assert config.speeds == {"full": "32mbit", "half": "15mbit"}

    def test_hosts_dict_format(self):
        """Test hosts with nested dict format (old style)."""
        config = load_string("""
[hosts.stb]
ip = "192.168.100.42"
""")
        assert config.hosts == {"stb": "192.168.100.42"}

    def test_hosts_string_format(self):
        """Test hosts with direct string format."""
        config = load_string("""
[hosts]
stb = "192.168.100.42"
""")
        assert config.hosts == {"stb": "192.168.100.42"}


class TestDevices:
    """Test device/interface parsing."""

    def test_devices_section(self):
        config = load_string("""
[devices.main]
dev = "eth0"
""")
        assert "main" in config.devices
        assert config.devices["main"].dev == "eth0"
        assert config.devices["main"].virtual is False

    def test_legacy_interfaces_section(self):
        """Test backward compatibility with [interfaces] section."""
        config = load_string("""
[interfaces.nic]
dev = "wlo1"
""")
        assert "nic" in config.devices
        assert config.devices["nic"].dev == "wlo1"

    def test_virtual_device(self):
        config = load_string("""
[devices.ifb0]
dev = "ifb0"
virtual = true
type = "ifb"
""")
        dev = config.devices["ifb0"]
        assert dev.virtual is True
        assert dev.dev_type == "ifb"
        assert len(dev.setup_commands) == 2
        assert "modprobe ifb numifbs=1" in dev.setup_commands
        assert "ip link set dev ifb0 up" in dev.setup_commands


class TestVariableInterpolation:
    """Test {varname} variable substitution."""

    def test_variable_in_device(self):
        config = load_string("""
[vars]
iface = "eth0"

[devices.main]
dev = "{iface}"
""")
        assert config.devices["main"].dev == "eth0"

    def test_variable_in_qdisc_params(self):
        config = load_string("""
[vars]
bw = "100mbit"

[shaper.root]
dev = "eth0"
type = "cake"
bandwidth = "{bw}"
""")
        assert config.qdiscs[0].params["bandwidth"] == "100mbit"

    def test_unresolved_variable_left_as_is(self):
        config = load_string("""
[vars]
a = "1"

[shaper.root]
dev = "eth0"
bandwidth = "{unknown}"
""")
        assert config.qdiscs[0].params["bandwidth"] == "{unknown}"

    def test_variable_in_speeds(self):
        config = load_string("""
[vars]
maxbw = "100mbit"

[speeds]
full = "{maxbw}"
""")
        assert config.speeds["full"] == "100mbit"


class TestQdiscParsing:
    """Test [shaper.*] section parsing."""

    def test_basic_qdisc(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
type = "htb"
""")
        assert len(config.qdiscs) == 1
        q = config.qdiscs[0]
        assert q.name == "root"
        assert q.qdisc_type == "htb"
        assert q.device == "eth0"
        assert q.parent == "root"

    def test_qdisc_defaults(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        q = config.qdiscs[0]
        assert q.qdisc_type == "htb"  # Default type
        assert q.parent == "root"  # Default parent

    def test_qdisc_with_explicit_handle(self):
        config = load_string("""
[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"
""")
        q = config.qdiscs[0]
        assert q.handle == "ffff:"

    def test_qdisc_passthrough_params(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
type = "netem"
delay = "100ms"
loss = "1%"
""")
        q = config.qdiscs[0]
        assert q.params["delay"] == "100ms"
        assert q.params["loss"] == "1%"

    def test_qdisc_with_default_class(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
default = "myclass"
""")
        q = config.qdiscs[0]
        assert q.default == "myclass"


class TestClassParsing:
    """Test [class.*] section parsing."""

    def test_basic_class(self):
        config = load_string("""
[class.myclass]
parent = "root"
rate = "10mbit"
""")
        assert len(config.classes) == 1
        c = config.classes[0]
        assert c.name == "myclass"
        assert c.class_type == "htb"
        assert c.parent == "root"
        assert c.params["rate"] == "10mbit"

    def test_class_with_ceil(self):
        config = load_string("""
[class.myclass]
parent = "root"
rate = "10mbit"
ceil = "100mbit"
""")
        c = config.classes[0]
        assert c.params["ceil"] == "100mbit"


class TestFilterParsing:
    """Test [match.*] section parsing."""

    def test_u32_filter(self):
        config = load_string("""
[match.filt1]
protocol = "ip"
parent = "root"
sendTo = "myclass"
ip = {dport = "80"}
""")
        f = config.filters[0]
        assert f.name == "filt1"
        assert f.filter_type == "u32"
        assert f.protocol == "ip"
        assert f.send_to == "myclass"
        assert f.ip_matches == {"dport": "80"}

    def test_fw_filter(self):
        config = load_string("""
[match.filt1]
protocol = "ip"
type = "fw"
parent = "root"
sendTo = "myclass"
handle = "42"
""")
        f = config.filters[0]
        assert f.filter_type == "fw"
        assert f.handle == "42"

    def test_matchall_filter_with_action_subtable(self):
        config = load_string("""
[match.redirect]
dev = "eth0"
parent = "ingress"
type = "matchall"

[match.redirect.action]
type = "mirred"
direction = "egress"
mode = "redirect"
target = "ifb0"
""")
        f = config.filters[0]
        assert f.filter_type == "matchall"
        assert len(f.actions) == 1
        a = f.actions[0]
        assert a.type == "mirred"
        assert a.params["direction"] == "egress"
        assert a.params["mode"] == "redirect"
        assert a.params["target"] == "ifb0"

    def test_inline_string_action(self):
        """Test legacy string action format."""
        config = load_string("""
[match.filt1]
protocol = "ip"
parent = "root"
sendTo = "myclass"
action = "drop"
""")
        f = config.filters[0]
        assert len(f.actions) == 1
        assert f.actions[0].type == "drop"


class TestConfigErrors:
    """Test error handling in config loading."""

    def test_invalid_shaper_entry(self):
        with pytest.raises(ConfigError):
            load_string("""
[shaper]
root = "not a table"
""")


class TestFlowerFilterParsing:
    """Test [match.*.flower] sub-table parsing for flower filters."""

    def test_flower_subtable_basic(self):
        config = load_string("""
[match.filt1]
protocol = "ip"
parent = "root"
type = "flower"

[match.filt1.flower]
dst_ip = "10.0.0.1"
ip_proto = "tcp"
dst_port = "80"
""")
        f = config.filters[0]
        assert f.filter_type == "flower"
        assert f.match_params == {"dst_ip": "10.0.0.1", "ip_proto": "tcp", "dst_port": "80"}

    def test_flower_subtable_empty(self):
        config = load_string("""
[match.filt1]
type = "flower"
parent = "root"

[match.filt1.flower]
""")
        f = config.filters[0]
        assert f.filter_type == "flower"
        assert f.match_params == {}

    def test_flower_with_action_subtable(self):
        config = load_string("""
[match.classify]
dev = "eth0"
protocol = "ip"
parent = "root"
type = "flower"

[match.classify.flower]
dst_ip = "10.0.0.1"
ip_proto = "tcp"

[match.classify.action]
type = "skbedit"
mark = "42"
""")
        f = config.filters[0]
        assert f.filter_type == "flower"
        assert f.match_params == {"dst_ip": "10.0.0.1", "ip_proto": "tcp"}
        assert len(f.actions) == 1
        assert f.actions[0].type == "skbedit"
        assert f.actions[0].params["mark"] == "42"

    def test_flower_match_params_interpolation(self):
        """Variable interpolation should work in flower match_params."""
        config = load_string("""
[vars]
server = "10.0.0.5"

[match.filt1]
parent = "root"
type = "flower"

[match.filt1.flower]
dst_ip = "{server}"
""")
        f = config.filters[0]
        assert f.match_params == {"dst_ip": "10.0.0.5"}

    def test_flower_does_not_interfere_with_u32(self):
        """A u32 filter should not have match_params."""
        config = load_string("""
[match.filt1]
protocol = "ip"
parent = "root"
sendTo = "myclass"
ip = {dport = "80"}
""")
        f = config.filters[0]
        assert f.filter_type == "u32"
        assert f.ip_matches == {"dport": "80"}
        assert f.match_params == {}


class TestNewQdiscParsing:
    """Test parsing of new Tier 1 qdisc types."""

    def test_prio_qdisc(self):
        config = load_string("""
[shaper.sched]
dev = "eth0"
type = "prio"
bands = "4"
""")
        q = config.qdiscs[0]
        assert q.qdisc_type == "prio"
        assert q.params["bands"] == "4"

    def test_hfsc_qdisc(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
type = "hfsc"
default = "default_class"
""")
        q = config.qdiscs[0]
        assert q.qdisc_type == "hfsc"
        assert q.default == "default_class"

    def test_clsact_qdisc(self):
        config = load_string("""
[shaper.classify]
dev = "eth0"
type = "clsact"
handle = "ffff:"
""")
        q = config.qdiscs[0]
        assert q.qdisc_type == "clsact"
        assert q.handle == "ffff:"

    def test_hfsc_class(self):
        config = load_string("""
[class.realtime]
type = "hfsc"
parent = "root"
rt = "m1 100mbit d 50ms m2 10mbit"
ls = "m1 50mbit d 100ms m2 5mbit"
""")
        c = config.classes[0]
        assert c.class_type == "hfsc"
        assert c.params["rt"] == "m1 100mbit d 50ms m2 10mbit"
        assert c.params["ls"] == "m1 50mbit d 100ms m2 5mbit"


class TestPrioAutoGeneration:
    """Test auto-generation of prio band classes."""

    def test_auto_generates_3_bands_default(self):
        config = load_string("""
[shaper.sched]
dev = "eth0"
type = "prio"
""")
        assert len(config.classes) == 3
        assert config.classes[0].name == "sched:band0"
        assert config.classes[0].class_type == "prio"
        assert config.classes[0].parent == "sched"
        assert config.classes[1].name == "sched:band1"
        assert config.classes[2].name == "sched:band2"

    def test_auto_generates_custom_bands(self):
        config = load_string("""
[shaper.sched]
dev = "eth0"
type = "prio"
bands = "5"
""")
        assert len(config.classes) == 5
        for i in range(5):
            assert config.classes[i].name == f"sched:band{i}"
            assert config.classes[i].class_type == "prio"
            assert config.classes[i].parent == "sched"

    def test_no_auto_gen_if_user_defined_classes(self):
        """If user already declares classes parented to the prio qdisc, skip auto-gen."""
        config = load_string("""
[shaper.sched]
dev = "eth0"
type = "prio"
bands = "3"

[class.high]
type = "prio"
parent = "sched"

[class.med]
type = "prio"
parent = "sched"

[class.low]
type = "prio"
parent = "sched"
""")
        # Should have exactly the 3 user-defined classes, no auto-generated ones
        assert len(config.classes) == 3
        names = [c.name for c in config.classes]
        assert "high" in names
        assert "med" in names
        assert "low" in names

    def test_auto_gen_does_not_affect_other_qdiscs(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
type = "htb"
""")
        assert len(config.classes) == 0
