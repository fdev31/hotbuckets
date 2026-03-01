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


# ── New Tier 1 qdisc plugins ─────────────────────────────────────────────────


class TestPrioPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("prio")
        assert plugin.generate({}) == []

    def test_generate_with_bands(self):
        plugin = Registry.get_qdisc("prio")
        result = plugin.generate({"bands": "3"})
        assert result == ["bands", "3"]

    def test_generate_with_priomap(self):
        plugin = Registry.get_qdisc("prio")
        result = plugin.generate({"priomap": "1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1"})
        assert result == ["priomap", "1", "2", "2", "2", "1", "2", "0", "0", "1", "1", "1", "1", "1", "1", "1", "1"]

    def test_generate_with_bands_and_priomap(self):
        plugin = Registry.get_qdisc("prio")
        result = plugin.generate({"bands": "4", "priomap": "1 2 3 3 1 2 0 0 1 1 1 1 1 1 1 1"})
        assert result == [
            "bands",
            "4",
            "priomap",
            "1",
            "2",
            "3",
            "3",
            "1",
            "2",
            "0",
            "0",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
            "1",
        ]

    def test_validate_ok(self):
        plugin = Registry.get_qdisc("prio")
        assert plugin.validate({}) == []
        assert plugin.validate({"bands": "3"}) == []

    def test_validate_bands_too_low(self):
        plugin = Registry.get_qdisc("prio")
        errors = plugin.validate({"bands": "1"})
        assert len(errors) == 1
        assert "2-16" in errors[0]

    def test_validate_bands_too_high(self):
        plugin = Registry.get_qdisc("prio")
        errors = plugin.validate({"bands": "17"})
        assert len(errors) == 1
        assert "2-16" in errors[0]

    def test_validate_bands_not_integer(self):
        plugin = Registry.get_qdisc("prio")
        errors = plugin.validate({"bands": "abc"})
        assert len(errors) == 1
        assert "integer" in errors[0]

    def test_validate_priomap_wrong_count(self):
        plugin = Registry.get_qdisc("prio")
        errors = plugin.validate({"priomap": "1 2 3"})
        assert len(errors) == 1
        assert "16" in errors[0]


class TestHfscPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("hfsc")
        assert plugin.generate({}) == []

    def test_generate_ignores_params(self):
        """default is handled by script.py, not the plugin."""
        plugin = Registry.get_qdisc("hfsc")
        assert plugin.generate({"default": "1"}) == []

    def test_validate_always_passes(self):
        plugin = Registry.get_qdisc("hfsc")
        assert plugin.validate({}) == []


class TestClsactPlugin:
    def test_generate_empty(self):
        plugin = Registry.get_qdisc("clsact")
        assert plugin.generate({}) == []

    def test_generate_ignores_params(self):
        plugin = Registry.get_qdisc("clsact")
        assert plugin.generate({"foo": "bar"}) == []

    def test_validate_always_passes(self):
        plugin = Registry.get_qdisc("clsact")
        assert plugin.validate({}) == []


# ── New Tier 1 filter plugins ────────────────────────────────────────────────


class TestFlowerFilterPlugin:
    def test_generate_single_match(self):
        plugin = Registry.get_filter("flower")
        result = plugin.generate({"match_params": {"dst_ip": "10.0.0.1"}, "hosts": {}})
        assert result == ["dst_ip", "10.0.0.1"]

    def test_generate_multiple_matches(self):
        plugin = Registry.get_filter("flower")
        result = plugin.generate(
            {
                "match_params": {"dst_ip": "10.0.0.1", "ip_proto": "tcp", "dst_port": "80"},
                "hosts": {},
            }
        )
        # Stable order: dst_ip, ip_proto, dst_port
        assert result == ["dst_ip", "10.0.0.1", "ip_proto", "tcp", "dst_port", "80"]

    def test_generate_host_alias_src_ip(self):
        plugin = Registry.get_filter("flower")
        result = plugin.generate(
            {
                "match_params": {"src_ip": "myhost"},
                "hosts": {"myhost": "192.168.1.10"},
            }
        )
        assert result == ["src_ip", "192.168.1.10"]

    def test_generate_host_alias_dst_ip(self):
        plugin = Registry.get_filter("flower")
        result = plugin.generate(
            {
                "match_params": {"dst_ip": "server"},
                "hosts": {"server": "10.0.0.5"},
            }
        )
        assert result == ["dst_ip", "10.0.0.5"]

    def test_generate_no_alias_for_non_ip(self):
        """Host alias resolution only applies to src_ip and dst_ip."""
        plugin = Registry.get_filter("flower")
        result = plugin.generate(
            {
                "match_params": {"dst_port": "myhost"},
                "hosts": {"myhost": "192.168.1.10"},
            }
        )
        assert result == ["dst_port", "myhost"]

    def test_generate_all_fields(self):
        plugin = Registry.get_filter("flower")
        result = plugin.generate(
            {
                "match_params": {
                    "src_ip": "1.2.3.4",
                    "dst_ip": "5.6.7.8",
                    "ip_proto": "udp",
                    "src_port": "1234",
                    "dst_port": "5678",
                    "src_mac": "aa:bb:cc:dd:ee:ff",
                    "dst_mac": "11:22:33:44:55:66",
                    "vlan_id": "100",
                    "vlan_prio": "3",
                    "indev": "eth0",
                },
                "hosts": {},
            }
        )
        expected = [
            "src_ip",
            "1.2.3.4",
            "dst_ip",
            "5.6.7.8",
            "ip_proto",
            "udp",
            "src_port",
            "1234",
            "dst_port",
            "5678",
            "src_mac",
            "aa:bb:cc:dd:ee:ff",
            "dst_mac",
            "11:22:33:44:55:66",
            "vlan_id",
            "100",
            "vlan_prio",
            "3",
            "indev",
            "eth0",
        ]
        assert result == expected

    def test_generate_empty(self):
        plugin = Registry.get_filter("flower")
        assert plugin.generate({"match_params": {}, "hosts": {}}) == []

    def test_validate_empty_match_params(self):
        plugin = Registry.get_filter("flower")
        errors = plugin.validate({"match_params": {}})
        assert len(errors) == 1
        assert "at least one" in errors[0]

    def test_validate_with_match_params(self):
        plugin = Registry.get_filter("flower")
        assert plugin.validate({"match_params": {"dst_ip": "10.0.0.1"}}) == []


# ── New Tier 1 action plugins ────────────────────────────────────────────────


class TestSkbeditActionPlugin:
    def test_generate_mark(self):
        plugin = Registry.get_action("skbedit")
        result = plugin.generate({"mark": "42"})
        assert result == ["action", "skbedit", "mark", "42"]

    def test_generate_priority(self):
        plugin = Registry.get_action("skbedit")
        result = plugin.generate({"priority": "7"})
        assert result == ["action", "skbedit", "priority", "7"]

    def test_generate_queue_mapping(self):
        plugin = Registry.get_action("skbedit")
        result = plugin.generate({"queue_mapping": "3"})
        assert result == ["action", "skbedit", "queue_mapping", "3"]

    def test_generate_all_params(self):
        plugin = Registry.get_action("skbedit")
        result = plugin.generate({"mark": "10", "priority": "5", "queue_mapping": "2"})
        assert result == ["action", "skbedit", "mark", "10", "priority", "5", "queue_mapping", "2"]

    def test_validate_missing_all(self):
        plugin = Registry.get_action("skbedit")
        errors = plugin.validate({})
        assert len(errors) == 1
        assert "at least one" in errors[0]

    def test_validate_with_mark(self):
        plugin = Registry.get_action("skbedit")
        assert plugin.validate({"mark": "42"}) == []

    def test_validate_with_priority(self):
        plugin = Registry.get_action("skbedit")
        assert plugin.validate({"priority": "7"}) == []

    def test_validate_with_queue_mapping(self):
        plugin = Registry.get_action("skbedit")
        assert plugin.validate({"queue_mapping": "3"}) == []
