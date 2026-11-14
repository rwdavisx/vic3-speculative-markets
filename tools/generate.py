"""Generate the Speculative Markets mod script.

Hype: every month each country records, per good, a fast and a slow moving average of how far the price in
its market sits above or below base price. Hype is how far the fast average runs ahead of the slow one,
scaled by the economic system law and the credit stance. Each building's ai_value is multiplied by the hype
of the goods it sells, so investors chase rising prices and back away from falling ones. This reaches AI
governments too: their construction follows the same market signals as private investors.

Confidence (0 to 100) rises with booming goods and drops when a good that boomed turns down, weighted by how
much of the market's trade each good is, and with war, default and revolution. High confidence pours credit
into the investment pool; a panic calls part of it back. Below the panic line a panic halves private
construction for months. Banking unlocks the bank rescue, Central Banking the credit stance and a cheaper rescue;
other financial techs make booms larger, losses smaller or larger, and recovery faster (FIN_*, MACRO).
The player sees it all in the Finance window (sidebar) and a journal entry.

Usage: py -3 tools/generate.py [--log]
--log adds a monthly debug.log line per country for tools/analyze_*.py.
Debug builds require SPEC_MOD_OUT set to a separate output directory; mod/ is release-only.
"""
import functools
import os
import re
import sys
import time
from pathlib import Path

import companies
import concepts
import credit_ai
import depression
import diplomacy
import economy
from economy import GROWTH_K, GROWTH_MAX, GROWTH_NORMAL, DEFAULT_FROM, DEFAULT_COST, BROKE_COST, BROKE_WEEKS  # into k, for the loc
from diplomacy import PLAY_TURMOIL, FLIGHT_GAIN, FLIGHT_FROM, WAR_COST, WAR_BASE, WAR_WORST, WAR_BEST, WAR_ALL_MIN, WAR_ALL_MAX, WAR_END, SOURCES  # into k, for the loc
import goods_panel
import i18n
import icons
import journal
import levers
import leverage
import market_tab
import interest_board  # after market_tab, which it imports from
import cycle
import centres
import exposure
import finance_icon
import charts
import market_visual
import movements
import notify
import probe
import stories
import tech_ties
import tuning
import vanilla_ties

GAME =Path("G:/SteamLibrary/steamapps/common/Victoria 3/game")
HAND_MADE = set()  # files under the built folders that no script writes: none since the unused map mode's heat_glow.dds went
MOD = Path(os.environ.get("SPEC_MOD_OUT") or Path(__file__).resolve().parent.parent / "mod")  # SPEC_MOD_OUT: build elsewhere while the game runs
WRITTEN = set()

FAST = tuning.get("FAST", 0.15)  # monthly smoothing of the two price averages; 0.3 let interest jitter month to month
SLOW = 0.05
# a good changes interest word only once its hype is past the cut by this share of the cut (for cuts below 1, the
# same on the 1/x side), else it keeps last month's word, so a good sitting on a cut does not flip every month
WORD_BUFFER = tuning.get("WORD_BUFFER", 0.04)
HYPE_GAIN = tuning.get("HYPE_GAIN", 60)              # trend = gain * (fast - slow); 6 with a cap of 3 had no measurable effect
# hype = 1 + trend when rising, 1 / (1 - trend) when falling: a fall reads as far below 1 as the same rise reads
# above it (x2 at +1, x0.5 at -1), so the falling words need as large a move as the rising ones
HYPE_MAX = tuning.get("HYPE_MAX", 20)
HYPE_MIN = 1 / HYPE_MAX
# ponytail: hype multiplies ai_value, only the base term of the AI's building score (the profit and output
# terms are added to it, then a random factor), so x20 here moved building about +30%, not x20. Show players
# words and the price trend, never hype as a percentage. The cap binds in under 1% of country-good months.

CONF_START = tuning.get("CONF_START", 55)             # confidence drifts back here
CONF_RECOVER = tuning.get("CONF_RECOVER", 0.04)        # share of the gap to CONF_START closed each month
# Market Mood: each month mood = mood x MOOD_KEEP + a random draw within +-MOOD_SHOCK, added to confidence. A lasting
# random push gives swings of a year or more; with 0.05 drift and no mood the 40 year run sat at 45 to 66 (deciles).
# ponytail: first values from replaying data/run_v06_1836_40y.txt (drift 0.035, mood 0.8 and 1.5): deciles about
# 36 to 76, mania 6 to 7% of months, panic 1.5%, one per 33 country years. Calibrate from a fresh --log run.
MOOD_SHOCK = tuning.get("MOOD_SHOCK", 0.75)   # 1.5 until 1.0: mood was a third of all movement and the top cause of a quarter of panics
MOOD_SHALLOW = tuning.get("MOOD_SHALLOW", 0.5)  # share of the mood a country with no Financial Districts feels (spec_depth at its least)
PANIC_SHALLOW = tuning.get("PANIC_SHALLOW", 5)  # and how far under PANIC its panic line sits: under 3k GDP they panicked 7 times as often as the largest
# C2 a mania feeds itself: interest in a rising price, by confidence band (falling prices are untouched)
BAND_GAIN = tuning.get("BAND_GAIN", {"wary": 0.8, "buoyant": 1.15, "mania": 1.3})
MOOD_KEEP = tuning.get("MOOD_KEEP", 0.75)
HOT_HYPE = tuning.get("HOT_HYPE", 3)                # a good this hyped is booming
RISING_HYPE = tuning.get("RISING_HYPE", 2)             # the goods board's Keen word starts here
COOLING_HYPE = 1 / RISING_HYPE  # and Doubtful below this, the mirror of Keen; Calm sits between
CONF_PER_HOT = tuning.get("CONF_PER_HOT", 0.85)        # confidence a month per booming good at full weight, before research
# financial research: booms grow with the market's machinery, so they are small in 1836 and large by the 1880s, as
# the century's manias were (railways 1845, 1857, the founders' boom of 1873, Argentina 1890, mining around 1900)
FIN_BOOM_BASE = tuning.get("FIN_BOOM_BASE", 0.7)        # booms' size without the techs below
FIN_BOOM = {"stock_exchange": 0.25, "investment_banks": 0.3}   # added to it by each (0.15 each left Mania at 1.5 to 3.5% of months after 1846)
FIN_RISK = {"mutual_funds": 0.85}   # boom-ending losses x this: funds spread the risk
FIN_LEVERAGE = ("modern_financial_instruments", 1.1)   # booms and boom-ending losses both x this
MACRO = ("macroeconomics", 1.5)     # the drift back to CONF_START and a country's own Long Depression recovery, x this
# capital flight into a calm Great Power (diplomacy.FLIGHT_GAIN) x this base, plus each tech's share: money moves
# with trade, and moves fastest under common exchange standards. Most countries start with International Trade, so
# the tuned figure (1, then 2 with the standards) holds for them
FLIGHT_BASE = 0.5
FLIGHT_TECHS = {"international_trade": 0.5, "international_exchange_standards": 1}
# foreign panic losses x this without a standard currency: investors trust no paper they cannot price. Most
# countries start with Currency Standards, so the tuned contagion holds for them
UNSTANDARD = ("currency_standards", 1.25)
# a boom's bubble: with a Stock Exchange, each month at HEAT_FROM or more adds confidence - 70 to its heat, and when
# confidence falls below BURST_BELOW the bubble bursts, BURST_PER_HEAT x the heat, at most BURST_MAX. Bursting only
# from a Mania (80, below 65) left the 40 largest economies, which boom in the 60s and 70s, at 2.2 panics per 100
# country years against history's 4 (stats.HISTORY). From 72 at 0.25 (tune5, to 1865) overshot: 6.1 panics, 45% of
# manias ending in one; replaying it (scaled by its own logged/replayed ratio) 76, 0.15, 40 and booms x0.8 give
# about 4 panics; with Tight still a cap at 75 they came out at 1.8 (tune6), and with Tight a pull at 2.1 (tune7),
# Mania 2.4%, 17% of manias ending in a panic. Halfway back towards tune5: 74, 0.2 and booms 0.72, since rounded to 75 and 0.7
HEAT_FROM, BURST_BELOW = tuning.get("HEAT_FROM", 75), tuning.get("BURST_BELOW", 60)
RESTRAIN_DEFLATE = tuning.get("RESTRAIN_DEFLATE", 0.9)  # a restrained boom's peak keeps this much of its excess a month (else 0.97)
# the bubble kept each month confidence sits between BURST_BELOW and spec_heat_from. 0.9 played 2.5 panics, 12% of manias ending
# in one; tune8 played no cooling at 3.3 to 4.6 and 21 to 31%. See FINDINGS for what fastsim gives at 0.98. Mania and debt don't move
HEAT_COOL = tuning.get("HEAT_COOL", 0.98)
BURST_PER_HEAT = tuning.get("BURST_PER_HEAT", 0.2)
BURST_MAX = tuning.get("BURST_MAX", 40)
# the Market Volatility game rule: Historical uses the values above; Heightened those of tune5 (bubbles from 72 at
# 0.25 x heat, booms x1.25), which gave the 40 largest economies 6.1 panics per 100 country years to history's 4
VOLATILITY = {"historical": {"heat": HEAT_FROM, "per": BURST_PER_HEAT, "max": BURST_MAX, "boom": 1},
              "heightened": {"heat": 70, "per": 0.25, "max": 45, "boom": 1.1}}
CONF_BOOM_MAX = 3
PEAK_FOR_CRASH = tuning.get("PEAK_FOR_CRASH", 6)          # a good that peaked this high and falls below CRASH_BELOW has crashed
CRASH_BELOW = round(1 / PEAK_FOR_CRASH, 3)  # Fleeing, the mirror of Feverish
CONF_PER_CRASH_HYPE = tuning.get("CONF_PER_CRASH_HYPE", 6) # confidence lost per point of the crashed good's peak above 1, at full weight
# every boom ends, more gently the lower it peaked: severity (var:spec_sev_<g>), the peak it needs, the interest it
# ends below, confidence lost per point of peak above 1 at full weight, months the good then stays in a glut
UNWINDS = [(3, PEAK_FOR_CRASH, CRASH_BELOW, CONF_PER_CRASH_HYPE, 12),   # Collapse: Feverish to Fleeing
           (2, HOT_HYPE, COOLING_HYPE, tuning.get("BUST_PER_HYPE", 2.5), 6),   # Bust: Eager to Doubtful
           (1, RISING_HYPE, COOLING_HYPE, tuning.get("CORRECTION_PER_HYPE", 1.25), 3)]   # Correction: Keen to Doubtful
# ponytail: replaying data/cycle_1856_v03_contagion.txt with Busts and Corrections at 1.6 and 1.9 times the Collapse
# rate (their ratio in loop_x20_1856.txt) put panics up about a third at 2.5 a point; 2.2 brings them back level.
# Rerun the replay on a fresh --log run if the rates differ.
# ponytail: the symmetric words made every unwind need a deeper fall. Replaying loop_control_1856.txt (gain 6, so the
# trend is visible down to -7.5) at gain 60: Collapses -57%, Busts -22%, Corrections -42%, Busts and Corrections
# now about 3.9 times the Collapse rate. Panics will be rarer; recalibrate from a fresh --log run.
# ponytail: 2026-10-31 full runs (FINDINGS.md, Tuning): at 2.05, 1 and 0.5 with booms 0.5 a month, the 12 largest economies
# panicked 3 times in two 70 year games and a Mania ended in a panic 1% of the time. Replaying the logged pushes, all
# three unwinds 2.5 times as costly, booms 1.3 times and mood 1.5 gave large economies about 1.4 panics per 100 years
GLUT_HYPE = 0.4             # a glut sets interest to this, Doubtful: the overbuilt industry waits out its stock
GLUT_MONTHS = {sev: months for sev, *_, months in UNWINDS}  # for the loc
CONF_CRASH_MAX = tuning.get("CONF_CRASH_MAX", 40)         # most a month of crashes can take, after scaling by confidence and depth
EXPOSURE_FULL = 0.03        # a good with this share of the market's trade counts fully toward confidence
TOAST_SHARE = 0.01          # boom-end and Feverish toasts only for goods with this share of the market's trade (measured: 3 to 6 endings a year without it)
# tight credit pulls confidence down by this share of its height above TIGHT_FROM each month (at 85, -2.5). It was a cap
# at 75: the AI tightening at the Mania line then ended the largest economies' manias within a month (tune6: median
# 1 month, against 3 elsewhere), so they never built bubbles and panicked half as often as history
TIGHT_PULL, TIGHT_FROM = tuning.get("TIGHT_PULL", 0.1), 60
# PANIC 25 (was 20): at 20 the 40 largest panicked 3.2 times per 100 country years in three worlds, under the target of
# about 4, and the 10 largest hardly ever; 25 with CONTAGION 20 gave 3.7 to 5.7 (tune9, tune11)
MANIA, MANIA_RESET, PANIC = tuning.get("MANIA", 80), 65, tuning.get("PANIC", 25)
PANIC_NEAR = PANIC + 5                                 # a player is warned when confidence first falls below this
WARY = tuning.get("WARY", 35)                   # AI loosens credit below this (40 had it Loose 43% of the time, feeding panics)
# investment by Capitalists, Aristocrats and Shopkeepers in each confidence band (market_tab.TIERS); Steady has none
BAND_INVEST = {"panic": -0.2, "wary": -0.1, "steady": 0, "buoyant": 0.1, "mania": 0.2}
# the loan interest rate: dearer in fear, cheaper as confidence climbs. Steady was -10% with nothing above it, so loans got
# dearer in a boom, and with the Exchange's and the journal's cuts reached about -45% on top of vanilla's -50% for Great Powers
BAND_RATE = {"panic": 0.2, "wary": 0.1, "steady": -0.04, "buoyant": -0.07, "mania": -0.1}
BAND_TRADE = {"panic": -0.1, "wary": -0.05, "buoyant": 0.05, "mania": 0.1}  # trade volume: merchants ship more in a boom
PANIC_DAYS = tuning.get("PANIC_DAYS", 195)  # 6.5 months, rounded up by law: 4 to 8 months, 7 at x1. 180 cuts a month at x0.8 and x1, 210 adds one at x0.6 and x1.2
PANIC_ENDS_AT = tuning.get("PANIC_ENDS_AT", 40)      # a panic ends early once confidence is back here (out of Wary), PANIC_DAYS at the latest
PANIC_MIN_MONTHS = 2       # but never sooner than this
PANIC_COOLDOWN = 12         # months after a panic ends before another can start
# 55 (was 60), where confidence rests: at 60 banks lent only in booms, 35 to 37% of months, and the AI held a median 0.5
# months of debt; at 55 about double, past the safe line twice as often (tune12)
CREDIT_FROM = tuning.get("CREDIT_FROM", 55)            # credit flows above this confidence
# ponytail: credit was 0.05% of GDP a month, about 1% of the investment pool's income in a 1836-1842 run (runs/
# 20261103_005410_credit_sev): flavour only. Now sized on the pool: at Mania (80) banks add about 15% of a month's
# pool income, a long boom builds up about 5 months of it owed, and a panic recalls half of that at once
VERSION = "1.0.3"
CREDIT_SHARE = tuning.get("CREDIT_SHARE", 1.5)         # monthly credit at full confidence, as a share of a month's pool income
CREDIT_FLOW_MAX = tuning.get("CREDIT_FLOW_MAX", 0.4)       # confidence's part of a month's credit is at most this share of a month's pool income
CREDIT_CEILING = tuning.get("CREDIT_CEILING", 0.6)        # then times the lending rate (stance, laws, techs...), and never more than this share
CREDIT_CAP_MONTHS = 12      # banks stop lending once outstanding credit reaches this many months of pool income
WEEKS_PER_MONTH = 4.3       # investment_pool_gross_income is weekly
CREDIT_RUNOFF = tuning.get("CREDIT_RUNOFF", 0.02)        # share of outstanding credit repaid each month: loans of about four years (was 0.03, tune12)
CLAWBACK = tuning.get("CLAWBACK", 0.5)              # share of outstanding credit a panic pulls back out of the investment pool
RESCUE_COST = 0.04          # share of GDP, with Central Banking (was 0.02: with the discounts it fell to 0.4%)
RESCUE_FLOOR = 0.015        # the share after every discount (reform, Lending Standards, pledge) never falls below this
# a panic crashes the economy: every building's throughput, the taxes collected, and relief for the jobless paid from
# the treasury each week (a share of a year's GDP) until it ends; a rescue halves the first two and ends it sooner
PANIC_THROUGHPUT = tuning.get("PANIC_THROUGHPUT", -0.1)
PANIC_TAX = tuning.get("PANIC_TAX", -0.15)
PANIC_RELIEF = tuning.get("PANIC_RELIEF", 0.04)
RESCUE_MONTHS = 2
# Banking alone: private banks club together, dearer and slower
RESCUE_COST_PRIVATE, RESCUE_MONTHS_PRIVATE = 0.06, 6
# the share is for a panic with RESCUE_REF_MONTHS left, scaled by the months it actually has left within RESCUE_SCALE:
# a flat cost made an early rescue of a long panic as cheap as a late one (2026-10-31 review). Never under x1, or a
# last-month rescue was half price
RESCUE_REF_MONTHS, RESCUE_SCALE = 6, (1, 2)
RESCUE_CONF = 20
MANIA_CAUTION = 10          # confidence the mania event's warning takes off
MANIA_TAX, MANIA_TAX_CONF = 0.0025, 5   # the mania event's levy: share of GDP raised, confidence lost
# the events' timed interest group modifiers: key, vanilla timed modifier icon, approval, name
EVENT_MODIFIERS = [
    ("spec_boom_riding", "modifier_coins_positive", 2, "Riding the Boom"),
    ("spec_boom_warning", "modifier_documents_negative", -1, "Unwelcome Warning"),
    ("spec_prudent_counsel", "modifier_lightbulb_positive", 2, "Prudent Counsel"),
    ("spec_speculation_levy", "modifier_coins_negative", -2, "Speculation Levy"),
    ("spec_market_left_alone", "modifier_flag_positive", 2, "Market Left Alone"),
    ("spec_bank_bailout", "modifier_coins_negative", -2, "Bank Rescue"),
    ("spec_blamed_for_panic", "modifier_fist_negative", -2, "Blamed for the Panic"),
    ("spec_speculators_blamed", "modifier_fist_positive", 2, "Speculators Blamed"),
]
STANCE_COOLDOWN = 6         # months before the credit stance can change again
CONTAGION = tuning.get("CONTAGION", 20)              # confidence a linked country loses when a panic starts, before weighting
# how close each tie is: the share of CONTAGION a linked country takes, before scaling by the two GDPs
LINKS = {"market": 1, "subject": 0.8, "investment": 0.6, "trade": 0.4, "owned": 0.9}
# ownership tie: from OWNED_FROM of a country's GDP owned by the panicking country, growing to LINKS["owned"] at OWNED_FULL
OWNED_FROM, OWNED_FULL = tuning.get("OWNED_FROM", 0.1), tuning.get("OWNED_FULL", 0.3)
TRADE_RELIANCE = 0.2        # a market relying this much on trade with the panicking market is linked
# how far a panic reaches, by the panicking country's rank (vanilla rank_value: 7 Great Power, 6 Major, 5 unrecognized
# Major): the 1866 to 1906 run without it had 1 in 5 country months take a full hit, the British market's members
# panicking as often as the cooldown let them (30 panics per 100 country years)
REACH = tuning.get("REACH", {7: 1, 6: 0.5, 5: 0.5})
REACH_MINOR = tuning.get("REACH_MINOR", 0.15)
# a panic that starts within this many days of a hit of CAUGHT_FROM or more was caught, not home grown: it passes nothing on
CAUGHT_DAYS, CAUGHT_FROM = 90, 3

# economic system law -> how strongly hype moves investors and how long panics last
LAWS = [("laissez_faire", 1.5, 1.2), ("interventionism", 0.7, 0.7), ("extraction_economy", 1, 0.8),
        ("agrarianism", 0.5, 0.6), ("traditionalism", 0.5, 0.6), ("industry_banned", 0.3, 0.6),
        ("command_economy", 0, 0), ("cooperative_ownership", 0, 0)]
CREDIT_TECHS = ["stock_exchange", "investment_banks", "mutual_funds", "modern_financial_instruments"]  # each adds half the base credit
STANCES = [("tight", -1), ("normal", 0), ("loose", 1)]

# building -> the good its investors watch
SELLS = {
    "01_industry": {
        "food_industry": "groceries", "textile_mill": "clothes", "furniture_manufactory": "furniture",
        "glassworks": "glass", "tooling_workshop": "tools", "paper_mill": "paper", "chemical_plant": "fertilizer",
        "explosives_factory": "explosives", "steel_mill": "steel", "motor_industry": "engines",
        "shipyard": "clippers", "automotive_industry": "automobiles", "electrics_industry": "telephones",
        "arms_industry": "small_arms", "artillery_foundry": "artillery", "munition_plant": "ammunition",
        "synthetics_plant": "dye",
    },
    "02_agro": {
        "rye_farm": "grain", "wheat_farm": "grain", "rice_farm": "grain", "maize_farm": "grain",
        "millet_farm": "grain", "livestock_ranch": "meat", "vineyard": "wine",
    },
    "03_mines": {"coal_mine": "coal", "copper_mine": "copper", "iron_mine": "iron", "lead_mine": "lead", "sulfur_mine": "sulfur"},
    "04_plantations": {
        "coffee_plantation": "coffee", "cotton_plantation": "fabric", "dye_plantation": "dye",
        "opium_plantation": "opium", "tea_plantation": "tea", "tobacco_plantation": "tobacco",
        "sugar_plantation": "sugar", "banana_plantation": "fruit", "silk_plantation": "silk",
    },
    "09_misc_resource": {
        "logging_camp": "wood", "rubber_plantation": "rubber", "fishing_wharf": "fish", "oil_rig": "oil",
        "whaling_station": "oil",
    },
    # power plants: electricity's price swings like any other's. Not gold: its price is fixed, so it could never boom
    # ponytail: electricity is a local good, priced by state; its market figures are taken to be the market's average
    "06_urban_center": {"art_academy": "fine_art", "power_plant": "electricity"},
    "11_private_infrastructure": {"port": "merchant_marine"},
}
# goods a building's later production methods switch to, and the tech unlocking them (None: open from the start): once
# researched, investors watch the average of the base good and these
# ponytail: hand list of output switches; a building counts these goods whether or not it has switched to them
UPGRADES = {"shipyard": [("steamers", "gantry_cranes")], "electrics_industry": [("radios", "radio")],
            "automotive_industry": [("aeroplanes", "military_aviation"), ("tanks", "mobile_armor")],
            "food_industry": [("liquor", "distillation")], "logging_camp": [("hardwood", None)],
            "textile_mill": [("luxury_clothes", None)], "furniture_manufactory": [("luxury_furniture", None)],
            "glassworks": [("porcelain", None)], "synthetics_plant": [("silk", "art_silk")],
            "whaling_station": [("meat", None)]}
cycle.setup(GAME, SELLS, UPGRADES)
GOODS = sorted({g for m in SELLS.values() for g in m.values()} | {g for u in UPGRADES.values() for g, _ in u})
BUILDINGS = [b for m in SELLS.values() for b in m]


def block_end(s, open_at):
    """Index of the brace closing the one at open_at, skipping comments and strings."""
    depth, i = 0, open_at
    while i < len(s):
        ch = s[i]
        if ch == "#":
            i = s.find("\n", i)
            if i < 0:
                break
        elif ch == '"':
            i += 1
            while i < len(s):
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == '"':
                    break
                i += 1
            if i >= len(s):
                raise ValueError("unterminated string")
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced braces")


def vanilla_block(path, key):
    s = (GAME / path).read_text(encoding="utf-8-sig")
    start = s.index(f"\n{key} = {{") + 1
    return s[start:block_end(s, s.index("{", start))]


@functools.cache
def categories():
    """Each good's vanilla category (staple, industrial, luxury or military), for the goods board's filters."""
    return {g: re.search(r"\bcategory = (\w+)", vanilla_block("common/goods/00_goods.txt", g)).group(1) for g in GOODS}


def law_alloc():
    """Each law's private construction allocation: a panic takes away half of it."""
    out = {}
    for law, *_ in LAWS:
        m = re.search(r"country_private_construction_allocation_mult = ([\d.]+)",
                      vanilla_block("common/laws/01_economic_system.txt", f"law_{law}"))
        out[law] = float(m.group(1)) if m else 0
    return out


def goods_cost():
    return {g: float(re.search(r"\bcost = ([\d.]+)", vanilla_block("common/goods/00_goods.txt", g)).group(1))
            for g in GOODS}


def goods_tax_cost():
    """Vanilla Authority cost of a consumption tax on each good that sets one (levers.py prices interventions by it)."""
    found = {g: re.search(r"consumption_tax_cost = ([\d.]+)", vanilla_block("common/goods/00_goods.txt", g)) for g in GOODS}
    return {g: float(m.group(1)) for g, m in found.items() if m}


def watched(name, good):
    return f"spec_bhype_{name}" if name in UPGRADES else f"spec_hype_{good}"


def hype_ops(var):
    # no law check: leaving the market economy clears the hype variables (spec_shut_down, state_vars)
    return (f"\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\towner ?= {{ has_variable = {var} }}\n\t\t\t}}\n"
            f"\t\t\tmultiply = owner.var:{var}\n\t\t}}\n")


def building_inject(s, name, good):
    """the hype ops on top of pmr_ai_value_<name>, injected rather than a copy of the vanilla file, so other mods'
    buildings stay theirs; BUILDINGS_FILE loads after their files, so this ai_value is the one that holds.
    Production Method Rework defines pmr_ai_value_<name> as its investment logic; PMR_FALLBACK_FILE defines the same
    names as vanilla's ai_value and loads before PMR's file, so PMR's win when it is on and vanilla's hold when it is not.
    Returns the inject and the fallback."""
    start = s.index(f"building_{name} = {{")
    body = s[start:block_end(s, s.index("{", start))]
    m = re.search(r"\n\tai_value = (\{|[\d.]+[^\n]*)", body)
    if m is None:
        # 1000 is NAI.PRODUCTION_BUILDING_BASE_VALUE, the engine's value when none is scripted
        base = "{\n\tvalue = 1000\n}"
    elif m.group(1) == "{":
        # block_end stops before the closing brace
        base = re.sub(r"(?m)^\t", "", body[m.start(1):block_end(body, m.start(1))]).rstrip() + "\n}"
    else:
        base = f"{{\n\tvalue = {m.group(1).split('#')[0].strip()}\n}}"
    # Vanilla plantation priorities contain strict owner scopes (British dictates). Late-game priority evaluation
    # can reach these values without a valid owner. Keep those bonuses conditional on a
    # real owner; optional scope alone need not make the surrounding trigger false when the owner is missing.
    # Only copied fallback conditions change: PMR can still replace the whole named value, and all base values,
    # additions and other vanilla conditions remain intact.
    base = re.sub(r"(?m)^([ \t]*)owner([ \t]*)=([ \t]*)(?=\{)",
                  r"\1exists = owner\n\1owner\2?=\3", base)
    ai = f"{{\n\t\tvalue = pmr_ai_value_{name}\n{hype_ops(watched(name, good))}\t}}"
    return f"INJECT:building_{name} = {{\n\tai_value = {ai}\n}}\n", f"pmr_ai_value_{name} = {base}\n"


BUILDINGS_FILE = "common/buildings/zzz_spec_investors.txt"
PMR_FALLBACK_FILE = "common/script_values/00_spec_pmr_fallback.txt"  # sorts before PMR's pmr_ipw_values.txt


def write(rel, text):
    p = MOD / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if rel.endswith(".yml"):  # a loc value passed as a string inside [...] must be quote-escaped, as vanilla's '$concept_x|q$'
        text = re.sub(r"'\$(\w+)\$'", r"'$\1|q$'", text)
    p.write_text(text, encoding="utf-8-sig", newline="\n")
    WRITTEN.add(p.relative_to(MOD).as_posix())


def remove_stale():
    """Use this build's outputs, not timestamps, to remove obsolete generated files."""
    stale = [f for d in ("common", "events", "gui", "gfx", "localization") for f in (MOD / d).rglob("*")
             if f.is_file() and f.relative_to(MOD).as_posix() not in WRITTEN | HAND_MADE]
    for f in stale:
        f.unlink()
    return stale


def law_value(name, by_law, first=""):
    """Script value choosing a number by economic system law; first: an earlier branch's limit, for a value of 0."""
    branches = "".join(f"\telse_if = {{\n\t\tlimit = {{ has_law_or_variant = law_type:law_{law} }}\n"
                       f"\t\tvalue = {n}\n\t}}\n" for law, n in by_law.items())
    if first:
        branches = f"\telse_if = {{\n\t\tlimit = {{ {first} }}\n\t\tvalue = 0\n\t}}\n" + branches
    return f"{name} = {{\n\tvalue = 1\n" + branches.replace("\telse_if", "\tif", 1) + "}"


def _free(g):
    """A restrained boom cannot end (levers.py), so it is left out of what could end."""
    return f"\tif = {{\n\t\tlimit = {{ NOT = {{ has_variable = spec_restrain_{g} }} }}\n\t\tadd = spec_risk_raw_{g}\n\t}}\n"


def log_values():
    """Values only the --log line reads; written to spec_log_values.txt in a log build only."""
    sv = ["spec_expo_raw_next = {\n\tvalue = 0\n" + "".join(_free(g) for g in GOODS) + "\tmultiply = spec_crash_scale\n}",
          "spec_log_wsum = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_weight_{g}\n" for g in GOODS) + "}"]
    sv += [f"spec_log_{k} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = {v} }}\n\t\tvalue = var:{v}\n\t}}\n}}"
           for k, v in (("heat", "spec_heat"), ("burst", "spec_c_burst"))]
    return sv + cycle.log_values(GOODS) + leverage.LOG_VALUES


def flag(name, trigger):
    return f"{name} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ {trigger} }}\n\t\tvalue = 1\n\t}}\n}}"


def values():
    # a decentralized country has no market of its own to speculate in: 0 keeps the monthly engine off it
    sv = [law_value("spec_law_mult", {law: h for law, h, _ in LAWS}, "is_country_type = decentralized"),
          law_value("spec_panic_mult", {law: p for law, _, p in LAWS}),
          law_value("spec_alloc_base", law_alloc())]
    sv.append("spec_alloc_half = {\n\tvalue = spec_alloc_base\n\tmultiply = 0.5\n}")
    sv.append("spec_alloc_quarter = {\n\tvalue = spec_alloc_base\n\tmultiply = 0.25\n}")
    # hype scaling: tight credit halves it, loose credit adds 30% (to rising prices only, spec_hype_mult_down)
    sv.append("spec_stance_hype = {\n\tvalue = 1\n"
              "\tif = {\n\t\tlimit = { spec_stance_value = -1 }\n\t\tvalue = 0.5\n\t}\n"
              "\telse_if = {\n\t\tlimit = { spec_stance_value = 1 }\n\t\tvalue = 1.3\n\t}\n}")
    # spec_depth: Financial Districts against the size of the economy (vanilla_ties.py)
    sv.append("spec_band_gain = {\n\tvalue = 1\n\tif = {\n\t\tlimit = { has_variable = spec_conf }\n"
              f"\t\tif = {{\n\t\t\tlimit = {{ var:spec_conf < {market_tab.TIERS[1][2]} }}\n\t\t\tvalue = {BAND_GAIN['wary']:g}\n\t\t}}\n"
              f"\t\telse_if = {{\n\t\t\tlimit = {{ var:spec_conf >= {MANIA} }}\n\t\t\tvalue = {BAND_GAIN['mania']:g}\n\t\t}}\n"
              f"\t\telse_if = {{\n\t\t\tlimit = {{ var:spec_conf >= {market_tab.TIERS[3][1]} }}\n\t\t\tvalue = {BAND_GAIN['buoyant']:g}\n\t\t}}\n\t}}\n}}")
    sv.append("spec_hype_mult = {\n\tvalue = spec_law_mult\n\tmultiply = spec_stance_hype\n\tmultiply = spec_tech_hype\n\tmultiply = spec_depth\n\tmultiply = spec_band_gain\n" + centres.HYPE_REF + "}")
    # 1 with no Financial Districts, 0 from the depth where spec_depth is 1
    sv.append(f"spec_shallow = {{\n\tvalue = 1\n\tsubtract = spec_depth\n\tdivide = {1 - vanilla_ties.DEPTH_MIN:g}\n\tmin = 0\n\tmax = 1\n}}")
    sv.append(f"spec_mood_scale = {{\n\tvalue = spec_shallow\n\tmultiply = {MOOD_SHALLOW - 1:g}\n\tadd = 1\n{centres.MOOD_REF}}}")
    sv.append(f"spec_shallow_panic = {{\n\tvalue = spec_shallow\n\tmultiply = {PANIC_SHALLOW:g}\n}}")
    # Rescues shorten the remaining deadline, not the time that has actually elapsed.
    # Keep the old calculation only to migrate a panic already running in an older save.
    sv.append("spec_panic_run = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_panic_elapsed }\n"
              "\t\tvalue = var:spec_panic_elapsed\n\t}\n\telse_if = {\n\t\tlimit = {\n\t\t\thas_variable = spec_panic\n\t\t\thas_variable = spec_panic_len\n\t\t}\n"
              "\t\tvalue = var:spec_panic_len\n\t\tsubtract = var:spec_panic\n\t\tmin = 0\n\t}\n}")
    # falling prices: Loose credit adds nothing (it fed slumps into Busts), Tight still damps them
    sv.append("spec_hype_mult_down = {\n\tvalue = spec_law_mult\n\tmultiply = {\n\t\tvalue = spec_stance_hype\n\t\tmax = 1\n\t}\n"
              "\tmultiply = spec_tech_hype\n\tmultiply = spec_depth\n}")
    techs = "".join(f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n\t\tadd = 0.5\n\t}}\n"
                    for t in CREDIT_TECHS)
    sv.append(f"spec_tech_credit = {{\n\tvalue = 0.5\n{techs}}}")
    sv.append("spec_stance_credit = {\n\tvalue = 1\n"
              "\tif = {\n\t\tlimit = { spec_stance_value = -1 }\n\t\tvalue = 0\n\t}\n"
              "\telse_if = {\n\t\tlimit = { spec_stance_value = 1 }\n\t\tvalue = 1.6\n\t}\n}")
    sv.append("spec_credit_mult = {\n\tvalue = spec_law_mult\n\tmultiply = spec_tech_credit\n\tmultiply = spec_stance_credit\n\tmultiply = spec_reform_credit\n}")
    # every factor of the month's lending: the rows of the Credit Lent tooltip, and its Lending rate word
    sv.append(f"spec_credit_rate = {{\n\tvalue = spec_credit_mult\n{cycle.CREDIT}{centres.CREDIT}}}")
    # banks lend against the savings flowing through them: a share of the investment pool's month of income (the
    # game's figure is weekly), confidence's share at most CREDIT_FLOW_MAX, then times the lending rate, never more than
    # CREDIT_CEILING of it in a month, and only while outstanding credit is under the credit limit in months of the income
    # leverage is measured against, as reserves ran out on 19th century banks
    sv.append(f"spec_pool_month = {{\n\tvalue = investment_pool_gross_income\n\tmultiply = {WEEKS_PER_MONTH}\n\tmin = 0\n}}")
    # fixed_range gives every country updating on the same day the same number (test lev7: 7023 of 7437 days), so each
    # adds its own changing figures and wraps back into the range. Wrapping an even roll leaves it even, so the odds don't change
    sv.append(f"spec_mood_roll = {{\n\tvalue = total_population\n\tmultiply = 0.01731\n\tadd = spec_pool_month\n\tadd = var:spec_mood_shift\n"
              f"\tmodulo = {2 * MOOD_SHOCK:g}\n\tsubtract = {MOOD_SHOCK:g}\n}}")
    sv.append(f"spec_credit_ceiling = {{\n\tvalue = spec_pool_month\n\tmultiply = {CREDIT_CEILING}\n}}")
    if leverage.ON:
        sv.append(leverage.limit(centres.LIMIT_REF))
    sv.append(f"spec_credit_room = {{\n\tvalue = {'spec_lev_income' if leverage.ON else 'spec_pool_month'}\n{leverage.cap(CREDIT_CAP_MONTHS)}"
              "\tif = {\n\t\tlimit = { has_variable = spec_debt }\n\t\tsubtract = var:spec_debt\n\t}\n\tmin = 0\n}")
    capped = "\tmax = spec_credit_ceiling\n\tmax = spec_credit_room\n\tmin = 0\n"
    base = (f"\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_conf }}\n\t\tadd = var:spec_conf\n\t}}\n\tsubtract = {CREDIT_FROM}\n\tdivide = {100 - CREDIT_FROM}\n"
            f"\tmultiply = {CREDIT_SHARE}\n\tmax = {CREDIT_FLOW_MAX}\n\tmultiply = spec_pool_month\n")
    sv.append(f"spec_credit = {{\n{base}\tmultiply = spec_credit_rate\n{capped}}}")
    # display only: this month's credit under Normal and Loose, for the tab's stance tooltips
    preview = (f"{base}\tmultiply = spec_law_mult\n\tmultiply = spec_tech_credit\n\tmultiply = spec_reform_credit\n{cycle.CREDIT}{centres.CREDIT}"
               "{loose}\tif = {\n\t\tlimit = { " + leverage.BLOCKED + " }\n\t\tvalue = 0\n\t}\n" + capped)
    sv.append("spec_credit_preview = {\n" + preview.replace("{loose}", "") + "}")
    sv.append("spec_credit_preview_loose = {\n" + preview.replace("{loose}", "\tmultiply = 1.6\n") + "}")
    sv.append("spec_reach = {\n\tvalue = " + f"{REACH_MINOR:g}\n" + "".join(
        f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ country_rank = rank_value:{r} }}\n\t\tvalue = {REACH[v]:g}\n\t}}\n"
        for i, (v, r) in enumerate([(7, "great_power"), (6, "major_power"), (5, "unrecognized_major_power")])) + "}")
    # display only: the price trend at which each interest level starts here, levels 2 to 6 (the tab's level
    # tooltips). Interest is 1 + trend x HYPE_GAIN x spec_hype_mult rising, 1 / (1 - that) falling, so a cut c sits at
    # c - 1 or 1 - 1/c of a trend point
    for i, c in enumerate([CRASH_BELOW, COOLING_HYPE, RISING_HYPE, HOT_HYPE, PEAK_FOR_CRASH], 2):
        sv.append(f"spec_level_from_{i} = {{\n\tvalue = {(c - 1 if c >= 1 else 1 - 1 / c):.4g}\n\tdivide = {HYPE_GAIN}\n"
                  f"\tdivide = {{\n\t\tvalue = spec_hype_mult{'' if c >= 1 else '_down'}\n\t\tmin = 0.01\n\t}}\n}}")
    # read by the tab as well, so it must not assume the variable exists yet
    sv.extend(leverage.values(PANIC, PANIC_NEAR))
    sv.extend(leverage.BAILOUT_VALUES)
    sv.append(f"spec_clawback = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_debt }}\n\t\tvalue = var:spec_debt\n\t\tmultiply = {CLAWBACK}\n\t\tmax = investment_pool\n\t\tmin = 0\n\t}}\n}}")
    # this month's runoff of outstanding credit, and what the investment pool repays of it: never more than the pool holds
    sv.append(f"spec_credit_runoff = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = spec_debt }}\n\t\tvalue = var:spec_debt\n\t\tmultiply = {CREDIT_RUNOFF}\n\t\tmin = 0\n\t}}\n}}")
    sv.append("spec_credit_repay = {\n\tvalue = spec_credit_runoff\n\tmax = investment_pool\n\tmin = 0\n}")
    # to the nearest 1,000, as spec_speculator_tax: event tooltips show it whole
    sv.append(f"spec_rescue_share = {{\n\tvalue = {RESCUE_COST_PRIVATE}\n\tif = {{\n\t\tlimit = {{ has_technology_researched = central_banking }}\n"
              f"\t\tvalue = {RESCUE_COST}\n\t}}\n\tmultiply = spec_reform_rescue\n{cycle.COST}{centres.PLEDGE_COST}\tmin = {RESCUE_FLOOR}\n}}")
    sv.append(f"spec_rescue_months = {{\n\tvalue = {RESCUE_MONTHS_PRIVATE}\n\tif = {{\n\t\tlimit = {{ has_technology_researched = central_banking }}\n"
              f"\t\tvalue = {RESCUE_MONTHS}\n\t}}\n\tadd = spec_reform_rescue_months\n}}")
    tech = lambda t: f"\tif = {{\n\t\tlimit = {{ has_technology_researched = {t} }}\n"
    sv.append(f"spec_fin_boom = {{\n\tvalue = {FIN_BOOM_BASE:g}\n" + "".join(f"{tech(t)}\t\tadd = {n:g}\n\t}}\n" for t, n in FIN_BOOM.items())
              + f"{tech(FIN_LEVERAGE[0])}\t\tmultiply = {FIN_LEVERAGE[1]:g}\n\t}}\n\tmultiply = spec_reform_boom\n}}")
    sv.append("spec_fin_risk = {\n\tvalue = 1\n" + "".join(f"{tech(t)}\t\tmultiply = {n:g}\n\t}}\n" for t, n in [*FIN_RISK.items(), FIN_LEVERAGE])
              + "\tmultiply = spec_reform_risk\n}")
    rule = lambda name, key: (f"{name} = {{\n\tvalue = {VOLATILITY['historical'][key]:g}\n\tif = {{\n"
                              f"\t\tlimit = {{ has_game_rule = spec_volatility_heightened }}\n"
                              f"\t\tvalue = {VOLATILITY['heightened'][key]:g}\n\t}}\n}}")
    sv += [rule("spec_heat_from", "heat"), rule("spec_burst_per_heat", "per"), rule("spec_burst_max", "max"),
           rule("spec_boom_rule", "boom"), "spec_burst_floor = {\n\tvalue = 0\n\tsubtract = spec_burst_max\n}"]
    sv.append(f"spec_macro = {{\n\tvalue = 1\n{tech(MACRO[0])}\t\tvalue = {MACRO[1]:g}\n\t}}\n}}")
    sv.append(f"spec_recover_pct = {{\n\tvalue = {CONF_RECOVER * 100:g}\n\tmultiply = spec_macro\n{centres.RECOVER_REF}}}")  # display only
    sv.append(f"spec_ld_own_drift = {{\n\tvalue = {depression.OWN_DRIFT:g}\n\tmultiply = spec_macro\n}}")
    sv.append(f"spec_flight_mult = {{\n\tvalue = {FLIGHT_BASE:g}\n" + "".join(f"{tech(t)}\t\tadd = {n:g}\n\t}}\n" for t, n in FLIGHT_TECHS.items()) + centres.FLIGHT_REF + "}")
    sv.append(f"spec_foreign_loss_mult = {{\n\tvalue = {UNSTANDARD[1]:g}\n{tech(UNSTANDARD[0])}\t\tvalue = 1\n\t}}\n}}")
    sv.append(f"spec_flight_gain_max = {{\n\tvalue = {FLIGHT_GAIN:g}\n\tmultiply = spec_flight_mult\n}}")  # display only
    # the share scales with the panic left to cut short: x(months left / RESCUE_REF_MONTHS), within RESCUE_SCALE
    sv.append(f"spec_rescue_scale = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{ has_variable = spec_panic }}\n"
              f"\t\tvalue = var:spec_panic\n\t\tdivide = {RESCUE_REF_MONTHS}\n\t\tmin = {RESCUE_SCALE[0]:g}\n\t\tmax = {RESCUE_SCALE[1]:g}\n\t}}\n}}")
    sv.append("spec_rescue_share_now = {\n\tvalue = spec_rescue_share\n\tmultiply = spec_rescue_scale\n}")
    sv.append(f"spec_panic_relief_week = {{\n\tvalue = gdp\n\tdivide = {52 / PANIC_RELIEF:g}\n\tmin = 1\n}}")
    sv.append(f"spec_rescue_cost = {{\n\tvalue = gdp\n\tmultiply = spec_rescue_share_now\n\tdivide = 1000\n\tround = yes\n\tmultiply = 1000\n\tmin = 1000\n}}")
    # the mania event's levy on speculators, rounded to 1000 like vanilla's event money
    sv.append(f"spec_speculator_tax = {{\n\tvalue = gdp\n\tdivide = 100000\n\tmultiply = {MANIA_TAX * 100:g}\n"
              "\tround = yes\n\tmultiply = 1000\n\tmin = 1000\n}")
    sv.append(f"spec_panic_months = {{\n\tvalue = {PANIC_DAYS / 30:g}\n\tmultiply = spec_panic_mult\n"
              "\tceiling = yes\n\tmin = 1\n}")
    sv.append(f"spec_conf_recover = {{\n\tvalue = {CONF_START}\n\tsubtract = var:spec_conf\n\tmultiply = {CONF_RECOVER}\n\tmultiply = spec_macro\n{centres.RECOVER_REF}}}")
    sv.append("spec_conf_pre = {\n\tvalue = var:spec_conf\n\tadd = var:spec_c_recover\n\tadd = var:spec_c_boom\n"
              "\tadd = var:spec_c_crash\n\tadd = var:spec_c_restrain\n\tadd = var:spec_c_turmoil\n\tadd = var:spec_c_debt\n\tadd = var:spec_c_foreign\n\tadd = var:spec_c_world\n"
              "\tadd = var:spec_c_mood\n\tadd = var:spec_c_growth\n\tadd = var:spec_c_business\n}")
    sv.append(f"spec_tight_pull = {{\n\tvalue = {TIGHT_FROM}\n\tsubtract = spec_conf_pre\n\tmultiply = {TIGHT_PULL:g}\n\tmax = 0\n}}")
    sv.append("spec_conf_next = {\n\tvalue = spec_conf_pre\n\tadd = var:spec_c_tight\n\tmin = 0\n\tmax = 100\n}")
    # deeper speculation falls harder, Manor Houses steady it (vanilla_ties.py)
    sv.append(f"spec_crash_scale = {{\n\tvalue = var:spec_conf\n\tdivide = {CONF_START}\n\tmultiply = spec_depth\n\tmultiply = spec_steady\n\tmultiply = spec_fin_risk\n}}")
    cost = goods_cost()
    # market_goods scope: its trade value, as spec_mv_<g> reads it from the country, for sorting the goods board
    sv.append("spec_mg_value = {\n\tvalue = market_goods_sell_orders\n\tmultiply = goods.base_price\n}")
    sv.append("spec_market_value = {\n\tvalue = 0\n" + "".join(f"\tadd = spec_mv_{g}\n" for g in GOODS) + "\tmin = 1\n}")
    sv.extend(exposure.values(GOODS))
    sv.extend(cycle.values(GOODS, TOAST_SHARE / EXPOSURE_FULL))
    for g in GOODS:
        # market_goods_pricier is signed: negative when the good sits below base price
        sv.append(f"spec_dev_{g} = {{\n\tvalue = 0\n\tmarket ?= {{\n\t\tmg:{g} ?= {{\n\t\t\tadd = market_goods_pricier\n\t\t}}\n\t}}\n}}")
        sv.append(f"spec_mv_{g} = {{\n\tvalue = 0\n\tmarket ?= {{\n\t\tmg:{g} ?= {{\n\t\t\tadd = market_goods_sell_orders\n\t\t}}\n\t}}\n"
                  f"\tmultiply = {cost[g]:g}\n}}")
        # how much this good moves confidence: its share of the market's trade, full at EXPOSURE_FULL
        sv.append(f"spec_weight_{g} = {{\n\tvalue = spec_mv_{g}\n\tdivide = var:spec_mv_total\n\tdivide = {EXPOSURE_FULL}\n\tmax = 1\n}}")
        sv.append(f"spec_fast_next_{g} = {{\n\tvalue = var:spec_fast_{g}\n\tmultiply = {1 - FAST:g}\n"
                  f"\tadd = {{\n\t\tvalue = spec_dev_{g}\n\t\tmultiply = {FAST}\n\t}}\n}}")
        sv.append(f"spec_slow_next_{g} = {{\n\tvalue = var:spec_slow_{g}\n\tmultiply = {1 - SLOW:g}\n"
                  f"\tadd = {{\n\t\tvalue = spec_dev_{g}\n\t\tmultiply = {SLOW}\n\t}}\n}}")
        # raw: what the market alone makes of it; next: after the speculation levers (levers.py)
        sv.append(f"spec_trend_{g} = {{\n\tvalue = var:spec_fast_{g}\n\tsubtract = var:spec_slow_{g}\n"
                  f"\tmultiply = {HYPE_GAIN}\n\tif = {{\n\t\tlimit = {{ var:spec_fast_{g} >= var:spec_slow_{g} }}\n\t\tmultiply = var:spec_hm\n\t}}\n"
                  f"\telse = {{\n\t\tmultiply = var:spec_hmd\n\t}}\n}}")
        sv.append(f"spec_hype_raw_{g} = {{\n\tvalue = 1\n\tif = {{\n\t\tlimit = {{ spec_trend_{g} >= 0 }}\n\t\tadd = spec_trend_{g}\n\t}}\n"
                  f"\telse = {{\n\t\tdivide = {{\n\t\t\tvalue = 1\n\t\t\tsubtract = spec_trend_{g}\n\t\t}}\n\t}}\n"
                  f"\tmin = {HYPE_MIN}\n\tmax = {HYPE_MAX}\n}}")
        # a glut sets interest to Doubtful; a lever (levers.py) then overrides it, but Encourage is not allowed in a glut
        sv.append(f"spec_hype_next_{g} = {{\n\tvalue = spec_hype_raw_{g}\n"
                  f"\tif = {{\n\t\tlimit = {{ has_variable = spec_glut_{g} }}\n\t\tvalue = {GLUT_HYPE}\n\t}}\n"
                  f"{levers.hype_clamp(g, RISING_HYPE)}}}")
        # the peak drifts back to 1 so an old boom stops counting; eased to Calm, a restrained boom only drifts
        # restrained, it deflates faster: the boom winds down as a Correction over about a year (spec_c_restrain)
        sv.append(f"spec_peak_next_{g} = {{\n\tvalue = var:spec_peak_{g}\n\tmultiply = 0.97\n\tadd = 0.03\n"
                  f"\tif = {{\n\t\tlimit = {{ has_variable = spec_restrain_{g} }}\n\t\tvalue = var:spec_peak_{g}\n"
                  f"\t\tmultiply = {RESTRAIN_DEFLATE}\n\t\tadd = {1 - RESTRAIN_DEFLATE:.4g}\n\t}}\n"
                  f"\tif = {{\n\t\tlimit = {{ var:spec_hype_{g} > var:spec_peak_{g} }}\n\t\tvalue = var:spec_hype_{g}\n\t}}\n}}")
        # what this month's deflation of a restrained boom costs: a Correction's rate on the peak it let out
        sv.append(f"spec_restrain_cost_{g} = {{\n\tvalue = var:spec_peak_{g}\n\tsubtract = spec_peak_next_{g}\n\tmin = 0\n"
                  f"\tmultiply = {UNWINDS[2][3]:g}\n\tmultiply = spec_weight_{g}\n\tmultiply = spec_exp_mult_{g}\n}}")
        # how this boom would end now (UNWINDS), and the confidence that would cost before the cap and the scaling
        tiers = lambda body: "".join(f"\t{'if' if i == 0 else 'else_if'} = {{\n\t\tlimit = {{ var:spec_peak_{g} >= {peak} }}\n{body(sev, rate)}\t}}\n"
                                     for i, (sev, peak, _, rate, _) in enumerate(UNWINDS))
        sv.append(f"spec_sev_next_{g} = {{\n\tvalue = 0\n{tiers(lambda sev, rate: f'{chr(9) * 2}value = {sev}{chr(10)}')}}}")
        # the multiplications inside each tier: a good with no boom to end stays 0 without working them out
        sv.append(f"spec_risk_raw_{g} = {{\n\tvalue = 0\n"
                  + tiers(lambda sev, rate: f"\t\tvalue = var:spec_peak_{g}\n\t\tsubtract = 1\n\t\tmultiply = {rate:g}\n"
                          f"\t\tmultiply = spec_weight_{g}\n\t\tmultiply = spec_exp_mult_{g}\n{cycle.over_mult(g).replace(chr(9), chr(9) * 2, 1)}")
                  + "}")
        sv.append(f"spec_risk_next_{g} = {{\n\tvalue = spec_risk_raw_{g}\n\tmultiply = spec_crash_scale\n\tmax = {CONF_CRASH_MAX}\n}}")
    # all of them collapsing at once, scaled and capped as a month's collapses are
    sv.append("spec_exposure_next = {\n\tvalue = 0\n" + "".join(_free(g) for g in GOODS)
              + f"\tmultiply = spec_crash_scale\n\tmax = {CONF_CRASH_MAX}\n}}")
    # how many booms could end (the Booms at Risk tooltip)
    sv.append("spec_n_risk_next = {\n\tvalue = 0\n" + "".join(
        f"\tif = {{\n\t\tlimit = {{ has_variable = spec_sev_{g} var:spec_sev_{g} > 0 NOT = {{ has_variable = spec_restrain_{g} }} }}\n\t\tadd = 1\n\t}}\n" for g in GOODS) + "}")
    sv.append("spec_n_held_next = {\n\tvalue = 0\n" + "".join(
        f"\tif = {{\n\t\tlimit = {{ has_variable = spec_sev_{g} var:spec_sev_{g} > 0 has_variable = spec_restrain_{g} }}\n\t\tadd = 1\n\t}}\n" for g in GOODS) + "}")
    for b, ups in UPGRADES.items():
        base = next(m[b] for m in SELLS.values() if b in m)
        known = lambda t: f"has_technology_researched = {t}" if t else "always = yes"
        adds = "".join(f"\tif = {{\n\t\tlimit = {{ {known(t)} }}\n\t\tadd = var:spec_hype_{g}\n\t}}\n" for g, t in ups)
        count = "".join(f"\t\tif = {{\n\t\t\tlimit = {{ {known(t)} }}\n\t\t\tadd = 1\n\t\t}}\n" for _, t in ups)
        sv.append(f"spec_bhype_next_{b} = {{\n\tvalue = var:spec_hype_{base}\n{adds}\tdivide = {{\n\t\tvalue = 1\n{count}\t}}\n}}")
    sv += [flag("spec_in_panic", "has_variable = spec_panic"), flag("spec_has_je", "has_journal_entry = je_spec_markets"),
           flag("spec_has_central_banking", "has_technology_researched = central_banking"),
           flag("spec_rescued_value", "has_variable = spec_rescued"),
           "spec_stance_value = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_stance }\n\t\tvalue = var:spec_stance\n\t}\n}"]
    # a trusted government steadies the market: panic length x1.2 at 0 legitimacy, x1 at 50, x0.8 at 100
    sv.append("spec_trust_mult = {\n\tvalue = 1.2\n\tsubtract = {\n\t\tvalue = government_legitimacy\n\t\tdivide = 250\n\t}\n"
              "\tmin = 0.8\n\tmax = 1.2\n}")
    sv.append("spec_panic_months_trust = {\n\tvalue = spec_panic_months\n\tmultiply = spec_trust_mult\n\tmultiply = spec_reform_panic_len\n\tceiling = yes\n\tmin = 1\n}")
    write("common/script_values/spec_values.txt", "\n\n".join(sv) + "\n")


def state_vars():
    """Every variable the mod keeps on a country, so leaving the market economy can clear them."""
    per_good = [f"spec_{k}_{g}" for g in GOODS for k in ("fast", "slow", "hype", "hprev", "peak")]
    ranks = [f"spec_{k}{s}" for k in ("top1", "top2", "top3", "low1", "low2") for s in ("", "_v")]
    return (["spec_centre_score", "spec_conf", "spec_stance", "spec_stance_cooldown", "spec_panic", "spec_panic_len", "spec_panic_elapsed", "spec_rescued",
             "spec_panic_cooldown", "spec_mania", "spec_debt", "spec_clawed", "spec_crashed", "spec_crash_top",
             "spec_foreign_pending", "spec_foreign_src", "spec_caught", "spec_src_gdp", "spec_je_added", "spec_temper",
             "spec_calm", "spec_inquired"]
            + per_good + [f"spec_bhype_{b}" for b in UPGRADES] + ranks + market_visual.STATE_VARS
            + [f"spec_{k}_{g}" for g in GOODS for k in ("word", "risk", "sev", "glut", "cb", "cc")] + [f"spec_n_w{i}" for i in range(1, 7)]
            + ["spec_boom_raw", "spec_crash_raw"] + [f"spec_tm_{k}" for k in ("play", "default", "revolution", "broke", "warcap")]
            + [f"spec_hist{n}" for n in range(1, market_tab.HISTORY + 1)]
            + [f"spec_n_w{i}_{c}" for i in range(1, 7) for c in market_tab.CATEGORIES]
            + ["spec_exposure", "spec_risk_src", "spec_risk_src_hit", "spec_risk_src_tie", "spec_risk_src_w", "spec_risk_src_reach", "spec_risk_src_size"]
            + ["spec_mood_shift", "spec_restrain_raw", "spec_fh_size", "spec_fh_tie", "spec_fh_reach"]
            + ["spec_expo_raw", "spec_n_risk", "spec_n_held", "spec_risk_top", "spec_risk_top_good", "spec_n_end_1", "spec_n_end_2", "spec_n_end_3"]
            + [f"spec_p{n}" for n in range(1, len(market_tab.PRESSURES) + 1)]
            + ["spec_hm", "spec_hmd", "spec_c_limit", "spec_c_rescue", "spec_c_burst", "spec_heat", "spec_c_caution", "spec_c_mood", "spec_c_restrain"]
            + leverage.STATE_VARS + levers.state_vars(GOODS) + interest_board.state_vars(GOODS) + exposure.state_vars(GOODS) + cycle.state_vars(GOODS) + charts.state_vars(GOODS) + diplomacy.STATE_VARS + economy.STATE_VARS + movements.state_vars() + vanilla_ties.STATE_VARS
            # the Exchange's trust and charter: a country coming back to the market economy starts its Exchange afresh
            + (["spec_centre_trust", "spec_centre_calm", "spec_centre_yrs", "spec_exch_known"] if centres.ON else [])
            + (["spec_charter_lock", "spec_pursue_n", "spec_pw_sum"] + [f"spec_{p}_{k}" for k, *_ in centres.NAMES for p in ("pu", "pw")] + [f"spec_{p}_{k}" for k, *_ in centres.NAMES for p in ("has", "lead")]
               if centres.NAMES_ON else []) + (centres.RIVAL_VARS if centres.RIVAL_ON else []))


def skip_idle(g, block):
    """D6: a good this market does not trade, with nothing left to wind down, is left alone: the month's block would
    only write back the values it already holds. Any trade, price move, lever or glut makes it run again."""
    near = lambda v, at: f"var:{v} > {at - 0.001:g} var:{v} < {at + 0.001:g}"
    t = "\t\t\t"
    idle = [f"has_variable = spec_word_{g}", f"var:spec_word_{g} = 0", f"has_variable = spec_hprev_{g}",
            f"NOT = {{ has_variable = spec_glut_{g} }}", f"NOT = {{ has_variable = spec_restrain_{g} }}",
            f"NOT = {{ has_variable = spec_encourage_{g} }}", f"var:spec_sev_{g} = 0", near(f"spec_fast_{g}", 0),
            near(f"spec_slow_{g}", 0), near(f"spec_hype_{g}", 1), near(f"spec_hprev_{g}", 1), f"var:spec_peak_{g} < 1.01",
            f"spec_mv_{g} = 0", f"spec_dev_{g} = 0"]
    return (f"{t}if = {{\n{t}\tlimit = {{\n{t}\t\tNOT = {{\n{t}\t\t\tAND = {{\n" + "".join(f"{t}\t\t\t\t{c}\n" for c in idle)
            + f"{t}\t\t\t}}\n{t}\t\t}}\n{t}\t}}\n" + "".join("\t" + l for l in block.splitlines(True)) + f"{t}}}\n")


def word_block(g, cuts):
    """Sets spec_word_<g> (3 tabs deep): 0 untraded, else the word for raw hype the first month (or once traded
    again), then a move only once hype is past a cut by WORD_BUFFER of it (below 1, on the 1/x side): up to the highest
    word whose start hype clears by the buffer, or down to the lowest word whose end it falls short of by the buffer.
    The words overlap by the buffer, so last month's word holds there. cuts: where words 2 to 6 start."""
    up = [c * (1 + WORD_BUFFER) if c >= 1 else c / (1 - WORD_BUFFER) for c in cuts]
    down = [c * (1 - WORD_BUFFER) if c >= 1 else c / (1 + WORD_BUFFER) for c in cuts]
    assert all(a < b for a, b in zip(up, down[1:])), "the buffer must not close a word"
    t, h, var = "\t\t\t\t\t", f"var:spec_hype_{g}", f"var:spec_word_{g}"
    put = lambda w: f"{t}\tset_variable = {{ name = spec_word_{g} value = {w} }}\n{t}}}\n"
    raw = ("".join(f"{t}{'if' if w == 6 else 'else_if'} = {{\n{t}\tlimit = {{ {h} >= {c:.4g} }}\n" + put(w)
                   for w, c in zip(range(6, 1, -1), reversed(cuts)))
           + f"{t}else = {{\n{t}\tset_variable = {{ name = spec_word_{g} value = 1 }}\n{t}}}\n")
    moves = ([(f"{var} < {w} {h} >= {c:.4g}", w) for w, c in zip(range(6, 1, -1), reversed(up))]
             + [(f"{var} > {w} {h} < {c:.4g}", w) for w, c in zip(range(1, 6), down)])
    held = "".join(f"{t}{'if' if i == 0 else 'else_if'} = {{\n{t}\tlimit = {{ {test} }}\n" + put(w)
                   for i, (test, w) in enumerate(moves))
    return (f"\t\t\tif = {{\n\t\t\t\tlimit = {{ spec_mv_{g} > 0 }}\n"
            f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{\n\t\t\t\t\t\thas_variable = spec_word_{g}\n\t\t\t\t\t\t{var} > 0\n\t\t\t\t\t}}\n"
            f"{held}\t\t\t\t}}\n\t\t\t\telse = {{\n{raw}\t\t\t\t}}\n\t\t\t}}\n"
            f"\t\t\telse = {{\n\t\t\t\tset_variable = {{ name = spec_word_{g} value = 0 }}\n\t\t\t}}\n")


def monthly(log):
    # the goods board's interest words start at these levels: Doubtful, Calm, Keen, Eager, Feverish
    word_cuts = [CRASH_BELOW, COOLING_HYPE, RISING_HYPE, HOT_HYPE, PEAK_FOR_CRASH]
    # the goods board's counts and lists and the Market Heat shares only matter where a player can see them
    shown = ["".join(f"\t\t\tset_variable = {{ name = spec_n_w{w} value = 0 }}\n\t\t\tclear_variable_list = spec_goods_w{w}\n"
                     + "".join(f"\t\t\tset_variable = {{ name = spec_n_w{w}_{c} value = 0 }}\n\t\t\tclear_variable_list = spec_goods_w{w}_{c}\n"
                               for c in market_tab.CATEGORIES)
                     for w in range(1, 7))]
    shown += ["".join(f"\t\t\t{'if' if w == 1 else 'else_if'} = {{\n\t\t\t\tlimit = {{ var:spec_word_{g} = {w} }}\n"
                      f"\t\t\t\tchange_variable = {{ name = spec_n_w{w} add = 1 }}\n"
                      f"\t\t\t\tchange_variable = {{ name = spec_n_w{w}_{categories()[g]} add = 1 }}\n\t\t\t}}\n"
                      for w in range(1, 7)) for g in GOODS]
    # the tab's per-frame figures, worked out once a month: each band's tile rows and each tile's bar, move and badge
    shown.append(interest_board.monthly(GOODS, categories()))
    shown.append(exposure.ui(GOODS))
    shown.append(cycle.ui(GOODS, TOAST_SHARE / EXPOSURE_FULL))
    # D4: the country-wide interest multipliers, worked out once here instead of twice for each good
    goods = ["\t\t\tset_variable = { name = spec_hm value = spec_hype_mult }\n"
             "\t\t\tset_variable = { name = spec_hmd value = spec_hype_mult_down }\n"]
    for g in GOODS:
        goods.append(skip_idle(g,
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ NOT = {{ has_variable = spec_fast_{g} }} }}\n"
            f"\t\t\t\tset_variable = {{ name = spec_fast_{g} value = spec_dev_{g} }}\n"
            f"\t\t\t\tset_variable = {{ name = spec_slow_{g} value = spec_dev_{g} }}\n"
            f"\t\t\t\tset_variable = {{ name = spec_peak_{g} value = 1 }}\n\t\t\t}}\n"
            f"\t\t\tset_variable = {{ name = spec_fast_{g} value = spec_fast_next_{g} }}\n"
            f"\t\t\tset_variable = {{ name = spec_slow_{g} value = spec_slow_next_{g} }}\n"
            # last month's interest, so the tab can show which way it is moving
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_variable = spec_hype_{g} }}\n"
            f"\t\t\t\tset_variable = {{ name = spec_hprev_{g} value = var:spec_hype_{g} }}\n\t\t\t}}\n"
            f"\t\t\tset_variable = {{ name = spec_hype_{g} value = spec_hype_next_{g} }}\n"
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_variable = spec_restrain_{g} }}\n"
            f"\t\t\t\tchange_variable = {{ name = spec_c_restrain subtract = spec_restrain_cost_{g} }}\n\t\t\t}}\n"
            f"\t\t\tset_variable = {{ name = spec_peak_{g} value = spec_peak_next_{g} }}\n"
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ var:spec_hype_{g} >= {HOT_HYPE} }}\n"
            f"\t\t\t\tchange_variable = {{ name = spec_c_boom add = {{ value = spec_weight_{g} multiply = {CONF_PER_HOT} }} }}\n"
            # this good's part, before the cap and Manor Houses scale the sum (the Goods chip scales it back)
            f"\t\t\t\tset_variable = {{ name = spec_cb_{g} value = {{ value = spec_weight_{g} multiply = {CONF_PER_HOT} }} }}\n"
            f"\t\t\t\tchange_variable = {{ name = spec_n_boom add = 1 }}\n\t\t\t}}\n"
            # the boom ends: a Correction, Bust or Collapse by how high it went (UNWINDS); the bigger the boom and
            # the more of the market it was, the bigger the loss, and the industry is left in a glut for a while
            f"\t\t\tset_variable = {{ name = spec_sev_{g} value = spec_sev_next_{g} }}\n"
            # Encourage lifts once the good is in a boom that could end in a Bust or Collapse, so its floor never holds one up
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_variable = spec_encourage_{g} var:spec_sev_{g} >= 2 }}\n"
            f"\t\t\t\tremove_variable = spec_encourage_{g}\n\t\t\t}}\n"
            + "".join(f"\t\t\t{'if' if i == 0 else 'else_if'} = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\tvar:spec_sev_{g} = {sev}\n"
                      f"\t\t\t\t\tvar:spec_hype_{g} < {below}\n\t\t\t\t}}\n"
                      # the ending's cost, worked out once
                      f"\t\t\t\tset_local_variable = {{ name = spec_rr value = spec_risk_raw_{g} }}\n"
                      f"\t\t\t\tchange_variable = {{ name = spec_c_crash subtract = local_var:spec_rr }}\n"
                      f"\t\t\t\tset_variable = {{ name = spec_cc_{g} value = local_var:spec_rr days = 28 }}\n"
                      f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ OR = {{ NOT = {{ has_variable = spec_crash_top }} local_var:spec_rr > var:spec_crash_top }} }}\n"
                      f"\t\t\t\t\tset_variable = {{ name = spec_crashed value = g:{g} }}\n"
                      f"\t\t\t\t\tset_variable = {{ name = spec_crash_top value = local_var:spec_rr days = 28 }}\n\t\t\t\t}}\n{companies.crash(g, sev)}{cycle.burn(g, sev, TOAST_SHARE / EXPOSURE_FULL)}{centres.boom_end(g, sev, TOAST_SHARE / EXPOSURE_FULL)}"
                      + (f"\t\t\t\tchange_variable = {{ name = spec_n_end_{sev} add = 1 }}\n" if log else "") +  # only the log line reads it
                      f"\t\t\t\tset_variable = {{ name = spec_glut_{g} value = {sev} days = {months * 30} }}\n"
                      # the Investor Interest row's crash month (interest_board.ui_effect, later this month)
                      f"\t\t\t\tset_variable = {{ name = spec_ui_crash_{g} value = {sev} days = 28 }}\n"
                      f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ is_player = yes spec_weight_{g} >= {TOAST_SHARE / EXPOSURE_FULL:.3f} }}\n\t\t\t\t\tg:{g} = {{ save_scope_as = spec_note_good }}\n"
                      f"\t\t\t\t\t{exposure.note(g)}{cycle.note(g)}{notify.boom_note_scopes(g)}"
                      f"{notify.boom_post(sev)}\t\t\t\t}}\n"
                      f"\t\t\t\tset_variable = {{ name = spec_peak_{g} value = 1 }}\n{exposure.ended(g)}"
                      f"\t\t\t\tset_variable = {{ name = spec_sev_{g} value = 0 }}\n\t\t\t}}\n"
                      for i, (sev, _, below, _, months) in enumerate(UNWINDS))
            +
            # the interest word of goods traded here (0 untraded, 1 Fleeing to 6 Feverish), read by the levers and
            # the AI, and what a collapse of this boom would cost
            f"{cycle.over_track(g)}\t\t\tset_local_variable = {{ name = spec_wold value = 0 }}\n"
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_variable = spec_word_{g} }}\n"
            f"\t\t\t\tset_local_variable = {{ name = spec_wold value = var:spec_word_{g} }}\n\t\t\t}}\n"
            + word_block(g, word_cuts)
            + f"\t\t\tif = {{\n\t\t\t\tlimit = {{\n\t\t\t\t\tis_player = yes\n\t\t\t\t\tvar:spec_word_{g} = 6\n"
            f"\t\t\t\t\tlocal_var:spec_wold > 0\n\t\t\t\t\tlocal_var:spec_wold < 6\n\t\t\t\t\tspec_weight_{g} >= {TOAST_SHARE / EXPOSURE_FULL:.3f}\n\t\t\t\t}}\n"
            f"\t\t\t\tg:{g} = {{ save_scope_as = spec_note_good }}\n\t\t\t\tpost_notification = spec_feverish\n\t\t\t}}\n"
            + f"\t\t\tset_variable = {{ name = spec_risk_{g} value = spec_risk_next_{g} }}\n"))
    goods.append("\t\t\tset_variable = { name = spec_exposure value = spec_exposure_next }\n"
                 + ("\t\t\tset_variable = { name = spec_expo_raw value = spec_expo_raw_next }\n" if log else "") +  # a sum over every good that only the log line reads
                 "\t\t\tset_variable = { name = spec_n_risk value = spec_n_risk_next }\n"
                 "\t\t\tset_variable = { name = spec_n_held value = spec_n_held_next }\n")
    # the boom whose ending would cost most, for the Booms at Risk chip
    goods.append("\t\t\tset_variable = { name = spec_risk_top value = 0 }\n"
                 + "".join(f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_variable = spec_risk_{g} var:spec_risk_{g} > var:spec_risk_top NOT = {{ has_variable = spec_restrain_{g} }} }}\n"
                           f"\t\t\t\tset_variable = {{ name = spec_risk_top value = var:spec_risk_{g} }}\n"
                           f"\t\t\t\tset_variable = {{ name = spec_risk_top_good value = g:{g} }}\n\t\t\t}}\n" for g in GOODS))
    # the sums before scaling, so the Goods chip can share the scaled ones out among its goods
    goods.append("\t\t\tset_variable = { name = spec_boom_raw value = var:spec_c_boom }\n"
                 "\t\t\tset_variable = { name = spec_crash_raw value = var:spec_c_crash }\n"
                 "\t\t\tset_variable = { name = spec_restrain_raw value = var:spec_c_restrain }\n")
    # Market Heat: the share of trade at each interest word, and of booms that would end in a collapse
    shown += [market_tab.ind(market_visual.script_reset(), 3)] + [market_tab.ind(market_visual.script_tally(g), 3) for g in GOODS]
    shown.append(market_tab.ind(market_visual.script_shares(), 3))
    # the board's lists, largest share of trade first: each good into a scratch list for its word, then the market's
    # goods in order of trade value (spec_mg_value, as spec_mv_<g>) move over. One sort of the market's goods per month
    shown += ["".join(f"\t\t\t{'if' if w == 1 else 'else_if'} = {{\n\t\t\t\tlimit = {{ var:spec_word_{g} = {w} }}\n"
                      f"\t\t\t\tadd_to_variable_list = {{ name = spec_goods_t{w}_{categories()[g]} target = g:{g} }}\n\t\t\t}}\n"
                      for w in range(1, 7)) for g in GOODS]
    shown.append("\t\t\tmarket = {\n\t\t\t\tordered_market_goods = {\n\t\t\t\t\tlimit = { market_goods_sell_orders > 0 }\n"
                 "\t\t\t\t\torder_by = spec_mg_value\n\t\t\t\t\tmin = 0\n\t\t\t\t\tmax = 99\n\t\t\t\t\tcheck_range_bounds = no\n"
                 "\t\t\t\t\tgoods = { save_temporary_scope_as = spec_g }\n\t\t\t\t\troot = {\n"
                 + "".join(f"\t\t\t\t\t\t{'if' if (w, c) == (6, market_tab.CATEGORIES[0]) else 'else_if'} = {{\n\t\t\t\t\t\t\tlimit = {{ is_target_in_variable_list = "
                           f"{{ name = spec_goods_t{w}_{c} target = scope:spec_g }} }}\n"
                           f"\t\t\t\t\t\t\tadd_to_variable_list = {{ name = spec_goods_w{w} target = scope:spec_g }}\n"
                           f"\t\t\t\t\t\t\tadd_to_variable_list = {{ name = spec_goods_w{w}_{c} target = scope:spec_g }}\n\t\t\t\t\t\t}}\n"
                           for w in range(6, 0, -1) for c in market_tab.CATEGORIES)
                 + "\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n"
                 + "".join(f"\t\t\tclear_variable_list = spec_goods_t{w}_{c}\n" for w in range(1, 7) for c in market_tab.CATEGORIES))
    shown.append(charts.interest_script(GOODS))  # needs the word lists just built
    # the tab's own figures: a player's country (its own market tab), or a market owner (any other market's tab shows
    # its owner's figures, for whoever opens it, observers too). Market members that are neither never show them
    goods.append("\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\tOR = {\n\t\t\t\t\t\tis_player = yes\n"
                 "\t\t\t\t\t\tmarket ?= { owner ?= root }\n\t\t\t\t\t}\n\t\t\t\t}\n"
                 + market_tab.ind("".join(shown), 1) + "\t\t\t}\n")
    baskets ="".join(f"\t\t\tset_variable = {{ name = spec_bhype_{b} value = spec_bhype_next_{b} }}\n" for b in UPGRADES)
    # for the journal entry: the three most and two least hyped goods, players only
    rank = []
    for g in GOODS:
        h = f"var:spec_hype_{g}"
        rank.append(
            f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {h} > var:spec_top1_v }}\n"
            "\t\t\t\t\tset_variable = { name = spec_top3 value = var:spec_top2 }\n\t\t\t\t\tset_variable = { name = spec_top3_v value = var:spec_top2_v }\n"
            "\t\t\t\t\tset_variable = { name = spec_top2 value = var:spec_top1 }\n\t\t\t\t\tset_variable = { name = spec_top2_v value = var:spec_top1_v }\n"
            f"\t\t\t\t\tset_variable = {{ name = spec_top1 value = g:{g} }}\n\t\t\t\t\tset_variable = {{ name = spec_top1_v value = {h} }}\n\t\t\t\t}}\n"
            f"\t\t\t\telse_if = {{\n\t\t\t\t\tlimit = {{ {h} > var:spec_top2_v }}\n"
            "\t\t\t\t\tset_variable = { name = spec_top3 value = var:spec_top2 }\n\t\t\t\t\tset_variable = { name = spec_top3_v value = var:spec_top2_v }\n"
            f"\t\t\t\t\tset_variable = {{ name = spec_top2 value = g:{g} }}\n\t\t\t\t\tset_variable = {{ name = spec_top2_v value = {h} }}\n\t\t\t\t}}\n"
            f"\t\t\t\telse_if = {{\n\t\t\t\t\tlimit = {{ {h} > var:spec_top3_v }}\n"
            f"\t\t\t\t\tset_variable = {{ name = spec_top3 value = g:{g} }}\n\t\t\t\t\tset_variable = {{ name = spec_top3_v value = {h} }}\n\t\t\t\t}}\n"
            f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {h} < var:spec_low1_v }}\n"
            "\t\t\t\t\tset_variable = { name = spec_low2 value = var:spec_low1 }\n\t\t\t\t\tset_variable = { name = spec_low2_v value = var:spec_low1_v }\n"
            f"\t\t\t\t\tset_variable = {{ name = spec_low1 value = g:{g} }}\n\t\t\t\t\tset_variable = {{ name = spec_low1_v value = {h} }}\n\t\t\t\t}}\n"
            f"\t\t\t\telse_if = {{\n\t\t\t\t\tlimit = {{ {h} < var:spec_low2_v }}\n"
            f"\t\t\t\t\tset_variable = {{ name = spec_low2 value = g:{g} }}\n\t\t\t\t\tset_variable = {{ name = spec_low2_v value = {h} }}\n\t\t\t\t}}\n")
    first = GOODS[0]
    rank_init = "".join(f"\t\t\t\tset_variable = {{ name = spec_{k} value = g:{first} }}\n\t\t\t\tset_variable = {{ name = spec_{k}_v value = {v} }}\n"
                        for k, v in (("top1", 0), ("top2", 0), ("top3", 0), ("low1", 99), ("low2", 99)))
    log_line = ""
    if log:
        log_line = ("\t\t\tdebug_log = \"SPEC tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString]"
                    " conf=[THIS.Var('spec_conf').GetValue] boom=[THIS.Var('spec_c_boom').GetValue]"
                    " crash=[THIS.Var('spec_c_crash').GetValue] foreign=[THIS.Var('spec_c_foreign').GetValue] turmoil=[THIS.Var('spec_c_turmoil').GetValue]"
                    " panic=[THIS.ScriptValue('spec_in_panic')] pool=[THIS.Var('spec_credit_given').GetValue] je=[THIS.ScriptValue('spec_has_je')]"
                    " stance=[THIS.ScriptValue('spec_stance_value')] debt=[THIS.Var('spec_debt').GetValue]"
                    " rescued=[THIS.ScriptValue('spec_rescued_value')] gdp=[THIS.ScriptValue('spec_rescue_cost')]"
                    " depth=[THIS.ScriptValue('spec_depth')] steady=[THIS.ScriptValue('spec_steady')] fd=[THIS.Var('spec_fd').GetValue]"
                    " ipi=[THIS.ScriptValue('spec_log_ipi')] ip=[THIS.ScriptValue('spec_log_ip')]"
                    " levers=[THIS.ScriptValue('spec_levers_used')] ld=[THIS.ScriptValue('spec_log_ld')] mood=[THIS.Var('spec_c_mood').GetValue] fin=[THIS.ScriptValue('spec_fin_boom')]"
                    " expo=[THIS.Var('spec_exposure').GetValue] expo_raw=[THIS.Var('spec_expo_raw').GetValue] nrisk=[THIS.Var('spec_n_risk').GetValue]"
                    " risktop=[THIS.Var('spec_risk_top').GetValue] wsum=[THIS.ScriptValue('spec_log_wsum')]"
                    " heat=[THIS.ScriptValue('spec_log_heat')] burst=[THIS.ScriptValue('spec_log_burst')]"
                    " bankbooms=[THIS.ScriptValue('spec_exp_booms')] restrain=[THIS.Var('spec_c_restrain').GetValue]" + leverage.LOG + cycle.LOG + centres.LOG +
                    " end1=[THIS.Var('spec_n_end_1').GetValue] end2=[THIS.Var('spec_n_end_2').GetValue] end3=[THIS.Var('spec_n_end_3').GetValue]"
                    # every pressure on confidence this month (the tab's own list), 0 when unset, for the Stats tab
                    + "".join(f" d_{n}=[THIS.ScriptValue('spec_log_d_{n}')]" for n, _ in market_tab.DRIVERS) +
                    # last: these are only set where a player can see the tab, and an unset one ends the line
                    " top1=[THIS.Var('spec_top1').GetGoods.GetNameNoFormatting] hot=[THIS.Var('spec_heat_boom').GetValue]\"\n")
        log_line += ("\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\tc:GBR ?= this\n\t\t\t\t\tNOT = { has_variable = spec_own_year }\n\t\t\t\t}\n"
                     "\t\t\t\tset_variable = { name = spec_own_year days = 360 }\n\t\t\t\tspec_log_owned = yes\n\t\t\t}\n")
        log_line += diplomacy.war_log()
    counters = "".join(f"\t\t\tset_variable = {{ name = spec_{k} value = 0 }}\n" for k in
                       ("c_boom", "c_crash", "c_tight", "c_foreign", "c_world", "credit_given", "n_boom", "n_end_1", "n_end_2", "n_end_3", "c_restrain")) \
        + "\t\t\tremove_variable = spec_crash_top\n"  # this month's largest ending only: its days = 28 can outlive a 28-day February
    # in a log build, a line at game start that proves which build loaded (tools/observe.py checks for it); only an
    # on_actions list on the vanilla on_action, never an effect block, which would replace vanilla's
    marker = ""
    if log:
        import datetime
        import hashlib
        tj = Path(__file__).resolve().parent / "tuning.json"
        # which balance values the run used: the tuner's overrides, or none
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + " tuning " + (
            hashlib.md5(tj.read_bytes()).hexdigest()[:8] if tj.exists() else "defaults")
        marker = f"""on_game_started_after_lobby = {{
	on_actions = {{ spec_init_marker }}
}}

spec_init_marker = {{
	effect = {{
		debug_log = "SPEC_MARKETS init OK build {stamp}"
	}}
}}

"""
    return marker + f"""on_monthly_pulse_country = {{
	on_actions = {{ spec_monthly }}
}}

spec_monthly = {{
	effect = {{
		# leaving the market economy switches the system off and clears it; coming back starts fresh
		if = {{
			limit = {{
				NOT = {{ spec_law_mult > 0 }}
				OR = {{ has_variable = spec_conf has_modifier = spec_panic_relief }}
			}}
			spec_shut_down = yes
		}}
		else_if = {{
			limit = {{ spec_law_mult > 0 }}
			if = {{
				limit = {{ NOT = {{ has_variable = spec_conf }} }}
				set_variable = {{ name = spec_conf value = {CONF_START} }}
				set_variable = {{ name = spec_stance value = 0 }}
			}}
			if = {{
				limit = {{ NOT = {{ has_variable = spec_debt }} }}
				set_variable = {{ name = spec_debt value = 0 }}
			}}
{counters}{vanilla_ties.MONTHLY}			set_variable = {{ name = spec_mv_total value = spec_market_value }}
{"".join(goods)}{baskets}			if = {{
				limit = {{ var:spec_c_boom > {CONF_BOOM_MAX} }}
				set_variable = {{ name = spec_c_boom value = {CONF_BOOM_MAX} }}
			}}
			# scaled first, then capped: capping first let a deep market at high confidence lose 80 in a month
			change_variable = {{ name = spec_c_crash multiply = spec_crash_scale }}
			change_variable = {{ name = spec_c_restrain multiply = spec_crash_scale }}
			if = {{
				limit = {{ var:spec_c_crash < -{CONF_CRASH_MAX} }}
				set_variable = {{ name = spec_c_crash value = -{CONF_CRASH_MAX} }}
			}}
			set_local_variable = {{ name = spec_boom_floor value = {{ value = -{CONF_CRASH_MAX} subtract = var:spec_c_crash }} }}
			if = {{
				limit = {{ var:spec_c_restrain < local_var:spec_boom_floor }}
				set_variable = {{ name = spec_c_restrain value = local_var:spec_boom_floor }}
			}}
			change_variable = {{ name = spec_c_boom multiply = spec_steady }}
			change_variable = {{ name = spec_c_boom multiply = spec_fin_boom }}
			change_variable = {{ name = spec_c_boom multiply = spec_boom_rule }}
			# no booms during a panic
			if = {{
				limit = {{ has_variable = spec_panic }}
				set_variable = {{ name = spec_c_boom value = 0 }}
			}}
			set_variable = {{ name = spec_c_turmoil value = 0 }}
			remove_variable = spec_tm_play
			remove_variable = spec_tm_default
			remove_variable = spec_tm_revolution
{diplomacy.WAR_MONTHLY}			# a play short of war; a war already counts, so not both
			if = {{
				limit = {{
					var:spec_war_n = 0
					is_active_in_diplomatic_play = yes
				}}
				change_variable = {{ name = spec_c_turmoil add = -{PLAY_TURMOIL} }}
				set_variable = {{ name = spec_tm_play value = -{PLAY_TURMOIL} }}
			}}
			if = {{
				limit = {{ in_default = yes }}
				change_variable = {{ name = spec_c_turmoil add = -5 }}
				set_variable = {{ name = spec_tm_default value = -5 }}
			}}
			if = {{
				limit = {{ has_revolution = yes }}
				change_variable = {{ name = spec_c_turmoil add = -2 }}
				set_variable = {{ name = spec_tm_revolution value = -2 }}
			}}
{economy.BROKE_MONTHLY}			set_variable = {{ name = spec_c_debt value = spec_debt_drag }}
{economy.MONTHLY}			# a panic in a linked country, passed on by spec_catch_panic since the last update
			if = {{
				limit = {{ has_variable = spec_foreign_pending }}
				set_variable = {{ name = spec_c_foreign value = {{ value = var:spec_foreign_pending multiply = -1 }} }}
				if = {{
					limit = {{ var:spec_foreign_pending >= {CAUGHT_FROM} }}
					set_variable = {{ name = spec_caught days = {CAUGHT_DAYS} }}
				}}
				remove_variable = spec_foreign_pending
			}}
{diplomacy.MONTHLY}{''.join(f'			remove_variable = spec_fs{n}{chr(10)}			if = {{{chr(10)}				limit = {{ has_variable = spec_fp{n} }}{chr(10)}'f'				set_variable = {{ name = spec_fs{n} value = var:spec_fp{n} }}{chr(10)}				remove_variable = spec_fp{n}{chr(10)}			}}{chr(10)}' for n in range(1, SOURCES + 1))}{depression.MONTHLY}			# market mood: a random shift that fades over some months (fixed_range as in vanilla's krakatoa_events.txt)
			if = {{
				limit = {{ NOT = {{ has_variable = spec_c_mood }} }}
				set_variable = {{ name = spec_c_mood value = 0 }}
			}}
			change_variable = {{ name = spec_c_mood multiply = {MOOD_KEEP:g} }}
			set_variable = {{ name = spec_mood_shift value = {{ fixed_range = {{ min = 0 max = {2 * MOOD_SHOCK:g} }} }} }}
			set_variable = {{ name = spec_mood_shift value = spec_mood_roll }}
			change_variable = {{ name = spec_mood_shift multiply = spec_mood_scale }}
{centres.LEAN}			change_variable = {{ name = spec_c_mood add = var:spec_mood_shift }}
			set_variable = {{ name = spec_c_recover value = spec_conf_recover }}
			if = {{
				limit = {{ spec_stance_value = -1 }}
				set_variable = {{ name = spec_c_tight value = spec_tight_pull }}
			}}
			set_variable = {{ name = spec_c_total value = {{ value = spec_conf_next subtract = var:spec_conf }} }}
			# for the tab: what the 0 to 100 limit took off, and no one-off jumps yet this month
			set_variable = {{ name = spec_c_limit value = {{ value = spec_conf_next subtract = spec_conf_pre subtract = var:spec_c_tight }} }}
			remove_variable = spec_c_rescue
			remove_variable = spec_c_warend
			remove_variable = spec_c_burst
			remove_variable = spec_c_caution
{leverage.CLEAR_DROP}			set_local_variable = {{ name = spec_conf_was value = var:spec_conf }}
			set_variable = {{ name = spec_conf value = spec_conf_next }}
			if = {{
				limit = {{
					is_player = yes
					NOT = {{ has_variable = spec_panic }}
					local_var:spec_conf_was >= {leverage.near_limit(PANIC_NEAR)}
					var:spec_conf < {leverage.near_limit(PANIC_NEAR)}
					var:spec_conf >= {leverage.panic_limit(PANIC)}
				}}
				post_notification = spec_near_panic
			}}
			# the card's pressure chips: this month's three biggest drivers, where a player can see the tab
			if = {{
				limit = {{
					OR = {{
						is_player = yes
						market ?= {{ owner ?= root }}
					}}
				}}
				spec_pick_driver = yes
{"".join(f"				if = {{ limit = {{ has_variable = spec_hist{n - 1} }} set_variable = {{ name = spec_hist{n} value = var:spec_hist{n - 1} }} }}{chr(10)}" for n in range(market_tab.HISTORY, 1, -1))}				set_variable = {{ name = spec_hist1 value = var:spec_conf }}
			}}
			spec_update_band = yes
			spec_update_companies = yes

			# credit: high confidence pours money into the investment pool; it runs off slowly, repaid out of the pool
			# as far as the pool can, and what the pool cannot cover this month is written off
			set_local_variable = {{ name = spec_repaid value = spec_credit_repay }}
			set_local_variable = {{ name = spec_runoff value = spec_credit_runoff }}
			add_investment_pool = {{ value = local_var:spec_repaid multiply = -1 }}
{leverage.ON_REPAY}			change_variable = {{ name = spec_debt subtract = local_var:spec_runoff }}
{exposure.clear(GOODS)}			set_local_variable = {{ name = spec_lent value = 0 }}  # leverage.MONTHLY: no new loans, no bigger bonus
			if = {{
				limit = {{
					var:spec_conf > {CREDIT_FROM}
					NOT = {{ has_variable = spec_panic }}
					NOT = {{ spec_stance_value = -1 }}
{depression.NO_CREDIT}{leverage.NO_CREDIT}				}}
				set_variable = {{ name = spec_credit_given value = spec_credit }}
				set_local_variable = {{ name = spec_lent value = var:spec_credit_given }}
				add_investment_pool = var:spec_credit_given
{exposure.lend(GOODS)}				change_variable = {{ name = spec_debt add = var:spec_credit_given }}
			}}
{cycle.monthly()}{leverage.MONTHLY}
			# Leverage History and the bank chart's goods: after this month's repayment and lending, so they match the Leverage bar and the shares shown
			if = {{
				limit = {{
					OR = {{
						is_player = yes
						market ?= {{ owner ?= root }}
					}}
				}}
{charts.history_shift()}{charts.script(GOODS, chr(9) * 4)}			}}
			# mania warning, once per boom
			if = {{
				limit = {{
					var:spec_conf >= {MANIA}
					NOT = {{ has_variable = spec_mania }}
				}}
				set_variable = spec_mania
{leverage.FEVER_ROLL}				# paper fortunes: investors credit the government, until the panic takes it back
				add_loyalists = {{ value = 0.05 pop_type = capitalists }}
				add_loyalists = {{ value = 0.02 pop_type = shopkeepers }}
				# AI countries take it too, choosing by temperament
				trigger_event = {{ id = spec_markets.1 popup = yes }}
				spec_notify_tied = {{ TYPE = spec_tied_mania }}
			}}
			# the bubble: confidence above 70 summed over the boom's months, bursting when confidence falls below BURST_BELOW
			if = {{
				limit = {{
					var:spec_conf >= spec_heat_from
					has_technology_researched = stock_exchange
				}}
				if = {{
					limit = {{ NOT = {{ has_variable = spec_heat }} }}
					set_variable = {{ name = spec_heat value = 0 }}
				}}
				change_variable = {{ name = spec_heat add = {{ value = var:spec_conf subtract = 70 multiply = spec_reform_heat }} }}
			}}
			# a soft landing: between BURST_BELOW and spec_heat_from the bubble cools instead of waiting to burst
			else_if = {{
				limit = {{
					has_variable = spec_heat
					var:spec_conf >= {BURST_BELOW}
				}}
				change_variable = {{ name = spec_heat multiply = {HEAT_COOL} }}
				if = {{
					limit = {{ var:spec_heat < 1 }}
					remove_variable = spec_heat
				}}
			}}
			if = {{
				limit = {{
					has_variable = spec_mania
					var:spec_conf < {MANIA_RESET}
				}}
				remove_variable = spec_mania
			}}
			if = {{
				limit = {{
					has_variable = spec_heat
					var:spec_conf < {BURST_BELOW}
				}}
				# a one-off jump, shown in the tab until the next monthly update
				set_variable = {{ name = spec_c_burst value = {{ value = var:spec_heat multiply = spec_burst_per_heat multiply = -1 min = spec_burst_floor }} }}
				set_variable = {{ name = spec_conf value = {{ value = var:spec_conf add = var:spec_c_burst min = 0 }} }}
				change_variable = {{ name = spec_c_total add = var:spec_c_burst }}
				remove_variable = spec_heat
				if = {{
					limit = {{ is_player = yes }}
					post_notification = spec_bubble_burst
				}}
				spec_pick_driver = yes
				spec_update_band = yes
			}}
			spec_update_movements = yes

			spec_refresh_credit_igs = yes

			# countdowns in months so the tab can show them
			if = {{
				limit = {{ has_variable = spec_stance_cooldown }}
				change_variable = {{ name = spec_stance_cooldown add = -1 }}
				if = {{
					limit = {{ var:spec_stance_cooldown <= 0 }}
					remove_variable = spec_stance_cooldown
				}}
			}}
			if = {{
				limit = {{ has_variable = spec_panic_cooldown }}
				change_variable = {{ name = spec_panic_cooldown add = -1 }}
				if = {{
					limit = {{ var:spec_panic_cooldown <= 0 }}
					remove_variable = spec_panic_cooldown
				}}
			}}
			if = {{
				limit = {{ has_variable = spec_panic }}
				if = {{
					limit = {{ NOT = {{ has_variable = spec_panic_elapsed }} }}
					set_variable = {{ name = spec_panic_elapsed value = spec_panic_run }}
				}}
				change_variable = {{ name = spec_panic_elapsed add = 1 }}
				change_variable = {{ name = spec_panic add = -1 }}
				if = {{
					limit = {{
						OR = {{
							var:spec_panic <= 0
							AND = {{
								var:spec_conf >= {PANIC_ENDS_AT}
								spec_panic_run >= {PANIC_MIN_MONTHS}
							}}
						}}
					}}
					spec_end_panic = yes
				}}
			}}
			else_if = {{
				limit = {{
					var:spec_conf < {leverage.panic_limit(PANIC)}
					NOT = {{ has_variable = spec_panic_cooldown }}
				}}
				spec_start_panic = yes
{leverage.AFTER_PANIC}			}}
{journal.MONTHLY}
			if = {{
				limit = {{
					is_player = yes
					NOT = {{ has_variable = spec_je_added }}
				}}
				# has_journal_entry misses an entry that is shown but not active, so remember adding it
				set_variable = spec_je_added
				add_journal_entry = {{ type = je_spec_markets }}
			}}
{leverage.FEVER_END}			# AI countries use the same tools by rule: cool a mania, stop cooling once it has passed,
			# loosen when wary, and stop loosening once confidence is back
			if = {{
				limit = {{ is_player = no }}
				# thresholds move with temperament and the interest groups in government (credit_ai.py)
				spec_ai_temper = yes
				if = {{
					limit = {{
						{leverage.ai_tight("var:spec_conf > spec_ai_tight_at")}
						spec_can_stance_tight = yes
					}}
					spec_stance_to_tight = yes
				}}
				else_if = {{
					limit = {{
						spec_stance_value = -1
						var:spec_conf < spec_ai_untight_at
{leverage.AI_BACK}						spec_can_stance_normal = yes
					}}
					spec_stance_to_normal = yes
				}}
				else_if = {{
					limit = {{
						spec_stance_value = 0
						var:spec_conf < spec_ai_loose_at
{leverage.AI_BACK}						NOT = {{ has_variable = spec_panic }}
						spec_can_stance_loose = yes
					}}
					spec_stance_to_loose = yes
				}}
				else_if = {{
					limit = {{
						spec_stance_value = 1
						OR = {{
							var:spec_conf >= spec_ai_unloose_at
							has_variable = spec_panic
						}}
						spec_can_stance_normal = yes
					}}
					spec_stance_to_normal = yes
				}}
				if = {{
					limit = {{
						spec_can_rescue = yes
						# the AI pays only from money it has, never by borrowing
						in_default = no
						scaled_debt < 0.6
						gold_reserves >= spec_rescue_cost
						NOT = {{ spec_nearly_broke = yes }}
					}}
					if = {{
						limit = {{ var:spec_panic > spec_rescue_months }}
						spec_ai_rescue_roll = yes
					}}
				}}
{leverage.AI_BAILOUT}{journal.MONTHLY_AI}{levers.ai_block(GOODS, HOT_HYPE, RISING_HYPE, COOLING_HYPE)}			}}
			# for everyone: the levers' Authority cost moves with each good's share of the market, their money with its output
			spec_update_levers = yes

			je:je_spec_markets ?= {{
				set_bar_progress = {{ name = spec_confidence_bar value = root.var:spec_conf }}
{journal.BARS}			}}

			# the most and least favored goods, for the tab and the journal entry
			if = {{
				limit = {{ is_player = yes }}
{rank_init}{"".join(rank)}				spec_find_risk_src = yes
			}}
{log_line}		}}
	}}
}}
"""


def stance_effects():
    out = [f"spec_stance_to_{k} = {{\n\tset_variable = {{ name = spec_stance value = {n} }}\n\tspec_set_stance = yes\n}}\n"
           for k, n in STANCES]
    return "\n".join(out)


def effects(log=False):
    # a log build lists who owns what when a panic starts and, for Britain, each year, to calibrate the ownership tie
    owned_log, owned_log_def = "", ""
    if log:
        owned_log = "\tspec_log_owned = yes\n"
        owned_log_def = ("spec_log_owned = {\n\tsave_scope_as = spec_tie_src\n\tevery_country = {\n\t\tlimit = {\n\t\t\tNOT = { this = root }\n\t\t\tspec_owned_share >= 0.02\n\t\t}\n"
                         "\t\tset_variable = { name = spec_own_log value = spec_owned_share }\n"
                         "\t\tdebug_log = \"SPECOWN tag=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString] share=[THIS.Var('spec_own_log').GetValue]\"\n"
                         "\t\tremove_variable = spec_own_log\n\t}\n}\n\n")
    clear = "".join(f"\tremove_variable = {v}\n" for v in state_vars())
    clear += "".join(f"\tclear_variable_list = {l}\n" for l in charts.LISTS)
    clear += "".join(f"\tclear_variable_list = spec_goods_w{w}\n" + "".join(f"\tclear_variable_list = spec_goods_w{w}_{c}\n" for c in market_tab.CATEGORIES)
                     for w in range(1, 7))  # the goods board's lists
    clear += "\tspec_update_levers = yes\n"  # levers are cleared above, so this removes their modifiers
    clear += "\tspec_update_companies = yes\n"  # and the company modifiers

    def in_band(lo, hi):
        return " ".join(([f"var:spec_conf >= {lo}"] if lo > 0 else []) + ([f"var:spec_conf < {hi}"] if hi < 100 else []))
    bands = [(f"spec_conf_{t}", lo, hi, "") for t, lo, hi, *_ in market_tab.TIERS if t in BAND_INVEST]
    # during a panic its own modifier carries the investment loss, so the panic band swaps to one without it
    bands = [b for m, lo, hi, _ in bands for b in ([(m, lo, hi, "NOT = { has_modifier = spec_panic }"),
                                                    (f"{m}_held", lo, hi, "has_modifier = spec_panic")]
                                                   if m == "spec_conf_panic" else [(m, lo, hi, "")])]
    band = "".join(f"""	if = {{
		limit = {{ NOT = {{ has_modifier = {m} }} {in_band(lo, hi)} {cond} }}
		add_modifier = {{ name = {m} }}
	}}
	else_if = {{
		limit = {{ has_modifier = {m} NOT = {{ AND = {{ {in_band(lo, hi)} {cond} }} }} }}
		remove_modifier = {m}
	}}
""" for m, lo, hi, cond in bands)
    unband = "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {m} }}\n\t\tremove_modifier = {m}\n\t}}\n" for m, *_ in bands)
    return f"""# the investment modifier of the confidence band the country is in, and no other
spec_update_band = {{
{band}}}

{owned_log_def}spec_start_panic = {{
	# months left, counted down monthly; the one clock for the panic
	set_variable = {{ name = spec_panic value = spec_panic_months_trust }}
	set_variable = {{ name = spec_panic_len value = var:spec_panic }}
	set_variable = {{ name = spec_panic_elapsed value = 0 }}
{leverage.on_panic(PANIC)}{depression.ON_PANIC}	add_modifier = {{ name = spec_panic }}
	add_modifier = {{
		name = spec_panic_crunch
		multiplier = spec_alloc_half
	}}
	add_modifier = {{
		name = spec_panic_relief
		multiplier = spec_panic_relief_week
	}}
	spec_update_band = yes
	# ruined investors turn on the government; workers radicalize through vanilla's loss of living standards
	add_radicals = {{ value = 0.1 pop_type = capitalists }}
	add_radicals = {{ value = 0.05 pop_type = aristocrats }}
	add_radicals = {{ value = 0.05 pop_type = shopkeepers }}
	# banks call in part of the credit they lent
	set_variable = {{ name = spec_clawed value = spec_clawback }}
	add_investment_pool = {{ value = var:spec_clawed multiply = -1 }}
	change_variable = {{ name = spec_debt subtract = var:spec_clawed }}
	set_variable = {{ name = spec_centre_calm value = 0 }}  # centres.py: a rescued panic can end before its monthly pass sees it
{centres.PANIC}{leverage.after_clawback(CLAWBACK)}{centres.PLEDGE_RESCUE}	trigger_event = {{ id = spec_markets.2 popup = yes }}
	# contagion: countries tied to this one lose confidence, the closer the tie and the bigger this economy
	# compared with theirs, the more
	set_variable = {{ name = spec_src_gdp value = gdp }}
	if = {{
		limit = {{ NOT = {{ has_variable = spec_caught }} }}
		spec_every_tied = {{ EFFECT = spec_catch_panic }}
		spec_notify_tied = {{ TYPE = spec_tied_panic }}
	}}
	spec_capital_flight = yes
	spec_panic_movements = yes
{owned_log}}}

# runs $EFFECT$ = {{ WEIGHT = tie weight }} on each country tied to root, once per tie, so a country with two ties
# gets it twice. scope:spec_tie_src is the country whose ownership spec_owned_share measures
spec_every_tied = {{
	root = {{ save_scope_as = spec_tie_src }}
	market ?= {{
		every_scope_country = {{
			limit = {{ NOT = {{ this = root }} }}
			$EFFECT$ = {{ WEIGHT = spec_tie_market }}
		}}
	}}
	every_subject_or_below = {{
		$EFFECT$ = {{ WEIGHT = {LINKS['subject']} }}
	}}
	every_overlord_or_above = {{
		$EFFECT$ = {{ WEIGHT = {LINKS['subject']} }}
	}}
	every_country = {{
		limit = {{
			NOT = {{ this = root }}
			any_scope_treaty = {{
				binds = root
				any_scope_article = {{ has_type = foreign_investment_rights }}
			}}
		}}
		$EFFECT$ = {{ WEIGHT = spec_tie_investment }}
	}}
	every_country = {{
		limit = {{
			NOT = {{ this = root }}
			spec_owned_share >= {OWNED_FROM}
		}}
		$EFFECT$ = {{ WEIGHT = spec_tie_owned }}
	}}
	every_market = {{
		limit = {{
			NOT = {{ this = root.market }}
			market_trade_reliance = {{ target = root.market value > {TRADE_RELIANCE} }}
		}}
		every_scope_country = {{
			limit = {{ spec_no_embargo_with_root = yes }}
			$EFFECT$ = {{ WEIGHT = spec_tie_trade }}
		}}
	}}
}}

# on a country tied to root, which has just panicked: keep the biggest hit until its next monthly update
spec_catch_panic = {{
	if = {{
		limit = {{
			has_variable = spec_conf
			gdp > 0
		}}
		set_variable = {{
			name = spec_foreign_hit
			value = {{
				value = root.var:spec_src_gdp
				divide = gdp
				max = 1
				multiply = {CONTAGION}
				multiply = $WEIGHT$
				multiply = root.spec_reach
				multiply = spec_foreign_loss_mult
			}}
		}}
		if = {{
			limit = {{
				OR = {{
					NOT = {{ has_variable = spec_foreign_pending }}
					var:spec_foreign_hit > var:spec_foreign_pending
				}}
			}}
			set_variable = {{ name = spec_foreign_pending value = var:spec_foreign_hit }}
			set_variable = {{ name = spec_foreign_src value = root }}
			# the largest hit's parts, for the calculator
			set_variable = {{ name = spec_fh_size value = {{ value = root.var:spec_src_gdp divide = gdp max = 1 }} }}
			set_variable = {{ name = spec_fh_tie value = $WEIGHT$ }}
			set_variable = {{ name = spec_fh_reach value = root.spec_reach }}
		}}
{diplomacy.NOTE_SRC}
		remove_variable = spec_foreign_hit
	}}
}}

# for the tab, on a player: the tied country whose panic would cost the most, among those near one (Wary and
# below) or in a mania. The ties mirror spec_start_panic's, seen from the country that would catch it.
spec_find_risk_src = {{
	remove_variable = spec_risk_src
	remove_variable = spec_risk_src_tie
	set_variable = {{ name = spec_risk_src_hit value = 0 }}
	market ?= {{
		every_scope_country = {{
			limit = {{ NOT = {{ this = root }} }}
			spec_rate_risk_src = {{ WEIGHT = root.spec_tie_market TIE = 1 }}
		}}
	}}
	every_subject_or_below = {{
		spec_rate_risk_src = {{ WEIGHT = {LINKS['subject']} TIE = 2 }}
	}}
	every_overlord_or_above = {{
		spec_rate_risk_src = {{ WEIGHT = {LINKS['subject']} TIE = 2 }}
	}}
	every_country = {{
		limit = {{
			NOT = {{ this = root }}
			any_scope_treaty = {{
				binds = root
				any_scope_article = {{ has_type = foreign_investment_rights }}
			}}
		}}
		spec_rate_risk_src = {{ WEIGHT = root.spec_tie_investment TIE = 3 }}
	}}
	every_country = {{
		limit = {{ NOT = {{ this = root }} }}
		save_scope_as = spec_tie_src
		if = {{
			limit = {{ root = {{ spec_owned_share >= {OWNED_FROM} }} }}
			spec_rate_risk_src = {{ WEIGHT = root.spec_tie_owned TIE = 5 }}
		}}
	}}
	every_market = {{
		limit = {{
			NOT = {{ this = root.market }}
			root.market = {{ market_trade_reliance = {{ target = prev value > {TRADE_RELIANCE} }} }}
		}}
		every_scope_country = {{
			limit = {{ spec_no_embargo_with_root = yes }}
			spec_rate_risk_src = {{ WEIGHT = root.spec_tie_trade TIE = 4 }}
		}}
	}}
	if = {{
		limit = {{ NOT = {{ has_variable = spec_risk_src }} }}
		remove_variable = spec_risk_src_hit
	}}
}}

# on a country tied to root: keep it as root's outside risk if its panic would hit root hardest so far
spec_rate_risk_src = {{
	if = {{
		limit = {{
			has_variable = spec_conf
			NOT = {{ has_variable = spec_panic }}
			NOT = {{ has_variable = spec_panic_cooldown }}
			OR = {{
				var:spec_conf < 40
				var:spec_conf >= {MANIA}
			}}
			root.gdp > 0
		}}
		set_variable = {{
			name = spec_risk_try
			value = {{
				value = gdp
				divide = root.gdp
				max = 1
				multiply = {CONTAGION}
				multiply = $WEIGHT$
				multiply = spec_reach
			}}
		}}
		if = {{
			limit = {{ var:spec_risk_try > root.var:spec_risk_src_hit }}
			# its parts, for the calculator, read here: the tie's weight belongs to this country
			set_variable = {{ name = spec_risk_w value = $WEIGHT$ }}
			set_variable = {{ name = spec_risk_r value = spec_reach }}
			set_variable = {{ name = spec_risk_s value = {{ value = gdp divide = root.gdp max = 1 }} }}
			root = {{
				set_variable = {{ name = spec_risk_src_hit value = prev.var:spec_risk_try }}
				set_variable = {{ name = spec_risk_src value = prev }}
				set_variable = {{ name = spec_risk_src_tie value = $TIE$ }}
				set_variable = {{ name = spec_risk_src_w value = prev.var:spec_risk_w }}
				set_variable = {{ name = spec_risk_src_reach value = prev.var:spec_risk_r }}
				set_variable = {{ name = spec_risk_src_size value = prev.var:spec_risk_s }}
			}}
			remove_variable = spec_risk_w
			remove_variable = spec_risk_r
			remove_variable = spec_risk_s
		}}
		remove_variable = spec_risk_try
	}}
}}

# the card's pressure chips (market_tab.DRIVERS), before the effects that call it
{market_tab.pick_driver()}
spec_end_panic = {{
	if = {{
		limit = {{ is_player = yes }}
		post_notification = spec_panic_over
	}}
{cycle.panic_over()}{centres.PANIC_OVER}	remove_variable = spec_panic
	remove_variable = spec_panic_len
	remove_variable = spec_panic_elapsed
	remove_variable = spec_rescued
	remove_modifier = spec_panic
	remove_modifier = spec_panic_crunch
	remove_modifier = spec_panic_relief
	set_variable = {{ name = spec_panic_cooldown value = {PANIC_COOLDOWN} }}
	spec_update_band = yes
}}

# the bank rescue, once per panic, from the tab, the journal entry or the panic event
spec_rescue = {{
{stories.RESCUE_PAY}{stories.BAILOUT_IGS}
	# the tab's button and the events say what this does in words (SPEC_RESCUE_TT): the swap is not listed
	hidden_effect = {{
		# the Industrialists approved of leaving the market alone (the panic event's first option): a rescue ends that
		ig:ig_industrialists ?= {{ remove_modifier = spec_market_left_alone }}
		remove_modifier = spec_panic
		remove_modifier = spec_panic_crunch
		add_modifier = {{
			name = spec_panic
			multiplier = 0.5
		}}
		add_modifier = {{
			name = spec_panic_crunch
			multiplier = spec_alloc_quarter
		}}
	}}
	set_variable = {{ name = spec_panic value = {{ value = var:spec_panic max = spec_rescue_months }} }}
	# the jump, after the 100 limit, shown in the tab until the next monthly update
	set_variable = {{ name = spec_c_rescue value = {{ value = var:spec_conf multiply = -1 }} }}
	set_variable = {{ name = spec_conf value = {{ value = var:spec_conf add = {RESCUE_CONF} max = 100 }} }}
	change_variable = {{ name = spec_c_rescue add = var:spec_conf }}
	change_variable = {{ name = spec_c_total add = var:spec_c_rescue }}
	set_variable = spec_rescued
{cycle.rescued()}	spec_pick_driver = yes
	spec_update_band = yes
}}


{leverage.bailout_effect(stories.BAILOUT_IGS)}# the mania event's options: confidence down by AMOUNT, never below 0, shown in the tab as this month's change
spec_cool_conf = {{
	# Pending mania and pledge responses must not restart markets after a law change.
	if = {{
		limit = {{ has_variable = spec_conf spec_law_mult > 0 }}
		if = {{
			limit = {{ NOT = {{ has_variable = spec_c_total }} }}
			set_variable = {{ name = spec_c_total value = 0 }}
		}}
		set_variable = {{ name = spec_c_caution value = {{ value = var:spec_conf max = $AMOUNT$ multiply = -1 }} }}
		change_variable = {{ name = spec_c_total add = var:spec_c_caution }}
		set_variable = {{ name = spec_conf value = {{ value = var:spec_conf subtract = $AMOUNT$ min = 0 }} }}
		spec_pick_driver = yes
		spec_update_band = yes
	}}
}}

spec_set_stance = {{
	set_variable = {{ name = spec_stance_cooldown value = {STANCE_COOLDOWN} }}
	# the stance buttons' tooltips give the approval in words (credit_ai.ig_lines); hidden here so it is not listed twice
	hidden_effect = {{
		spec_update_credit_igs = yes
	}}
}}

{stance_effects()}
spec_shut_down = {{
	spec_ld_leave = yes
	remove_modifier = spec_panic_relief
{'\tspec_exch_clear = yes' if centres.ON else ''}
	if = {{
		limit = {{ has_modifier = spec_panic }}
		remove_modifier = spec_panic
	}}
	if = {{
		limit = {{ has_modifier = spec_panic_crunch }}
		remove_modifier = spec_panic_crunch
	}}
{leverage.SHUT_DOWN}{cycle.shut_down()}{unband}	spec_remove_credit_igs = yes
{clear}}}
"""


def triggers():
    out = [f"""spec_can_stance_{k} = {{
	has_technology_researched = central_banking
	custom_tooltip = {{
		text = spec_stance_current_tt
		NOT = {{ spec_stance_value = {n} }}
	}}
	custom_tooltip = {{
		text = spec_stance_cooldown_tt
		NOT = {{ has_variable = spec_stance_cooldown }}
	}}
}}
""" for k, n in STANCES]
    out.append("""spec_can_rescue = {
	custom_tooltip = {
		text = spec_suspend_panic_tt
		has_variable = spec_panic
	}
	has_technology_researched = banking
	custom_tooltip = {
		text = spec_rescued_tt
		NOT = { has_variable = spec_rescued }
	}
}
""")
    out.append(leverage.BAILOUT_TRIGGER)
    return "\n".join(out)


def sguis():
    out = [f"""spec_sgui_{k} = {{
	scope = country
	is_valid = {{ spec_can_stance_{k} = yes }}
	effect = {{ spec_stance_to_{k} = yes }}
}}
""" for k, _ in STANCES]
    out.append("""spec_sgui_rescue = {
	scope = country
	is_valid = { spec_can_rescue = yes }
	effect = { spec_rescue = yes }
}
""")
    out.append(leverage.BAILOUT_SGUI)
    return "\n".join(out)


def bar():
    return f"""spec_confidence_bar = {{
	name = "spec_confidence_bar"
	desc = "spec_confidence_bar_desc"
	start_value = {CONF_START}
	min_value = 0
	max_value = 100
	progress_texture = "gfx/interface/progressbar/progressbar_gold.dds"
	background_texture = "gfx/interface/progressbar/progressbar_bad.dds"
	glow_texture = "gfx/interface/progressbar/progressbar_gold_glow.dds"
	glow_line_texture = "gfx/interface/progressbar/progressbar_gold_glow_line.dds"
	marker = yes
	# this month's change by driver, for the tooltip (journal.conf_progress)
	monthly_progress = {{
{journal.conf_progress(market_tab.DRIVERS)}	}}
}}
"""


def modifiers():
    timed = "".join(f"{k} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/{icon}.dds\n"
                    f"\tinterest_group_approval_add = {n}\n}}\n\n" for k, icon, n, _ in EVENT_MODIFIERS)
    bands = "".join(f"spec_conf_{t} = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_coins_{'positive' if m > 0 or BAND_RATE.get(t, 0) < 0 else 'negative'}.dds\n"
                    + "".join(f"\tstate_{c}_investment_pool_efficiency_mult = {m:g}\n" for c in ("capitalists", "aristocrats", "shopkeepers") if m)
                    + (f"\tcountry_loan_interest_rate_mult = {BAND_RATE[t]:g}\n" if t in BAND_RATE else "")
                    + (f"\tstate_trade_quantity_mult = {BAND_TRADE[t]:g}\n" if t in BAND_TRADE else "")
                    + companies.band(t) + "}\n\n" for t, m in BAND_INVEST.items())
    # the panic band while a panic is on: spec_panic carries the investment loss instead
    bands += (f"spec_conf_panic_held = {{\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds\n"
              f"\tcountry_loan_interest_rate_mult = {BAND_RATE['panic']:g}\n"
              f"\tstate_trade_quantity_mult = {BAND_TRADE['panic']:g}\n{companies.band('panic')}}}\n\n")
    return f"""# the confidence bands, one at a time from spec_update_band; a panic's own modifier applies on top
{bands}spec_panic = {{
	icon = {icons.path('mod_panic')}
	state_capitalists_investment_pool_efficiency_mult = -0.4
	state_aristocrats_investment_pool_efficiency_mult = -0.4
	state_shopkeepers_investment_pool_efficiency_mult = -0.4
	# the investing classes' interest groups blame the government; a rescue halves this with the rest
	interest_group_ig_industrialists_approval_add = -2
	interest_group_ig_petty_bourgeoisie_approval_add = -2
	building_throughput_add = {PANIC_THROUGHPUT:g}
	state_tax_collection_mult = {PANIC_TAX:g}
{companies.PANIC}}}

# relief for the jobless while a panic lasts: applied with the week's cost as its multiplier (spec_panic_relief_week)
spec_panic_relief = {{
	icon = {icons.path('mod_panic')}
	country_expenses_add = 1
}}

{cycle.modifiers()}{leverage.modifiers(icons.path('mod_loose'), icons.path('mod_crunch'))}# applied with half the law's allocation as its multiplier, so a panic halves private construction
spec_panic_crunch = {{
	icon = {icons.path('mod_crunch')}
	country_private_construction_allocation_mult = -1
}}

spec_loose_credit = {{
	icon = {icons.path('mod_loose')}
	interest_group_approval_add = {credit_ai.IG_APPROVAL}
}}

# both on the interest group preferring that stance, and at -1 on the one preferring the other
spec_tight_credit = {{
	icon = {icons.path('mod_tight')}
	interest_group_approval_add = {credit_ai.IG_APPROVAL}
}}

# timed interest group modifiers from the two events
{timed}"""


# the panic event's opening line by cause: a collapse this month, a panic abroad, anything else
PANIC_CAUSES = [("crash", "has_variable = spec_crashed var:spec_c_crash < 0"),
                ("foreign", "exists = var:spec_foreign_src var:spec_c_foreign < 0"), ("other", "")]
# the two events' pictures by the capital's region (stories.REGIONS), west as the fallback
MANIA_PICS = {"west": "europenorthamerica_london_center", "latam": "southamerica_aristocrats",
              "mideast": "middleeast_upperclass_party", "africa": "africa_city_center", "asia": "unspecific_world_fair"}
PANIC_PICS = {"west": "unspecific_factory_closed", "africa": "africa_public_protest", "asia": "asia_poor_people_moving"}


def panic_descs():
    return "".join(f"\t\t\ttriggered_desc = {{\n\t\t\t\tdesc = spec_markets.2.d_{cause}{loans}{bad}\n"
                   f"\t\t\t\ttrigger = {{ {when} {'always = yes' if loans else 'var:spec_clawed > 0'} {extra} }}\n\t\t\t}}\n"
                   for bad, extra in leverage.PANIC_DESCS for cause, when in PANIC_CAUSES for loans in ("", "_no_loans"))


def panic_loc(root):
    cap = "[ROOT.GetCountry.GetCapital.GetCityHubName]"
    queue = f"depositors have queued outside the banks of {cap} since first light."
    opening = {
        "crash": f"The end of the boom in [{root}.Var('spec_crashed').GetGoods.GetName], the largest of the booms that ended, has become a general panic. Houses that lent "
                 f"against its price are failing one after another, and {queue}",
        "foreign": f"The panic in [{root}.Var('spec_foreign_src').GetCountry.GetName] has crossed into our markets. Houses that "
                   f"traded or borrowed there are failing one after another, and {queue}",
        "other": f"Confidence has failed all at once. Sound firms cannot borrow at any price, and {queue}",
    }
    loans = {"": f"The banks are calling in #v @money![{root}.Var('spec_clawed').GetValue|D]#! of loans, and investors hold on "
                 "to what little they have left.",
             "_no_loans": "Investors hold on to what little they have left."}
    rest = (f"[concept_private_construction] will be halved for #v [{root}.Var('spec_panic').GetValue|0]#! months.\\n\\n"
            "Ruined $capitalists_no_icon$, $aristocrats_no_icon$ and $shopkeepers_no_icon$ blame the government, and some become "
            f"[Concept('concept_radical','$concept_radicals$')]. {movements.PANIC_LINE}{centres.PLEDGE_UNMET}")
    return ("".join(f' spec_markets.2.d_{c}{k}: "{opening[c]} {loans[k]} {rest}"\n' for c, _ in PANIC_CAUSES for k in loans)
            + leverage.panic_event_loc(root, [f"spec_markets.2.d_{c}{k}" for c, _ in PANIC_CAUSES for k in loans]))


def events():
    def ig(key, mod, days="short_modifier_time"):
        return (f"\t\tig:ig_{key} ?= {{\n\t\t\tadd_modifier = {{\n\t\t\t\tname = {mod}\n"
                f"\t\t\t\tdays = {days}\n\t\t\t}}\n\t\t}}\n")
    def temper(t, n):
        return f"\t\t\tmodifier = {{\n\t\t\t\ttrigger = {{ var:spec_temper ?= {t} }}\n\t\t\t\tadd = {n}\n\t\t\t}}\n"
    return f"""namespace = spec_markets

# mania warning
spec_markets.1 = {{
	type = country_event
	placement = root
	title = spec_markets.1.t
	desc = {stories.field('spec_markets.1.d', 'has_variable = spec_top1 has_variable = spec_top2 has_variable = spec_top3')}	flavor = spec_markets.1.f
	duration = 3
{stories.pictures(MANIA_PICS)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "{icons.path('event_mania')}"

	option = {{
		name = spec_markets.1.a
		default_option = yes
{ig('industrialists', 'spec_boom_riding')}		ai_chance = {{
			base = 50
{temper(1, 30)}		}}
	}}
	option = {{
		name = spec_markets.1.b
		custom_tooltip = {{
			text = spec_markets.1.b.tt
			spec_cool_conf = {{ AMOUNT = {MANIA_CAUTION} }}
		}}
{ig('industrialists', 'spec_boom_warning')}{ig('intelligentsia', 'spec_prudent_counsel')}		ai_chance = {{
			base = 30
{temper(-1, 30)}		}}
	}}
	option = {{
		name = spec_markets.1.c
		custom_tooltip = {{
			text = spec_levy_tt
			add_treasury = spec_speculator_tax
		}}
		custom_tooltip = {{
			text = spec_markets.1.c.tt
			spec_cool_conf = {{ AMOUNT = {MANIA_TAX_CONF} }}
		}}
{ig('industrialists', 'spec_speculation_levy', 'normal_modifier_time')}		ai_chance = {{
			base = 20
{temper(-1, 20)}		}}
	}}
}}

# panic
spec_markets.2 = {{
	type = country_event
	placement = root
	title = spec_markets.2.t
	# what broke confidence this month, and whether the banks had loans to call in
	desc = {{
		first_valid = {{
{panic_descs()}		}}
	}}
	flavor = spec_markets.2.f
	duration = 3
{stories.pictures(PANIC_PICS)}	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "{icons.path('event_panic')}"

	option = {{
		name = spec_markets.2.a
		trigger = {{ NOT = {{ has_variable = spec_rescued }} }}  # the pledged rescue came with the panic (centres.PLEDGE_RESCUE)
		default_option = yes
		custom_tooltip = spec_markets.2.a.tt
{ig('industrialists', 'spec_market_left_alone')}		ai_chance = {{
			base = 50
		}}
	}}
	option = {{
		name = spec_markets.2.b
		trigger = {{ spec_can_rescue = yes }}
{stories.RESCUE_OPTION}		# the AI rescues later, by its own roll (credit_ai.py)
		ai_chance = {{
			base = 0
		}}
	}}
	option = {{
		name = spec_markets.2.c
{ig('industrialists', 'spec_blamed_for_panic', 'normal_modifier_time')}{ig('trade_unions', 'spec_speculators_blamed')}{ig('intelligentsia', 'spec_speculators_blamed')}		# workers who feared for their jobs welcome a government that takes their side
		add_loyalists = {{ value = 0.05 strata = lower }}
		ai_chance = {{
			base = 20
		}}
	}}
}}
"""


def test_events():
    """Debug builds only: the console's event command runs these on a country to test without waiting."""
    tests = [(90, "spec_start_panic = yes"), (91, "if = { limit = { spec_can_rescue = yes } spec_rescue = yes }"),
             (92, "activate_law = law_type:law_command_economy"), (93, "activate_law = law_type:law_laissez_faire"),
             (94, "set_variable = { name = spec_conf value = 85 }"),
             (89, "remove_global_variable = spec_names_year")]  # the yearly Renown pass (and AI charters) next month
    return "".join(f"""
spec_markets.{n} = {{
	type = country_event
	hidden = yes
	immediate = {{ {effect} }}
}}
""" for n, effect in tests)


def unwind_loc():
    """For the goods board's risk tooltips (market_tab SPEC_RISK_TT and SPEC_RISK_NONE_TT): how the boom would end."""
    fx, sev, glut = market_tab.fx, market_tab.good_var("spec_sev"), market_tab.good_var("spec_glut")
    at = lambda n: f"GreaterThanOrEqualTo_CFixedPoint({sev}, {fx(n)})"
    pick = lambda key: f"[SelectLocalization({at(3)}, '{key}_3', SelectLocalization({at(2)}, '{key}_2', '{key}_1'))]"
    # the price trend at which interest crosses cut: hype is 1 + trend rising, 1 / (1 - trend) falling (values())
    trend = lambda cut: (f"[Divide_CFixedPoint({fx(round(cut - 1 if cut >= 1 else 1 - 1 / cut, 3))}, Multiply_CFixedPoint({fx(HYPE_GAIN)}, "
                         f"Max_CFixedPoint({market_tab.sv('spec_hype_mult' if cut >= 1 else 'spec_hype_mult_down')}, {fx(0.01)})))|%1]")
    name = {3: "Collapse", 2: "Bust", 1: "Correction"}
    peak = {3: "Feverish", 2: "Eager", 1: "Keen"}
    out = [f' SPEC_UNWIND: "{pick("SPEC_UNWIND")}"', f' SPEC_UNWIND_LINK: "{pick("SPEC_UNWIND_C")}"', f' SPEC_UNWIND_DESC: "{pick("SPEC_UNWIND_DESC")}"',
           f" SPEC_RISK_NONE: \"[SelectLocalization({at(1)}, 'SPEC_RISK_SLIGHT', SelectLocalization("
           f"GreaterThan_CFixedPoint({glut}, {fx(0)}), 'SPEC_RISK_GLUT', 'SPEC_RISK_CALM'))]\"",
           ' SPEC_RISK_SLIGHT: "#header Risk of a $SPEC_UNWIND$#!\\n[concept_spec_market_confidence] if the boom ends: #v Slight#!'
           '\\n$TOOLTIP_DELIMITER$\\n$SPEC_UNWIND_DESC$"',
           ' SPEC_RISK_GLUT: "#header Recovering#!\\n$TOOLTIP_DELIMITER$\\n[Goods.GetName] is recovering after its last boom ended. '
           'Investors hold back, keeping [concept_spec_investor_interest] at #v Doubtful#! for a while."',
           ' SPEC_RISK_CALM: "#header No Boom#!\\n$TOOLTIP_DELIMITER$\\n[Goods.GetName] has had no recent boom. Once '
           '[concept_spec_investor_interest] reaches #v Keen#! or higher, a fall back to #v Doubtful#! ends the boom, and the '
           'higher it went, the harder it falls."']
    for s, _, below, _, months in UNWINDS:
        end = f"the boom ends in a [concept_spec_{name[s].lower()}]"
        out += [f' SPEC_UNWIND_{s}: "{name[s]}"', f' SPEC_UNWIND_C_{s}: "[concept_spec_{name[s].lower()}]"',
                f' SPEC_UNWIND_DESC_{s}: "This [concept_good] has had a boom that reached #v {peak[s]}#!. If its price trend '
                f'falls below #v {trend(below)}#!, [concept_spec_investor_interest] turns #v {"Fleeing" if s == 3 else "Doubtful"}#! '
                f'and {end}. Investors then hold back for #v {months}#! months. The risk fades as the boom ages."']
    return "".join(line + "\n" for line in out)


def loc():
    c = "JournalEntry.GetCountry.MakeScope"
    v = lambda name, fmt="|1": f"[{c}.Var('{name}').GetValue{fmt}]"
    good = lambda k: f"#v [{c}.Var('spec_{k}').GetGoods.GetName]#!"
    root = "ROOT.GetCountry.MakeScope"
    goods = "[Concept('concept_good','$concept_goods$')]"
    bailout = next(a for key, _, a, _ in EVENT_MODIFIERS if key == "spec_bank_bailout")
    requires = (f"Choosing it locks [concept_spec_credit_policy] for #v {STANCE_COOLDOWN}#! months. "
                "Requires [GetTechnology('central_banking').GetName].")
    return f"""l_english:
 spec_confidence_bar: "Market Confidence"
 spec_confidence_bar_desc: "[concept_spec_market_confidence]: #v [JournalEntry.GetCurrentBarValue(ScriptedProgressBar.Self)|0]#!"
 spec_stance_current_tt: "This is not already the [concept_spec_credit_policy]"
 spec_stance_cooldown_tt: "[concept_spec_credit_policy] has not changed in the last #v {STANCE_COOLDOWN}#! months"
 spec_rescued_tt: "We have neither lent to the banks nor suspended the Bank Act during this [concept_spec_financial_panic]"
 spec_credit_tight: "Tight Credit"
 spec_credit_tight_fx: "[concept_spec_credit_policy] becomes #v Tight#!"
 spec_credit_normal_fx: "[concept_spec_credit_policy] becomes #v Normal#!"
 spec_credit_loose_fx: "[concept_spec_credit_policy] becomes #v Loose#!"
 spec_credit_tight_desc: "Banks stop lending and investors react less to rising prices. Booms stay smaller, so their endings and panics are milder. Each month [concept_spec_market_confidence] loses #N {TIGHT_PULL:.0%}#! of how far it is above #v {TIGHT_FROM}#!. {requires}\\n\\n{credit_ai.ig_lines('tight')}"
 spec_credit_normal: "Normal Credit"
 spec_credit_normal_desc: "Banks lend into the [concept_investment_pool] while [concept_spec_market_confidence] is above #v {CREDIT_FROM}#!. {requires}"
 spec_credit_loose: "Loose Credit"
 spec_credit_loose_desc: "Banks lend more and investors react more strongly to rising prices. Booms grow larger, and so do the losses when they end. {requires}\\n\\n{credit_ai.ig_lines('loose')}"
 spec_rescue_banks: "Lend to the Banks"
 spec_rescue_banks_desc: "Spend about #v [{root}.ScriptValue('spec_rescue_share_now')|%1]#! of [concept_gdp] from the [concept_treasury] to end the [concept_spec_financial_panic] within #v [{root}.ScriptValue('spec_rescue_months')|0]#! months and halve its effects. [concept_spec_market_confidence] rises by #v {RESCUE_CONF}#!. The more months the panic has left, the more it costs. Can be done once per panic. [GetTechnology('central_banking').GetName] makes it cheaper and faster."
 spec_conf_panic: "Shaken Investors"
 spec_conf_panic_held: "Shaken Investors"
 spec_conf_wary: "Wary Investors"
 spec_conf_steady: "Steady Investors"
 spec_conf_buoyant: "Buoyant Investors"
 spec_conf_mania: "Manic Investors"
 spec_conf_panic_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_conf_panic_held_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_conf_wary_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_conf_steady_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_conf_buoyant_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_conf_mania_desc: "Effects of [concept_spec_market_confidence] on investment and the interest on [concept_loans]"
 spec_panic: "Financial Panic"
 spec_panic_desc: "Effects of a [concept_spec_financial_panic] in the [concept_market]"
 spec_panic_crunch: "Credit Crunch"
 spec_panic_crunch_desc: "Banks have stopped lending during the [concept_spec_financial_panic], halving [concept_private_construction]"
{leverage.LOC} spec_loose_credit: "Loose Credit"
 spec_loose_credit_desc: "Effects of the [concept_spec_credit_policy]"
 spec_tight_credit: "Tight Credit"
 spec_tight_credit_desc: "Effects of the [concept_spec_credit_policy]"
 spec_markets.1.t: "Speculative Mania"
 spec_markets.1.d: "Fortunes are being made in [ROOT.GetCountry.GetCapital.GetCityHubName] faster than they can be counted. The prices of [{root}.Var('spec_top1').GetGoods.GetName], [{root}.Var('spec_top2').GetGoods.GetName] and [{root}.Var('spec_top3').GetGoods.GetName] climb by the week, new companies to produce them are floated almost daily, and the banks lend against their shares without a second look. Few stop to ask what any of it is worth.\\n\\nSome $capitalists_no_icon$ and $shopkeepers_no_icon$ credit the government with their new wealth and become [Concept('concept_loyalist','$concept_loyalists$')]. {movements.MANIA_LINE}"
 spec_markets.1.d_generic: "Fortunes are being made in [ROOT.GetCountry.GetCapital.GetCityHubName] faster than they can be counted. Prices climb by the week, new companies are floated almost daily, and the banks lend against their shares without a second look. Few stop to ask what any of it is worth.\\n\\nSome $capitalists_no_icon$ and $shopkeepers_no_icon$ credit the government with their new wealth and become [Concept('concept_loyalist','$concept_loyalists$')]. {movements.MANIA_LINE}"
 spec_markets.1.f: ""Buy, my boy, and never mind the price. Whatever you pay today, some other fellow will pay more tomorrow.""
 spec_markets.1.a: "Prosperity speaks for itself."
 spec_markets.1.b: "Counsel restraint."
 spec_markets.1.b.tt: "[concept_spec_market_confidence] falls by #v {MANIA_CAUTION}#!"
 spec_markets.1.c: "Let the speculators pay their share."
 spec_markets.1.c.tt: "[concept_spec_market_confidence] falls by #v {MANIA_TAX_CONF}#!"
 spec_markets.2.t: "Financial Panic"
{panic_loc(root)} spec_markets.2.f: ""Yesterday I was worth forty thousand. This morning I am worth my coat, and I have been offered very little for that.""
 spec_markets.2.a: "The market must find its own floor."
 spec_markets.2.a.tt: "The [concept_spec_financial_panic] runs its full course unless we later #v Lend to the Banks#!, which also removes this $ig_industrialists$ [concept_approval] change"
 spec_markets.2.b: "We must lend to the banks."
 spec_markets.2.b.tt: "The [concept_spec_financial_panic] ends within #v [{root}.ScriptValue('spec_rescue_months')|0]#! months and its effects are halved\\n[concept_spec_market_confidence] rises by #v {RESCUE_CONF}#!"
 spec_rescue_cost_tt: "[concept_treasury]: #N -@money![{root}.ScriptValue('spec_rescue_cost')|D]#!, about #v [{root}.ScriptValue('spec_rescue_share_now')|%1]#! of [concept_gdp]"
 spec_levy_tt: "[concept_treasury]: #P +@money![{root}.ScriptValue('spec_speculator_tax')|D]#!, about #v {MANIA_TAX * 100:g}%#! of [concept_gdp]"
 spec_bank_bailout_tt: "$ig_trade_unions$ and $ig_rural_folk$ [concept_approval]: #N {bailout}#! for #v 2.5#! years"
 spec_markets.2.c: "The speculators brought this upon us."
{"".join(f' {k}: "{name}"{chr(10)}' for k, _, _, name in EVENT_MODIFIERS)}{unwind_loc()}"""


def information_panel_bar():
    """The vanilla side bar with one more large button, Finance, under Power Bloc, and the Finance window
    (market_tab.tab_type) hosted beside it where vanilla's own panels sit. The window is ours, not one of
    InformationPanelBar's, so every side bar button that opens a vanilla panel also closes it."""
    gui = (GAME / "gui/information_panel_bar.gui").read_text(encoding="utf-8-sig")

    def sub(pattern, repl, want=1, flags=0):
        nonlocal gui
        gui, n = re.subn(pattern, repl, gui, flags=flags)
        if n != want and want is not None or n == 0:
            sys.exit(f"information_panel_bar.gui changed, {n} of {pattern[:50]!r}")

    # everything under Power Bloc moves down one large button
    sub(r"^@(\w+_position) = (\d+)", lambda m: m[0] if int(m[2]) < 300 else f"@{m[1]} = {int(m[2]) + 50}", None, re.M)
    sub(r"^@power_bloc_position = 250$", "@power_bloc_position = 250\n@spec_finance_position = 300", flags=re.M)
    # and the skin behind them grows by one large socket
    sub(r'\t+icon = \{\s+texture = "gfx/interface/main_hud/sidebar_skin_bg_3', lambda m: """				icon = {
					texture = "gfx/interface/main_hud/sidebar_skin_bg_2.dds"
					size = { 50 50 }

					using = hud_shiny_effect
				}

""" + m[0])
    # opening or closing Finance also ends the Exchange tab's speciality pick (centres.py), so no slot stays armed
    unpick = "[GetVariableSystem.Clear('spec_pick_slot')]"
    sub(r'^(\s*)(onclick = "\[InformationPanelBar\.Open[^\n]*)$',
        lambda m: f"{m[0]}\n{m[1]}onclick = \"[GetVariableSystem.Clear('{market_tab.FIN}')]\"\n{m[1]}onclick = \"{unpick}\"", None, re.M)
    click = f"""onclick = "[InformationPanelBar.ClosePanel]"
						onclick = "[GetVariableSystem.Toggle('{market_tab.FIN}')]"
						onclick = "{unpick}\""""
    is_open = f"visible = \"[GetVariableSystem.Exists('{market_tab.FIN}')]\""
    sub(r"\t\t\t\t### POLITICS\n", lambda m: f"""				### FINANCE (Speculative Markets)
				sidebar_label_button = {{
					position = {{ -100 @spec_finance_position }}
					blockoverride "onclick" {{
						{click}
					}}
				}}
				sidebar_label_text = {{
					position = {{ -100 @spec_finance_position }}
					text = "SPEC_FINANCE_BTN"
				}}
				widget = {{
					position = {{ 0 @spec_finance_position }}
					using = clickthrough_blocker
					using = sidebar_button_size
					using = selected_sidepanel_animation
					blockoverride "selected_visibility" {{
						{is_open}
					}}
					sidepanel_button_big = {{
						blockoverride "icon" {{
							texture = "{finance_icon.PATH}"
						}}
						blockoverride "button_selected" {{
							{is_open}
						}}
						{click}
					}}
				}}
				sidebar_tooltip_area = {{
					position = {{ 0 @spec_finance_position }}
					tooltip = "SPEC_FINANCE_BUTTON_TT"
				}}

{m[0]}""")
    # the bar becomes a screen-sized host: the Finance window laid out as ingame_hud lays out vanilla's panels, and
    # over it the bar itself, as it was
    sub(r"\t\tallow_outside = yes\s+focuspolicy = all\s+position = \{ 0 200 \}\n", "\t\tsize = { 100% 100% }\n")
    sub(r"\t\t### BACKGROUND FOR LABEL BUTTONS\n", lambda m: """		spec_finance_navigation_guard = {}
		widget = {
			position = { 0 78 }
			size = { 100% 100% }
			scissor = yes
			vbox = {
				margin_top = 7
				margin_bottom = 78
				hbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding
					spec_finance_window = {}
					widget = {
						layoutpolicy_horizontal = expanding
						layoutpolicy_vertical = expanding
					}
				}
			}
		}
		# the flag's pole and drape, then the rank badge, again over the Finance window, as vanilla's panels leave them
		# showing (flags.gui:353 fancy_flag, ingame_hud.gui:271); cut at the window's top so the 3D flag stays the top bar's
		widget = {
			position = { 0 78 }
			size = { 117 87 }
			scissor = yes
			alwaystransparent = yes
			icon = {
				position = { 0 -78 }
				size = { 117 165 }
				texture = "gfx/interface/flag/fancy_flag_decoration.dds"
			}
			icon = {
				position = { 0 -78 }
				size = { 117 165 }
				texture = "gfx/interface/flag/fancy_flag_cloth.dds"
			}
			icon = {
				position = { 0 -78 }
				size = { 117 165 }
				texture = "gfx/interface/flag/fancy_flag_cloth.dds"
				color = "[GetPlayer.GetMapColor]"
				alpha = 0.6
			}
		}
		topbar_rank = {}

		widget = {
		allow_outside = yes
		focuspolicy = all
		position = { 0 200 }

""" + m[0])
    sub(r"\n\t\}\n(?=\s*type power_bloc_icon_button_widget)", "\n\t}\n\t}\n")
    return gui


def pool_breakdown():
    """Vanilla's investment pool breakdown (budget panel and the tab's pool row) with a line for the mod's credit,
    replaced key by key from localization/replace so no vanilla file is overridden."""
    p = "GetPlayer.MakeScope"
    credit = f"GreaterThan_CFixedPoint({p}.Var('spec_credit_given').GetValueWithDefault('(CFixedPoint)0'), '(CFixedPoint)0')"
    recall = (f"And(GreaterThan_CFixedPoint({p}.ScriptValue('spec_in_panic'), '(CFixedPoint)0'), "
              f"GreaterThan_CFixedPoint({p}.Var('spec_clawed').GetValueWithDefault('(CFixedPoint)0'), '(CFixedPoint)0'))")
    bad = f"{p}.Var('spec_crunch').IsSet"
    return f"""l_english:
 INVESTMENT_POOL_CHANGE:1 "[GetPlayer.GetInvestmentPoolChangeFromConstructionDesc]\\n[GetPlayer.GetInvestmentPoolChangeFromInvestmentDesc][SelectLocalization({credit}, 'SPEC_POOL_CREDIT', 'SPEC_POOL_NONE')][SelectLocalization({recall}, 'SPEC_POOL_RECALL', 'SPEC_POOL_NONE')][SelectLocalization({bad}, 'SPEC_POOL_BAD', 'SPEC_POOL_NONE')]"
 SPEC_POOL_CREDIT: "\\n#bold Credit Lent:#! #v @money![{p}.Var('spec_credit_given').GetValueWithDefault('(CFixedPoint)0')|+D]#! this month"
 SPEC_POOL_RECALL: "\\n#bold Withdrawn in [concept_spec_financial_panic]:#! #N @money!-[{p}.Var('spec_clawed').GetValueWithDefault('(CFixedPoint)0')|D]#!"
 SPEC_POOL_BAD: "\\n#bold [concept_spec_bad_debts]:#! #N -[{p}.ScriptValue('spec_crunch_invest_pct')|0]%#! investment, fading over #v [{p}.ScriptValue('spec_crunch_months')|0]#! months"
 SPEC_POOL_NONE: ""
"""


def law_table():
    """Each economic system and trade policy law's effects here, as tech_ties modifier lines read from the tuned values.
    A law that leaves a figure as it is shows no line for it, as vanilla does."""
    t = {f"law_{law}": [("country_spec_trade_tie_mult", n - 1)] for law, n in vanilla_ties.TRADE_TIE.items()}
    for law, hype, panic in LAWS:
        lines = [("country_spec_interest_response_mult", hype - 1), ("country_spec_bank_lending_mult", hype - 1),
                 ("country_spec_panic_length_mult", panic - 1)] if hype else [("country_spec_off_bool", None)]
        t[f"law_{law}"] = [line for line in lines if line[1] != 0]
    return t


def tech_table():
    """Each finance tech's effects here, as tech_ties modifier lines: what it adds to the figure without it."""
    t = {}
    line = lambda tech, key, v=None: t.setdefault(tech, []).append((key, v))
    for tech, n in FIN_BOOM.items():
        line(tech, "country_spec_boom_size_mult", n / FIN_BOOM_BASE)
    line(FIN_LEVERAGE[0], "country_spec_boom_size_mult", FIN_LEVERAGE[1] - 1)
    for tech, n in [*FIN_RISK.items(), FIN_LEVERAGE]:
        line(tech, "country_spec_boom_end_loss_mult", n - 1)
    for tech in CREDIT_TECHS:  # spec_tech_credit: 0.5, and 0.5 more for each
        line(tech, "country_spec_bank_lending_mult", 1)
    line(MACRO[0], "country_spec_confidence_recovery_mult", MACRO[1] - 1)
    for tech, n in FLIGHT_TECHS.items():
        line(tech, "country_spec_capital_flight_mult", n / FLIGHT_BASE)
    line(UNSTANDARD[0], "country_spec_foreign_loss_mult", 1 / UNSTANDARD[1] - 1)
    line("international_exchange_standards", "country_spec_foreign_ties_mult", vanilla_ties.EXCHANGE_TIE - 1)
    for tech, months in zip(leverage.LADDER_TECHS, leverage.LADDER_STEPS) if leverage.ON else ():
        line(tech, "country_spec_credit_limit_add", months)
    line("joint_stock_companies", "country_spec_interest_response_mult", vanilla_ties.STOCK_HYPE - 1)
    for tech in companies.TIE_TECHS:
        line(tech, "country_spec_company_bust_mult", companies.TIE_PER_TECH)
    line("stock_exchange", "country_spec_excess_bool")
    line("banking", "country_spec_rescue_bool")
    line("banking", "country_spec_banknote_bool")
    line("central_banking", "country_spec_credit_policy_bool")
    line("central_banking", "country_spec_llr_bool")
    line("central_banking", "country_spec_rescue_cost_mult", RESCUE_COST / RESCUE_COST_PRIVATE - 1)
    line("central_banking", "country_spec_rescue_months_add", RESCUE_MONTHS - RESCUE_MONTHS_PRIVATE)
    line("joint_stock_companies", "country_spec_company_law_bool")
    return t


def game_version():
    return re.search(r'"rawVersion":\s*"([^"]+)"', (GAME.parent / "launcher/launcher-settings.json").read_text(encoding="utf-8")).group(1)


def main(log=False):
    if log and MOD.resolve() == (Path(__file__).resolve().parent.parent / "mod").resolve():
        raise SystemExit("Debug builds require SPEC_MOD_OUT pointing outside mod/. The release was not changed.")
    WRITTEN.clear()
    painted = icons.build(MOD)
    WRITTEN.update((Path(icons.DIR) / f"{name}.dds").as_posix() for name in painted)
    WRITTEN.add("gui/spec_texticons.gui")
    finance_icon.build(MOD)
    WRITTEN.add(finance_icon.PATH)
    injects = []
    for fname, sells in SELLS.items():
        (MOD / f"common/buildings/{fname}.txt").unlink(missing_ok=True)  # was a copy of the vanilla file
        s = (GAME / f"common/buildings/{fname}.txt").read_text(encoding="utf-8-sig")
        injects += [building_inject(s, name, good) for name, good in sells.items()]
    write(BUILDINGS_FILE, "# investors favour building what is booming: each building's ai_value grows with its good's hype\n"
          + "\n".join(i for i, _ in injects))
    write(PMR_FALLBACK_FILE, "# vanilla's ai_value under Production Method Rework's names; PMR's own definitions load later and win\n"
          + "\n".join(f for _, f in injects))
    values()
    (MOD / "common/script_values/spec_log_values.txt").unlink(missing_ok=True)
    if log:  # for the log line: the country's Long Depression phase, 0 when it is not in one
        write("common/script_values/spec_log_values.txt",
              "spec_log_ld = {\n\tvalue = 0\n\tif = {\n\t\tlimit = { has_variable = spec_ld }\n\t\tvalue = var:spec_ld\n\t}\n}\n"
              + "".join(f"spec_log_d_{n} = {{\n\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_variable = {v} }}\n\t\tvalue = var:{v}\n\t}}\n}}\n"
                        for n, v in market_tab.DRIVERS)
              # the investment pool's weekly gross income and its balance, to size credit against them
              + "spec_log_ipi = {\n\tvalue = investment_pool_gross_income\n}\nspec_log_ip = {\n\tvalue = investment_pool\n}\n"
              + "\n".join(log_values()) + "\n")
    # before monthly(), which places companies.crash()
    for rel, text in companies.script(GAME, SELLS, UPGRADES, lambda n: f"gfx/interface/icons/timed_modifier_icons/{n}.dds").items():
        write(rel, text)
    write("common/on_actions/spec_on_actions.txt", monthly(log))
    write("common/scripted_effects/spec_effects.txt", effects(log))
    write("common/scripted_triggers/spec_triggers.txt", triggers())
    (MOD / "common/scripted_buttons/spec_buttons.txt").unlink(missing_ok=True)  # the journal's Credit Policy and Lend: tab only now
    write("common/scripted_guis/spec_sguis.txt", sguis())
    write("common/journal_entries/spec_journal.txt", journal.entry(STANCES))
    write("common/scripted_progress_bars/spec_bars.txt", bar())
    write("common/static_modifiers/spec_modifiers.txt", modifiers())
    for rel, text in levers.script(GOODS, levers.industry(SELLS, UPGRADES), goods_tax_cost(), goods_cost()).items():
        write(rel, text)
    write("events/spec_markets_events.txt", events() + (test_events() if log else ""))
    k = {name: value for name, value in globals().items() if name.isupper() and isinstance(value, (int, float, dict))}
    # for the goods chart's category filters: staple, industrial, luxury or military
    k["CATEGORY"] = categories()
    k["UNWINDS"] = UNWINDS
    journal.build(write, k)
    write("common/scripted_effects/spec_ui_effects.txt", interest_board.ui_effect(k))
    for rel, text in {**credit_ai.script(k), **movements.script(k)}.items():
        write(rel, text)
    stories.build(write, k, log)
    (MOD / "common/scripted_guis/spec_response_sguis.txt").unlink(missing_ok=True)  # the tab's measures, now journal only
    for rel in probe.files():
        (MOD / rel).unlink(missing_ok=True)
    probe.build(write, log)
    notify.build(write)
    __import__("centres").build(write)
    for rel, text in vanilla_ties.script(k).items():
        write(rel, text)
    diplomacy.build(write, log)
    economy.build(write)
    # the Crash passes along market and subject ties always, never along an isolationist trade tie
    assert LINKS['trade'] * vanilla_ties.TRADE_TIE['isolationism'] < depression.SPREAD_MIN <= LINKS['subject'], depression.SPREAD_MIN
    depression.build(write, GAME, MOD, log)
    write("localization/english/spec_markets_l_english.yml",
          loc() + journal.loc(k) + market_tab.loc(k) + market_tab.item_loc(GOODS, k) + concepts.loc(k) + levers.loc() + stories.loc(k) + notify.loc(PANIC) + movements.loc() + vanilla_ties.loc(k) + companies.loc() + __import__("company_section").loc() + __import__("centres").loc() + market_visual.loc(k) + goods_panel.loc() + depression.loc() + tech_ties.loc() + cycle.loc())
    write("localization/english/replace/spec_markets_replace_l_english.yml", pool_breakdown())
    write("common/game_rules/spec_game_rules.txt", "spec_market_volatility = {\n\tdefault = spec_volatility_historical\n\n"
          + "".join(f"\tspec_volatility_{n} = {{\n\t}}\n" for n in VOLATILITY) + "}\n")
    tip = lambda n, name: f"#tooltippable #tooltip:[GetPlayer.GetTooltipTag],setting_spec_volatility_{n}_desc {name}#!#!"
    # worded as vanilla's rules (game_rules_l_english.yml, rule_ai_aggression): a short setting name, the non-default
    # one in #high, and one sentence on what it does
    panics = "[Concept('concept_spec_financial_panic', '$concept_spec_financial_panics$')]"
    write("localization/english/spec_rules_l_english.yml", "l_english:\n rule_spec_market_volatility: \"Market Volatility\"\n"
          f" setting_spec_volatility_historical: \"{tip('historical', 'Historical')}\"\n"
          f" setting_spec_volatility_historical_desc: \"Speculative booms and {panics} occur about as often as they did "
          "in the 19th century\"\n"
          f" setting_spec_volatility_heightened: \"{tip('heightened', '#high High#!')}\"\n"
          " setting_spec_volatility_heightened_desc: \"Speculative booms grow larger and end more abruptly, and "
          f"{panics} occur more often than they did in the 19th century\"\n")
    write("common/game_concepts/spec_concepts.txt", concepts.definitions())
    write("gui/spec_market_tab.gui", market_tab.tab_type(k))
    write("gui/information_panel_bar.gui", information_panel_bar())
    write("gui/goods_panel.gui", goods_panel.patch((GAME / "gui/goods_panel.gui").read_text(encoding="utf-8-sig")))
    write("gui/spec_goods_panel.gui", goods_panel.block_type())
    (MOD / tech_ties.VANILLA_FILE).unlink(missing_ok=True)  # was a copy of the vanilla file
    for rel, text in tech_ties.files(GAME, tech_table(), law_table()).items():
        write(rel, text)
    i18n.build(write)
    meta = MOD / ".metadata/metadata.json"
    live = Path(__file__).resolve().parent.parent / "mod"
    template = meta if meta.exists() else live / ".metadata/metadata.json"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(re.sub(r'"version": "[^"]*"', f'"version": "{VERSION}"', template.read_text(encoding="utf-8-sig")), encoding="utf-8")
    # GUI overrides must be regenerated after a game update. Side builds carry their own provenance too.
    built = MOD.parent / "built_against.txt" if MOD.resolve() == live.resolve() else meta.parent / "built_against.txt"
    built.write_text(game_version(), encoding="utf-8")
    # a file this build did not write is from an older version of the mod and would still load in the game
    stale = remove_stale()
    if stale:
        print("removed left-over files:", [f.relative_to(MOD).as_posix() for f in stale])
    print(f"{len(BUILDINGS)} buildings, {len(GOODS)} goods, {len(painted)}/{len(icons.SLOTS)} icons painted{', logging' if log else ''}")


if __name__ == "__main__":
    main("--log" in sys.argv)
