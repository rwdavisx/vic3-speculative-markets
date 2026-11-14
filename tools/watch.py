"""Watches a running test and calls out a bad tune early, so a game isn't played to the end for nothing.

py -3 tools/watch.py <test> [--stop]   prints a line every 2 game years of the game running now, a DECADE line every 10, and TRIP lines
Reads the running game's mirror.log as it grows. Only --stop changes anything: a trip then writes `runs/sweep_<test>/stop`.
The limits sit well above what final-rule games read (lev8, fin1), so only a clearly broken tune trips them. Silence
means only that: it says little about one badly hurt country, and it can't rank two decent tunes (tools/score.py).
ponytail: all countries, fixed limits. Good enough to catch a broken tune early, nothing finer."""
import json
import re
import sys
import time
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
ROW = re.compile(r"SPEC tag=(\S+) date=(\w+) (\d+), (\d{4}) .*? panic=(\S+)(?: .*? lev=([0-9.]+) crunch=([0-9.]+))?")
GDP = re.compile(r"PROBE tag=(\S+) date=(\w+) (\d+), (\d{4}) gdp=([0-9.]+)")   # real GDP. The SPEC line's gdp= is the bank rescue cost, which halves in a panic
MONTH_START = dict(zip("January February March April May June July August September October November December".split(), (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
LIMITS = {"panics": 9.0, "debts": 6.0, "severe": 2.0, "over5": 15.0}   # panics per 100 country years, the rest % of country months. This counts civil war sides, so panics
                                                                        # read high. over5 is loose: the credit ladder is meant to let late countries owe more
DECADE_PANICS = 12.0   # one finished decade, so a late breakdown isn't averaged away by a calm start
FEW_PANICS, FEW_AFTER = 1.0, 20   # fewer than this a hundred country years, this many years in: the system has gone quiet
SMALL = 1500000   # GDP under this counts towards nothing here. A tiny country's income is noise
MIN_ROWS = 3000   # a few years of every country: one panic in the first rows isn't a rate
SETTLE_YEARS = 3   # a game forked from a save starts unsettled


def country(tag, month, day, year):
    """Two countries can share a tag, and read as one panic starting every month. Each reports every 30 days on its own days, and a game year has 365."""
    return tag, (int(year) * 365 + MONTH_START[month] + int(day)) % 30


class Tally:
    def __init__(self):
        self.rows = self.panics = self.debts = self.severe = self.over5 = 0
        self.first = self.year = None
        self.was, self.size, self.gdp, self.top = {}, {}, {}, 0.0
        self.decade = dict(panics=0, rows=0)
        self.decades = []

    def see(self, line):
        if g := GDP.search(line):
            who = country(*g.group(1, 2, 3, 4))
            try:
                self.size[who] = float(g.group(5))
            except ValueError:  # the game wrote another log line into this one
                return
            self.gdp.setdefault(int(g.group(4)), {})[who] = self.size[who]
            return
        m = ROW.search(line)
        if not m:
            return
        try:
            who, year, panic, lev, crunch = country(*m.group(1, 2, 3, 4)), int(m.group(4)), float(m.group(5)), float(m.group(6) or 0), float(m.group(7) or 0)
        except ValueError:  # the game wrote another log line into this one
            return
        self.first = self.first or year
        began = panic > 0 and not self.was.get(who)
        self.was[who] = panic > 0
        if self.year and year != self.year and year % 10 == 6:
            self.close_decade(year)
        self.year = year
        if year - self.first < SETTLE_YEARS or self.size.get(who, SMALL) < SMALL:
            return
        self.rows += 1
        self.decade["rows"] += 1
        self.top = max(self.top, lev)
        self.decade["panics"] += began
        self.panics += began
        self.debts += crunch > 0
        self.severe += crunch >= 15
        self.over5 += lev > 5

    def close_decade(self, year):
        now, then = self.gdp.get(year - 1, {}), self.gdp.get(year - 11, {})
        both = now.keys() & then.keys()   # countries in both years: one that leaves the market or is annexed isn't a slump
        self.decades.append(dict(year=year, panics=1200 * self.decade["panics"] / max(self.decade["rows"], 1), world=sum(now.values()), before=sum(then.values()) or None,
                                 same_now=sum(now[t] for t in both), same_then=sum(then[t] for t in both)))
        self.decade = dict(panics=0, rows=0)

    def read(self):
        n = max(self.rows, 1)
        return {"panics": 1200 * self.panics / n, "debts": 100 * self.debts / n, "severe": 100 * self.severe / n, "over5": 100 * self.over5 / n}

    def trips(self):
        if self.rows < MIN_ROWS:
            return []
        out = [k for k, v in self.read().items() if v > LIMITS[k]]
        if self.year and self.year - self.first >= FEW_AFTER and self.read()["panics"] < FEW_PANICS:
            out.append("few panics")
        for d in self.decades:
            if d["panics"] > DECADE_PANICS:
                out.append(f"decade to {d['year']} panics")
            if d["panics"] < FEW_PANICS and d["year"] - self.first >= FEW_AFTER:
                out.append(f"decade to {d['year']} few panics")
            if d["same_then"] and d["same_now"] < d["same_then"]:
                out.append(f"world GDP fell in the decade to {d['year']}")
        return out


def main(test, stop=False):
    folder = RUNS / f"sweep_{test}"
    tallies, sizes, shown, tripped, told = {}, {}, {}, set(), {}
    while True:
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        games = status["games"]
        for name, g in games.items():
            if g.get("state") != "running" or not g.get("user"):
                continue
            t = tallies.setdefault(name, Tally())
            log = Path(g["user"]) / "mirror.log"
            if not log.exists():
                continue
            with open(log, encoding="utf-8", errors="replace") as f:
                f.seek(sizes.get(name, 0))
                text = f.read()
                sizes[name] = f.tell()
            for line in text[:text.rfind("\n") + 1].splitlines():
                t.see(line)
            sizes[name] -= len(text[text.rfind("\n") + 1:].encode("utf-8", "replace"))
            if t.year and t.year >= shown.get(name, 0) + 2:
                shown[name] = t.year
                v = t.read()
                print(f"{name} {t.year}: panics {v['panics']:.1f} per 100 years, Bad Debts {v['debts']:.1f}%, severe {v['severe']:.2f}%, past 5 months {v['over5']:.1f}%", flush=True)
            for d in t.decades[told.get(name, 0):]:
                v = t.read()
                print(f"DECADE {name} {d['year']}: world GDP {d['world'] / 1e9:.2f}B (was {(d['before'] or 0) / 1e9:.2f}B), panics this decade {d['panics']:.1f}, all game {v['panics']:.1f}, "
                      f"Bad Debts {v['debts']:.1f}%, severe {v['severe']:.2f}%, past 5 months {v['over5']:.1f}%, highest leverage {t.top:.1f}", flush=True)
            told[name] = len(t.decades)
            for k in t.trips():
                if (name, k) not in tripped:
                    tripped.add((name, k))
                    print(f"TRIP {name} {t.year}: {k} {t.read()}", flush=True)
                    if stop:
                        (folder / "stop").touch()
        if all(g.get("state") not in ("running", "waiting") for g in games.values()):
            print("test finished", flush=True)
            return
        time.sleep(120)


def selftest():
    t = Tally()
    for y in range(1850, 1855):
        t.see(f"SPEC tag=AAA date=May 1, {y} conf=20 panic={1 if y == 1854 else 0} pool=0 lev=6.0 crunch=20")
    t.see("SPEC tag=BBB date=May 1, 1854 conf=20 panic=1 pool=0")   # a build with no leverage still counts
    assert t.panics == 2 and t.severe == 2 and t.over5 == 2 and not t.trips(), t.read()
    t.rows = t.severe = MIN_ROWS
    assert "severe" in t.trips(), t.read()
    t = Tally()
    for y, day, g in ((1845, 1, 900), (1855, 11, 800), (1856, 6, 800)):   # days a whole number of 30-day reports apart
        t.see(f"PROBE tag=AAA date=May {day}, {y} gdp={g}0000 sol=1")
        t.see(f"SPEC tag=AAA date=May {day}, {y} conf=60 panic=0 pool=0 gdp=5 lev=1.0 crunch=0")
    t.rows = MIN_ROWS
    assert any("world GDP fell" in k for k in t.trips()), t.decades
    t = Tally()   # a small country is left out on its real GDP, whatever SPEC's gdp= says, and a namesake on other days is another country
    t.see("PROBE tag=AAA date=May 1, 1850 gdp=900000 sol=1")
    t.see("SPEC tag=AAA date=May 1, 1853 conf=20 panic=0 pool=0 gdp=99999999 lev=6.0 crunch=20")
    t.first = 1850
    t.see("PROBE tag=AAA date=May 31, 1853 gdp=900000 sol=1")
    t.see("SPEC tag=AAA date=May 31, 1853 conf=20 panic=1 pool=0 gdp=99999999 lev=6.0 crunch=20")
    assert t.rows == 0 and country("AAA", "May", 1, 1850) == country("AAA", "May", 31, 1850) and country("AAA", "May", 1, 1850) != country("AAA", "May", 2, 1850)
    print("watch ok")


if __name__ == "__main__":
    main(sys.argv[1], "--stop" in sys.argv) if sys.argv[1:] else selftest()
