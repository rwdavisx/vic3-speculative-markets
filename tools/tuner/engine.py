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
from datetime import date
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import fiscal

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
import sectors  # noqa: E402
import investor_sentiment as sentiment  # noqa: E402
import monetary  # noqa: E402
import rivals  # noqa: E402
import vanilla_ties as vt  # noqa: E402

# ---------- the constants: (tuning.json key or None, module, attribute, group, label) ----------
# A key means generate.py and friends read it through tuning.get(key, default), so the tuner can write it back.
TRUST_KEYS = ("TRUST_STRICT", "TRUST_CAUTIOUS", "TRUST_SOUND", "TRUST_LAX", "TRUST_RECKLESS")
_TRUST = SimpleNamespace(**dict(zip(TRUST_KEYS, centres.TRUST_BY_LAX)))  # centres keeps them as one tuple
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
    ("LEV_REWARD_TP_FULL", lv, "TP_FULL", "Leverage", "Smooth bonus, throughput at the ruin line (both full values 0: whole months)"),
    ("LEV_REWARD_INV_FULL", lv, "INV_FULL", "Leverage", "Smooth bonus, investment at the ruin line"),
    ("LEV_REWARD_CURVE", lv, "CURVE", "Leverage", "Smooth bonus shape, 1 straight, 0.5 front-loaded"),
    ("LEV_REWARD_TAPER", lv, "TAPER_KEY", "Leverage", "Tapered bonus, throughput a month past the bonus months (-1 off)"),
    ("LEV_BONUS_FADE", lv, "BONUS_FADE", "Leverage", "Bonus months lost a month"),
    ("LEV_RECORD_TP", lv, "RECORD_TP", "Leverage", "Sound Credit: throughput per month of leverage it grows toward (0 off)"),
    ("LEV_RECORD_GAIN", lv, "RECORD_GAIN", "Leverage", "Sound Credit: share of the way closed a calm month"),
    ("LEV_RECORD_LOSS", lv, "RECORD_LOSS", "Leverage", "Sound Credit: share lost a panic or Bad Debts month, x (1 + stress)"),
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
    # the AI's per-temperament tables, each moved as one (tuning.scaled), and its other levers
    ("AI_LEV_SCALE", lv, "AI_LEV_SCALE", "AI", "AI leverage limits, scale"),
    ("AI_LEV_BACK", lv, "AI_LEV_BACK", "AI", "AI loosens below this share of its limit"),
    ("AI_FEVER_SCALE", lv, "FEVER_SCALE", "AI", "AI carried away by a Mania, scale"),
    ("RESCUE_SCALE", credit_ai, "RESCUE_SCALE", "AI", "AI rescue chances, scale"),
    ("AI_BAILOUT_CHANCE", lv, "AI_BAILOUT_CHANCE", "AI", "AI buys up bad loans, chance a month"),
    ("TEMPER_TILT", credit_ai, "TEMPER_TILT", "AI", "Temperament weight moved from Cautious to Bold"),
    ("AI_CONF", levers, "AI_CONF", "AI", "AI restrains a boom from"),
    ("AI_RISK", levers, "AI_RISK", "AI", "AI restrains booms risking at least"),
    ("AI_FUNDS", levers, "AI_FUNDS", "AI", "AI encourages with a surplus of this many subsidies"),
    # the Exchange's rescue pledge (centres._pledge_month, PLEDGE_RESCUE): the AI's rule, and what the pledge does
    ("AI_PLEDGE_DEBT", centres, "AI_PLEDGE_DEBT", "AI", "AI pledges a rescue below this scaled debt"),
    ("AI_PLEDGE_LEAVE", centres, "AI_PLEDGE_LEAVE", "AI", "AI gives notice on the pledge above this scaled debt"),
    ("AI_PLEDGE_CHANCE", centres, "AI_PLEDGE_CHANCE", "AI", "AI pledges a rescue, chance a month once it can"),
    ("EXCH_PLEDGE_COST", centres, "PLEDGE_SHARE", "Pledge", "Rescue cost while pledged, share"),
    ("EXCH_PLEDGE_PANIC", centres, "PLEDGE_PANIC", "Pledge", "Panic trust loss while pledged, share"),
    ("EXCH_PLEDGE_NOTICE", centres, "PLEDGE_NOTICE", "Pledge", "Months of notice to withdraw the pledge"),
    # the journal entry's AI (journal.MONTHLY_AI, spec_reform.1's ai_chance)
    ("AI_INQUIRY_CHANCE", journal, "AI_INQUIRY_CHANCE", "AI", "AI opens a Commission of Inquiry, chance a month"),
    ("AI_CONVERT_CHANCE", journal, "AI_CONVERT_CHANCE", "AI", "AI converts the debt, chance a month"),
    ("AI_RELIEF_CHANCE", journal, "AI_RELIEF_CHANCE", "AI", "AI pays Relief Works, chance a month (not modeled)"),
    *((f"REFORM_AI_{k}", journal, f"REFORM_AI_{k}", "AI events", f"Inquiry report, AI weight {w}") for k, w in
      (("CURRENCY", "for the Currency School"), ("FREE", "for Free Banking"), ("TEMPER", "added to those for Cautious and Bold"),
       ("LLR", "for the lender of last resort"), ("COMPANY", "for company law"), ("SHELVE", "to shelve it"))),
    *((k, g, k, "AI events", f"Mania event, AI weight {w}") for k, w in
      (("MANIA_AI_RIDE", "to ride it"), ("MANIA_AI_RIDE_BOLD", "to ride it, added for Bold"), ("MANIA_AI_WARN", "for the warning"),
       ("MANIA_AI_WARN_CAUTIOUS", "for the warning, added for Cautious"), ("MANIA_AI_LEVY", "for the levy"),
       ("MANIA_AI_LEVY_CAUTIOUS", "for the levy, added for Cautious"))),
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
    ("PANIC_THROUGHPUT", g, "PANIC_THROUGHPUT", "Panic", "Panic throughput"), ("PANIC_INVEST", g, "PANIC_INVEST", "Panic", "Panic investment"),
    *((k, _TRUST, k, "Exchange", f"Trust a calm month, {w}") for k, w in
      (("TRUST_STRICT", "Strict"), ("TRUST_CAUTIOUS", "Cautious"), ("TRUST_SOUND", "Sound"), ("TRUST_LAX", "Lax"), ("TRUST_RECKLESS", "Reckless (x loss)"))),
    # trust's level effects (centres.TRUST_FX) added on top of the released ones; minting and prestige are not modeled
    ("TRUST_ALLOC_STEP", centres, "TRUST_ALLOC_STEP", "Exchange", "Private construction allocation a trust level step"),
    ("TRUST_IND_DISTRUST", centres, "TRUST_IND_DISTRUST", "Exchange", "Industrialists' approval lost when Distrusted"),
    ("BAND_INVEST_STEP", g, "BAND_INVEST_STEP", "Confidence", "Investment per tier (Wary -1, Mania +2)"),
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
# the Industrialists' approval each trust level gives as released (centres.TRUST_FX less TRUST_IND_DISTRUST, which K adds)
TRUST_IND = np.array([sum(x for m, x in f if m == "interest_group_ig_industrialists_approval_add") for f in centres.TRUST_FX], float)
TRUST_IND[0] += centres.TRUST_IND_DISTRUST


def current():
    """{key: value} as the generators have them now. Keys without a tuning name are the module's attribute name."""
    out = {}
    for key, mod, attr, *_ in SPEC:
        if attr is None:
            out[key] = next(rate for sev, _, _, rate, _ in g.UNWINDS if sev == _UNWIND[key])
        else:
            out[key if key else attr] = getattr(mod, attr)
    out["LADDER"] = tuple(lv.LADDER)
    out["AI_LOOSE"] = credit_ai.tuning.get("AI_LOOSE", None)  # credit_ai.script's loose point: WARY unless set on its own
    return out


def lev_shape(m, ruin, curve):
    """leverage.shape: the smooth bonus's share of its full value at m months, straight between leverage.REWARD_NODES."""
    t = np.clip(m / ruin, 0, 1)
    ks = np.array(lv.REWARD_NODES, float) / 12
    i = np.clip(np.searchsorted(ks, t, side="right"), 1, len(ks) - 1)
    a, b = ks[i - 1], ks[i]
    sa, sb = a ** curve, b ** curve
    return sa + (t - a) * (sb - sa) / (b - a)


def per_temper(base, scale, temper, whole=False):
    """A per-temperament table (base {temper: value}) as the generator scales it (tuning.scaled), for each economy's
    temperament and scale (a number, or one a economy when the candidates differ). A temperament it lacks is 0."""
    tabs = {}

    def one(s, t):
        if s not in tabs:
            tabs[s] = {int(k): v for k, v in credit_ai.tuning.scaled(base, float(s), whole).items()}
        return tabs[s].get(int(t), 0)
    return np.vectorize(one, otypes=[float])(scale, temper)


TUNABLE = [s for s in SPEC if s[0]]
LAWS = {law: (h, p) for law, h, p in g.LAWS}  # economic system -> (hype x, panic length x)
ALLOC = g.law_alloc()  # the law's private construction share (spec_alloc_base)
MONEY = dict(monetary.FX)  # monetary law -> {key: multiplier}
LADDER_TECHS = lv.LADDER_TECHS
CREDIT_TECHS = g.CREDIT_TECHS
TECHS = sorted({"banking", "stock_exchange", "central_banking", "joint_stock_companies", "macroeconomics", "currency_standards",
                *CREDIT_TECHS, *LADDER_TECHS, *g.FIN_BOOM, *g.FIN_RISK, g.FIN_LEVERAGE[0]})
BANDS = market_tab.TIERS  # (name, from, to)
TIER = {b[0]: b[1:3] for b in BANDS}
WORDS = cycle.LAX_WORDS

# ---------- the game's side, abstracted: bounded input streams ----------
# name: (default, low, high, label). The sweep draws each economy's figures inside [low, high]; the page edits both.
GOODS_MAX = 48  # goods an economy can have
# Each good's price, as generate's market_goods_pricier (spec_dev_<g>) moves in the logs (parallel3, every good of the 40
# largest market owners, 1836, 1866 and 1896): its booms come from the fast and slow averages of this one series. The
# swing a month falls with the good's weight and with its economy's size, and nothing else is left by decade once GDP is
# in (log spread ~ weight x -0.192, GDP x -0.168). Each good keeps its own factor, spread 0.55 on a log scale (0.635 less
# the window's sampling noise). Shares of trade are log-normal, 1.1 wide: the logs' weights sum to 18-21 with 41-29% at 1.
# The price is a slow part that lasts price_months plus a month's noise, 0.25 of the slow part's spread: that matches the
# logs' autocorrelation of the price (0.56 at 3 months, 0.24 at 12), of the averages' gap and of the monthly change (-0.22)
# at 14 months. In markets of 25 goods or more, 6.5% of a good's price movement is the market's own (mean pairwise
# correlation 0.06-0.07). The game starts out of balance: in 1836-37 prices move 1 + 0.9 e^(-month / 6) times as much.
SHARE_SD, PRICE_W_EXP, PRICE_GDP_EXP, PRICE_GDP_AT, PRICE_SPREAD = 1.1, 0.192, 0.168, 1e7, 0.55
PRICE_NOISE, PRICE_COMMON, PRICE_START, PRICE_START_MONTHS = 0.25, 0.065, 0.9, 6
INPUTS = {
    "years": (100, 10, 150, "Years run"),
    "pool_share": ((0.012, 0.035), 0.001, 0.06, "Pool income a month, share of GDP"),  # the logs' 10% is 0.25%: 0.005 clipped the fit
    "pool_noise": ((0.02, 0.08), 0, 0.3, "Pool income noise a month"),
    "pool_spend": ((0.35, 0.7), 0.05, 1, "Share of the pool spent a month"),
    "growth": ((0.005, 0.035), -0.02, 0.06, "GDP growth a year"),
    "gdp_noise": ((0.002, 0.006), 0, 0.03, "GDP noise a month"),
    "recessions": ((2, 6), 0, 20, "Vanilla recessions a century"),
    "recession_depth": ((0.03, 0.10), 0, 0.4, "Recession depth"),
    # the logs' market owners trade 29 goods in 1836-46, 35 in 1866-76 and 39 in 1896-1906: a line through them
    "goods": ((29, 29), 1, GOODS_MAX, "Goods traded in 1841"),
    "goods_growth": ((17, 17), 0, 40, "Goods added a century"),
    "price_sd": ((0.03, 0.03), 0.001, 0.3, "Price swing a month, a good of weight 1 at GDP 10 million"),  # fit.py --boom
    "price_months": ((14, 14), 1, 1000, "Months a price deviation lasts"),  # 1 / (1 - kept a month), from the logs' autocorrelation
    "foreign_rate": ((3, 12), 0, 150, "Foreign panics reaching us a century"),
    "foreign_size": ((0.02, 0.6), 0, 1, "Their hit, share of Contagion"),
    "war_rate": ((1, 5), 0, 50, "Wars a century"),
    "war_months": ((6, 48), 1, 120, "Months a war lasts"),
    "war_cost": ((0.35, 1.2), 0, 3, "Confidence a war month"),
    "approval_sd": ((0.8, 2.0), 0, 5, "Industrialists' approval noise"),
    "legitimacy": ((20, 90), 0, 100, "Legitimacy"),
    "scaled_debt": ((0, 0.8), 0, 1.5, "Government debt, share of credit"),
    "reserves": ((0.01, 0.08), 0, 0.5, "Gold reserves, share of GDP"),
    "weekly_balance": ((-0.001, 0.001), -0.05, 0.05, "Weekly budget balance, share of GDP (independent inputs)"),
    "depth": ((vt.DEPTH_MIN, vt.DEPTH_MAX), vt.DEPTH_MIN, vt.DEPTH_MAX, "Financial District depth"),
    "steady": ((vt.STEADY_MIN, vt.STEADY_MAX), vt.STEADY_MIN, vt.STEADY_MAX, "Manor House steadiness"),
    # the world beyond, replayed from the logs (world.npz) rather than drawn: wars, defaults and crises come with their
    # heavy tails and together, as they do in the game; 0 draws them from the rates below instead
    "world_replay": (1, 0, 1, "Replay the logged wars, crises and foreign panics"),
    # stand-ins, fitted (fit.py's roughness block): with every logged driver matched, the games still had twice the AI's panics
    "after_panic": ((0.6, 0.6), 0, 5, "Confidence lost a month in the year after a panic: the unrest, falling GDP and approval that follow one"),
    "rough_sd": ((1.0, 1.0), 0, 10, "The world's roughness: a slow swing of confidence the model lacks, its size a month"),
    "rough_months": ((6, 6), 0.5, 60, "How long a swing of the world's roughness lasts, months"),
    # rivals.spec_rv_ai_move: an AI in a contest Lures its rival's capital only below rivals.AI_LEV leverage; how often it
    # gets the chance (contests, cooldowns, its looks) is read off runs/windows_120's debt jumps (fit.py's lure block)
    "lure_rate": ((0.04, 0.04), 0, 1, "Rival Lures a month, an AI below the lure's leverage line"),
    # rivals.spec_rv_vs: their Exchange's score over ours, held to VS_LO..VS_HI. Drawn even in this range and then held, so
    # its ends carry the logged Lures' shares at each limit (fit.py --windows: most Lures fall on weaker rivals)
    "lure_vs": ((1, rivals.VS_HI), -10, 10, "A Lure's rival score over ours, before rivals.VS_LO..VS_HI holds it"),
    "flight_share": (0.3, 0, 1, "Countries capital flight reaches"),
    "flight_rate": ((15, 240), 0, 300, "Capital flights a century, where it reaches"),  # one for most panics anywhere
    "flight_size": ((0.2, 2), 0, 10, "A capital flight's gain"),
    # the Long Depression, read off the logs' ld= (146 games since 2026-11-07, countries reaching 1880): it reached 59%,
    # its first month fell in 1870 to 1879 (median 1875), and the Depression phase ran 17 to 45 months (median 23)
    "ld_join": (0.6, 0, 1, "Countries the Long Depression reaches"),
    "great_powers": (8, 1, 12, "Maximum active Great Powers per simulated world"),
    "ld_months": ((17, 45), 4, 60, "Months the Depression phase lasts"),
    "e_gdp": (0.6, 0, 2, "GDP felt per unit of throughput"),
    "e_pool": (1.0, 0, 2, "Pool income felt per unit of investment"),
    # calib_growth.py on runs/windows_120/campaign (PARITY.md, November 23): yearly GDP growth per unit of monthly pool income
    # over GDP that the mod adds or takes; 0 is the old level-only model
    "inv_growth": (3.5, 0, 20, "GDP growth a year per unit of pool income share added"),
    # the banks' lending against the base at confidence 57 to 65 (Normal, 1850 on): 0.56 in the pre-1.2 logs, 0.75 in three
    # current-build games (runs/sweep_calib12), where the engine gave 0.43 at 0.55, so the current build needs about 1
    "e_credit": (1.0, 0, 2, "Credit felt per unit of the mod's lending"),
    # levers.afford: the AI pulls a lever only with twice its Authority cost to spare. Its spare Authority, in levers, is a
    # draw (even on a log scale) that lasts AUTH_YEARS on average, fitted to the logs' levers= (how many it holds at once)
    "ai_authority": ((0.1, 10), 0, 50, "The AI's spare Authority, in levers"),
    "fiscal_profiles": (1, 0, 1, "Use observed GDP, budgets, reserves, debt, Authority and governing interest groups (overrides their independent ranges)"),
    "observed_research": (1, 0, 1, "Follow the sampled country's recorded technologies and laws when using fiscal profiles"),
    "heightened": (0, 0, 1, "Heightened volatility rule"),
}
# the laws in 1836 among the largest economies (vanilla common/history/countries: interventionism 16, traditionalism 7,
# agrarianism 2, laissez-faire none), Britain alone on gold (monetary.GOLD_AT_START). A variant replaces its parent beside
# its Economic System (monetary.SWAP)
ECON_MIX = {"laissez_faire": 0.02, "interventionism": 0.62, "agrarianism": 0.08, "traditionalism": 0.28}
MONEY_MIX = {"bimetallism": 0.96, "gold_standard": 0.04}
# the moves countries make over the century, in order: (law kind, from, {to: weight}, share of those on it that move, years
# after 1836 low to high), each after the economy's last move of that kind. Fiat requires monetary.FIAT_TECH.
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
TECH_BIT = {t: i for i, t in enumerate(g.LOG_TECHS)}  # the log's techs= bitmask, and fit.py --history's
REPLAY_LOOP = 360  # months of the campaign's world replayed again after its end (inputs())
TECH_YEARS = {"banking": (0, 0), "currency_standards": (0, 0), "international_trade": (0, 0), "stock_exchange": (0, 15),
              "joint_stock_companies": (0, 15), "central_banking": (5, 50), "investment_banks": (32, 90),
              "international_exchange_standards": (40, 100), "mutual_funds": (50, 110), "modern_financial_instruments": (65, 130),
              "macroeconomics": (75, 130)}
# how wars end, read off 8,667 SPECWAREND lines (DLC-on games since 2026-11-07, every country): (share of ends, share of
# those with the war goal enforced), and the stakes: share at diplomacy.WAR_STAKES_MIN, share at full, the rest between
WAR_ENDS = {"won": (0.83, 0.21), "lost": (0.10, 0.26), "drawn": (0.07, 0)}
WAR_STAKES = (0.77, 0.15)
AUTH_YEARS = 5


@cache
def goods_tax_bases():
    costs = g.goods_tax_cost()
    return np.array([costs.get(good) or levers.DEFAULT_TAX_COST for good in g.GOODS])


@cache
def word_boundaries():
    cuts = [g.CRASH_BELOW, g.COOLING_HYPE, g.RISING_HYPE, g.HOT_HYPE, g.PEAK_FOR_CRASH]
    up = [c * (1 + g.WORD_BUFFER) if c >= 1 else c / (1 - g.WORD_BUFFER) for c in cuts]
    down = [c * (1 - g.WORD_BUFFER) if c >= 1 else c / (1 + g.WORD_BUFFER) for c in cuts]
    return tuple([float(f"{value:.4g}") for value in limits] for limits in (cuts, up, down))


CHARTERS = {"commodity": 1, "money": 2, "share": 3}
PLAYER_CREDIT = {"tight": -1, "normal": 0, "loose": 1}


def player_finance_orders(cfg):
    charter, credit = cfg.get("player_charter"), cfg.get("player_credit")
    if charter is not None and charter not in CHARTERS:
        raise ValueError("Choose a Commodity Exchange, Money Market or Share Market.")
    if credit is not None and credit not in PLAYER_CREDIT:
        raise ValueError("Choose Tight, Normal or Loose Credit.")
    return charter, PLAYER_CREDIT.get(credit)


def player_lever_orders(lines):
    orders = {}
    for line in lines:
        try:
            when, good, action = line.split()
            day = date.fromisoformat(when)
            month = (day.year - 1836) * 12 + day.month - 1
            if month < 0 or action not in ("restrain", "encourage"):
                raise ValueError()
            order = (day, g.GOODS.index(good), action)
        except (AttributeError, ValueError):
            raise ValueError(f"Invalid player goods order '{line}'. Use a date from 1836, a traded good and encourage or restrain.") from None
        orders.setdefault(month, []).append(order)
    return {m: sorted(at, key=lambda order: order[0]) for m, at in orders.items()}


@cache
def research_order():
    """Project the installed game's research tree onto the technologies the simulator dates."""
    requires = {}
    for source in sorted((g.GAME / "common/technology/technologies").glob("*.txt")):
        script = re.sub(r"#.*", "", source.read_text(encoding="utf-8-sig"))
        for tech, body in re.findall(r"(?ms)^(\w+)\s*=\s*\{(.*?)^\}", script):
            parents = re.search(r"unlocking_technologies\s*=\s*\{([^}]*)\}", body)
            requires[tech] = parents[1].split() if parents else []

    @cache
    def ancestors(tech):
        return {p for parent in requires[tech] for p in (parent, *ancestors(parent))}

    return sorted(((t, ancestors(t) & set(TECH_YEARS)) for t in TECH_YEARS), key=lambda row: len(row[1]))


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
            _world.clear()
            _world.update(key=key, t=z["t"], f=z["f"], w=z["w"], contagion=float(z["contagion"]))
            if "h_tags" in z.files:  # fit.py --history: the campaign's laws and techs by tag
                _world["history"] = {k[2:]: z[k] for k in z.files if k.startswith("h_")}
    return _world


def history():
    """{tags, econ, money, techs, last}: each fiscal tag's month-by-month laws and techs in the clean 1.2.0 campaign, or None."""
    W = world()
    return W.get("history") if W else None


def defaults(fitted=True):
    import json
    inputs = {k: v[0] for k, v in INPUTS.items()}
    if fitted and FITTED.exists():
        inputs |= {k: v for k, v in json.loads(FITTED.read_text(encoding="utf-8"))["inputs"].items() if k in INPUTS}
    # ponytail: a what-if for an input the logs can't fit, e.g. SPEC_TUNER_INPUTS='{"inv_growth": 10}'
    inputs |= json.loads(__import__("os").environ.get("SPEC_TUNER_INPUTS") or "{}")
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
    # borrows as the Balanced AI does, but goes Tight while the Panic Risk alert shows (the Risks bar's floor under the
    # panic line, journal.alerts) and back once it clears; rescues and buys up as skilled does
    "skilled_timing": dict(like_ai=True, rescue=1, bailout=1, bailout_from=10, mania=(0, 1, 0), afford=False),
    # the mod's own AI (credit_ai.py and generate.monthly's is_player = no block), by temperament
    "ai": "ai",
}
# ponytail: a what-if for the skilled bot's thresholds, e.g. SPEC_TUNER_SKILLED='{"tight_lev": 8, "untight_lev": 7}'
BOTS["skilled"].update(__import__("json").loads(__import__("os").environ.get("SPEC_TUNER_SKILLED") or "{}"))


def ai_policy(K, temper, lean):
    """The AI's thresholds (credit_ai.script) for each economy: temper -1/0/1, lean = its temper and IG shift."""
    lim = per_temper(lv.AI_LIMIT_BASE, K["AI_LEV_SCALE"], temper)
    loose = K["WARY"] if K.get("AI_LOOSE") is None else K["AI_LOOSE"]
    return dict(tight_conf=K["AI_TIGHT"] + lean, tight_lev=lim,
                untight_conf=np.maximum(K["AI_TIGHT"] - 1 + lean, K["CONF_START"] + 3), untight_lev=lim,
                loose_conf=loose + lean, loose_lev=lim * K["AI_LEV_BACK"],
                unloose_conf=np.minimum(K["CREDIT_FROM"] + lean, K["CONF_START"] - 1),
                rescue=per_temper(credit_ai.RESCUE_BASE, K["RESCUE_SCALE"], temper, True) / 100, bailout=K["AI_BAILOUT_CHANCE"] / 100, bailout_from=0,
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
              ("= Booms ending", "c_crash", "=+2"), ("Goods restrained", "restraining", "0"), ("Goods encouraged", "encouraging", "0")],
    "banks": [("Confidence above the line", "credit_base", "%1"), ("x a month's pool income", "pool_month", "Â£"),
              ("x law", "law_mult", "x2"), ("x techs", "tech_credit", "x2"), ("x credit policy", "stance_credit", "x2"),
              ("x Lending Standards", "lax_credit", "x2"), ("x Bad Debts", "crunch_lend", "x2"), ("Ceiling", "ceiling", "Â£"),
              ("Room under the Lending Limit", "room", "Â£"), ("= Lent this month", "lent", "=Â£")],
    "lax": [("Last month", "lax_was", "%0"), ("Quiet month", "lax_drift", "+%1"), ("Booms ending", "lax_booms", "+%1"),
            ("Rescues and panics", "lax_jump", "+%1"), ("= Lending Standards", "lax", "=%0"),
            ("Exchange Trust", "exchange_trust", "%1")],
    "excess": [("Confidence over the line", "xs_over", "+1"), ("x Monetary Standard", "reform_heat", "x2"),
               ("Grows", "xs_grow", "+1"), ("Cools", "xs_cool", "+1"), ("A burst takes from confidence", "c_burst", "+1"),
               ("Burst leaves Bad Debts", "xs_bad", "1"), ("= Speculative Excess", "heat", "=1")],
    "credit": [("Last month", "debt_was", "Â£"), ("Runoff", "runoff_neg", "Â£"), ("Lent", "lent", "Â£"),
               ("Recalled, paid from the pool", "recall_neg", "Â£"), ("Recalled, written off", "writeoff_neg", "Â£"), ("A rival Lured", "lured", "Â£"), ("= Outstanding Credit", "debt", "=Â£"),
               ("Lending Limit (months)", "credit_limit", "1")],
    "pool": [("Last month", "pool_last", "Â£"), ("A month's income", "pool_month", "Â£"), ("Spent on construction", "spend_neg", "Â£"), ("Repaid to banks", "repaid_neg", "Â£"),
             ("Lent in", "lent", "Â£"), ("Recalled", "clawed_neg", "Â£"), ("= Investment Pool", "pool", "=Â£")],
    "lev": [("Outstanding Credit", "debt", "Â£"), ("/ income it is measured on", "lev_income", "Â£"), ("= Leverage (months)", "lev", "=2"),
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
    def standard_normal(self, size): return self._do(self.g.standard_normal, size)


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


class DepressionWorlds:
    """Monthly global gate. Each world gets AI peers running this candidate's financial mechanics."""
    def __init__(self, K, cfg, n, seed, copies):
        per_candidate = n // copies
        self.count = min(8, per_candidate)  # share external histories across focal economies
        self.power_limit = int(cfg["inputs"].get("great_powers", 8))
        self.powers = len(fiscal.power_tags()) if cfg["inputs"].get("fiscal_profiles", 1) else self.power_limit
        world_count = self.count * copies
        peer_count = self.count * self.powers
        def peers_value(v):
            return np.repeat(v[::per_candidate], peer_count) if isinstance(v, np.ndarray) and v.ndim else v
        peer_K = {k: peers_value(v) for k, v in K.items()}
        peer_K["LADDER"] = tuple(peers_value(v) for v in K["LADDER"])
        self.peers = Economies(peer_K, cfg, "ai", peer_count * copies, seed + 7129, copies=copies, peer=True)
        r = _Tiled(np.random.default_rng([seed, 41]), copies)
        D = depression
        self.opens = (D.EARLIEST_YEAR - 1836) * 12 + np.maximum(0, np.ceil(r.uniform(0, D.EARLIEST_SPREAD * 12, world_count)) - 1)
        self.origins = np.zeros((world_count, self.powers), bool)
        self.priority = r.random((world_count, self.powers))
        self.can_repeat = r.random(world_count) < D.SECOND_CHANCE / 100
        self.started = np.full(world_count, -1)
        self.depressions = np.zeros(world_count, int)
        duration_range = cfg["inputs"].get("ld_months", INPUTS["ld_months"][0])
        self.duration = np.stack([np.clip(np.rint(_draw(r, duration_range, world_count)), 1, D.DEPRESSION_MAX)
                                  for _ in range(D.MAX_PER_GAME)])
        self.local_world = np.tile(np.arange(per_candidate) % self.count, copies) + np.repeat(np.arange(copies) * self.count, per_candidate)

    def advance(self, m, panic):
        D = depression
        eligible = panic & ~self.origins
        start = (m >= self.opens) & eligible.any(axis=1) & (self.depressions < 1 + self.can_repeat.astype(int))
        self.origins[start, np.where(eligible, self.priority, -1).argmax(1)[start]] = True
        self.started[start] = m
        self.depressions += start
        length = self.duration[np.maximum(self.depressions - 1, 0), np.arange(len(start))]
        finish = D.CRASH_MONTHS + length + D.RECOVERY_MONTHS
        self.opens[start] = m + finish[start] + D.COOLDOWN_YEARS * 12
        age = m - self.started
        phase = _first([self.started < 0, age < D.CRASH_MONTHS, age < finish - D.RECOVERY_MONTHS, age < finish],
                       [0, 1, 2, 3], 0)
        return phase, start

    def step(self, m):
        peers = self.peers
        eligible = (peers.in_panic & (peers.law_mult > 0)).reshape(-1, self.powers)
        if peers.I["fiscal_profiles"]:
            active = peers.fiscal_gp[np.maximum(peers.fiscal_era, 0), np.arange(peers.n)].reshape(eligible.shape)
            if self.power_limit < self.powers:
                scores = np.where(active, self.priority, -1)
                cutoff = np.partition(scores, -self.power_limit, axis=1)[:, -self.power_limit]
                active &= scores >= cutoff[:, None]
            eligible &= active
        phase, start = self.advance(m, eligible)
        peers.step((phase.repeat(self.powers), start.repeat(self.powers)))
        return phase[self.local_world], start[self.local_world]


class Economies:
    """N economies stepped in lockstep. Variables mirror the mod's (spec_<name>); a 'has_variable' is a flag or > 0."""

    def __init__(self, K, cfg, bot, n, seed, trace=False, keep=0, copies=1, peer=False):
        self.keep, self.kept = keep, []  # the first `keep` economies' monthly inputs, for fit.py's comparison with the logs
        self.K, self.n, self.trace = K, n, trace
        throughput = np.asarray(K["LEV_CRUNCH_THROUGHPUT"], dtype=float)
        self.debt_point_scale = np.divide(lv.LEGACY_THROUGHPUT, throughput, out=np.ones_like(throughput), where=throughput > 0)
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
        G = GOODS_MAX
        self.goods, growth = draw("goods"), draw("goods_growth")
        rg = tile(np.random.default_rng([seed, 29]))  # the basket's own draws, so the others stay
        # a good enters when the line reaches it (the first goods before 1836); its share of trade is log-normal
        self.entry = np.maximum(60 + (np.arange(G) - self.goods[:, None] + 1) / np.maximum(growth[:, None], 1e-9) * 1200, 0)
        self.share0 = np.exp(SHARE_SD * rg.standard_normal((n, G)))
        self.share = self.share0 * (self.entry <= 0)
        self.share /= self.share.sum(1, keepdims=True)
        self.price_z = np.exp(PRICE_SPREAD * rg.standard_normal((n, G)))
        self.price_sd0, self.price_keep = draw("price_sd"), 1 - 1 / draw("price_months")
        self.w = np.minimum(self.share / self.kg("EXPOSURE_FULL"), 1)
        # The simulated basket has anonymous goods. Assign real goods without replacement for their tax costs.
        rf = tile(np.random.default_rng([seed, 23]))
        tax = goods_tax_bases()
        self.goods_ids = np.argsort(rf.random((n, len(tax))), axis=1)[:, :G]
        base_cost = np.minimum(tax[self.goods_ids], levers.DEFAULT_TAX_COST) * levers.LEVER_TAX_SHARE
        categories = sectors.BY_GOOD
        category_ids = np.array([tuple(sectors.GROUPS).index(categories[good]) for good in g.GOODS])
        category_count = len(sectors.GROUPS)
        self.category_index = category_ids[self.goods_ids] + np.arange(n)[:, None] * category_count
        self.category_weight = np.bincount(self.category_index.ravel(), self.share.ravel(), minlength=n * category_count)
        self.category_trend = np.full(n * category_count, np.nan)
        self.sentiment_rng = tile(np.random.default_rng([seed, 47]))
        self.sentiment_term = np.zeros_like(self.share, dtype=np.int16)
        self.sentiment_case = np.zeros_like(self.sentiment_term)
        self.term_effect = np.zeros_like(self.share)
        self.base_cost = base_cost
        self.set_shares(self.entry <= 0)
        # a few countries see most of the wars and foreign panics: their rates even on a log scale
        self.f_p, self.war_p = _draw(rng, I["foreign_rate"], n, log=True) / 1200, _draw(rng, I["war_rate"], n, log=True) / 1200
        self.appr_sd, self.legit, self.sdebt, self.reserves = draw("approval_sd"), draw("legitimacy"), draw("scaled_debt"), draw("reserves")
        self.depth, self.steady = draw("depth"), draw("steady")
        # the world beyond: capital flight, the Long Depression and war endings, from their own draws so the ones above stay
        r2 = self.rng2 = tile(np.random.default_rng([seed, 2]))
        self.flight_p = _draw(r2, I["flight_rate"], n) / 1200 * (r2.random(n) < _draw(r2, I["flight_share"], n))
        self.worlds = None
        self.world_args = (K, cfg, n, seed, copies)
        self.ld_join_chance = _draw(r2, I["ld_join"], n)
        self.ld_member = np.zeros(n, bool)
        self.auth = _draw(r2, I["ai_authority"], n, log=True)
        self.trust = np.full(n, centres.CALM / 2)  # centres._trust: every country's Exchange starts Respected
        self.charter = np.zeros(n, int)
        self.charter_until = np.zeros(n, int)
        self.desired_charter, self.desired_credit = player_finance_orders(cfg) if bot != "ai" and not peer else (None, None)
        self.rule = "heightened" if I["heightened"] else "historical"
        self.money, self.law_mult, self.panic_mult, self.alloc = self.money_base.copy(), np.ones(n), np.ones(n), np.ones(n)
        # journal.reform_parts: the Monetary Standard's, times the institutions a Commission of Inquiry made (the AI's only)
        self.reform = {k: np.ones(n) for k in ("boom", "heat", "risk", "panic_len", "rescue", "credit", "loss")}
        self.enacted = {r: np.zeros(n, bool) for r in journal.REFORMS}
        self.set_laws(range(n))
        # the AI's temperament (credit_ai.TEMPERS, without the ruler traits) and the interest groups in government
        self.temper_u = rng.random(n)
        self.government = {ig: rng.random(n) < 0.5 for ig in credit_ai.PREFS}
        self.industrialists = self.government["industrialists"]
        self.bot_name = bot
        self.set_temper()
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
        self.rng_lure = tile(np.random.default_rng([seed, 11]))  # rival Lures, on their own draws so the others stay
        self.lure_p = _draw(self.rng_lure, I.get("lure_rate", INPUTS["lure_rate"][0]), n)
        self.gdp_base = np.full(n, 1e7)
        self.base_cash, self.base_debt = self.reserves.copy(), self.sdebt.copy()
        self.cash_draw = np.zeros(n)  # unreplenished intervention spending in pounds
        self.base_net = _draw(rf, I["weekly_balance"], n)
        self.observed_default, self.observed_near = f.copy(), f.copy()
        self.in_default, self.nearly_broke = f.copy(), f.copy()
        self.credit_capacity = np.ones(n)  # native borrowing limit as a share of GDP
        self.tech_line = self.hist_rows = None
        if I["fiscal_profiles"]:
            years, profiles = fiscal.profiles()
            percentile = rf.random(n)
            ranks = (percentile * profiles["gdp"].shape[1]).astype(int)
            self.fiscal_ranks = np.tile(ranks, (len(years), 1))
            slots = 1
            if peer:
                roster = fiscal.power_tags()
                slots = len(roster)
                self.fiscal_gp = np.zeros_like(self.fiscal_ranks, bool)
                for era, tags in enumerate(profiles["tag"]):
                    for slot, tag in enumerate(roster):
                        match = np.flatnonzero(tags == tag)
                        if match.size:
                            self.fiscal_ranks[era, slot::slots] = match[0]
                            self.fiscal_gp[era, slot::slots] = profiles["gp"][era, match[0]] > 0
            self.fiscal_dates = [rf.uniform((a - 1836) * 12, (b - 1836) * 12, n // slots).repeat(slots)
                                 for a, b in zip(years, years[1:])]
            self.fiscal_era = np.full(n, -1)
            self.gdp_base = profiles["gdp"][0, self.fiscal_ranks[0]].copy()
            if I["observed_research"]:
                tags = np.tile(fiscal.power_tags(), n // slots) if peer else profiles["tag"][0, ranks]
                if history() is not None:
                    self.follow_history(ranks, tags if peer else None, cfg["tech_years"], tile(np.random.default_rng([seed, 73])))
                else:
                    self.bound_research(tags, cfg["tech_years"], tile(np.random.default_rng([seed, 73])), fiscal.research_bounds())
        for tech, parents in research_order():
            if tech in self.tech_at:
                for parent in parents:
                    self.tech_at[tech] = np.maximum(self.tech_at[tech], self.tech_at.get(parent, self.months + 1))
        self.drift = self.law_moves if hasattr(self, "law_moves") else self.plan_drift(tile(np.random.default_rng([seed, 1836])), cfg.get("law_drift", LAW_DRIFT))
        self.pool_base_x = np.ones(n)
        self.gdp = self.gdp_base.copy()
        self.gdp_avg = self.gdp.copy()
        self.pool = self.gdp * self.pool_share
        self.conf, self.stance, self.debt, self.c_mood = np.full(n, K["CONF_START"], float), z.copy(), z.copy(), z.copy()
        self.lax = np.full(n, K["LAX_START"], float)
        self.lev_avg, self.lev_last = np.full(n, np.nan), np.full(n, np.nan)
        self.held, self.crunch, self.bite, self.bailed = z.copy(), z.copy(), z.copy(), f.copy()
        self.cap = np.ones(n)  # GDP built by the pool income the market added or took (inv_growth), against none
        self.bonus_inv = z.copy()
        self.record, self.record_held = z.copy(), z.copy()  # leverage's lasting reward (spec_lev_record, its modifier's steps)
        self.heat, self.has_heat, self.mania, self.mania_ago = z.copy(), f.copy(), f.copy(), np.full(n, 10 ** 6)
        self.panic, self.in_panic, self.panic_len, self.elapsed, self.cut, self.rescued = z.copy(), f.copy(), z.copy(), z.copy(), z.copy(), f.copy()
        self.funded_rescue = f.copy()  # suspending the Bank Act also sets spec_rescued but leaves the modifiers at full strength
        # the AI's rescue pledge (centres._pledge_month): pledged, months of notice left (0 none), pledged as this month's panic began
        self.pledge, self.pledge_leave, self.pledge_start = f.copy(), np.zeros(n, int), f.copy()
        self.rng_pledge = tile(np.random.default_rng([seed, 13]))  # its monthly roll (AI_PLEDGE_CHANCE), on its own draws
        self.panic_cd, self.stance_cd, self.fever, self.xs_bad = z.copy(), z.copy(), f.copy(), z.copy()
        self.appr, self.war_left, self.war_c, self.ld_recent = z.copy(), z.copy(), z.copy(), z.copy()
        # the AI's journal (journal.MONTHLY_AI): months without a panic, an inquiry since the last, months left of a sitting
        # Commission (-1 none), of the conversion's cooldown and of the moral hazard after the Bank Act is suspended
        self.calm_m, self.inquired, self.sitting, self.converted, self.hazard = z.copy(), f.copy(), np.full(n, -1), z.copy(), z.copy()
        self.mania_pick = np.full(n, -1)
        # goods (exposure.py's spec_exp_<g>, generate.values' spec_peak/spec_sev, and each good's price and its averages)
        self.h, self.peak, self.exp = np.ones((n, G)), np.ones((n, G)), np.zeros((n, G))
        keep = self.price_keep[:, None]
        self.price_level = self.price_sd() / np.sqrt(np.maximum(1 - keep ** 2, 1e-3)) * self.sentiment_rng.standard_normal((n, G))
        self.price_premium = np.clip(self.price_level, -0.75, 0.75)
        self.fast, self.slow = self.price_premium.copy(), self.price_premium.copy()
        self.glut = np.zeros((n, G))
        self.word = np.zeros((n, G), int)
        self.lever, self.push, self.risk, self.h_raw = np.zeros((n, G), int), np.ones((n, G)), np.zeros((n, G)), np.ones((n, G))  # levers.py: -1 Restrain, 1 Encourage
        self.player_orders = player_lever_orders(cfg.get("player_lever_orders", ())) if bot != "ai" else {}
        if self.player_orders:
            self.lever_wait = np.zeros((n, G), int)
            self.grace_until = np.zeros((n, G), int)
        # results
        self.stats = {k: z.copy() for k in ("trust_top_months", "panics", "panic_months", "panic_len_sum", "mania_months", "manias", "mania_panics",
                                           "bursts", "crunch_max", "crunch_months", "crunch_spells", "frozen", "rescues", "rescue_cost", "bailouts",
                                           "bailout_cost", "restrains", "restrain_months", "reforms", "tight_months", "loose_months", "lev_sum", "lev_max", "gdp_gap_sum",
                                           "pool_gap_sum", "conf_sum", "lent_sum", "debt_sum", "panic_loss_sum", "inv_panic_sum", "inv_calm_sum",
                                           "boom_gap_sum", "boom_months", "steady_gap_sum", "steady_months", "low_months", "up_months", "reckless_months",
                                           "late_panic_months", "pledge_months", "pledge_rescues", "distrust_late_months")}
        self.was_bad = f.copy()
        # lending frozen (spec_crunch_lend 0): each finished spell's length, as frozen_spells.py reads the game's logs
        self.stats["frz_hist"] = np.zeros((n, FRZ_BINS), int)
        self.frz_run = np.zeros(n, int)
        self.loss_left = z.copy()
        self.hist = [] if trace else None
        self.snap = []

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

    def set_shares(self, f):
        """Each good's share of trade (of the goods traded, f), its weight (generate's spec_weight_<g>),
        its sector's weight and its lever's Authority cost."""
        self.share = self.share0 * f
        self.share /= np.maximum(self.share.sum(1, keepdims=True), 1e-12)
        self.w = np.minimum(self.share / self.kg("EXPOSURE_FULL"), 1)
        self.category_weight = np.bincount(self.category_index.ravel(), self.share.ravel(), minlength=self.category_weight.size)
        self.lever_cost = np.floor(self.base_cost * (levers.LEVER_FLOOR + (1 - levers.LEVER_FLOOR) * self.w) / levers.COST_STEP + 0.5) * levers.COST_STEP

    def price_sd(self):
        """A good's price swing a month (see SHARE_SD): smaller for a heavier good and a larger economy; none untraded."""
        size = (np.maximum(self.gdp, 1) / PRICE_GDP_AT) ** -PRICE_GDP_EXP
        start = 1 + PRICE_START * np.exp(-getattr(self, "m", 0) / PRICE_START_MONTHS)
        return self.price_sd0[:, None] * start * np.maximum(self.w, 0.01) ** -PRICE_W_EXP * size[:, None] * self.price_z * (self.share > 0)

    def set_temper(self):
        """credit_ai.TEMPERS weighted by the economic law, the lean and the AI's policy (finances() renews the lean)."""
        K, n = self.K, self.n
        w = np.stack([np.full(n, float(b)) for _, (b, adds) in sorted(credit_ai.TEMPERS.items())], 1)
        for i, (_, (b, adds)) in enumerate(sorted(credit_ai.TEMPERS.items())):
            for trig, a in adds:
                m = re.search(r"law_type:law_(\w+)", trig)
                if m:
                    w[:, i] += a * (self.econ == m.group(1))
        tilt = K["TEMPER_TILT"] - credit_ai.TEMPER_TILT  # the swept tilt, not the import-time table's
        w[:, 0], w[:, 2] = w[:, 0] - tilt, w[:, 2] + tilt
        cum = np.cumsum(w / w.sum(1, keepdims=True), 1)
        self.temper = (self.temper_u[:, None] > cum).sum(1) - 1
        self.lean = self.temper * K["TEMPER_SHIFT"] + sum(
            pref * K["IG_SHIFT"] * self.government[ig] for ig, pref in credit_ai.PREFS.items())
        b = BOTS[self.bot_name]
        self.pol = (ai_policy(K, self.temper, self.lean) if b == "ai" else
                    ai_policy(K, np.zeros(n), np.zeros(n)) | b | {"timing": True} if b.get("like_ai") else b)

    def follow_history(self, ranks, tags, windows, rng):
        """observed_research with fit.py --history: each economy follows the clean 1.2.0 campaign's country of its GDP rank
        at each fiscal snapshot's year (a Great Power world's economy its own tag throughout): its Economic System and
        Monetary Standard month by month, and each technology from the first month it or an earlier country of its rank
        had it. After the last country's last logged month the laws stay; a technology not seen by then draws inside its
        TECH_YEARS window, no earlier than that month (bound_research)."""
        H = history()
        M = H["econ"].shape[1]
        if tags is not None:  # Great Power worlds: one tag throughout
            row = {t: i for i, t in enumerate(H["tags"])}
            who = np.tile(np.array([row[t] for t in tags]), (len(H["start"]), 1))
        else:
            who = H["rank"][:, np.minimum(ranks, H["rank"].shape[1] - 1)]  # (snapshots, n): the row followed from each
        era = np.searchsorted(H["start"], np.arange(M), "right") - 1
        rows = who[era].T  # (n, M)
        cols = np.arange(M)
        econ_names = np.array(["none"] + g.LOG_ECON, dtype=object)
        money_names = np.array(["none"] + monetary.LAWS, dtype=object)
        moves = []
        for kind, names, attr in (("econ", econ_names, "econ"), ("money", money_names, "money_base")):
            codes = H[kind][rows, cols]
            start = codes[:, 0] > 0
            getattr(self, attr)[start] = names[codes[start, 0]]
            # each later change of its law: the j-th change's month and law, -1 where it has no j-th
            change = (codes[:, 1:] != codes[:, :-1]) & (codes[:, 1:] > 0)
            for j in range(int(change.sum(1).max(initial=0))):
                nth = change & (np.cumsum(change, 1) == j + 1)
                at = np.where(nth.any(1), nth.argmax(1) + 1, -1)
                moves.append((kind, at, names[codes[np.arange(self.n), np.maximum(at, 0)]]))
        self.law_moves = moves
        self.set_laws(range(self.n))
        self.set_temper()
        # the techs a month are its country's: one country of a rank may lack what the last had (has() reads them)
        bits = H["techs"][rows, cols]
        self.tech_line = np.ascontiguousarray(bits.T)
        self.hist_rows = np.ascontiguousarray(rows.T)  # inputs(): their world, when world_replay is on; step(): depth, steadiness
        self.depth, self.steady = H["depth"][rows[:, 0], 0].astype(float), H["steady"][rows[:, 0], 0].astype(float)
        last = H["last"][rows[:, -1]]
        key = np.array([f"{a}:{b}" for a, b in zip(who.T.tolist(), last)])  # economies with the same rows share their bounds
        bounds = {}
        for k in np.unique(key):
            i = np.flatnonzero(key == k)[0]
            bounds[k] = {t: (0, 0) if (bits[i, -1] >> b) & 1 else (last[i] + 1, np.inf) for b, t in enumerate(g.LOG_TECHS)}
        self.bound_research(key, windows, rng, bounds)  # tech_at: after the log

    def bound_research(self, tags, windows, rng, bounds):
        distinct, inverse = np.unique(tags, return_inverse=True)
        for tech, (lo, hi) in windows.items():
            if tech not in fiscal.FINANCE_TECHS:
                continue
            earliest, latest = np.array([bounds[tag][tech] for tag in distinct])[inverse].T
            lower, upper = np.maximum(lo * 12, earliest), np.minimum(hi * 12, latest)
            conflict = lower > upper
            # When observations exclude the scenario window, use the recorded bracket. After the last
            # absence with no observed unlock, leave at least one further snapshot interval to research.
            lower = np.where(conflict, earliest, lower)
            fallback = np.where(np.isfinite(latest), latest, earliest + max(360, (hi - lo) * 12))
            upper = np.where(conflict, fallback, upper)
            self.tech_at[tech] = np.floor(lower + rng.random(self.n) * (upper - lower + 1)).astype(int)

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
            if kind == "money":
                fiat = move & (dest == "fiat_money")
                at = np.where(fiat, np.maximum(at, self.tech_at.get(monetary.FIAT_TECH, self.months + 1)), at)
            plan[kind], after[kind] = np.where(move, dest, plan[kind]), np.where(move, at, after[kind])
            out.append((kind, at, dest))
        return out

    def has(self, tech):
        if self.tech_line is not None and self.m < len(self.tech_line) and tech in TECH_BIT:  # follow_history's months
            return (self.tech_line[self.m] >> TECH_BIT[tech]) & 1 > 0
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

    def after_risks(self):
        """journal.spec_after_risks: confidence if the Risks bar's risks struck now, the costliest unrestrained boom ending
        (spec_risk_top, from 1) and the bubble bursting now (spec_burst_now, over 0.05). ponytail: the panic-source, war and
        default chips are left out; the engine draws foreign shocks and wars without the plays that warn of them."""
        top = np.where(self.lever == -1, 0, self.risk).max(1)
        top = np.where(top >= 1, np.minimum(top, self.conf), 0)
        per = self.K["BURST_PER_HEAT"] if self.rule == "historical" else g.VOLATILITY[self.rule]["per"]
        burst = np.where(self.has_heat, np.minimum(self.heat * per, self.K["BURST_BELOW"]), 0)
        return np.maximum(self.conf - top - np.where(burst > 0.05, burst, 0), 0)

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
        cap = np.where(self.has("central_banking"), self.K["RESCUE_MONTHS"], self.K["RESCUE_MONTHS_PRIVATE"]) - self.enacted["llr"]  # spec_reform_rescue_months
        return np.where(self.in_panic, np.minimum(cap, np.maximum(1, np.ceil(self.panic / 2))), cap)

    def rescue_cost(self):  # generate.values: spec_rescue_cost, paid in pounds and reported as a share of GDP
        K = self.K
        share = np.where(self.has("central_banking"), K["RESCUE_COST"], K["RESCUE_COST_PRIVATE"]) * self.reform["rescue"] * self.lax_k("LAX_COST")
        share = share * np.where(self.pledge, K["EXCH_PLEDGE_COST"], 1)  # centres.PLEDGE_COST, before the floor
        share = np.maximum(share, K["RESCUE_FLOOR"])
        return self.treasury_price(share * np.clip(self.panic / K["RESCUE_REF_MONTHS"], 1, 2))

    def treasury_price(self, share):
        return np.maximum(1, np.floor(self.gdp * share / 1000 + 0.5)) * 1000 / self.gdp

    def finances(self):
        if self.I["fiscal_profiles"]:
            era = sum((self.m >= date).astype(int) for date in self.fiscal_dates)
            if np.any(era != self.fiscal_era):
                _, p = fiscal.profiles()
                idx = (era, self.fiscal_ranks[era, np.arange(self.n)])
                size = p["gdp"][idx]
                self.base_cash, self.base_debt = p["cash"][idx] / size, p["sdebt"][idx]
                self.base_net, self.auth = p["net"][idx] / size, p["auth"][idx]
                # Native credit limits can be inferred for borrowers. For others, use the observed borrowers' median.
                borrowers = p["sdebt"] > 0
                capacities = p["debt"][borrowers] / (p["sdebt"][borrowers] * p["gdp"][borrowers])
                self.credit_capacity = np.divide(p["debt"][idx], size * self.base_debt,
                    out=np.full(self.n, np.median(capacities)), where=self.base_debt > 0)
                self.observed_default, self.observed_near = p["default"][idx] > 0, p["near"][idx] > 0
                self.industrialists = p["ind"][idx] > 0
                self.lean = self.temper * self.K["TEMPER_SHIFT"] + self.K["IG_SHIFT"] * (p["ind"][idx] - p["intel"][idx])
                if self.bot_name == "ai":
                    self.pol = ai_policy(self.K, self.temper, self.lean)
                self.fiscal_era = era
        # Domestic weekly output at base prices is approximated by each simulated good's share of GDP.
        size = self.gdp[:, None]
        weekly = self.share * size / 52
        self.subsidy = np.floor(weekly * levers.SUBSIDY_SHARE + 0.5) / size
        levy = np.floor(weekly * levers.LEVY_SHARE + 0.5) / size
        self.net_income = self.base_net + ((self.lever < 0) * levy - (self.lever > 0) * self.subsidy).sum(1)
        self.cash_draw = np.maximum(self.cash_draw - np.maximum(self.net_income, 0) * self.gdp * g.WEEKS_PER_MONTH, 0)
        self.update_treasury()

    def update_treasury(self):
        available = self.base_cash - self.cash_draw / self.gdp
        self.reserves = np.maximum(available, 0)
        self.sdebt = self.base_debt + np.maximum(-available, 0) / self.credit_capacity
        self.in_default = self.observed_default | (self.sdebt >= 1)
        credit_room = np.maximum(1 - self.sdebt, 0) * self.credit_capacity
        self.nearly_broke = self.observed_near | ((self.sdebt > 0) & (credit_room < -self.net_income * economy.BROKE_WEEKS))

    def pay(self, cost):
        self.sdebt += np.maximum(cost - self.reserves, 0) / self.credit_capacity
        self.cash_draw += cost * self.gdp
        self.reserves = np.maximum(self.reserves - cost, 0)
        self.in_default |= self.sdebt >= 1

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
        if W and self.hist_rows is not None:  # follow_history's countries: their own wars, crises and foreign panics
            H, M = history(), len(self.hist_rows)
            # ponytail: past the campaign's end its last REPLAY_LOOP months repeat; a longer clean campaign would replace it
            k = self.m if self.m < M else M - REPLAY_LOOP + (self.m - M) % REPLAY_LOOP
            who = self.hist_rows[min(self.m, M - 1)]
            f = H["foreign"][who, k]
            self.rp_turmoil = H["turmoil"][who, k]
            self.rp_foreign = np.where(f < 0, f * self.K["CONTAGION"] / H["contagion"], f)
            self.war_end = H["warend"][who, k]
            self.rp_business = H["business"][who, k] if "business" in H else None
        elif W:  # the drawn wars above still run, for the draws' sake, but the replayed ones count
            k = self.m % W["t"].shape[1]
            f = W["f"][self.pick, k]
            self.rp_turmoil = W["t"][self.pick, k]
            self.rp_foreign = np.where(f < 0, f * self.K["CONTAGION"] / W["contagion"], f)  # a hit scales with Contagion
            self.war_end = W["w"][self.pick, k]
        # spare Authority moves with decrees, laws and wars: a fresh draw every AUTH_YEARS on average
        auth_change = r2.random(n) < 1 / (AUTH_YEARS * 12)
        auth_draw = _draw(r2, self.I["ai_authority"], n, log=True)
        if not self.I["fiscal_profiles"]:
            self.auth = np.where(auth_change, auth_draw, self.auth)
        self.mood_u = r.uniform(-1, 1, n)
        self.appr = self.appr * 0.95 + r.normal(0, 1, n) * self.appr_sd
        self.ai_u = r.random((n, 4))

    def feedback(self):
        """The mod's modifiers back into the economy (generate.modifiers, leverage.modifiers): throughput moves GDP by
        e_gdp, the investing classes' investment moves pool income by e_pool. ponytail: a level, not a growth path."""
        K = self.K
        pm = np.where(self.funded_rescue, K["RESCUE_CUT"], 1.0) * self.in_panic
        step = K["BAND_INVEST_STEP"]  # generate.BAND_INVEST: the tier's place times the step, read from K so a sweep reaches it
        band = _first([self.conf < b[2] for b in BANDS], [g.TIER_STEPS[b[0]] * step for b in BANDS], g.TIER_STEPS["mania"] * step)
        band = np.where(self.in_panic & (self.conf < BANDS[0][2]), 0, band)  # spec_conf_panic_held carries no investment
        smooth = (K["LEV_REWARD_TP_FULL"] > 0) | (K["LEV_REWARD_INV_FULL"] > 0)  # leverage.SMOOTH
        sh = lev_shape(self.held, K["LEV_RUIN"], K["LEV_REWARD_CURVE"])
        taper = np.where(K["LEV_REWARD_TAPER"] >= 0, np.clip(self.held - K["LEV_REWARD_MAX"], 0, K["LEV_RUIN"] - K["LEV_REWARD_MAX"]) * K["LEV_REWARD_TAPER"], 0)
        step = np.minimum(self.held, K["LEV_REWARD_MAX"]) * K["LEV_REWARD"] + taper  # leverage.taper_value; held never passes MAX untapered
        self.bonus_tp = np.where(smooth, K["LEV_REWARD_TP_FULL"] * sh, step)
        self.bonus_inv = np.where(smooth, K["LEV_REWARD_INV_FULL"] * sh, 0)
        self.panic_tp, self.bad_tp = pm * K["PANIC_THROUGHPUT"], -self.bite * K["LEV_CRUNCH_THROUGHPUT"]
        self.bad_inv = -self.bite * K["LEV_CRUNCH_INVEST"]
        self.lever_tp = (self.lever * self.share).sum(1) * levers.LEVER_THROUGHPUT  # the levered goods' producers
        self.lever_tp = self.lever_tp + (self.term_effect * sentiment.TP_SHARE * self.share).sum(1)  # Favored/Shunned producers
        self.bonus_tp = self.bonus_tp + self.record_held * lv.RECORD_STEP  # spec_lev_record, the lasting part
        self.tp = self.bonus_tp + self.panic_tp + self.bad_tp + self.lever_tp
        self.inv = band + pm * K["PANIC_INVEST"] + self.bad_inv + self.bonus_inv
        self.pool_inv = np.maximum(1 + self.I["e_pool"] * self.inv, 0.02)
        # the pool income the market adds (or takes) builds (or forgoes) GDP that stays: inv_growth a year per unit of it over GDP
        self.cap *= np.exp(self.I["inv_growth"] / 12 * self.pool_share * self.pool_base_x * (self.pool_inv - 1))
        self.gdp = self.gdp_base * self.cap * np.maximum(1 + self.I["e_gdp"] * self.tp, 0.05)

    def advance_sentiment(self, premium, rolls):
        """One weighted draw per open side per country. The no-award entry is first."""
        term = self.sentiment_term
        term -= np.sign(term)
        active = self.law_mult[:, None] > 0
        term[~np.broadcast_to(active, term.shape)] = 0
        material = active & (self.share > 0) & (term == 0)
        side = np.where(material & (premium >= sentiment.PREMIUM), 1,
                        np.where(material & (premium <= -sentiment.PREMIUM), -1, 0))
        case = self.sentiment_case
        case[:] = side * np.minimum(sentiment.MATURE, np.maximum(0, side * case) + 1)
        for column, (_, sign) in enumerate(sentiment.SIDES):
            weights = (sign * case >= sentiment.QUALIFY).astype(int) + (sign * case >= sentiment.MATURE)
            weights += (sign * case >= sentiment.QUALIFY) & (self.share >= sentiment.SHARE)
            totals = weights.cumsum(axis=1)
            # no cap: every running term, either side, adds no-award tickets (the Favored draw's award counts for the Shunned one)
            passes = sentiment.PASS_WEIGHT + sentiment.PASS_PER_TERM * (term != 0).sum(axis=1)
            passes = passes * (1 - sign * sentiment.TILT * (self.conf - sentiment.CONF_MID) / sentiment.CONF_MID)
            ticket = rolls[:, column] * (passes + totals[:, -1]) - passes
            awarded = ticket >= 0
            rows = np.flatnonzero(awarded)
            goods = (totals[rows] > ticket[rows, None]).argmax(axis=1)
            term[rows, goods] = sign * sentiment.MONTHS
            case[rows, goods] = 0

    # ---- one month: spec_monthly in order ----
    def step(self, global_crisis=None):
        K, n = self.K, self.n
        if global_crisis is None:
            if self.worlds is None:
                self.worlds = DepressionWorlds(*self.world_args)
            global_crisis = self.worlds.step(self.m)
        phase, began = global_crisis
        tied = self.rng2.random(n) < self.ld_join_chance
        self.ld_member = np.where(began, self.in_panic | (self.ld_recent > 0) | tied, self.ld_member & (phase > 0))
        if self.hist_rows is not None and self.m < len(self.hist_rows):  # follow_history: its country's depth and steadiness
            H, who = history(), self.hist_rows[self.m]
            self.depth, self.steady = H["depth"][who, self.m].astype(float), H["steady"][who, self.m].astype(float)
        if self.m % 12 == 0:  # a new year: goods the line reaches start trading
            self.set_shares(self.entry <= self.m)
        for kind, at, dest in self.drift:  # a law changed this month
            due = at == self.m
            if due.any():
                (self.econ if kind == "econ" else self.money_base)[due] = dest[due]
                self.set_laws(np.flatnonzero(due))
        self.inputs()
        self.feedback()
        self.finances()
        self.exch_mood, self.exch_recover, _ = centres.links(self.trust, 0)  # the Exchange's links (centres._links_values)
        ld = np.where(self.ld_member & (self.law_mult > 0), phase, 0)
        c_world = np.array([0] + [depression.PRESSURE.get(p, depression.PRESSURE.get(str(p), 0)) for p in (1, 2, 3)], float)[ld]
        pm = self.pool_month()
        self.cut_shown = self.cut * np.where(self.funded_rescue, K["RESCUE_CUT"], 1) * self.in_panic
        # trust's level effects (centres._trust_mods, from last month's trust): Industrialists' approval, construction allocation.
        # ponytail: allocation only speeds the pool's spending; construction has no path to GDP here (a level, not a growth path)
        t_lv = np.clip((self.trust // (centres.CALM / 4)).astype(int), 0, 3)
        self.trust_ind = TRUST_IND[t_lv] - np.where(t_lv == 0, K["TRUST_IND_DISTRUST"], 0)
        spend_mult = 1 + np.take([-2, -1, 1, 2], t_lv) * K["TRUST_ALLOC_STEP"]
        spend = self.pool * self.spend * spend_mult * (1 - self.alloc * self.cut_shown)  # construction draws on the pool between pulses
        self.pool = self.pool - spend + pm
        pool_was, debt_was, lax_was, conf_was = self.pool.copy(), self.debt.copy(), self.lax.copy(), self.conf.copy()
        c_burst, c_drop, c_rescue, c_caution, recall, clawed, writeoff = (np.zeros(n) for _ in range(7))
        self.xs_bad = np.zeros(n)  # leverage.CLEAR_DROP

        # goods (generate.monthly's per-good block): interest, peak, booms and their endings
        if self.desired_charter:
            self.grant_charter(self.desired_charter)
        hm = self.law_mult * self.stance_hype() * np.where(self.has("joint_stock_companies"), vt.STOCK_HYPE, 1) * self.depth * self.band_gain()
        hm *= np.where(self.charter == 1, centres.KNOWN_HYPE, 1)
        hmd = self.law_mult * np.minimum(self.stance_hype(), 1) * np.where(self.has("joint_stock_companies"), vt.STOCK_HYPE, 1) * self.depth
        # each good's price (generate: spec_dev_<g>), its fast and slow averages, and their gap's push (spec_trend_<g>)
        keep, sd = self.price_keep[:, None], self.price_sd()
        z = self.sentiment_rng.normal(0, 1, (n, GOODS_MAX + 1))
        step = (np.sqrt(1 - PRICE_COMMON) * z[:, 1:] + np.sqrt(PRICE_COMMON) * z[:, :1]) * sd
        self.price_level = np.clip(keep * self.price_level + step, -0.75, 0.75)
        noise = self.sentiment_rng.normal(0, 1, self.share.shape) * PRICE_NOISE * sd / np.sqrt(np.maximum(1 - keep ** 2, 1e-3))
        self.price_premium = np.clip(self.price_level + noise, -0.75, 0.75) * (self.share > 0)
        self.fast = self.fast * (1 - g.FAST) + self.price_premium * g.FAST
        self.slow = self.slow * (1 - g.SLOW) + self.price_premium * g.SLOW
        trend = (self.fast - self.slow) * g.HYPE_GAIN
        self.advance_sentiment(self.price_premium, self.sentiment_rng.random((n, 2)))
        previous = self.category_trend[self.category_index]
        supported = np.sign(trend) * np.clip(np.sign(trend) * previous, 0, np.abs(trend))
        signal = np.where(np.isnan(previous), trend, (1 - sectors.CATEGORY_WEIGHT) * trend + sectors.CATEGORY_WEIGHT * supported)
        totals = np.bincount(self.category_index.ravel(), (self.share * trend).ravel(), minlength=self.category_weight.size)
        np.divide(totals, self.category_weight, out=self.category_trend, where=self.category_weight > 0)
        gain = np.where(signal >= 0, hm[:, None], hmd[:, None]) * signal
        h = np.where(gain >= 0, 1 + gain, 1 / (1 - np.minimum(gain, 0)))
        h = np.clip(h, 1 / self.kg("HYPE_MAX"), self.kg("HYPE_MAX"))
        self.glut = np.maximum(self.glut - 1, 0)
        h = np.where(self.glut > 0, self.kg("GLUT_HYPE"), h)
        # the speculation levers (levers.push_values, hype_push): LEVER_EASE of the way to the full push at last month's confidence
        self.h_raw = h
        self.term_effect = sentiment.effect_np(np, np.sign(self.sentiment_term), self.sentiment_term, self.price_premium, self.conf[:, None], self.share)
        h = np.where((self.glut > 0) | (self.share == 0), h, h * np.maximum(1 + self.term_effect, 0))
        mp = (self.conf / K["CONF_START"])[:, None]
        full = np.where(self.lever < 0, mp / (mp + 1 / levers.PUSH["restrain"] - 1), np.where(self.lever > 0, 1 + (levers.PUSH["encourage"] - 1) * mp, 1))
        self.push = np.where(self.lever != 0, self.push + (full - self.push) * levers.LEVER_EASE, 1)
        h = np.clip(h * self.push, 1 / self.kg("HYPE_MAX"), self.kg("HYPE_MAX"))
        h = np.where(self.lever < 0, np.maximum(h, levers.RESTRAIN_TO), h)
        self.h = h
        # generate.word_block uses buffered boundaries once a traded good already has a word.
        self.word = self.goods_words(h)
        keep = np.where(self.lever < 0, g.RESTRAIN_DEFLATE, 0.97)  # restrained, the peak deflates faster
        nxt = np.where(h > self.peak, h, self.peak * keep + (1 - keep))  # spec_peak_next
        wind = np.where(self.lever < 0, np.maximum(self.peak - nxt, 0), 0)  # spec_restrain_cost, before its rate
        self.peak = nxt
        sev = _first([self.peak >= p for _, p, *_ in g.UNWINDS], [s for s, *_ in g.UNWINDS], 0)  # spec_sev_next
        self.lever = np.where((self.lever > 0) & (sev >= 2), 0, self.lever)
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
        self.n_end_s = {}
        for s in (3, 2, 1):
            e = (sev == s) & (h < below[s])
            self.n_end_s[s] = e.sum(1)
            ends |= e
            rr += e * (self.peak - 1) * rate[s] * self.w * exp_mult
            self.glut = np.where(e, months[s], self.glut)
        crash_raw = rr.sum(1)
        restrain_raw = (wind * rate[1] * self.w * exp_mult).sum(1)  # a restrained boom winds down as a Correction
        self.peak = np.where(ends, 1, self.peak)
        self.exp = np.where(ends, self.exp * 0.5, self.exp)  # exposure.ended
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
        appr = self.appr + credit_ai.IG_APPROVAL * self.stance * self.industrialists + self.trust_ind
        appr += K["PANIC_APPROVAL"] * self.in_panic * np.where(self.funded_rescue, K["RESCUE_CUT"], 1)
        c_business = np.zeros(n)
        hit = np.zeros(n, bool)
        for op, at, val in economy.BUSINESS:
            m = ~hit & ((appr >= at) if op == ">=" else (appr <= at))
            c_business, hit = np.where(m, val, c_business), hit | m
        if self.replay and self.hist_rows is not None and self.rp_business is not None:  # the followed country's own Business Mood
            c_business = self.rp_business
        c_foreign = -self.foreign * np.where(self.has(g.UNSTANDARD[0]), 1, g.UNSTANDARD[1])  # spec_catch_panic's spec_foreign_loss_mult
        safe = (self.conf >= diplomacy.FLIGHT_FROM) & ~self.in_panic & (self.war_left <= 0) & (self.foreign <= 0)  # spec_capital_flight
        # ponytail: spec_exch_flight (Standing, and PLEDGE_FLIGHT while pledged) is in the fitted flight_size, and in the replayed log
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
        credit *= np.where(self.charter == 3, centres.KNOWN_CREDIT, 1)
        credit = np.maximum(np.minimum(np.minimum(credit, ceiling), room), 0)
        lends = (self.conf > K["CREDIT_FROM"]) & ~self.in_panic & (self.stance != -1) & (crunch_lend > 0) & (self.conf >= p_at)
        lent = np.where(lends, credit, 0)
        # exposure.lend: where the new credit goes, before it is added
        pull = self.share * np.clip((self.h - exposure.HEAT_FROM) / (exposure.HEAT_FULL - exposure.HEAT_FROM), 0, 1)
        pull *= np.where(self.lever < 0, exposure.RESTRAINED, 1)
        pt = pull.sum(1)
        boom_share = np.minimum(pt * K["EXP_PULL"] * self.lax_k("LAX_PULL"), K["EXP_SHARE_MAX"])
        d0 = np.maximum(self.debt, 0)
        tot = d0 + lent
        new = np.where(pt > 0, lent * boom_share / np.where(pt > 0, pt, 1), 0)
        upd = (tot > 0)[:, None] & ((self.exp > 0) | (pull > 0))
        self.exp = np.where(upd, np.clip((self.exp * d0[:, None] + pull * new[:, None]) / np.where(tot > 0, tot, 1)[:, None], 0, 1), self.exp)
        self.pool += lent
        self.lent_yr = lent * 12 / np.maximum(self.gdp, 1e-9) * 100  # the chart's new lending, % of GDP a year
        self.debt += lent

        # cycle.monthly: Lending Standards drift
        quiet = ~self.in_panic & (self.stance != -1) & ~(self.crunch > 0)
        drift_step = np.round(1 / (12 * K["LAX_QUIET_YEARS"]), 5)
        repairing = ~self.in_panic & (self.stance == -1) & (self.crunch <= 0)
        lax_drift = quiet * drift_step * cycle.LAX_SCALE * (1 - self.lax) - repairing * np.clip(self.lax - cycle.SOUND_MID, 0, drift_step)
        lax_booms = (c_crash + c_restrain) * K["LAX_PER_CONF"] * cycle.LAX_SCALE * self.lax
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
        smooth = (K["LEV_REWARD_TP_FULL"] > 0) | (K["LEV_REWARD_INV_FULL"] > 0)  # leverage.SMOOTH: tenths of a month up to RUIN
        tapered = ~smooth & (K["LEV_REWARD_TAPER"] >= 0)  # leverage.TAPERED: tenths of a month, up to RUIN once it tapers
        cap = np.where(smooth | (tapered & (K["LEV_REWARD_TAPER"] > 0)), K["LEV_RUIN"], K["LEV_REWARD_MAX"])  # leverage.HELD_MAX
        reward = np.where(smooth | tapered, np.floor(np.minimum(lev2, cap) * 10 + 1e-9) / 10, np.floor(np.minimum(lev2, K["LEV_REWARD_MAX"])))
        reward = np.where(self.in_panic | (self.crunch > 0), 0, reward)
        lev_now = np.maximum(reward, np.where(self.held > 0, self.held - K["LEV_BONUS_FADE"], 0))
        lev_now = np.where(lent <= 0, np.where(self.held > 0, np.minimum(lev_now, self.held), 0), lev_now)
        self.held = np.maximum(lev_now, 0)
        # leverage.MONTHLY's lasting reward (spec_lev_record): in calm months it closes LEV_RECORD_GAIN of the way to
        # LEV_RECORD_TP per month of leverage (spec_lev_record_to), in a panic or Bad Debts it keeps spec_lev_record_keep;
        # its modifier in whole RECORD_STEPs (spec_lev_record_now)
        bad = self.in_panic | (self.crunch > 0)
        keep = np.maximum(1 - K["LEV_RECORD_LOSS"] * (1 + self.stress(lev2)), 0)
        built = self.record + (lev2 * (K["LEV_RECORD_TP"] / lv.RECORD_STEP) - self.record) * K["LEV_RECORD_GAIN"]  # in RECORD_STEPs
        self.record = np.where(bad, self.record * keep, built)
        self.record_held = np.maximum(np.floor(self.record + 1e-9), 0)

        # mania warning (once per Mania), then Speculative Excess, then the burst
        new_mania = (self.conf >= K["MANIA"]) & ~self.mania
        self.mania |= new_mania
        self.mania_ago = np.where(self.mania, 0, self.mania_ago + 1)
        if BOTS[self.bot_name] == "ai":
            if not hasattr(self, "fever_p"):  # temperament is fixed for the run
                self.fever_p = per_temper(lv.FEVER_BASE, K["AI_FEVER_SCALE"], self.temper, True) / 100
            chance = self.fever_p
            self.fever |= new_mania & (self.ai_u[:, 0] < chance)  # leverage.FEVER_ROLL
        self.mania_pick = np.where(new_mania, self.pick_mania(), self.mania_pick)
        heat_from = K["HEAT_FROM"] if self.rule == "historical" else g.VOLATILITY[self.rule]["heat"]  # the swept value, not the import-time table
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
        per = K["BURST_PER_HEAT"] if self.rule == "historical" else g.VOLATILITY[self.rule]["per"]
        xs = np.minimum((self.heat * per - self.conf) * self.debt_point_scale, K["LEV_CRUNCH_MAX"])  # leverage.ON_BURST (spec_nx_burst and spec_nx_bad are 1: no Exchange specialities)
        self.xs_bad = np.where(burst & (xs > 0), xs, 0)
        newc = burst & (xs > 0)
        self.bite = np.where(newc & ~(self.crunch > 0), 0, self.bite)
        combined = np.minimum(self.crunch + self.xs_bad, K["LEV_CRUNCH_MAX"])
        self.bailed &= ~(combined > self.crunch)
        self.crunch = combined
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
        lax_jump = np.where(end & ~self.rescued, -K["LAX_PANIC"] * self.lax, 0)  # cycle.panic_over
        over = end & ~self.rescued & (self.panic <= 0)  # centres.PANIC_OVER: it ran its full course unrescued
        self.ld_recent = np.where(start, depression.WINDOW_DAYS // 30, np.maximum(self.ld_recent - 1, 0))
        self.lax += lax_jump
        self.stats["panic_len_sum"] += np.where(end, self.elapsed, 0)
        self.in_panic &= ~end
        self.rescued &= ~end
        self.funded_rescue &= ~end
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
            crunch_if = np.clip(self.stress(lev3) * K["LEV_CRUNCH_MAX"] + self.xs_bad, self.crunch, K["LEV_CRUNCH_MAX"])
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
        # centres.PLEDGE_RESCUE, after the trust cut and the clawback: a pledged country is rescued as its panic starts, if it
        # has the banking tech, is not in default and can pay out of reserves; if not, the panic runs and the pledge stands
        self.pledge_start = start & self.pledge
        kept = self.pledge_kept = self.pledge_start & self.has("banking") & ~self.in_default & (self.reserves >= self.rescue_cost())
        self.c_pledge, self.lax_pledge = self.rescue_now(kept) if kept.any() else (np.zeros(n), np.zeros(n))
        self.stats["pledge_rescues"] += kept

        # journal.MONTHLY: months without a panic; a panic clears the last inquiry
        self.calm_m = np.where(self.in_panic, 0, self.calm_m + 1)
        self.inquired &= ~self.in_panic
        self.hazard = np.maximum(self.hazard - 1, 0)
        # the player's levers, or the AI's rules (generate.monthly's is_player = no block)
        c_rescue, c_caution, lax_jump2 = self.decide()
        c_rescue, lax_jump2 = c_rescue + self.c_pledge, lax_jump2 + self.lax_pledge  # the pledged rescue at the panic's start
        self.did_rescue |= self.pledge_kept
        if self.player_orders:
            self.lever_wait = np.maximum(self.lever_wait - 1, 0)
            for day, good, action in self.player_orders.get(self.m, ()):
                self.player_toggle(day, good, action, np.where(ends, 0, sev))
        lax_jump = lax_jump + lax_jump2

        # the Exchange's trust (centres._trust, _crunch, boom_end, spec_exch_panic_cut, PANIC_OVER), for next month's links
        loss = self.reform["loss"] * np.where(self.charter == 2, centres.KNOWN_LOSS, 1)
        by = [K[k] for k in TRUST_KEYS]  # centres.TRUST_BY_LAX, graded by level (centres._trust), from K so a sweep reaches it
        gain = np.where(self.lax < cycle.LAX_CUTS[0], by[0], np.where(self.lax < cycle.LAX_CUTS[1], by[1], by[2])) * centres.TRUST_MONTH
        month = np.where(self.lax >= cycle.LAX_CUTS[3], by[4] * centres.TRUST_MONTH * loss,
                         np.where((self.crunch <= 0) & (self.lax < cycle.LAX_CUTS[2]), gain, 0))
        tr = self.trust + np.where(self.in_panic, 0, month) - (self.crunch > 0) * centres.LINK_CRUNCH * centres.CRUNCH * loss
        te = {int(k): d for k, d in centres.TRUST_END.items()}
        move = _first([sev == s for s in te], list(te.values()), 0)
        tr += (ends * (self.share >= centres.MAIN_SHARE) * np.where(move < 0, move * loss[:, None], move)).sum(1)
        cut_t = centres.PANIC_CUT[0] + centres.PANIC_CUT[1] * np.clip((lev3 - K["LEV_SAFE"]) / (K["LEV_RUIN"] - K["LEV_SAFE"]), 0, 1)
        cut_t = cut_t * np.where(self.pledge_start, K["EXCH_PLEDGE_PANIC"], 1)  # spec_exch_panic_cut: less under the pledge
        tr = np.where(start, tr * (1 - cut_t * loss), tr) * np.where(over, 1 - centres.PANIC_OVER_CUT * loss, 1)
        self.trust = np.clip(tr, 0, centres.CALM)

        # results
        s = self.stats
        s["panic_months"] += self.in_panic
        s["mania_months"] += self.conf >= K["MANIA"]
        s["trust_top_months"] += self.trust >= centres.CALM / 2  # Respected or Trusted (centres.TRUST_LV, quarters of CALM)
        s["manias"] += new_mania
        s["bursts"] += burst
        s["restrain_months"] += c_restrain < -1e-6
        s["crunch_max"] = np.maximum(s["crunch_max"], self.crunch)
        s["crunch_months"] += self.crunch > 0
        s["crunch_spells"] += (self.crunch > 0) & ~self.was_bad
        self.was_bad = self.crunch > 0
        frz = self.crunch_lend() <= 0
        self.frz_end(~frz)
        self.frz_run = np.where(frz, self.frz_run + 1, 0)
        s["tight_months"] += self.stance == -1
        s["loose_months"] += self.stance == 1
        lev4 = self.lev(pm)
        s["lev_sum"] += lev4
        s["lev_max"] = np.maximum(s["lev_max"], lev4)
        gap = self.gdp / self.gdp_base - 1
        s["gdp_gap_sum"] += gap
        # output lost over a panic, against no market: from its start to a year after its end (a panic inside the last
        # one's year extends the window, so the pair counts as two panics sharing it)
        self.loss_left = np.where(self.in_panic, 13, np.maximum(self.loss_left - 1, 0))
        s["panic_loss_sum"] += np.where(self.loss_left > 0, -gap, 0)
        s["inv_panic_sum"] += np.where(self.in_panic, self.pool_inv, 0)
        s["inv_calm_sum"] += np.where(self.in_panic, 0, self.pool_inv)
        up = ~self.in_panic & (self.conf >= TIER["buoyant"][0])
        steady = ~self.in_panic & (self.conf >= TIER["steady"][0]) & (self.conf < TIER["steady"][1])
        s["boom_gap_sum"] += up * gap
        s["boom_months"] += up
        s["steady_gap_sum"] += steady * gap
        s["steady_months"] += steady
        s["low_months"] += self.conf < TIER["steady"][0]  # Wary or Panic, as the gauge shows it
        s["up_months"] += self.conf >= TIER["buoyant"][0]  # Buoyant or Mania
        s["reckless_months"] += self.lax >= cycle.LAX_CUTS[3]
        s["late_panic_months"] += self.in_panic & (self.m >= self.months * 0.7)  # the last 30 years
        s["distrust_late_months"] += (self.trust < centres.CALM / 4) & (self.m >= DISTRUST_FROM)  # Distrusted, 1866 on
        s["pool_gap_sum"] += self.pool_inv - 1
        s["conf_sum"] += self.conf
        s["lent_sum"] += lent / np.maximum(pm, 1)
        s["debt_sum"] += self.debt
        if self.keep:  # as the log has them: fastsim scales a month's crash by the confidence it started from
            k = self.keep
            self.kept.append(dict(conf=self.conf[:k].copy(), gdp=self.gdp[:k].copy(), pool=pm[:k].copy(), boom=c_boom[:k].copy(), crash=(c_crash * K["CONF_START"] / np.maximum(conf_was, 1))[:k],
                                  foreign=c_foreign[:k].copy(), turmoil=c_turmoil[:k].copy(), business=c_business[:k].copy(), debt=c_debt[:k].copy(),
                                  panic=self.in_panic[:k].copy(), levers=(self.lever[:k] != 0).sum(1) * 1.0, restrain=c_restrain[:k].copy(),
                                  convert=self.did_convert[:k] * 1.0, braw=boom_raw[:k].copy(), wsum=self.w[:k].sum(1),  # the log's braw, wsum and end1-3 (fit.py --boom)
                                  **{f"end{s}": self.n_end_s[s][:k] * 1.0 for s in (1, 2, 3)},
                                  # the rest of the month's confidence, as the log's d_<name> (windows.py's breakdown)
                                  **{f"d_{x}": v[:k].copy() for x, v in dict(drift=c_recover, mood=self.c_mood, growth=c_growth, world=c_world, rough=c_rough,
                                                                             tight=c_tight, limit=c_limit, burst=c_burst, drop=c_drop, rescue=c_rescue,
                                                                             caution=c_caution, warend=self.war_end).items()}))
        if self.m % SNAP == 0:
            self.snap.append((self.conf.copy(), self.in_panic.copy(), lev4.copy(), self.crunch.copy(), self.lax.copy(),
                              self.trust / centres.CALM, self.n_boom.copy(), (self.sentiment_term != 0).sum(1), self.lent_yr.copy()))
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
                      runoff_neg=-runoff[i], recall_neg=-clawed[i], writeoff_neg=-(recall[i] - clawed[i]), lured=self.lured[i], debt=self.debt[i],
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
                      bailout_cost=self.treasury_price(self.crunch ** 2 * K["LEV_BAILOUT_COST"])[i], bailed=bool(self.bailed[i]),
                      stance_cd=int(self.stance_cd[i]), reserves=self.reserves[i], in_default=bool(self.in_default[i]),
                      exchange_trust=self.trust[i] / centres.CALM, charter=int(self.charter[i]),
                      restraining=int((self.lever[i] < 0).sum()), encouraging=int((self.lever[i] > 0).sum()),
                      rescue_now=bool(self.did_rescue[i]), bailout_now=bool(self.did_bailout[i]), stance_now=int(self.did_stance[i]))
            self.hist.append({k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in fr.items()})
        self.m += 1

    def pick_mania(self):
        """The Mania event's option: 0 ride it, 1 the warning, 2 the levy (generate.events, spec_markets.1)."""
        u = self.ai_u[:, 1]
        if self.pol["mania"] is None:  # the AI's ai_chance, by temperament (generate.MANIA_AI)
            K = self.K
            w = np.stack([K["MANIA_AI_" + k] + K[f"MANIA_AI_{k}_{b}"] * (self.temper == t)
                          for k, t, b in (("RIDE", 1, "BOLD"), ("WARN", -1, "CAUTIOUS"), ("LEVY", -1, "CAUTIOUS"))], 1).astype(float)
        else:
            w = np.tile(np.array(self.pol["mania"], float), (self.n, 1))
        cum = np.cumsum(w / w.sum(1, keepdims=True), 1)
        return (u[:, None] > cum).sum(1)

    def grant_charter(self, name):
        """A player order, subject to the technology gate, ten-year lock and replacement cost."""
        kind = CHARTERS[name]
        eligible = (self.charter != kind) & (self.m >= self.charter_until) & self.has("banking") & (self.law_mult > 0)
        if kind == 3:
            eligible &= self.has("stock_exchange")
        self.trust *= np.where(eligible & (self.charter != 0), 1 - centres.CHARTER_COST, 1)
        self.charter[eligible] = kind
        self.charter_until[eligible] = self.m + 12 * centres.CHARTER_LOCK
        return eligible

    def rescue_now(self, rescue, cost=None):
        """spec_rescue for the economies in rescue: paid, the panic cut to the rescue's months, confidence up, Lending
        Standards laxer (cycle.rescued). Returns (confidence moved, Lending Standards jump)."""
        K = self.K
        cost = self.rescue_cost() if cost is None else cost
        self.pay(np.where(rescue, cost, 0))
        was = self.conf.copy()
        self.panic = np.where(rescue, np.minimum(self.panic, self.rescue_months()), self.panic)
        self.conf = np.where(rescue, np.minimum(self.conf + K["RESCUE_CONF"], 100), self.conf)
        self.rescued |= rescue
        self.funded_rescue |= rescue
        j = np.where(rescue, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)
        self.lax += j
        self.stats["rescues"] += rescue
        self.stats["rescue_cost"] += np.where(rescue, cost, 0)
        return self.conf - was, j

    def pledge_month(self):
        """centres._pledge_month for AI economies: a default breaks the pledge (all trust, PLEDGE_BREAK confidence), notice
        counts down, then the AI makes it (banking, National Standing, scaled debt under AI_PLEDGE_DEBT, a rescue's cost in
        reserves, no panic; AI_PLEDGE_CHANCE a month) or gives notice (debt over AI_PLEDGE_LEAVE, or reserves short of the
        pledged cost). Returns the confidence a broken pledge took.
        ponytail: the Broken Pledge's legitimacy hit is left out (one break in all the logged games)."""
        K, n = self.K, self.n
        was = self.conf.copy()
        broke = self.pledge & self.in_default
        self.trust = np.where(broke, 0, self.trust)
        self.conf = np.where(broke, np.maximum(self.conf - centres.PLEDGE_BREAK["conf"], 0), self.conf)
        self.pledge &= ~broke
        leaving = ~broke & (self.pledge_leave > 0)
        self.pledge_leave = np.where(broke, 0, np.where(leaving, self.pledge_leave - 1, self.pledge_leave))
        self.pledge &= ~(leaving & (self.pledge_leave <= 0))
        cost = self.rescue_cost()  # full for the unpledged, PLEDGE_COST's share for the pledged
        can = (self.has("banking") & self.stand_ok() & (self.sdebt <= centres.PLEDGE_DEBT) & ~self.in_panic & ~self.pledge)  # spec_can_pledge
        make = (can & ~self.in_default & (self.sdebt < K["AI_PLEDGE_DEBT"]) & (self.reserves >= cost)
                & (self.rng_pledge.random(n) < K["AI_PLEDGE_CHANCE"] / 100))
        leave = (self.pledge & (self.pledge_leave <= 0) & ((self.sdebt > K["AI_PLEDGE_LEAVE"]) | (self.reserves < cost)))
        self.pledge |= make
        self.pledge_leave = np.where(leave, K["EXCH_PLEDGE_NOTICE"], self.pledge_leave).astype(int)  # K's may be one a economy (batch)
        self.stats["pledge_months"] += self.pledge
        return self.conf - was

    def stand_ok(self):
        """The Exchange's Standing at National or higher (spec_can_pledge): the followed campaign country's (fit.py --history's
        h_stand), its last month's past the campaign.
        ponytail: without that history every economy counts as National (the logs: 70-85% of the top 40)."""
        H = history()
        if self.hist_rows is None or H is None or "stand" not in H:
            return np.ones(self.n, bool)
        m = min(self.m, len(self.hist_rows) - 1)
        return H["stand"][self.hist_rows[m], m] >= 1

    def decide(self):
        """After the pulse: credit policy, Lend to the Banks, Buy Up Bad Loans, then the Mania event's choice."""
        K, P, n = self.K, self.pol, self.n
        is_ai = BOTS[self.bot_name] == "ai"
        lev = self.lev(self.pool_month())
        c_rescue, c_caution, lax_jump = np.zeros(n), np.zeros(n), np.zeros(n)
        self.did_rescue, self.did_bailout, self.did_stance, self.lured = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n), np.zeros(n)
        if is_ai:
            self.fever &= ~(~self.mania | self.in_panic)  # leverage.FEVER_END
            c_caution += self.pledge_month()
        can = self.has("central_banking") & (self.stance_cd <= 0)  # generate.triggers: spec_can_stance_*
        fever = self.fever if is_ai else np.zeros(n, bool)
        to_tight = can & (self.stance != -1) & ((self.conf > P["tight_conf"]) | (lev > P["tight_lev"])) & ~fever
        to_normal_t = can & (self.stance == -1) & (self.conf < P["untight_conf"]) & (lev < P["untight_lev"])
        to_loose = can & (self.stance == 0) & (self.conf < P["loose_conf"]) & (lev < P["loose_lev"]) & ~self.in_panic
        to_normal_l = can & (self.stance == 1) & ((self.conf >= P["unloose_conf"]) | self.in_panic)
        if P.get("timing"):  # the Panic Risk alert's condition (journal.alerts: spec_after_risks < spec_panic_at)
            risky = self.after_risks() < self.panic_at(lev)
            to_tight |= can & (self.stance != -1) & risky
            to_normal_t &= ~risky
        elif not is_ai:  # a player's loosening: "loose_conf" INF means Loose whenever Normal and calm
            to_tight &= self.stance == 0 if P["tight_conf"] < INF or P["tight_lev"] < INF else to_tight
        new = _first([to_tight, to_normal_t, to_loose, to_normal_l], [-1, 0, 1, 0], self.stance)
        if self.desired_credit is not None:
            new = np.where(can, self.desired_credit, self.stance)
        changed = new != self.stance
        self.stance, self.stance_cd = new, np.where(changed, K["STANCE_COOLDOWN"], self.stance_cd)
        self.did_stance = np.where(changed, new + 10, 0)  # +10 so Normal reads as a change
        # Lend to the Banks (spec_rescue): the AI only from money it has, and only with more months left than a rescue takes
        cost = self.rescue_cost()
        can_rescue = self.in_panic & ~self.rescued & self.has("banking")
        if P["afford"]:
            can_rescue &= ~self.in_default & ~self.nearly_broke & (self.sdebt < 0.6) & (self.reserves >= cost) & (self.panic > self.rescue_months())
        rescue = can_rescue & (self.ai_u[:, 2] < P["rescue"])
        if rescue.any():
            c_rescue, j = self.rescue_now(rescue, cost)
            lax_jump += j
            self.did_rescue = rescue
        # Buy Up Bad Loans (leverage.bailout_effect), once per spell of Bad Debts
        bcost = self.treasury_price(self.crunch ** 2 * K["LEV_BAILOUT_COST"])
        can_bail = (self.crunch > 0) & self.has("banking") & ~self.bailed & ~self.in_default & (self.crunch >= P["bailout_from"])
        if P["afford"]:
            can_bail &= ~self.nearly_broke & (self.sdebt < 0.6) & (self.reserves >= bcost)
        bail = can_bail & (self.ai_u[:, 3] < P["bailout"])
        if bail.any():
            self.pay(np.where(bail, bcost, 0))
            self.crunch = np.where(bail, self.crunch * (1 - K["LEV_BAILOUT_CUT"]), self.crunch)
            self.bite = np.where(bail, np.minimum(self.bite, self.crunch), self.bite)
            self.bailed |= bail
            j = np.where(bail, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)
            self.lax += j
            lax_jump += j
            self.stats["bailouts"] += bail
            self.stats["bailout_cost"] += np.where(bail, bcost, 0)
            self.did_bailout = bail
        if is_ai:  # rivals.spec_rv_lure: the AI's Lure Their Capital, its own debt of LURE_DEBT months of pool income x spec_rv_vs
            # ponytail: contests, cooldowns and the AI's looks are one fitted chance (lure_rate) and vs a fitted draw (lure_vs);
            # the target's lost pool income and Bear Raids (fit.py: about 0.1 confidence a country-year) are left out
            r = self.rng_lure
            lure = ~self.in_panic & (lev < rivals.AI_LEV) & (r.random(n) < self.lure_p)
            vs = np.clip(_draw(r, self.I["lure_vs"], n), rivals.VS_LO, rivals.VS_HI)
            self.lured = np.where(lure, rivals.LURE_DEBT * vs * self.pool_month(), 0)
            self.debt += self.lured
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
        """journal.MONTHLY_AI: a Commission of Inquiry when one can sit (AI_INQUIRY_CHANCE a month) and the institution it
        makes when it reports (spec_reform.1's ai_chance, REFORM_AI_*), debt converted in good times (AI_CONVERT_CHANCE), and
        the Bank Act suspended when the state cannot lend to the banks. Relief Works moves neither confidence nor credit, so
        it is left out (ponytail: its treasury cost would lower reserves, and with them rescues and pledges; AI_RELIEF_CHANCE
        is a key for the generator only).
        Returns the confidence each moved (rescue, caution) and the Lending Standards jump."""
        K, J, n = self.K, journal, self.n
        note_free = ~(self.enacted["currency"] | self.enacted["free"])
        choices = {"currency": (note_free, K["REFORM_AI_CURRENCY"] + K["REFORM_AI_TEMPER"] * (self.temper == -1)),
                   "free": (note_free, K["REFORM_AI_FREE"] + K["REFORM_AI_TEMPER"] * (self.temper == 1)),
                   "llr": (self.has("central_banking") & ~self.enacted["llr"], K["REFORM_AI_LLR"]),
                   "company": (self.has("joint_stock_companies") & ~self.enacted["company"], K["REFORM_AI_COMPANY"])}
        was = self.conf.copy()
        due = self.sitting == 0
        if due.any():  # the report: one institution, or shelved (base 5, SHELVE_CONF)
            w = np.stack([np.where(ok, wt, 0) for ok, wt in choices.values()] + [np.broadcast_to(K["REFORM_AI_SHELVE"], n)], 1).astype(float)
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
               & (u[:, 1] < K["AI_INQUIRY_CHANCE"] / 100))
        self.sitting = np.where(sit, J.INQUIRY_MONTHS - 1, self.sitting)
        self.inquired |= sit
        self.calm_m = np.where(sit, 0, self.calm_m)
        conv = ~self.in_panic & (self.conf >= J.CONVERT_FROM) & (self.sdebt >= J.CONVERT_DEBT) & (self.converted <= 0) & (u[:, 2] < K["AI_CONVERT_CHANCE"] / 100)
        self.conf = np.where(conv, np.maximum(self.conf - J.CONVERT_CONF, 0), self.conf)
        self.converted = np.where(conv, J.CONVERT_COOLDOWN_YEARS * 12, np.maximum(self.converted - 1, 0))
        self.did_convert = conv
        caution = self.conf - was
        was = self.conf.copy()
        sus = (self.in_panic & self.enacted["currency"] & ~self.rescued & (self.panic > J.SUSPEND_MONTHS)
               & (self.in_default | ~self.has("banking") | (self.reserves < self.rescue_cost())))
        self.panic = np.where(sus, np.minimum(self.panic, J.SUSPEND_MONTHS), self.panic)
        self.conf = np.where(sus, np.minimum(self.conf + J.SUSPEND_CONF, 100), self.conf)
        self.rescued |= sus
        lax = np.where(sus, np.minimum(K["LAX_RESCUE"], 1 - self.lax), 0)  # cycle.rescued
        self.lax += lax
        self.hazard = np.where(sus, J.HAZARD_YEARS * 12, self.hazard)
        return self.conf - was, caution, lax

    def goods_words(self, h):
        cuts, up, down = word_boundaries()
        raw = 1 + np.searchsorted(cuts, h, side="right")
        held = np.clip(self.word, 1 + np.searchsorted(up, h, side="right"), 1 + np.searchsorted(down, h, side="right"))
        return np.where(self.share > 0, np.where(self.word == 0, raw, held), 0)

    def spare_authority(self):
        base = levers.DEFAULT_TAX_COST * levers.LEVER_TAX_SHARE
        authority = self.auth if self.I["fiscal_profiles"] else self.auth * base
        return authority - (self.lever_cost * (self.lever != 0)).sum(1)

    def player_toggle(self, day, good, action, severity):
        """A dated goods-panel click after the monthly pulse, on a good in this country's traded basket."""
        kind = -1 if action == "restrain" else 1
        selected = (self.goods_ids == good) & (self.share > 0)
        held = self.lever == kind
        free = self.lever_wait == 0
        turn_off = selected & held & (free | (day.toordinal() < self.grace_until))
        fits = ((self.word >= 5) | (self.risk >= levers.RESTRAIN_RISK)) if kind < 0 else (
            (self.word < levers.ENCOURAGE_BELOW) & (self.glut == 0) & (severity < 2))
        turn_on = selected & free & (self.lever == 0) & fits & (self.law_mult[:, None] > 0)
        turn_on &= self.spare_authority()[:, None] >= self.lever_cost
        self.lever[turn_off], self.lever[turn_on] = 0, kind
        self.grace_until[turn_off], self.grace_until[turn_on] = 0, day.toordinal() + levers.GRACE_DAYS
        self.lever_wait[turn_off | turn_on] = levers.WAIT_MONTHS

    def ai_levers(self, lev):
        """levers.ai_block: lift a restraint once its boom has passed, restrain the riskiest boom while confident or lent past
        the safe line, then encourage the most favored Calm good while Wary, each with Authority to spare (self.auth).
        Great Issues and Exchange specialities are outside this model."""
        K, P, n = self.K, self.pol, self.n
        hr = self.h_raw
        # The mod refreshes its Authority modifier after both AI choices.
        spare = self.spare_authority()
        affordable = spare[:, None] >= 2 * self.lever_cost
        lift = (self.lever < 0) & ((self.peak < g.RISING_HYPE) | ((hr < g.HOT_HYPE) & (hr >= g.COOLING_HYPE)))
        self.lever = np.where(lift, 0, self.lever)
        risk = np.where((self.lever == 0) & (self.share > 0) & affordable, self.risk, 0)
        # The generated else_if chains walk GOODS in order, including ties between Calm goods at 1.0.
        best = np.where(risk == risk.max(1, keepdims=True), self.goods_ids, len(g.GOODS)).argmin(1)
        go = ((self.conf >= K["AI_CONF"]) | (lev >= K["LEV_SAFE"])) & (risk[np.arange(n), best] >= K["AI_RISK"])
        self.lever[go, best[go]] = -1
        self.stats["restrains"] += go
        stop = (self.conf >= P["unloose_conf"]) | self.in_panic | self.in_default | (self.net_income < 0)
        self.lever = np.where(stop[:, None] & (self.lever > 0), 0, self.lever)
        calm = (self.lever == 0) & (self.word == levers.CALM_WORD)
        funds = np.reshape(K["AI_FUNDS"], (-1, 1))  # one, or one a economy
        calm &= affordable & (self.net_income[:, None] > self.subsidy * funds)
        want = ~stop & (self.conf < P["loose_conf"]) & ~(self.lever > 0).any(1) & calm.any(1)
        favored = np.where(calm, self.h, -1)
        pick = np.where(favored == favored.max(1, keepdims=True), self.goods_ids, len(g.GOODS)).argmin(1)
        self.lever[want, pick[want]] = 1

    def run(self):
        for _ in range(self.months):
            self.step()
        self.frz_end(self.frz_run > 0)  # a spell running at the end counts as it stands
        return self

    def frz_end(self, done):
        i = np.nonzero(done & (self.frz_run > 0))[0]
        np.add.at(self.stats["frz_hist"], (i, np.minimum(self.frz_run[i], FRZ_BINS - 1)), 1)


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
    "trust_top_pct": ("Months with the Exchange Respected or Trusted", "%"),
    "panic_output_loss": ("Output lost over one panic, % of a year's GDP", "%"), "panic_invest_pct": ("Investment in a panic against calm months", "%"),
    "boom_output_pct": ("GDP in Buoyant and Mania months against Steady", "%"),
    "low_pct": ("Months Wary or in Panic", "%"), "up_pct": ("Months Buoyant or in Mania", "%"),
    "reckless_pct": ("Months with Reckless Lending Standards", "%"), "late_panic_pct": ("Months in panic, last 30 years", "%"),
    "rescue_share": ("Panics rescued", "%"),
    "frozen_spell_p90": ("Lending frozen, longest spells (90th percentile)", "months"),
    "distrust_late_pct": ("Months with the Exchange Distrusted, 1866 on", "%"),
}
DISTRUST_FROM = 30 * 12  # months from 1836 to 1866
FRZ_BINS = 241  # spell lengths 0 to 240 months; longer ones count as 240


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
        "trust_top_pct": s["trust_top_months"] / T * 100,
        "low_pct": s["low_months"] / T * 100, "up_pct": s["up_months"] / T * 100, "reckless_pct": s["reckless_months"] / T * 100,
        "late_panic_pct": s["late_panic_months"] / (T - int(T * 0.7)) * 100,
        "distrust_late_pct": s["distrust_late_months"] / max(T - DISTRUST_FROM, 1) * 100,
    }
    out = {k: dict(zip(("p10", "p50", "p90"), map(float, np.percentile(v, [10, 50, 90])))) | {"mean": float(np.mean(v))} for k, v in per.items()}
    # pooled ratios: the panic length and manias ending in a panic over every economy at once
    out["panic_length"] = {"mean": float(s["panic_len_sum"].sum() / max(s["panics"].sum(), 1))}
    out["mania_to_panic_pct"] = {"mean": float(s["mania_panics"].sum() / max(s["manias"].sum(), 1) * 100)}
    out["frozen_pct"] = {"mean": float(s["frozen"].sum() / max(s["panics"].sum(), 1) * 100)}
    h = s["frz_hist"].sum(0)  # pooled over the economies: 90% of frozen spells are this long or shorter
    out["frozen_spell_p90"] = {"mean": float(np.searchsorted(np.cumsum(h), 0.9 * h.sum()) if h.sum() else 0.0), "spells": int(h.sum())}
    out["bad_spell"] = {"mean": float(s["crunch_months"].sum() / max(s["crunch_spells"].sum(), 1))}
    out["rescue_share"] = {"mean": float(s["rescues"].sum() / max(s["panics"].sum(), 1) * 100)}
    out["panic_output_loss"] = {"mean": float(s["panic_loss_sum"].sum() / max(s["panics"].sum(), 1) / 12 * 100)}
    out["panic_invest_pct"] = {"mean": float((s["inv_panic_sum"].sum() / max(s["panic_months"].sum(), 1))
                                             / (s["inv_calm_sum"].sum() / max(T * len(s["panics"]) - s["panic_months"].sum(), 1)) * 100 - 100)}
    out["boom_output_pct"] = {"mean": float((s["boom_gap_sum"].sum() / max(s["boom_months"].sum(), 1)
                                             - s["steady_gap_sum"].sum() / max(s["steady_months"].sum(), 1)) * 100)}
    out["_hist"] = np.histogram(per["panics_per_century"], bins=np.arange(0, 16))[0].tolist()  # panics a century, 0 to 15
    return out


SNAP = 6  # months between the snapshots the charts draw


def bands(e):
    """The charts over the run, a point every SNAP months: confidence, leverage (10/50/90% across the economies),
    Bad Debts (50/90%), Lending Standards (50%), and the share of economies in a panic."""
    c, p, lev, bad, lax, trust, booms, terms, lent = (np.array(a) for a in zip(*e.snap))
    q = lambda a, *k: [np.percentile(a, x, 1).round(2).tolist() for x in k]
    return {"every": SNAP, "conf": q(c, 10, 50, 90), "lev": q(lev, 10, 50, 90), "bad": q(bad, 50, 90), "lax": q(lax, 50)[0],
            "panic": p.mean(1).round(3).tolist(),
            # the middle 80% (10/50/90%) of the rest of the loop, for the charts
            "bad80": q(bad, 10, 50, 90), "lax80": q(lax, 10, 50, 90), "trust": q(trust, 10, 50, 90),
            "booms": q(booms, 10, 50, 90), "terms": q(terms, 10, 50, 90), "lent": q(lent, 10, 50, 90)}


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
    # the AI's pledge and journal rules carry the engine's numbers (centres._pledge_month, PLEDGE_RESCUE; journal.MONTHLY_AI, spec_reform.1)
    pm = centres._pledge_month("")
    assert f"scaled_debt < {K['AI_PLEDGE_DEBT']:g}" in pm and f"scaled_debt > {K['AI_PLEDGE_LEAVE']:g}" in pm, pm
    assert ("chance = " in pm) == (K["AI_PLEDGE_CHANCE"] < 100) and "gold_reserves >= spec_rescue_cost" in pm
    assert f"value = {K['EXCH_PLEDGE_COST']:g}" in centres._pledge_values() and f"multiply = {K['EXCH_PLEDGE_PANIC']:g}" in centres._panic_cut()
    assert "multiply = spec_pledge_cost" in _value(sv, "spec_rescue_share") and "spec_rescue = yes" in centres.PLEDGE_RESCUE
    for key, act in (("AI_INQUIRY_CHANCE", "inquiry"), ("AI_CONVERT_CHANCE", "convert"), ("AI_RELIEF_CHANCE", "relief")):
        assert f"chance = {K[key]:g}\n\t\t\t\t\t\tspec_do_{act} = yes" in journal.MONTHLY_AI, key
    ev = journal.events()
    for key in ("REFORM_AI_CURRENCY", "REFORM_AI_FREE", "REFORM_AI_LLR", "REFORM_AI_COMPANY", "REFORM_AI_SHELVE"):
        assert f"base = {K[key]:g}\n" in ev, key
    assert ev.count(f"add = {K['REFORM_AI_TEMPER']}\n") >= 2
    monthly = g.monthly(False)
    for p in (f"var:spec_conf > {K['CREDIT_FROM']}", f"var:spec_conf >= {K['MANIA']}", f"var:spec_conf < {K['BURST_BELOW']}",
              f"var:spec_conf >= {K['PANIC_ENDS_AT']}", f"spec_panic_run >= {K['PANIC_MIN_MONTHS']}", f"multiply = {K['MOOD_KEEP']:g}",
              f"var:spec_c_boom > {K['CONF_BOOM_MAX']}", f"value = -{K['CONF_CRASH_MAX']}", f"add = {K['LEV_CRUNCH_RAMP']}"):
        assert p in monthly, p
    assert f"spec_lax add = {{ value = 1 subtract = var:spec_lax multiply = {cycle.LAX_SCALE / (12 * K['LAX_QUIET_YEARS']):.5f} }}" in cycle.monthly()
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
    if r.hist_rows is not None:  # follow_history: past the campaign each keeps its last country's last laws
        H = history()
        last = H["econ"][r.hist_rows[-1], -1]
        assert all(c == 0 or r.econ[i] == g.LOG_ECON[c - 1] for i, c in enumerate(last)), "laws left the campaign's"
        lf = 0.3
    assert 0.2 < lf < 0.6 and all(at[at >= 0].min(initial=10 ** 6) >= 75 * 12 for k, at, d in r.drift if k == "money" and (d == "fiat_money").all()), lf
    note = lambda i: journal.REFORMS["currency"]["panic_len"] if r.enacted["currency"][i] else 1  # the Currency School, the AI's Commissions
    assert all(r.law_mult[i] == LAWS[r.econ[i]][0] and abs(r.reform["panic_len"][i] - MONEY.get(r.money[i], {}).get("panic_len", 1) * note(i)) < 1e-9 for i in range(r.n))
    # 4c. the world beyond: trust stays 0 to CALM, the Long Depression comes after EARLIEST_YEAR and reaches at least its share
    assert ((r.trust >= 0) & (r.trust <= centres.CALM)).all() and r.flight_p.max() > 0
    assert np.array_equal(r.worlds.origins.sum(1), r.worlds.depressions)
    # 4d. the AI restrains booms and its Commissions make institutions
    assert r.bot_name == "ai" and r.stats["restrains"].sum() > 0 and r.stats["reforms"].sum() > 0, (r.stats["restrains"].sum(), r.stats["reforms"].sum())
    # 4e. the AI pledges, and a pledged panic is rescued as it starts (each a rescue counted once)
    assert r.stats["pledge_months"].sum() > 0 and 0 < r.stats["pledge_rescues"].sum() <= r.stats["rescues"].sum(), (r.stats["pledge_rescues"].sum(), r.stats["rescues"].sum())
    # 5. the Inspector's rows add up to the figure they explain, every month of a traced run
    for bot in ("passive", "reckless", "ai"):
        for f in run({}, defaults(), bot, 1, 3, trace=True).hist:
            for total, rows in (("conf", [r[1] for r in CALC["conf"][:-1]]), ("debt", ["debt_was", "runoff_neg", "lent", "recall_neg", "writeoff_neg", "lured"]),
                                ("pool", ["pool_last", "pool_month", "spend_neg", "repaid_neg", "lent", "clawed_neg"])):
                got = sum(f[r] for r in rows)
                assert abs(got - f[total]) <= 1e-3 * (1 + abs(f[total])) + 0.01, (bot, f["m"], total, got, f[total])
    assert log_fragment().count("=[") == len(REPLAY_FIELDS) and parse_log("SPEC conf=55.2 tag=GBR")["conf"] == 55.2
    print("engine ok:", len(TUNABLE), "tunable constants match the generators")
