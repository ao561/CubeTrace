"""Command-line entry point: `cubetrace`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cubetrace import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cubetrace",
        description="Analyse 3x3 Rubik's cube speedsolves (CFOP).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    analyze = sub.add_parser("analyze", help="analyse a typed solve (scramble + solution)")
    analyze.add_argument("--scramble", required=True, help="scramble in WCA notation")
    analyze.add_argument("--solution", required=True, help="solution in WCA/SiGN notation")
    analyze.add_argument("--time", type=float, help="solve time in seconds")
    analyze.add_argument("--out", type=Path, required=True, help="output directory")
    analyze.set_defaults(phase=2)

    ev = sub.add_parser("eval", help="evaluate vision and decoding on a dataset split")
    ev.add_argument("--split", choices=["train", "val", "test"], default="val")
    ev.set_defaults(phase=5)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    print(f"cubetrace {args.command}: not implemented yet (Phase {args.phase})", file=sys.stderr)
    return 2
