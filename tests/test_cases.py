import json
import random
from collections import defaultdict
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from cubetrace.cases import (
    LL,
    OLL_ALGS,
    PLL_ALGS,
    case_state,
    f2l_solved,
    ll_oriented,
    ll_states,
    normalise,
    oll_classes,
    oll_key,
    pll_classes,
    pll_key,
    recognise_oll,
    recognise_pll,
)
from cubetrace.cube import ORIENTATIONS, SOLVED, Color, apply, relative
from cubetrace.notation import invert, parse

WIKI = json.loads((Path(__file__).parent / "data" / "wiki_ll_algs.json").read_text())
EXCLUDED = {(e["set"], e["case"], e["alg"]) for e in WIKI["excluded"]}
PLL_NAMES = "Aa Ab E F Ga Gb Gc Gd H Ja Jb Na Nb Ra Rb T Ua Ub V Y Z".split()  # noqa: SIM905
AUFS = ["", "U", "U2", "U'"]
SOLVED_REL = relative(SOLVED)


def oll_name(n: int) -> str:
    return f"OLL {n}"


@cache
def states_by_oll_key() -> dict[bytes, list[np.ndarray]]:
    key_of_pattern: dict[bytes, bytes] = {}
    groups: dict[bytes, list[np.ndarray]] = defaultdict(list)
    for s in ll_states():
        pattern = (s[LL] == 0).tobytes()
        if pattern not in key_of_pattern:
            key_of_pattern[pattern] = oll_key(s)
        groups[key_of_pattern[pattern]].append(s)
    return groups


@cache
def states_by_pll_key() -> dict[bytes, list[np.ndarray]]:
    groups: dict[bytes, list[np.ndarray]] = defaultdict(list)
    for s in ll_states():
        if ll_oriented(s):
            groups[pll_key(s)].append(s)
    return groups


# --- Enumeration and class counts ------------------------------------------------------------
def test_every_last_layer_state_is_enumerated():
    states = ll_states()
    # 4!*4!/2 permutations (parity) x 3^3 corner twists x 2^3 edge flips
    assert len(states) == 288 * 27 * 8 == 62_208
    assert all(f2l_solved(s) for s in states)
    assert sum(ll_oriented(s) for s in states) == 288


def test_there_are_58_oll_and_22_pll_classes():
    assert len(oll_classes()) == 58  # 57 cases + solved
    assert len(pll_classes()) == 22  # 21 cases + solved


# --- Reference algorithms --------------------------------------------------------------------
def test_reference_tables_are_complete():
    assert sorted(OLL_ALGS) == list(range(1, 58))
    assert sorted(PLL_ALGS) == sorted(PLL_NAMES)


def test_reference_algs_come_from_the_wiki():
    for n, alg in OLL_ALGS.items():
        assert alg in WIKI["oll"][str(n)], n
    for name, alg in PLL_ALGS.items():
        assert alg in WIKI["pll"][name], name


@pytest.mark.parametrize("n", sorted(OLL_ALGS))
def test_oll_alg_orients_every_state_in_its_class(n):
    alg = parse(OLL_ALGS[n])
    key = oll_key(case_state(alg))
    assert key != oll_key(SOLVED_REL)
    members = states_by_oll_key()[key]
    for s in random.Random(n).sample(members, 25):
        results = [normalise(apply(s, parse(a) + alg), Color.YELLOW) for a in AUFS]
        assert any(f2l_solved(r) and ll_oriented(r) for r in results)


@pytest.mark.parametrize("name", PLL_NAMES)
def test_pll_alg_solves_every_state_in_its_class(name):
    alg = parse(PLL_ALGS[name])
    key = pll_key(case_state(alg))
    assert key != pll_key(SOLVED_REL)
    members = states_by_pll_key()[key]
    assert members
    for s in members:
        after = [normalise(apply(s, parse(a) + alg), Color.YELLOW) for a in AUFS]
        assert any(np.array_equal(apply(r, b), SOLVED_REL) for r in after for b in AUFS), name


def test_reference_algs_name_distinct_classes_covering_every_case():
    oll_keys = [oll_key(case_state(a)) for a in OLL_ALGS.values()]
    pll_keys = [pll_key(case_state(a)) for a in PLL_ALGS.values()]
    assert len(set(oll_keys)) == 57
    assert len(set(pll_keys)) == 21
    assert set(oll_keys) == oll_classes() - {oll_key(SOLVED_REL)}
    assert set(pll_keys) == pll_classes() - {pll_key(SOLVED_REL)}


# --- Cross-check against every other algorithm the wiki lists --------------------------------
def _wiki_algs(kind):
    return [
        (case, alg)
        for case, algs in WIKI[kind].items()
        for alg in algs
        if (kind, case, alg) not in EXCLUDED
    ]


@pytest.mark.parametrize(("case", "alg"), _wiki_algs("oll"))
def test_every_wiki_oll_alg_agrees_with_reference(case, alg):
    rel = case_state(alg)
    assert f2l_solved(rel)
    assert recognise_oll(rel, Color.YELLOW) == oll_name(int(case))


@pytest.mark.parametrize(("case", "alg"), _wiki_algs("pll"))
def test_every_wiki_pll_alg_agrees_with_reference(case, alg):
    rel = case_state(alg)
    assert f2l_solved(rel)
    assert ll_oriented(rel)
    assert recognise_pll(rel, Color.YELLOW) == case


@pytest.mark.parametrize("entry", WIKI["excluded"], ids=lambda e: f"{e['case']}:{e['alg']}")
def test_excluded_wiki_algs_really_are_wrong(entry):
    rel = case_state(entry["alg"])
    if not f2l_solved(rel) or (entry["set"] == "pll" and not ll_oriented(rel)):
        return
    recognise = recognise_oll if entry["set"] == "oll" else recognise_pll
    expected = oll_name(int(entry["case"])) if entry["set"] == "oll" else entry["case"]
    assert recognise(rel, Color.YELLOW) != expected


# --- Recognition -----------------------------------------------------------------------------
def _recoloured(state, o):
    """Repaint the cube with the colour scheme rotated by orientation `o`, so the same
    physical case appears with a different cross colour."""
    lut = np.array(o.centres, dtype=np.uint8)
    return lut[state], int(lut[Color.YELLOW])


CASES = [("oll", n, alg) for n, alg in OLL_ALGS.items()] + [
    ("pll", n, alg) for n, alg in PLL_ALGS.items()
]


@pytest.mark.parametrize(("kind", "case", "alg"), CASES, ids=lambda x: str(x))
def test_recognition_ignores_auf_rotation_and_colour_scheme(kind, case, alg):
    recognise = recognise_oll if kind == "oll" else recognise_pll
    expected = oll_name(case) if kind == "oll" else case
    held = apply(SOLVED, invert(parse(alg)))  # the case, held as the solver would
    rng = random.Random(str(case))
    for pre in AUFS:
        s = apply(held, pre)
        for o in ORIENTATIONS:
            rotated = s[o.perm]
            assert recognise(rotated, Color.YELLOW) == expected
            repainted, cross = _recoloured(rotated, rng.choice(ORIENTATIONS))
            assert recognise(repainted, cross) == expected


@pytest.mark.parametrize("name", PLL_NAMES)
def test_pll_recognition_ignores_post_auf(name):
    for post in AUFS:
        state = apply(apply(SOLVED, post), invert(parse(PLL_ALGS[name])))
        assert recognise_pll(state, Color.YELLOW) == name


def test_skips():
    tperm = apply(SOLVED, "R U R' U' R' F R2 U' R' U' R U R' F'")
    assert recognise_oll(tperm, Color.YELLOW) == "OLL skip"
    assert recognise_oll(SOLVED, Color.YELLOW) == "OLL skip"
    for auf in AUFS:
        assert recognise_pll(apply(SOLVED, auf), Color.YELLOW) == "PLL skip"


def test_recognition_rejects_unfinished_states():
    with pytest.raises(ValueError, match="F2L"):
        recognise_oll(apply(SOLVED, "R"), Color.YELLOW)
    with pytest.raises(ValueError, match="F2L"):
        recognise_pll(apply(SOLVED, "R"), Color.YELLOW)
    with pytest.raises(ValueError, match="orient"):
        recognise_pll(apply(SOLVED, "F R U R' U' F'"), Color.YELLOW)


def test_recognition_uses_the_given_cross_colour():
    # OLL 45 with the white cross on D: recognised with white as the cross colour, and not
    # recognisable with yellow (relative to a yellow cross, F2L isn't solved).
    state = apply(SOLVED, "x2 " + " ".join(str(m) for m in invert(parse(OLL_ALGS[45]))))
    assert recognise_oll(state, Color.WHITE) == "OLL 45"
    with pytest.raises(ValueError):
        recognise_oll(state, Color.YELLOW)
