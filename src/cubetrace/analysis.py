"""CFOP analysis of a typed solve: inspection rotation, cross colour, stage splits, slots,
OLL/PLL cases, totals and score.

Stage rules (CLAUDE.md): a stage ends on the first move at or after the previous stage's end at
which its condition holds, judged relative to the centres:
  cross   the 4 edges around the cross-colour centre are solved
  f2l k   cross solved and at least k slots (corner + edge) solved
  oll     cross and all 4 slots solved, and the last-layer face is one colour
  pll     the cube is solved
Moves between two stage ends (rotations and AUFs included) belong to the later stage. Moves after
the cube is first solved are added to PLL.

Cross colour: the colour on D when F2L finishes, i.e. at the first move where the colour then on
D has its cross and 4 slots solved. (Taking "the first colour to finish F2L" instead goes wrong
when the last layer is skipped: one move before the end, the cube is a single face turn from
solved, which counts as a finished F2L for the colour opposite that face.)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from cubetrace.cases import recognise_oll, recognise_pll
from cubetrace.cube import (
    CENTRES,
    CORNERS,
    EDGES,
    FACE_OF,
    SOLVED,
    Color,
    apply,
    find_inspection_rotation,
    is_solved,
    move_perm,
    opposite,
    piece_solved,
    relative,
)
from cubetrace.notation import Alg, Move, count, format_alg, to_moves
from cubetrace.score import score

STAGES = ("cross", "f2l1", "f2l2", "f2l3", "f2l4", "oll", "pll")
# Label for a stage that ends on the same move as the stage before it.
_ZERO_MOVE_LABEL = {
    "cross": "skip",
    "f2l1": "xcross",
    "f2l2": "multislot",
    "f2l3": "multislot",
    "f2l4": "multislot",
    "oll": "skip",
    "pll": "skip",
}
D_FACE = 3
# Order in which a slot's two colours are listed (matches the reel fixture: green-red).
_SLOT_ORDER = [Color.GREEN, Color.BLUE, Color.RED, Color.ORANGE, Color.WHITE, Color.YELLOW]


def _piece_faces(piece: tuple[int, ...]) -> frozenset[int]:
    return frozenset(int(FACE_OF[f]) for f in piece)


_EDGE_BY_FACES = {_piece_faces(e): e for e in EDGES}
# For each face (as the cross face): its 4 cross edges, and its 4 slots as
# (corner, edge, (side face a, side face b)).
_CROSS_EDGES = {f: [e for e in EDGES if f in _piece_faces(e)] for f in range(6)}
_SLOTS = {
    f: [
        (c, _EDGE_BY_FACES[_piece_faces(c) - {f}], tuple(sorted(_piece_faces(c) - {f})))
        for c in CORNERS
        if f in _piece_faces(c)
    ]
    for f in range(6)
}


class _Checks:
    """Stage conditions for one state, relative to a cross colour."""

    def __init__(self, state: np.ndarray, cross_colour: int):
        self.state = state
        self.rel = relative(state)
        self.face = int(np.flatnonzero(state[CENTRES] == cross_colour)[0])

    def cross(self) -> bool:
        return all(piece_solved(self.rel, e) for e in _CROSS_EDGES[self.face])

    def slots(self) -> list[tuple[str, str]]:
        """Colour pairs of the solved slots."""
        centres = self.state[CENTRES]
        solved = []
        for corner, edge, (a, b) in _SLOTS[self.face]:
            if piece_solved(self.rel, corner) and piece_solved(self.rel, edge):
                pair = sorted((Color(centres[a]), Color(centres[b])), key=_SLOT_ORDER.index)
                solved.append((pair[0].name.lower(), pair[1].name.lower()))
        return solved

    def f2l(self, k: int) -> bool:
        return self.cross() and len(self.slots()) >= k

    def oll(self) -> bool:
        ll = opposite(self.face)
        return self.f2l(4) and bool((self.rel[ll * 9 : ll * 9 + 9] == ll).all())

    def pll(self) -> bool:
        return is_solved(self.state, ignore_orientation=True)


def _cross_colour(states: list[np.ndarray]) -> int:
    for state in states:
        on_d = int(state[CENTRES][D_FACE])
        if _Checks(state, on_d).f2l(4):
            return on_d
    raise AssertionError("the solve ends solved, so F2L must finish for the colour on D")


def _stage_ends(states: list[np.ndarray], cross_colour: int) -> list[int]:
    """For each stage, the number of solution moves done when it ends."""
    conditions = [
        lambda c: c.cross(),
        lambda c: c.f2l(1),
        lambda c: c.f2l(2),
        lambda c: c.f2l(3),
        lambda c: c.f2l(4),
        lambda c: c.oll(),
        lambda c: c.pll(),
    ]
    ends, k = [], 0
    for cond in conditions:
        while not cond(_Checks(states[k], cross_colour)):
            k += 1
        ends.append(k)
    return ends


def _check_move_times(move_times: Sequence[Sequence[float]], n: int) -> list[tuple[float, float]]:
    times = [(float(a), float(b)) for a, b in move_times]
    if len(times) != n:
        raise ValueError(f"move_times has {len(times)} entries but the solution has {n} moves")
    previous_start = 0.0
    for i, (start, end) in enumerate(times):
        # Turns may overlap at speed, so only the start times have to increase.
        if not (previous_start <= start <= end):
            raise ValueError(
                f"move_times: move {i + 1} must start no earlier than the move before it "
                "and end no earlier than it starts"
            )
        previous_start = start
    return times


def analyze(
    scramble: Alg,
    solution: Alg,
    time: float | None = None,
    move_times: Sequence[Sequence[float]] | None = None,
    score_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyse a solve. `move_times` gives (start_s, end_s) for every solution move, measured
    from the timer start; with it, steps get durations and the score includes pauses."""
    scr, sol = to_moves(scramble), to_moves(solution)
    times = _check_move_times(move_times, len(sol)) if move_times is not None else None
    if time is None and times:
        time = times[-1][1]

    rotation = find_inspection_rotation(scr, sol)
    states = [apply(SOLVED, scr + list(rotation.moves))]
    for m in sol:
        states.append(states[-1][move_perm(m)])

    cross_colour = _cross_colour(states)
    ends = _stage_ends(states, cross_colour)
    ends[-1] = len(sol)  # anything after the cube is solved goes into PLL

    steps = []
    claimed: list[tuple[str, str]] = []
    start = 0
    for name, end in zip(STAGES, ends, strict=True):
        moves: list[Move] = sol[start:end]
        turns_before = count(sol[:start]).turns
        c = count(moves)
        step: dict[str, Any] = {
            "name": name,
            "moves": format_alg(moves),
            "turns": c.turns,
            "rotations": c.rotations,
            "start_turn": turns_before,
            "end_turn": turns_before + c.turns,
            "slot": None,
            "case": None,
            "label": None,
            "duration_s": None,
        }
        if name.startswith("f2l"):
            new = [s for s in _Checks(states[end], cross_colour).slots() if s not in claimed]
            if new:
                claimed.append(new[0])
                step["slot"] = list(new[0])
        if name == "oll":
            step["case"] = recognise_oll(states[start], cross_colour)
        if name == "pll":
            step["case"] = recognise_pll(states[start], cross_colour)

        if not moves:
            step["label"] = _ZERO_MOVE_LABEL[name]
        elif step["case"] in ("OLL skip", "PLL skip"):
            step["label"] = "skip"

        if times is not None:
            t_start = times[start - 1][1] if start else 0.0
            t_end = times[end - 1][1] if end else 0.0
            step["duration_s"] = round(max(0.0, t_end - t_start), 3)

        steps.append(step)
        start = end

    total = count(sol)
    return {
        "scramble": format_alg(scr),
        "solution": format_alg(sol),
        "inspection_rotation": rotation.name,
        "cross_color": Color(cross_colour).name.lower(),
        "steps": steps,
        "totals": {
            "time_s": time,
            "turns": total.turns,
            "rotations": total.rotations,
            "tps": round(total.turns / time, 2) if time else None,
        },
        "score": score(total.turns, total.rotations, time, times, score_config),
    }
