import itertools
import random

import numpy as np
import pytest

from cubetrace.cube import (
    CENTRES,
    CORNERS,
    EDGES,
    FACE_OF,
    ORIENTATIONS,
    SOLVED,
    AmbiguousInspectionRotation,
    Color,
    NoInspectionRotation,
    alg_perm,
    apply,
    compose,
    face_with_centre,
    find_inspection_rotation,
    inverse_perm,
    is_solved,
    opposite,
    orientation_of,
    perm_order,
    piece_solved,
    relative,
)
from cubetrace.notation import Move, invert

WHITE, RED, GREEN, YELLOW, ORANGE, BLUE = Color
ALL_BASES = list("UDLRFB") + list("udlrfb") + list("MES") + list("xyz")
IDENTITY = np.arange(54)


def idx(name: str) -> int:
    """Kociemba facelet name -> index, e.g. 'U1' -> 0, 'R1' -> 9, 'B9' -> 53."""
    return "URFDLB".index(name[0]) * 9 + int(name[1]) - 1


def same(a, b) -> bool:
    return np.array_equal(alg_perm(a), alg_perm(b))


# --- Turn directions -------------------------------------------------------------------------
# Physical facts from WCA/SiGN conventions (faces turn clockwise as seen looking at that face;
# M follows L, E follows D, S follows F; x follows R, y follows U, z follows F), checked on the
# Kociemba facelet net. Most order and identity tests below still pass if every turn is
# reversed (only the T-perm order catches that), so these pin each direction separately.
DIRECTION_CASES = [
    ("R", "U3 U6 U9", GREEN),
    ("R", "F3 F6 F9", YELLOW),
    ("R'", "U3 U6 U9", BLUE),
    ("U", "F1 F2 F3", RED),
    ("U", "L1 L2 L3", GREEN),
    ("F", "R1 R4 R7", WHITE),
    ("F", "U7 U8 U9", ORANGE),
    ("D", "R7 R8 R9", GREEN),
    ("L", "F1 F4 F7", WHITE),
    ("B", "L1 L4 L7", WHITE),
    ("B", "U1 U2 U3", RED),
    ("M", "F2 F5 F8", WHITE),
    ("E", "R4 R5 R6", GREEN),
    ("S", "R2 R5 R8", WHITE),
    ("r", "U2 U3 U5 U6 U8 U9", GREEN),
    ("r", "U1 U4 U7", WHITE),
    ("x", "U1 U2 U3 U4 U5 U6 U7 U8 U9", GREEN),
    ("y", "F1 F2 F3 F4 F5 F6 F7 F8 F9", RED),
    ("z", "R1 R2 R3 R4 R5 R6 R7 R8 R9", WHITE),
]


@pytest.mark.parametrize(("alg", "facelets", "colour"), DIRECTION_CASES)
def test_turn_direction(alg, facelets, colour):
    state = apply(SOLVED, alg)
    got = {name: Color(state[idx(name)]).name for name in facelets.split()}
    assert got == {name: colour.name for name in facelets.split()}


# --- Move table sanity -----------------------------------------------------------------------
@pytest.mark.parametrize("base", ALL_BASES)
def test_every_move_is_a_permutation(base):
    for amount in (1, 2, 3):
        p = alg_perm([Move(base, amount)])
        assert sorted(p.tolist()) == list(range(54))


@pytest.mark.parametrize("base", list("UDLRFB"))
def test_face_turns_keep_centres_and_move_20_stickers(base):
    p = alg_perm(base)
    assert np.array_equal(p[CENTRES], CENTRES)
    assert int((p != IDENTITY).sum()) == 20


# --- Orders ----------------------------------------------------------------------------------
@pytest.mark.parametrize("base", ALL_BASES)
def test_quarter_turn_order_4_and_half_turn_order_2(base):
    assert perm_order(alg_perm(base)) == 4
    assert perm_order(alg_perm(base + "2")) == 2


@pytest.mark.parametrize(
    ("alg", "order"),
    [
        ("R U R' U'", 6),
        ("R U", 105),
        ("R U'", 63),  # differs from R U, so this catches R and U turning opposite ways
        ("R U R' U' R' F R2 U' R' U' R U R' F'", 2),  # T-perm
    ],
)
def test_known_orders(alg, order):
    assert perm_order(alg_perm(alg)) == order


# --- Inverses --------------------------------------------------------------------------------
def test_random_algorithm_then_inverse_is_identity():
    rng = random.Random(0)
    all_moves = [Move(b, a) for b in ALL_BASES for a in (1, 2, 3)]
    for _ in range(200):
        alg = [rng.choice(all_moves) for _ in range(rng.randint(1, 30))]
        assert np.array_equal(alg_perm(alg + invert(alg)), IDENTITY)
        assert np.array_equal(apply(apply(SOLVED, alg), invert(alg)), SOLVED)
        assert np.array_equal(compose(alg_perm(alg), inverse_perm(alg_perm(alg))), IDENTITY)


def test_powers_agree():
    assert same("R2", "R R")
    assert same("R'", "R R R")
    assert same("x'", "x x x")


# --- Wide and slice identities ---------------------------------------------------------------
@pytest.mark.parametrize(
    ("lhs", "rhs"),
    [
        ("r", "R M'"),
        ("l", "L M"),
        ("u", "U E'"),
        ("d", "D E"),
        ("f", "F S"),
        ("b", "B S'"),
        ("x", "R M' L'"),
        ("y", "U E' D'"),
        ("z", "F S B'"),
    ],
)
def test_wide_and_rotation_identities(lhs, rhs):
    assert same(lhs, rhs)


# --- Solved checks and orientations ----------------------------------------------------------
def test_solved_state():
    assert is_solved(SOLVED)
    assert is_solved(SOLVED, ignore_orientation=True)
    assert not is_solved(apply(SOLVED, "R"))
    assert not is_solved(apply(SOLVED, "R"), ignore_orientation=True)
    assert not is_solved(apply(SOLVED, "M"), ignore_orientation=True)


def test_there_are_24_distinct_orientations():
    assert len(ORIENTATIONS) == 24
    assert len({o.perm.tobytes() for o in ORIENTATIONS}) == 24
    assert len(set(ORIENTATIONS)) == 24


def test_orientations_are_closed_under_composition():
    perms = {o.perm.tobytes() for o in ORIENTATIONS}
    for a, b in itertools.product(ORIENTATIONS, repeat=2):
        assert compose(a.perm, b.perm).tobytes() in perms


def test_orientation_names_match_their_perms():
    for o in ORIENTATIONS:
        assert np.array_equal(alg_perm(list(o.moves)), o.perm), o.name


def test_rotated_solved_cube_is_solved_only_when_ignoring_orientation():
    for o in ORIENTATIONS:
        state = SOLVED[o.perm]
        assert is_solved(state, ignore_orientation=True), o.name
        assert is_solved(state) == (o.name == ""), o.name


def test_orientation_of_ignores_face_turns():
    assert orientation_of(apply(SOLVED, "R U F' D2 x")) == orientation_of(apply(SOLVED, "x"))
    assert orientation_of(SOLVED).name == ""


# --- Inspection-rotation finder --------------------------------------------------------------
def test_finder_errors_when_nothing_works():
    with pytest.raises(NoInspectionRotation):
        find_inspection_rotation("R U F", "F'")


def test_finder_errors_when_several_work():
    # A solved cube with an empty solution is solved from every orientation.
    with pytest.raises(AmbiguousInspectionRotation):
        find_inspection_rotation("", "")


def test_finder_simple_case():
    # Scramble R U. After a y rotation the old R face sits at F and U stays at U, so the solver
    # undoes the scramble with U' F'. The finder must work out that rotation was y.
    found = find_inspection_rotation("R U", "U' F'")
    assert found == orientation_of(apply(SOLVED, "y"))
    assert found.name == "y"


# --- Pieces and centre-relative colours ------------------------------------------------------
def test_pieces_cover_every_non_centre_facelet_once():
    assert len(EDGES) == 12
    assert len(CORNERS) == 8
    covered = [f for piece in EDGES + CORNERS for f in piece]
    assert sorted(covered) == sorted(set(range(54)) - set(CENTRES.tolist()))
    for piece in EDGES + CORNERS:
        assert len({int(FACE_OF[f]) for f in piece}) == len(piece)  # one sticker per face


def test_named_pieces():
    # UF edge is U8 + F2; URF corner is U9 + R1 + F3 (Kociemba net).
    assert tuple(sorted((idx("U8"), idx("F2")))) in {tuple(sorted(e)) for e in EDGES}
    urf = tuple(sorted((idx("U9"), idx("R1"), idx("F3"))))
    assert urf in {tuple(sorted(c)) for c in CORNERS}


def test_pieces_stay_pieces_under_every_move():
    piece_sets = {frozenset(p) for p in EDGES + CORNERS}
    for base in ALL_BASES:
        p = alg_perm(base)
        for piece in EDGES + CORNERS:
            assert frozenset(int(p[f]) for f in piece) in piece_sets, base


def test_relative_removes_orientation():
    for o in ORIENTATIONS:
        assert np.array_equal(relative(SOLVED[o.perm]), FACE_OF), o.name
    assert not np.array_equal(relative(apply(SOLVED, "M")), FACE_OF)
    # R M' L' turns every layer the same way (it equals x), so it is solved relative to centres.
    assert np.array_equal(relative(apply(SOLVED, "R M' L'")), FACE_OF)
    assert not np.array_equal(relative(apply(SOLVED, "M' R' L x")), FACE_OF)  # = M2


def test_piece_solved_and_face_with_centre():
    rel = relative(apply(SOLVED, "R"))
    uf = next(e for e in EDGES if idx("U8") in e)
    ur = next(e for e in EDGES if idx("U6") in e)
    assert piece_solved(rel, uf)
    assert not piece_solved(rel, ur)
    assert face_with_centre(apply(SOLVED, "x2"), Color.WHITE) == "URFDLB".index("D")
    assert [opposite(f) for f in range(6)] == [3, 4, 5, 0, 1, 2]
