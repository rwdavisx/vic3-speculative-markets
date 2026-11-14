"""Reads Sovereign Debt test games for the tuner's Debt tab. Read-only, stdlib only.

Each test is a folder under runs/debt/ holding lines.log (the game's SDT log lines) and meta.json (title, summary,
findings). Run this file for its self-test.
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs" / "debt"
LINE = re.compile(r"\b(SDTW|SDT_STEP|SDT_HOOK|SDT) (.*)$")
SCORE_LINE = re.compile(r"\b(SD_EVENT|SD_WORLD) (.*)$")
FIELD = re.compile(r"(\w+)=(.*?)(?= \w+=|$)")
TARGET_ACTIVE, TARGET_YEAR, MAX_LENDER_SHARE = 10, 1860, 0.5
TEXT_FIELDS = {"country", "date"}
NO_LOANS_BY, MIN_LOANS_TO_JUDGE = "1838", 10
CIVIL_WAR_SIDES = {"Carlist Spain"}  # starts 1836 losing a war, so its default says nothing about loan tuning
GAME_START = "1836-01-01"  # on_country_no_longer_default fires for every country here, which means nothing


def _iso(date):
    return datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d")


def _row(fields):
    row = {k: v if k in TEXT_FIELDS or not v else float(v) for k, v in fields.items()}
    row["date"] = _iso(row["date"])
    if "position" not in row and "gold" in row and "principal" in row:
        row["position"] = row["gold"] - row["principal"]
    return row


def parse(lines):
    """Returns monthly and weekly rows by country, and the dated steps and hooks, from raw log lines."""
    monthly, weekly, events = {}, {}, set()
    for line in lines:
        found = LINE.search(line)
        # A line still holding [ is the game echoing the unfilled log string, not a result
        if not found or "[" in found.group(2):
            continue
        kind, rest = found.groups()
        fields = dict(FIELD.findall(rest))
        if "date" not in fields:
            continue
        if kind in ("SDT", "SDTW"):
            rows = monthly if kind == "SDT" else weekly
            rows.setdefault(fields["country"], []).append(_row(fields))
            continue
        date = _iso(fields["date"])
        text = rest.split(" date=")[0].replace(" country=", ": ")
        if date != GAME_START:
            events.add((date, "step" if kind == "SDT_STEP" else "hook", text))
    for rows in (*monthly.values(), *weekly.values()):
        rows.sort(key=lambda r: r["date"])
    return {"monthly": monthly, "weekly": weekly,
            "events": [{"date": d, "kind": k, "text": t} for d, k, t in sorted(events)]}


def scorecard(lines):
    """Judges a Sovereign Debt game against the targets: returns the verdict, tiles and findings the Debt tab shows."""
    kinds, lenders, active, payments, in_crisis = Counter(), Counter(), [], (0, 0), set()
    for line in lines:
        found = SCORE_LINE.search(line)
        if not found or "[" in found.group(2):
            continue
        fields = dict(FIELD.findall(found.group(2)))
        if found.group(1) == "SD_WORLD":
            active.append((_iso(fields["date"]), int(float(fields["active"]))))
            payments = (float(fields.get("due", 0)), float(fields.get("running", 0)))
            continue
        kinds[fields["kind"]] += 1
        if fields["kind"] == "crisis" and fields["borrower"] not in CIVIL_WAR_SIDES and "Revolt" not in fields["borrower"]:
            in_crisis.add(fields["borrower"])
        if fields["kind"] == "loan":
            lenders[fields["lender"]] += 1

    loans = kinds["loan"]
    reached = active[-1][0][:4] if active else "the start"
    by_target = max((n for d, n in active if d < f"{TARGET_YEAR + 1}"), default=0)
    top, top_loans = lenders.most_common(1)[0] if lenders else ("nobody", 0)
    share = top_loans / loans if loans else 0
    target_seen = bool(active) and reached >= str(TARGET_YEAR)

    findings = [
        {"say": f"{by_target} loans active at once, target {TARGET_ACTIVE} by {TARGET_YEAR}",
         "tone": "good" if by_target >= TARGET_ACTIVE else "bad" if target_seen else "warn",
         "why": f"The game reached {reached}."},
        {"say": f"{kinds['repaid']} loans repaid", "tone": "good" if kinds["repaid"] else "warn", "why": "Some loans should end well."},
        {"say": f"{len(in_crisis)} established countries hit a crisis", "tone": "good" if in_crisis else "warn",
         "why": f"Some loans should end in crisis. {kinds['crisis']} crisis events in all, counting repeats and civil war sides."},
        {"say": f"{top} made {share:.0%} of all loans", "tone": "good" if share <= MAX_LENDER_SHARE else "bad",
         "why": f"No single lender should hold more than {MAX_LENDER_SHARE:.0%}."},
        {"say": f"{kinds['lender_default']} lenders defaulted", "tone": "warn" if kinds["lender_default"] else "good",
         "why": "Lending should not be what breaks a great power."},
    ]
    due, running = payments
    if due:
        findings.insert(0, {"say": f"Treaties carry {running / due:.0%} of the payments the loans expect",
                            "tone": "good" if abs(running - due) <= due * 0.01 else "bad",
                            "why": f"Latest count: {running:,.0f} a week running against {due:,.0f} due."})
    failed = [f for f in findings if f["tone"] != "good"]
    return {
        "verdict": "On target." if not failed else f"Not there yet: {failed[0]['say']}.",
        "tone": "good" if not failed else "bad" if any(f["tone"] == "bad" for f in failed) else "warn",
        "findings": findings,
        "tiles": [["Loans made", loans, f"by {len(lenders)} lenders"],
                  ["Active now", active[-1][1] if active else 0, f"goal: {TARGET_ACTIVE} by {TARGET_YEAR}"],
                  ["Repaid", kinds["repaid"], f"{kinds['repaid'] / loans:.0%} of loans" if loans else "no loans yet"],
                  ["Countries in crisis", len(in_crisis), f"{kinds['crisis']} crisis events in all"],
                  ["Repudiated", kinds["repudiated"], "refused to pay at all"]],
        "active": active,
        "goal": TARGET_ACTIVE,
        "outcomes": [["Repaid in full", kinds["repaid"]], ["Hit a crisis", kinds["crisis"]], ["Kept paying after a crisis", kinds["kept_paying"]],
                     ["Repudiated", kinds["repudiated"]], ["Treaty ended early", kinds["lost"]]],
        "lenders": lenders.most_common(8),
    }


def stop_reason(lines, errors):
    """Says why a running game has already failed, or None while it is still worth watching."""
    if errors:
        return f"{len(errors)} script errors from the mod"
    card = scorecard(lines)
    loans = card["tiles"][0][1]
    if not loans:
        return f"No loans by {NO_LOANS_BY}" if card["active"] and card["active"][-1][0] >= NO_LOANS_BY else None
    failed = [f["say"] for f in card["findings"] if f["tone"] == "bad"]
    return failed[0] if failed and loans >= MIN_LOANS_TO_JUDGE else None


def rescore(name, meta=None):
    """Refreshes a test's saved scorecard from its log, using the given title and game details or the saved ones."""
    path = RUNS / name / "meta.json"
    meta = meta or json.loads(path.read_text(encoding="utf-8"))
    lines = (RUNS / name / "lines.log").read_text(encoding="utf-8", errors="replace").splitlines()
    card = scorecard(lines)
    game = meta.get("game") or {}
    if game.get("errors"):
        card["findings"].insert(0, {"say": f"{game['errors']} script errors from the mod", "tone": "bad", "why": "See errors.log in this test's folder."})
        card["tone"] = "bad"
    if game.get("stopped"):
        card["verdict"] = f"Stopped early: {game['stopped']}."
        card["tone"] = "bad"
    if game.get("status") == "running":
        card["verdict"] = f"Still running. So far: {card['verdict']}" if card["active"] else "The game is still loading."
        card["tone"] = card["tone"] if card["active"] else "warn"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({**meta, **card}, indent=2), encoding="utf-8")
    temp.replace(path)  # a page reading mid-save never sees half a file


def tests():
    folders = [f for f in RUNS.iterdir() if (f / "meta.json").exists()] if RUNS.exists() else []
    folders.sort(key=lambda f: (f / "meta.json").stat().st_mtime, reverse=True)
    return [{"name": f.name, "title": json.loads((f / "meta.json").read_text(encoding="utf-8"))["title"],
             "when": (f / "lines.log").stat().st_mtime} for f in folders]


def test(name):
    folder = RUNS / Path(name).name  # the name comes from a URL; keep it inside runs/debt
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    lines = (folder / "lines.log").read_text(encoding="utf-8", errors="replace").splitlines()
    return {**meta, "name": folder.name, **parse(lines)}


def selftest():
    sample = [
        "[22:01:24][jomini_effect_impl.cpp:459]: x.txt:21: SDT month=2 country=Great Britain date=March 31, 1836 principal=10.5 gold=4 default=0",
        "[22:01:24][jomini_effect_impl.cpp:459]: x.txt:21: SDT month=1 country=Great Britain date=March 1, 1836 position=7 principal=0 gold=7",
        "x.txt:9: SDTW country=Denmark date=June 4, 1836 position=6720.5 net=6422",
        "x.txt:9: SDT_STEP pushing POR past its credit limit date=May 30, 1836",
        "x.txt:9: SDT_STEP pushing POR past its credit limit date=May 30, 1836",
        "x.txt:9: SDT_HOOK on_country_default country=Portugal date=May 30, 1836",
        "x.txt:9: SDT_HOOK on_country_no_longer_default country=France date=January 1, 1836 bankrupt=0",
        "x.txt:9: SDT_HOOK on_country_default country=[THIS.GetCountry.GetNameNoFormatting] date=[TimeKeeper.GetCurrentDate.GetString]",
        "an unrelated line",
    ]
    got = parse(sample)
    britain = got["monthly"]["Great Britain"]
    assert [r["month"] for r in britain] == [1, 2], "monthly rows sort by date"
    assert britain[1]["position"] == 4 - 10.5, "position is worked out when the log has none"
    assert britain[0]["position"] == 7, "a logged position is kept"
    assert got["weekly"]["Denmark"][0]["date"] == "1836-06-04"
    assert [e["text"] for e in got["events"]] == ["on_country_default: Portugal", "pushing POR past its credit limit"], got["events"]

    game = [
        "x.txt:1: SD_WORLD date=January 1, 1850 active=4",
        "x.txt:1: SD_WORLD date=January 1, 1860 active=12",
        "x.txt:1: SD_WORLD date=January 1, 1870 active=2",
        "x.txt:1: SD_EVENT kind=loan date=May 1, 1840 borrower=Portugal lender=Great Britain amount=5",
        "x.txt:1: SD_EVENT kind=loan date=May 1, 1841 borrower=Spain lender=France amount=5",
        "x.txt:1: SD_EVENT kind=repaid date=May 1, 1846 borrower=Portugal",
        "x.txt:1: SD_EVENT kind=crisis date=May 1, 1847 borrower=Spain",
        "x.txt:1: SD_EVENT kind=loan date=[TimeKeeper.GetCurrentDate.GetString] borrower=[THIS]",
    ]
    card = scorecard(game)
    assert card["tone"] == "good" and card["verdict"] == "On target.", card
    assert {k: v for k, v, _ in card["tiles"]}["Active now"] == 2, "active now is the latest count, not the peak"
    broken = scorecard(game + ["x.txt:1: SD_WORLD date=January 1, 1871 active=2 due=100 running=0"])
    assert broken["findings"][0]["tone"] == "bad", "payments missing from the treaties must fail"
    short = scorecard(game[:1] + game[3:4])
    assert short["findings"][0]["tone"] == "warn", "a game that stopped before the target year has not failed it yet"
    assert short["findings"][3]["tone"] == "bad", "one lender making every loan fails"
    civil_war = [line.replace("borrower=Spain", "borrower=Carlist Spain") for line in game]
    assert scorecard(civil_war)["tone"] == "warn", "a civil war side's default is not a real crisis"
    repeats = game + ["x.txt:1: SD_EVENT kind=crisis date=May 1, 1848 borrower=Spain", "x.txt:1: SD_EVENT kind=crisis date=May 2, 1848 borrower=Spanish Nationalist Revolt"]
    assert {k: v for k, v, _ in scorecard(repeats)["tiles"]}["Countries in crisis"] == 1, "repeat and revolt crises count one country"
    assert scorecard(game + ["x.txt:1: SD_EVENT kind=lender_default date=May 1, 1848 lender=France"])["tone"] == "warn"
    assert stop_reason(game, ["sd_loan error"]) == "1 script errors from the mod"
    assert stop_reason(game, []) is None, "a healthy game keeps running"
    assert stop_reason(["x.txt:1: SD_WORLD date=July 1, 1837 active=0"], []) is None, "no loans yet is fine early on"
    assert stop_reason(["x.txt:1: SD_WORLD date=January 1, 1838 active=0"], []) == "No loans by 1838"
    one_lender = [game[3]] * 10
    assert "made 100%" in stop_reason(one_lender, []), "one lender making every loan stops the game"
    assert stop_reason([game[3]] * 9, []) is None, "too few loans to judge"
    print("debt.py self-test passed")


if __name__ == "__main__":
    rescore(sys.argv[1]) if sys.argv[1:] else selftest()
