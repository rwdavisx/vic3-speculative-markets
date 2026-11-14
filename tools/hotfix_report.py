"""Read-only hotfix run audit; write JSON/text evidence, never change a build or a running game.

    py -3 -B tools/hotfix_report.py
    py -3 -B tools/hotfix_report.py runs/sweep_hotfix_1_0_paired_base runs/sweep_hotfix_1_0_paired_fixed
    py -3 -B tools/hotfix_report.py --self-test

Completed old-run error logs missing from the result directory are recovered from
the isolated userdir named by status.json. Reports go to runs/hotfix_1_0/reports/.
Running results are explicitly partial snapshots. GDP comes from PROBE, never SPEC.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import shutil
import statistics

import observe

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
REPORTS = RUNS / "hotfix_1_0/reports"
ACTIVE = {"running", "waiting"}
LINE = re.compile(r"\b(SPEC|PROBE) tag=(\S+) date=([A-Za-z]+ \d{1,2}, \d{4}) (.*)")
STAMP = re.compile(r"^\[\d\d:\d\d:\d\d\]")
MOD_PATH = re.compile(r"(?:common|events|gui|localization)[/\\][^\n]*?[/\\][^/\\\s:]*spec_[^/\\\s:]*", re.I)
MOD_NAME = re.compile(r"\b(?:je_|notification_|concept_)?spec_[A-Za-z0-9_.]+")
TEST_PATH = re.compile(r"(?:events|common)/[^\n]*zz_(?:spec_)?(?:hotfix|mechanics)_[^\s:]*\.txt", re.I)
METHOD = [
    "Descriptive observations from these saved worlds, not independent randomized replicates or statistical confidence intervals.",
    "Country identity uses observe.streams: a tag plus its monthly reporting cadence. Detected shared/colliding tags are excluded from paired cohorts in both arms; undetected tag reuse cannot be ruled out.",
    "Panic starts require adjacent 20-45 day reports changing 0 to 1. Already-active first observations and post-gap onsets are censored, not new starts.",
    "Paired metrics use the same tag/date observations inside the common window. Cohorts must appear within 45 days of both window edges; missing/annexed/ambiguous countries are excluded explicitly.",
    "GDP is read only from PROBE. Endpoint sums describe the matched cohort, not the whole world. A shared save filename identifies a paired start; the runner did not record its content hash.",
    "Error counts are complete timestamped records, not occurrences of spec_. A mod path anywhere in a script-error stack attributes it to a mod call chain, not necessarily its ultimate cause.",
    "Running logs are partial snapshots. A completed process status does not independently prove every requested date was reached; observed coverage is shown.",
]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def read_text(path, partial=False):
    if not path or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return text[:text.rfind("\n") + 1] if partial and not text.endswith("\n") else text


def distribution(values):
    values = sorted(x for x in values if x is not None)
    if not values:
        return None
    return {"n": len(values), "min": values[0], "p10": values[int((len(values) - 1) * .1)],
            "median": statistics.median(values), "mean": statistics.fmean(values),
            "p90": values[int((len(values) - 1) * .9)], "max": values[-1]}


def telemetry(text, kind):
    """Parse complete actual rows; remove exact repeats before inferring civil-war streams."""
    by_tag, seen, conflicts = defaultdict(list), set(), defaultdict(set)
    invalid, duplicates = 0, 0
    for line in text.splitlines():
        match = LINE.search(line)
        if not match or match[1] != kind:
            continue
        try:
            date = datetime.strptime(match[3], "%B %d, %Y").date()
        except ValueError:
            invalid += 1
            continue
        fields = dict(re.findall(r"(\w+)=([^\s]*)", match[4]))
        if number(fields.get("conf" if kind == "SPEC" else "gdp")) is None or (kind == "SPEC" and number(fields.get("panic")) not in (0, 1)):
            invalid += 1
            continue
        signature = (match[2], date, tuple(sorted(fields.items())))
        if signature in seen:
            duplicates += 1
            continue
        seen.add(signature)
        conflicts[(match[2], date)].add(signature)
        by_tag[match[2]].append({**fields, "when": match[3], "_date": date, "_tag": match[2]})
    streams, ambiguous = {}, {tag for (tag, _), rows in conflicts.items() if len(rows) > 1}
    for tag, rows in sorted(by_tag.items()):
        split = observe.streams(tag, sorted(rows, key=lambda r: r["_date"]))
        if len(split) > 1:
            ambiguous.add(tag)
        streams.update(split)
    return {"streams": streams, "ambiguous": ambiguous, "invalid_rows": invalid, "duplicate_rows": duplicates}


def date_bounds(streams):
    dates = [row["_date"] for rows in streams.values() for row in rows]
    return (min(dates), max(dates)) if dates else (None, None)


def spec_summary(streams):
    rows = [row for records in streams.values() for row in records]
    starts = left = right = gaps = gap_onsets = adjacent = 0
    for records in streams.values():
        records = sorted(records, key=lambda r: r["_date"])
        if not records:
            continue
        left += number(records[0].get("panic")) == 1
        right += number(records[-1].get("panic")) == 1
        for before, after in zip(records, records[1:]):
            previous, current = number(before.get("panic")), number(after.get("panic"))
            if 20 <= (after["_date"] - before["_date"]).days <= 45 and previous in (0, 1) and current in (0, 1):
                adjacent += 1
                starts += previous == 0 and current == 1
            else:
                gaps += 1
                gap_onsets += previous == 0 and current == 1
    confidence = [number(row.get("conf")) for row in rows]
    panic = [number(row.get("panic")) for row in rows if number(row.get("panic")) in (0, 1)]
    bounds = date_bounds(streams)
    return {"first_date": str(bounds[0]) if bounds[0] else None, "last_date": str(bounds[1]) if bounds[1] else None,
            "inferred_streams": len(streams), "observations": len(rows), "confidence": distribution(confidence),
            "confidence_outside_0_100": sum(x is not None and not 0 <= x <= 100 for x in confidence),
            "panic_observations": int(sum(panic)), "panic_observation_share": sum(panic) / len(panic) if panic else None,
            "mania_observations": sum(x is not None and x >= 80 for x in confidence),
            "confirmed_panic_starts": starts, "eligible_adjacent_transitions": adjacent,
            "left_censored_active_spells": left, "right_censored_active_spells": right,
            "nonadjacent_transitions": gaps, "uncertain_postgap_onsets": gap_onsets,
            "leverage": distribution([number(row.get("lev")) for row in rows]),
            "bad_debts": distribution([number(row.get("crunch")) for row in rows]),
            "trust": distribution([number(row.get("trust")) for row in rows]),
            "lending_standards": distribution([number(row.get("lax")) for row in rows])}


def error_records(text):
    records, current = [], []
    for line in text.splitlines():
        if STAMP.match(line) and current:
            records.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        records.append("\n".join(current))
    return [record.strip() for record in records if record.strip()]


def classify(record):
    own = bool(MOD_PATH.search(record) or MOD_NAME.search(record))
    if TEST_PATH.search(record.replace("\\", "/")):
        return "test_harness_script_errors"
    if ".metadata/metadata.json" in record.replace("\\", "/"):
        return "build_metadata_issues"
    if own and ("is set but is never used" in record or "is used but is never set" in record):
        return "mod_variable_load_warnings"
    if own and "is orphaned" in record:
        return "mod_orphaned_event_load_warnings"
    if own and "[jomini_scriptlists.cpp:" in record:
        return "mod_runtime_list_warnings"
    if "Script system error!" in record or "Script location:" in record:
        if "spec_hotfix_" in record or TEST_PATH.search(record.replace("\\", "/")):
            return "test_harness_script_errors"
        return "mod_script_errors" if own else "basegame_script_errors"
    return "mod_other_diagnostics" if own else "engine_or_basegame_other"


def error_summary(text):
    groups = defaultdict(dict)
    for record in error_records(text):
        category = classify(record)
        shape = re.sub(r"^\[\d\d:\d\d:\d\d\]", "", record)
        shape = re.sub(r":\d+", ":#", shape)
        entry = groups[category].setdefault(shape, {"count": 0, "example": record})
        entry["count"] += 1
    return {"counts": {name: sum(item["count"] for item in shapes.values()) for name, shapes in sorted(groups.items())},
            "groups": {name: sorted(shapes.values(), key=lambda x: (-x["count"], x["example"]))
                       for name, shapes in sorted(groups.items())}}


def error_chain(folder):
    """Oldest numbered rotation first, current file last. No claim that overwritten rotations survive."""
    found = []
    if folder and folder.is_dir():
        for path in folder.glob("error*.log"):
            match = re.fullmatch(r"error(?:\.(\d+))?\.log", path.name)
            if match:
                found.append((int(match[1] or 0), path))
    return [path for _, path in sorted(found, key=lambda item: -item[0])]


def load_run(session, name, status):
    folder = session / name
    meta_path = folder / "meta.json"
    meta = json.loads(read_text(meta_path)) if meta_path.is_file() else {}
    state = status.get("state", meta.get("status", "unknown"))
    partial = state in ACTIVE or state == "unknown"
    user = Path(status["user"]) if status.get("user") else None
    live_error = user / "error_mirror.log" if user and partial else None
    live_cumulative = bool(live_error and live_error.is_file())
    cumulative = bool(meta.get("error_log_cumulative")) or live_cumulative
    recovered = []
    user_logs = user / "logs" if user else None
    if not cumulative and not partial and folder.resolve().is_relative_to(RUNS.resolve()):
        for source in error_chain(user_logs):
            target = folder / source.name
            if not target.is_file():
                folder.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                recovered.append(str(target))
    error_sources = ([live_error] if live_cumulative else
                     [folder / "error.log"] if cumulative and (folder / "error.log").is_file()
                     else error_chain(user_logs) if partial else error_chain(folder))
    error_text = "\n".join(read_text(path, partial and path.name in ("error.log", "error_mirror.log")) for path in error_sources)
    capture_note = ("Runner's live cumulative error mirror; partial snapshot of a running process." if live_cumulative else
                    "Runner's cumulative error mirror (metadata marker present)." if cumulative else
                    "Available error.log and numbered rotations; earlier overwritten rotations cannot be ruled out. Counts are observed records, not a full-run zero-error guarantee.")
    mirror = user / "mirror.log" if user else None
    mirror_text = read_text(mirror, partial) if mirror and mirror.is_file() else ""
    spec_file, probe_file = folder / "telemetry.log", folder / "probe.log"
    spec = telemetry(read_text(spec_file) if spec_file.is_file() else mirror_text, "SPEC")
    probe = telemetry(read_text(probe_file) if probe_file.is_file() else mirror_text, "PROBE")
    summary = spec_summary(spec["streams"])
    probe_dates = date_bounds(probe["streams"])
    public = {"id": f"{session.name}/{name}", "folder": str(folder.resolve()), "state": state, "partial": partial,
              "build": status.get("build", meta.get("build")), "save": status.get("save", meta.get("save")),
              "reported_finish_date": meta.get("date", status.get("date")), "wall_minutes": meta.get("minutes"),
              "spec_source": str(spec_file if spec_file.is_file() else mirror) if spec_file.is_file() or mirror else None,
              "probe_source": str(probe_file if probe_file.is_file() else mirror) if probe_file.is_file() or mirror else None,
              "error_sources": [str(path) for path in error_sources], "recovered_error_logs": recovered,
              "error_log_present": bool(error_sources), "error_log_cumulative": cumulative,
              "error_capture_note": capture_note, "errors": error_summary(error_text), "spec": summary,
              "probe": {"observations": sum(map(len, probe["streams"].values())),
                        "first_date": str(probe_dates[0]) if probe_dates[0] else None,
                        "last_date": str(probe_dates[1]) if probe_dates[1] else None},
              "identity": {"ambiguous_spec_tags": sorted(spec["ambiguous"]), "ambiguous_probe_tags": sorted(probe["ambiguous"]),
                           "duplicate_spec_rows_removed": spec["duplicate_rows"], "duplicate_probe_rows_removed": probe["duplicate_rows"],
                           "invalid_spec_rows": spec["invalid_rows"], "invalid_probe_rows": probe["invalid_rows"]}}
    return {"public": public, "spec": spec, "probe": probe}


def paired(original, fixed):
    a, b = original["public"], fixed["public"]
    result = {"original": a["id"], "fixed": b["id"], "shared_save_name": a["save"],
              "partial": a["partial"] or b["partial"], "independent_replicates_claimed": 0}
    bounds = [date_bounds(run["spec"]["streams"]) for run in (original, fixed)]
    if any(first is None for first, _ in bounds):
        return {**result, "available": False, "reason": "One or both runs have no complete SPEC rows yet."}
    start, end = max(first for first, _ in bounds), min(last for _, last in bounds)
    if end < start:
        return {**result, "available": False, "reason": "No overlapping observed dates."}
    result.update(available=True, first_date=str(start), last_date=str(end))
    ambiguous = set().union(*(run[kind]["ambiguous"] for run in (original, fixed) for kind in ("spec", "probe")))
    candidates = original["spec"]["streams"].keys() & fixed["spec"]["streams"].keys()
    all_tags = {row["_tag"] for run in (original, fixed) for rows in run["spec"]["streams"].values() for row in rows}
    kept, dropped, aligned = [], {}, [{}, {}]
    for tag in sorted(candidates):
        if "#" in tag or tag in ambiguous:
            continue
        maps = [{r["_date"]: r for r in run["spec"]["streams"][tag] if start <= r["_date"] <= end}
                for run in (original, fixed)]
        dates = sorted(maps[0].keys() & maps[1].keys())
        if not dates or dates[0] > start + timedelta(days=45) or dates[-1] < end - timedelta(days=45):
            dropped[tag] = "missing a common observation near a window edge"
            continue
        kept.append(tag)
        for index in (0, 1):
            aligned[index][tag] = [maps[index][date] for date in dates]
    result["cohort"] = {"tags": kept, "n": len(kept), "excluded_ambiguous_tags": sorted(ambiguous & all_tags),
                        "excluded_noncommon_tags": sorted(all_tags - candidates - ambiguous), "excluded_edge_tags": dropped}
    result["original_spec"], result["fixed_spec"] = map(spec_summary, aligned)
    endpoints = []
    missing_probe = []
    for tag in kept:
        maps = [{r["_date"]: r for r in run["probe"]["streams"].get(tag, []) if start <= r["_date"] <= end}
                for run in (original, fixed)]
        dates = sorted(maps[0].keys() & maps[1].keys())
        if not dates or dates[0] > start + timedelta(days=45) or dates[-1] < end - timedelta(days=45):
            missing_probe.append(tag)
            continue
        first, last = dates[0], dates[-1]
        values = [number(maps[i][d].get("gdp")) for i in (0, 1) for d in (first, last)]
        if any(v is None or v <= 0 for v in values):
            missing_probe.append(tag)
            continue
        endpoints.append({"tag": tag, "first_date": str(first), "last_date": str(last),
                          "original_start_gdp": values[0], "original_end_gdp": values[1],
                          "fixed_start_gdp": values[2], "fixed_end_gdp": values[3],
                          "fixed_end_difference_pct": 100 * (values[3] / values[1] - 1)})
    result["probe_cohort"] = {"n": len(endpoints), "excluded_missing_or_nonpositive": missing_probe,
                              "endpoints": endpoints, "end_gdp_difference_pct": distribution([r["fixed_end_difference_pct"] for r in endpoints])}
    if endpoints:
        original_end = sum(r["original_end_gdp"] for r in endpoints)
        fixed_end = sum(r["fixed_end_gdp"] for r in endpoints)
        result["probe_cohort"].update(original_end_gdp_sum=original_end, fixed_end_gdp_sum=fixed_end,
                                      end_gdp_sum_difference_pct=100 * (fixed_end / original_end - 1))
    return result


def build_side(name):
    """Known build labels; test-only builds without a saved start remain unpaired."""
    words = set(re.split(r"[_-]+", (name or "").lower()))
    if "baseline" in words:
        return "original"
    if any(re.fullmatch(r"(?:fixed|final|release|verified)\d*", word) for word in words):
        return "fixed"
    return None


def build_report(paths):
    runs = []
    for path in paths:
        path = path.resolve()
        if (path / "status.json").is_file():
            status = json.loads(read_text(path / "status.json"))
            runs.extend(load_run(path, name, game) for name, game in sorted(status.get("games", {}).items()))
        elif (path / "meta.json").is_file():
            status = json.loads(read_text(path.parent / "status.json")) if (path.parent / "status.json").is_file() else {}
            runs.append(load_run(path.parent, path.name, status.get("games", {}).get(path.name, {})))
        else:
            raise ValueError(f"No sweep status.json or result meta.json at {path}")
    runs = list({run["public"]["id"]: run for run in runs}.values())
    groups = defaultdict(lambda: {"original": [], "fixed": []})
    for run in runs:
        public = run["public"]
        if not public["save"]:
            continue
        side = build_side(public["build"])
        if side:
            groups[public["save"]][side].append(run)
    # Never silently drop a later fixed build when one original control serves several hotfix revisions.
    # Reusing the control creates no additional independent saved world.
    comparisons = [paired(group["original"][min(index, len(group["original"]) - 1)], fixed)
                   for group in groups.values() if group["original"]
                   for index, fixed in enumerate(group["fixed"])]
    for comparison in comparisons:
        comparison["shared_original_control_uses"] = sum(p["original"] == comparison["original"] for p in comparisons)
    compared = {comparison[side] for comparison in comparisons for side in ("original", "fixed")}
    return {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "method_and_limits": METHOD,
            "runs": [run["public"] for run in runs], "paired_comparisons": comparisons,
            "paired_start_groups": sum(bool(group["original"] and group["fixed"]) for group in groups.values()),
            "unpaired_run_ids": sorted(run["public"]["id"] for run in runs if run["public"]["id"] not in compared),
            "unpaired_by_save": {name: {side: [run["public"]["id"] for run in group[side]] for side in group}
                                  for name, group in groups.items() if not group["original"] or not group["fixed"]}}


def render(report):
    lines = [f"Hotfix evidence snapshot: {report['generated_at_utc']}", ""]
    for run in report["runs"]:
        spec, counts = run["spec"], run["errors"]["counts"]
        lines += [f"{run['id']}: {run['state']}{' (PARTIAL)' if run['partial'] else ''}",
                  f"  Observed SPEC dates: {spec['first_date']} to {spec['last_date']}; {spec['observations']} rows, {spec['inferred_streams']} inferred streams."]
        if spec["confidence"]:
            conf = spec["confidence"]
            lines.append(f"  Confidence observed range {conf['min']:.3f}..{conf['max']:.3f}, median {conf['median']:.3f}; out-of-range rows {spec['confidence_outside_0_100']}.")
        lines += [f"  Panic: {spec['confirmed_panic_starts']} confirmed starts, {spec['panic_observations']} active rows; left/right-censored spells {spec['left_censored_active_spells']}/{spec['right_censored_active_spells']}; uncertain post-gap onsets {spec['uncertain_postgap_onsets']}.",
                  "  Error records: " + (", ".join(f"{key}={value}" for key, value in counts.items()) if run["error_log_present"] else "UNAVAILABLE (not zero)"),
                  f"  Capture: {run['error_capture_note']}",
                  f"  Shared/ambiguous SPEC tags: {', '.join(run['identity']['ambiguous_spec_tags']) or 'none detected'}."]
        for category in ("mod_script_errors", "mod_runtime_list_warnings", "test_harness_script_errors", "mod_other_diagnostics"):
            for item in run["errors"]["groups"].get(category, [])[:6]:
                example = " | ".join(line.strip() for line in item["example"].splitlines() if line.strip())
                lines.append(f"    {category} x{item['count']}: {example}")
        lines.append("")
    for pair in report["paired_comparisons"]:
        lines += [f"PAIR {pair['original']} -> {pair['fixed']}", f"  Shared saved start: {pair['shared_save_name']}; {'PARTIAL' if pair['partial'] else 'completed process snapshots'}."]
        if not pair["available"]:
            lines += [f"  {pair['reason']}", ""]
            continue
        cohort = pair["cohort"]
        a, b = pair["original_spec"], pair["fixed_spec"]
        lines += [f"  Common window {pair['first_date']} to {pair['last_date']}; {cohort['n']} unambiguous, edge-covered tags and {a['observations']} exact matched tag/date rows per arm.",
                  f"  Excluded: {len(cohort['excluded_ambiguous_tags'])} ambiguous, {len(cohort['excluded_noncommon_tags'])} noncommon, {len(cohort['excluded_edge_tags'])} lacking edge coverage.",
                  f"  Confirmed panic starts {a['confirmed_panic_starts']} -> {b['confirmed_panic_starts']}; active panic observations {a['panic_observations']} -> {b['panic_observations']}."]
        if a["confidence"] and b["confidence"]:
            lines.append(f"  Median confidence {a['confidence']['median']:.3f} -> {b['confidence']['median']:.3f}; observed ranges {a['confidence']['min']:.3f}..{a['confidence']['max']:.3f} -> {b['confidence']['min']:.3f}..{b['confidence']['max']:.3f}.")
        probe = pair["probe_cohort"]
        if probe["n"]:
            lines.append(f"  PROBE matched endpoint cohort ({probe['n']} tags): GDP sum {probe['original_end_gdp_sum']:,.0f} -> {probe['fixed_end_gdp_sum']:,.0f} ({probe['end_gdp_sum_difference_pct']:+.3f}%). This is a cohort sum, not world GDP.")
        lines += ["  One saved-world comparison; no independent-replicate or general balance claim.", ""]
    lines += ["Method and limits:"] + [f"- {line}" for line in report["method_and_limits"]]
    return "\n".join(lines) + "\n"


def self_test():
    assert build_side("baseline_log") == "original"
    assert all(build_side(name) == "fixed" for name in ("fixed_log", "final_log", "release_log", "release2_log", "verified_log"))
    assert build_side("unrelated_build") is None
    def line(day, panic, conf=50):
        return f"SPEC tag=AAA date={day} conf={conf} panic={panic} gdp=999"
    data = "\n".join([line("January 1, 1840", 1), line("January 31, 1840", 0), line("March 1, 1840", 1),
                       line("March 1, 1840", 1), line("April 1, 1840", 0), line("July 1, 1840", 1)])
    parsed = telemetry(data, "SPEC")
    summary = spec_summary(parsed["streams"])
    assert parsed["duplicate_rows"] == 1 and summary["confirmed_panic_starts"] == 1
    assert summary["left_censored_active_spells"] == 1 and summary["right_censored_active_spells"] == 1
    assert summary["uncertain_postgap_onsets"] == 1
    same_tag = "\n".join([line("January 1, 1840", 0), line("January 2, 1840", 1),
                           line("January 31, 1840", 0), line("February 1, 1840", 1)])
    assert telemetry(same_tag, "SPEC")["ambiguous"] == {"AAA"}
    errors = """[01:00:00][jomini_effect.cpp:1140]: Variable 'spec_gui' is set but is never used.
[01:00:01][jomini_script_system.cpp:247]: Script system error!
  Error: ordered_country effect [ Given max value was bigger than the list ]
  Script location: common/scripted_effects/spec_centre_effects.txt:3275
common/on_actions/spec_centre_on_actions.txt:6
[01:00:02][jomini_script_system.cpp:247]: Script system error!
  Script location: events/vanilla.txt:20
[01:00:03][jomini_script_system.cpp:247]: Script system error!
  Error: Invalid right side during comparison 'c'
  Script location: events/zz_hotfix_economy_events.txt:246
"""
    counts = error_summary(errors)["counts"]
    assert counts == {"basegame_script_errors": 1, "mod_script_errors": 1, "mod_variable_load_warnings": 1,
                      "test_harness_script_errors": 1}, counts
    assert telemetry("PROBE tag=AAA date=January 1, 1840 gdp=100 sol=10", "PROBE")["streams"]["AAA"][0]["gdp"] == "100"
    assert telemetry("SPEC tag=AAA date=January 1, 1840 conf=40", "SPEC")["invalid_rows"] == 1
    # Matched economic comparisons use PROBE GDP even though SPEC contains an unrelated gdp field.
    def run(name, gdp):
        spec = telemetry("\n".join([line("January 1, 1840", 0), line("January 31, 1840", 1)]), "SPEC")
        probe = telemetry(f"PROBE tag=AAA date=January 1, 1840 gdp=100 sol=10\nPROBE tag=AAA date=January 31, 1840 gdp={gdp} sol=10", "PROBE")
        return {"public": {"id": name, "save": "same_start", "partial": False}, "spec": spec, "probe": probe}
    comparison = paired(run("base", 200), run("fixed", 220))
    assert comparison["cohort"]["n"] == 1 and comparison["original_spec"]["confirmed_panic_starts"] == 1
    assert abs(comparison["probe_cohort"]["end_gdp_sum_difference_pct"] - 10) < 1e-8
    print("hotfix_report self-test passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", nargs="*", type=Path)
    parser.add_argument("--name", default="latest", help="Report filename stem under runs/hotfix_1_0/reports")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.name) or args.name in (".", ".."):
        parser.error("--name must be a plain filename stem")
    paths = args.folders or sorted(RUNS.glob("sweep_hotfix_1_0_*"))
    report = build_report(paths)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{args.name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REPORTS / f"{args.name}.txt").write_text(render(report), encoding="utf-8")
    print(render(report))
    print(f"Saved {REPORTS / (args.name + '.json')} and {REPORTS / (args.name + '.txt')}")


if __name__ == "__main__":
    main()
