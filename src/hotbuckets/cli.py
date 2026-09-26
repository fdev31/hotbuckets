"""CLI entry point for hotbuckets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hotbuckets import __version__


def _print_list() -> None:
    """Print all available plugin types with descriptions and parameters."""
    # Ensure plugins are loaded
    import hotbuckets.plugins  # noqa: F401
    from hotbuckets.registry import Registry

    info = Registry.list_all()

    sections = [
        ("Qdiscs", info["qdiscs"]),
        ("Filters", info["filters"]),
        ("Actions", info["actions"]),
    ]

    for section_name, entries in sections:
        print(f"\n{section_name}:")
        print("  " + "-" * 70)
        for entry in entries:
            name = entry["name"]
            desc = entry["description"] or "(no description)"
            print(f"  {name:<12} {desc}")
            params = entry["params"]
            if params:
                for pname, pinfo in params.items():
                    req = " (required)" if pinfo["required"] else ""
                    ex = f"  e.g. {pinfo['example']}" if pinfo["example"] else ""
                    print(f"    {pname:<18} {pinfo['description']}{req}{ex}")
            print()


def _parse_speed(value: str) -> tuple[int, int] | None:
    """Parse a ``DL/UL`` Mbit override, or ``None`` if malformed."""
    try:
        down, up = value.split("/")
        return int(down), int(up)
    except (ValueError, AttributeError):
        return None


def _run_auto(args: argparse.Namespace) -> None:
    """Detect the gateway interface, measure speeds, and emit the config."""
    from hotbuckets import auto

    speed = None
    if args.speed is not None:
        speed = _parse_speed(args.speed)
        if speed is None:
            print("Error: --speed must be DL/UL in Mbit, e.g. 950/100", file=sys.stderr)
            sys.exit(1)

    try:
        toml_text, nic = auto.build_auto_config(timeout=args.timeout, speed=speed)
    except auto.AutoConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        args.output.write_text(toml_text)
        print(f"Generated config for '{nic}' -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(toml_text)


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the htb command."""
    parser = argparse.ArgumentParser(
        prog="htb",
        description="Generate tc (traffic control) rules from a TOML configuration file.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--list",
        default=False,
        help="list all available qdisc, filter, and action types with descriptions",
        action="store_true",
    )
    parser.add_argument(
        "--show",
        default=False,
        help="display a graphical representation using graphviz",
        action="store_true",
    )
    parser.add_argument(
        "--check",
        default=False,
        help="validate the configuration without generating output",
        action="store_true",
    )
    parser.add_argument(
        "--auto",
        default=False,
        help="auto-generate a config for the default gateway interface (measures real speeds)",
        action="store_true",
    )
    parser.add_argument(
        "--speed",
        help="override measured speeds in Mbit, e.g. 950/100 (with --auto)",
        metavar="DL/UL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="speed test timeout in seconds (with --auto, default 60)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="write output to a file instead of stdout",
        type=Path,
    )
    parser.add_argument(
        "config",
        help="TOML file containing all the rules",
        type=Path,
        metavar="CONFIG",
        nargs="?",
    )

    args = parser.parse_args(argv)

    # --list doesn't require a config file
    if args.list:
        _print_list()
        return

    # --auto generates a config for the default gateway interface
    if args.auto:
        _run_auto(args)
        return

    # All other modes require a config file
    if not args.config:
        parser.error("CONFIG is required (unless using --list or --auto)")

    # Import here to avoid circular imports and to ensure plugins are loaded
    from hotbuckets.config import load_file
    from hotbuckets.errors import HotbucketsError
    from hotbuckets.resolver import resolve
    from hotbuckets.script import generate

    # Ensure plugins are loaded
    import hotbuckets.plugins  # noqa: F401

    try:
        config = load_file(args.config)
        result = resolve(config)

        if args.check:
            print(f"Configuration '{args.config}' is valid.")
            return

        output = generate(config, result)

        if args.output:
            args.output.write_text(output)
        else:
            sys.stdout.write(output)

        if args.show:
            try:
                from hotbuckets.graph import render_graph

                render_graph(config, result)
            except ImportError:
                print(
                    "graphviz package not installed. Install with: pip install hotbuckets[viz]",
                    file=sys.stderr,
                )

    except HotbucketsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.config}", file=sys.stderr)
        sys.exit(1)
