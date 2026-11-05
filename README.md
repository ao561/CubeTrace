# cubetrace

Analyse 3x3 Rubik's cube speedsolves (CFOP) from phone video, without a smart cube.

Status: early development. See `docs/PLAN.md` for the roadmap and `docs/PROGRESS.md` for where
things stand.

## Setup (macOS)

```sh
brew install uv ffmpeg     # uv manages Python; ffmpeg/ffprobe read and write video
uv sync                    # creates .venv with Python 3.12 and all dependencies
```

Keep the project outside iCloud-synced folders such as `~/Documents`. iCloud marks the files
in `.venv` as hidden, which makes Python skip the editable install and breaks `import cubetrace`.

## Use

Analyse a typed solve. This writes `analysis.json` and `report.html`, which has a scorecard,
stage splits with slots and OLL/PLL cases, the score breakdown, and a 3D replay:

```sh
uv run cubetrace analyze --scramble "B R2 D2 ..." --solution "L R' F D ..." --time 8.31 --out out/solve1
```

Add `--move-times times.json` (a list of `[start_s, end_s]` pairs, one per solution move,
measured from the timer start) to get per-stage durations and the pauses part of the score.

Write a page showing every OLL and PLL case, to check the case tables by eye:

```sh
uv run cubetrace cases --out out/
```

Development:

```sh
uv run pytest -q                                      # tests
uv run ruff check . && uv run ruff format --check .   # lint
```

## Notation

Moves use WCA/SiGN notation: face turns `U D L R F B`, wide turns `Rw` or `r` (and so on),
slices `M E S`, and rotations `x y z`, each with an optional `'` or `2`. `R2'` is read as `R2`.
Parentheses are ignored, so `(R U R' U')` is fine. Anything else is rejected with an error.

Scrambles are applied with white on top and green in front.
