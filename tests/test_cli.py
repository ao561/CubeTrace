import json
import subprocess
import sys

import pytest

from cubetrace.cli import main


def test_help_exits_zero_and_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for command in ("analyze", "cases", "eval"):
        assert command in out


def test_no_subcommand_prints_help_and_fails(capsys):
    assert main([]) != 0
    assert "usage" in capsys.readouterr().err


def test_eval_is_not_implemented_yet(capsys):
    assert main(["eval", "--split", "test"]) != 0
    assert "not implemented" in capsys.readouterr().err


def test_python_dash_m_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "cubetrace", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "analyze" in result.stdout


# --- analyze ---------------------------------------------------------------------------------
def test_analyze_writes_json_and_report(tmp_path, reel, capsys):
    sol = " ".join(s["moves"] for s in reel["steps"])
    argv = ["analyze", "--scramble", reel["scramble"], "--solution", sol, "--time", "8.31"]
    assert main([*argv, "--out", str(tmp_path)]) == 0
    result = json.loads((tmp_path / "analysis.json").read_text())
    assert [s["turns"] for s in result["steps"]] == [6, 7, 8, 6, 8, 12, 14]
    assert (tmp_path / "report.html").exists()
    out = capsys.readouterr().out
    assert "61 turns" in out
    assert "7.34 TPS" in out
    assert "report.html" in out


def test_analyze_reads_move_times(tmp_path):
    times = tmp_path / "times.json"
    times.write_text(json.dumps([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]]))
    argv = ["analyze", "--scramble", "R U R' D'", "--solution", "D R U' R'"]
    assert main([*argv, "--move-times", str(times), "--out", str(tmp_path / "out")]) == 0
    result = json.loads((tmp_path / "out" / "analysis.json").read_text())
    assert result["totals"]["time_s"] == pytest.approx(0.8)
    assert "pauses" in result["score"]["components"]


@pytest.mark.parametrize(
    ("scramble", "solution", "message"),
    [
        ("R U Q", "U' R'", "unknown move 'Q'"),
        ("R U", "U'", "no inspection rotation"),
    ],
)
def test_analyze_reports_bad_input_without_a_traceback(
    tmp_path, capsys, scramble, solution, message
):
    argv = ["analyze", "--scramble", scramble, "--solution", solution, "--out", str(tmp_path)]
    assert main(argv) == 2
    err = capsys.readouterr().err
    assert message in err
    assert "Traceback" not in err
    assert not (tmp_path / "analysis.json").exists()


# --- cases -----------------------------------------------------------------------------------
def test_cases_writes_review_page(tmp_path, capsys):
    assert main(["cases", "--out", str(tmp_path)]) == 0
    assert "OLL 53" in (tmp_path / "cases.html").read_text()
    assert "cases.html" in capsys.readouterr().out
