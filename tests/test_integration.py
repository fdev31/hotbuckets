"""End-to-end integration tests — load TOML fixtures and compare to expected output."""

from pathlib import Path

import pytest

from hotbuckets.config import load_file
from hotbuckets.resolver import resolve
from hotbuckets.script import generate

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Discover all fixtures that have a .toml + .expected pair
FIXTURE_NAMES = sorted(p.stem for p in FIXTURES_DIR.glob("*.toml") if (FIXTURES_DIR / f"{p.stem}.expected").exists())


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_fixture_output_matches_expected(fixture_name: str):
    """Load a TOML fixture, generate output, and compare line-by-line to .expected."""
    toml_path = FIXTURES_DIR / f"{fixture_name}.toml"
    expected_path = FIXTURES_DIR / f"{fixture_name}.expected"

    config = load_file(toml_path)
    result = resolve(config)
    output = generate(config, result)

    # Strip the shebang and comment-only lines for comparison,
    # matching the original regression test approach.
    # Actually, the .expected files include non-comment lines only (cleanup, set -ex, rules).
    # But our expected files are the full output without shebang.
    # Let's compare the full output stripped of shebang against expected.
    expected_text = expected_path.read_text()

    # The expected files don't have #!/bin/bash — strip it from output
    output_lines = output.splitlines()
    expected_lines = expected_text.strip().splitlines()

    # Filter out shebang and section-comment lines from output
    # (# Cleanup:, # Device setup:, # Rules:) to match expected format
    filtered_output = []
    for line in output_lines:
        if line == "#!/bin/bash":
            continue
        if line in ("# Cleanup:", "# Rules:", "# Device setup:"):
            continue
        filtered_output.append(line)

    assert filtered_output == expected_lines, (
        f"Output mismatch for {fixture_name}:\n"
        f"--- expected ---\n{chr(10).join(expected_lines)}\n"
        f"--- got ---\n{chr(10).join(filtered_output)}"
    )


class TestEndToEndSpecific:
    """Specific end-to-end tests for known behaviors."""

    def test_basic_single_tbf(self):
        """basic.toml: single TBF qdisc, simplest possible config."""
        config = load_file(FIXTURES_DIR / "basic.toml")
        result = resolve(config)
        output = generate(config, result)
        assert "tbf" in output
        assert "wlo1" in output

    def test_desktop_htb_hierarchy(self):
        """desktop.toml: HTB with classes, SFQ leaf qdiscs, u32 filters."""
        config = load_file(FIXTURES_DIR / "desktop.toml")
        result = resolve(config)
        output = generate(config, result)
        assert "htb" in output
        assert "sfq" in output
        assert "u32" in output
        assert "flowid 1:3" in output

    def test_hqlq_filter_ordering(self):
        """hqlq.toml: fw filter (handle=42) sorts before u32 filters."""
        config = load_file(FIXTURES_DIR / "hqlq.toml")
        result = resolve(config)
        output = generate(config, result)
        lines = output.splitlines()

        filter_lines = [l for l in lines if "filter add" in l]
        assert len(filter_lines) == 3

        # filt3 (fw handle=42) should come first
        assert "filt3" in filter_lines[0]
        # Then filt1 and filt2 (u32)
        assert "filt1" in filter_lines[1]
        assert "filt2" in filter_lines[2]

    def test_ifb_cake_setup(self):
        """ifb_cake.toml: IFB device setup, ingress, mirred redirect, CAKE."""
        config = load_file(FIXTURES_DIR / "ifb_cake.toml")
        result = resolve(config)
        output = generate(config, result)

        assert "modprobe ifb numifbs=1" in output
        assert "ip link set dev ifb0 up" in output
        assert "cake" in output
        assert "mirred egress redirect dev ifb0" in output

    def test_gate_speed_alias_resolution(self):
        """gate.toml: speed aliases like 'full' resolve to actual values."""
        config = load_file(FIXTURES_DIR / "gate.toml")
        result = resolve(config)
        output = generate(config, result)
        assert "30mbit" in output  # 'full' -> '30mbit'
        assert "25mbit" in output  # 'almost' -> '25mbit'
