"""WCA/SiGN move notation: parsing, formatting, inverting and counting.

Accepted tokens (whitespace-separated):
  face turns     U D L R F B
  wide turns     Uw Dw Lw Rw Fw Bw, or u d l r f b
  slices         M E S
  rotations      x y z
each followed by nothing (clockwise), 2 (half turn), ' (anticlockwise) or 2' (same as 2).
Parentheses are ignored. The typographic primes ’ and ′ (e.g. from iPhone smart punctuation)
are read as '. Anything else raises NotationError.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NamedTuple

FACES = "UDLRFB"
WIDES = "udlrfb"
SLICES = "MES"
ROTATIONS = "xyz"
BASES = FACES + WIDES + SLICES + ROTATIONS

_SUFFIX = {1: "", 2: "2", 3: "'"}
_AMOUNT = {"": 1, "2": 2, "2'": 2, "'": 3}
_TOKEN = re.compile(r"(?P<base>[UDLRFB]w|[UDLRFBudlrfbMESxyz])(?P<suffix>2'|2|'|)")
_PRIMES = str.maketrans({"’": "'", "′": "'", "(": " ", ")": " "})


class NotationError(ValueError):
    """Raised for a move token that isn't valid WCA/SiGN notation."""


@dataclass(frozen=True, slots=True)
class Move:
    """One move. `base` is a letter from BASES (wide turns are lowercase); `amount` is the
    number of clockwise quarter turns: 1, 2 or 3 (3 is written ')."""

    base: str
    amount: int

    def __post_init__(self) -> None:
        if len(self.base) != 1 or self.base not in BASES:
            raise ValueError(f"unknown move base {self.base!r}")
        if self.amount not in _SUFFIX:
            raise ValueError(f"move amount must be 1, 2 or 3, got {self.amount!r}")

    @property
    def is_rotation(self) -> bool:
        return self.base in ROTATIONS

    def inverse(self) -> Move:
        return Move(self.base, 4 - self.amount)

    def __str__(self) -> str:
        return self.base + _SUFFIX[self.amount]


class Counts(NamedTuple):
    turns: int
    rotations: int


Alg = str | Sequence[Move]


def parse(text: str) -> list[Move]:
    """Parse a move sequence. Raises NotationError naming the first bad token."""
    clean = text.translate(_PRIMES)
    moves = []
    for m in re.finditer(r"\S+", clean):
        tok = _TOKEN.fullmatch(m.group())
        if tok is None:
            raise NotationError(
                f"unknown move {text[m.start() : m.end()]!r} at character {m.start() + 1} "
                f"of {text!r}"
            )
        base = tok["base"]
        if len(base) == 2:  # "Rw" -> "r"
            base = base[0].lower()
        moves.append(Move(base, _AMOUNT[tok["suffix"]]))
    return moves


def to_moves(alg: Alg) -> list[Move]:
    """Accept either a notation string or a sequence of Moves."""
    return parse(alg) if isinstance(alg, str) else list(alg)


def format_alg(moves: Iterable[Move]) -> str:
    return " ".join(str(m) for m in moves)


def invert(moves: Sequence[Move]) -> list[Move]:
    return [m.inverse() for m in reversed(moves)]


def count(moves: Iterable[Move]) -> Counts:
    """Turns (every move except x/y/z, each counting 1) and rotations (x/y/z)."""
    turns = rotations = 0
    for m in moves:
        if m.is_rotation:
            rotations += 1
        else:
            turns += 1
    return Counts(turns, rotations)
