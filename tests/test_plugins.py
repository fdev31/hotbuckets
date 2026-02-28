"""Tests for individual plugin validate() and generate() methods."""

from hotbuckets.registry import Registry


# ── Qdisc plugins ────────────────────────────────────────────────────────────


class TestHtbPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("htb")
        assert plugin.generate({}) == []

    def test_generate_with_rate(self):
        plugin = Registry.get_qdisc("htb")
        result = plugin.generate({"rate": "10mbit"})
        assert result == ["rate", "10mbit"]

    def test_generate_with_all_params(self):
        plugin = Registry.get_qdisc("htb")
        result = plugin.generate({"latency": "200ms", "burst": "5000", "rate": "10mbit"})
        assert result == ["latency", "200ms", "burst", "5000", "rate", "10mbit"]

    def test_validate_always_passes(self):
        plugin = Registry.get_qdisc("htb")
        assert plugin.validate({}) == []


class TestTbfPlugin:
    def test_generate_with_rate(self):
        plugin = Registry.get_qdisc("tbf")
        result = plugin.generate({"rate": "10mbit", "burst": "5000", "latency": "200ms"})
        assert result == ["latency", "200ms", "burst", "5000", "rate", "10mbit"]

    def test_validate_missing_rate(self):
        plugin = Registry.get_qdisc("tbf")
        errors = plugin.validate({})
        assert len(errors) == 1
        assert "rate" in errors[0].lower()

    def test_validate_with_rate(self):
        plugin = Registry.get_qdisc("tbf")
        assert plugin.validate({"rate": "10mbit"}) == []


class TestSfqPlugin:
    def test_generate_default_perturb(self):
        plugin = Registry.get_qdisc("sfq")
        result = plugin.generate({})
        assert result == ["perturb", "10"]

    def test_generate_explicit_perturb(self):
        plugin = Registry.get_qdisc("sfq")
        result = plugin.generate({"perturb": "15"})
        assert result == ["perturb", "15"]

    def test_generate_with_quantum(self):
        plugin = Registry.get_qdisc("sfq")
        result = plugin.generate({"quantum": "1500", "perturb": "10"})
        assert result == ["quantum", "1500", "perturb", "10"]


class TestNetemPlugin:
    def test_generate_delay(self):
        plugin = Registry.get_qdisc("netem")
        result = plugin.generate({"delay": "100ms"})
        assert result == ["delay", "100ms"]

    def test_generate_multiple_params(self):
        plugin = Registry.get_qdisc("netem")
        result = plugin.generate(
            {
                "delay": "60ms 20ms",
                "loss": "1% 1%",
                "corrupt": "0.1%",
                "reorder": "50% 50%",
            }
        )
        assert "delay" in result
        assert "loss" in result
        assert "corrupt" in result
        assert "reorder" in result

    def test_generate_empty(self):
        plugin = Registry.get_qdisc("netem")
        assert plugin.generate({}) == []


class TestCakePlugin:
    def test_generate_bandwidth(self):
        plugin = Registry.get_qdisc("cake")
        result = plugin.generate({"bandwidth": "100mbit"})
        assert result == ["bandwidth", "100mbit"]

    def test_generate_boolean_flags(self):
        plugin = Registry.get_qdisc("cake")
        result = plugin.generate({"bandwidth": "100mbit", "diffserv4": "true"})
        assert "bandwidth" in result
        assert "100mbit" in result
        assert "diffserv4" in result

    def test_boolean_false_not_emitted(self):
        plugin = Registry.get_qdisc("cake")
        result = plugin.generate({"diffserv4": "false"})
        assert "diffserv4" not in result

    def test_generate_empty(self):
        plugin = Registry.get_qdisc("cake")
        assert plugin.generate({}) == []


class TestIngressPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("ingress")
        assert plugin.generate({}) == []

    def test_generate_ignores_params(self):
        plugin = Registry.get_qdisc("ingress")
        assert plugin.generate({"foo": "bar"}) == []


class TestFqCodelPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("fq_codel")
        assert plugin.generate({}) == []

    def test_generate_limit_and_flows(self):
        plugin = Registry.get_qdisc("fq_codel")
        result = plugin.generate({"limit": "1000", "flows": "1024"})
        assert result == ["limit", "1000", "flows", "1024"]


# ── Filter plugins ───────────────────────────────────────────────────────────


class TestU32FilterPlugin:
    def test_generate_dport(self):
        plugin = Registry.get_filter("u32")
        result = plugin.generate({"ip_matches": {"dport": "80"}, "hosts": {}})
        assert result == ["match", "ip", "dport", "80", "0xffff"]

    def test_generate_sport(self):
        plugin = Registry.get_filter("u32")
        result = plugin.generate({"ip_matches": {"sport": "443"}, "hosts": {}})
        assert result == ["match", "ip", "sport", "443", "0xffff"]

    def test_generate_dst(self):
        """Non-port matches don't get the 0xffff mask."""
        plugin = Registry.get_filter("u32")
        result = plugin.generate({"ip_matches": {"dst": "192.168.1.1"}, "hosts": {}})
        assert result == ["match", "ip", "dst", "192.168.1.1"]

    def test_generate_host_alias(self):
        plugin = Registry.get_filter("u32")
        result = plugin.generate(
            {
                "ip_matches": {"dst": "myhost"},
                "hosts": {"myhost": "10.0.0.1"},
            }
        )
        assert result == ["match", "ip", "dst", "10.0.0.1"]

    def test_generate_empty(self):
        plugin = Registry.get_filter("u32")
        assert plugin.generate({"ip_matches": {}, "hosts": {}}) == []

    def test_generate_multiple_matches(self):
        plugin = Registry.get_filter("u32")
        result = plugin.generate(
            {
                "ip_matches": {"dst": "10.0.0.1", "sport": "80"},
                "hosts": {},
            }
        )
        # Should have two match clauses
        assert result.count("match") == 2


class TestFwFilterPlugin:
    def test_generate_with_handle(self):
        plugin = Registry.get_filter("fw")
        result = plugin.generate({"handle": "42"})
        assert result == ["handle", "42"]

    def test_generate_no_handle(self):
        plugin = Registry.get_filter("fw")
        assert plugin.generate({}) == []


class TestMatchallFilterPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_filter("matchall")
        assert plugin.generate({}) == []


# ── Action plugins ───────────────────────────────────────────────────────────


class TestMirredActionPlugin:
    def test_generate_redirect(self):
        plugin = Registry.get_action("mirred")
        result = plugin.generate(
            {
                "direction": "egress",
                "mode": "redirect",
                "target": "ifb0",
            }
        )
        assert result == ["action", "mirred", "egress", "redirect", "dev", "ifb0"]

    def test_generate_mirror(self):
        plugin = Registry.get_action("mirred")
        result = plugin.generate(
            {
                "direction": "egress",
                "mode": "mirror",
                "target": "eth1",
            }
        )
        assert result == ["action", "mirred", "egress", "mirror", "dev", "eth1"]

    def test_generate_defaults(self):
        """Default direction=egress, mode=redirect."""
        plugin = Registry.get_action("mirred")
        result = plugin.generate({"target": "ifb0"})
        assert result == ["action", "mirred", "egress", "redirect", "dev", "ifb0"]

    def test_generate_with_device_alias(self):
        plugin = Registry.get_action("mirred")
        result = plugin.generate(
            {
                "target": "my_ifb",
                "_devices": {"my_ifb": "ifb0"},
            }
        )
        assert result == ["action", "mirred", "egress", "redirect", "dev", "ifb0"]

    def test_validate_missing_target(self):
        plugin = Registry.get_action("mirred")
        errors = plugin.validate({})
        assert len(errors) == 1
        assert "target" in errors[0].lower()


class TestPoliceActionPlugin:
    def test_generate_rate(self):
        plugin = Registry.get_action("police")
        result = plugin.generate({"rate": "1mbit", "burst": "10k"})
        assert result == ["action", "police", "rate", "1mbit", "burst", "10k"]

    def test_generate_empty(self):
        plugin = Registry.get_action("police")
        assert plugin.generate({}) == ["action", "police"]


class TestDropActionPlugin:
    def test_generate(self):
        plugin = Registry.get_action("drop")
        assert plugin.generate({}) == ["action", "drop"]

    def test_generate_ignores_params(self):
        plugin = Registry.get_action("drop")
        assert plugin.generate({"foo": "bar"}) == ["action", "drop"]
