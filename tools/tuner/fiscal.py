"""Recorded Victoria 3 fiscal inputs for the offline tuner. Build from the fiscal probe's March samples.

py -3 -B tools/tuner/fiscal.py runs/sweep_tuner_profiles_1836/beta_01/probe.log ...
"""
import csv
from functools import cache
from pathlib import Path
import re
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from probe import FINANCE_TECHS

FILE = Path(__file__).with_name("fiscal_profiles.csv")
FIELDS = [*"gdp cash sdebt debt net auth default near gp ind intel".split(), *FINANCE_TECHS]


def collect(paths):
    rows = []
    years = set()
    for path in paths:
        countries = {}
        year = None
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            m = re.search(r"PROBE tag=(\w+) date=March (\d+), (\d+) ", line)
            if not m:
                continue
            observed_year = int(m[3])
            if year is not None and year != observed_year:
                raise ValueError(f"Multiple March snapshots in {path}. Supply one year per log.")
            year = observed_year
            fields = dict(p.split("=", 1) for p in line[m.end():].split() if "=" in p)
            values = {k: float(fields[k]) for k in FIELDS}
            # Undo the sampled country's existing interventions before the simulated AI chooses its own.
            values["net"] += float(fields["grant"]) - float(fields["levy"])
            values["auth"] += float(fields["used"])
            # A breakaway can report under the same tag. Keep the larger economy.
            if values["gdp"] > 0 and (m[1] not in countries or values["gdp"] > countries[m[1]]["gdp"]):
                countries[m[1]] = values
        if len(countries) < 40:
            raise ValueError(f"Missing March observations in {path}")
        if year in years:
            raise ValueError(f"Duplicate snapshot for {year}")
        years.add(year)
        for tag, vals in sorted(countries.items(), key=lambda item: -item[1]["gdp"])[:40]:
            rows.append([year, tag, *(vals[k] for k in FIELDS)])
    if len(years) < 2:
        raise ValueError("Provide March logs from at least two different years.")
    with FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["year", "tag", *FIELDS])
        writer.writerows(rows)


@cache
def profiles():
    with FILE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    years = sorted({int(row["year"]) for row in rows})
    groups = [sorted((r for r in rows if int(r["year"]) == year), key=lambda r: -float(r["gdp"])) for year in years]
    data = {k: np.array([[float(r[k]) for r in group] for group in groups]) for k in FIELDS}
    data["tag"] = np.array([[r["tag"] for r in group] for group in groups])
    return np.array(years), data


@cache
def power_tags():
    _, data = profiles()
    return np.unique(data["tag"][data["gp"] > 0])


@cache
def research_bounds():
    """Earliest and latest possible research month per technology and observed tag."""
    years, p = profiles()
    months = (years - 1836) * 12 + 2  # March
    result = {}
    for tag in np.unique(p["tag"]):
        eras, cols = np.where(p["tag"] == tag)
        result[tag] = {}
        for tech in FINANCE_TECHS:
            seen = p[tech][eras, cols] > 0
            latest = min(months[eras[seen]], default=np.inf)
            # A later snapshot can reuse a tag. Research already observed stays unlocked.
            absent = months[eras[~seen]]
            earliest = max(absent[absent < latest], default=-1) + 1
            result[tag][tech] = (earliest, latest)
    return result


if __name__ == "__main__":
    collect(sys.argv[1:])
