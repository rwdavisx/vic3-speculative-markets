"""Fast development checks. Use --engine BETA_MOD for a single-boot mechanics batch."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import hotfix_testbed
import mechanics_testbed as mechanics
import probe
import rival_notification_testbed


ROOT = Path(__file__).resolve().parents[1]
# These fixtures initialize the values they assert and can share one disposable 1836 world.
IMMEDIATE = (
    "ai_policy", "all_goods_endings", "bank_display", "banking",
    "burst_accounting", "capital_flight", "confidence", "confidence_accounting",
    "construction", "credit_cycle", "economy", "exchange",
    "exchange_monthly", "goods", "interventions", "journal",
    "output_baskets", "politics", "pursuit_weights", "renown_reach",
    "rival_notifications", "technology", "finance_priority", "player_feedback",
)


def local_checks(source):
    commands = {
        "Python": ["-m", "unittest", "discover", "-s", "tests"],
        "Generated mod": ["tools/check.py"],
        "CMF": ["-m", "unittest", "discover", "-s", "compatibility/cmf", "-p", "test_build.py"],
    }

    def run(item):
        name, args = item
        started = time.monotonic()
        env = os.environ.copy()
        if name == "Generated mod":
            env["SPEC_MOD_OUT"] = str(source)
        elif name == "CMF":
            env["SPEC_CMF_TEST_PARENT"] = str(source)
        result = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, text=True, errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        return name, result, time.monotonic() - started

    ok = True
    with ThreadPoolExecutor(max_workers=len(commands)) as pool:
        for name, result, elapsed in pool.map(run, commands.items()):
            print(f"{name}: {'FAIL' if result.returncode else 'PASS'} ({elapsed:.1f}s)", flush=True)
            if result.returncode:
                print(result.stdout)
                ok = False
    return ok


def immediate_cases():
    # Additional standalone cases can be selected individually when diagnosing a mechanic.
    individual = (
        "ai_frequency", "capitulation", "cashflow", "contagion", "crisis_overlap",
        "depression", "depression_options", "depression_pops", "depression_social",
        "panic", "pledge_cash", "renown_score", "rival_ai", "rival_bounds", "rival_choose",
        "review_120", "investor_sentiment", "rival_large_network", "rival_network", "rival_points", "rival_press", "rival_put", "rival_year", "standing",
    )
    available = []
    for case in sorted((*IMMEDIATE, *individual)):
        fixture = ROOT / "tests/mechanics" / f"{case}.txt"
        script = fixture.read_text(encoding="utf-8-sig")
        events = re.findall(r"(?m)^\s*(spec_mechanics_\w+\.\d+)\s*=", script)
        if (events == [f"spec_mechanics_{case}.1"]
                and not re.search(r"trigger_event\s*=\s*\{[^}]*\bdays\s*=", script)
                and not fixture.with_suffix(".on_actions.txt").exists()
                and not fixture.with_suffix(".static_modifiers.txt").exists()):
            available.append(case)
    return available


def prepare_batch(source, dest, cases):
    if json.loads((source / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))["id"] != "speculative_markets_beta":
        raise ValueError("Engine fixtures require a beta build.")
    shutil.copytree(source, dest)
    for name, content in probe.files().items():
        (dest / name).write_text(content, encoding="utf-8-sig")
    expected = []
    helpers = []
    for case in cases:
        _, script, names = mechanics.fixture_contract(case)
        rules, snippets = mechanics.fixture_helpers(source, case)
        # Shared helper names may refer to different blocks in different suites.
        helper_text = "".join(snippets)
        if case == "rival_notifications":
            helper_text = rival_notification_testbed.instrument(helper_text)
        for key in sorted(rules, key=len, reverse=True):
            pattern = rf"\b{re.escape(key)}(?=\s*=\s*(?:yes\b|\{{))"
            script = re.sub(pattern, f"{key}_{case}", script)
            helper_text = re.sub(pattern, f"{key}_{case}", helper_text)
        helpers.append(helper_text)
        script = re.sub(r'"HOTFIX (PASS|FAIL) (\w+)"', rf'"HOTFIX \1 {case}__\2"', script)
        script = script.replace('"HOTFIX SUITE COMPLETE"', f'"HOTFIX COMPLETE {case}"')
        (dest / "events" / f"zz_fast_{case}.txt").write_text(script, encoding="utf-8-sig")
        expected.extend(f"{case}__{name}" for name in names)
    (dest / "common/scripted_effects/zz_fast_helpers.txt").write_text("".join(helpers), encoding="utf-8-sig")
    calls = "\n".join(f"        trigger_event = {{ id = spec_mechanics_{case}.1 }}" for case in cases)
    (dest / "common/on_actions/zz_fast_start.txt").write_text(
        """on_monthly_pulse_country = { on_actions = { spec_fast_batch } }
spec_fast_batch = {
    trigger = { c:GBR ?= this has_variable = spec_conf NOT = { has_variable = spec_fast_started } }
    effect = {
        set_variable = spec_fast_started
""" + calls + "\n    }\n}\n", encoding="utf-8-sig")
    return expected


def engine_batch(source, cases):
    import sweep
    stamp = "quick_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    dest = ROOT / "runs" / stamp / "mod"
    expected = prepare_batch(source, dest, cases)
    # A month is enough to initialize Finance and enter the dispatcher.
    sweep.run(stamp, {"test": str(dest)}, 1, "1836.2.10", 1, timeout=4)
    evidence = ROOT / "runs" / f"sweep_{stamp}" / "test_01"
    assertions = evidence / "assertions.log"
    log = assertions.read_text(encoding="utf-8") if assertions.is_file() else ""
    results = hotfix_testbed.RESULT.findall(log)
    failed = [name for result, name in results if result == "FAIL"]
    passed = Counter(name for result, name in results if result == "PASS")
    completed = Counter(re.findall(r"HOTFIX COMPLETE (\w+)", log))
    error_log = evidence / "error.log"
    errors = hotfix_testbed.check_error_logs([error_log]) if error_log.is_file() else {"blocking_error_count": None}
    meta = json.loads((evidence / "meta.json").read_text())
    ok = (meta["status"] == "done" and not failed and passed == Counter(expected)
          and completed == Counter(cases) and errors["blocking_error_count"] == 0)
    report = {"passed": ok, "source": str(source), "source_version": json.loads((source / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))["version"],
              "cases": cases, "assertions_passed": sum(passed.values()), "failed": failed,
              "missing": list((Counter(expected) - passed).elements()), "completions": dict(completed),
              "error_gate": errors, "game_status": meta["status"], "evidence": str(evidence)}
    path = dest.parent / "report.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"One game: {sum(passed.values())}/{len(expected)} assertions; {'PASS' if ok else 'FAIL'}. {path}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "mod", help="Generated stable layout for static checks")
    parser.add_argument("--engine", type=Path, metavar="BETA_MOD", help="Also check immediate mechanics in one game")
    parser.add_argument("--cases", nargs="+", choices=immediate_cases(), help="Run selected immediate cases in one disposable world; the default group is tested together")
    args = parser.parse_args()
    if args.cases and (not args.engine or len(args.cases) != len(set(args.cases))):
        parser.error("--cases requires --engine and distinct case names")
    started = time.monotonic()
    ok = local_checks(args.source.resolve())
    if ok and args.engine:
        ok = engine_batch(args.engine.resolve(), args.cases or IMMEDIATE)
    print(f"Elapsed {time.monotonic() - started:.1f}s", flush=True)
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
