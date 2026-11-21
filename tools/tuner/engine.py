"""The tuning engine: Speculative Markets' monthly loop for one country, outside the game, thousands of economies at once.

Every constant is read from the generator modules (tools/*.py) as they stand, tools/tuning.json included, so the engine
runs the build's own numbers. Each mechanic below names the generator code it mirrors; the order of the steps in
step() is spec_monthly's order (generate.monthly). The game's side (GDP, pool income, investor interest, wars, foreign
panics) is a set of bounded random input streams (INPUTS), with a simple feedback curve from panics and Bad Debts
back into GDP and pool income (feedback()).

py -3 -B tools/tuner/engine.py     self-check: the engine's constants against the generators and their script
"""
import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
import centres  # noqa: E402
import credit_ai  # noqa: E402
import cycle  # noqa: E402
import depression  # noqa: E402
import diplomacy  # noqa: E402
import economy  # noqa: E402
import exposure  # noqa: E402
import generate as g  # noqa: E402
import journal  # noqa: E402
import leverage as lv  # noqa: E402
import levers  # noqa: E402
import market_tab  # noqa: E402
import monetary  # noqa: E402
import vanilla_ties as vt  # noqa: E402

# ---------- the constants: (tuning.json key or None, module, attribute, group, label) ----------
# A key means generate.py and friends read it through tuning.get(key, default), so the tuner can write it back.
SPEC = [
    ("CONF_START", g, "CONF_START", "Confidence", "Resting confidence"),
    ("CONF_RECOVER", g, "CONF_RECOVER", "Confidence", "Drift back a month"),
    ("MOOD_SHOCK", g, "MOOD_SHOCK", "Confidence", "Mood shock"),
    ("MOOD_KEEP", g, "MOOD_KEEP", "Confidence", "Mood memory"),
    ("MOOD_SHALLOW", g, "MOOD_SHALLOW", "Confidence", "Mood felt with no districts"),
    ("PANIC_SHALLOW", g, "PANIC_SHALLOW", "Confidence", "Panic line drop with no districts"),
    ("CONF_PER_HOT", g, "CONF_PER_HOT", "Booms", "Confidence per boom"),
    ("FIN_BOOM_BASE", g, "FIN_BOOM_BASE", "Booms", "Boom size before finance techs"),
    ("CONF_CRASH_MAX", g, "CONF_CRASH_MAX", "Booms", "Most a month of endings takes"),
    ("CORRECTION_PER_HYPE", g, None, "Booms", "Correction cost"),
    ("BUST_PER_HYPE", g, None, "Booms", "Bust cost"),
    ("CONF_PER_CRASH_HYPE", g, "CONF_PER_CRASH_HYPE", "Booms", "Collapse cost"),
    ("CREDIT_FROM", g, "CREDIT_FROM", "Credit", "Banks lend above"),
    ("CREDIT_SHARE", g, "CREDIT_SHARE", "Credit", "Credit share at full confidence"),
    ("CREDIT_FLOW_MAX", g, "CREDIT_FLOW_MAX", "Credit", "Confidence's part at most"),
    ("CREDIT_CEILING", g, "CREDIT_CEILING", "Credit", "Ceiling, share of a month's income"),
    ("CREDIT_RUNOFF", g, "CREDIT_RUNOFF", "Credit", "Runoff a month"),
    ("CLAWBACK", g, "CLAWBACK", "Panic", "Share of credit recalled"),
    ("CLAW_FLOOR", g, "CLAW_FLOOR", "Panic", "Pool share taken at low leverage"),
    ("PANIC", g, "PANIC", "Panic", "Panic line"),
    ("PANIC_DAYS", g, "PANIC_DAYS", "Panic", "Panic length (days)"),
    ("PANIC_ENDS_AT", g, "PANIC_ENDS_AT", "Panic", "Panic ends at"),
    ("MANIA", g, "MANIA", "Confidence", "Mania line"),
    ("TIGHT_PULL", g, "TIGHT_PULL", "Credit", "Tight pull a month"),
    ("HEAT_FROM", g, "HEAT_FROM", "Excess", "Excess builds from"),
    ("BURST_BELOW", g, "BURST_BELOW", "Excess", "Bursts below"),
    ("HEAT_COOL", g, "HEAT_COOL", "Excess", "Kept a month while cooling"),
    ("HEAT_COOL_TIGHT", g, "HEAT_COOL_TIGHT", "Excess", "Kept a month under Tight"),
    ("BURST_PER_HEAT", g, "BURST_PER_HEAT", "Excess", "Confidence per point of Excess"),
    ("WARY", g, "WARY", "AI", "AI loosens below"),
    ("CONTAGION", g, "CONTAGION", "Inputs", "Contagion"),
    ("LEV_SAFE", lv, "SAFE", "Leverage", "Safe line (months)"),
    ("LEV_RUIN", lv, "RUIN", "Leverage", "Ruin line (months)"),
    ("LEV_PANIC_SPAN", lv, "PANIC_SPAN", "Leverage", "Panic Threshold rise at ruin"),
    ("LEV_REWARD", lv, "REWARD", "Leverage", "Throughput per month of leverage"),
    ("LEV_REWARD_MAX", lv, "REWARD_MAX", "Leverage", "Bonus months at most"),
    ("LEV_BONUS_FADE", lv, "BONUS_FADE", "Leverage", "Bonus months lost a month"),
    ("LEV_CRUNCH_RAMP", lv, "CRUNCH_RAMP", "Bad Debts", "Felt a month"),
    ("LEV_CRUNCH_MAX", lv, "CRUNCH_MAX", "Bad Debts", "Bad Debts at ruin"),
    ("LEV_CRUNCH_FADE", lv, "CRUNCH_FADE", "Bad Debts", "Fade a month"),
    ("LEV_CRUNCH_FADE_TIGHT", lv, "CRUNCH_FADE_TIGHT", "Bad Debts", "Fade a month under Tight"),
    ("LEV_BAD_STOP", lv, "BAD_STOP", "Bad Debts", "Bad Debts that stop lending"),
    ("LEV_CRUNCH_THROUGHPUT", lv, "CRUNCH_THROUGHPUT", "Bad Debts", "Throughput lost a point"),
    ("LEV_CRUNCH_INVEST", lv, "CRUNCH_INVEST", "Bad Debts", "Investment lost a point"),
    ("LEV_BAILOUT_CUT", lv, "BAILOUT_CUT", "Bad Debts", "Buy Up Bad Loans cut"),
    ("LEV_BAILOUT_COST", lv, "BAILOUT_COST", "Bad Debts", "Buy Up cost per point squared"),
    ("LEV_INCOME_SMOOTH", lv, "INCOME_SMOOTH", "Leverage", "Income average weight"),
    ("LEV_INCOME_FLOOR", lv, "INCOME_FLOOR", "Leverage", "Income floor, share of GDP"),
    ("LAX_START", cycle, "LAX_START", "Lending Standards", "Start"),
    ("LAX_QUIET_YEARS", cycle, "LAX_QUIET_YEARS", "Lending Standards", "Quiet years, strict to reckless"),
    ("LAX_PER_CONF", cycle, "LAX_PER_CONF", "Lending Standards", "Stricter per point of boom loss"),
    ("LAX_RESCUE", cycle, "LAX_RESCUE", "Lending Standards", "Laxer per rescue"),
    ("LAX_PANIC", cycle, "LAX_PANIC", "Lending Standards", "Stricter per unrescued panic"),
    ("LAX_CREDIT", cycle, "LAX_CREDIT", "Lending Standards", "Credit swing"),
    ("LAX_PULL", cycle, "LAX_PULL", "Lending Standards", "Boom-lending swing"),
    ("LAX_COST", cycle, "LAX_COST", "Lending Standards", "Rescue cost swing"),
    ("LAX_RECALL", cycle, "LAX_RECALL", "Lending Standards", "Recall swing"),
    ("LAX_BADSTOP", cycle, "LAX_BADSTOP", "Lending Standards", "Bad Debt stop swing"),
    ("EXP_PULL", exposure, "PULL", "Booms", "Boom lending pull"),
    ("EXP_SHARE_MAX", exposure, "SHARE_MAX", "Booms", "Boom lending at most"),
    ("EXP_PER_MONTH", exposure, "PER_MONTH", "Booms", "Ending harder per month lent"),
    ("EXP_MULT_MAX", exposure, "MULT_MAX", "Booms", "Ending multiplier at most"),
    ("TEMPER_SHIFT", credit_ai, "TEMPER_SHIFT", "AI", "Temperament shift"),
    ("AI_TIGHT", credit_ai, "AI_TIGHT", "AI", "AI tightens above"),
    ("IG_SHIFT", credit_ai, "IG_SHIFT", "AI", "Interest group shift"),
    ("DEBT_MAX", vt, "DEBT_MAX", "Inputs", "Government debt drag at most"),
    # read but not written back: no tuning.get in the generator
    (None, g, "PANIC_MIN_MONTHS", "Panic", "Shortest panic"), (None, g, "PANIC_COOLDOWN", "Panic", "Calm after a panic"),
    (None, g, "PANIC_LEV_LEN", "Panic", "Longer per month of leverage"), (None, g, "CRUNCH_FLOOR", "Panic", "Construction cut at the safe line"),
    (None, g, "MANIA_RESET", "Confidence", "Mania resets below"), (None, g, "TIGHT_FROM", "Credit", "Tight pulls toward"),
    (None, g, "CONF_BOOM_MAX", "Booms", "Boom push at most"), (None, g, "WEEKS_PER_MONTH", "Credit", "Weeks a month"),
    (None, g, "RESCUE_CONF", "Rescue", "Rescue confidence"), (None, g, "RESCUE_MONTHS", "Rescue", "Rescue months"),
    (None, g, "RESCUE_MONTHS_PRIVATE", "Rescue", "Rescue months, private"), (None, g, "RESCUE_COST", "Rescue", "Rescue cost, share of GDP"),
    (None, g, "RESCUE_COST_PRIVATE", "Rescue", "Rescue cost, private"), (None, g, "RESCUE_FLOOR", "Rescue", "Rescue cost floor"),
    (None, g, "RESCUE_REF_MONTHS", "Rescue", "Rescue reference months"), (None, g, "RESCUE_CUT", "Rescue", "Rescued penalties"),
    (None, g, "STANCE_COOLDOWN", "Credit", "Months between stances"), (None, g, "MANIA_CAUTION", "Confidence", "Mania warning"),
    (None, g, "MANIA_TAX_CONF", "Confidence", "Mania levy"), (None, g, "MANIA_TAX", "Confidence", "Mania levy, share of GDP"),
    (None, g, "PANIC_THROUGHPUT", "Panic", "Panic throughput"), (None, g, "PANIC_INVEST", "Panic", "Panic investment"),
    (None, g, "PANIC_APPROVAL", "Panic", "Panic approval"), (None, g, "HOT_HYPE", "Booms", "Booming at"),
    (None, g, "GLUT_HYPE", "Booms", "Glut interest"), (None, g, "EXPOSURE_FULL", "Booms", "Share of trade at full weight"),
    (None, g, "HYPE_MAX", "Booms", "Interest at most"), (None, lv, "DANGER", "Leverage", "Dangerous from"),
    (None, credit_ai, "IG_SHIFT", "AI", "Interest group shift"),
    (None, economy, "GROWTH_KEEP", "Inputs", "GDP average kept"), (None, economy, "GROWTH_K", "Inputs", "Growth confidence"),
    (None, economy, "GROWTH_MAX", "Inputs", "Growth at most"), (None, economy, "GROWTH_NORMAL", "Inputs", "Normal growth"),
    (None, economy, "DEFAULT_COST", "Inputs", "Default a month"), (None, diplomacy, "PLAY_TURMOIL", "Inputs", "Diplomatic play a month"),
    (None, diplomacy, "WAR_BASE", "Inputs", "War a month at least"), (None, diplomacy, "WAR_COST", "Inputs", "War a month, typical"),
    (None, vt, "DEBT_FROM", "Inputs", "Debt drag from"), (None, vt, "DEPTH_MIN", "Inputs", "Depth at least"),
]
_UNWIND = {"CORRECTION_PER_HYPE": 1, "BUST_PER_HYPE": 2}  # severity -> UNWINDS row, read off generate.UNWINDS


def current():
    """{key: value} as the generators have them now. Keys without a tuning name are the module's attribute name."""
    out = {}
    for key, mod, attr, *_ in SPEC:
        if attr is None:
            out[key] = next(rate for sev, _, _, rate, _ in g.UNWINDS if sev == _UNWIND[key])
        else:
            out[key if key else attr] = getattr(mod, attr)
    out["LADDER"] = tuple(lv.LADDER)
    out["AI_LEV_LIMIT"] = {int(k): v for k, v in lv.AI_LIMIT.items()}
    out["AI_FEVER"] = dict(lv.FEVER)
    out["RESCUE_CHANCE"] = dict(credit_ai.RESCUE_CHANCE)
    out["AI_LOOSE"] = credit_ai.tuning.get("AI_LOOSE", g.WARY)  # credit_ai.script's loose point
    return out


TUNABLE = [s for s in SPEC if s[0]]
LAWS = {law: (h, p) for law, h, p in g.LAWS}  # economic system -> (hype x, panic length x)
ALLOC = g.law_alloc()  # the law's private construction share (spec_alloc_base)
MONEY = dict(monetary.FX)  # monetary law -> {key: multiplier}
LADDER_TECHS = lv.LADDER_TECHS
CREDIT_TECHS = g.CREDIT_TECHS
TECHS = sorted({"banking", "stock_exchange", "central_banking", "joint_stock_companies", "macroeconomics", "currency_standards",
                *CREDIT_TECHS, *LADDER_TECHS, *g.FIN_BOOM, *g.FIN_RISK, g.FIN_LEVERAGE[0]})
BANDS = market_tab.TIERS  # (name, from, to)
WORDS = cycle.LAX_WORDS

# ---------- the game's side, abstracted: bounded input streams ----------
# name: (default, low, high, label). The sweep draws each economy's figures inside [low, high]; the page edits both.
GOODS_MAX = 24  # goods an economy can have
INPUTS = {
    "years": (100, 10, 150, "Years run"),
    "pool_share": ((0.012, 0.035), 0.005, 0.06, "Pool income a month, share of GDP"),
    "pool_noise": ((0.02, 0.08), 0, 0.3, "Pool income noise a month"),
    "pool_spend": ((0.35, 0.7), 0.05, 1, "Share of the pool spent a month"),
    "growth": ((0.005, 0.035), -0.02, 0.06, "GDP growth a year"),
    "gdp_noise": ((0.002, 0.006), 0, 0.03, "GDP noise a month"),
    "recessions": ((2, 6), 0, 20, "Vanilla recessions a century"),
    "recession_depth": ((0.03, 0.10), 0, 0.4, "Recession depth"),
    "goods": ((6, 20), 1, GOODS_MAX, "Goods that can boom"),  # a market can have 10 to 20 goods past EXPOSURE_FULL
    "good_share": ((0.005, 0.08), 0.0001, 0.2, "Each good's share of trade"),
    "boom_rate": ((0.02, 0.5), 0, 8, "Booms a year, each good"),  # per country, even on a log scale: some economies boom far more
    "boom_months": ((8, 40), 3, 120, "Months a boom runs"),
    "boom_peak": ((0.5, 14), 0, 60, "Interest above 1 at the peak, x1 multiplier"),  # HYPE_MAX clips the result, not the draw
    "boom_fall": ((0.10, 0.45), 0.05, 0.5, "Interest a boom falls to"),
    "foreign_rate": ((3, 12), 0, 150, "Foreign panics reaching us a century"),
    "foreign_size": ((0.02, 0.6), 0, 1, "Their hit, share of Contagion"),
    "war_rate": ((1, 5), 0, 50, "Wars a century"),
    "war_months": ((6, 48), 1, 120, "Months a war lasts"),
    "war_cost": ((0.35, 1.2), 0, 3, "Confidence a war month"),
    "approval_sd": ((0.8, 2.0), 0, 5, "Industrialists' approval noise"),
    "legitimacy": ((20, 90), 0, 100, "Legitimacy"),
    "scaled_debt": ((0, 0.8), 0, 1.5, "Government debt, share of credit"),
    "reserves": ((0.01, 0.08), 0, 0.5, "Gold reserves, share of GDP"),
    "depth": ((vt.DEPTH_MIN, vt.DEPTH_MAX), vt.DEPTH_MIN, vt.DEPTH_MAX, "Financial District depth"),
    "steady": ((vt.STEADY_MIN, vt.STEADY_MAX), vt.STEADY_MIN, vt.STEADY_MAX, "Manor House steadiness"),
    # the world beyond, replayed from the logs (world.npz) rather than drawn: wars, defaults and crises come with their
    # heavy tails and together, as they do in the game; 0 draws them from the rates below instead
    "world_replay": (1, 0, 1, "Replay the logged wars, crises and foreign panics"),
    # stand-ins, fitted (fit.py's roughness block): with every logged driver matched, the games still had twice the AI's panics
    "after_panic": ((0.6, 0.6), 0, 5, "Confidence lost a month in the year after a panic: the unrest, falling GDP and approval that follow one"),
    "rough_sd": ((1.0, 1.0), 0, 10, "The world's roughness: a slow swing of confidence the model lacks, its size a month"),
    "rough_months": ((6, 6), 0.5, 60, "How long a swing of the world's roughness lasts, months"),
    "flight_share": (0.3, 0, 1, "Countries capital flight reaches"),
    "flight_rate": ((15, 240), 0, 300, "Capital flights a century, where it reaches"),  # one for most panics anywhere
    "flight_size": ((0.2, 2), 0, 10, "A capital flight's gain"),
    # the Long Depression, read off the logs' ld= (146 games since 2026-11-07, countries reaching 1880): it reached 59%,
    # its first month fell in 1870 to 1879 (median 1875), and the Depression phase ran 17 to 45 months (median 23)
    "ld_join": (0.6, 0, 1, "Countries the Long Depression reaches"),
    "ld_wait": ((0, 4), 0, 30, "Years it waits for a Great Power's panic"),
    "ld_months": ((17, 45), 4, 60, "Months the Depression phase lasts"),
    "e_gdp": (0.6, 0, 2, "GDP felt per unit of throughput"),
    "e_pool": (1.0, 0, 2, "Pool income felt per unit of investment"),
    # the banks' lending against the base at confidence 57 to 65 (Normal, 1850 on): 0.56 in the pre-1.2 logs, 0.75 in three
    # current-build games (runs/sweep_calib12), where the engine gave 0.43 at 0.55, so the current build needs about 1
    "e_credit": (1.0, 0, 2, "Credit felt per unit of the mod's lending"),
    # levers.afford: the AI pulls a lever only with twice its Authority cost to spare. Its spare Authority, in levers, is a
    # draw (even on a log scale) that lasts AUTH_YEARS on average, fitted to the logs' levers= (how many it holds at once)
    "ai_authority": ((0.1, 10), 0, 50, "The AI's spare Authority, in levers"),
    "heightened": (0, 0, 1, "Heightened volatility rule"),
}
# the laws in 1836 among the largest economies (vanilla common/history/countries: interventionism 16, traditionalism 7,
# agrarianism 2, laissez-faire none), Britain alone on gold (monetary.GOLD_AT_START). A variant replaces its parent beside
# its Economic System (monetary.SWAP)
ECON_MIX = {"laissez_faire": 0.02, "interventionism": 0.62, "agrarianism": 0.08, "traditionalism": 0.28}
MONEY_MIX = {"bimetallism": 0.96, "gold_standard": 0.04}
# the moves countries make over the century, in order: (law kind, from, {to: weight}, share of those on it that move, years
# after 1836 low to high), each after the economy's last move of that kind. Fiat needs Central Banking (monetary.FIAT_TECH),
# which every economy has by year 30. ponytail: estimates, as the logs record no laws; fit them if a log ever does
LAW_DRIFT = [("econ", "traditionalism", {"laissez_faire": 0.55, "interventionism": 0.3, "agrarianism": 0.15}, 0.7, 10, 70),
             ("econ", "agrarianism", {"laissez_faire": 0.6, "interventionism": 0.4}, 0.5, 15, 80),
             ("econ", "interventionism", {"laissez_faire": 1}, 0.45, 20, 90),
             ("econ", "laissez_faire", {"interventionism": 1}, 0.2, 60, 100),
             ("money", "bimetallism", {"gold_standard": 1}, 0.75, 30, 70),
             ("money", "gold_standard", {"fiat_money": 1}, 0.3, 75, 100),
             ("money", "bimetallism", {"fiat_money": 1}, 0.3, 75, 100)]
# research year after 1836, low to high: the start's techs at 0. The logs' 40 largest (fastsim's fin= readings, 146 games
# since 2026-11-07): the Stock Exchange 52% by 1840 and 98% by 1860; Investment Banks 3% by 1870, 24% by 1890, 61% by
# 1910, 79% by 1920. The rest are not logged: later in the tree, so after Investment Banks (estimates)
TECH_YEARS = {"banking": (0, 0), "currency_standards": (0, 0), "international_trade": (0, 0), "stock_exchange": (0, 15),
              "joint_stock_companies": (0, 15), "central_banking": (5, 50), "investment_banks": (32, 90),
              "international_exchange_standards": (40, 100), "mutual_funds": (50, 110), "modern_financial_instruments": (65, 130),
              "macroeconomics": (75, 130)}
# how wars end, read off 8,667 SPECWAREND lines (DLC-on games since 2026-11-07, every country): (share of ends, share of
# those with the war goal enforced), and the stakes: share at diplomacy.WAR_STAKES_MIN, share at full, the rest between
WAR_ENDS = {"won": (0.83, 0.21), "lost": (0.10, 0.26), "drawn": (0.07, 0)}
WAR_STAKES = (0.77, 0.15)
AUTH_YEARS = 5


FITTED = Path(__file__).resolve().parent / "inputs.json"  # fit.py: the inputs read off the headless games
WORLD = FITTED.with_name("world.npz")  # fit.py: each logged country's turmoil, foreign hits and war endings, a row a month
_world = {}


def world():
    """world.npz as {t, f, w: (countries, months), contagion}, reread when fit.py rewrites it; None without one."""
    if not WORLD.exists():
        return None
    key = WORLD.stat().st_mtime_ns
    if _world.get("key") != key:
        with np.load(WORLD) as z:
            _world.update(key=key, t=z["t"], f=z["f"], w=z["w"], contagion=float(z["contagion"]))
    return _world


def defaults(fitted=True):
    import json
    inputs = {k: v[0] for k, v in INPUTS.items()}
    if fitted and FITTED.exists():
        inputs |= {k: v for k, v in json.loads(FITTED.read_text(encoding="utf-8"))["inputs"].items() if k in INPUTS}
    return {"inputs": inputs, "econ_mix": dict(ECON_MIX), "money_mix": dict(MONEY_MIX), "law_drift": [list(r) for r in LAW_DRIFT], "tech_years": {k: list(v) for k, v in TECH_YEARS.items()}}


# ---------- player bots: one threshold policy, presets for each behaviour ----------
INF = 1e9
BOTS = {
    # Normal throughout, never pays for anything, rides every Mania (the event's default option)
    "passive": dict(tight_conf=INF, tight_lev=INF, untight_conf=-INF, untight_lev=INF, loose_conf=-INF, loose_lev=INF,
                    unloose_conf=INF, rescue=0, bailout=0, bailout_from=0, mania=(1, 0, 0), afford=False),
    # tightens ahead of a Mania or once leverage leaves the safe line, rescues every panic, buys up large Bad Debts
    "careful": dict(tight_conf=72, tight_lev=lv.SAFE + 1, untight_conf=60, untight_lev=lv.SAFE, loose_conf=-INF, loose_lev=INF,
                    unloose_conf=INF, rescue=1, bailout=1, bailout_from=10, mania=(0, 1, 0), afford=False),
    # mastery: lets leverage run a few months past the safe line, tightens late ahead of a Mania, rescues, buys up large Bad Debts
    "skilled": dict(tight_conf=76, tight_lev=lv.SAFE + 3, untight_conf=60, untight_lev=lv.SAFE + 2, loose_conf=-INF, loose_lev=INF,
                    unloose_conf=INF, rescue=1, bailout=1, bailout_from=10, mania=(0, 1, 0), afford=False),
    # Loose whenever it can, rescues and buys up everything, rides every Mania
    "reckless": dict(tight_conf=INF, tight_lev=INF, untight_conf=-INF, untight_lev=INF, loose_conf=INF, loose_lev=INF,
                     unloose_conf=INF, rescue=1, bailout=1, bailout_from=0, mania=(1, 0, 0), afford=False),
    # reckless, but never buys up Bad Debts: is buying up worth it?
    "nobuy": dict(tight_conf=INF, tight_lev=INF, untight_conf=-INF, untight_lev=INF, loose_conf=INF, loose_lev=INF,
                  unloose_conf=INF, rescue=1, bailout=0, bailout_from=0, mania=(1, 0, 0), afford=False),
    # the mod's own AI (credit_ai.py and generate.monthly's is_player = no block), by temperament
    "ai": "ai",
}


def ai_policy(K, temper, lean):
    """The AI's thresholds (credit_ai.script) for each economy: temper -1/0/1, lean = its temper and IG shift."""
    lim = np.vectorize(lambda t: K["AI_LEV_LIMIT"][int(t)])(temper).astype(float)
    return dict(tight_conf=K["AI_TIGHT"] + lean, tight_lev=lim,
                untight_conf=np.maximum(K["MANIA_RESET"] + lean, K["CONF_START"] + 3), untight_lev=lim * 0.5,
                loose_conf=K["AI_LOOSE"] + lean, loose_lev=lim * 0.5,
                unloose_conf=np.minimum(K["CREDIT_FROM"] + lean, K["CONF_START"] - 1),
                rescue=np.vectorize(lambda t: K["RESCUE_CHANCE"][int(t)] / 100)(temper), bailout=0.15, bailout_from=0,
                mania=None, afford=True)


def best_response(K, inputs, search, n=500, seed=1):
    """Hook for a later step: search the threshold policy's figures (`search`: {field: (lo, hi)}) for the player's best
    outcome against these mechanics. ponytail: not built yet; the presets above stand in."""
    raise NotImplementedError("best_response: a later step")


# ---------- the calculations the Inspector shows: (label, frame field, format) ----------
CALC = {
    "conf": [("Last month", "conf_was", "1"), ("Drift back to resting", "c_recover", "+2"), ("Booms", "c_boom", "+2"),
             ("Booms ending", "c_crash", "+2"), ("Market Mood", "c_mood", "+2"), ("Growth", "c_growth", "+2"),
             ("Business", "c_business", "+2"), ("Government debt", "c_debt", "+2"), ("Turmoil", "c_turmoil", "+2"),
             ("Panics abroad, capital flight", "c_foreign", "+2"), ("Long Depression", "c_world", "+2"), ("War ending", "c_warend", "+2"), ("Restrained booms", "c_restrain", "+2"), ("World roughness (stand-in)", "c_rough", "+2"), ("Tight credit", "c_tight", "+2"), ("0 to 100 limit", "c_limit", "+2"),
             ("Bubble burst", "c_burst", "+2"), ("Panic's fall", "c_drop", "+2"), ("Rescue", "c_rescue", "+2"),
             ("Mania event", "c_caution", "+2"), ("= Market Confidence", "conf", "=1")],
    "booms": [("Booming goods", "n_boom", "0"), ("Their weight x confidence per boom", "boom_raw", "2"),
              ("Capped at", "boom_cap", "2"), ("x Manor Houses", "steady", "x2"), ("x finance techs", "fin_boom", "x2"),
              ("= Booms", "c_boom", "=+2"), ("Endings, raw", "crash_raw", "2"), ("x crash scale", "crash_scale", "x2"),
              ("= Booms ending", "c_crash", "=+2")],
    "banks": [("Confidence above the line", "credit_base", "%1"), ("x a month's pool income", "pool_month", "£"),
              ("x law", "law_mult", "x2"), ("x techs", "tech_credit", "x2"), ("x credit policy", "stance_credit", "x2"),
              ("x Lending Standards", "lax_credit", "x2"), ("x Bad Debts", "crunch_lend", "x2"), ("Ceiling", "ceiling", "£"),
              ("Room under the Lending Limit", "room", "£"), ("= Lent this month", "lent", "=£")],
    "lax": [("Last month", "lax_was", "%0"), ("Quiet month", "lax_drift", "+%1"), ("Booms ending", "lax_booms", "+%1"),
            ("Rescues and panics", "lax_jump", "+%1"), ("= Lending Standards", "lax", "=%0")],
    "excess": [("Confidence over the line", "xs_over", "+1"), ("x Monetary Standard", "reform_heat", "x2"),
               ("Grows", "xs_grow", "+1"), ("Cools", "xs_cool", "+1"), ("A burst takes from confidence", "c_burst", "+1"),
               ("Burst leaves Bad Debts", "xs_bad", "1"), ("= Speculative Excess", "heat", "=1")],
    "credit": [("Last month", "debt_was", "£"), ("Runoff", "runoff_neg", "£"), ("Lent", "lent", "£"),
               ("Recalled, paid from the pool", "recall_neg", "£"), ("Recalled, written off", "writeoff_neg", "£"), ("= Outstanding Credit", "debt", "=£"),
               ("Lending Limit (months)", "credit_limit", "1")],
    "pool": [("Last month", "pool_last", "£"), ("A month's income", "pool_month", "£"), ("Spent on construction", "spend_neg", "£"), ("Repaid to banks", "repaid_neg", "£"),
             ("Lent in", "lent", "£"), ("Recalled", "clawed_neg", "£"), ("= Investment Pool", "pool", "=£")],
    "lev": [("Outstanding Credit", "debt", "£"), ("/ income it is measured on", "lev_income", "£"), ("= Leverage (months)", "lev", "=2"),
            ("Stress past the safe line", "stress", "%0"), ("Panic Threshold", "panic_at", "1")],
    "panic": [("Panic Threshold", "panic_at", "1"), ("Months left", "panic", "0"), ("Months run", "elapsed", "0"),
              ("Length set at the start", "panic_len", "0"), ("Construction cut", "cut_shown", "%0"), ("Calm months left", "panic_cd", "0")],
    "bad": [("Bad Debts", "crunch", "1"), ("Felt now", "bite", "1"), ("Fade a month once felt", "crunch_fade", "1"),
            ("Lending x", "crunch_lend", "x2"), ("Throughput", "bad_tp", "+%1"), ("Investment", "bad_inv", "+%1")],
    "out": [("Leverage bonus", "bonus_tp", "+%1"), ("Panic", "panic_tp", "+%1"), ("Bad Debts", "bad_tp", "+%1"),
            ("= Throughput", "tp", "=+%1"), ("Investment", "inv", "+%1"), ("GDP against no market", "gdp_gap", "+%1")],
}


# ---------- the engine ----------
class _Tiled:
    """A generator for `c` copies of the same economies: each draw is made once, for one copy's share, and repeated, so a
    batch of candidates sees the very draws each would see alone (the economies' first axis is copy-major)."""
    def __init__(self, g, c):
        self.g, self.c = g, c

    def _do(self, f, size, *a, **kw):
        shape = (size,) if np.isscalar(size) else tuple(size)
        assert shape[0] % self.c == 0, shape  # a draw not one per economy would set the copies apart
        x = f(*a, size=(shape[0] // self.c, *shape[1:]), **kw)
        return np.tile(x, (self.c,) + (1,) * (x.ndim - 1))

    def random(self, size): return self._do(self.g.random, size)
    def normal(self, loc, scale, size): return self._do(self.g.normal, size, loc, scale)
    def uniform(self, lo, hi, size): return self._do(self.g.uniform, size, lo, hi)
    def integers(self, lo, hi, size): return self._do(self.g.integers, size, lo, hi)
    def choice(self, a, size, p=None): return self._do(self.g.choice, size, a, p=p)


def _first(conds, vals, default):
    """np.select (the first true condition's value) as a chain of np.where: same result, a fraction of the time."""
    out = default
    for c, v in zip(conds[::-1], vals[::-1]):
        out = np.where(c, v, out)
    return out


def _draw(rng, lohi, n, log=False):
    """Uniform in the range; log: even on a log scale, for a figure the logs have mostly small with a few large."""
    lo, hi = (lohi, lohi) if np.isscalar(lohi) else lohi
    if hi <= lo:
        return np.full(n, float(lo))
    if log:
        lo = max(lo, hi / 1000)
        return lo * (hi / lo) ** rng.random(n)
    return rng.uniform(lo, hi, n)


class Economies:
    """N economies stepped in lockstep. Variables mirror the mod's (spec_<name>); a 'has_variable' is a flag or > 0."""

    def __init__(self, K, cfg, bot, n, seed, trace=False, keep=0, copies=1):
        self.keep, self.kept = keep, []  # the first `keep` economies' monthly inputs, for fit.py's comparison with the logs
        self.K, self.n, self.trace = K, n, trace
        tile = (lambda g: _Tiled(g, copies)) if copies > 1 else (lambda g: g)  # batch(): copies of one set of economies
        rng = self.rng = tile(np.random.default_rng(seed))
        I = {k: cfg["inputs"].get(k, v[0]) for k, v in INPUTS.items()}
        self.I = I
        self.months = int(I["years"] * 12)
        p = lambda mix: np.array(list(mix.values())) / sum(mix.values())
        self.econ = rng.choice(list(cfg["econ_mix"]), n, p=p(cfg["econ_mix"])).astype(object)
        self.money_base = rng.choice(list(cfg["money_mix"]), n, p=p(cfg["money_mix"])).astype(object)
        self.tech_at = {t: rng.integers(int(lo * 12), int(hi * 12) + 1, n) for t, (lo, hi) in cfg["tech_years"].items()}
        draw = lambda k: _draw(rng, I[k], n)
        self.pool_share, self.pool_sd, self.spend = draw("pool_share"), draw("pool_noise"), draw("pool_spend")
        self.grow, self.gdp_sd = draw("growth") / 12, draw("gdp_noise")
        self.rec_p, self.rec_depth = draw("recessions") / 1200, draw("recession_depth")
        self.goods = np.floor(draw("goods")).astype(int)
        G = GOODS_MAX
        self.share = _draw(rng, I["good_share"], n * G).reshape(n, G) * (np.arange(G) < self.goods[:, None])
        self.w = np.minimum(self.share / self.kg("EXPOSURE_FULL"), 1)
        self.boom_p = _draw(rng, I["boom_rate"], n, log=True)[:, None] / 12 * (self.share > 0)
        # a few countries see most of the wars and foreign panics: their rates even on a log scale
        self.f_p, self.war_p = _draw(rng, I["foreign_rate"], n, log=True) / 1200, _draw(rng, I["war_rate"], n, log=True) / 1200
        self.appr_sd, self.legit, self.sdebt, self.reserves = draw("approval_sd"), draw("legitimacy"), draw("scaled_debt"), draw("reserves")
        self.depth, self.steady = draw("depth"), draw("steady")
        # the world beyond: capital flight, the Long Depression and war endings, from their own draws so the ones above stay
        r2 = self.rng2 = tile(np.random.default_rng([seed, 2]))
        self.flight_p = _draw(r2, I["flight_rate"], n) / 1200 * (r2.random(n) < _draw(r2, I["flight_share"], n))
        self.ld_at, self.ld_dep, self.ld_in = self.plan_depression(r2, I)
        self.auth = _draw(r2, I["ai_authority"], n, log=True)
        self.trust = np.full(n, centres.CALM / 2)  # centres._trust: every country's Exchange starts Respected
        self.rule = "heightened" if I["heightened"] else "historical"
        self.money, self.law_mult, self.panic_mult, self.alloc = self.money_base.copy(), np.ones(n), np.ones(n), np.ones(n)
        # journal.reform_parts: the Monetary Standard's, times the institutions a Commission of Inquiry made (the AI's only)
        self.reform = {k: np.ones(n) for k in ("boom", "heat", "risk", "panic_len", "rescue", "credit")}
        self.enacted = {r: np.zeros(n, bool) for r in journal.REFORMS}
        self.set_laws(range(n))
        self.drift = self.plan_drift(tile(np.random.default_rng([seed, 1836])), cfg.get("law_drift", LAW_DRIFT))
        # the AI's temperament (credit_ai.TEMPERS, without the ruler traits) and the interest groups in government
        w = np.stack([np.full(n, float(b)) for _, (b, adds) in sorted(credit_ai.TEMPERS.items())], 1)
        for i, (_, (b, adds)) in enumerate(sorted(credit_ai.TEMPERS.items())):
            for trig, a in adds:
                m = re.search(r"law_type:law_(\w+)", trig)
                if m:
                    w[:, i] += a * (self.econ == m.group(1))
        cum = np.cumsum(w / w.sum(1, keepdims=True), 1)
        self.temper = (rng.random(n)[:, None] > cum).sum(1) - 1
        ig = sum(pref * K["IG_SHIFT"] * (rng.random(n) < 0.5) for pref in credit_ai.PREFS.values())
        self.lean = self.temper * K["TEMPER_SHIFT"] + ig
        self.bot_name = bot
        self.pol = ai_policy(K, self.temper, self.lean) if BOTS[bot] == "ai" else BOTS[bot]
        # state
        z, f = np.zeros(n), np.zeros(n, bool)
        self.m = 0
        self.did_convert = np.zeros(n, bool)
        W = world() if self.I.get("world_replay", 0) else None
        self.replay = W  # each economy replays one logged country, from its own draw so the others stay
        self.pick = tile(np.random.default_rng([seed, 3])).integers(0, len(W["t"]), n) if W else None
        r5 = self.rng5 = tile(np.random.default_rng([seed, 5]))  # the stand-ins, on their own draws so the others stay
        self.after_p, self.rough_sd = _draw(r5, I["after_panic"], n), _draw(r5, I["rough_sd"], n)
        self.rough_keep = 0.5 ** (1 / np.maximum(_draw(r5, I["rough_months"], n), 0.1))
        self.rough, self.since_end = np.zeros(n), np.full(n, 10 ** 6)
        self.gdp_base = np.full(n, 1e7)
        self.pool_base_x = np.ones(n)
        self.gdp = self.gdp_base.copy()
        self.gdp_avg = self.gdp.copy()
        self.pool = self.gdp * self.pool_share
        self.conf, self.stance, self.debt, self.c_mood = np.full(n, K["CONF_START"], float), z.copy(), z.copy(), z.copy()
        self.lax = np.full(n, K["LAX_START"], float)
        self.lev_avg, self.lev_last = np.full(n, np.nan), np.full(n, np.nan)
        self.held, self.crunch, self.bite, self.bailed = z.copy(), z.copy(), z.copy(), f.copy()
        self.heat, self.has_heat, self.mania, self.mania_ago = z.copy(), f.copy(), f.copy(), np.full(n, 10 ** 6)
        self.panic, self.in_panic, self.panic_len, self.elapsed, self.cut, self.rescued = z.copy(), f.copy(), z.copy(), z.copy(), z.copy(), f.copy()
        self.panic_cd, self.stance_cd, self.fever, self.xs_bad = z.copy(), z.copy(), f.copy(), z.copy()
        self.appr, self.war_left, self.war_c, self.ld_recent = z.copy(), z.copy(), z.copy(), z.copy()
        # the AI's journal (journal.MONTHLY_AI): months without a panic, an inquiry since the last, months left of a sitting
        # Commission (-1 none), of the conversion's cooldown and of the moral hazard after the Bank Act is suspended
        self.calm_m, self.inquired, self.sitting, self.converted, self.hazard = z.copy(), f.copy(), np.full(n, -1), z.copy(), z.copy()
        self.mania_pick = np.full(n, -1)
        # goods (exposure.py's spec_exp_<g>, generate.values' spec_peak/spec_sev, and a boom episode each)
        self.h, self.peak, self.exp = np.ones((n, G)), np.ones((n, G)), np.zeros((n, G))
        self.ep_t, self.ep_d, self.ep_x, self.ep_end = np.full((n, G), -1), np.ones((n, G)), np.zeros((n, G)), np.ones((n, G))
        self.glut = np.zeros((n, G))
        self.lever, self.push, self.risk, self.h_raw = np.zeros((n, G), int), np.ones((n, G)), np.zeros((n, G)), np.ones((n, G))  # levers.py: -1 Restrain, 1 Encourage
        # results
        self.stats = {k: z.copy() for k in ("panics", "panic_months", "panic_len_sum", "mania_months", "manias", "mania_panics",
                                           "bursts", "crunch_max", "crunch_months", "crunch_spells", "frozen", "rescues", "rescue_cost", "bailouts",
                                           "bailout_cost", "restrains", "restrain_months", "reforms", "tight_months", "loose_months", "lev_sum", "lev_max", "gdp_gap_sum",
                                           "pool_gap_sum", "conf_sum", "lent_sum", "debt_sum")}
        self.was_bad = f.copy()
        self.hist = [] if trace else None
        self.snap = []

    def plan_depression(self, r, I):
        """depression.py's Long Depression as each economy meets it: (start month or -1, Depression months, joins) for the
        first and a possible second. Its year is rolled from EARLIEST_YEAR, then it waits for a Great Power's panic (ld_wait);
        a second follows in SECOND_CHANCE of games, COOLDOWN_YEARS after the first's Recovery. ponytail: who joins (ties to
        the origin, chains in the Crash) is a share, ld_join, plus a panic of our own within the window (ld_phase)."""
        n, D = self.n, depression
        wait = lambda: np.round(_draw(r, I["ld_wait"], n) * 12)
        first = np.round((D.EARLIEST_YEAR - 1836 + r.uniform(0, D.EARLIEST_SPREAD, n)) * 12) + wait()
        dep = np.stack([np.round(_draw(r, I["ld_months"], n)) for _ in range(2)])
        again = r.random(n) < D.SECOND_CHANCE / 100
        second = np.where(again, first + D.CRASH_MONTHS + dep[0] + D.RECOVERY_MONTHS + D.COOLDOWN_YEARS * 12 + wait(), -1)
        joins = np.stack([r.random(n) < _draw(r, I["ld_join"], n) for _ in range(2)])
        return np.stack([first, second]).astype(int), dep, joins

    def ld_phase(self):
        """The Long Depression's phase this month (depression.PHASES, 0 outside it) where it reached us."""
        D, out = depression, np.zeros(self.n, int)
        for at, dep, joins in zip(self.ld_at, self.ld_dep, self.ld_in):
            t = self.m - at
            joins |= (at >= 0) & (t == 0) & ((self.ld_recent > 0) | self.in_panic)  # depression.ON_PANIC's window
            ph = _first([t < 0, t < D.CRASH_MONTHS, t < D.CRASH_MONTHS + dep, t < D.CRASH_MONTHS + dep + D.RECOVERY_MONTHS], [0, 1, 2, 3], 0)
            out = np.where((at >= 0) & joins, np.maximum(out, ph), out)
        return out

    def war_ending(self, r, ended):
        """diplomacy.war_actions: a war's end moves confidence once, WAR_END by outcome and war goal, times the stakes
        (WAR_STAKES_MIN to 1). The outcomes and stakes are the logs' (WAR_ENDS, WAR_STAKES)."""
        n = self.n
        u, goal, s, between = r.random(n), r.random(n), r.random(n), r.uniform(diplomacy.WAR_STAKES_MIN, 1, n)
        jump, lo = np.zeros(n), 0.0
        for kind, (share, with_goal) in WAR_ENDS.items():
            full, plain = diplomacy.WAR_END[kind]
            jump = np.where((u >= lo) & (u < lo + share), np.where(goal < with_goal, full, plain), jump)
            lo += share
        at_min, at_full = WAR_STAKES
        stakes = np.where(s < at_min, diplomacy.WAR_STAKES_MIN, np.where(s >= 1 - at_full, 1, between))
        return np.where(ended, jump * stakes, 0)

    def set_laws(self, idx):
        """The laws' multipliers for the economies in idx; the Monetary Standard's variant beside its Economic System (monetary.SWAP)."""
        for i in idx:
            e, m = self.econ[i], self.money_base[i]
            m = next((v for v, (par, ec, *_) in monetary.VARIANTS.items() if par == m and ec == e), m)
            self.money[i], (self.law_mult[i], self.panic_mult[i]), self.alloc[i] = m, LAWS[e], ALLOC.get(e, 0.5)
            for k, a in self.reform.items():
                a[i] = MONEY.get(m, {}).get(k, 1.0) * math.prod(fx.get(k, 1) for r, fx in journal.REFORMS.items() if self.enacted[r][i])

    def plan_drift(self, rng, rows):
        """LAW_DRIFT's moves, drawn at the start: (kind, month or -1, law moved to) a row."""
        n, out = self.n, []
        plan, after = {"econ": self.econ.copy(), "money": self.money_base.copy()}, {"econ": np.full(n, -1), "money": np.full(n, -1)}
        for kind, frm, to, share, lo, hi in rows:
            move = (plan[kind] == frm) & (rng.random(n) < share)
            at = np.where(move, np.maximum(rng.integers(int(lo * 12), int(hi * 12) + 1, n), after[kind] + 1), -1)
            dest = rng.choice(list(to), n, p=np.array(list(to.values()), float) / sum(to.values())).astype(object)
            plan[kind], after[kind] = np.where(move, dest, plan[kind]), np.where(move, at, after[kind])
            out.append((kind, at, dest))
        return out

    def has(self, tech):
        return self.m >= self.tech_at[tech] if tech in self.tech_at else np.zeros(self.n, bool)

    # ---- spec_values: script values read in the pulse ----
    def pool_month(self):
        return self.pool_base * self.pool_inv  # spec_pool_month (investment_pool_gross_income x WEEKS_PER_MONTH), felt

    def lev_income(self, pm):  # leverage.values: spec_lev_income
        li = np.maximum(pm, self.gdp * self.K["LEV_INCOME_FLOOR"])
        return np.where(np.isnan(self.lev_avg), li, np.maximum(li, self.lev_avg))

    def lev(self, pm):  # leverage.values: spec_lev (no land lost, so spec_lev_adj and spec_lev_bad are spec_lev)
        li = self.lev_income(pm)
        return np.where(li > 1, np.maximum(self.debt / np.maximum(li, 1), 0),
                        np.where((self.debt > 0) & ~np.isnan(self.lev_last), np.nan_to_num(self.lev_last), 0))

    def stress(self, lev):  # leverage.values: spec_lev_stress
        K = self.K
        return np.clip((lev - K["LEV_SAFE"]) / (K["LEV_RUIN"] - K["LEV_SAFE"]), 0, 1)

    def shallow(self):  # generate.values: spec_shallow
        return np.clip((1 - self.depth) / (1 - self.K["DEPTH_MIN"]), 0, 1)

    def panic_at(self, lev):  # leverage.values: spec_panic_at
        return self.K["PANIC"] + self.stress(lev) * self.K["LEV_PANIC_SPAN"] - self.shallow() * self.K["PANIC_SHALLOW"]

    def stance_hype(self):  # generate.values: spec_stance_hype
        return np.where(self.stance == -1, g.STANCE_HYPE["tight"], np.where(self.stance == 1, g.STANCE_HYPE["loose"], 1.0))

    def band_gain(self):  # generate.values: spec_band_gain
        c, bg = self.conf, g.BAND_GAIN
        return np.where(c < BANDS[1][2], bg["wary"], np.where(c >= self.K["MANIA"], bg["mania"], np.where(c >= BANDS[3][1], bg["buoyant"], 1.0)))

    def lax_k(self, key):  # cycle.values: spec_lax_<k>
        return (self.lax - 0.5) * 2 * self.K[key] + 1

    def crunch_lend(self):  # leverage.values: spec_crunch_lend
        return np.maximum(1 - self.crunch / (self.K["LEV_BAD_STOP"] * self.lax_k("LAX_BADSTOP")), 0)

    def credit_limit(self):  # leverage.limit (centres' and power blocs' additions not modelled)
        lim = np.full(self.n, self.K["LADDER"][0], float)
        L = self.K["LADDER"]  # its first rung is LEV_SAFE: a batch's per-economy array
        for t, a, b in zip(LADDER_TECHS, L, L[1:]):
            lim += (b - a) * self.has(t)
        return np.minimum(lim, self.K["LEV_RUIN"])

    def fin_boom(self):  # generate.values: spec_fin_boom
        v = np.full(self.n, self.K["FIN_BOOM_BASE"], float)
        for t, a in g.FIN_BOOM.items():
            v += a * self.has(t)
        return v * np.where(self.has(g.FIN_LEVERAGE[0]), g.FIN_LEVERAGE[1], 1) * self.reform["boom"]

    def fin_risk(self):  # generate.values: spec_fin_risk
        v = np.ones(self.n)
        for t, a in [*g.FIN_RISK.items(), g.FIN_LEVERAGE]:
            v *= np.where(self.has(t), a, 1)
        return v * self.reform["risk"]

    def rescue_months(self):  # generate.values: spec_rescue_months
        return np.where(self.has("central_banking"), self.K["RESCUE_MONTHS"], self.K["RESCUE_MONTHS_PRIVATE"]) - self.enacted["llr"]  # spec_reform_rescue_months

    def rescue_cost(self):  # generate.values: spec_rescue_cost, as a share of GDP before the rounding to 1000
        K = self.K
        share = np.where(self.has("central_banking"), K["RESCUE_COST"], K["RESCUE_COST_PRIVATE"]) * self.reform["rescue"] * self.lax_k("LAX_COST")
        share = np.maximum(share, K["RESCUE_FLOOR"])
        return share * np.clip(self.panic / K["RESCUE_REF_MONTHS"], 1, 2)

    def kg(self, k):
        """A setting beside the per-good arrays: in a batch (engine.batch), its per-economy array as a column."""
        v = self.K[k]
        return v[:, None] if np.ndim(v) else v

    def crunch_fade(self):  # leverage.values: spec_crunch_fade
        return np.where(self.stance == -1, self.K["LEV_CRUNCH_FADE_TIGHT"], self.K["LEV_CRUNCH_FADE"])

    # ---- the game's side: this month's inputs ----
    def inputs(self):
        r, n, K = self.rng, self.n, self.K
        rec = r.random(n) < self.rec_p
        self.gdp_base *= np.exp(self.grow + r.normal(0, 1, n) * self.gdp_sd) * np.where(rec, 1 - self.rec_depth, 1)
        self.pool_base_x = np.clip(self.pool_base_x * 0.8 + 0.2 + r.normal(0, 1, n) * self.pool_sd, 0.04, 3)
        self.pool_base = self.gdp_base * self.pool_share * self.pool_base_x
        self.u = r.random((n, GOODS_MAX))  # one fixed set of draws a month: the same months whatever the mechanics do
        war_was = self.war_left
        self.war_left = np.where(self.war_left > 0, self.war_left - 1,
                                 np.where(r.random(n) < self.war_p, np.round(_draw(r, self.I["war_months"], n, log=True)), 0))
        self.war_c = np.where(self.war_left > 0, np.where(self.war_c > 0, self.war_c, _draw(r, self.I["war_cost"], n, log=True)), 0)
        self.foreign = np.where(r.random(n) < self.f_p, K["CONTAGION"] * _draw(r, self.I["foreign_size"], n, log=True), 0)
        r2 = self.rng2  # the world beyond: capital flight from a panic elsewhere, and how a war that ended this month ended
        self.flight = np.where(r2.random(n) < self.flight_p, _draw(r2, self.I["flight_size"], n, log=True), 0)
        self.war_end = self.war_ending(r2, war_was == 1)
        self.ai_u2 = r2.random((n, 3))  # the AI's journal rolls
        W = self.replay
        if W:  # the drawn wars above still run, for the draws' sake, but the replayed ones count
            k = self.m % W["t"].shape[1]
            f = W["f"][self.pick, k]
            self.rp_turmoil = W["t"][self.pick, k]
            self.rp_foreign = np.where(f < 0, f * self.K["CONTAGION"] / W["contagion"], f)  # a hit scales with Contagion
            self.war_end = W["w"][self.pick, k]
        # spare Authority moves with decrees, laws and wars: a fresh draw every AUTH_YEARS on average
        self.auth = np.where(r2.random(n) < 1 / (AUTH_YEARS * 12), _draw(r2, self.I["ai_authority"], n, log=True), self.auth)
        self.mood_u = r.uniform(-1, 1, n)
        self.appr = self.appr * 0.95 + r.normal(0, 1, n) * self.appr_sd
        self.ep_draw = tuple(_draw(r, self.I[k], n * GOODS_MAX).reshape(n, GOODS_MAX) for k in ("boom_months", "boom_peak", "boom_fall"))
        self.ai_u = r.random((n, 4))

    def feedback(self):
        """The mod's modifiers back into the economy (generate.modifiers, leverage.modifiers): throughput moves GDP by
        e_gdp, the investing classes' investment moves pool income by e_pool. ponytail: a level, not a growth path."""
        K = self.K
        pm = np.where(self.rescued, K["RESCUE_CUT"], 1.0) * self.in_panic
        band = _first([self.conf < b[2] for b in BANDS], [g.BAND_INVEST[b[0]] for b in BANDS], g.BAND_INVEST["mania"])
        band = np.where(self.in_panic & (self.conf < BANDS[0][2]), 0, band)  # spec_conf_panic_held carries no investment
        self.bonus_tp, self.panic_tp, self.bad_tp = self.held * K["LEV_REWARD"], pm * K["PANIC_THROUGHPUT"], -self.bite * K["LEV_CRUNCH_THROUGHPUT"]
        self.bad_inv = -self.bite * K["LEV_CRUNCH_INVEST"]
        self.lever_tp = (self.lever * self.share).sum(1) * levers.LEVER_THROUGHPUT  # the levered goods' producers
        self.tp = self.bonus_tp + self.panic_tp + self.bad_tp + self.lever_tp
        self.inv = band + pm * K["PANIC_INVEST"] + self.bad_inv
        self.gdp = self.gdp_base * np.maximum(1 + self.I["e_gdp"] * self.tp, 0.05)
        self.pool_inv = np.maximum(1 + self.I["e_pool"] * self.inv, 0.02)

    # ---- one month: spec_monthly in order ----
    def step(self):
        K, n = self.K, self.n
        for kind, at, dest in self.drift:  # a law changed this month
            due = at == self.m
            if due.any():
                (self.econ if kind == "econ" else self.money_base)[due] = dest[due]
                self.set_laws(np.flatnonzero(due))
        self.inputs()
        self.feedback()
        self.exch_mood, self.exch_recover, _ = centres.links(self.trust, 0)  # the Exchange's links (centres._links_values)
        ld = self.ld_phase()
        c_world = np.array([0] + [depression.PRESSURE.get(p, depression.PRESSURE.get(str(p), 0)) for p in (1, 2, 3)], float)[ld]
        pm = self.pool_month()
        self.cut_shown = self.cut * np.where(self.rescued, K["RESCUE_CUT"], 1) * self.in_panic
        spend = self.pool * self.spend * (1 - self.alloc * self.cut_shown)  # construction draws on the pool between pulses
        self.pool = self.pool - spend + pm
        pool_was, debt_was, lax_was, conf_was = self.pool.copy(), self.debt.copy(), self.lax.copy(), self.conf.copy()
        c_burst, c_drop, c_rescue, c_caution, recall, clawed, writeoff = (np.zeros(n) for _ in range(7))
        self.xs_bad = np.zeros(n)  # leverage.CLEAR_DROP

        # goods (generate.monthly's per-good block): interest, peak, booms and their endings
        hm = self.law_mult * self.stance_hype() * np.where(self.has("joint_stock_companies"), vt.STOCK_HYPE, 1) * self.depth * self.band_gain()
        hmd = self.law_mult * np.minimum(self.stance_hype(), 1) * np.where(self.has("joint_stock_companies"), vt.STOCK_HYPE, 1) * self.depth
        D, X, E = self.ep_draw
        start = (self.ep_t < 0) & (self.glut <= 0) & (self.u < self.boom_p)
        self.ep_t = np.where(start, 0, np.where(self.ep_t >= 0, self.ep_t + 1, -1))
        self.ep_d, self.ep_x, self.ep_end = np.where(start, np.round(D), self.ep_d), np.where(start, X, self.ep_x), np.where(start, E, self.ep_end)
        ph = self.ep_t / np.maximum(self.ep_d, 1)
        rising = ph <= 0.6
        ex = self.ep_x * np.where(rising, ph / 0.6, (1 - ph) / 0.4)
        h = 1 + ex * np.where(rising, hm[:, None], hmd[:, None])  # ponytail: one boom's trend as a rise and fall, x the multipliers
        h = np.clip(h, 1 / self.kg("HYPE_MAX"), self.kg("HYPE_MAX"))
        fallen = (self.ep_t >= self.ep_d)
        h = np.where(fallen, self.ep_end, np.where(self.ep_t >= 0, h, 1.0))
        self.glut = np.maximum(self.glut - 1, 0)
        h = np.where(self.glut > 0, self.kg("GLUT_HYPE"), h)
        # the speculation levers (levers.push_values, hype_push): LEVER_EASE of the way to the full push at last month's confidence
        self.h_raw = h
        mp = (self.conf / K["CONF_START"])[:, None]
        full = np.where(self.lever < 0, mp / (mp + 1 / levers.PUSH["restrain"] - 1), np.where(self.lever > 0, 1 + (levers.PUSH["encourage"] - 1) * mp, 1))
        self.push = np.where(self.lever != 0, self.push + (full - self.push) * levers.LEVER_EASE, 1)
        h = np.clip(h * self.push, 1 / self.kg("HYPE_MAX"), self.kg("HYPE_MAX"))
        h = np.where(self.lever < 0, np.maximum(h, levers.RESTRAIN_TO), h)
        self.h = h
        keep = np.where(self.lever < 0, g.RESTRAIN_DEFLATE, 0.97)  # restrained, the peak deflates faster
        nxt = np.where(h > self.peak, h, self.peak * keep + (1 - keep))  # spec_peak_next
        wind = np.where(self.lever < 0, np.maximum(self.peak - nxt, 0), 0)  # spec_restrain_cost, before its rate
        self.peak = nxt
        sev = _first([self.peak >= p for _, p, *_ in g.UNWINDS], [s for s, *_ in g.UNWINDS], 0)  # spec_sev_next
        booming = h >= self.kg("HOT_HYPE")
        self.n_boom = booming.sum(1)
        boom_raw = (self.w * booming).sum(1) * K["CONF_PER_HOT"]
        lev0 = self.lev(pm)
        exp_mult = np.minimum(1 + self.exp * lev0[:, None] * self.kg("EXP_PER_MONTH"), self.kg("EXP_MULT_MAX"))  # exposure: spec_exp_mult
        rate = {1: self.kg("CORRECTION_PER_HYPE"), 2: self.kg("BUST_PER_HYPE"), 3: self.kg("CONF_PER_CRASH_HYPE")}
        months = {s: m for s, *_, m in g.UNWINDS}
        below = {s: b for s, _, b, *_ in g.UNWINDS}
        ends = np.zeros_like(h, bool)
        rr = np.zeros_like(h)
        for s in (3, 2, 1):
            e = (sev == s) & (h < below[s])
            ends |= e
            rr += e * (self.peak - 1) * rate[s] * self.w * exp_mult
            self.glut = np.where(e, months[s], self.glut)
        crash_raw = rr.sum(1)
        restrain_raw = (wind * rate[1] * self.w * exp_mult).sum(1)  # a restrained boom winds down as a Correction
        self.peak = np.where(ends, 1, self.peak)
        self.exp = np.where(ends, self.exp * 0.5, self.exp)  # exposure.ended
        done = ends | (fallen & (sev == 0))
        self.ep_t = np.where(done, -1, self.ep_t)
        self.n_end = ends.sum(1)

        # the month's pushes, capped and scaled (generate.monthly after the goods)
        boom_cap = np.minimum(boom_raw, K["CONF_BOOM_MAX"])
        crash_scale = self.conf / K["CONF_START"] * self.depth * self.steady * self.fin_risk()  # spec_crash_scale
        c_crash = np.maximum(-crash_raw * crash_scale, -K["CONF_CRASH_MAX"])
        c_restrain = np.maximum(-restrain_raw * crash_scale, -K["CONF_CRASH_MAX"] - c_crash)  # spec_boom_floor
        sev_rate = _first([sev == s for s in (1, 2, 3)], [rate[s] for s in (1, 2, 3)], 0)
        self.risk = np.minimum((self.peak - 1) * sev_rate * self.w * exp_mult * crash_scale[:, None], self.kg("CONF_CRASH_MAX"))  # spec_risk_next
        fb = self.fin_boom()
        c_boom = boom_cap * self.steady * fb * g.VOLATILITY[self.rule]["boom"]
        c_boom = np.where(self.in_panic, 0, c_boom)
        # turmoil: wars (diplomacy.WAR_MONTHLY, abstracted), debt drag (vanilla_ties), growth and business (economy.MONTHLY)
        c_turmoil = self.rp_turmoil if self.replay else -self.war_c
        c_debt = np.where(self.sdebt > vt.DEBT_FROM, np.maximum((self.sdebt - vt.DEBT_FROM) * -K["DEBT_MAX"] / (1 - vt.DEBT_FROM), -K["DEBT_MAX"]), 0)
        growth = (self.gdp - self.gdp_avg) / self.gdp_avg
        c_growth = np.clip((growth - K["GROWTH_NORMAL"]) * K["GROWTH_K"], -K["GROWTH_MAX"], K["GROWTH_MAX"])
        self.gdp_avg = self.gdp_avg * K["GROWTH_KEEP"] + self.gdp * (1 - K["GROWTH_KEEP"])
        appr = self.appr + K["PANIC_APPROVAL"] * self.in_panic * np.where(self.rescued, K["RESCUE_CUT"], 1)
        c_business = np.zeros(n)
        hit = np.zeros(n, bool)
        for op, at, val in economy.BUSINESS:
            m = ~hit & ((appr >= at) if op == ">=" else (appr <= at))
            c_business, hit = np.where(m, val, c_business), hit | m
        c_foreign = -self.foreign * np.where(self.has(g.UNSTANDARD[0]), 1, g.UNSTANDARD[1])  # spec_catch_panic's spec_foreign_loss_mult
        safe = (self.conf >= diplomacy.FLIGHT_FROM) & ~self.in_panic & (self.war_left <= 0) & (self.foreign <= 0)  # spec_capital_flight
        c_foreign += np.where(safe, self.flight, 0)  # diplomacy.MONTHLY adds spec_c_flight to spec_c_foreign
        if self.replay:  # the log's figure has the Currency Standards multiplier and the flight gate in it already
            c_foreign = self.rp_foreign
        # Market Mood (spec_mood_roll is a hash of the month's figures: a uniform draw stands in)
        self.c_mood *= K["MOOD_KEEP"]
        mood_scale = (self.shallow() * (K["MOOD_SHALLOW"] - 1) + 1) * self.exch_mood
        self.c_mood += self.mood_u * K["MOOD_SHOCK"] * mood_scale
        macro = np.where(self.has(g.MACRO[0]), g.MACRO[1], 1)
        c_recover = (K["CONF_START"] - self.conf) * K["CONF_RECOVER"] * macro * self.exch_recover  # spec_conf_recover
        # the stand-ins (fit.py's roughness block): a slow swing (AR(1), rough_sd its spread), and the year after a panic
        self.rough = self.rough * self.rough_keep + self.rng5.normal(0, 1, n) * self.rough_sd * np.sqrt(1 - self.rough_keep ** 2)
        c_rough = self.rough - np.where(self.since_end < 12, self.after_p, 0)
        pre = (self.conf + c_recover + c_boom + c_crash + c_turmoil + c_debt + c_foreign + self.c_mood + c_growth + c_business + c_world
               + self.war_end + c_restrain + c_rough)
        c_tight = np.where(self.stance == -1, np.minimum((K["TIGHT_FROM"] - pre) * K["TIGHT_PULL"], 0), 0)  # spec_tight_pull
        nxt = np.clip(pre + c_tight, 0, 100)
        c_limit = nxt - pre - c_tight
        self.conf = nxt

        # credit (generate.monthly): runoff and repayment, then this month's lending
        runoff = np.maximum(self.debt * K["CREDIT_RUNOFF"], 0)
        repaid = np.clip(runoff, 0, np.maximum(self.pool, 0))
        self.pool -= repaid
        self.debt -= runoff
        self.exp = np.where((self.debt < 1)[:, None], 0, self.exp)  # exposure.clear
        lev1 = self.lev(pm)
        p_at = self.panic_at(lev1)
        crunch_lend = self.crunch_lend()
        tech_credit = 0.5 + 0.5 * sum(self.has(t) for t in CREDIT_TECHS)
        stance_credit = np.where(self.stance == -1, g.STANCE_CREDIT["tight"], np.where(self.stance == 1, g.STANCE_CREDIT["loose"], 1.0))
        lax_credit = self.lax_k("LAX_CREDIT")
        credit_base = np.minimum((self.conf - K["CREDIT_FROM"]) / (100 - K["CREDIT_FROM"]) * K["CREDIT_SHARE"], K["CREDIT_FLOW_MAX"])
        ceiling = pm * K["CREDIT_CEILING"]
        climit = np.where(ld == 1, 0, self.credit_limit())  # depression.NO_CREDIT: none in the World Crash
        room = np.maximum(self.lev_income(pm) * climit - self.debt, 0)
        credit = credit_base * pm * self.law_mult * tech_credit * stance_credit * lax_credit * crunch_lend * self.reform["credit"] * self.I["e_credit"]
        credit = np.maximum(np.minimum(np.minimum(credit, ceiling), room), 0)
        lends = (self.conf > K["CREDIT_FROM"]) & ~self.in_panic & (self.stance != -1) & (crunch_lend > 0) & (self.conf >= p_at)
        lent = np.where(lends, credit, 0)
        # exposure.lend: where the new credit goes, before it is added
        pull = self.share * np.clip((self.h - exposure.HEAT_FROM) / (exposure.HEAT_FULL - exposure.HEAT_FROM), 0, 1)
        pt = pull.sum(1)
        boom_share = np.minimum(pt * K["EXP_PULL"] * self.lax_k("LAX_PULL"), K["EXP_SHARE_MAX"])
        d0 = np.maximum(self.debt, 0)
        tot = d0 + lent
        new = np.where(pt > 0, lent * boom_share / np.where(pt > 0, pt, 1), 0)
        upd = (tot > 0)[:, None] & ((self.exp > 0) | (pull > 0))
        self.exp = np.where(upd, np.clip((self.exp * d0[:, None] + pull * new[:, None]) / np.where(tot > 0, tot, 1)[:, None], 0, 1), self.exp)
        self.pool += lent
        self.debt += lent

        # cycle.monthly: Lending Standards drift
        quiet = ~self.in_panic & (self.stance != -1) & ~(self.crunch > 0)
        lax_drift = quiet / (12 * K["LAX_QUIET_YEARS"])
        lax_booms = (c_crash + c_restrain) * K["LAX_PER_CONF"]
        self.lax = np.clip(self.lax + lax_drift + lax_booms, 0, 1)

        # leverage.MONTHLY: the income average, Bad Debts fading and biting, the leverage bonus
        calm = ~self.in_panic & ~(self.crunch > 0)
        self.lev_avg = np.where(calm, np.where(np.isnan(self.lev_avg), pm, self.lev_avg + (pm - self.lev_avg) * K["LEV_INCOME_SMOOTH"]), self.lev_avg)
        li = self.lev_income(pm)
        lev2 = self.lev(pm)
        self.lev_last = np.where(li > 1, lev2, self.lev_last)
        fade = self.crunch_fade()
        had = self.crunch > 0
        self.crunch = np.where(had & (self.bite >= self.crunch), self.crunch - fade, self.crunch)
        gone = had & (self.crunch <= 0)
        self.crunch, self.bite = np.where(gone, 0, self.crunch), np.where(gone, 0, self.bite)
        self.bailed &= ~gone
        self.bite = np.where(had & ~gone, np.minimum(self.bite + K["LEV_CRUNCH_RAMP"], self.crunch), self.bite)
        reward = np.where(self.in_panic | (self.crunch > 0), 0, np.floor(np.minimum(lev2, K["LEV_REWARD_MAX"])))
        lev_now = np.maximum(reward, np.where(self.held > 0, self.held - K["LEV_BONUS_FADE"], 0))
        lev_now = np.where(lent <= 0, np.where(self.held > 0, np.minimum(lev_now, self.held), 0), lev_now)
        self.held = np.maximum(lev_now, 0)

        # mania warning (once per Mania), then Speculative Excess, then the burst
        new_mania = (self.conf >= K["MANIA"]) & ~self.mania
        self.mania |= new_mania
        self.mania_ago = np.where(self.mania, 0, self.mania_ago + 1)
        if BOTS[self.bot_name] == "ai":
            if not hasattr(self, "fever_p"):  # temperament is fixed for the run
                self.fever_p = np.array([K["AI_FEVER"].get(int(t), 0) / 100 for t in (-1, 0, 1)])[self.temper + 1]
            chance = self.fever_p
            self.fever |= new_mania & (self.ai_u[:, 0] < chance)  # leverage.FEVER_ROLL
        self.mania_pick = np.where(new_mania, self.pick_mania(), self.mania_pick)
        heat_from = g.VOLATILITY[self.rule]["heat"]
        grows = (self.conf >= heat_from) & self.has("stock_exchange")
        xs_over = np.where(grows, self.conf - heat_from, 0)
        xs_grow = xs_over * self.reform["heat"] * np.where(self.hazard > 0, journal.HAZARD_HEAT, 1)  # journal.excess_calc: spec_xs_grow
        self.heat = np.where(grows, np.where(self.has_heat, self.heat, 0) + xs_grow, self.heat)
        self.has_heat |= grows
        cools = ~grows & self.has_heat & (self.conf >= K["BURST_BELOW"])
        xs_cool = np.where(cools, self.heat * (np.where(self.stance < 0, K["HEAT_COOL_TIGHT"], K["HEAT_COOL"]) - 1), 0)
        self.heat += xs_cool
        self.has_heat &= ~(cools & (self.heat < 1))
        self.mania &= ~(self.mania & (self.conf < K["MANIA_RESET"]))
        burst = self.has_heat & (self.conf < K["BURST_BELOW"])
        per = g.VOLATILITY[self.rule]["per"]
        xs = self.heat * per - self.conf  # leverage.ON_BURST (spec_nx_burst and spec_nx_bad are 1: no Exchange specialities)
        self.xs_bad = np.where(burst & (xs > 0), xs, 0)
        newc = burst & (xs > 0)
        self.bite = np.where(newc & ~(self.crunch > 0), 0, self.bite)
        self.crunch = np.where(newc, np.where(self.crunch > 0, self.crunch + xs, xs), self.crunch)
        self.bailed &= ~newc
        c_burst = np.where(burst, np.maximum(-self.heat * per, -self.conf), 0)
        self.conf = np.where(burst, np.maximum(self.conf + c_burst, 0), self.conf)
        self.heat, self.has_heat = np.where(burst, 0, self.heat), self.has_heat & ~burst

        # countdowns, then the panic (generate.monthly; spec_start_panic and spec_end_panic in generate.effects)
        self.stance_cd = np.maximum(self.stance_cd - 1, 0)
        self.panic_cd = np.maximum(self.panic_cd - 1, 0)
        was = self.in_panic.copy()
        self.elapsed = np.where(was, self.elapsed + 1, self.elapsed)
        self.panic = np.where(was, self.panic - 1, self.panic)
        end = was & ((self.panic <= 0) | ((self.conf >= K["PANIC_ENDS_AT"]) & (self.elapsed >= K["PANIC_MIN_MONTHS"])))
        lev3 = self.lev(pm)
        p_at = self.panic_at(lev3)
        start = ~was & (self.conf < p_at) & (self.panic_cd <= 0)
        lax_jump = np.where(end & ~self.rescued, -np.minimum(K["LAX_PANIC"], self.lax), 0)  # cycle.panic_over
        over = end & ~self.rescued & (self.panic <= 0)  # centres.PANIC_OVER: it ran its full course unrescued
        self.ld_recent = np.where(start, depression.WINDOW_DAYS // 30, np.maximum(self.ld_recent - 1, 0))
        self.lax += lax_jump
        self.stats["panic_len_sum"] += np.where(end, self.elapsed, 0)
        self.in_panic &= ~end
        self.rescued &= ~end
        self.panic_cd = np.where(end, K["PANIC_COOLDOWN"], self.panic_cd)
        self.since_end = np.where(end, 0, self.since_end + 1)
        if start.any():
            months = np.maximum(np.ceil(K["PANIC_DAYS"] / 30 * self.panic_mult), 1)  # spec_panic_months (spec_nx_panic 1)
            trust = np.clip(1.2 - self.legit / 250, 0.8, 1.2)  # spec_trust_mult
            lev_len = 1 + np.clip(lev3 - K["LEV_SAFE"], 0, K["LEV_RUIN"] - K["LEV_SAFE"]) * K["PANIC_LEV_LEN"]
            months = np.maximum(np.ceil(months * trust * self.reform["panic_len"] * lev_len), 1)  # spec_panic_months_trust
            cut = np.minimum(K["CRUNCH_FLOOR"] + np.maximum(lev3 - K["LEV_SAFE"], 0) * (1 - K["CRUNCH_FLOOR"]) / (K["DANGER"] - K["LEV_SAFE"]), 1)
            self.panic, self.panic_len = np.where(start, months, self.panic), np.where(start, months, self.panic_len)
            self.elapsed, self.cut = np.where(start, 0, self.elapsed), np.where(start, cut, self.cut)
            # leverage.on_panic: the fall to the line, then Bad Debts sized on the stress
            drop = start & (self.conf >= K["PANIC"])
            c_drop = np.where(drop, (K["PANIC"] - 0.1) - self.conf, 0)
            self.conf = np.where(drop, K["PANIC"] - 0.1, self.conf)
            crunch_if = np.maximum(self.stress(lev3) * K["LEV_CRUNCH_MAX"] + self.xs_bad, self.crunch)
            bad = start & (crunch_if > 0)
            self.bailed &= ~(bad & (crunch_if > self.crunch))
            self.crunch = np.where(bad, crunch_if, self.crunch)
            self.bite = np.where(bad, np.minimum(self.bite + K["LEV_CRUNCH_RAMP"], self.crunch), self.bite)
            self.stats["frozen"] += start & (self.crunch_lend() <= 0)
            # the recall: the share Lending Standards call back, out of the pool as far as it can, the rest written off
            req = self.debt * K["CLAWBACK"] * self.lax_k("LAX_RECALL")
            claw_share = np.clip(lev3 / K["DANGER"], K["CLAW_FLOOR"], 1)
            claw = np.maximum(np.minimum(np.minimum(req, np.maximum(self.pool, 0)), np.maximum(self.pool, 0) * claw_share), 0)
            recall, clawed = np.where(start, req, 0), np.where(start, claw, 0)
            self.pool -= clawed
            after = np.maximum(self.debt - req, 0)
            writeoff = np.where(start, self.debt - clawed - after, 0)
            self.debt = np.where(start, after, self.debt)
            self.in_panic |= start
            self.stats["panics"] += start
            self.stats["mania_panics"] += start & (self.mania_ago <= 24)
            self.mania_ago = np.where(start, 10 ** 6, self.mania_ago)  # one panic per Mania counts

        # journal.MONTHLY: months without a panic; a panic clears the last inquiry
        self.calm_m = np.where(self.in_panic, 0, self.calm_m + 1)
        self.inquired &= ~self.in_panic
        self.hazard = np.maximum(self.hazard - 1, 0)
        # the player's levers, or the AI's rules (generate.monthly's is_player = no block)
        c_rescue, c_caution, lax_jump2 = self.decide()
        lax_jump = lax_jump + lax_jump2

        # the Exchange's trust (centres._trust, _crunch, boom_end, spec_exch_panic_cut, PANIC_OVER), for next month's links
        month = np.where(self.lax >= cycle.LAX_CUTS[3], -centres.TRUST_MONTH,
                         np.where((self.crunch <= 0) & (self.lax < cycle.LAX_CUTS[2]), centres.TRUST_MONTH, 0))
        tr = self.trust + np.where(self.in_panic, 0, month) - (self.crunch > 0) * centres.LINK_CRUNCH * centres.CRUNCH
        te = {int(k): d for k, d in centres.TRUST_END.items()}
        tr += (ends * (self.share >= centres.MAIN_SHARE) * _first([sev == s for s in te], list(te.values()), 0)).sum(1)
        cut_t = centres.PANIC_CUT[0] + centres.PANIC_CUT[1] * np.clip((lev3 - K["LEV_SAFE"]) / (K["LEV_RUIN"] - K["LEV_SAFE"]), 0, 1)
        tr = np.where(start, tr * (1 - cut_t), tr) * np.where(over, 1 - centres.PANIC_OVER_CUT, 1)
        self.trust = np.clip(tr, 0, centres.CALM)

        # results
        s = self.stats
        s["panic_months"] += self.in_panic
        s["mania_months"] += self.conf >= K["MANIA"]
        s["manias"] += new_mania
        s["bursts"] += burst
        s["restrain_months"] += c_restrain < -1e-6
        s["crunch_max"] = np.maximum(s["crunch_max"], self.crunch)
        s["crunch_months"] += self.crunch > 0
        s["crunch_spells"] += (self.crunch > 0) & ~self.was_bad
        self.was_bad = self.crunch > 0
        s["tight_months"] += self.stance == -1
        s["loose_months"] += self.stance == 1
        lev4 = self.lev(pm)
        s["lev_sum"] += lev4
        s["lev_max"] = np.maximum(s["lev_max"], lev4)
        s["gdp_gap_sum"] += self.gdp / self.gdp_base - 1
        s["pool_gap_sum"] += self.pool_inv - 1
        s["conf_sum"] += self.conf
        s["lent_sum"] += lent / np.maximum(pm, 1)
        s["debt_sum"] += self.debt
        if self.keep:  # as the log has them: fastsim scales a month's crash by the confidence it started from
            k = self.keep
            self.kept.append(dict(conf=self.conf[:k].copy(), gdp=self.gdp[:k].copy(), pool=pm[:k].copy(), boom=c_boom[:k].copy(), crash=(c_crash * K["CONF_START"] / np.maximum(conf_was, 1))[:k],
                                  foreign=c_foreign[:k].copy(), turmoil=c_turmoil[:k].copy(), business=c_business[:k].copy(), debt=c_debt[:k].copy(),
                                  panic=self.in_panic[:k].copy(), levers=(self.lever[:k] != 0).sum(1) * 1.0, restrain=c_restrain[:k].copy(),
                                  convert=self.did_convert[:k] * 1.0))
        if self.m % SNAP == 0:
            self.snap.append((self.conf.copy(), self.in_panic.copy(), lev4.copy(), self.crunch.copy(), self.lax.copy()))
        if self.trace:
            i = 0
            band = next(b[0] for b in BANDS[::-1] if self.conf[i] >= b[1])
            fr = dict(m=self.m, conf=self.conf[i], conf_was=conf_was[i], c_recover=c_recover[i], c_boom=c_boom[i], c_crash=c_crash[i],
                      c_mood=self.c_mood[i], c_growth=c_growth[i], c_business=c_business[i], c_debt=c_debt[i], c_turmoil=c_turmoil[i],
                      c_foreign=c_foreign[i], c_world=c_world[i], c_warend=self.war_end[i], c_restrain=c_restrain[i], c_rough=c_rough[i], ld=int(ld[i]), trust=self.trust[i], c_tight=c_tight[i], c_limit=c_limit[i], c_burst=c_burst[i], c_drop=c_drop[i],
                      c_rescue=c_rescue[i], c_caution=c_caution[i], band=band, n_boom=self.n_boom[i], boom_raw=boom_raw[i],
                      boom_cap=boom_cap[i], steady=self.steady[i], fin_boom=fb[i], crash_raw=crash_raw[i], crash_scale=crash_scale[i],
                      n_end=self.n_end[i], credit_base=max(credit_base[i], 0), pool_month=pm[i], law_mult=self.law_mult[i],
                      tech_credit=tech_credit[i], stance_credit=stance_credit[i], lax_credit=lax_credit[i], crunch_lend=crunch_lend[i],
                      ceiling=ceiling[i], room=room[i], lent=lent[i], lends=bool(lends[i]), lax_was=lax_was[i], lax_drift=lax_drift[i],
                      lax_booms=lax_booms[i], lax_jump=lax_jump[i], lax=self.lax[i], lax_word=WORDS[int(np.searchsorted(cycle.LAX_CUTS, self.lax[i], "right"))],
                      lax_recall=self.lax_k("LAX_RECALL")[i], xs_over=xs_over[i], reform_heat=self.reform["heat"][i], xs_grow=xs_grow[i],
                      xs_cool=xs_cool[i], xs_bad=self.xs_bad[i], heat=self.heat[i], burst=bool(burst[i]), debt_was=debt_was[i],
                      runoff_neg=-runoff[i], recall_neg=-clawed[i], writeoff_neg=-(recall[i] - clawed[i]), debt=self.debt[i],
                      pool_last=pool_was[i] - pm[i] + spend[i],
                      credit_limit=climit[i], spend_neg=-spend[i], repaid_neg=-repaid[i], clawed_neg=-clawed[i], pool=self.pool[i],
                      pool_was=pool_was[i], repaid=repaid[i], recall=recall[i], clawed=clawed[i], lev_income=li[i], lev=lev4[i],
                      stress=self.stress(lev4)[i], panic_at=self.panic_at(lev4)[i], panic=self.panic[i] * self.in_panic[i],
                      in_panic=bool(self.in_panic[i]), rescued=bool(self.rescued[i]), elapsed=self.elapsed[i] * self.in_panic[i],
                      panic_len=self.panic_len[i] * self.in_panic[i], cut_shown=self.cut_shown[i], panic_cd=self.panic_cd[i],
                      panic_start=bool(start[i]), panic_end=bool(end[i]), crunch=self.crunch[i], bite=self.bite[i],
                      crunch_fade=fade[i], bad_tp=self.bad_tp[i], bad_inv=self.bad_inv[i], bonus_tp=self.bonus_tp[i],
                      panic_tp=self.panic_tp[i], tp=self.tp[i], inv=self.inv[i], gdp_gap=self.gdp[i] / self.gdp_base[i] - 1,
                      held=self.held[i], stance=int(self.stance[i]), mania=bool(self.mania[i]), new_mania=bool(new_mania[i]),
                      boom_share=boom_share[i], pull_lent=lent[i] * boom_share[i], rescue_cost=self.rescue_cost()[i],
                      bailout_cost=self.crunch[i] ** 2 * K["LEV_BAILOUT_COST"], bailed=bool(self.bailed[i]),
                      rescue_now=bool(self.did_rescue[i]), bailout_now=bool(self.did_bailout[i]), stance_now=int(self.did_stance[i]))
            self.hist.append({k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in fr.items()})
        self.m += 1

    def pick_mania(self):
        """The Mania event's option: 0 ride it, 1 the warning, 2 the levy (generate.events, spec_markets.1)."""
        u = self.ai_u[:, 1]
        if self.pol["mania"] is None:  # the AI's ai_chance, by temperament
            w = np.stack([50 + 30 * (self.temper == 1), 30 + 30 * (self.temper == -1), 20 + 20 * (self.temper == -1)], 1).astype(float)
        else:
            w = np.tile(np.array(self.pol["mania"], float), (self.n, 1))
        cum = np.cumsum(w / w.sum(1, keepdims=True), 1)
        return (u[:, None] > cum).sum(1)

    def decide(self):
        """After the pulse: credit policy, Lend to the Banks, Buy Up Bad Loans, then the Mania event's choice."""
        K, P, n = self.K, self.pol, self.n
        is_ai = BOTS[self.bot_name] == "ai"
        lev = self.lev(self.pool_month())
        c_rescue, c_caution, lax_jump = np.zeros(n), np.zeros(n), np.zeros(n)
        self.did_rescue, self.did_bailout, self.did_stance = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n)
        if is_ai:
            self.fever &= ~(~self.mania | self.in_panic)  # leverage.FEVER_END
        can = self.has("central_banking") & (self.stance_cd <= 0)  # generate.triggers: spec_can_stance_*
        fever = self.fever if is_ai else np.zeros(n, bool)
        to_tight = can & (self.stance != -1) & ((self.conf > P["tight_conf"]) | (lev > P["tight_lev"])) & ~fever
        to_normal_t = can & (self.stance == -1) & (self.conf < P["untight_conf"]) & (lev < P["untight_lev"])
        to_loose = can & (self.stance == 0) & (self.conf < P["loose_conf"]) & (lev < P["loose_lev"]) & ~self.in_panic
        to_normal_l = can & (self.stance == 1) & ((self.conf >= P["unloose_conf"]) | self.in_panic)
        if not is_ai:  # a player's loosening: "loose_conf" INF means Loose whenever Normal and calm
            to_tight &= self.stance == 0 if P["tight_conf"] < INF or P["tight_lev"] < INF else to_tight
        new = _first([to_tight, to_normal_t, to_loose, to_normal_l], [-1, 0, 1, 0], self.stance)
        changed = new != self.stance
        self.stance, self.stance_cd = new, np.where(changed, K["STANCE_COOLDOWN"], self.stance_cd)
        self.did_stance = np.where(changed, new + 10, 0)  # +10 so Normal reads as a change
        # Lend to the Banks (spec_rescue): the AI only from money it has, and only with more months left than a rescue takes
        cost = self.rescue_cost()
        can_rescue = self.in_panic & ~self.rescued & self.has("banking")
        if P["afford"]:
            can_rescue &= (self.sdebt < 0.6) & (self.reserves >= cost) & (self.panic > self.rescue_months())
        rescue = can_rescue & (self.ai_u[:, 2] < P["rescue"])
        if rescue.any():
            was = self.conf.copy()
            self.panic = np.where(rescue, np.minimum(self.panic, self.rescue_months()), self.panic)
            self.conf = np.where(rescue, np.minimum(self.conf + K["RESCUE_CONF"], 100), self.conf)
            c_rescue = self.conf - was
            self.rescued |= rescue
            j = np.where(rescue, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)  # cycle.rescued
            self.lax += j
            lax_jump += j
            self.stats["rescues"] += rescue
            self.stats["rescue_cost"] += np.where(rescue, cost, 0)
            self.did_rescue = rescue
        # Buy Up Bad Loans (leverage.bailout_effect), once per spell of Bad Debts
        bcost = self.crunch ** 2 * K["LEV_BAILOUT_COST"]
        can_bail = (self.crunch > 0) & self.has("banking") & ~self.bailed & (self.crunch >= P["bailout_from"])
        if P["afford"]:
            can_bail &= (self.sdebt < 0.6) & (self.reserves >= bcost)
        bail = can_bail & (self.ai_u[:, 3] < P["bailout"])
        if bail.any():
            self.crunch = np.where(bail, self.crunch * (1 - K["LEV_BAILOUT_CUT"]), self.crunch)
            self.bite = np.where(bail, np.minimum(self.bite, self.crunch), self.bite)
            self.bailed |= bail
            j = np.where(bail, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)
            self.lax += j
            lax_jump += j
            self.stats["bailouts"] += bail
            self.stats["bailout_cost"] += np.where(bail, bcost, 0)
            self.did_bailout = bail
        if is_ai:  # journal.MONTHLY_AI, then levers.ai_block
            j_rescue, j_caution, j_lax = self.ai_journal(self.ai_u2)
            c_rescue, c_caution, lax_jump = c_rescue + j_rescue, c_caution + j_caution, lax_jump + j_lax
            self.ai_levers(lev)
        # the Mania event resolves after the pulse (journal.conf_jump through spec_cool_conf)
        pick = self.mania_pick
        amount = np.where(pick == 1, K["MANIA_CAUTION"], np.where(pick == 2, K["MANIA_TAX_CONF"], 0))
        was = self.conf.copy()
        self.conf = np.where(pick >= 0, np.maximum(self.conf - amount, 0), self.conf)
        c_caution += self.conf - was
        self.mania_pick = np.full(n, -1)
        return c_rescue, c_caution, lax_jump

    def ai_journal(self, u):
        """journal.MONTHLY_AI: a Commission of Inquiry when one can sit (10% a month) and the institution it makes when it
        reports (spec_reform.1's ai_chance), debt converted in good times (10%), and the Bank Act suspended when the state
        cannot lend to the banks. Relief Works moves neither confidence nor credit, so it is left out.
        Returns the confidence each moved (rescue, caution) and the Lending Standards jump."""
        K, J, n = self.K, journal, self.n
        note_free = ~(self.enacted["currency"] | self.enacted["free"])
        choices = {"currency": (note_free, 10 + 30 * (self.temper == -1)), "free": (note_free, 10 + 30 * (self.temper == 1)),
                   "llr": (self.has("central_banking") & ~self.enacted["llr"], 25),
                   "company": (self.has("joint_stock_companies") & ~self.enacted["company"], 15)}
        was = self.conf.copy()
        due = self.sitting == 0
        if due.any():  # the report: one institution, or shelved (base 5, SHELVE_CONF)
            w = np.stack([np.where(ok, wt, 0) for ok, wt in choices.values()] + [np.full(n, 5)], 1).astype(float)
            pick = (u[:, 0][:, None] > np.cumsum(w / w.sum(1, keepdims=True), 1)).sum(1)
            for j, r in enumerate(choices):
                self.enacted[r] |= due & (pick == j)
            self.stats["reforms"] += due & (pick < len(choices))
            self.set_laws(np.flatnonzero(due))
            self.conf = np.where(due & (pick == len(choices)), np.minimum(self.conf + J.SHELVE_CONF, 100), self.conf)
        self.sitting = np.maximum(self.sitting - 1, -1)
        # a Commission sits after a panic not yet inquired into, or after INQUIRY_CALM months without one
        open_ = np.any([ok for ok, _ in choices.values()], 0)
        sit = (open_ & ~self.in_panic & (self.sitting < 0) & (((self.panic_cd > 0) & ~self.inquired) | (self.calm_m >= J.INQUIRY_CALM))
               & (u[:, 1] < 0.1))
        self.sitting = np.where(sit, J.INQUIRY_MONTHS - 1, self.sitting)
        self.inquired |= sit
        self.calm_m = np.where(sit, 0, self.calm_m)
        conv = ~self.in_panic & (self.conf >= J.CONVERT_FROM) & (self.sdebt >= J.CONVERT_DEBT) & (self.converted <= 0) & (u[:, 2] < 0.1)
        self.conf = np.where(conv, np.maximum(self.conf - J.CONVERT_CONF, 0), self.conf)
        self.converted = np.where(conv, J.CONVERT_COOLDOWN_YEARS * 12, np.maximum(self.converted - 1, 0))
        self.did_convert = conv
        caution = self.conf - was
        was = self.conf.copy()
        sus = (self.in_panic & self.enacted["currency"] & ~self.rescued & (self.panic > J.SUSPEND_MONTHS)
               & (~self.has("banking") | (self.reserves < self.rescue_cost())))
        self.panic = np.where(sus, np.minimum(self.panic, J.SUSPEND_MONTHS), self.panic)
        self.conf = np.where(sus, np.minimum(self.conf + J.SUSPEND_CONF, 100), self.conf)
        self.rescued |= sus
        lax = np.where(sus, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)  # cycle.rescued
        self.lax += lax
        self.hazard = np.where(sus, J.HAZARD_YEARS * 12, self.hazard)
        return self.conf - was, caution, lax

    def ai_levers(self, lev):
        """levers.ai_block: lift a restraint once its boom has passed, restrain the riskiest boom while confident or lent past
        the safe line, then encourage the most favored Calm good while Wary, each with Authority to spare (self.auth).
        ponytail: every lever costs the same, the budget is taken as enough, and Great Issues are left out (they need an
        Exchange of National Standing)."""
        K, P, n = self.K, self.pol, self.n
        hr = self.h_raw
        lift = (self.lever < 0) & ((self.peak < g.RISING_HYPE) | ((hr < g.HOT_HYPE) & (hr >= g.COOLING_HYPE)))
        self.lever = np.where(lift, 0, self.lever)
        risk = np.where((self.lever == 0) & (self.share > 0), self.risk, 0)
        best = risk.argmax(1)
        free = lambda: self.auth - (self.lever != 0).sum(1) >= 2  # levers.afford, a lever costing 1
        go = ((self.conf >= levers.AI_CONF) | (lev >= K["LEV_SAFE"])) & (risk[np.arange(n), best] >= levers.AI_RISK) & free()
        self.lever[go, best[go]] = -1
        self.stats["restrains"] += go
        stop = (self.conf >= P["unloose_conf"]) | self.in_panic
        self.lever = np.where(stop[:, None] & (self.lever > 0), 0, self.lever)
        calm = (self.lever == 0) & (self.share > 0) & (self.h >= g.COOLING_HYPE) & (self.h < g.RISING_HYPE)
        want = ~stop & (self.conf < P["loose_conf"]) & ~(self.lever > 0).any(1) & calm.any(1) & free()
        pick = np.where(calm, self.h, -1).argmax(1)
        self.lever[want, pick[want]] = 1

    def run(self):
        for _ in range(self.months):
            self.step()
        return self


# ---------- results ----------
METRICS = {  # name: (label, unit)
    "panics_per_century": ("Panics a century", ""), "panic_months_pct": ("Months in panic", "%"),
    "panic_length": ("Panic length", "months"), "mania_pct": ("Months in Mania", "%"),
    "mania_to_panic_pct": ("Manias ending in a panic", "%"), "bursts_per_century": ("Bursts a century", ""),
    "crunch_max": ("Worst Bad Debts", ""), "crunch_months_pct": ("Months with Bad Debts", "%"),
    "frozen_pct": ("Panics that stop bank lending", "%"), "bad_spell": ("Bad Debts last", "months"),
    "lev_mean": ("Leverage, mean", "months"), "lev_max": ("Leverage, worst", "months"),
    "output_pct": ("GDP against no market, after rescue and buy-up costs", "%"), "pool_pct": ("Pool income against no market", "%"),
    "conf_mean": ("Confidence, mean", ""), "tight_pct": ("Months Tight", "%"), "loose_pct": ("Months Loose", "%"),
    "rescues_per_century": ("Rescues a century", ""), "spend_pct_gdp": ("Rescues and buy-ups, % of a year's GDP", "%"),
}


def summarize(e):
    """Per-economy figures, then the 10/50/90% of each across the economies, and the pooled mean."""
    s, T = e.stats, e.months
    cent = 1200 / T
    spend = (s["rescue_cost"] + s["bailout_cost"]) * 100  # % of a year's GDP over the run
    per = {
        "panics_per_century": s["panics"] * cent, "panic_months_pct": s["panic_months"] / T * 100,
        "mania_pct": s["mania_months"] / T * 100, "bursts_per_century": s["bursts"] * cent, "crunch_max": s["crunch_max"],
        "crunch_months_pct": s["crunch_months"] / T * 100, "lev_mean": s["lev_sum"] / T, "lev_max": s["lev_max"],
        # the GDP gap, less rescue and buy-up spending spread over the run (both % of GDP a year)
        "output_pct": s["gdp_gap_sum"] / T * 100 - spend / (T / 12), "pool_pct": s["pool_gap_sum"] / T * 100, "conf_mean": s["conf_sum"] / T,
        "tight_pct": s["tight_months"] / T * 100, "loose_pct": s["loose_months"] / T * 100,
        "rescues_per_century": s["rescues"] * cent, "spend_pct_gdp": spend,
    }
    out = {k: dict(zip(("p10", "p50", "p90"), map(float, np.percentile(v, [10, 50, 90])))) | {"mean": float(np.mean(v))} for k, v in per.items()}
    # pooled ratios: the panic length and manias ending in a panic over every economy at once
    out["panic_length"] = {"mean": float(s["panic_len_sum"].sum() / max(s["panics"].sum(), 1))}
    out["mania_to_panic_pct"] = {"mean": float(s["mania_panics"].sum() / max(s["manias"].sum(), 1) * 100)}
    out["frozen_pct"] = {"mean": float(s["frozen"].sum() / max(s["panics"].sum(), 1) * 100)}
    out["bad_spell"] = {"mean": float(s["crunch_months"].sum() / max(s["crunch_spells"].sum(), 1))}
    out["_hist"] = np.histogram(per["panics_per_century"], bins=np.arange(0, 16))[0].tolist()  # panics a century, 0 to 15
    return out


SNAP = 6  # months between the snapshots the charts draw


def bands(e):
    """The charts over the run, a point every SNAP months: confidence, leverage (10/50/90% across the economies),
    Bad Debts (50/90%), Lending Standards (50%), and the share of economies in a panic."""
    c, p, lev, bad, lax = (np.array(a) for a in zip(*e.snap))
    q = lambda a, *k: [np.percentile(a, x, 1).round(2).tolist() for x in k]
    return {"every": SNAP, "conf": q(c, 10, 50, 90), "lev": q(lev, 10, 50, 90), "bad": q(bad, 50, 90), "lax": q(lax, 50)[0],
            "panic": p.mean(1).round(3).tolist()}


def run(values, cfg, bot, n, seed, trace=False, keep=0):
    K = current() | values
    if lv.LADDER[0] == lv.SAFE:  # leverage.LADDER starts at the safe line unless LEV_LADDER is tuned on its own
        K["LADDER"] = (K["LEV_SAFE"], *lv.LADDER[1:])
    return Economies(K, cfg, bot, n, seed, trace, keep).run()


def _part(e, i, n):
    """Candidate i's economies of a batch, as summarize and bands read them."""
    sl = slice(i * n, (i + 1) * n)
    return SimpleNamespace(stats={k: v[sl] for k, v in e.stats.items()}, months=e.months, snap=[tuple(a[sl] for a in t) for t in e.snap])


def batch(a):
    """A sweep job of several candidates: their economies stepped together, each with the draws it would have alone, so
    the month's fixed cost is paid once. (candidate ids, bot, values each, cfg, economies, seed) -> each one's results.
    A setting the candidates differ on is a per-economy array."""
    cids, bot, vals, cfg, n, seed = a
    K = current()
    for k in {k for v in vals for k in v}:
        x = [v.get(k, K.get(k)) for v in vals]
        K[k] = x[0] if all(y == x[0] for y in x) else np.repeat(np.array(x), n)
    if lv.LADDER[0] == lv.SAFE:
        K["LADDER"] = (K["LEV_SAFE"], *lv.LADDER[1:])
    e = Economies(K, cfg, bot, n * len(vals), seed, copies=len(vals)).run()
    return [(c, bot, summarize(_part(e, i, n)), bands(_part(e, i, n))) for i, c in enumerate(cids)]


def job(a):
    """One sweep job in a worker process: (candidate id, bot, values, cfg, economies, seed) -> its results."""
    cid, bot, values, cfg, n, seed = a
    e = run(values, cfg, bot, n, seed)
    return cid, bot, summarize(e), bands(e)


def score(results, targets):
    """Each target: (metric, bot or 'a-b', target, low, high, weight). Squared distance in the band's half-width.
    A target whose players were not run scores nothing and reads as not run (value None)."""
    total, parts = 0.0, []
    for metric, who, aim, lo, hi, w in targets:
        bots = who.split("-")
        if not all(metric in results.get(b, {}) for b in bots):  # a run from before the metric or the player existed
            parts.append({"metric": metric, "who": who, "value": None, "target": aim, "lo": lo, "hi": hi, "in": False})
            continue
        v = results[bots[0]][metric]["mean"] - (results[bots[1]][metric]["mean"] if len(bots) > 1 else 0)
        half = (aim - lo) if v < aim else (hi - aim)
        d = (v - aim) / max(half, 1e-9)
        total += w * d * d
        parts.append({"metric": metric, "who": who, "value": v, "target": aim, "lo": lo, "hi": hi, "in": lo <= v <= hi})
    return total, parts


TARGETS = [  # fastsim.TARGETS: history's readings for the 40 largest economies, and recklessness punished
    ["panics_per_century", "passive", 4, 2.5, 5.5, 1], ["panic_months_pct", "passive", 1.5, 0.8, 2.5, 1],
    ["panic_length", "passive", 4.5, 3, 6, 1], ["mania_pct", "passive", 4, 2, 8, 1],
    ["mania_to_panic_pct", "passive", 20, 10, 35, 1], ["output_pct", "reckless-careful", -3, -8, -1, 1],
]

# ---------- replay (scaffold): what the mod's LOG line would need to carry for a month-by-month comparison ----------
# key in the log line: (script expression, engine field). Present today: conf, crash, foreign, turmoil, panic, debt, stance,
# rescued, mood, heat, burst, lev, crunch, bite, lax, and the d_* drivers. These are the missing inputs and states.
REPLAY_FIELDS = {
    "praw": ("THIS.Var('spec_boom_raw').GetValue", "boom_raw"),  # booms before the cap: the engine's goods input
    "craw": ("THIS.Var('spec_crash_raw').GetValue", "crash_raw"),  # endings before the scale
    "pm": ("THIS.ScriptValue('spec_pool_month')", "pool_month"),
    "pool": ("THIS.ScriptValue('spec_log_ip')", "pool"),  # the investment pool's balance
    "gdpv": ("THIS.ScriptValue('spec_log_gdp')", "gdp"),  # needs spec_log_gdp = { value = gdp }
    "lavg": ("THIS.ScriptValue('spec_log_lavg')", "lev_avg"),  # needs a value reading spec_lev_avg, 0 when unset
    "lent": ("THIS.Var('spec_credit_given').GetValue", "lent"),
    "pat": ("THIS.ScriptValue('spec_panic_at')", "panic_at"),
    "climit": ("THIS.ScriptValue('spec_credit_limit')", "credit_limit"),  # centres.LOG has it with BRAKE
    "held": ("THIS.ScriptValue('spec_log_held')", "held"),  # needs a value reading spec_lev_held
    "pleft": ("THIS.ScriptValue('spec_log_pleft')", "panic"),  # needs spec_panic, 0 when unset
    "cd": ("THIS.ScriptValue('spec_log_pcd')", "panic_cd"),  # needs spec_panic_cooldown, 0 when unset
    "scd": ("THIS.ScriptValue('spec_log_scd')", "stance_cd"),  # needs spec_stance_cooldown, 0 when unset
    "money": ("THIS.ScriptValue('spec_log_money')", "money"),  # 0 bimetallism, 1 gold, 2 fiat, 3 classical, 4 elastic
    "law": ("THIS.ScriptValue('spec_law_mult')", "law_mult"),
    "techs": ("THIS.ScriptValue('spec_log_techs')", "techs"),  # a bitmask over TECHS, one add per tech
    "legit": ("THIS.ScriptValue('spec_log_legit')", "legit"),  # needs { value = government_legitimacy }
    "sdebt": ("THIS.ScriptValue('spec_debt_share')", "scaled_debt"),
    "cmood": ("THIS.Var('spec_mood_shift').GetValue", "mood_shift"),  # this month's roll, so the replay needs no random draw
    "caution": ("THIS.Var('spec_c_caution').GetValue", "c_caution"),  # the Mania event's choice, as it landed
    "rescue": ("THIS.Var('spec_c_rescue').GetValue", "c_rescue"),
    "bailed": ("THIS.ScriptValue('spec_log_bailed')", "bailed"),
}


def log_fragment():
    """The text to add to centres.LOG (or generate's log line) for the replay: one ' key=[expr]' a field."""
    return "".join(f" {k}=[{expr}]" for k, (expr, _) in REPLAY_FIELDS.items())


def parse_log(line):
    """A SPEC log line's key=value pairs as floats where they parse. ponytail: feeding them through step() is the next step."""
    out = {}
    for k, v in re.findall(r"(\w+)=(\S+)", line):
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = v
    return out


# ---------- self-check ----------
def _script():
    got = {}
    real = g.write
    g.write = lambda rel, text: got.setdefault(rel, text)
    try:
        g.values()
    finally:
        g.write = real
    return got["common/script_values/spec_values.txt"]


def _value(sv, name):
    i = sv.index(f"\n{name} = {{") + 1
    return sv[i:sv.index("\n}", i) + 2]


if __name__ == "__main__" and "--json" in sys.argv:  # the server's fresh read after an apply
    import json
    print(json.dumps({k: v for k, v in current().items() if k in {s[0] for s in TUNABLE}}))
    sys.exit()

if __name__ == "__main__":
    K = current()
    src = "\n".join(p.read_text(encoding="utf-8") for p in TOOLS.glob("*.py"))
    # 1. every tunable key is one the generators read through tuning.get, and the engine has the module's value
    for key, mod, attr, *_ in TUNABLE:
        assert re.search(rf"tuning\.get\(\"{key}\"", src), f"{key}: no tuning.get in tools/"
        if attr:
            assert K[key] == getattr(mod, attr), key
    for sev, key in ((1, "CORRECTION_PER_HYPE"), (2, "BUST_PER_HYPE")):
        assert K[key] == next(r for s, _, _, r, _ in g.UNWINDS if s == sev), key
    # 2. the generated script carries the engine's numbers where the engine uses them
    sv = _script()
    checks = {
        "spec_conf_recover": [f"value = {K['CONF_START']}", f"multiply = {K['CONF_RECOVER']}"],
        "spec_credit": [f"subtract = {K['CREDIT_FROM']}", f"multiply = {K['CREDIT_SHARE']}", f"max = {K['CREDIT_FLOW_MAX']}",
                        "multiply = spec_credit_rate", "max = spec_credit_ceiling", "max = spec_credit_room"],
        "spec_credit_ceiling": [f"multiply = {K['CREDIT_CEILING']}"],
        "spec_credit_runoff": [f"multiply = {K['CREDIT_RUNOFF']}"],
        "spec_clawback": [f"multiply = {K['CLAWBACK']}", "multiply = spec_lax_recall", "max = investment_pool"],
        "spec_claw_share": [f"divide = {K['DANGER']}", f"min = {K['CLAW_FLOOR']}"],
        "spec_tight_pull": [f"value = {K['TIGHT_FROM']}", f"multiply = {K['TIGHT_PULL']:g}", "max = 0"],
        "spec_panic_at": [f"value = {K['PANIC']}"], "spec_pl_lev": [f"multiply = {K['LEV_PANIC_SPAN']}"],
        "spec_lev_stress": [f"subtract = {K['LEV_SAFE']}", f"divide = {K['LEV_RUIN'] - K['LEV_SAFE']}"],
        "spec_crunch_if": [f"multiply = {K['LEV_CRUNCH_MAX']}", "add = spec_xs_bad_sv", "min = spec_crunch_sv"],
        "spec_crunch_fade": [f"value = {K['LEV_CRUNCH_FADE']}", f"value = {K['LEV_CRUNCH_FADE_TIGHT']}"],
        "spec_crunch_stop": [f"value = {K['LEV_BAD_STOP']}", "multiply = spec_lax_badstop"],
        "spec_lev_avg_next": [f"multiply = {K['LEV_INCOME_SMOOTH']}"],
        "spec_lev_floor": [f"multiply = {K['LEV_INCOME_FLOOR']:g}"],
        "spec_panic_months": [f"value = {K['PANIC_DAYS'] / 30:g}", "ceiling = yes"],
        "spec_panic_lev_len": [f"multiply = {K['PANIC_LEV_LEN']:g}"],
        "spec_panic_cut_if": [f"value = {K['CRUNCH_FLOOR']:g}"],
        "spec_mood_scale": [f"multiply = {K['MOOD_SHALLOW'] - 1:g}"],
        "spec_shallow_panic": [f"multiply = {K['PANIC_SHALLOW']:g}"],
        "spec_heat_cool": [f"value = {K['HEAT_COOL']:g}", f"value = {K['HEAT_COOL_TIGHT']:g}"],
        "spec_crash_scale": [f"divide = {K['CONF_START']}"],
        "spec_fin_boom": [f"value = {K['FIN_BOOM_BASE']:g}"],
        "spec_lax_credit": [f"multiply = {K['LAX_CREDIT']}"], "spec_lax_recall": [f"multiply = {K['LAX_RECALL']}"],
        "spec_lax_badstop": [f"multiply = {K['LAX_BADSTOP']}"], "spec_lax_cost": [f"multiply = {K['LAX_COST']}"],
        "spec_boom_share": [f"multiply = {K['EXP_PULL']}", f"max = {K['EXP_SHARE_MAX']}"],
        "spec_bailout_share": ["multiply = spec_crunch_sv"],
    }
    for name, parts in checks.items():
        body = _value(sv, name)
        for p in parts:
            assert p in body, f"{name}: {p!r} not in\n{body}"
    monthly = g.monthly(False)
    for p in (f"var:spec_conf > {K['CREDIT_FROM']}", f"var:spec_conf >= {K['MANIA']}", f"var:spec_conf < {K['BURST_BELOW']}",
              f"var:spec_conf >= {K['PANIC_ENDS_AT']}", f"spec_panic_run >= {K['PANIC_MIN_MONTHS']}", f"multiply = {K['MOOD_KEEP']:g}",
              f"var:spec_c_boom > {K['CONF_BOOM_MAX']}", f"value = -{K['CONF_CRASH_MAX']}", f"add = {K['LEV_CRUNCH_RAMP']}"):
        assert p in monthly, p
    assert f"change_variable = {{ name = spec_lax add = {1 / (12 * K['LAX_QUIET_YEARS']):.5f} }}" in cycle.monthly()
    # 3. the engine's Bad Debts curve is leverage's own model: they peak at the size set and last the months shown
    e = Economies(K, defaults(), "passive", 1, 0)
    for c, b0, tight in ((40, 3, 0), (22, 3, 0), (40, 3, 1), (13, 30, 0)):
        e.crunch, e.bite, e.stance, steps, peak = np.array([float(c)]), np.array([float(min(b0, c))]), np.array([-1.0 * tight]), 0, min(b0, c)
        while e.crunch[0] > 0:
            fade = e.crunch_fade()
            had = e.crunch > 0
            e.crunch = np.where(had & (e.bite >= e.crunch), e.crunch - fade, e.crunch)
            e.crunch = np.where(e.crunch <= 0, 0, e.crunch)
            e.bite = np.where(e.crunch > 0, np.minimum(e.bite + K["LEV_CRUNCH_RAMP"], e.crunch), 0)
            steps, peak = steps + 1, max(peak, float(e.bite[0]))
        f = K["LEV_CRUNCH_FADE_TIGHT"] if tight else K["LEV_CRUNCH_FADE"]
        assert peak == c and steps == math.ceil(max(c - b0, 0) / K["LEV_CRUNCH_RAMP"]) + math.ceil(c / f), (c, b0, steps)
    # 4. the Panic Threshold at the ruin line, and a run of each bot stays in bounds
    e.depth = np.array([1.0])
    assert abs(e.panic_at(np.array([K["LEV_RUIN"]]))[0] - (K["PANIC"] + K["LEV_PANIC_SPAN"])) < 1e-9
    for bot in BOTS:
        r = run({}, defaults(), bot, 300, 7)
        c = np.array([s[0] for s in r.snap])
        assert c.min() >= 0 and c.max() <= 100 and np.isfinite(r.debt).all() and (r.debt >= -1e-6).all(), bot
        sm = summarize(r)
        print(f"{bot:9s} panics/century {sm['panics_per_century']['mean']:.2f}  in panic {sm['panic_months_pct']['mean']:.2f}%  "
              f"length {sm['panic_length']['mean']:.1f}  mania {sm['mania_pct']['mean']:.1f}%  mania->panic {sm['mania_to_panic_pct']['mean']:.0f}%  "
              f"lev {sm['lev_mean']['mean']:.2f}  bad max {sm['crunch_max']['mean']:.1f}  GDP {sm['output_pct']['mean']:+.2f}%")
    # 4b. laws move over the century: a century on, laissez-faire is common, fiat comes late, and each multiplier is its law's
    lf = np.mean(r.econ == "laissez_faire")
    assert 0.2 < lf < 0.6 and all(at[at >= 0].min(initial=10 ** 6) >= 75 * 12 for k, at, d in r.drift if k == "money" and (d == "fiat_money").all()), lf
    note = lambda i: journal.REFORMS["currency"]["panic_len"] if r.enacted["currency"][i] else 1  # the Currency School, the AI's Commissions
    assert all(r.law_mult[i] == LAWS[r.econ[i]][0] and abs(r.reform["panic_len"][i] - MONEY.get(r.money[i], {}).get("panic_len", 1) * note(i)) < 1e-9 for i in range(r.n))
    # 4c. the world beyond: trust stays 0 to CALM, the Long Depression comes after EARLIEST_YEAR and reaches at least its share
    assert ((r.trust >= 0) & (r.trust <= centres.CALM)).all() and r.ld_at[0].min() >= (depression.EARLIEST_YEAR - 1836) * 12
    assert r.ld_in[0].mean() >= np.mean(r.I["ld_join"]) - 0.1 and r.flight_p.max() > 0
    # 4d. the AI restrains booms and its Commissions make institutions
    assert r.bot_name == "ai" and r.stats["restrains"].sum() > 0 and r.stats["reforms"].sum() > 0, (r.stats["restrains"].sum(), r.stats["reforms"].sum())
    # 5. the Inspector's rows add up to the figure they explain, every month of a traced run
    for bot in ("passive", "reckless", "ai"):
        for f in run({}, defaults(), bot, 1, 3, trace=True).hist:
            for total, rows in (("conf", [r[1] for r in CALC["conf"][:-1]]), ("debt", ["debt_was", "runoff_neg", "lent", "recall_neg", "writeoff_neg"]),
                                ("pool", ["pool_last", "pool_month", "spend_neg", "repaid_neg", "lent", "clawed_neg"])):
                got = sum(f[r] for r in rows)
                assert abs(got - f[total]) <= 1e-3 * (1 + abs(f[total])) + 0.01, (bot, f["m"], total, got, f[total])
    assert log_fragment().count("=[") == len(REPLAY_FIELDS) and parse_log("SPEC conf=55.2 tag=GBR")["conf"] == 55.2
    print("engine ok:", len(TUNABLE), "tunable constants match the generators")
