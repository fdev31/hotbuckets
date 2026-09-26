"""Tests for automatic configuration generation (``--auto``)."""

from pathlib import Path

from hotbuckets import auto
from hotbuckets.cli import _parse_speed
from hotbuckets.config import load_string
from hotbuckets.resolver import resolve
from hotbuckets.script import generate


class TestGenerateToml:
    def test_roundtrip_loads_and_resolves(self):
        toml = auto.generate_toml("enp12s0", 950, 100, "speedtest-cli")
        config = load_string(toml)
        result = resolve(config)
        output = generate(config, result)
        assert "dev enp12s0" in output
        assert "cake bandwidth 950mbit" in output
        assert "cake bandwidth 100mbit" in output
        assert "mirred egress redirect dev ifb0" in output
        assert "modprobe ifb numifbs=1" in output

    def test_contains_expected_sections(self):
        toml = auto.generate_toml("eth0", 500, 50, "override")
        assert '[devices.main]' in toml
        assert 'dev = "eth0"' in toml
        assert '[devices.ifb0]' in toml
        assert 'bandwidth = "500mbit"' in toml
        assert 'bandwidth = "50mbit"' in toml


class TestMeasureSpeeds:
    def test_override(self):
        result = auto.measure_speeds("eth0", 60, override=(950, 100))
        assert result.download == 950
        assert result.upload == 100
        assert result.source == "override"

    def test_override_clamps_minimum(self):
        result = auto.measure_speeds("eth0", 60, override=(0, 0))
        assert result.download == 1
        assert result.upload == 1


class TestParseSpeed:
    def test_valid(self):
        assert _parse_speed("950/100") == (950, 100)

    def test_invalid(self):
        assert _parse_speed("950") is None
        assert _parse_speed("abc/100") is None
        assert _parse_speed("1/2/3") is None


class TestFindGateway:
    def test_returns_string_or_none(self):
        result = auto.find_default_gateway_nic()
        assert result is None or isinstance(result, str)

    def test_parsing_picks_lowest_metric(self, monkeypatch):
        fake = (
            "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\n"
            "eth8\t00000000\tFE01A8C0\t0003\t0\t0\t200\t00000000\n"
            "eth9\t00000000\tFE01A8C0\t0003\t0\t0\t100\t00000000\n"
        )
        real_read_text = Path.read_text

        def fake_read_text(self, *args, **kwargs):
            if str(self) == "/proc/net/route":
                return fake
            return real_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fake_read_text)
        assert auto.find_default_gateway_nic() == "eth9"
