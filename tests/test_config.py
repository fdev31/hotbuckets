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
