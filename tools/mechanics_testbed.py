"""Run hand-specified mechanic contracts against a disposable copy of beta.

Prepare one suite per fresh game, then run it with sweep.py. No assertions or
test helpers are installed into beta/mod or mod. See MECHANICS_AUDIT.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import hotfix_testbed
import probe

ROOT = Path(__file__).resolve().parents[1]
KIND = "speculative-markets-mechanic-contracts"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, out, suite):
    source, out = source.resolve(), out.resolve()
    if not out.is_relative_to(ROOT / "runs") or out == ROOT / "runs":
        raise ValueError("Test builds must be a new child of runs/")
    if out.exists():
        raise ValueError("Use a new test directory; previous evidence is immutable")
    metadata = json.loads((source / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))
    if metadata["id"] != "speculative_markets_beta":
        raise ValueError("Mechanics tests require the beta distribution")
    fixture = ROOT / "tests/mechanics" / f"{suite}.txt"
    script = fixture.read_text(encoding="utf-8-sig")
    expected = re.findall(r'"HOTFIX PASS (\w+)"', script)
    failures = re.findall(r'"HOTFIX FAIL (\w+)"', script)
    if not expected or len(expected) != len(set(expected)) or sorted(expected) != sorted(failures):
        raise ValueError("Every assertion needs one uniquely named PASS and FAIL branch")
    if "HOTFIX SUITE COMPLETE" not in script:
        raise ValueError("Suite must explicitly complete")
    markers = re.findall(r'"(HOTFIX (?:PASS|FAIL)[^"\n]*)"', script)
    if any(not re.fullmatch(r"HOTFIX (?:PASS|FAIL) \w+", marker) for marker in markers):
        raise ValueError("Malformed assertion marker")
    # Capture source hashes before copying; no regenerated production substitute.
    hashes = {p.relative_to(source).as_posix(): digest(p) for p in sorted(source.rglob("*")) if p.is_file()}
    shutil.copytree(source, out)
    for rel, content in probe.files().items():
        (out / rel).write_text(content, encoding="utf-8-sig")
    (out / "events/zz_spec_mechanics_tests.txt").write_text(script, encoding="utf-8-sig")
    action = f'''on_monthly_pulse_country = {{ on_actions = {{ spec_mechanics_start }} }}
spec_mechanics_start = {{
    trigger = {{ c:GBR ?= this has_variable = spec_conf NOT = {{ has_variable = spec_mechanics_started }} }}
    effect = {{
        set_variable = spec_mechanics_started
        debug_log = "HOTFIX SUITE START"
        trigger_event = {{ id = spec_mechanics_{suite}.1 days = 1 }}
    }}
}}
'''
    (out / "common/on_actions/zz_spec_mechanics_start.txt").write_text(action, encoding="utf-8-sig")
    # Helpers only expose otherwise embedded production blocks. Read the actual
    # beta files, never a second implementation of a mechanic.
    helper_file = ROOT / "tests/mechanics" / f"{suite}.helpers.json"
    helpers = {}
    helper_text = []
    if helper_file.exists():
        for name, spec in json.loads(helper_file.read_text()).items():
            original = (source / spec["path"]).read_text(encoding="utf-8-sig")
            if original.count(spec["start"]) != 1 or original.count(spec["end"]) != 1:
                raise ValueError(f"Ambiguous production helper boundary: {name}")
            snippet = original.split(spec["start"], 1)[1].split(spec["end"], 1)[0]
            if snippet.count("{") != snippet.count("}"):
                raise ValueError(f"Helper must contain complete production blocks: {name}")
            helpers[name] = {**spec, "sha256": hashlib.sha256(snippet.encode()).hexdigest()}
            helper_text.append(f"{name} = {{\n{snippet}\n}}\n")
    if helper_text:
        (out / "common/scripted_effects/zz_spec_mechanics_helpers.txt").write_text("".join(helper_text), encoding="utf-8-sig")
    manifest = {"kind": KIND, "suite": suite, "source": str(source), "source_version": metadata["version"],
                "expected_assertions": expected, "source_sha256": hashes, "fixture_sha256": digest(fixture),
                "helpers": helpers, "warning": "TEST ONLY. Never package or upload this build."}
    (out / "mechanics-test-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {suite}: {len(expected)} assertions in {out}")


def report(out, logs, errors):
    manifest = json.loads((out / "mechanics-test-manifest.json").read_text())
    text = "\n".join(p.read_text(encoding="utf-8-sig", errors="replace") for p in logs)
    results = hotfix_testbed.RESULT.findall(text)
    passed = {name for status, name in results if status == "PASS"}
    failed = {name for status, name in results if status == "FAIL"}
    expected = set(manifest["expected_assertions"])
    result = {"suite": manifest["suite"], "passed": sorted(passed), "failed": sorted(failed),
              "missing": sorted(expected - passed - failed), "unexpected": sorted((passed | failed) - expected),
              "complete": "HOTFIX SUITE COMPLETE" in text,
              **hotfix_testbed.check_error_logs(errors)}
    print(json.dumps(result, indent=2))
    return int(bool(failed or result["missing"] or result["unexpected"] or not result["complete"] or result["blocking_error_count"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "beta/mod")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--suite")
    parser.add_argument("--report", type=Path, nargs="+")
    parser.add_argument("--error-log", type=Path, nargs="+")
    args = parser.parse_args()
    if args.report:
        if not args.error_log:
            parser.error("Reports require cumulative error logs, not just PASS markers")
        return report(args.out, args.report, args.error_log)
    if not args.suite or not re.fullmatch(r"[a-z_]+", args.suite):
        parser.error("Choose a named suite from tests/mechanics")
    prepare(args.source, args.out, args.suite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
