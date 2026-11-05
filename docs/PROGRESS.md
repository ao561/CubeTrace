# Progress

## Status
- Phase 0 (project setup): done.
- Phase 1 (cube model and notation): done. Waiting for OK to start Phase 2.

## What exists
- `notation.py`: `Move`, `parse`, `format_alg`, `invert`, `count`. Accepts `R2'` (as `R2`), `Rw`
  (as `r`), parentheses (ignored) and the typographic primes `’` / `′`. Anything else raises
  `NotationError` with the token and its character position.
- `cube.py`: 54-facelet model in Kociemba order (checked against the kociemba README net). Move
  tables are generated from 3D rotations, not typed by hand. `apply`, `alg_perm`, `compose`,
  `inverse_perm`, `perm_order`, `is_solved`, the 24 `ORIENTATIONS`, `orientation_of`,
  `find_inspection_rotation`.
- `cli.py`: `analyze` / `eval` subcommands exist but exit with "not implemented".

## Metrics
- 173 tests pass; ruff clean.
- Fixture: 61 turns, 1 rotation, 7.34 TPS, step boundaries match; the finder returns `x2 y`
  (equal to `z2 y'`), and the solve ends solved.
- Mutation check: reversing every turn fails all 19 direction tests and the fixture tests.

## Open problems
- On this Mac, something set the macOS `hidden` flag on everything in `.venv`. Python skips
  hidden `.pth` files, so `import cubetrace` failed. Fixed with `chflags -R nohidden .venv`; the
  cause is unknown. If imports break again, run that command first.
- Phase 2 needs 5–10 more real reconstructions with known splits (OLL skip, PLL skip,
  multislot/XCross, non-white cross, wide/slice turns).
- OLL/PLL numbering can't be fully checked in code (see the Phase 2 plan). It needs a one-off
  check by eye against the wiki.

## Next step
- Phase 2: read its section in `docs/PLAN.md`, propose a plan, wait for OK.
