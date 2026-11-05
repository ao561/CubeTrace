import pytest

from cubetrace.notation import Move, NotationError, count, format_alg, invert, parse

BASES = list("UDLRFB") + list("udlrfb") + list("MES") + list("xyz")


def test_parse_basic():
    assert parse("R U R' U'") == [Move("R", 1), Move("U", 1), Move("R", 3), Move("U", 3)]


def test_empty_and_whitespace():
    assert parse("") == []
    assert parse("   \n\t ") == []


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize("suffix", ["", "2", "'"])
def test_every_token_round_trips(base, suffix):
    token = base + suffix
    assert format_alg(parse(token)) == token


@pytest.mark.parametrize(
    ("written", "canonical"),
    [
        ("Rw", "r"),
        ("Lw' Uw2 Dw Fw Bw'", "l' u2 d f b'"),
        ("R2'", "R2"),
        ("Rw2'", "r2"),
        ("(R U R' U') y (R' F R F')", "R U R' U' y R' F R F'"),
        ("R’ U′", "R' U'"),  # iPhone smart quote and the prime symbol
        ("  R   U  ", "R U"),
    ],
)
def test_accepted_variants_normalise(written, canonical):
    assert format_alg(parse(written)) == canonical


@pytest.mark.parametrize(
    "bad", ["Q", "R3", "Rx", "2R", "3Rw", "R''", "U'2", "Mw", "xw", "RU", "R2x", "r w"]
)
def test_unknown_tokens_are_rejected(bad):
    with pytest.raises(NotationError):
        parse(bad)


def test_error_names_token_and_position():
    with pytest.raises(NotationError) as exc:
        parse("R U Q2 D")
    msg = str(exc.value)
    assert "'Q2'" in msg
    assert "character 5" in msg


def test_move_validates_fields():
    with pytest.raises(ValueError):
        Move("Q", 1)
    with pytest.raises(ValueError):
        Move("R", 4)


def test_invert_reverses_and_inverts():
    assert invert(parse("R U2 F' x")) == parse("x' F U2 R'")
    assert invert([]) == []


def test_count_turns_and_rotations():
    # Every token except x/y/z counts as one turn; rotations are counted separately.
    assert count(parse("U2 M r x y'")) == (3, 2)
    assert count(parse("R U R' U'")) == (4, 0)
    assert count([]) == (0, 0)
    c = count(parse("y R"))
    assert c.turns == 1
    assert c.rotations == 1
