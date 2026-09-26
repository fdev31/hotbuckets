"""Automatic configuration for the default gateway interface.

``hotbuckets --auto`` detects the network interface used by the default
route, measures its real download/upload speeds with an online speed test,
and emits a single-interface shaping configuration modelled on
``examples/desktop-modern.toml``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# URL used by the built-in download test when speedtest-cli is unavailable.
# A large file from a CDN gives a stable throughput reading.
_DOWNLOAD_TEST_URL = "https://speed.cloudflare.com/__down?bytes=100000000"
_DOWNLOAD_TEST_BYTES = 100_000_000

# When only the download direction can be measured, assume this fraction
# of it for the upload direction.
_FALLBACK_UPLOAD_RATIO = 0.10

# Last-resort fallback when no real speed test can run: the negotiated link
# speed scaled by a typical end-to-end efficiency.
_LINK_EFFICIENCY_DOWN = 0.95
_LINK_EFFICIENCY_UP = 0.10
_DEFAULT_LINK_MBPS = 1000

# Speeds are reported in whole Mbit, never below this.
_MIN_MBPS = 1


class AutoConfigError(RuntimeError):
    """Raised when the automatic configuration cannot be produced."""


@dataclass
class SpeedResult:
    """Measured link speeds in Mbit/s."""

    download: int
    upload: int
    source: str


def _warn(message: str) -> None:
    print(f"hotbuckets: warning: {message}", file=sys.stderr)


def _bits_to_mbps(bits: int) -> int:
    return max(_MIN_MBPS, round(bits / 1_000_000))


def _read_link_mbps(nic: str) -> int:
    """Read the negotiated link speed from sysfs, with a sane fallback."""
    try:
        value = int(Path(f"/sys/class/net/{nic}/speed").read_text().strip())
        if value > 0:
            return value
    except (OSError, ValueError):
        pass
    return _DEFAULT_LINK_MBPS


def find_default_gateway_nic() -> str | None:
    """Return the interface name used by the default route, or ``None``.

    Reads ``/proc/net/route`` (the ``00000000`` destination), picking the
    lowest-metric default route. Falls back to parsing ``ip route``.
    """
    try:
        lines = Path("/proc/net/route").read_text().splitlines()
        best: tuple[int, str] | None = None  # (metric, iface)
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 8 or parts[1] != "00000000":
                continue
            metric = int(parts[6])
            if best is None or metric < best[0]:
                best = (metric, parts[0])
        if best is not None:
            return best[1]
    except (OSError, ValueError):
        pass

    try:
        proc = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in proc.stdout.splitlines():
        parts = line.split()
        for i, part in enumerate(parts):
            if part == "dev" and i + 1 < len(parts):
                return parts[i + 1]
    return None


def _speedtest_cli(timeout: int) -> SpeedResult | None:
    """Run ``speedtest-cli --json`` and parse the result.

    Returns ``None`` when the tool is missing or the run fails.
    """
    exe = shutil.which("speedtest-cli") or shutil.which("speedtest")
    if exe is None:
        return None
    try:
        proc = subprocess.run(
            [exe, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    start = proc.stdout.find("{")
    end = proc.stdout.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(proc.stdout[start : end + 1])
        download = int(data["download"])  # bit/s
        upload = int(data["upload"])  # bit/s
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if download <= 0 or upload <= 0:
        return None
    return SpeedResult(
        download=_bits_to_mbps(download),
        upload=_bits_to_mbps(upload),
        source="speedtest-cli",
    )


def _download_test(timeout: int) -> SpeedResult | None:
    """Measure download speed by fetching a large file.

    Upload cannot be measured this way, so it is estimated as a fraction of
    the download speed. Returns ``None`` on failure.
    """
    try:
        request = urllib.request.Request(
            _DOWNLOAD_TEST_URL,
            headers={"User-Agent": "hotbuckets/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            start = time.monotonic()
            total = 0
            while total < _DOWNLOAD_TEST_BYTES:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if time.monotonic() - start > timeout:
                    break
            elapsed = time.monotonic() - start
    except (OSError, urllib.error.URLError):
        return None
    if elapsed <= 0 or total < 1024 * 1024:
        return None
    download = max(_MIN_MBPS, round((total * 8) / elapsed / 1_000_000))
    upload = max(_MIN_MBPS, round(download * _FALLBACK_UPLOAD_RATIO))
    return SpeedResult(download=download, upload=upload, source="download-test")


def measure_speeds(
    nic: str,
    timeout: int,
    override: tuple[int, int] | None = None,
) -> SpeedResult:
    """Determine the real download/upload speeds for ``nic``.

    Tries, in order: an explicit override, ``speedtest-cli`` (real download
    and upload), then a built-in download test (real download, estimated
    upload). As an absolute last resort it estimates from the negotiated
    link speed, emitting a warning.
    """
    if override is not None:
        return SpeedResult(
            download=max(_MIN_MBPS, override[0]),
            upload=max(_MIN_MBPS, override[1]),
            source="override",
        )

    result = _speedtest_cli(timeout)
    if result is not None:
        return result
    _warn("speedtest-cli unavailable or failed; trying built-in download test")
    result = _download_test(timeout)
    if result is not None:
        _warn("upload speed estimated (10% of measured download)")
        return result
    link = _read_link_mbps(nic)
    _warn(
        f"no real speed test possible for '{nic}'; "
        f"estimating from link speed ({link}mbit)"
    )
    return SpeedResult(
        download=max(_MIN_MBPS, round(link * _LINK_EFFICIENCY_DOWN)),
        upload=max(_MIN_MBPS, round(link * _LINK_EFFICIENCY_UP)),
        source="link-speed",
    )


def generate_toml(nic: str, download: int, upload: int, source: str) -> str:
    """Render a single-interface shaping configuration as TOML."""
    return f"""# Auto-generated by `hotbuckets --auto`
# Interface: {nic} (default gateway)
# Speeds: {download}mbit down / {upload}mbit up ({source})

[devices.main]
dev = "{nic}"

[devices.ifb0]
dev = "ifb0"
virtual = true
type = "ifb"

[shaper.ingress]
dev = "main"
type = "ingress"
handle = "ffff:"

[match.redirect_to_ifb]
dev = "main"
parent = "ingress"
type = "matchall"

[match.redirect_to_ifb.action]
type = "mirred"
direction = "egress"
mode = "redirect"
target = "ifb0"

[shaper.download_shaping]
dev = "ifb0"
type = "cake"
bandwidth = "{download}mbit"
diffserv4 = true
wash = true

[shaper.upload_shaping]
dev = "main"
type = "cake"
bandwidth = "{upload}mbit"
diffserv4 = true
"""


def build_auto_config(
    timeout: int = 60,
    speed: tuple[int, int] | None = None,
) -> tuple[str, str]:
    """Detect the gateway NIC, measure real speeds, and build the TOML.

    Returns ``(toml_text, nic)``. Raises :class:`AutoConfigError` when the
    gateway interface or a real speed measurement cannot be determined.
    """
    nic = find_default_gateway_nic()
    if nic is None:
        raise AutoConfigError("could not determine the default gateway interface")
    speeds = measure_speeds(nic, timeout, override=speed)
    return generate_toml(nic, speeds.download, speeds.upload, speeds.source), nic
