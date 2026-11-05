import html
import re
from html.parser import HTMLParser

import pytest

from cubetrace.analysis import analyze
from cubetrace.cases import OLL_ALGS, PLL_ALGS
from cubetrace.report import CUBING_JS, render_cases_page, render_report, write_report


@pytest.fixture(scope="module")
def reel_analysis(reel):
    sol = " ".join(s["moves"] for s in reel["steps"])
    return analyze(reel["scramble"], sol, time=reel["time_s"])


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def parse_html(page: str) -> _Collector:
    c = _Collector()
    c.feed(page)
    return c


def test_cubing_js_is_pinned_to_an_exact_version():
    assert re.search(r"/cubing@\d+\.\d+\.\d+/", CUBING_JS)


def test_report_contents(reel_analysis):
    page = render_report(reel_analysis)
    doc = parse_html(page)
    text = " ".join(doc.text)
    assert reel_analysis["scramble"] in text
    for step in reel_analysis["steps"]:
        assert step["moves"] in text
    for word in ("OLL 53", "Ua", "green", "red", "8.31", "61", "7.34", "7.2"):
        assert word in text
    scripts = [a for t, a in doc.tags if t == "script"]
    assert any(a.get("src") == CUBING_JS and a.get("type") == "module" for a in scripts)


def test_replay_setup_and_alg(reel_analysis):
    doc = parse_html(render_report(reel_analysis))
    player = next(a for t, a in doc.tags if t == "twisty-player")
    setup = player["experimental-setup-alg"]
    assert setup == f"{reel_analysis['scramble']} {reel_analysis['inspection_rotation']}"
    # The replay alg is the solution, one stage per line with a comment naming it.
    lines = [line.split("//")[0].strip() for line in player["alg"].splitlines()]
    assert " ".join(x for x in lines if x) == reel_analysis["solution"]
    assert "// oll: OLL 53" in player["alg"]
    viewer = next(a for t, a in doc.tags if t == "twisty-alg-viewer")
    assert viewer["for"] == player["id"]


def test_durations_column_only_with_timestamps():
    plain = render_report(analyze("R U R' D'", "D R U' R'"))
    timed = render_report(
        analyze(
            "R U R' D'", "D R U' R'", move_times=[(0.1, 0.2), (0.3, 0.4), (0.5, 0.6), (0.7, 0.8)]
        )
    )
    assert "Duration" not in plain
    assert "Duration" in timed


def test_text_is_escaped(reel_analysis):
    page = render_report(reel_analysis, title="<b>&")
    assert html.escape("<b>&") in page
    assert "<b>&" not in page


def test_write_report(tmp_path, reel_analysis):
    path = write_report(reel_analysis, tmp_path)
    assert path == tmp_path / "report.html"
    assert path.read_text() == render_report(reel_analysis)


def test_cases_page_shows_every_case():
    doc = parse_html(render_cases_page())
    text = " ".join(doc.text)
    for n in OLL_ALGS:
        assert f"OLL {n}" in text
    for name, alg in PLL_ALGS.items():
        assert name in text
        assert alg in text
    assert sum(1 for t, _ in doc.tags if t == "svg") == 57 + 21
