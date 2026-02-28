"""Tests for hotbuckets.script — script generation."""

from hotbuckets.config import load_string
from hotbuckets.resolver import resolve
from hotbuckets.script import generate, _resolve_speed


class TestResolveSpeed:
    """Test the speed alias and unit resolution helper."""

    def test_plain_value(self):
        config = load_string("")
        assert _resolve_speed("10mbit", config) == "10mbit"

    def test_speed_alias(self):
        config = load_string("""
[speeds]
full = "32mbit"
""")
        assert _resolve_speed("full", config) == "32mbit"

    def test_bare_int_with_unit(self):
        config = load_string('unit = "mbit"')
        assert _resolve_speed("10", config) == "10mbit"

    def test_bare_int_without_unit(self):
        config = load_string("")
        assert _resolve_speed("10", config) == "10"

    def test_non_integer_not_suffixed(self):
        config = load_string('unit = "mbit"')
        assert _resolve_speed("10kbps", config) == "10kbps"


class TestScriptStructure:
    """Test the overall structure of generated scripts."""

    def test_shebang(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert output.startswith("#!/bin/bash\n")

    def test_cleanup_section(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "# Cleanup:" in output
        assert "tc qdisc del dev eth0 root" in output

    def test_set_ex(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "set -ex" in output

    def test_rules_section(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "# Rules:" in output

    def test_custom_tc_path(self):
        config = load_string("""
tc = "/sbin/tc"

[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "/sbin/tc qdisc del dev eth0 root" in output
        assert "/sbin/tc qdisc add" in output

    def test_ends_with_newline(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert output.endswith("\n")


class TestScriptQdisc:
    """Test qdisc command generation."""

    def test_htb_root_qdisc(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "tc qdisc add dev eth0 root handle 1: htb # root" in output

    def test_tbf_qdisc(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
type = "tbf"
rate = "10mbit"
burst = "5000"
latency = "200ms"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "tc qdisc add dev eth0 root handle 1: tbf" in output
        assert "rate 10mbit" in output
        assert "burst 5000" in output
        assert "latency 200ms" in output

    def test_htb_default_class(self):
        config = load_string("""
[shaper.root]
dev = "eth0"
default = "c1"

[class.c1]
parent = "root"
rate = "10mbit"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "default 1" in output

    def test_ingress_qdisc_no_root_parent(self):
        config = load_string("""
[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"
""")
        result = resolve(config)
        output = generate(config, result)
        # Ingress qdisc should NOT have "root" in the command
        line = [l for l in output.splitlines() if "ingress" in l and "qdisc add" in l][0]
        assert "root" not in line.split("ingress")[0]


class TestScriptClass:
    """Test class command generation."""

    def test_htb_class(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"
ceil = "20mbit"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "tc class add dev eth0 parent 1: classid 1:1 htb rate 10mbit ceil 20mbit # c1" in output

    def test_class_speed_alias(self):
        config = load_string("""
[speeds]
full = "32mbit"

[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "full"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "rate 32mbit" in output

    def test_class_burst(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"
burst = "15k"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "burst 15k rate 10mbit" in output


class TestScriptFilter:
    """Test filter command generation."""

    def test_u32_filter(self):
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
        output = generate(config, result)
        assert "tc filter add dev eth0 protocol ip parent 1: u32 match ip dport 80 0xffff flowid 1:1 # f1" in output

    def test_fw_filter(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"

[match.f1]
protocol = "ip"
type = "fw"
parent = "root"
sendTo = "c1"
handle = "42"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "fw handle 42 flowid 1:1" in output

    def test_filter_prio(self):
        config = load_string("""
[shaper.root]
dev = "eth0"

[class.c1]
parent = "root"
rate = "10mbit"

[match.f1]
protocol = "ip"
prio = "2"
parent = "root"
sendTo = "c1"
ip = {sport = "80"}
""")
        result = resolve(config)
        output = generate(config, result)
        assert "prio 2" in output

    def test_matchall_with_mirred_action(self):
        config = load_string("""
[devices.ifb0]
dev = "ifb0"
virtual = true
type = "ifb"

[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"

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
        result = resolve(config)
        output = generate(config, result)
        assert "matchall action mirred egress redirect dev ifb0" in output


class TestScriptVirtualDevices:
    """Test virtual device setup in generated scripts."""

    def test_ifb_setup_commands(self):
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
        output = generate(config, result)
        assert "modprobe ifb numifbs=1" in output
        assert "ip link set dev ifb0 up" in output

    def test_ingress_cleanup(self):
        config = load_string("""
[shaper.ingress]
dev = "eth0"
type = "ingress"
handle = "ffff:"
""")
        result = resolve(config)
        output = generate(config, result)
        assert "tc qdisc del dev eth0 ingress" in output
