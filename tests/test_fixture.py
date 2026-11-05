"""Regression test on the verified reel solve. This must pass in every phase.

Phase 1 checks the cube model, notation and inspection-rotation finder against it.
Later phases add the analysis checks (stage splits, slots, cases, score).
"""

from cubetrace.cube import (
    SOLVED,
    Color,
    apply,
    find_inspection_rotation,
    is_solved,
    orientation_of,
)
from cubetrace.notation import count, parse


def solution(reel):
    return [m for step in reel["steps"] for m in parse(step["moves"])]


def test_turn_and_rotation_counts(reel):
    moves = solution(reel)
    turns, rotations = count(moves)
    assert (turns, rotations) == (reel["totals"]["turns"], reel["totals"]["rotations"])
    assert round(turns / reel["time_s"], 2) == reel["totals"]["tps"]

    done = 0
    for step in reel["steps"]:
        c = count(parse(step["moves"]))
        assert (c.turns, c.rotations) == (step["turns"], step["rotations"]), step["name"]
        done += c.turns
        assert done == step["ends_after_turn"], step["name"]


def test_inspection_rotation_is_x2_y(reel):
    found = find_inspection_rotation(reel["scramble"], solution(reel))
    x2_y = orientation_of(apply(SOLVED, reel["inspection_rotation"]))
    z2_yp = orientation_of(apply(SOLVED, "z2 y'"))
    assert x2_y == z2_yp
    assert found == x2_y


def test_full_solve_ends_solved(reel):
    rot = find_inspection_rotation(reel["scramble"], solution(reel))
    start = apply(SOLVED, reel["scramble"])
    assert not is_solved(start, ignore_orientation=True)

    end = apply(start, list(rot.moves) + solution(reel))
    assert is_solved(end, ignore_orientation=True)

    # Without the inspection rotation the same solution does not solve the cube.
    assert not is_solved(apply(start, solution(reel)), ignore_orientation=True)


def test_inspection_rotation_puts_yellow_on_top_red_in_front(reel):
    rot = find_inspection_rotation(reel["scramble"], solution(reel))
    state = apply(SOLVED, list(rot.moves))
    u_centre, f_centre = state[4], state[22]  # U5 and F5 in Kociemba order
    assert (Color(u_centre), Color(f_centre)) == (Color.YELLOW, Color.RED)
