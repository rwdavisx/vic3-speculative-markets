"""Prepare an isolated Victoria 3 debug build with automatic hotfix regressions.

    py -3 -B tools/hotfix_testbed.py --out runs/hotfix_1_0/scenarios_log
    py -3 -B tools/hotfix_testbed.py --report path/to/debug.log --error-log path/to/error.log

Preparation never launches the game. Run the resulting build in a disposable
1836 observer game until at least April 1836. The harness changes Britain's laws,
market variables and modifiers; its output must never be published.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNS = (ROOT / "runs").resolve()
DEFAULT_OUT = RUNS / "hotfix_1_0/scenarios_log"
MANIFEST = "hotfix-test-manifest.json"
KIND = "speculative-markets-isolated-hotfix-tests"
RESULT = re.compile(r"\bHOTFIX (PASS|FAIL) ([A-Za-z0-9_]+)\b")
DEFINITION = re.compile(r"^(spec_hotfix_[A-Za-z0-9_]+\.\d+)\s*=\s*\{", re.M)
CORE_EXPECTED = [
    "panic_minimum", "panic_recovery", "shutdown_relief", "legacy_relief",
]


def destination(path):
    """No release tree, runs root, outside path, or redirected child is writable."""
    out = Path(path)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    if not out.is_relative_to(RUNS) or out == RUNS:
        raise ValueError("Test output must be a strict child of this workspace's runs/ directory")
    if out.exists():
        if not out.is_dir():
            raise ValueError(f"Test output is not a directory: {out}")
        existing = list(out.iterdir())
        marker = out / MANIFEST
        if existing and (not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")).get("kind") != KIND):
            raise ValueError(f"Refusing to overwrite an unrecognized nonempty directory: {out}")
        for child in out.rglob("*"):
            if not child.resolve().is_relative_to(out):
                raise ValueError(f"Test output contains a path redirected outside its directory: {child}")
    return out


def event(number, body):
    lines = "\n".join("\t\t" + line for line in body.strip().splitlines())
    return f"spec_hotfix_core.{number} = {{\n\ttype = country_event\n\thidden = yes\n\timmediate = {{\n{lines}\n\t}}\n}}\n\n"


def assertion(name, condition):
    return (
        "if = {\n\tlimit = {\n"
        + "\n".join("\t\t" + line for line in condition.strip().splitlines())
        + f'\n\t}}\n\tdebug_log = "HOTFIX PASS {name}"\n}}\n'
        + f'else = {{ debug_log = "HOTFIX FAIL {name}" }}\n'
    )


def schedule(event_id, days=1):
    return f"trigger_event = {{ id = {event_id} days = {days} }}\n"


def core_events(economy_ids, journal_ids, diplomacy_ids=()):
    # Each dispatched test is followed by a new wrapper one day later, so an engine
    # event queue cannot reorder a destructive test ahead of its predecessor.
    extra = ""
    next_number = 20

    def chain(ids, final):
        nonlocal extra, next_number
        if not ids:
            return final
        first = f"spec_hotfix_core.{next_number}"
        for index, event_id in enumerate(ids):
            current = next_number
            next_number += 1
            following = f"spec_hotfix_core.{next_number}" if index + 1 < len(ids) else final
            extra += event(current, f"trigger_event = {{ id = {event_id} }}\n" + schedule(following))
        return first

    economy_start = chain([*economy_ids, *diplomacy_ids], "spec_hotfix_core.1")
    journal_start = chain(journal_ids, "spec_hotfix_core.99")
    monthly = "trigger_event = { on_action = spec_monthly }\n"
    body = "namespace = spec_hotfix_core\n\n"
    body += event(1, """
activate_law = law_type:law_interventionism
if = {
    limit = { NOT = { has_technology_researched = central_banking } }
    add_technology_researched = central_banking
}
remove_variable = spec_llr
remove_variable = spec_rescued
set_variable = { name = spec_conf value = 55 }
set_variable = { name = spec_debt value = 0 }
set_variable = { name = spec_c_total value = 0 }
spec_start_panic = yes
set_variable = { name = spec_panic value = 6 }
set_variable = { name = spec_panic_len value = 6 }
set_variable = { name = spec_panic_elapsed value = 0 }
spec_rescue = yes
set_variable = { name = spec_conf value = 80 }
""" + monthly + schedule("spec_hotfix_core.2"))
    body += event(2, assertion("panic_minimum", """
has_variable = spec_panic
spec_panic_run = 1
""") + "set_variable = { name = spec_conf value = 80 }\n" + monthly + schedule("spec_hotfix_core.3"))
    body += event(3, assertion("panic_recovery", """
NOR = {
    has_variable = spec_panic
    has_modifier = spec_panic
    has_modifier = spec_panic_crunch
    has_modifier = spec_panic_relief
}
""") + """
set_variable = { name = spec_conf value = 55 }
spec_start_panic = yes
activate_law = law_type:law_command_economy
""" + monthly + schedule("spec_hotfix_core.4"))
    body += event(4, assertion("shutdown_relief", """
NOR = {
    has_variable = spec_conf
    has_variable = spec_panic
    has_modifier = spec_panic
    has_modifier = spec_panic_crunch
    has_modifier = spec_panic_relief
}
""") + """
remove_variable = spec_conf
add_modifier = { name = spec_panic_relief multiplier = 100 }
""" + monthly + schedule("spec_hotfix_core.5"))
    body += event(5, assertion("legacy_relief", """
NOR = {
    has_variable = spec_conf
    has_modifier = spec_panic_relief
}
""") + schedule(journal_start))
    body += event(99, 'set_variable = spec_hotfix_done\ndebug_log = "HOTFIX SUITE COMPLETE"')
    body += extra
    actions = f"""# TEST BUILD ONLY: one run on initialized Britain, a day after a natural monthly pulse.
on_monthly_pulse_country = {{
    on_actions = {{ spec_hotfix_start }}
}}

spec_hotfix_start = {{
    trigger = {{
        c:GBR ?= this
        has_variable = spec_conf
        NOT = {{ has_variable = spec_hotfix_started }}
    }}
    effect = {{
        set_variable = spec_hotfix_started
        debug_log = "HOTFIX SUITE START"
        {schedule(economy_start).strip()}
    }}
}}
"""
    return body, actions


def cases():
    """Read dedicated engine tests without importing the production generator."""
    files = []
    for filename, required in (("hotfix_economy_events.txt", False), ("hotfix_diplomacy_events.txt", False),
                               ("hotfix_journal_events.txt", True)):
        source = ROOT / "tests" / filename
        if not source.exists():
            if required:
                raise ValueError(f"Required engine cases are missing: {source}")
            continue
        text = source.read_text(encoding="utf-8-sig")
        ids = DEFINITION.findall(text)
        if not ids:
            raise ValueError(f"No hidden regression events found: {source}")
        expected = sorted({name for status, name in RESULT.findall(text) if status == "PASS"})
        if not expected:
            raise ValueError(f"No PASS assertions found: {source}")
        files.append({"source": source, "text": text, "ids": ids, "expected": expected})
    return files


def prepare(path):
    out = destination(path)
    suites = cases()
    economy_ids = [event_id for suite in suites if "economy" in suite["source"].name for event_id in suite["ids"]]
    diplomacy_ids = [event_id for suite in suites if "diplomacy" in suite["source"].name for event_id in suite["ids"]]
    journal_ids = [event_id for suite in suites if "journal" in suite["source"].name for event_id in suite["ids"]]
    core, actions = core_events(economy_ids, journal_ids, diplomacy_ids)
    expected = CORE_EXPECTED + [name for suite in suites for name in suite["expected"]]
    if len(expected) != len(set(expected)):
        raise ValueError("Regression assertion names must be unique across suites")
    manifest = {
        "kind": KIND, "status": "preparing", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "output": str(out), "expected_assertions": expected,
        "event_order": economy_ids + diplomacy_ids + [f"spec_hotfix_core.{n}" for n in range(1, 6)] + journal_ids,
        "included_case_files": [str(suite["source"].relative_to(ROOT)) for suite in suites],
        "warning": "Disposable engine-test build: changes Britain, never publish.",
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*sorted((ROOT / "tools").glob("*.py")), *(suite["source"] for suite in suites)]
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    marker = out / MANIFEST
    marker.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    env = {**os.environ, "SPEC_MOD_OUT": str(out), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/generate.py"), "--log"], cwd=ROOT, env=env)
    if result.returncode:
        manifest["status"] = "build_failed"
        marker.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"Debug generator exited {result.returncode}; no game was launched")
    # Write tests only after generation, which removes stale files in generated directories.
    (out / "events/zz_spec_hotfix_core.txt").write_text(core, encoding="utf-8-sig")
    (out / "common/on_actions/zz_spec_hotfix_start.txt").write_text(actions, encoding="utf-8-sig")
    for suite in suites:
        # Engine script files require a BOM even when their repository fixtures do not have one.
        (out / "events" / ("zz_" + suite["source"].name)).write_text(suite["text"], encoding="utf-8-sig")
    if any("spec_hotfix_update_seat" in suite["text"] for suite in suites):
        # Exercise the exact production seat update on an annexed country. The normal
        # world ranking visits active countries and cannot supply that edge-case scope.
        import centres
        helper = "spec_hotfix_update_seat = {\n" + centres._seat("\t") + "}\n"
        helper_path = "common/scripted_effects/zz_spec_hotfix_helpers.txt"
        (out / helper_path).write_text(helper, encoding="utf-8-sig")
        manifest["generated_test_helpers"] = [helper_path]
    manifest["status"] = "prepared"
    marker.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {out}")
    print(f"Expected {len(expected)} assertions: {', '.join(expected)}")
    print("No game launched. Run this build in an isolated 1836 observer game through April 1836.")
    return 0


def check_error_logs(logs):
    """Inspect complete error records, including their stacks, without loading telemetry."""
    from hotfix_report import classify, error_records

    blocking_categories = {
        "mod_script_errors", "mod_runtime_list_warnings",
        "test_harness_script_errors", "mod_other_diagnostics",
    }
    text = "\n".join(Path(log).read_text(encoding="utf-8-sig", errors="replace") for log in logs)
    counts, blocking = Counter(), []
    for record in error_records(text):
        category = classify(record)
        # Direct fixture failures may name only zz_hotfix_*.txt, whereas ordinary
        # mod effects and the generated core harness use the spec_ prefix.
        fixture = re.search(r"(?:events|common)/[^\n]*zz_(?:spec_)?hotfix_[^\s:]*\.txt", record.replace("\\", "/"))
        if fixture and ("Script system error!" in record or "Script location:" in record or "[jomini_scriptlists.cpp:" in record):
            category = "test_harness_script_errors"
        counts[category] += 1
        if category in blocking_categories:
            blocking.append({"category": category, "record": record})
    return {
        "error_logs_checked": [str(log) for log in logs],
        "error_categories": dict(sorted(counts.items())),
        "blocking_error_count": len(blocking),
        "blocking_error_examples": blocking[:5],
    }


def report(path, logs, error_logs=()):
    out = destination(path)
    manifest = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    text = "\n".join(Path(log).read_text(encoding="utf-8-sig", errors="replace") for log in logs)
    found = RESULT.findall(text)
    passed = {name for status, name in found if status == "PASS"}
    failed = {name for status, name in found if status == "FAIL"}
    missing = set(manifest["expected_assertions"]) - passed - failed
    complete = "HOTFIX SUITE COMPLETE" in text
    result = {"passed": sorted(passed), "failed": sorted(failed), "missing": sorted(missing), "suite_complete": complete}
    errors = check_error_logs(error_logs) if error_logs else {"error_logs_checked": [], "blocking_error_count": 0}
    result.update(errors)
    print(json.dumps(result, indent=2))
    return 1 if failed or missing or not complete or errors["blocking_error_count"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Isolated output under workspace/runs/")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare the build (the default; never launches a game)")
    parser.add_argument("--report", type=Path, nargs="+", metavar="LOG", help="Read logs and fail on missing/failed assertions")
    parser.add_argument("--error-log", type=Path, nargs="+", default=[], metavar="LOG",
                        help="With --report, also fail on mod/harness runtime errors and unrecognized mod diagnostics")
    args = parser.parse_args(argv)
    if args.error_log and not args.report:
        parser.error("--error-log requires --report")
    try:
        return report(args.out, args.report, args.error_log) if args.report else prepare(args.out)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
