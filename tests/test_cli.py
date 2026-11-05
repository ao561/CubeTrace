import subprocess
import sys

import pytest

from cubetrace.cli import main


def test_help_exits_zero_and_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "analyze" in out
    assert "eval" in out


def test_no_subcommand_prints_help_and_fails(capsys):
    assert main([]) != 0
    assert "usage" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["analyze", "--scramble", "R U", "--solution", "U' R'", "--out", "out/"],
        ["eval", "--split", "test"],
    ],
)
def test_unimplemented_subcommands_fail_clearly(argv, capsys):
    assert main(argv) != 0
    assert "not implemented" in capsys.readouterr().err


def test_python_dash_m_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "cubetrace", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "analyze" in result.stdout
