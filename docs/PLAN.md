# Roadmap

Build the analysis engine first, because it's needed anyway and it's how vision output gets
checked. Then build the vision side in small, measured steps. Each phase ends with something that
works and has tests.

## Phase 0 — Project setup
- uv project with a src layout, pytest, ruff, and an argparse CLI skeleton.
- README with setup steps. `docs/PROGRESS.md`.
- Done when: `uv run pytest` passes one trivial test and `uv run cubetrace --help` works.

## Phase 1 — Cube model and notation
- Facelet model, a move table for every notation in CLAUDE.md, apply/invert, `is_solved`
  (with and without ignoring whole-cube orientation), the 24 orientations, and the inspection-rotation finder.
- Tests:
  - each face turn has order 4; `R U R' U'` has order 6; `R U` has order 105
  - any algorithm followed by its inverse is the identity
  - wide and slice identities: `r` == `R M'`, `x` == `R M' L'`, and so on
  - the T-perm `R U R' U' R' F R2 U' R' U' R U R' F'` has order 2
  - Fixture: the finder returns the orientation of `x2 y` (the same as `z2 y'`), and the full
    solution ends solved.
- Done when: all tests pass.

## Phase 2 — Analysis engine (typed moves)
- `analyze(scramble, solution, time=None, move_times=None)` returns JSON containing: the inspection
  rotation, the cross colour, and a list of steps. Each step has a name, moves, turns, rotations,
  start and end turn, slot colours (F2L steps), case name (OLL/PLL steps), and a duration when
  timestamps exist. It also returns totals (time, turns, rotations, TPS) and the score with its breakdown.
- Case recognition (`cases.py`):
  - Build the OLL and PLL tables programmatically. Enumerate last-layer states with F2L solved,
    then group them: OLL by pre-AUF, PLL by pre- and post-AUF.
  - Assert exactly 58 OLL classes (57 + solved) and 22 PLL classes (21 + solved).
  - Name each class with one reference algorithm, using the standard numbering (SpeedSolving wiki).
    A test applies every reference algorithm and confirms it solves its own class.
  - Recognise cases by state, never by matching algorithm text. Mirrors and inverses must come out right.
- Score v1 (`score.py`): 0–10, transparent and configurable, keeping all weights and targets in one
  config dict. Each component is scored 0–1 against a target:
  - TPS
  - turns compared with a target (around 55 for CFOP)
  - rotations
  - pauses: the longest gap and the total of gaps over 0.3 s between turns, when timestamps exist
  The report shows the breakdown. Don't try to copy cubiq's number.
- HTML report (`report.py`), laid out like the reel:
  - a scorecard: time, turns, rotations, TPS, score
  - the scramble
  - each step's moves, with its case name and slot colours
  - a twisty-player replay, with setup = scramble + inspection rotation and alg = solution
- More fixtures: ask me for 5–10 more real reconstructions with known splits. Include at least one
  OLL skip, one PLL skip, one multislot or XCross, one non-white cross, and one with wide or slice turns.
- Done when the fixture reproduces exactly:
  - step turns [6, 7, 8, 6, 8, 12, 14]
  - slot order green-red, green-orange, blue-orange, blue-red
  - OLL 53, Ua perm
  - 61 turns, 1 rotation, 7.34 TPS
  - every other fixture also passes

## Recording protocol (for every solve in the dataset)
- Use iPhone Slo-mo at 240 fps, or 120 fps if 240 isn't available.
- Put the phone on a stand in the same spot each time. Never handheld.
- Angle: slightly above and in front, so the U and F faces are clear and R is visible during normal turning.
- Bright, even, neutral-white light. Warm bulbs make white/yellow and red/orange hard to tell apart.
  Use a plain background with no cube colours.
- The cube should fill at least a third of the frame's width.
- Hold the scrambled cube still for about 1 s before starting, in the orientation you'll start in,
  and hold the solved cube still for about 1 s at the end.
- Save the scramble text with the video.
- Make sure you keep the original file. Check with ffprobe that it reports around 240 fps, because
  some sharing routes re-encode slo-mo to 30 fps.

## Data layout
```
data/solves/<solve_id>/
  video.mov
  meta.json     # scramble, solution (once reconstructed), nominal fps, camera setup, speed bucket, split
  labels.json   # moves: [{token, start_pts, end_pts}]
  stickers/     # hand-labelled frames (Phase 4)
```
- Splits (train/val/test) are assigned per solve, never per frame.
- Test solves are never used for tuning.

## Phase 3 — Video input and labelling tool
- `video/`: read frames with their PTS, with an option to downscale, and compute a per-frame motion
  score around the cube to find settled (still) frames.
- Labelling tool: a local web page served by a small Python server. It steps through the video
  frame by frame next to the known solution. I mark where each turn starts and ends, and the tool
  suggests boundaries from the motion score. It saves `labels.json`.
- Done when: I can label a 60-turn solve in about 15 minutes, and labels save and load without loss.

## Phase 4 — Sticker reader
- Input: one frame. Output, for each visible face:
  - which face it is (by centre colour)
  - the 3x3 colour grid
  - a confidence per sticker
  - each sticker's position in the image, which the overlays need later
- Start with classical computer vision:
  - find the cube
  - fit each face's grid (sticker blobs, then a quad/homography fit)
  - classify colours in Lab space
- Calibrate colours per video rather than with fixed thresholds. Centres never change colour, and
  the still second at the start shows known stickers, because the scramble gives the expected
  state. Red/orange and white/yellow are the known hard pairs.
- Build a small tool for hand-labelling about 200 settled frames from at least 5 solves (click a
  face's 4 corners, confirm the colours). That's the eval set.
- Move to a learned detector only if the classical approach misses the target. Ask me first.
- Done when, on held-out labelled frames:
  - sticker colours are at least 99% correct on settled frames
  - the face grid is found in at least 95% of settled frames
  - the report includes a per-colour confusion matrix

## Phase 5 — State tracking and decoding
- Start state: scramble, plus the orientation read from the centres in the first still frame.
- Beam search over turn sequences:
  - Between observed frames, consider 0–3 turns, more if the gap is long.
  - Score each candidate by how well its predicted visible stickers match the reader's output
    (weighted by confidence), plus a prior over turns: no same-face repeats like `R R`, common
    CFOP triggers more likely, and turn rates that are physically plausible given the timestamps.
- Rotations show up as a change in the visible centres.
- Hard constraint: the final state is solved. Make the beam width configurable and keep the top
  alternatives for the correction screen.
- Move set: start with face turns plus rotations. Add wide and slice turns once that works.
- Output: a reconstruction with a time and confidence per turn, fed into the Phase 2 analysis.
- `cubetrace eval` reports:
  - per-turn accuracy (edit distance against the true reconstruction)
  - percentage of solves fully correct
  - stage-split accuracy
  - each of these by speed bucket: under 3 TPS, 3–6 TPS, over 6 TPS
- Done when: per-turn accuracy is at least 99% on slow test solves, with medium and fast results
  reported as baselines.

## Phase 6 — Correction screen
- A local web page with a video scrubber and the proposed turns.
- Low-confidence turns are highlighted. I can change, insert or delete a turn. Each edit re-runs
  the analysis and checks the cube still ends solved.
- Saved corrections become new labelled data.
- Done when: fixing a solve with 3 wrong turns takes under 2 minutes.

## Phase 7 — Overlay video
- Render a copy of the video with:
  - a running timer and turn counter
  - a move ticker with the current turn lit
  - a stage card: name, slot colours, case name
  - a small cube showing the current state
  - outlines on the pieces in the current case, using Phase 4 sticker positions
  - the scorecard at the end
- Draw with OpenCV/Pillow and encode with ffmpeg (H.264, `-preset veryfast`), keeping the original audio.
- Done when: any analysed solve renders a full overlay video.

## Phase 8 (only if needed) — Learned turn classifier
- Where the decoder fails (usually fast bursts with no settled frames between turns), train a small
  model on short clips around each labelled turn from Phases 3 and 6. It gives the decoder
  per-turn probabilities.
- Ask me before adding torch. Report eval numbers with and without it.
