"""Stage detection on constructed (not real) solves.

These inputs are deliberately artificial: each scramble is the inverse of a short solution, built
to hit one rule in CLAUDE.md (skips, several stages ending on one turn, non-white cross). Real
reconstructions in tests/fixtures/ are the acceptance tests.
"""

import json

import pytest

from cubetrace.analysis import STAGES, analyze
from cubetrace.cases import OLL_ALGS
from cubetrace.cube import SOLVED, NoInspectionRotation, apply, orientation_of
from cubetrace.notation import format_alg, invert, parse


def steps_by_name(result):
    return {s["name"]: s for s in result["steps"]}


def turns(result):
    return [s["turns"] for s in result["steps"]]


def test_stage_names_and_order():
    assert STAGES == ("cross", "f2l1", "f2l2", "f2l3", "f2l4", "oll", "pll")


def test_oll_only_solve_skips_everything_else():
    # The "solve" is just OLL 45, so cross and F2L are done before the first turn.
    alg = OLL_ALGS[45]
    r = analyze(format_alg(invert(parse(alg))), alg)
    s = steps_by_name(r)
    assert turns(r) == [0, 0, 0, 0, 0, 6, 0]
    assert r["cross_color"] == "yellow"
    assert s["cross"]["label"] == "skip"
    assert s["f2l1"]["label"] == "xcross"
    assert [s[n]["label"] for n in ("f2l2", "f2l3", "f2l4")] == ["multislot"] * 3
    assert s["oll"]["case"] == "OLL 45"
    assert s["oll"]["label"] is None
    assert s["pll"]["case"] == "PLL skip"
    assert s["pll"]["label"] == "skip"


def test_pll_skip_that_needs_an_auf():
    alg = OLL_ALGS[45]
    r = analyze("U' " + format_alg(invert(parse(alg))), alg + " U")
    s = steps_by_name(r)
    assert s["oll"]["moves"] == alg
    assert s["pll"]["moves"] == "U"
    assert s["pll"]["turns"] == 1
    assert s["pll"]["case"] == "PLL skip"
    assert s["pll"]["label"] == "skip"


def test_one_turn_finishes_cross_and_three_slots():
    # R U R' breaks only the FR slot; D' shifts the whole bottom layer. The first solution
    # turn (D) therefore finishes the cross and three slots at once (an XCross plus a
    # multislot), and R U' R' finishes the last slot, OLL and PLL together.
    r = analyze("R U R' D'", "D R U' R'")
    s = steps_by_name(r)
    # One move before the end the cube is a single R turn from solved, which is a finished
    # F2L for an orange cross. The cross colour must still be the one on D: yellow.
    assert r["cross_color"] == "yellow"
    assert turns(r) == [1, 0, 0, 0, 3, 0, 0]
    assert [s[n]["end_turn"] for n in STAGES] == [1, 1, 1, 1, 4, 4, 4]
    assert [s[n]["start_turn"] for n in STAGES] == [0, 1, 1, 1, 1, 4, 4]
    assert s["f2l1"]["label"] == "xcross"
    assert s["f2l2"]["label"] == "multislot"
    assert s["f2l3"]["label"] == "multislot"
    assert s["f2l4"]["label"] is None
    assert s["f2l4"]["slot"] == ["green", "red"]
    first_three = {tuple(s[n]["slot"]) for n in ("f2l1", "f2l2", "f2l3")}
    assert first_three == {("green", "orange"), ("blue", "orange"), ("blue", "red")}
    assert s["oll"]["label"] == s["pll"]["label"] == "skip"


def test_non_white_cross_after_an_inspection_rotation():
    # The same solve as above, but the solver holds the cube with x (green on top, blue on D).
    # In WCA terms the scramble's U and D faces become F and B.
    r = analyze("R F R' B'", "D R U' R'")
    assert r["cross_color"] == "blue"
    assert turns(r) == [1, 0, 0, 0, 3, 0, 0]
    assert steps_by_name(r)["f2l4"]["slot"] == ["red", "yellow"]
    found = orientation_of(apply(SOLVED, r["inspection_rotation"]))
    assert found == orientation_of(apply(SOLVED, "x"))


def test_rotations_belong_to_the_stage_they_happen_in():
    # As above, but the solver rotates y before the last pair. After y the old R face is in
    # front, so R U' R' becomes F U' F'. The y goes into F2L 4 and isn't counted as a turn.
    r = analyze("R U R' D'", "D y F U' F'")
    s = steps_by_name(r)
    assert s["f2l4"]["moves"] == "y F U' F'"
    assert (s["f2l4"]["turns"], s["f2l4"]["rotations"]) == (3, 1)
    assert s["f2l4"]["slot"] == ["green", "red"]
    assert (r["totals"]["turns"], r["totals"]["rotations"]) == (4, 1)


def test_totals_and_tps():
    r = analyze("R U R' D'", "D R U' R'", time=2.0)
    assert r["totals"] == {"time_s": 2.0, "turns": 4, "rotations": 0, "tps": 2.0}
    assert analyze("R U R' D'", "D R U' R'")["totals"]["tps"] is None


def test_durations_from_move_times():
    times = [(0.5, 0.6), (0.7, 0.8), (1.0, 1.1), (1.2, 1.3)]
    r = analyze("R U R' D'", "D R U' R'", move_times=times)
    durations = [s["duration_s"] for s in r["steps"]]
    assert durations == pytest.approx([0.6, 0, 0, 0, 0.7, 0, 0])
    assert r["totals"]["time_s"] == pytest.approx(1.3)


def test_move_times_must_match_the_solution():
    with pytest.raises(ValueError, match="move_times"):
        analyze("R U R' D'", "D R U' R'", move_times=[(0.1, 0.2)])
    with pytest.raises(ValueError, match="move_times"):
        analyze("R U R' D'", "D R U' R'", move_times=[(0.5, 0.6), (0.4, 0.5), (1, 2), (2, 3)])


def test_unsolvable_input_raises():
    with pytest.raises(NoInspectionRotation):
        analyze("R U R' D'", "D R U'")


def test_result_is_json_serialisable():
    r = analyze("R U R' D'", "D R U' R'", time=2.0, move_times=None)
    json.dumps(r)
    assert set(r) >= {
        "scramble",
        "solution",
        "inspection_rotation",
        "cross_color",
        "steps",
        "totals",
        "score",
    }
    assert set(r["steps"][0]) == {
        "name",
        "moves",
        "turns",
        "rotations",
        "start_turn",
        "end_turn",
        "slot",
        "case",
        "label",
        "duration_s",
    }
