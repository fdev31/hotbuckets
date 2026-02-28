"""CLI entry point for hotbuckets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hotbuckets import __version__


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
    )

    args = parser.parse_args(argv)

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
