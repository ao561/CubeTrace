"""Facelet model of the 3x3 cube.

State: a uint8 array of 54 sticker colours in Kociemba facelet order
(U1..U9, R1..R9, F1..F9, D1..D9, L1..L9, B1..B9). Each face is read row by row as seen
looking at it, on the standard net: U above F with B at its top edge, D below F with F at its
top edge, and L, F, R, B in a row with U at their top edges.

Colours are the Color values 0..5, named after where they sit on a solved cube held in WCA
orientation (white U, red R, green F, yellow D, orange L, blue B).

Moves are permutations: applying perm p gives new_state = state[p], i.e. new_state[i] is the
sticker that moved to facelet i. "p then q" is p[q] (see `compose`).

The move tables are not typed by hand. Each facelet gets a 3D position and outward normal, and
every move is a 90° rotation of the facelets in its layer(s), mapped back to facelet indices.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from functools import cache

import numpy as np

from cubetrace.notation import Alg, Move, to_moves

FACE_ORDER = "URFDLB"


class Color(IntEnum):
    WHITE = 0  # U
    RED = 1  # R
    GREEN = 2  # F
    YELLOW = 3  # D
    ORANGE = 4  # L
    BLUE = 5  # B


SOLVED = np.repeat(np.arange(6, dtype=np.uint8), 9)
SOLVED.setflags(write=False)
CENTRES = np.arange(4, 54, 9)  # U5 R5 F5 D5 L5 B5
IDENTITY = np.arange(54)
IDENTITY.setflags(write=False)

# --- Geometry -------------------------------------------------------------------------------
# Axes: x points to R, y to U, z to F (right-handed).
# For each face: outward normal, and the 3D directions of "right" and "down" in that face's
# reading order on the Kociemba net.
_X, _Y, _Z = np.eye(3, dtype=int)
_FACE_FRAMES = {
    "U": (_Y, _X, _Z),  # viewed from above, B at the top
    "R": (_X, -_Z, -_Y),  # viewed from the right, U at the top, F on the left
    "F": (_Z, _X, -_Y),
    "D": (-_Y, _X, -_Z),  # viewed from below, F at the top
    "L": (-_X, _Z, -_Y),  # viewed from the left, B on the left
    "B": (-_Z, -_X, -_Y),  # viewed from the back, R on the left
}


def _facelet_geometry() -> tuple[np.ndarray, np.ndarray]:
    positions, normals = [], []
    for face in FACE_ORDER:
        normal, right, down = _FACE_FRAMES[face]
        for row in range(3):
            for col in range(3):
                positions.append(normal + (col - 1) * right + (row - 1) * down)
                normals.append(normal)
    return np.array(positions), np.array(normals)


_POS, _NORM = _facelet_geometry()
_INDEX = {(tuple(p), tuple(n)): i for i, (p, n) in enumerate(zip(_POS, _NORM, strict=True))}
assert len(_INDEX) == 54


def _rotate_cw(v: np.ndarray, axis: np.ndarray) -> np.ndarray:
    """Rotate vectors v (N x 3) by 90° clockwise as seen looking down `axis` from outside,
    i.e. by -90° about `axis` (Rodrigues with cos = 0, sin = -1)."""
    return -np.cross(axis, v) + np.outer(v @ axis, axis)


def _layer_perm(axis: np.ndarray, layers: tuple[int, ...]) -> np.ndarray:
    """Quarter turn of the facelets whose position along `axis` is in `layers`."""
    perm = IDENTITY.copy()
    moving = np.isin(_POS @ axis, layers)
    new_pos = _rotate_cw(_POS[moving], axis)
    new_norm = _rotate_cw(_NORM[moving], axis)
    for src, p, n in zip(np.flatnonzero(moving), new_pos, new_norm, strict=True):
        perm[_INDEX[(tuple(p), tuple(n))]] = src
    return perm


# Clockwise quarter turns. Face turns rotate about their outward normal; slices follow
# M = L, E = D, S = F; rotations follow x = R, y = U, z = F.
_AXES = {"U": _Y, "D": -_Y, "R": _X, "L": -_X, "F": _Z, "B": -_Z}
_QUARTER: dict[str, np.ndarray] = {}
for _f, _a in _AXES.items():
    _QUARTER[_f] = _layer_perm(_a, (1,))
    _QUARTER[_f.lower()] = _layer_perm(_a, (0, 1))
for _s, _f in (("M", "L"), ("E", "D"), ("S", "F")):
    _QUARTER[_s] = _layer_perm(_AXES[_f], (0,))
for _r, _f in (("x", "R"), ("y", "U"), ("z", "F")):
    _QUARTER[_r] = _layer_perm(_AXES[_f], (-1, 0, 1))


# --- Permutation helpers --------------------------------------------------------------------
def compose(*perms: np.ndarray) -> np.ndarray:
    """The permutation for applying each of `perms` in order."""
    out = IDENTITY
    for p in perms:
        out = out[p]
    return out


def inverse_perm(p: np.ndarray) -> np.ndarray:
    return np.argsort(p)


def perm_order(p: np.ndarray) -> int:
    """Smallest k >= 1 with p^k = identity (lcm of cycle lengths)."""
    seen = np.zeros(len(p), dtype=bool)
    order = 1
    for start in range(len(p)):
        length = 0
        i = start
        while not seen[i]:
            seen[i] = True
            i = p[i]
            length += 1
        if length:
            order = math.lcm(order, length)
    return order


@cache
def move_perm(move: Move) -> np.ndarray:
    q = _QUARTER[move.base]
    p = compose(*([q] * move.amount))
    p.setflags(write=False)
    return p


def alg_perm(alg: Alg) -> np.ndarray:
    return compose(*(move_perm(m) for m in to_moves(alg)))


def apply(state: np.ndarray, alg: Alg) -> np.ndarray:
    return state[alg_perm(alg)]


def is_solved(state: np.ndarray, ignore_orientation: bool = False) -> bool:
    """Solved in WCA orientation, or (ignore_orientation) every face a single colour."""
    if not ignore_orientation:
        return bool(np.array_equal(state, SOLVED))
    faces = state.reshape(6, 9)
    return bool((faces == faces[:, 4:5]).all())


# --- Whole-cube orientations ----------------------------------------------------------------
@dataclass(frozen=True)
class Orientation:
    """A whole-cube rotation, identified by where it puts the six centres.
    Equality compares the rotation itself, not its name."""

    centres: tuple[int, ...]
    name: str = field(compare=False)
    moves: tuple[Move, ...] = field(compare=False, repr=False)
    perm: np.ndarray = field(compare=False, repr=False)


def _orientations() -> tuple[Orientation, ...]:
    """All 24 rotations, each named by the shortest x/y/z sequence found first by BFS."""
    gens = [Move(b, a) for b in "xzy" for a in (2, 1, 3)]
    found: dict[bytes, Orientation] = {}
    queue: deque[tuple[Move, ...]] = deque([()])
    while queue:
        moves = queue.popleft()
        perm = alg_perm(moves)
        if perm.tobytes() in found:
            continue
        perm.setflags(write=False)
        centres = tuple(int(c) for c in SOLVED[perm][CENTRES])
        name = " ".join(str(m) for m in moves)
        found[perm.tobytes()] = Orientation(centres, name, moves, perm)
        if len(moves) < 2:
            queue.extend(moves + (g,) for g in gens)
    return tuple(found.values())


ORIENTATIONS = _orientations()
_BY_CENTRES = {o.centres: o for o in ORIENTATIONS}


def orientation_of(state: np.ndarray) -> Orientation:
    """The whole-cube rotation from WCA orientation, read from the centres."""
    return _BY_CENTRES[tuple(int(c) for c in state[CENTRES])]


# --- Inspection rotation --------------------------------------------------------------------
class NoInspectionRotation(ValueError):
    pass


class AmbiguousInspectionRotation(ValueError):
    pass


def find_inspection_rotation(scramble: Alg, solution: Alg) -> Orientation:
    """The single rotation r such that scramble + r + solution leaves every face one colour."""
    start = apply(SOLVED, scramble)
    sol = alg_perm(solution)
    matches = [
        o for o in ORIENTATIONS if is_solved(start[compose(o.perm, sol)], ignore_orientation=True)
    ]
    if not matches:
        raise NoInspectionRotation(
            "no inspection rotation makes scramble + rotation + solution solved"
        )
    if len(matches) > 1:
        names = ", ".join(repr(o.name) for o in matches)
        raise AmbiguousInspectionRotation(f"{len(matches)} inspection rotations work: {names}")
    return matches[0]
