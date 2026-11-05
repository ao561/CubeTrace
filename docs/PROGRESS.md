# Progress

## Status
- Phases 0 and 1: done (committed).
- Phase 2 (analysis engine): built and passing on the reel solve. Not done until the extra real
  reconstructions pass and the OLL/PLL review page has been checked by eye.

## What exists
- `analysis.py`: `analyze(scramble, solution, time, move_times)` returns the inspection rotation,
  cross colour, 7 stages (moves, turns, rotations, start/end turn, slot, case, label, duration),
  totals and score. Stage rules as in CLAUDE.md, stages ending "at or after" the previous one.
- `cases.py`: all 62,208 last-layer states enumerated, giving 58 OLL and 22 PLL classes.
  Reference algorithms come from the SpeedSolving wiki (retrieved 2026-11-05). All 429 parseable
  wiki algorithms are in `tests/data/wiki_ll_algs.json`; every one agrees with its case except
  12 wiki errors, which are listed with reasons and tested.
- `score.py`: score v1. Weights and targets are in `DEFAULT_CONFIG`.
- `report.py`: solve report (cubing.js 0.66.1 from jsDelivr) and the OLL/PLL review page.
- CLI: `cubetrace analyze ...` and `cubetrace cases --out out/`.

## Metrics
- 822 tests pass; ruff clean.
- Reel fixture: turns [6, 7, 8, 6, 8, 12, 14], slots green-red, green-orange, blue-orange,
  blue-red, OLL 53, Ua, 61 turns, 1 rotation, 7.34 TPS, score 7.2. These match exactly.

## Decisions made this phase
- Cross colour: CLAUDE.md's rule (the colour on D at the first move where that colour's F2L is
  complete). The "first colour to finish F2L" variant agreed at the Phase 2 kickoff was dropped:
  when the last layer is skipped it picks the wrong colour (test added).
- Analysis JSON uses the key `cross_color`, matching the fixture.
- The project moved from `~/Documents/CubeTrace/CubeTrace` to `~/Developer/CubeTrace`: iCloud
  marked `.venv` files hidden, which broke imports.
- `.gitignore` now ignores only the top-level `/data/` and `/out/` (plain `data/` was also
  ignoring `tests/data/`).

## Open problems
- Waiting on 5–10 real reconstructions: an OLL skip, a PLL skip, a multislot/XCross, a non-white
  cross, and one with wide or slice turns. They go in `tests/fixtures/` in the reel format.
- Review `out/cases.html` against the wiki once. Code can't detect two swapped case numbers.
- The 3D replay couldn't be checked in headless Chrome (no WebGL). The 2D view renders the
  correct start state. Check the 3D view in a normal browser.

## Next step
- Add the real reconstructions and fix any mismatches. Then Phase 2 is done.
