"""Balance overrides from tools/tuning.json, written by the tuner (tools/tuner.py). Missing or empty file: defaults.

Constants read through get(name, default); the tuner finds them by that call and takes the default from the source."""
import json
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


if __name__ == "__main__":
    _VALUES.update({"A": 2, "B": {"1": -3}})
    assert get("A", 1) == 2 and get("C", 5) == 5 and get("B", {1: 0, 2: 7}) == {1: -3, 2: 7}
    print("ok")
