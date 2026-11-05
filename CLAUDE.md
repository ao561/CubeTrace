# cubetrace

Analyse 3x3 Rubik's cube speedsolves (CFOP) from phone video, without a smart cube.
Output: a reconstruction (every turn with its timestamp), CFOP stage splits, OLL/PLL case names,
stats, a score, an HTML report, and eventually an overlay video like cubiq.coach.

Core idea: track the cube's state, not the hands. The scramble gives the exact start state, so
between clear frames the decoder only has to choose among a few possible turns, and the cube must
be solved at the end, which checks the whole result.

## Where things are
- Roadmap, phase by phase, with "done when" criteria: `docs/PLAN.md`. Read the section for the
  current phase before starting work on it.
- Current status, metrics and next step: `docs/PROGRESS.md`.
- Verified real solve used as the main regression test: `tests/fixtures/reel_solve.json`.

## Stack
- Python 3.12, managed with uv. Run everything through `uv run`.
- numpy, opencv-python, pytest, ruff. CLI uses argparse. Torch only in Phase 8, and ask first.
- ffmpeg/ffprobe for video input and output.
- Reports and review screens: static HTML pages. The 3D replay uses cubing.js `<twisty-player>`
  loaded from a CDN, pinned to an exact version. No frontend build step unless I agree to one.
- Layout: `src/cubetrace/` with `cube.py`, `notation.py`, `analysis.py`, `cases.py`, `score.py`,
  `report.py`, and the packages `video/`, `vision/`, `decode/`, `render/`. CLI entry point: `cubetrace`.

## Commands
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check . && uv run ruff format --check .`
- Analyse a typed solve: `uv run cubetrace analyze --scramble "..." --solution "..." [--time 8.31] --out out/`
- Vision eval (Phase 4 onwards): `uv run cubetrace eval --split test`

## Cube conventions (don't change these without asking me)
- Model: 54 facelets in Kociemba facelet order (U R F D L B, as used by the `kociemba` package).
  Each move is a precomputed permutation of the 54 indices.
- Notation: WCA/SiGN. Face turns U D L R F B with ' and 2; wide turns (Rw or r, and so on);
  slices M E S; rotations x y z. Reject unknown tokens with a clear error message.
- Scrambles are applied in WCA orientation: white on U, green on F.
- The solver's inspection rotation isn't written down. Find it by trying all 24 orientations and
  keeping the one where scramble + rotation + solution is solved (ignoring whole-cube orientation).
  Raise an error if no orientation works or more than one does. Compare orientations, not move strings.
- Turn count: every token except x/y/z rotations counts as 1 (U2 = 1, M = 1, r = 1).
  Rotations are counted separately. TPS = turns / time.
- A CFOP stage ends at the first turn, after the previous stage ended, at which its condition holds:
  - Cross: the 4 edges around the cross-colour centre are solved relative to the centres.
  - F2L k: the cross is solved and at least k F2L slots (corner plus edge) are solved.
  - OLL: the cross and all 4 slots are solved, and the last-layer face is all one colour.
  - PLL: the cube is solved.
  Conditions break and come back mid-step (inserting a pair breaks the cross). That's expected:
  only the first time counts. If one turn completes two stages, both end on that turn, and the later
  stage gets 0 moves and is labelled a skip or multislot. Rotations and AUFs belong to the stage
  they happen in.
- Cross colour = the colour of the D centre when F2L finishes. Don't assume white.

## Rules for working on this project
- One phase at a time. At the start of a phase, read its section in `docs/PLAN.md`, propose a short
  plan, and wait for my OK.
- Write tests first for logic. Run tests and lint before saying anything is done.
- Never weaken or delete a test to make it pass. If you think a test is wrong, tell me why.
- `tests/fixtures/reel_solve.json` must pass in every phase.
- Don't trust memory for cube data. Algorithms, OLL/PLL case tables and reconstructions must be
  checked in code: an algorithm has to actually solve the case it's named for. If you can't verify
  something, say so and ask me.
- Don't invent reconstructions or test data. Ask me for real solves.
- Measure vision work; don't eyeball it. Every change to vision or decoding code reports the eval
  numbers before and after. Never tune on the test split.
- Take video timestamps from frame PTS (ffprobe), never frame index × fps. iPhone video is often
  variable frame rate.
- `data/` and `out/` are gitignored. Never commit video.
- Ask before adding a dependency.
- End every session by updating `docs/PROGRESS.md`: what's done, current metrics, open problems,
  next step. Keep it short.
