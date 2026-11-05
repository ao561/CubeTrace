"""Score v1: a transparent 0-10 score. All weights and targets live in DEFAULT_CONFIG.

Each part is scored 0-1 by linear interpolation between its "zero" and "full" values (either can
be the larger one), clamped. The score is 10 x the weighted mean of the parts that can be
measured: TPS needs a time, pauses need per-move timestamps. Weights of missing parts are
dropped and the rest rescaled.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "weights": {"tps": 0.40, "turns": 0.25, "rotations": 0.15, "pauses": 0.20},
    "tps": {"zero": 2.0, "full": 10.0},
    "turns": {"zero": 85, "full": 55},
    "rotations": {"zero": 4, "full": 0},
    "pauses": {
        "threshold_s": 0.3,  # gaps between moves longer than this count as pauses
        "longest_gap_s": {"zero": 1.5, "full": 0.3},
        "total_long_gaps_s": {"zero": 3.0, "full": 0.0},
    },
}


def linear(value: float, zero: float, full: float) -> float:
    """0 at `zero`, 1 at `full`, linear in between, clamped to [0, 1]."""
    t = (value - zero) / (full - zero)
    return min(1.0, max(0.0, t))


def score(
    turns: int,
    rotations: int,
    time_s: float | None = None,
    move_times: Sequence[tuple[float, float]] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = DEFAULT_CONFIG if config is None else config
    parts: dict[str, dict[str, Any]] = {}

    if time_s:
        tps = turns / time_s
        parts["tps"] = {"value": round(tps, 2), "score": linear(tps, **cfg["tps"])}
    parts["turns"] = {"value": turns, "score": linear(turns, **cfg["turns"])}
    parts["rotations"] = {"value": rotations, "score": linear(rotations, **cfg["rotations"])}

    if move_times:
        p = cfg["pauses"]
        gaps = [b[0] - a[1] for a, b in zip(move_times, move_times[1:], strict=False)]
        longest = max(gaps, default=0.0)
        total = sum(g for g in gaps if g > p["threshold_s"])
        parts["pauses"] = {
            "value": {"longest_gap_s": round(longest, 3), "total_long_gaps_s": round(total, 3)},
            "score": (
                linear(longest, **p["longest_gap_s"]) + linear(total, **p["total_long_gaps_s"])
            )
            / 2,
        }

    weights = {name: cfg["weights"][name] for name in parts}
    total_weight = sum(weights.values())
    value = 10 * sum(weights[n] * parts[n]["score"] for n in parts) / total_weight
    for name, part in parts.items():
        part["weight"] = round(weights[name] / total_weight, 4)
        part["score"] = round(part["score"], 4)
    return {"value": round(value, 1), "components": parts}
