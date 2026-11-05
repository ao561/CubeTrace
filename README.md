# cubetrace

Analyse 3x3 Rubik's cube speedsolves (CFOP) from phone video, without a smart cube.

Status: early development. See `docs/PLAN.md` for the roadmap and `docs/PROGRESS.md` for where
things stand.

## Setup (macOS)

```sh
brew install uv ffmpeg     # uv manages Python; ffmpeg/ffprobe read and write video
uv sync                    # creates .venv with Python 3.12 and all dependencies
```

## Use

```sh
uv run cubetrace --help
uv run pytest -q                                      # tests
uv run ruff check . && uv run ruff format --check .   # lint
```

## Notation

Moves use WCA/SiGN notation: face turns `U D L R F B`, wide turns `Rw` or `r` (and so on),
slices `M E S`, and rotations `x y z`, each with an optional `'` or `2`. `R2'` is read as `R2`.
Parentheses are ignored, so `(R U R' U')` is fine. Anything else is rejected with an error.

Scrambles are applied with white on top and green in front.
