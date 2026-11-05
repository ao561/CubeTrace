"""Command-line entry point: `cubetrace`."""

from __future__ import annotations

import argparse
import json
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
    analyze.add_argument(
        "--move-times",
        type=Path,
        help="JSON file: [[start_s, end_s], ...], one pair per solution move",
    )
    analyze.add_argument("--out", type=Path, required=True, help="output directory")
    analyze.set_defaults(run=_run_analyze)

    cases = sub.add_parser("cases", help="write a page showing every OLL/PLL case for review")
    cases.add_argument("--out", type=Path, required=True, help="output directory")
    cases.set_defaults(run=_run_cases)

    ev = sub.add_parser("eval", help="evaluate vision and decoding on a dataset split")
    ev.add_argument("--split", choices=["train", "val", "test"], default="val")
    ev.set_defaults(run=_not_implemented(5))

    return parser


def _not_implemented(phase: int):
    def run(args: argparse.Namespace) -> int:
        print(f"cubetrace {args.command}: not implemented yet (Phase {phase})", file=sys.stderr)
        return 2

    return run


def _run_analyze(args: argparse.Namespace) -> int:
    from cubetrace.analysis import analyze
    from cubetrace.report import write_report

    move_times = json.loads(args.move_times.read_text()) if args.move_times else None
    try:
        result = analyze(args.scramble, args.solution, time=args.time, move_times=move_times)
    except ValueError as e:  # bad notation, unsolvable input, bad move times
        print(f"cubetrace analyze: {e}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    report = write_report(result, args.out)

    t = result["totals"]
    rotations = "rotation" if t["rotations"] == 1 else "rotations"
    parts = [f"{t['turns']} turns", f"{t['rotations']} {rotations}"]
    if t["time_s"]:
        parts += [f"{t['time_s']:.2f} s", f"{t['tps']:.2f} TPS"]
    parts.append(f"score {result['score']['value']:.1f}")
    print(", ".join(parts))
    for step in result["steps"]:
        what = step["case"] or ("-".join(step["slot"]) if step["slot"] else "")
        label = f" ({step['label']})" if step["label"] else ""
        print(f"  {step['name']:<5} {step['turns']:>2}  {what}{label}")
    print(f"Wrote {args.out / 'analysis.json'} and {report}")
    return 0


def _run_cases(args: argparse.Namespace) -> int:
    from cubetrace.report import write_cases_page

    path = write_cases_page(args.out)
    print(f"Wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    return args.run(args)
