import copy

import pytest

from cubetrace.score import DEFAULT_CONFIG, linear, score


def test_linear_scales_and_clamps_in_both_directions():
    assert linear(6, zero=2, full=10) == pytest.approx(0.5)
    assert linear(1, zero=2, full=10) == 0
    assert linear(11, zero=2, full=10) == 1
    # Lower is better: full marks at 55 turns, zero at 85.
    assert linear(70, zero=85, full=55) == pytest.approx(0.5)
    assert linear(40, zero=85, full=55) == 1
    assert linear(90, zero=85, full=55) == 0


def test_reel_numbers_without_timestamps():
    s = score(turns=61, rotations=1, time_s=8.31)
    assert set(s["components"]) == {"tps", "turns", "rotations"}
    assert s["components"]["tps"]["score"] == pytest.approx((61 / 8.31 - 2) / 8, abs=1e-3)
    assert s["components"]["turns"]["score"] == pytest.approx(0.8)
    assert s["components"]["rotations"]["score"] == pytest.approx(0.75)
    assert sum(c["weight"] for c in s["components"].values()) == pytest.approx(1)
    assert s["value"] == pytest.approx(7.2, abs=0.05)


def test_perfect_solve_scores_10():
    times = [(i * 0.08, i * 0.08 + 0.05) for i in range(40)]
    s = score(turns=40, rotations=0, time_s=3.2, move_times=times)
    assert s["value"] == 10


def test_pauses_use_longest_gap_and_total_of_long_gaps():
    # Gaps between moves: 0.1, 1.0, 0.1. Only the 1.0 s gap is over the 0.3 s threshold.
    times = [(0.0, 0.1), (0.2, 0.3), (1.3, 1.4), (1.5, 1.6)]
    s = score(turns=4, rotations=0, time_s=1.6, move_times=times)
    p = s["components"]["pauses"]
    assert p["value"]["longest_gap_s"] == pytest.approx(1.0)
    assert p["value"]["total_long_gaps_s"] == pytest.approx(1.0)
    longest = (1.5 - 1.0) / (1.5 - 0.3)
    total = (3.0 - 1.0) / 3.0
    assert p["score"] == pytest.approx((longest + total) / 2, abs=1e-3)


def test_parts_that_cannot_be_measured_are_left_out():
    s = score(turns=61, rotations=1)
    assert set(s["components"]) == {"turns", "rotations"}
    assert sum(c["weight"] for c in s["components"].values()) == pytest.approx(1)


def test_config_is_respected_and_not_mutated():
    before = copy.deepcopy(DEFAULT_CONFIG)
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["weights"] = {"tps": 1.0, "turns": 0.0, "rotations": 0.0, "pauses": 0.0}
    s = score(turns=61, rotations=1, time_s=8.31, config=cfg)
    assert s["value"] == pytest.approx(10 * (61 / 8.31 - 2) / 8, abs=0.05)
    assert before == DEFAULT_CONFIG
