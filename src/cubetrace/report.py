"""Static HTML pages: the solve report, and a review page of every OLL/PLL case."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import numpy as np

from cubetrace.cases import OLL_ALGS, PLL_ALGS, POST_AUF_RELABELS
from cubetrace.cube import _NORM, _POS, CORNERS, EDGES, FACE_OF, SOLVED, Color, apply, relative
from cubetrace.notation import invert, parse

CUBING_VERSION = "0.66.1"
CUBING_JS = f"https://cdn.jsdelivr.net/npm/cubing@{CUBING_VERSION}/dist/lib/cubing/twisty/index.js"

COLOUR_HEX = {
    "white": "#f4f4f5",
    "yellow": "#facc15",
    "green": "#16a34a",
    "blue": "#2563eb",
    "red": "#dc2626",
    "orange": "#f97316",
}
STAGE_TITLES = {
    "cross": "Cross",
    "f2l1": "F2L 1",
    "f2l2": "F2L 2",
    "f2l3": "F2L 3",
    "f2l4": "F2L 4",
    "oll": "OLL",
    "pll": "PLL",
}
PART_TITLES = {"tps": "TPS", "turns": "Turns", "rotations": "Rotations", "pauses": "Pauses"}

CSS = """
:root {
  --bg: #f6f5f3; --card: #ffffff; --fg: #1c1b1a; --muted: #6f6a64; --border: #e4e1dc;
  --accent: #2563eb; --bar: #d9d5cf; --code-bg: #f1efeb;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121110; --card: #1c1b19; --fg: #f1efec; --muted: #a29d96; --border: #2e2c29;
    --accent: #7aa7ff; --bar: #3a3733; --code-bg: #262421;
  }
}
:root[data-theme="dark"] {
  --bg: #121110; --card: #1c1b19; --fg: #f1efec; --muted: #a29d96; --border: #2e2c29;
  --accent: #7aa7ff; --bar: #3a3733; --code-bg: #262421;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 16px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted);
     margin: 0 0 12px; font-weight: 600; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px;
        padding: 16px; margin-bottom: 16px; }
.layout { display: grid; gap: 16px; grid-template-columns: minmax(0, 1fr); }
@media (min-width: 900px) { .layout { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); } }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; }
.tile .label { color: var(--muted); font-size: 13px; }
.tile .value { font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; }
.tile.score .value { color: var(--accent); }
code, .moves { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13.5px; }
code { background: var(--code-bg); padding: 2px 6px; border-radius: 6px; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px 8px; border-top: 1px solid var(--border);
         vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 13px; border-top: none; }
td.num { font-variant-numeric: tabular-nums; text-align: right; }
.chip { display: inline-block; width: 12px; height: 12px; border-radius: 3px;
        border: 1px solid rgba(0,0,0,.25); vertical-align: -1px; margin-right: 3px; }
.badge { display: inline-block; font-size: 12px; padding: 0 7px; border-radius: 999px;
         border: 1px solid var(--border); color: var(--muted); margin-left: 6px; }
.bar { height: 8px; background: var(--bar); border-radius: 4px; overflow: hidden;
       min-width: 80px; }
.bar > span { display: block; height: 100%; background: var(--accent); }
dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 6px 16px; margin: 0; }
dt { color: var(--muted); }
dd { margin: 0; overflow-wrap: anywhere; }
twisty-player { width: 100%; height: 340px; }
twisty-alg-viewer { display: block; margin-top: 12px; font-size: 13.5px; }
.cases { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
figure { margin: 0; text-align: center; }
figure svg { width: 110px; height: 110px; }
figcaption strong { display: block; }
figcaption code { display: inline-block; margin-top: 4px; font-size: 12px; }
.note { color: var(--muted); max-width: 70ch; }
a { color: var(--accent); }
"""


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _page(title: str, body: str, *, twisty: bool = False) -> str:
    script = f'<script type="module" src="{_e(CUBING_JS)}"></script>' if twisty else ""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_e(title)}</title>\n<style>{CSS}</style>\n{script}\n</head>\n"
        f"<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n"
    )


def _chip(colour: str) -> str:
    return f'<span class="chip" style="background:{COLOUR_HEX[colour]}"></span>'


# --- Solve report ----------------------------------------------------------------------------
def _fmt(value: float | None, digits: int, unit: str = "") -> str:
    return "—" if value is None else f"{value:.{digits}f}{unit}"


def _replay_alg(analysis: dict[str, Any]) -> str:
    lines = []
    for step in analysis["steps"]:
        note = step["case"] or ("-".join(step["slot"]) if step["slot"] else "")
        if step["label"]:
            note = f"{note} ({step['label']})" if note else step["label"]
        comment = f"// {step['name']}: {note}" if note else f"// {step['name']}"
        lines.append(f"{step['moves']} {comment}".strip())
    return "\n".join(lines)


def _part_value(name: str, part: dict[str, Any]) -> str:
    v = part["value"]
    if name == "pauses":
        return f"longest {v['longest_gap_s']:.2f} s · total {v['total_long_gaps_s']:.2f} s"
    return str(v)


def render_report(analysis: dict[str, Any], title: str | None = None) -> str:
    title = title or "Solve report"
    t, sc = analysis["totals"], analysis["score"]
    timed = any(s["duration_s"] is not None for s in analysis["steps"])

    tiles = [
        ("Time", _fmt(t["time_s"], 2, " s")),
        ("Turns", t["turns"]),
        ("Rotations", t["rotations"]),
        ("TPS", _fmt(t["tps"], 2)),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="label">{_e(k)}</div><div class="value">{_e(v)}</div></div>'
        for k, v in tiles
    )
    tile_html += (
        '<div class="tile score"><div class="label">Score</div>'
        f'<div class="value">{sc["value"]:.1f}<small> / 10</small></div></div>'
    )

    rows = []
    for step in analysis["steps"]:
        what = ""
        if step["slot"]:
            what = "".join(_chip(c) for c in step["slot"]) + _e("-".join(step["slot"]))
        if step["case"]:
            what = _e(step["case"])
        if step["label"]:
            what += f'<span class="badge">{_e(step["label"])}</span>'
        duration = f'<td class="num">{_fmt(step["duration_s"], 2, " s")}</td>' if timed else ""
        rows.append(
            f"<tr><td>{_e(STAGE_TITLES[step['name']])}</td>"
            f'<td class="moves">{_e(step["moves"]) or "—"}</td>'
            f'<td class="num">{step["turns"]}</td><td>{what}</td>{duration}</tr>'
        )
    duration_head = '<th class="num">Duration</th>' if timed else ""
    steps_html = (
        '<div class="scroll"><table><thead><tr><th>Stage</th><th>Moves</th>'
        f'<th class="num">Turns</th><th>Slot / case</th>{duration_head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )

    parts = []
    for name, part in sc["components"].items():
        pct = round(100 * part["score"])
        parts.append(
            f"<tr><td>{_e(PART_TITLES[name])}</td><td>{_e(_part_value(name, part))}</td>"
            f'<td><div class="bar"><span style="width:{pct}%"></span></div></td>'
            f'<td class="num">{part["score"]:.2f}</td>'
            f'<td class="num">{round(100 * part["weight"])}%</td></tr>'
        )
    score_html = (
        '<div class="scroll"><table><thead><tr><th>Part</th><th>Measured</th><th></th>'
        '<th class="num">Score</th><th class="num">Weight</th></tr></thead>'
        f"<tbody>{''.join(parts)}</tbody></table></div>"
    )

    rotation = analysis["inspection_rotation"]
    setup = f"{analysis['scramble']} {rotation}".strip()
    cross = analysis["cross_color"]
    details = (
        f"<dl><dt>Scramble</dt><dd><code>{_e(analysis['scramble'])}</code></dd>"
        f"<dt>Inspection</dt><dd><code>{_e(rotation or 'none')}</code></dd>"
        f"<dt>Cross</dt><dd>{_chip(cross)}{_e(cross)}</dd></dl>"
    )
    replay = (
        f'<twisty-player id="replay" puzzle="3x3x3" background="none" control-panel="bottom-row" '
        f'experimental-setup-alg="{_e(setup)}" alg="{_e(_replay_alg(analysis))}"></twisty-player>'
        '<twisty-alg-viewer for="replay"></twisty-alg-viewer>'
    )

    body = (
        f"<h1>{_e(title)}</h1>"
        f'<section class="card"><div class="tiles">{tile_html}</div></section>'
        '<div class="layout"><div>'
        f'<section class="card"><h2>Stages</h2>{steps_html}</section>'
        f'<section class="card"><h2>Score breakdown</h2>{score_html}</section>'
        "</div><div>"
        f'<section class="card"><h2>Replay</h2>{replay}</section>'
        f'<section class="card"><h2>Solve</h2>{details}</section>'
        "</div></div>"
    )
    return _page(title, body, twisty=True)


def write_report(analysis: dict[str, Any], out_dir: Path, title: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.html"
    path.write_text(render_report(analysis, title))
    return path


# --- Case review page ------------------------------------------------------------------------
# Top view, front at the bottom: a 3x3 U face with a thin strip for each side sticker.
_CELL, _GAP, _STRIP = 20, 2, 7
_DRAW_COLOURS = {0: "#facc15", 1: "#f97316", 2: "#16a34a", 3: "#f4f4f5", 4: "#dc2626", 5: "#2563eb"}
_GREY = "#8a8580"
_LL_FACELETS = [int(f) for f in np.flatnonzero(_POS[:, 1] == 1)]
_LL_PIECES = [p for p in EDGES + CORNERS if all(_POS[f][1] == 1 for f in p)]


def _span(i: int) -> tuple[float, float]:
    """Start and length along one axis for grid index 0..4 (0 and 4 are side strips)."""
    if i == 0:
        return 0, _STRIP
    if i == 4:
        return _STRIP + _GAP + 3 * (_CELL + _GAP), _STRIP
    return _STRIP + _GAP + (i - 1) * (_CELL + _GAP), _CELL


def _grid_pos(f: int) -> tuple[int, int]:
    x, _, z = (int(v) for v in _POS[f])
    nx, ny, nz = (int(v) for v in _NORM[f])
    if ny == 1:
        return x + 2, z + 2
    if nx:
        return (4 if nx > 0 else 0), z + 2
    return x + 2, (4 if nz > 0 else 0)


def _centre(f: int) -> tuple[float, float]:
    (x0, w), (y0, h) = (_span(i) for i in _grid_pos(f))
    return x0 + w / 2, y0 + h / 2


def _pll_targets(rel: np.ndarray) -> tuple[dict, np.ndarray]:
    """Where each top-layer piece goes, allowing whichever final AUF moves the fewest pieces
    (PLL diagrams ignore the final AUF). Returns the targets and the colour map used."""
    sides = {frozenset(int(FACE_OF[f]) for f in p if FACE_OF[f] != 0): p for p in _LL_PIECES}
    best = None
    for relabel in POST_AUF_RELABELS:
        targets = {
            p: sides[frozenset(int(relabel[rel[f]]) for f in p if rel[f] != 0)] for p in _LL_PIECES
        }
        moved = sum(t != p for p, t in targets.items())
        if best is None or moved < best[0]:
            best = (moved, targets, relabel)
    assert best is not None
    return best[1], best[2]


def _ll_svg(rel: np.ndarray, arrows: bool) -> str:
    size = 2 * _STRIP + 2 * _GAP + 3 * _CELL + 2 * _GAP
    shapes = []
    if arrows:
        targets, relabel = _pll_targets(rel)
        rel = relabel[rel]
    for f in _LL_FACELETS:
        col, row = _grid_pos(f)
        (x, w), (y, h) = _span(col), _span(row)
        colour = _DRAW_COLOURS[int(rel[f])] if arrows else ("#facc15" if rel[f] == 0 else _GREY)
        shapes.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{colour}" '
            'stroke="rgba(0,0,0,.35)" stroke-width=".6"/>'
        )
    if arrows:
        top = {p: next(f for f in p if FACE_OF[f] == 0) for p in _LL_PIECES}
        for p, target in targets.items():
            if target != p:
                (x1, y1), (x2, y2) = _centre(top[p]), _centre(top[target])
                shapes.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#111" '
                    'stroke-width="1.6" marker-end="url(#head)"/>'
                )
    defs = (
        '<defs><marker id="head" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" '
        'markerHeight="5" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#111"/></marker></defs>'
    )
    return (
        f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" role="img">'
        f"{defs}{''.join(shapes)}</svg>"
    )


def _case_figure(name: str, alg: str, arrows: bool) -> str:
    held = apply(SOLVED, invert(parse(alg)))  # as the solver holds it before the alg
    if held[31] != Color.YELLOW:  # an alg ending in a net rotation; put the cross back on D
        raise ValueError(f"{name}: the cross is not on D in the starting position")
    return (
        f"<figure>{_ll_svg(relative(held), arrows)}"
        f"<figcaption><strong>{_e(name)}</strong><code>{_e(alg)}</code></figcaption></figure>"
    )


def render_cases_page() -> str:
    oll = "".join(_case_figure(f"OLL {n}", a, arrows=False) for n, a in OLL_ALGS.items())
    pll = "".join(_case_figure(n, a, arrows=True) for n, a in PLL_ALGS.items())
    wiki = "https://www.speedsolving.com/wiki/index.php?title="
    body = (
        "<h1>OLL and PLL cases</h1>"
        '<p class="note">Check each diagram against the SpeedSolving wiki '
        f'(<a href="{wiki}OLL">OLL</a>, <a href="{wiki}PLL">PLL</a>). Each diagram is the case '
        "the algorithm under it solves, seen from above with the front at the bottom, in the "
        "position the algorithm starts from (bracketed pre-AUFs and rotations included). "
        "OLL: yellow is the last-layer colour. PLL: arrows show where each piece goes.</p>"
        f'<section class="card"><h2>OLL</h2><div class="cases">{oll}</div></section>'
        f'<section class="card"><h2>PLL</h2><div class="cases">{pll}</div></section>'
    )
    return _page("OLL and PLL cases", body)


def write_cases_page(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cases.html"
    path.write_text(render_cases_page())
    return path
