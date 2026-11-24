"""Balance overrides from tools/tuning.json, written by the tuner (tools/tuner.py). Missing or empty file: defaults.

Constants read through get(name, default); the tuner finds them by that call and takes the default from the source."""
import json
import math
import os
from pathlib import Path

PATH = Path(os.environ.get("SPEC_TUNING") or Path(__file__).resolve().parent / "tuning.json")  # SPEC_TUNING: a sweep's own values
try:
    _VALUES = json.loads(PATH.read_text(encoding="utf-8") or "{}")
except FileNotFoundError:
    _VALUES = {}


def get(name, default):
    v = _VALUES.get(name, default)
    if isinstance(default, dict) and isinstance(v, dict):  # JSON keys are strings: map back onto the default's keys
        return {k: v.get(str(k), d) for k, d in default.items()}
    return v


def snap(x, whole=False):
    """x on the round grid: steps of 5, 0.5, 0.05 ... by its own size, whole numbers at least 1 apart (the tuner's lab.snap)."""
    if x == 0:
        return x
    step = 5 * 10 ** (math.floor(math.log10(abs(x))) - 1)
    step = max(round(step), 1) if whole else step
    v = round(x / step) * step
    return int(round(v)) if step >= 1 else float(f"{v:.6g}")


def scaled(d, scale, whole=False):
    """A per-temperament table moved as one: each value times scale, back on the grid (whole numbers if whole: weights
    and percents). Scale 1 leaves it as it is."""
    if scale == 1:
        return dict(d)
    return {k: snap(v * scale, whole) for k, v in d.items()}


if __name__ == "__main__":
    _VALUES.update({"A": 2, "B": {"1": -3}})
    assert get("A", 1) == 2 and get("C", 5) == 5 and get("B", {1: 0, 2: 7}) == {1: -3, 2: 7}
    assert scaled({-1: 15, 0: 30, 1: 50}, 1.2, True) == {-1: 20, 0: 35, 1: 60} and scaled({0: 15}, 0.5, True) == {0: 8}
    assert scaled({"0": 8, "1": 9.5}, 1.1) == {"0": 9, "1": 10} and scaled({"0": 8}, 1.2) == {"0": 9.5}
    print("ok")
