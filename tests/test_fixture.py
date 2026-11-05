"""Regression test on the verified reel solve. This must pass in every phase.

Phase 1 checks the cube model, notation and inspection-rotation finder against it.
Phase 2 checks the full analysis (stage splits, slots, cases, totals) against every fixture.
"""

import json
from pathlib import Path

import pytest

from cubetrace.analysis import analyze
from cubetrace.cube import (
    SOLVED,
    Color,
    apply,
    find_inspection_rotation,
    is_solved,
    orientation_of,
)
from cubetrace.notation import count, format_alg, parse


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


# --- Phase 2: full analysis against every fixture --------------------------------------------
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.json"))


@pytest.fixture(params=FIXTURES, ids=lambda p: p.stem)
def fixture(request):
    return json.loads(request.param.read_text())


def test_analysis_matches_fixture(fixture):
    fx = fixture
    sol = " ".join(step["moves"] for step in fx["steps"])
    r = analyze(fx["scramble"], sol, time=fx.get("time_s"))

    if "inspection_rotation" in fx:
        got = orientation_of(apply(SOLVED, r["inspection_rotation"]))
        assert got == orientation_of(apply(SOLVED, fx["inspection_rotation"]))
    assert r["cross_color"] == fx["cross_color"]
    assert [s["name"] for s in r["steps"]] == [s["name"] for s in fx["steps"]]

    for got, want in zip(r["steps"], fx["steps"], strict=True):
        name = want["name"]
        assert got["moves"] == format_alg(parse(want["moves"])), name
        assert (got["turns"], got["rotations"]) == (want["turns"], want["rotations"]), name
        assert got["end_turn"] == want["ends_after_turn"], name
        # A slot is an unordered pair of colours.
        assert sorted(got["slot"] or []) == sorted(want.get("slot") or []), name
        assert got["case"] == want.get("case"), name
        if "label" in want:
            assert got["label"] == want["label"], name

    totals = r["totals"]
    assert (totals["turns"], totals["rotations"]) == (
        fx["totals"]["turns"],
        fx["totals"]["rotations"],
    )
    if "tps" in fx["totals"]:
        assert totals["tps"] == fx["totals"]["tps"]


def test_reel_phase_2_done_criteria(reel):
    sol = " ".join(step["moves"] for step in reel["steps"])
    r = analyze(reel["scramble"], sol, time=reel["time_s"])
    assert [s["turns"] for s in r["steps"]] == [6, 7, 8, 6, 8, 12, 14]
    assert [s["slot"] for s in r["steps"][1:5]] == [
        ["green", "red"],
        ["green", "orange"],
        ["blue", "orange"],
        ["blue", "red"],
    ]
    assert (r["steps"][5]["case"], r["steps"][6]["case"]) == ("OLL 53", "Ua")
    assert r["totals"] == {"time_s": 8.31, "turns": 61, "rotations": 1, "tps": 7.34}
