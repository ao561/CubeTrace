"""OLL and PLL case recognition, by cube state (never by matching algorithm text).

The case tables are built programmatically:
  * `ll_states` enumerates every last-layer state with F2L solved (62,208 of them).
  * OLL cases are orientation patterns of the last layer, grouped by pre-AUF (58 incl. solved).
  * PLL cases are oriented last-layer states, grouped by pre- and post-AUF (22 incl. solved).

Each case is named by one reference algorithm taken from the SpeedSolving wiki (see
`ALG_SOURCE`). A case's state is whatever that algorithm solves, so the names come from the
wiki's algorithm lists, not from memory. Tests check the algorithms keep F2L intact, land in
distinct classes that cover every case, and agree with every other algorithm the wiki lists.

All functions work on centre-relative states (see `cube.relative`) with the cross on D and the
last layer on U, so recognition ignores whole-cube orientation and the colour scheme.
"""

from __future__ import annotations

from collections import deque
from functools import cache

import numpy as np

from cubetrace.cube import (
    _POS,
    FACE_OF,
    ORIENTATIONS,
    SOLVED,
    Color,
    alg_perm,
    apply,
    relative,
)
from cubetrace.notation import Alg, invert, to_moves

U_FACE = 0
D_CENTRE = 31  # index of D5
LL = np.flatnonzero(_POS[:, 1] == 1)  # the 21 facelets in the top layer
F2L = np.flatnonzero(_POS[:, 1] <= 0)  # everything else, centres included
_U_POWERS = [alg_perm(s) for s in ("", "U", "U2", "U'")]


def _post_auf_relabel() -> np.ndarray:
    """Colour map for one post-AUF: side colour c -> the side face its top-row stickers reach
    after U. Derived from the move table, not typed in."""
    sigma = np.arange(6, dtype=np.uint8)
    turned = apply(SOLVED, "U")
    for f in LL:
        if FACE_OF[f] != U_FACE:
            sigma[turned[f]] = FACE_OF[f]
    return sigma


_SIGMA = _post_auf_relabel()
# Colour maps for the 4 post-AUFs: relabelling the top-layer colours by POST_AUF_RELABELS[b]
# is the same as allowing a final U^b.
POST_AUF_RELABELS = [np.arange(6, dtype=np.uint8)]
for _ in range(3):
    POST_AUF_RELABELS.append(_SIGMA[POST_AUF_RELABELS[-1]])


# --- Normalising a state ---------------------------------------------------------------------
def normalise(state: np.ndarray, cross_colour: int) -> np.ndarray:
    """Rotate the cube so `cross_colour` is on D, then recolour relative to the centres."""
    for o in ORIENTATIONS:
        rotated = state[o.perm]
        if rotated[D_CENTRE] == cross_colour:
            return relative(rotated)
    raise ValueError(f"no centre has colour {cross_colour}")


def f2l_solved(rel: np.ndarray) -> bool:
    return bool(np.array_equal(rel[F2L], FACE_OF[F2L]))


def ll_oriented(rel: np.ndarray) -> bool:
    return bool((rel[LL][FACE_OF[LL] == U_FACE] == U_FACE).all())


# --- Case keys -------------------------------------------------------------------------------
def oll_key(rel: np.ndarray) -> bytes:
    """Which top-layer stickers show the U colour, minimised over the 4 pre-AUFs."""
    return min((rel[p][LL] == U_FACE).tobytes() for p in _U_POWERS)


def pll_key(rel: np.ndarray) -> bytes:
    """Top-layer colours, minimised over the 4 pre-AUFs and 4 post-AUFs."""
    return min(s[rel[p][LL]].tobytes() for p in _U_POWERS for s in POST_AUF_RELABELS)


# --- Enumeration -----------------------------------------------------------------------------
# Generators only need to reach every last-layer state; the count check in the tests (62,208)
# proves they do, whatever they are.
_LL_GENERATORS = [
    "U",
    "R U R' U R U2 R'",
    "R U R' U' R' F R2 U' R' U' R U R' F'",
    "F R U R' U' F'",
]


@cache
def ll_states() -> tuple[np.ndarray, ...]:
    """Every state with F2L solved and centres fixed, by BFS from solved."""
    gens = [alg_perm(g) for g in _LL_GENERATORS]
    start = relative(SOLVED)
    seen = {start.tobytes()}
    states = [start]
    queue = deque([start])
    while queue:
        s = queue.popleft()
        for g in gens:
            t = s[g]
            key = t.tobytes()
            if key not in seen:
                seen.add(key)
                states.append(t)
                queue.append(t)
    return tuple(states)


@cache
def oll_classes() -> frozenset[bytes]:
    patterns = {(s[LL] == U_FACE).tobytes(): s for s in ll_states()}
    return frozenset(oll_key(s) for s in patterns.values())


@cache
def pll_classes() -> frozenset[bytes]:
    return frozenset(pll_key(s) for s in ll_states() if ll_oriented(s))


# --- Reference algorithms (SpeedSolving wiki) ------------------------------------------------
# For each case, the first algorithm listed on the wiki that parses and keeps F2L intact.
# Every other parseable wiki algorithm is in tests/data/wiki_ll_algs.json, and the tests check
# they all land in the same case as the reference.
ALG_SOURCE = "SpeedSolving wiki OLL and PLL pages (and their case templates), retrieved 2026-11-05"

OLL_ALGS: dict[int, str] = {
    1: "R U2' R2' F R F' U2 R' F R F'",
    2: "(U') R U' R2' D' r U r' D R2 U R'",
    3: "(U) f (R U R' U') f' U' F (R U R' U') F'",
    4: "f R U R' U' f' U F R U R' U' F'",
    5: "(U2) l' U2 L U L' U l",
    6: "(U2) r U2 R' U' R U' r'",
    7: "r U R' U R U2 r'",
    8: "l' U' L U' L' U2 l",
    9: "(U') R U R' U' R' F R2 U R' U' F'",
    10: "(U') R U R' U R' F R F' R U2' R'",
    11: "(U') r' R2 U R' U R U2' R' U M'",
    12: "(U') r R2' U' R U' R' U2 R U' r' R",
    13: "F U R U2' R' U' R U R' F'",
    14: "R' F R U R' F' R F U' F'",
    15: "(U2) l' U' l L' U' L U l' U l",
    16: "(U2) r U r' R U R' U' r U' r'",
    17: "R U R' U R' F R F' U2 R' F R F'",
    18: "R U2 R2 F R F' U2 M' U R U' r'",
    19: "(U) S' R U R' S U' R' F R F'",
    20: "r' R U R U R' U' r R' M' U R U' r'",
    21: "R U R' U R U' R' U R U2 R'",
    22: "R U2' R2' U' R2 U' R2' U2' R",
    23: "R2' D' R U2 R' D R U2 R",
    24: "r U R' U' r' F R F'",
    25: "(U2) F R' F' r U R U' r'",
    26: "(y') R U2 R' U' R U' R'",
    27: "R U R' U R U2' R'",
    28: "r U R' U' r' R U R U' R'",
    29: "(U) R U R' U' R U' R' F' U' F R U R'",
    30: "(U2) F U R U2' R' U' R U2 R' U' F'",
    31: "(U2) R' U' F U R U' R' F' R",
    32: "S R U R' U' R' F R f'",
    33: "R U R' U' R' F R F'",
    34: "R U R2' U' R' F R U R U' F'",
    35: "R U2' R2' F R F' R U2' R'",
    36: "(U2) L' U' L U' L' U L U L F' L' F",
    37: "(U) F R' F' R U R U' R'",
    38: "(U2) R U R' U R U' R' U' R' F R F'",
    39: "L F' L' U' L U F U' L'",
    40: "R' F R U R' U' F' U R",
    41: "(U2) R U R' U R U2 R' F R U R' U' F'",
    42: "R' U' R U' R' U2' R F R U R' U' F'",
    43: "(U) R' U' F' U F R",
    44: "(U2) F (U R U' R') F'",
    45: "F R U R' U' F'",
    46: "R' U' R' F R F' U R",
    47: "(U') F R' F' R U2 R U' R' U R U2' R'",
    48: "F R U R' U' R U R' U' F'",
    49: "(U2) r U' r2' U r2 U r2' U' r",
    50: "(U2) R' F R2 B' R2' F' R2 B R'",
    51: "F U R U' R' U R U' R' F'",
    52: "R U R' U R U' B U' B' R'",
    53: "l' U' L U' L' U L U' L' U2 l",
    54: "r U R' U R U' R' U R U2' r'",
    55: "(U) R' F R U R U' R2' F' R2 U' R' U R U R'",
    56: "r U r' U R U' R' U R U' R' r U' r'",
    57: "R U R' U' M' U R U' r'",
}

PLL_ALGS: dict[str, str] = {
    "Aa": "(U') x R' U R' D2 R U' R' D2 R2 x'",
    "Ab": "(U') x R2' D2 R U R' D2 R U' R x'",
    "E": "(U) x' R U' R' D R U R' D' R U R' D R U' R' D' x",
    "F": "y L R2 U R U R2 U' R' U' R2 U' R U2 L' U R'",
    "Ga": "(y) R2 U (R' U R' U') R U' R2 (D U' R' U) R D'",
    "Gb": "R' U' R U D' R2 U R' U R U' R U' R2 D",
    "Gc": "(y) R2 U' R U' R U R' U R2 D' U R U' R' D",
    "Gd": "(y2) R U R' U' D R2 U' R U' R' U R' U R2 D'",
    "H": "M2' U M2' U2 M2' U M2'",
    "Ja": "(y2) x R2' F R F' R U2 r' U r U2 x'",
    "Jb": "(y2) R' U L U' R U2' L' U L U2 L'",
    "Na": "R U R' U R U R' F' R U R' U' R' F R2 U' R' U2 R U' R'",
    "Nb": "R' (U r' F2 R F') M' (U r' F2 R F') r U",
    "Ra": "(y') R U' R' U' R U R D R' U' R D' R' U2 R'",
    "Rb": "R' U2 R U2 R' F (R U R' U') R' F' R2' U'",
    "T": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Ua": "R U R' U R' U' R2 U' R' U R' U R",
    "Ub": "(U2) M2 U' M U2 M' U' M2",
    "V": "(y) R U' R U R' D R D' R U' D R2 U R2 D' R2",
    "Y": "R' U' R U' L R U2 R' U' R U2 L' U R2 U R",
    "Z": "(U) M' U M2' U M2' U M' U2 M2'",
}


# --- Recognition -----------------------------------------------------------------------------
def case_state(alg: Alg) -> np.ndarray:
    """The centre-relative state (cross on D) that `alg` solves."""
    return normalise(apply(SOLVED, invert(to_moves(alg))), Color.YELLOW)


@cache
def _oll_names() -> dict[bytes, str]:
    names = {oll_key(relative(SOLVED)): "OLL skip"}
    for n, alg in OLL_ALGS.items():
        key = oll_key(case_state(alg))
        if key in names:
            raise AssertionError(f"OLL {n} and {names[key]} name the same case")
        names[key] = f"OLL {n}"
    return names


@cache
def _pll_names() -> dict[bytes, str]:
    names = {pll_key(relative(SOLVED)): "PLL skip"}
    for name, alg in PLL_ALGS.items():
        key = pll_key(case_state(alg))
        if key in names:
            raise AssertionError(f"{name} and {names[key]} name the same case")
        names[key] = name
    return names


def recognise_oll(state: np.ndarray, cross_colour: int) -> str:
    """OLL case name ("OLL 1".."OLL 57", or "OLL skip") of a state with F2L solved."""
    rel = normalise(state, cross_colour)
    if not f2l_solved(rel):
        raise ValueError("F2L is not solved, so there is no OLL case")
    return _oll_names()[oll_key(rel)]


def recognise_pll(state: np.ndarray, cross_colour: int) -> str:
    """PLL case name ("Aa".."Z", or "PLL skip") of a state with F2L solved and LL oriented."""
    rel = normalise(state, cross_colour)
    if not f2l_solved(rel):
        raise ValueError("F2L is not solved, so there is no PLL case")
    if not ll_oriented(rel):
        raise ValueError("the last layer is not oriented, so there is no PLL case")
    return _pll_names()[pll_key(rel)]
