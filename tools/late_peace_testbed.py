"""Instrument a disposable beta for the manual late-peace integration test."""
import argparse
import json
from pathlib import Path

import mechanics_testbed as testbed


def prepare(source, out):
    testbed.prepare(source, out, "late_peace")
    target = out / "common/scripted_effects/spec_diplomacy_effects.txt"
    original = target.read_text(encoding="utf-8-sig")
    marker = "spec_war_jump = {"
    if original.count(marker) != 1:
        raise ValueError("Expected exactly one production war-jump definition")
    # Preserve the full production body; count calls before delegating to it.
    target.write_text(original.replace(marker, "spec_mechanics_original_war_jump = {", 1) + '''
spec_war_jump = {
if = { limit = { has_variable = spec_test_war_tracking }
change_variable = { name = spec_test_jump_count add = 1 }
set_variable = { name = spec_test_last_jump value = var:spec_war_end }
}
spec_mechanics_original_war_jump = yes
}
''', encoding="utf-8-sig")
    manifest = out / "mechanics-test-manifest.json"
    data = json.loads(manifest.read_text())
    data["war_jump_instrumented_sha256"] = testbed.digest(target)
    data["manual_steps"] = "Play GBR. After the first monthly test start, wait for READY TO CAPITULATE PRU, switch to PRU and capitulate through the native war UI. Wait for READY TO CAPITULATE FRA, switch to FRA and capitulate. Advance at least three days, then report the full logs. Never retrigger the setup in the same game."
    manifest.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source.resolve(), args.out.resolve())
