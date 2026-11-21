"""Writes workshop/values.html: every gameplay number in the mod, in plain words, with its value read from the tools.

py -3 tools/values_table.py     Layout, text and art are left out on purpose.
ponytail: the words are by hand, and a new setting needs a row here. page() only proves the old rows still resolve."""
import ast
import html
import re
from pathlib import Path

import companies as c
import credit_ai as a
import depression as dp
import diplomacy as d
import economy as e
import exposure as x
import interest_board as b
import generate as g
import journal as j
import leverage as l
import levers as v
import movements as m
import stories as s
import vanilla_ties as t

HERE = Path(__file__).parent
OUT = HERE.parent / "workshop" / "values.html"
# from the built 0.7 in snapshots/v0.7.0_workshop: there is no copy of its tools
WAS = {"g.CREDIT_SHARE": "0.3x", "g.CREDIT_FLOW_MAX": "60%", "g.CREDIT_CAP_MONTHS": "12 months for everyone", "dp.EARLIEST_YEAR": "always 1870"}
pct = lambda n: f"{n * 100:g}%"
signed = lambda n: f"{n * 100:+g}%"
pairs = lambda dct, f=str: ", ".join(f"{str(k).replace('_', ' ')} {f(val)}" for k, val in dct.items())
laws = lambda i: ", ".join(f"{row[0].replace('_', ' ')} x{row[i]:g}" for row in g.LAWS)
war = lambda k: f"{d.WAR_ROWS[k][-2]:g} to {d.WAR_ROWS[k][-1]:+g}"
LD_NAMES = {"state_capitalists_investment_pool_efficiency_mult": "investment", "country_loan_interest_rate_mult": "loan rate",
            "state_construction_mult": "construction", "state_trade_quantity_mult": "trade",
            "state_radicals_and_loyalists_from_sol_change_mult": "radicals", c.FD_SOL: "Financial District pay"}
# a Long Depression phase modifier in words, from dp.MODS (FD_SOL is a flat value, the rest percentages)
ld = lambda m: ", ".join(f"{n} {dp.MODS[m][1][k]:+g}" if k == c.FD_SOL else f"{n} {signed(dp.MODS[m][1][k])}"
                        for k, n in LD_NAMES.items() if k in dp.MODS[m][1])

R = j.REFORMS
# (what it is, value in words, what it does, the code name) by system
GROUPS = [
    ("Leverage", "New in 0.8. Debt counted in months of pool income, and what it earns or risks.", [
        ("Safe line", f"{l.SAFE} months", "Past this, panics start sooner and crashes leave Bad Debts. Also the credit limit before Central Banking.", "l.SAFE"),
        ("Full danger", f"{l.RUIN} months", "Danger reaches its worst here and stops rising.", "l.RUIN"),
        ("Boom bonus per month", signed(l.REWARD), "Throughput for each whole month of leverage.", "l.REWARD"),
        ("Boom bonus stops at", f"{l.REWARD_MAX} months", "Largest bonus is this many months' worth.", "l.REWARD_MAX"),
        ("Panic line rise", f"+{l.PANIC_SPAN} points", f"At full danger the panic line moves from {g.PANIC} up to {g.PANIC + l.PANIC_SPAN}.", "l.PANIC_SPAN"),
        ("Worst Bad Debts", f"{l.CRUNCH_MAX} points", "Size of a crash at full danger. It grows in a straight line with the danger.", "l.CRUNCH_MAX"),
        ("Bad Debts on investment", signed(-l.CRUNCH_INVEST), f"Investment lost per point. Each point also costs {l.CRUNCH_THROUGHPUT:.1%} throughput.", "l.CRUNCH_INVEST"),
        ("Bad Debts fade", f"{l.CRUNCH_FADE} a month", f"Once felt in full, after {l.CRUNCH_RAMP} a month build-up. So the worst crash takes about {round((l.CRUNCH_MAX / l.CRUNCH_RAMP + l.CRUNCH_MAX / l.CRUNCH_FADE) / 12)} years to clear.", "l.CRUNCH_FADE"),
        ("Bad Debts fade, Tight credit", f"{l.CRUNCH_FADE_TIGHT} a month", f"The worst crash clears in about {round((l.CRUNCH_MAX / l.CRUNCH_RAMP + l.CRUNCH_MAX / l.CRUNCH_FADE_TIGHT) / 12)} years.", "l.CRUNCH_FADE_TIGHT"),
        ("Income average", pct(l.INCOME_SMOOTH), "What a new month counts for in the year-long income average that leverage is measured against.", "l.INCOME_SMOOTH"),
        ("Land loss that counts", pct(l.LAND_LOST), "Losing this much population stops the loss itself from inflating leverage.", "l.LAND_LOST"),
        ("Land loss relief", f"{l.RELIEF_MONTHS} months", "How long that protection fades over.", "l.RELIEF_MONTHS"),
        ("AI turns Tight at", f"{l.AI_LIMIT['-1']} / {l.AI_LIMIT['0']} / {l.AI_LIMIT['1']} months", "Cautious, ordinary and bold AI. It stays Tight until half that.", "l.AI_LIMIT"),
        ("Carried away by a Mania", f"{l.FEVER.get(0, 0)}% ordinary, {l.FEVER.get(1, 0)}% bold", "Chance in each Mania that an AI stops tightening until the Mania passes or a panic comes.", "l.FEVER"),
    ]),
    ("Bank credit", "How much banks lend, and how it is repaid.", [
        ("Lending starts at", f"{g.CREDIT_FROM} confidence", "Banks lend above this.", "g.CREDIT_FROM"),
        ("Lending size", f"{g.CREDIT_SHARE:g}x", "Monthly lending at full confidence, against a month of pool income, before the cap.", "g.CREDIT_SHARE"),
        ("Monthly lending cap", pct(g.CREDIT_FLOW_MAX), "Most of a month's credit that comes from confidence, as a share of pool income, before the lending rate (ceiling 60%).", "g.CREDIT_FLOW_MAX"),
        ("Credit limit", ", ".join(map(str, l.LADDER)) + " months, rising with each tech", "Central Banking, Investment Banks and International Exchange Standards each raise it.", "l.LADDER"),
        ("Monthly repayment", pct(g.CREDIT_RUNOFF), "Share of the debt repaid each month. With the lending cap, debt can reach the top of the credit limit if income stays flat.", "g.CREDIT_RUNOFF"),
        ("Panic clawback", pct(g.CLAWBACK), "Share of the debt a panic pulls back out of the pool.", "g.CLAWBACK"),
        ("Credit Policy: lending", "Tight x0, Loose x1.6", "Written straight into the formula, not a named setting.", "g.STANCES"),
        ("Credit Policy: hype", "Tight x0.5, Loose x1.3", "Written straight into the formula, not a named setting.", "g.STANCES"),
        ("Techs that add lending", f"{len(g.CREDIT_TECHS)} techs, +0.5 each", ", ".join(n.replace("_", " ") for n in g.CREDIT_TECHS), "g.CREDIT_TECHS"),
        ("Debt drag", f"-{t.DEBT_MAX} a month", "Confidence lost at the credit limit.", "t.DEBT_MAX"),
        ("Debt drag starts at", pct(t.DEBT_FROM), "Share of credit where government debt starts to weigh.", "t.DEBT_FROM"),
    ]),
    ("Market Confidence", "The 0 to 100 gauge, and the bands on it.", [
        ("Resting level", f"{g.CONF_START}", "Confidence drifts back here.", "g.CONF_START"),
        ("Drift back", pct(g.CONF_RECOVER), "Share of the gap closed each month.", "g.CONF_RECOVER"),
        ("Market Mood size", f"±{g.MOOD_SHOCK:g}", "Each country's random monthly nudge.", "g.MOOD_SHOCK"),
        ("Market Mood memory", pct(g.MOOD_KEEP), "How much of last month's mood carries over.", "g.MOOD_KEEP"),
        ("Panic line", f"{g.PANIC}", "Below this a panic starts.", "g.PANIC"),
        ("Wary line", f"{g.WARY}", "The AI loosens credit below this.", "g.WARY"),
        ("Mania line", f"{g.MANIA}", "Above this investors get reckless.", "g.MANIA"),
        ("Near-panic warning", f"{g.PANIC_NEAR}", "A player is warned below this.", "g.PANIC_NEAR"),
        ("Investment by band", pairs(g.BAND_INVEST, signed), "Investment from Capitalists, Aristocrats and Shopkeepers.", "g.BAND_INVEST"),
        ("Trade by band", pairs(g.BAND_TRADE, signed), "Trade volume: merchants ship more in a boom.", "g.BAND_TRADE"),
        ("Loan rate by band", pairs(g.BAND_RATE, signed), "Dearer in fear.", "g.BAND_RATE"),
    ]),
    ("Investor interest and booms", "How prices turn into interest, and interest into confidence.", [
        ("Fast price average", pct(g.FAST), "Monthly smoothing of the short average.", "g.FAST"),
        ("Slow price average", pct(g.SLOW), "Monthly smoothing of the long average.", "g.SLOW"),
        ("Hype gain", f"{g.HYPE_GAIN}", "How hard a price trend pushes interest.", "g.HYPE_GAIN"),
        ("Highest hype", f"{g.HYPE_MAX}x", "Interest can't go above this, or below its opposite.", "g.HYPE_MAX"),
        ("Booming from", f"{g.HOT_HYPE}x hype", "A good this hyped counts as booming.", "g.HOT_HYPE"),
        ("Keen from", f"{g.RISING_HYPE}x hype", "Where the Keen word starts. Doubtful mirrors it.", "g.RISING_HYPE"),
        ("Word buffer", pct(g.WORD_BUFFER), "Keeps a good from flickering between two words.", "g.WORD_BUFFER"),
        ("Lowest hype", f"{g.HYPE_MIN}x", "The mirror of the highest.", "g.HYPE_MIN"),
        ("Doubtful from", f"{g.COOLING_HYPE}x hype", "The mirror of Keen. Calm sits between them.", "g.COOLING_HYPE"),
        ("Rising or falling", f"{b.MOVE_MIN}", "Interest must move this much in a month to show as rising or falling.", "b.MOVE_MIN"),
        ("Confidence per boom", f"+{g.CONF_PER_HOT}", "Monthly confidence per booming good at full weight.", "g.CONF_PER_HOT"),
        ("Booms' most a month", f"+{g.CONF_BOOM_MAX}", "Cap on monthly confidence from booms.", "g.CONF_BOOM_MAX"),
        ("Boom size, base", f"{g.FIN_BOOM_BASE}", "Before the finance techs add to it.", "g.FIN_BOOM_BASE"),
        ("Full-weight share", pct(g.EXPOSURE_FULL), "A good with this share of the market's trade counts in full.", "g.EXPOSURE_FULL"),
        ("Glut interest", f"{g.GLUT_HYPE}x", "A glut sets interest to this, Doubtful.", "g.GLUT_HYPE"),
    ]),
    ("Boom endings", "What each ending costs in confidence, and how long the good then sits in a glut.", [
        ("Collapse cost", f"{g.UNWINDS[0][3]:g} per hype point", f"Peaked at Feverish. The good then sits in a glut for {g.UNWINDS[0][4]} months.", "g.CONF_PER_CRASH_HYPE"),
        ("Bust cost", f"{g.UNWINDS[1][3]:g} per hype point", f"Peaked at Eager. The good then sits in a glut for {g.UNWINDS[1][4]} months.", "g.UNWINDS"),
        ("Correction cost", f"{g.UNWINDS[2][3]:g} per hype point", f"Peaked at Keen. The good then sits in a glut for {g.UNWINDS[2][4]} months.", "g.UNWINDS"),
        ("Collapse needs", f"{g.PEAK_FOR_CRASH}x peak", "A good must peak this high, then fall to its opposite.", "g.PEAK_FOR_CRASH"),
        ("Collapse ends below", f"{g.CRASH_BELOW}x", "Fleeing, the mirror of Feverish.", "g.CRASH_BELOW"),
        ("Most lost in a month", f"-{g.CONF_CRASH_MAX}", "Cap on confidence lost to boom endings in one month.", "g.CONF_CRASH_MAX"),
    ]),
    ("Mania and the bubble", "What builds up at high confidence, and the price when it bursts.", [
        ("Bubble builds from", f"{g.HEAT_FROM} confidence", "Months above this add to the bubble.", "g.HEAT_FROM"),
        ("Bubble bursts below", f"{g.BURST_BELOW} confidence", "Falling under this bursts it.", "g.BURST_BELOW"),
        ("Bubble cools", pct(g.HEAT_COOL), "How much is kept each month in between.", "g.HEAT_COOL"),
        ("Bubble cools, Tight credit", pct(g.HEAT_COOL_TIGHT), "Kept each month in between under a Tight credit policy.", "g.HEAT_COOL_TIGHT"),
        ("Burst per point", f"{g.BURST_PER_HEAT}", "Confidence lost per point of bubble.", "g.BURST_PER_HEAT"),
        ("Biggest burst", "no cap", f"Takes the confidence it finds, under {g.BURST_BELOW}; each point past that is a point of Bad Debts. Was -40 until 1.2.", "l.ON_BURST"),
        ("Heightened volatility", f"from {g.VOLATILITY['heightened']['heat']}, {g.VOLATILITY['heightened']['per']} a point, booms x{g.VOLATILITY['heightened']['boom']}", "The game rule's stronger setting.", "g.VOLATILITY"),
        ("Mania event levy", f"{pct(g.MANIA_TAX)} of GDP, -{g.MANIA_TAX_CONF} confidence", "The levy option in the mania event.", "g.MANIA_TAX"),
        ("Mania warning", f"-{g.MANIA_CAUTION}", "Confidence the warning option takes off.", "g.MANIA_CAUTION"),
        ("Mania resets below", f"{g.MANIA_RESET} confidence", "A mania ends when confidence falls under this.", "g.MANIA_RESET"),
        ("Restrained peak keeps", pct(g.RESTRAIN_DEFLATE), "A restrained boom's excess kept each month.", "g.RESTRAIN_DEFLATE"),
    ]),
    ("Financial Panic", "How long it lasts and what it leaves behind.", [
        ("Length", f"{g.PANIC_DAYS} days", "Rounded up to 7 months, before the economic law scales it.", "g.PANIC_DAYS"),
        ("Ends early at", f"{g.PANIC_ENDS_AT}", "Confidence at which a panic ends before its months run out.", "g.PANIC_ENDS_AT"),
        ("Cooldown", f"{g.PANIC_COOLDOWN} months", "Before another can start.", "g.PANIC_COOLDOWN"),
        ("Length by legitimacy", "x0.8 to x1.2", "Low legitimacy lengthens it. Written straight into the formula.", "g.PANIC_DAYS"),
        ("Length by leverage", f"+{pct(g.PANIC_LEV_LEN)} a month past {g.leverage.SAFE}, to x{1 + g.PANIC_LEV_LEN * (g.leverage.RUIN - g.leverage.SAFE):g}",
         "Set as it starts. No cap on the length.", "g.PANIC_LEV_LEN"),
        ("Private construction cut", f"{pct(g.CRUNCH_FLOOR)} to all, by leverage {g.leverage.SAFE} to {g.leverage.DANGER} months",
         "Of the economic law's private share. A rescue halves it.", "g.CRUNCH_FLOOR"),
        ("Financial District pay", f"{c.FD_MANIA:+g} in mania, {c.FD_PANIC:+g} in a panic", "Standard of Living of its workers. A rescue halves the panic's.", "c.FD_PANIC"),
        ("Company bonus in a panic", f"{c.PANIC_COMPANY:+g}", "Company throughput bonus while it lasts.", "c.PANIC_COMPANY"),
    ]),
    ("Panics spreading", "How a panic reaches other countries.", [
        ("Contagion", f"-{g.CONTAGION}", "Confidence a tied country loses, before ties scale it.", "g.CONTAGION"),
        ("Tie strength", pairs(g.LINKS, lambda n: f"{n:g}"), "Share of contagion by kind of tie.", "g.LINKS"),
        ("Trade reliance", pct(g.TRADE_RELIANCE), "Relying this much on trade with a market counts as a tie.", "g.TRADE_RELIANCE"),
        ("Ownership tie", f"{pct(g.OWNED_FROM)} to {pct(g.OWNED_FULL)}", "Share owned where the tie starts, and where it is full.", "g.OWNED_FROM"),
        ("Reach by rank", f"Great Power {g.REACH[7]:g}, Major Power {g.REACH[6]:g}", "How far a panic carries from a country of this rank.", "g.REACH"),
        ("Reach of minors", f"{g.REACH_MINOR}", "The same for minor countries.", "g.REACH_MINOR"),
        ("Trade tie by policy", pairs(t.TRADE_TIE, lambda n: f"x{n:g}"), "Trade policy law scales the trade tie.", "t.TRADE_TIE"),
        ("Exchange Standards", f"x{t.EXCHANGE_TIE}", "Market and investment ties with this tech.", "t.EXCHANGE_TIE"),
        ("Capital flight gain", f"+{d.FLIGHT_GAIN}", "A safe Great Power gains this when another panics, before its techs.", "d.FLIGHT_GAIN"),
        ("Capital flight from", f"{d.FLIGHT_FROM} confidence", "Only at Steady or better.", "d.FLIGHT_FROM"),
        ("Flight base", f"{g.FLIGHT_BASE}", "Share of the gain with no techs.", "g.FLIGHT_BASE"),
        ("Without Currency Standards", f"x{g.UNSTANDARD[1]}", "Contagion for countries without it.", "g.UNSTANDARD"),
        ("Caught, not home grown", f"{g.CAUGHT_FROM}+ hit, {g.CAUGHT_DAYS} days", "A panic this soon after a hit this big from abroad passes nothing on.", "g.CAUGHT_DAYS"),
    ]),
    ("Rescue and Credit Policy", "The government's tools, and how the AI uses them.", [
        ("Rescue cost", f"{pct(g.RESCUE_COST_PRIVATE)} of GDP, {pct(g.RESCUE_COST)} with Central Banking", "Lend to the Banks.", "g.RESCUE_COST"),
        ("Rescue ends panic in", f"{g.RESCUE_MONTHS_PRIVATE} months, {g.RESCUE_MONTHS} with Central Banking", "How soon it finishes the panic.", "g.RESCUE_MONTHS"),
        ("Rescue confidence", f"+{g.RESCUE_CONF}", "Confidence a rescue gives back.", "g.RESCUE_CONF"),
        ("Rescue price scale", f"x{g.RESCUE_SCALE[0]} to x{g.RESCUE_SCALE[1]}, set at {g.RESCUE_REF_MONTHS} months left", "The cost scales with how much panic is left to cut short.", "g.RESCUE_SCALE"),
        ("Stance cooldown", f"{g.STANCE_COOLDOWN} months", "Before Credit Policy can change again.", "g.STANCE_COOLDOWN"),
        ("Tight pull", f"{pct(g.TIGHT_PULL)} above {g.TIGHT_FROM}", "How Tight credit pulls down high confidence.", "g.TIGHT_PULL"),
        ("AI cools at", f"{a.AI_TIGHT} confidence", "The AI turns Tight above this.", "a.AI_TIGHT"),
        ("Temperament shift", f"±{a.TEMPER_SHIFT}", "Confidence a bold or cautious AI moves its lines.", "a.TEMPER_SHIFT"),
        ("Temperament odds", f"{a.TEMPERS[-1][0]} / {a.TEMPERS[0][0]} / {a.TEMPERS[1][0]}", "Base weights for cautious, ordinary and bold. Rulers, heirs and laws shift them.", "a.TEMPERS"),
        ("Interest group shift", f"±{a.IG_SHIFT}", "Each interest group in government with a view.", "a.IG_SHIFT"),
        ("Interest group approval", f"±{a.IG_APPROVAL}", "Approval for the stance a group prefers.", "a.IG_APPROVAL"),
        ("AI rescue chance", f"{a.RESCUE_CHANCE[-1]}% / {a.RESCUE_CHANCE[0]}% / {a.RESCUE_CHANCE[1]}%", "A month, cautious, ordinary and bold.", "a.RESCUE_CHANCE"),
    ]),
    ("Technology and laws", "What finance techs and economic laws change.", [
        ("Boom size techs", pairs(g.FIN_BOOM, lambda n: f"+{n:g}"), "Added to the base boom size.", "g.FIN_BOOM"),
        ("Mutual Funds", f"x{g.FIN_RISK['mutual_funds']}", "Boom-ending losses.", "g.FIN_RISK"),
        ("Modern Financial Instruments", f"x{g.FIN_LEVERAGE[1]}", "Booms and boom-ending losses.", "g.FIN_LEVERAGE"),
        ("Macroeconomics", f"x{g.MACRO[1]}", "The drift back to rest, and own recovery from the Long Depression.", "g.MACRO"),
        ("Joint-Stock Companies", f"x{t.STOCK_HYPE}", "Hype.", "t.STOCK_HYPE"),
        ("Flight techs", pairs(g.FLIGHT_TECHS, lambda n: f"+{n:g}"), "Added to capital flight.", "g.FLIGHT_TECHS"),
        ("Interest by law", laws(1), "How strongly hype moves investors.", "g.LAWS"),
        ("Panic length by law", laws(2), "Scales panic length.", "g.LAWS"),
    ]),
    ("Banking Reforms and journal choices", "What a Commission of Inquiry can bring in, and the other choices in the journal entry.", [
        ("Notes tied to gold", f"lending x{R['currency']['credit']}, bubble x{R['currency']['heat']}, panics x{R['currency']['panic_len']}", "Safer and slower. Allows suspending the Bank Act.", "j.REFORMS"),
        ("Free note issue", f"lending x{R['free']['credit']}, booms x{R['free']['boom']}, losses x{R['free']['risk']}", "Faster and riskier.", "j.REFORMS"),
        ("Lender of last resort", f"rescue cost x{R['llr']['rescue']}, {-R['llr']['rescue_months']} month sooner", "Cheaper, quicker rescues.", "j.REFORMS"),
        ("Published accounts", f"losses x{R['company']['risk']}", "Softer boom endings.", "j.REFORMS"),
        ("Debt conversion needs", pct(j.CONVERT_DEBT), "Debt against the credit limit needed to convert.", "j.CONVERT_DEBT"),
        ("Conversion length", f"{j.CONVERT_YEARS} years, again after {j.CONVERT_COOLDOWN_YEARS}", "How long it lasts, and the wait to do it again.", "j.CONVERT_YEARS"),
        ("Conversion confidence", f"-{j.CONVERT_CONF}", "Confidence lost by converting.", "j.CONVERT_CONF"),
        ("Conversion rate", signed(j.CONVERT_RATE), f"Loan interest while converted, until the debt falls below {j.CONVERT_DEBT:.0%} of the credit limit.", "j.CONVERT_RATE"),
        ("Relief length", f"{j.RELIEF_MONTHS} months", "How long relief lasts.", "j.RELIEF_MONTHS"),
        ("Suspend the Bank Act", f"panic down to {j.SUSPEND_MONTHS} months, +{j.SUSPEND_CONF} confidence", f"Costs {j.SUSPEND_LEGIT} legitimacy for {j.SUSPEND_YEARS} years.", "j.SUSPEND_MONTHS"),
        ("After a suspension", f"bubble x{j.HAZARD_HEAT} for {j.HAZARD_YEARS} years", "Investors count on the next one.", "j.HAZARD_HEAT"),
        ("Sound finance reward", f"+{j.SOUND_PRESTIGE} prestige", "The Sound Finance modifier.", "j.SOUND_PRESTIGE"),
        ("Inquiry after calm", f"{j.INQUIRY_CALM} months", "Panic-free months before an inquiry can sit outside an aftermath.", "j.INQUIRY_CALM"),
        ("Inquiry sitting", f"{j.INQUIRY_MONTHS} months, Authority {signed(j.INQUIRY_AUTHORITY)}", "How long it sits and what it costs meanwhile.", "j.INQUIRY_MONTHS"),
        ("Bubble alert", f"{j.BUBBLE_ALERT} confidence", "Shows once a burst would cost this much.", "j.BUBBLE_ALERT"),
        ("Bubble bar top", f"{j.EXCESS_MAX}", "Where the bar fills: a pop this big takes all the confidence a pop can find. Past it, a pop also leaves Bad Debts.", "j.EXCESS_MAX"),
    ]),
    ("War and diplomacy", "What wars do to confidence.", [
        ("Any war", f"-{d.WAR_BASE} a month", "However it's going.", "d.WAR_BASE"),
        ("Average war target", f"-{d.WAR_COST} a month", "What the rows below aim to add up to.", "d.WAR_COST"),
        ("Monthly range, all wars", f"{g.WAR_ALL_MIN:g} to {g.WAR_ALL_MAX:+g}", "Cap on all wars together.", "g.WAR_ALL_MIN"),
        ("Casualties", war("casualties"), "Monthly range.", "d.WAR_ROWS"),
        ("GDP since the war began", war("gdp"), "Monthly range.", "d.WAR_ROWS"),
        ("Devastation", war("devastation"), "Monthly range.", "d.WAR_ROWS"),
        ("Battles", war("battles"), "Monthly range.", "d.WAR_ROWS"),
        ("Enemy land held", war("held"), "Monthly range.", "d.WAR_ROWS"),
        ("War pressure", war("pressure"), "Monthly range.", "d.WAR_ROWS"),
        ("Worst and best war month", f"{d.WAR_WORST} to {d.WAR_BEST:+g}", "All rows at their worst and best, with the base cost.", "d.WAR_WORST"),
        ("War end", pairs(d.WAR_END, lambda n: f"{n[0]:+g} / {n[1]:+g}"), "With a war goal enforced / without, at full stakes.", "d.WAR_END"),
        ("Small war's share", pct(d.WAR_STAKES_MIN), "Share of that when almost nobody died.", "d.WAR_STAKES_MIN"),
        ("Diplomatic play", f"-{d.PLAY_TURMOIL} a month", "During a play while not at war.", "d.PLAY_TURMOIL"),
    ]),
    ("Economy", "Growth, default and running out of money.", [
        ("Growth effect", f"{e.GROWTH_K} per 100%", "Monthly confidence from GDP above its year average.", "e.GROWTH_K"),
        ("Growth cap", f"±{e.GROWTH_MAX} a month", "Most growth can give or take.", "e.GROWTH_MAX"),
        ("Normal growth", pct(e.GROWTH_NORMAL), "Growth that counts as nothing special.", "e.GROWTH_NORMAL"),
        ("GDP average keeps", pct(e.GROWTH_KEEP), "About a year's memory.", "e.GROWTH_KEEP"),
        ("Default cost", f"-{e.DEFAULT_COST} a month", "Confidence during a default.", "e.DEFAULT_COST"),
        ("Default warning from", pct(e.DEFAULT_FROM), "Share of the credit limit borrowed.", "e.DEFAULT_FROM"),
        ("Running out warning", f"{e.BROKE_WEEKS} weeks", "Starts this long before bankruptcy.", "e.BROKE_WEEKS"),
        ("Running out cost", f"up to -{e.BROKE_COST} a month", "Rises to this at the last moment.", "e.BROKE_COST"),
        ("Business approval", " / ".join(f"{row[2]:+g}" for row in e.BUSINESS), "Monthly confidence from Industrialists' approval at +10, +5, -10, -5.", "e.BUSINESS"),
    ]),
    ("Long Depression", "The worldwide slump.", [
        ("Earliest year", f"{dp.EARLIEST_YEAR} to {dp.EARLIEST_YEAR + dp.EARLIEST_SPREAD}", "Rolled once a game.", "dp.EARLIEST_YEAR"),
        ("Second one", f"{dp.SECOND_CHANCE}% of games", "Can follow from another Great Power.", "dp.SECOND_CHANCE"),
        ("Most per game", f"{dp.MAX_PER_GAME}", "Long Depressions in one game.", "dp.MAX_PER_GAME"),
        ("Gap between", f"{dp.COOLDOWN_YEARS} years", "After the recovery ends.", "dp.COOLDOWN_YEARS"),
        ("Join window", f"{dp.WINDOW_DAYS} days", "Countries that panicked this recently join when it starts.", "dp.WINDOW_DAYS"),
        ("Spread needs", f"{dp.SPREAD_MIN}", "Tie strength needed to be drawn in.", "dp.SPREAD_MIN"),
        ("Phases", f"crash {dp.CRASH_MONTHS}, up to {dp.DEPRESSION_MAX}, recovery {dp.RECOVERY_MONTHS} months", "Length of each phase.", "dp.DEPRESSION_MAX"),
        ("Monthly pressure", f"{dp.PRESSURE[1]} / {dp.PRESSURE[2]} / {dp.PRESSURE[3]:+g}", "Confidence in crash, depression, recovery.", "dp.PRESSURE"),
        ("World recovery", f"{dp.WORLD_DRIFT} a month", "Base recovery of the world gauge.", "dp.WORLD_DRIFT"),
        ("Own recovery", f"{dp.OWN_DRIFT} a month", "A country's own recovery.", "dp.OWN_DRIFT"),
        ("Tariff hit", f"-{dp.TARIFF_HIT}", "Confidence a tied partner loses to our tariffs.", "dp.TARIFF_HIT"),
        ("Event chance", f"{dp.EVENT_CHANCE}% a month, {dp.EVENT_GAP} days apart", "Depression events.", "dp.EVENT_CHANCE"),
        ("World gauge choices", pairs(dp.WORLD, lambda n: f"{n[0]:+g} / {n[1]:+g}"), "What an event choice adds. Great Power / other.", "dp.WORLD"),
        ("Crash modifier", ld("spec_ld_crash"), "On countries in the crash phase.", "dp.MODS"),
        ("Depression modifier", ld("spec_ld_depression"), "On countries in the depression phase.", "dp.MODS"),
    ]),
    ("Market interventions", "Restrain Speculation and Encourage Investment.", [
        ("Throughput", f"±{pct(v.LEVER_THROUGHPUT)}", "For the good's producers.", "v.LEVER_THROUGHPUT"),
        ("Subsidy", pct(v.SUBSIDY_SHARE), "Encourage's cost, of weekly output at base price.", "v.SUBSIDY_SHARE"),
        ("Levy", pct(v.LEVY_SHARE), "Restrain's income, on the same base.", "v.LEVY_SHARE"),
        ("Authority cost", pct(v.LEVER_TAX_SHARE), "Share of the good's vanilla tax cost.", "v.LEVER_TAX_SHARE"),
        ("Authority floor", pct(v.LEVER_FLOOR), "Least a small good's cost falls to.", "v.LEVER_FLOOR"),
        ("Default Authority", f"{v.DEFAULT_TAX_COST}", "Where a good has no tax cost.", "v.DEFAULT_TAX_COST"),
        ("Authority rounding", f"{v.COST_STEP}", "The cost rounds to this.", "v.COST_STEP"),
        ("Push build-up", pct(v.LEVER_EASE), "Share of the gap to the full push closed each month.", "v.LEVER_EASE"),
        ("Restrain push", f"x{v.PUSH['restrain']:.2f}", f"At confidence {v.PUSH_CONF}; m/(m+{1 / v.PUSH['restrain'] - 1:.2g}) with m = confidence/{v.PUSH_CONF}, weaker as confidence rises. Times what the market makes of interest, never below {v.RESTRAIN_TO}x (Calm). Was flat until 1.2.", "v.PUSH"),
        ("Encourage push", f"x{v.PUSH['encourage']:g}", f"At confidence {v.PUSH_CONF}; 1 + {v.PUSH['encourage'] - 1:.2g}m with m = confidence/{v.PUSH_CONF}, stronger as confidence rises. Times what the market makes of interest. Was flat until 1.2.", "v.PUSH"),
        ("Restrain needs", f"end costing {v.RESTRAIN_RISK}+", "Or Eager interest or more.", "v.RESTRAIN_RISK"),
        ("Encourage needs", f"below interest {v.ENCOURAGE_BELOW}", "Below Keen.", "v.ENCOURAGE_BELOW"),
        ("AI restrains at", f"{v.AI_CONF} confidence, risk {v.AI_RISK}+", "Its riskiest boom.", "v.AI_CONF"),
        ("AI encourages with", f"{v.AI_FUNDS}x the subsidy", "Weekly surplus needed.", "v.AI_FUNDS"),
    ]),
    ("Companies and building output", "What interest does to buildings and companies.", [
        ("Throughput by interest", ", ".join(f"{c.TIER_WORDS[k]} {val:+g}%" for k, val in c.INTEREST_THROUGHPUT.items()), "For the buildings that make the good.", "c.INTEREST_THROUGHPUT"),
        ("Company bust", signed(c.COMPANY_BUST), f"After a collapse, for {c.UNWIND[3][1]} days. Busts take {pct(c.UNWIND[2][0])} of that for {c.UNWIND[2][1]}, corrections {pct(c.UNWIND[1][0])} for {c.UNWIND[1][1]}.", "c.COMPANY_BUST"),
        ("Company tie per tech", f"+{c.TIE_PER_TECH}", "Each corporate tech strengthens the tie.", "c.TIE_PER_TECH"),
        ("Financial District range", f"x{t.DEPTH_MIN} to x{t.DEPTH_MAX}, x1 at {pct(t.FD_SHARE_FULL)}", "Market depth from Financial Districts. It scales both hype and crashes.", "t.FD_SHARE_FULL"),
        ("Market depth words", f"Shallow under {t.DEPTH_WORDS[0]}, Deep over {t.DEPTH_WORDS[1]}", "Labels only.", "t.DEPTH_WORDS"),
        ("Steadiness range", f"x{t.STEADY_MIN} to x{t.STEADY_MAX}", "An economy more landed than typical moves less, a more financial one moves more.", "t.STEADY_MIN"),
        ("Landed share", f"typical {t.MANOR_TYPICAL}, steady {t.MANOR_STEADY}", "The shares that set the range above.", "t.MANOR_TYPICAL"),
    ]),
    ("Stories and politics", "Flavor events and movements.", [
        ("Story chance", f"{s.STORY_CHANCE}% a month", "A valid story event fires.", "s.STORY_CHANCE"),
        ("Story gap", f"{s.STORY_GAP} days", "Between story events.", "s.STORY_GAP"),
        ("Story hush", f"{s.HUSH} days", "None after a mania or panic starts.", "s.HUSH"),
        ("Warning from", f"{s.WARN_EXPOSURE} confidence at risk", "The press sounds the alarm.", "s.WARN_EXPOSURE"),
        ("Collapse makes a story", f"{s.CRASH_SEEN} confidence", "A month's collapse at or below this.", "s.CRASH_SEEN"),
        ("Foreign panic story", f"{s.FOREIGN_SEEN} confidence", "A foreign panic's hit at or below this.", "s.FOREIGN_SEEN"),
        ("Story memory", f"{s.REMEMBER} days", "How long either is remembered.", "s.REMEMBER"),
        ("Story delay", f"{s.STORY_DELAY} days", "After the monthly check, so the month's update has run.", "s.STORY_DELAY"),
        ("Panic movements", pairs(m.PANIC, lambda n: f"{n:+g}"), "Movement pressure after a panic.", "m.PANIC"),
        ("Mania movements", pairs(m.MANIA, lambda n: f"{n:+g}"), "After a long or large mania.", "m.MANIA"),
        ("Mania heat", f"{m.HEAT} over {m.HEAT_BASE}", "Heat needed: 12 months at 80, 6 at 90, 4 at 100.", "m.HEAT"),
    ]),
]

MODULES = {"l": l, "g": g, "t": t, "c": c, "d": d, "dp": dp, "e": e, "a": a, "j": j, "v": v, "s": s, "m": m, "x": x, "b": b}


def tuner_names(text):
    """Names assigned from tuning.get, pairing A, B = x, y so the plain numbers beside them don't count."""
    names = set()
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            target, value = node.targets[0], node.value
            pairs_ = zip(target.elts, value.elts) if isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple) else [(target, value)]
            names |= {n.id for n, val in pairs_ if isinstance(n, ast.Name) and "tuning.get" in ast.unparse(val)}
    return names


def page():
    rows = sum(len(r) for _, _, r in GROUPS)
    tunable = {k: tuner_names(Path(mod.__file__).read_text(encoding="utf-8")) for k, mod in MODULES.items()}
    body = []
    for title, intro, items in GROUPS:
        trs = []
        for label, value, what, code in items:
            mod, name = code.split(".")
            assert hasattr(MODULES[mod], name), code
            tags = ('<span class="tag new">0.8</span>' if code in WAS or title == "Leverage" else "") + ('<span class="tag">tuner</span>' if name in tunable[mod] else "")
            what = f"{what} Was {WAS[code]} in 0.7." if code in WAS else what
            trs.append(f'<tr><th scope="row">{html.escape(label)}{tags}</th><td class="v">{html.escape(value)}</td><td>{html.escape(what)}</td><td class="c">{name}</td></tr>')
        body.append(f'<section><h2>{html.escape(title)} <small>{len(items)}</small></h2><p>{html.escape(intro)}</p><div class="wrap"><table>'
                    f'<thead><tr><th scope="col">Setting</th><th scope="col">Now</th><th scope="col">What it does</th><th scope="col">Name in code</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div></section>')
    nav = "".join(f'<a href="#{re.sub("[^a-z]+", "-", t_.lower())}">{html.escape(t_)}</a>' for t_, _, _ in GROUPS)
    sections = "\n".join(b.replace("<section>", f'<section id="{re.sub("[^a-z]+", "-", GROUPS[i][0].lower())}">', 1) for i, b in enumerate(body))
    return (Path(__file__).with_name("values_table.html").read_text(encoding="utf-8")
            .replace("{{ROWS}}", str(rows)).replace("{{GROUPS}}", str(len(GROUPS))).replace("{{NAV}}", nav).replace("{{SECTIONS}}", sections))


if __name__ == "__main__":
    OUT.write_text(page(), encoding="utf-8", newline="\n")
    print(sum(len(r) for _, _, r in GROUPS), "settings in", len(GROUPS), "groups")
