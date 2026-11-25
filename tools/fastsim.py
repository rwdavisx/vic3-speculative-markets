"""The mod's monthly rules outside the game: confidence, panics, credit, leverage, Bad Debts, the bubble and the AI's stance.

py -3 tools/fastsim.py check              self-test, then predicts each older test arm from another arm's games
py -3 tools/fastsim.py exam               predicts six older games with different bubbles from one another, on their recorded rules
py -3 tools/fastsim.py try NAME=VALUE ... runs the games with other values, beside today's (ladder=3,6,9,12 flow_top=0.4)
py -3 tools/fastsim.py rank              moves each value 10% up and down and ranks what it changes

Each logged game gives the market's side month by month: what booms, collapses, foreign panics, wars and growth did to
confidence, and pool income. The rules then run on those inputs with whatever values you give them.
ponytail: one way only. Prices, income and GDP stay as logged, so a change that would move the economy doesn't change the
inputs. It answers how often panics come, how far debt runs and how long countries spend in each band. It says nothing
about GDP. Contagion only scales with the panic count: `exam` finds that scaling changes nothing, as a foreign hit is the largest
push behind 2 to 4% of panics. In `exam` it gets the direction of a change right and about two thirds of its size for panics, months
in panic and manias ending in one, so it can size those. Mania's share of months beats guessing no change but finds a third of the
size. The AI's months in Tight don't beat that guess, and Tight feeds hype, lending and debt, so treat what depends on it with care.
The current build's games are 20-year slices from saves: 1836 to 1856 twice, 1850 to 1870, 1864 to 1885. Compare them by year."""
import itertools
import pickle
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import credit_ai
import generate as g
import leverage as lv

RUNS = Path(__file__).parent.parent / "runs"
CACHE = Path("G:/GameDev/_claude_scratch/vic/fastsim_cache13")
LOG = re.compile(r"SPEC tag=([^\s#]+)\S* date=(\w+) (\d+), (\d{4}) (.*)")
MONTHS = "January February March April May June July August September October November December".split()
BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)  # days before each month
PER_100 = 36500 / 30  # a country's pulse comes every 30 days: rows to a rate per 100 country years
TOP = 40  # the largest economies at the start: the rest barely trade and their logs are mostly empty
KEPT = ("d_world", "d_turmoil", "d_debt", "d_growth", "d_business")  # from the log, whatever the rules do
STANCE_HYPE = {-1: 0.5, 0: 1, 1: 1.3}
STANCE_CREDIT = {-1: 0, 0: 1, 1: 1.6}
BASE = dict(lev_on=True, avg_income=True, reward=lv.REWARD, reward_max=lv.REWARD_MAX, safe=lv.SAFE, ruin=lv.RUIN, span=lv.PANIC_SPAN, crunch=lv.CRUNCH_MAX, fade=lv.CRUNCH_FADE, smooth=lv.INCOME_SMOOTH,
            ai_limit={-1: lv.AI_LIMIT["-1"], 0: lv.AI_LIMIT["0"], 1: lv.AI_LIMIT["1"]}, share=g.CREDIT_SHARE, flow=g.CREDIT_FLOW_MAX, cap=g.CREDIT_CAP_MONTHS,
            runoff=g.CREDIT_RUNOFF, clawback=g.CLAWBACK, credit_from=g.CREDIT_FROM, panic=g.PANIC, rest=g.CONF_START, recover=g.CONF_RECOVER,
            mood_keep=g.MOOD_KEEP, mood=g.MOOD_SHOCK, mania=g.MANIA, mania_reset=g.MANIA_RESET, heat_from=g.HEAT_FROM, burst_below=g.BURST_BELOW, heat_cool=g.HEAT_COOL,
            burst_per=g.BURST_PER_HEAT, burst_max=g.BURST_BELOW,  # ponytail: no cap since 1.2; Tight cooling (HEAT_COOL_TIGHT) not modelled
            panic_back=0, cooldown=g.PANIC_COOLDOWN, rescue_conf=g.RESCUE_CONF, rescue_months=g.RESCUE_MONTHS,
            rescue_months_private=g.RESCUE_MONTHS_PRIVATE, rescue_chance=dict(credit_ai.RESCUE_CHANCE), rescue_able=1.0, stance_cooldown=g.STANCE_COOLDOWN, tight_pull=g.TIGHT_PULL,
            tight_from=g.TIGHT_FROM, easy=0.2, ai_tight=80, ai_loose=g.WARY, temper_shift=credit_ai.TEMPER_SHIFT, boom_scale=g.CONF_PER_HOT / .72, crash_scale=1.0, crash_max=g.CONF_CRASH_MAX,
            stance_moves_hype=True, ladder=lv.LADDER, fever=lv.FEVER, flow_top=None, played_share=g.CREDIT_SHARE, foreign_scale=1.0, tight_cap=None, scale={}, logged_stance=False, warning=g.MANIA_CAUTION, levy=g.MANIA_TAX_CONF)
# history's readings for the 40 largest economies (FINDINGS.md, Benchmarks): centre, low, high
TARGETS = {"panics": (4, 2.5, 5.5), "in_panic": (1.5, 0.8, 2.5), "length": (4.5, 3, 6), "mania": (4, 2, 8), "mania_panic": (20, 10, 35)}
TEMPERS = (42, 33, 25)  # Cautious, Balanced, Bold: the base 30, 40, 30 with most countries' starting laws, +20 Cautious. Gives the event choices played
MANIA_CHOICE = {-1: (50, 60, 40), 0: (50, 30, 20), 1: (80, 30, 20)}  # the AI's odds in the mania event: ride it, warn, levy


def num(d, key):
    try:
        return float(d.get(key, 0))
    except ValueError:
        return 0.0


def parse(path):
    """{tag: [month]} for the largest economies, as plain dicts of numbers."""
    seen = defaultdict(dict)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SPEC tag=" not in line:
                continue
            m = LOG.search(line)
            if not m:
                continue
            d = dict(p.split("=", 1) for p in m[5].split() if "=" in p)
            if "conf" not in d or "d_mood" not in d:
                continue
            month = MONTHS.index(m[2])
            day = int(m[4]) * 365 + BEFORE[month] + int(m[3])
            if day not in seen[m[1]] or num(d, "gdp") > num(seen[m[1]][day][1], "gdp"):
                seen[m[1]][day] = (int(m[4]) * 12 + month + int(m[3]) / 32, d)
    per = {}
    for tag, days in seen.items():
        # a country reports every 30 days. A revolt's breakaway logs under the same tag on its own days: the larger one keeps the slot
        first, slots = min(days), {}
        for day, (when, d) in days.items():
            slot = (day - first) // 30
            if slot not in slots or num(d, "gdp") > num(slots[slot][1], "gdp"):
                slots[slot] = (when, d)
        per[tag] = [slots[k] for k in sorted(slots)]
    big = sorted((t for t in per if len(per[t]) >= 24), key=lambda t: -num(per[t][0][1], "gdp"))[:TOP]
    return {t: country(per[t]) for t in big}


def day_of(when):
    year, rest = divmod(when, 12)
    return int(year) * 365 + BEFORE[int(rest)] + round(rest % 1 * 32)


def filled(rows):
    """The logs lost 3 to 6% of reports, though the game ran those months. A lost month's drift would be missed, and drift is what
    holds confidence down near Mania. The next report's drift gives the confidence it started from, so the month can be rebuilt."""
    out, macro = rows[:1], rows[0]["macro"]
    for r in rows[1:]:
        a = out[-1]
        macro = macro or r["macro"]
        steps = round((day_of(r["when"]) - day_of(a["when"])) / 30)
        if 2 <= steps <= 6:
            pace = PLAYED["recover"] * (g.MACRO[1] if macro else 1)
            last = g.CONF_START - r["drift"] / pace
            calm = a["left"] <= 0 and r["left"] <= 0
            was = a["conf"]
            for n in range(1, steps):
                prev = out[-1]
                conf = was + (last - was) * n / (steps - 1)
                boom = (a["boom"] + r["boom"]) / 2 if calm else 0
                mood = a["mood"] * g.MOOD_KEEP
                pull = 0.0
                if a["stance"] == -1 and conf > g.TIGHT_FROM:  # what the Tight pull will take from the month, so it isn't counted twice
                    pull = -(conf - g.TIGHT_FROM) * g.TIGHT_PULL / (1 - g.TIGHT_PULL)
                # a burst lost with the month: the replay's own bubble makes it, so it mustn't be in the inputs as well
                burst = -min(a["heat"] * g.BURST_PER_HEAT, g.BURST_BELOW) if a["heat"] > 0 and r["heat"] <= 0 and r["burst"] >= 0 and n == steps - 1 else 0
                rest = conf - burst - pull - prev["conf"] - (g.CONF_START - prev["conf"]) * pace - boom - mood - (0.2 if a["stance"] == 1 else 0)
                for hit in (g.MANIA_CAUTION, g.MANIA_TAX_CONF):
                    if prev["conf"] >= g.MANIA and abs(rest + hit) < 2.5:
                        rest += hit
                out.append(dict(prev, when=prev["when"] + 1, conf=conf, left=a["left"] if a["left"] > 0 and r["left"] > 0 else 0, given=0, boom=boom, crash=0, restrain=0, foreign=0, burst=burst, tight=pull,
                                mood=mood, kept=rest, drift=(g.CONF_START - prev["conf"]) * pace, easy=0.2 if a["stance"] == 1 else 0, macro=macro, fill=True, warend=0, caution=0, **{k: 0 for k in KEPT}))
            r["crash"] *= was / max(last, 1) if r["crash"] else 1
        out.append(r)
    return out


def country(rows):
    """The month rows the rules read, and what the log only implies: the lending rate, Central Banking, a panic's length."""
    out, boom, prev = [], 0.0, None
    for when, d in rows:
        conf = num(d, "conf")
        r = dict(when=when, conf=conf, left=num(d, "panic"), stance=int(num(d, "stance")), debt=num(d, "debt"), given=num(d, "pool"), pool=num(d, "ipi") * g.WEEKS_PER_MONTH,
                 ip=num(d, "ip"), lev=num(d, "lev"), crunch=num(d, "crunch"), gdp=num(d, "gdp"), mood=num(d, "d_mood"), ld=num(d, "ld"), rescued=num(d, "rescued"),
                 stock=num(d, "fin") > 0.71 or "fin" not in d, banks=num(d, "fin") >= 1.2, kept=sum(num(d, k) for k in KEPT), **{k: num(d, k) for k in KEPT}, foreign=num(d, "d_foreign"), restrain=num(d, "d_restrain"), heat=num(d, "heat"), burst=num(d, "d_burst"), tight=num(d, "d_tight"), drift=num(d, "d_drift"), easy=num(d, "d_easy"), levers=num(d, "levers"), warend=num(d, "d_warend"), caution=num(d, "d_caution"))
        # booms are zero in a real panic: a replay that isn't in one needs what they would have been, so it gets the recent average
        raw = num(d, "d_boom")
        if prev and prev["left"] > 0:
            raw = boom
        else:
            boom += (raw - boom) * 0.1
        r["boom"] = raw
        was = prev["conf"] if prev else conf
        gap = (g.CONF_START - was) * PLAYED["recover"]
        r["macro"] = abs(gap) > 0.2 and abs(num(d, "d_drift") / gap - g.MACRO[1]) < 0.02  # Macroeconomics isn't logged, but it shows in the drift
        r["crash"] = num(d, "d_crash") * g.CONF_START / max(was, 1)  # per the rule's own scale, so it can follow the replay's confidence
        out.append(r)
        prev = r
    out = filled(out)
    rates, runs, spell = [], [], 0
    banking = None
    for i, r in enumerate(out):
        base = (r["conf"] - g.CREDIT_FROM) / (100 - g.CREDIT_FROM) * r["pool"] * STANCE_CREDIT[r["stance"]]
        if r["given"] > 0 and base > 0 and r["given"] < r["pool"] * 0.29:  # under every build's monthly cap
            rates.append(r["given"] / base)
        if banking is None and (r["stance"] != 0 or (r["given"] > 0 and r["debt"] > 3.05 * r["pool"] > 0)):
            banking = i
        if r["left"] > 0:  # the log's panic is only on or off
            spell += 1
        elif spell:
            runs.append(spell)
            spell = 0
    # a rescued panic is cut short, so the longest is the panic as it starts
    never = len(out)
    banks = next((i for i, r in enumerate(out) if r["banks"]), never)
    banking = never if banking is None else banking
    # ponytail: Exchange Standards isn't logged. It is an era after Investment Banks as they are after Central Banking
    standards = banks + max(banks - banking, 120) if banks < never else never
    return dict(rows=out, raw=statistics.median(rates) if rates else None, banking=banking, banks=max(banks, banking), standards=standards, length=max(runs) if runs else 7)


def load(path):
    CACHE.mkdir(exist_ok=True)
    key = CACHE / (re.sub(r"\W+", "_", str(path.relative_to(RUNS))) + f"_{path.stat().st_mtime_ns}.pkl")
    if key.exists():
        return pickle.loads(key.read_bytes())
    world = parse(path)
    key.write_bytes(pickle.dumps(world))
    return world


# what the logged games ran, where today's values differ. boom_scale is against the logged amount.
# ponytail: Collapse's 5.1 to 5 isn't here, as the logged crash mixes collapses with busts and corrections. Scaling all of it moved nothing
PLAYED = dict(heat_cool=.9, heat_from=74, recover=.042, ai_loose=34, smooth=.154, boom_scale=1, ladder=None, reward=.01, reward_max=8, ruin=10, span=30, crunch=25, fade=.2,
              flow=.3, fever={}, ai_limit={-1: 3, 0: 8, 1: 10})


def arm(run_set, name):
    """Every full game of one arm of a test set."""
    logs = sorted(p for p in (RUNS / run_set).glob(f"{name}__*/telemetry.log") if p.stat().st_size > 1e7)
    games = []
    for p in logs:
        w = load(p)
        if not any(same_game(w, x) for x in games):
            games.append(w)
    return games


def same_game(a, b):
    """A save rerun with the same random seed plays out alike: sweep_fin3's two logs match in 8895 of 8897 reports. That is one game, not two."""
    both = [t for t in a.keys() & b.keys() if min(len(a[t]["rows"]), len(b[t]["rows"])) > 100]
    return sum(a[t]["rows"][100]["conf"] == b[t]["rows"][100]["conf"] for t in both) > .9 * len(both)


def limit_of(p, i, c):
    """The credit limit in months at month i: `ladder` gives it for no tech, Central Banking, Investment Banks, Exchange Standards."""
    if not p["lev_on"]:
        return p["cap"]
    if p["ladder"]:
        return p["ladder"][sum(i >= c[k] for k in ("banking", "banks", "standards"))]
    return p["cap"] if i >= c["banking"] else p["safe"]


def run(c, p, rng, own_mood=False):
    """One country through its logged months. Returns its counts."""
    rows = c["rows"]
    r0 = rows[0]
    conf, debt, avg, crunch, mood = r0["conf"], r0["debt"], r0["pool"], r0["crunch"], r0["mood"]
    left, cool, stance, stance_cool, heat, rescued, mania = int(r0["left"]), 0, r0["stance"], 0, 0.0, False, False
    temper = rng.choices((-1, 0, 1), TEMPERS)[0]
    macro = False
    lean = temper * p["temper_shift"]
    lev = r0["lev"]
    rate = (c["raw"] or p["played_share"]) / p["played_share"]
    s = dict(months=0, bonus=0.0, drag=0.0, panics=0, medium=0, severe=0, over3=0, over5=0, mania=0, tight=0, loose=0, conf=0.0, lev=0.0, rescues=0, in_panic=0, manias=0, mania_panics=0, fevers=0)
    mania_at = None
    fever = False
    event = 0  # the mania event lands after the month it fires, so the next month starts from it
    for i, r in enumerate(rows[1:], 1):
        conf, event = max(conf - event, 0), 0
        was_left = left
        banking = i >= c["banking"]
        macro = macro or r["macro"]
        mood = r["mood"] if own_mood else mood * p["mood_keep"] + rng.uniform(-p["mood"], p["mood"])
        hype = STANCE_HYPE[stance] / STANCE_HYPE[r["stance"]] if p["stance_moves_hype"] else 1
        fall = min(STANCE_HYPE[stance], 1) / min(STANCE_HYPE[r["stance"]], 1) if p["stance_moves_hype"] else 1
        boom = 0 if left else r["boom"] * p["boom_scale"] * hype
        crash = max((r["crash"] * p["crash_scale"] * fall) * conf / p["rest"], -p["crash_max"])
        pre = conf + (p["rest"] - conf) * p["recover"] * (g.MACRO[1] if macro else 1) + boom + crash + r["restrain"] + r["kept"] + sum(r[k] * (v - 1) for k, v in p["scale"].items()) + r["foreign"] * p["foreign_scale"] + mood + (p["easy"] if stance == 1 else 0)
        if stance == -1:
            pre = min(pre, p["tight_cap"]) if p["tight_cap"] else pre + min((p["tight_from"] - pre) * p["tight_pull"], 0)  # older builds capped
        conf = min(max(pre, 0), 100)
        # credit
        debt -= min(debt * p["runoff"], max(r["ip"], 0))
        if conf > p["credit_from"] and not left and stance != -1 and crunch <= 0 and r["ld"] != 1:
            room = max(r["pool"] * limit_of(p, i, c) - debt, 0)
            flow = p["flow_top"] if p["flow_top"] and i >= c["standards"] else p["flow"]
            debt += max(min((conf - p["credit_from"]) / (100 - p["credit_from"]) * r["pool"] * p["share"] * rate * STANCE_CREDIT[stance], r["pool"] * flow, room), 0)
        avg += (r["pool"] - avg) * p["smooth"]
        crunch = max(crunch - p["fade"], 0)
        income = max(r["pool"], avg) if p["avg_income"] else r["pool"]
        if income > 1:
            lev = debt / income
        # the bubble
        if conf >= p["mania"] and not mania:
            mania, mania_at = True, i
            s["manias"] += 1
            fever = p["fever"].get(temper, 0) > 0 and rng.random() * 100 < p["fever"][temper]
            s["fevers"] += fever
            event = rng.choices((0, p["warning"], p["levy"]), MANIA_CHOICE[temper])[0]
        if conf >= p["heat_from"] and r["stock"]:
            heat += conf - p["heat_from"]
        elif heat and conf >= p["burst_below"]:
            heat *= p["heat_cool"]
            heat = 0 if heat < 1 else heat
        if conf < p["mania_reset"]:
            mania = fever = False
        if heat and conf < p["burst_below"]:
            conf = max(conf + max(-heat * p["burst_per"], -p["burst_max"]), 0)
            heat = 0
        # panics
        stance_cool = max(stance_cool - 1, 0)
        cool = max(cool - 1, 0)
        stress = min(max((lev - p["safe"]) / (p["ruin"] - p["safe"]), 0), 1) if p["lev_on"] else 0
        if left:
            left -= 1
            if not left:
                cool = p["cooldown"]
                rescued = False
                conf = max(conf, p["panic_back"])
        elif conf < p["panic"] + stress * p["span"] and not cool:
            left = int(c["length"])
            s["panics"] += 1
            fever = False
            if mania_at is not None and i - mania_at <= 36:
                s["mania_panics"] += 1
                mania_at = None
            size = stress ** 2 * p["crunch"]
            s["medium"] += size >= 5
            s["severe"] += size >= 15
            crunch = max(crunch, size)
            conf = min(conf, p["panic"] - 0.1)
            debt = debt * (1 - p["clawback"]) if p["lev_on"] else debt - min(debt * p["clawback"], max(r["ip"], 0))
            lev = debt / income if income > 1 else lev
        # the AI
        limit = p["ai_limit"][temper] if p["lev_on"] else 1e9
        can = banking and not stance_cool
        new = stance
        if can and stance != -1 and not fever and (conf > p["ai_tight"] + lean or lev > limit):
            new = -1
        elif can and stance == -1 and conf < max(p["mania_reset"] + lean, p["rest"] + 3) and lev < limit / 2:
            new = 0
        elif can and stance == 0 and conf < p["ai_loose"] + lean and lev < limit / 2 and not left:
            new = 1
        elif can and stance == 1 and (conf >= min(p["credit_from"] + lean, p["rest"] - 1) or left):
            new = 0
        if new != stance:
            stance, stance_cool = new, p["stance_cooldown"]
        if p["logged_stance"]:
            stance = rows[i + 1]["stance"] if i + 1 < len(rows) else stance
        months_to = p["rescue_months"] if banking else p["rescue_months_private"]
        if left > months_to and not rescued and rng.random() < p["rescue_chance"][temper] / (p["rescue_chance"][temper] + 100 - p["rescue_chance"][0]) * p["rescue_able"]:
            left, rescued = months_to, True
            conf = min(conf + p["rescue_conf"], 100)
            s["rescues"] += 1
        s["months"] += 1
        s["conf"] += conf
        s["lev"] += lev
        # none in a panic, its last month or Bad Debts. ponytail: raw leverage, where the mod eases it after land loss, and no investment effects, so not a net benefit
        s["bonus"] += 0 if left or was_left or crunch > 0 else min(int(lev), p["reward_max"]) * p["reward"] * 100
        s["drag"] += crunch
        s["over3"] += lev > 3
        s["over5"] += lev > 5
        s["mania"] += conf >= p["mania"]
        s["tight"] += stance == -1
        s["loose"] += stance == 1
        s["in_panic"] += left > 0
    return s


def logged(c):
    """The same counts, read straight from the log."""
    s = defaultdict(float)
    rows = c["rows"]
    mania, mania_at = False, None
    for i, (a, r) in enumerate(zip(rows, rows[1:])):
        if r["conf"] >= g.MANIA and not mania:
            mania, mania_at = True, i
            s["manias"] += 1
        elif r["conf"] < g.MANIA_RESET:
            mania = False
        s["months"] += 1
        s["conf"] += r["conf"]
        s["lev"] += r["lev"]
        s["over3"] += r["lev"] > 3
        s["over5"] += r["lev"] > 5
        s["mania"] += r["conf"] >= g.MANIA
        s["tight"] += r["stance"] == -1
        s["loose"] += r["stance"] == 1
        s["in_panic"] += r["left"] > 0
        if r["left"] > 0 and a["left"] <= 0:
            s["panics"] += 1
            if mania_at is not None and i - mania_at <= 36:
                s["mania_panics"] += 1
                mania_at = None
            raised = r["crunch"] if r["crunch"] > a["crunch"] else 0
            s["medium"] += raised >= 5
            s["severe"] += raised >= 15
        s["rescues"] += r["rescued"] > 0 and a["rescued"] <= 0
    return s


def rates(s):
    m = max(s["months"], 1)
    return dict(panics=s["panics"] / m * PER_100, medium=s["medium"] / m * PER_100, severe=s["severe"] / m * PER_100, over3=s["over3"] / m * 100, over5=s["over5"] / m * 100,
                lev=s["lev"] / m, conf=s["conf"] / m, mania=s["mania"] / m * 100, tight=s["tight"] / m * 100, loose=s["loose"] / m * 100, rescued=s["rescues"] / max(s["panics"], 1) * 100,
                bonus=s.get("bonus", 0) / m, drag=s.get("drag", 0) / m, in_panic=s["in_panic"] / m * 100, length=s["in_panic"] / max(s["panics"], 1), mania_panic=s["mania_panics"] / max(s["manias"], 1) * 100)


def once(games, p, seeds, own_mood):
    total = defaultdict(float)
    for seed in range(seeds):
        rng = random.Random(seed)
        for world in games:
            for c in world.values():
                for k, v in run(c, p, rng, own_mood).items():
                    total[k] += v
    return rates(total)


def sim(games, p, seeds=5, own_mood=False):
    """Twice: a panic abroad hits everyone tied to it, so foreign hits rise and fall with the panics the first pass found."""
    first = once(games, p, seeds, own_mood)
    played = actual(games)["panics"]
    return once(games, dict(p, foreign_scale=first["panics"] / played if played else 1), seeds, own_mood)


def actual(games):
    total = defaultdict(float)
    for world in games:
        for c in world.values():
            for k, v in logged(c).items():
                total[k] += v
    return rates(total)


# the older games' rules, from generate.py's notes and their logs. All ran without Leverage or a soft landing. hot is CONF_PER_HOT
OLD = {"tune3": ("20261031_111843_tune3_tech/run01/telemetry.log", dict(heat_from=80, burst_below=65, burst_per=.25, tight_cap=75, ai_tight=80), .8),
       "tune4": ("20261031_125249_tune4_fin/run01/telemetry.log", dict(heat_from=80, burst_below=65, burst_per=.25, tight_cap=75, ai_tight=80), .8),
       "tune5": ("20261031_134338_tune5_bubble/run01/telemetry.log", dict(heat_from=72, burst_per=.25, tight_cap=75, ai_tight=80), .8),
       "tune6": ("20261031_142409_tune6_hist/run01/telemetry.log", dict(heat_from=76, burst_per=.15, tight_cap=75, ai_tight=80), .64),
       "tune7": ("20261031_162416_tune7_tight/run01/telemetry.log", dict(heat_from=76, burst_per=.15, ai_tight=76), .64),
       "tune8": ("20261031_182730_tune8_mid/run01/debug_mirror.log", dict(heat_from=74, burst_per=.2, ai_tight=80), .72)}
EXAM = ("panics", "in_panic", "mania_panic", "mania", "tight")
LAST = 1892 * 12 + 2  # tune8 stops here


def until(world, end):
    cut = {t: dict(c, rows=[r for r in c["rows"] if r["when"] <= end]) for t, c in world.items()}
    return {t: c for t, c in cut.items() if len(c["rows"]) > 24}


def chance_range(world):
    """90% of a game's panics when its ten year blocks are drawn again, all countries in a block together."""
    blocks = defaultdict(lambda: [0, 0])
    for c in world.values():
        for a, r in zip(c["rows"], c["rows"][1:]):
            b = blocks[int(r["when"] // 120)]
            b[0] += r["left"] > 0 and a["left"] <= 0
            b[1] += 1
    rng, v, out = random.Random(1), list(blocks.values()), []
    for _ in range(2000):
        pick = rng.choices(v, k=len(v))
        out.append(sum(x[0] for x in pick) / sum(x[1] for x in pick) * PER_100)
    return sorted(out)[100], sorted(out)[1899]


def exam(seeds=10):
    """Each older game predicted from every other. Nothing is read from the game being predicted but its recorded rules."""
    games = {k: load(RUNS / v[0]) for k, v in OLD.items()}
    end = {k: min(max(r["when"] for c in w.values() for r in c["rows"]), LAST) for k, w in games.items()}
    rules = lambda k, src: {**BASE, **PLAYED, "lev_on": False, "heat_cool": 1, "boom_scale": OLD[k][2] / OLD[src][2], **OLD[k][1]}
    rows = []
    for a, b in itertools.permutations(games, 2):
        e = min(end[a], end[b])
        src, dst = until(games[a], e), until(games[b], e)
        lo, hi = chance_range(dst)
        rows.append(dict(src=a, dst=b, lo=lo, hi=hi, played=actual([dst]), same=actual([src]), pred=sim([src], rules(b, a), seeds), stay=sim([src], rules(a, a), seeds),
                         unscaled=once([src], rules(b, a), seeds, False)))
        r = rows[-1]
        print(f"  {a} to {b}, to {int(e // 12)}: panics {r['played']['panics']:.2f} ({lo:.1f} to {hi:.1f}), predicted {r['pred']['panics']:.2f}, no change {r['same']['panics']:.2f}", flush=True)
    print(f"  panics inside chance's range: {sum(r['lo'] <= r['pred']['panics'] <= r['hi'] for r in rows)} of {len(rows)}; for no change, {sum(r['lo'] <= r['same']['panics'] <= r['hi'] for r in rows)}")
    miss = lambda k, col: statistics.mean(abs(r["played"][k] - r[col][k]) for r in rows)
    for k in EXAM:
        real = [r["played"][k] - r["same"][k] for r in rows]
        model = [r["pred"][k] - r["stay"][k] for r in rows]
        print(f"  {k:12} typical miss {miss(k, 'pred'):.2f}, foreign unscaled {miss(k, 'unscaled'):.2f}, no change {miss(k, 'same'):.2f}; real against modelled change: "
              f"correlation {statistics.correlation(real, model):.2f}, size {statistics.linear_regression(real, model)[0]:.2f}")
    return rows


COLS = "panics medium severe over3 over5 lev conf mania tight loose rescued".split()


def show(name, r):
    print(f"{name:34}" + "".join(f"{r[k]:8.1f}" for k in COLS))


def header():
    print(" " * 34 + "".join(f"{k:>8}" for k in COLS))


def selftest():
    rows = [dict(when=i, conf=70, left=0, stance=0, debt=0, given=0, pool=100, ip=1e9, lev=0, crunch=0, gdp=1, mood=0, ld=0, rescued=0, stock=False, banks=False, kept=0, foreign=0, restrain=0, boom=0.6, crash=0, macro=False) for i in range(600)]
    c = dict(rows=rows, raw=None, banking=0, banks=9999, standards=9999, length=7)
    p = dict(BASE, ai_limit={-1: 99, 0: 99, 1: 99}, ai_tight=999, mood=0, span=0, temper_shift=0)
    s = run(dict(c, banks=0, standards=0), p, random.Random(1))
    assert s["panics"] == 0 and 9 < s["lev"] / s["months"] < 12.01, s  # lending 40% and repaying 3% can reach the top of the limit
    assert run(c, p, random.Random(1))["lev"] / 599 <= lv.LADDER[1] + .01  # Central Banking alone
    p = dict(p, ladder=None, cap=3)
    assert run(c, p, random.Random(1))["lev"] / 599 <= 3.01
    print("self-test ok")


def parity(games):
    """One month at a time: from the log's state at the end of a month, do the rules give the log's next month?"""
    drift, tight, easy, debt, lev, burst = [], [], [], [], [], []
    began_n = wrong = must = moved = 0
    for world in games:
        for c in world.values():
            rows = c["rows"]
            cool, avg, macro = 0, rows[0]["pool"], False
            rate = (c["raw"] or g.CREDIT_SHARE) / g.CREDIT_SHARE
            for i, (a, r) in enumerate(zip(rows, rows[1:]), 1):
                macro = macro or r["macro"]
                if "fill" in a or "fill" in r:  # the check is against what was logged
                    continue
                drift.append(abs((g.CONF_START - a["conf"]) * PLAYED["recover"] * (g.MACRO[1] if macro else 1) - r["drift"]))
                easy.append(abs((0.2 if a["stance"] == 1 else 0) - r["easy"]))
                began = r["left"] > 0 and a["left"] <= 0
                avg_was = avg
                avg += (r["pool"] - avg) * BASE["smooth"]
                income = max(r["pool"], avg)
                if a["stance"] == -1 and not began:
                    pre = r["conf"] - r["tight"] - r["burst"]
                    tight.append(abs(min((g.TIGHT_FROM - pre) * g.TIGHT_PULL, 0) - r["tight"]))
                if not began and r["left"] <= 0 and a["left"] <= 0 and r["debt"] > 1 and r["pool"] > 1:
                    d = a["debt"] - min(a["debt"] * g.CREDIT_RUNOFF, max(r["ip"], 0))
                    conf = r["conf"] - r["burst"]
                    if conf > g.CREDIT_FROM and a["stance"] != -1 and a["crunch"] <= 0 and r["ld"] != 1:
                        room = max(r["pool"] * limit_of(BASE, i, c) - d, 0)
                        d += max(min((conf - g.CREDIT_FROM) / (100 - g.CREDIT_FROM) * r["pool"] * g.CREDIT_SHARE * rate * STANCE_CREDIT[a["stance"]], r["pool"] * PLAYED["flow"], room), 0)
                    debt.append(abs(d - r["debt"]) / r["pool"])
                    lev.append(abs(d / income - r["lev"]))
                if a["heat"] > 0 and r["burst"] < 0:
                    burst.append(abs(max(-a["heat"] * g.BURST_PER_HEAT, -g.BURST_BELOW) - r["burst"]))
                cool = max(cool - 1, 0)
                stress = min(max((r["lev"] - BASE["safe"]) / (BASE["ruin"] - BASE["safe"]), 0), 1)
                if a["left"] > 0 and r["left"] <= 0:
                    cool = g.PANIC_COOLDOWN
                elif a["left"] <= 0:
                    began_n += began
                    wrong += not began and not cool and r["conf"] < g.PANIC + stress * BASE["span"]
                # past every temperament's Tight line, the AI has to turn Tight as soon as it may
                if i >= c["banking"] and a["stance"] != -1 and r["conf"] > BASE["ai_tight"] + BASE["temper_shift"] + credit_ai.IG_SHIFT:
                    must += 1
                    moved += r["stance"] == -1
    med = lambda x: statistics.median(x) if x else 0
    high = lambda x: sorted(x)[len(x) * 99 // 100] if x else 0
    for name, x in (("drift", drift), ("tight pull", tight), ("easy money", easy), ("debt, in months", debt), ("leverage", lev), ("burst", burst)):
        print(f"  {name:16} {len(x):8} months   typical error {med(x):.4f}   1 in 100 over {high(x):.3f}")
    print(f"  panics that began {began_n}; months the rules say one should have begun and none did {wrong}")
    print(f"  months past every Tight line {must}, Tight the same month {moved}")


def inputs():
    """The games the what-ifs run on. lev2 and lev3 ran with DLC off, so compare within this list, never with a played game."""
    return [w for s in ("sweep_fin0", "sweep_fin1", "sweep_fin2", "sweep_fin3") for w in arm(s, "b_v080")] + arm("sweep_lev2", "mix") + arm("sweep_lev3", "mix")


RANKED = ("safe ruin span crunch fade share flow cap runoff clawback credit_from panic rest recover mood_keep mood mania_reset heat_from burst_below heat_cool burst_per burst_max "
          "panic_back cooldown rescue_conf rescue_able stance_cooldown tight_pull tight_from easy ai_tight ai_loose temper_shift boom_scale crash_scale").split()


def rank():
    games = inputs()
    now = sim(games, BASE, seeds=3)
    print("today:", {k: round(now[k], 2) for k in ("panics", "medium", "severe", "over5", "mania", "conf")})
    rows = []
    for k in RANKED + ["ai_limit"]:
        res = []
        for f in (0.9, 1.1):
            v = {t: x * f for t, x in BASE[k].items()} if k == "ai_limit" else BASE[k] * f
            res.append(sim(games, dict(BASE, **{k: v}), seeds=3))
        rows.append((k, res))
    size = lambda res: sum(abs(res[1][m] - res[0][m]) / max(now[m], 0.1) for m in ("panics", "over5", "mania"))
    print(f"{'value':16}{'now':>7}  panics -10%/+10%   over 5 months     mania        mean confidence")
    for k, (a, b) in sorted(rows, key=lambda r: -size(r[1])):
        v = "-" if k == "ai_limit" else f"{BASE[k]:g}"
        print(f"{k:16}{v:>7}  {a['panics']:5.2f} {b['panics']:5.2f}       {a['over5']:5.2f} {b['over5']:5.2f}     {a['mania']:5.2f} {b['mania']:5.2f}    {a['conf']:5.1f} {b['conf']:5.1f}")


def main():
    if sys.argv[1:2] == ["check"]:
        selftest()
        BASE.update(PLAYED)  # `check` replays the logged games, it doesn't test the mod's values
        print("the rules one month at a time, current build")
        parity([w for s in ("sweep_fin0", "sweep_fin1", "sweep_fin2", "sweep_fin3") for w in arm(s, "b_v080")])
        old = dict(BASE, avg_income=False)  # lev2 and lev3 measured against one month's income
        prudent = dict(old, ai_limit={-1: 3, 0: 3, 1: 3})
        reckless = dict(old, ai_limit={-1: 99, 0: 99, 1: 99}, ai_tight=999)
        base = dict(old, lev_on=False, share=0.3, flow=0.6, played_share=0.3)
        header()
        for run_set in ("sweep_lev2", "sweep_lev3"):
            print(run_set)
            arms = {a: arm(run_set, a) for a in ("base", "mix", "prudent", "reckless")}
            for a, p in (("mix", old), ("prudent", prudent), ("reckless", reckless), ("base", base)):
                if arms[a]:
                    show(f"{a}: played", actual(arms[a]))
                    show(f"{a}: replay of its own games", sim(arms[a], p))
                    if a != "mix":
                        show(f"{a}: predicted from mix only", sim(arms["mix"], dict(p, played_share=g.CREDIT_SHARE)))
            show("mix: predicted from base only", sim(arms["base"], dict(old, played_share=0.3)))
        print("sweep_fin (the current build)")
        fin = [w for s in ("sweep_fin0", "sweep_fin1", "sweep_fin2", "sweep_fin3") for w in arm(s, "b_v080")]
        show("played", actual(fin))
        show("replay, logged mood", sim(fin, BASE, own_mood=True))
        now = sim(fin, BASE)
        show("replay, fresh mood", now)
        played = actual(fin)
        for k, (centre, low, high) in TARGETS.items():
            print(f"  {k:12} played {played[k]:6.2f}  replay {now[k]:6.2f}  history {low} to {high}, centre {centre}")
    elif sys.argv[1:2] == ["exam"]:
        exam()
    elif sys.argv[1:2] == ["try"]:
        games = inputs()
        p = dict(BASE)
        for a in sys.argv[2:]:
            k, v = a.split("=")
            p[k] = [float(x) for x in v.split(",")] if "," in v else float(v)
        header()
        show("today", sim(games, BASE))
        show("with those values", sim(games, p))
    elif sys.argv[1:2] == ["rank"]:
        rank()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
