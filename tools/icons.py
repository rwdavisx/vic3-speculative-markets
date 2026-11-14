"""The mod's own icons. Codex paints each one into art/raw/<name>.png; build() trims, squares and resizes it into a
DDS in the mod. A slot without art yet falls back to the vanilla icon it replaces (or to nothing), so the mod
always builds and each icon switches over as soon as its painting exists."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ART = Path(__file__).resolve().parent.parent / "art" / "raw"
DIR = "gfx/interface/icons/spec_markets"
V = "gfx/interface/icons"

# name: (size in pixels, vanilla fallback or None, what to paint)
SLOTS = {
    # Boom Ending tiers (generate.UNWINDS 1 to 3), one family that worsens: build() sets each on a tinted medallion
    # with its numeral, as vanilla's acceptance tiers and commander ranks
    "ending_0": (128, None, "a neat upright stack of gold coins standing firm and level on a solid stone plinth, calm and secure"),
    "ending_1": (128, None, "a tall stack of gold coins leaning slightly, its top three coins sliding off"),
    "ending_2": (128, None, "a stack of gold coins broken in half, coins tumbling and scattering, one torn share certificate"),
    "ending_3": (128, None, "a small classical bank building collapsing, a fallen column and cracked pediment, coins spilling from the rubble"),
    # the Exchange's four Standings (centres.tier), one family: iron, bronze, silver, gold
    **{f"exch_tier_{t}": (96, f"{V}/company_charter_icons/investment_charter.dds", d) for t, d in enumerate([
        "a plain iron-grey medallion with a small market hall", "a bronze medallion with a columned exchange building",
        "a silver medallion with the exchange building between laurel branches",
        "a gold medallion with a globe under a small crown, in a laurel wreath"])},
    # the Banking tab's Bank Rescue block: the panic card and the pledge row
    "bank_rescue": (128, f"{V}/alert_icons/bankruptcy.dds", "a red and white cork life ring hanging on the front of a small classical bank building with columns"),
    "rescue_pledge": (128, f"{V}/diplomatic_action_icons/guarantee_independence.dds", "a folded parchment bond tied with a ribbon and sealed with a large red wax seal, resting on a small stack of gold coins"),
    "state_panic": (256, f"{V}/invention_icons/investment_banks.dds",
                    "a crowd's raised hands at the closed iron doors of a bank, a torn share certificate on the ground"),
    "state_wary": (256, f"{V}/invention_icons/investment_banks.dds",
                   "a brass stock ticker machine with its paper tape curling downward, a few coins beside it"),
    "state_steady": (256, f"{V}/invention_icons/investment_banks.dds",
                     "a neat stack of share certificates tied with a ribbon beside a small stack of gold coins"),
    "state_buoyant": (256, f"{V}/invention_icons/investment_banks.dds",
                      "share certificates fanned out on top of growing stacks of gold coins, a small green ledger"),
    "state_mania": (256, f"{V}/invention_icons/investment_banks.dds",
                    "an overflowing heap of gold coins and share certificates spilling from an open strongbox"),
    "mod_panic": (120, f"{V}/timed_modifier_icons/modifier_coins_negative.dds",
                  "a torn share certificate, the whole object tinted dull red like the attached red coin modifier icon"),
    "mod_crunch": (120, f"{V}/timed_modifier_icons/modifier_coins_negative.dds",
                   "a padlocked strongbox, the whole object tinted dull red like the attached red coin modifier icon"),
    "mod_tight": (120, f"{V}/timed_modifier_icons/modifier_coins_negative.dds",
                  "a coin purse pulled shut with a cord, the whole object tinted dull red like the attached red coin modifier icon"),
    "mod_loose": (120, f"{V}/timed_modifier_icons/modifier_coins_positive.dds",
                  "an open coin purse with coins spilling out, the whole object tinted green like the attached green coin modifier icon"),
    "je_markets": (150, f"{V}/event_icons/event_trade.dds",
                   "a 19th century stock exchange building facade with a rising line of share prices on a paper chart in front"),
    "event_mania": (150, f"{V}/event_icons/event_trade.dds",
                    "a champagne glass standing on a pile of share certificates and gold coins"),
    "event_panic": (150, f"{V}/event_icons/event_protest.dds",
                    "a bank ledger slammed shut with scattered falling share certificates around it"),
    "crash_risk": (120, f"{V}/generic_icons/warning.dds",
                   "a gold coin split by a deep jagged crack through its middle, the two halves slightly apart, bold dark outline so it reads clearly at 24 pixels"),
    "driver_boom": (64, None, "a stack of gold coins with a small upward arrow made of brass"),
    "driver_crash": (64, None, "a broken stack of coins toppling over"),
    "driver_turmoil": (64, None, "a cannon ball resting on a torn banknote"),
    "driver_tight": (64, None, "a coin purse pulled shut with a cord"),
    "driver_foreign": (64, None, "a globe on a brass stand with a crack running across it"),
    # the per-good speculation levers' toggle buttons
    "lever_restrain": (64, f"{V}/generic_icons/map_list_lock.dds",
                       "a rolled share certificate bound tight with an iron chain and a closed brass padlock, "
                       "bold dark outline so it reads clearly at 24 pixels"),
    "lever_encourage": (64, f"{V}/generic_icons/upgrade_arrow.dds",
                        "a gloved hand offering a small stack of gold coins, a green upward arrow above it, "
                        "bold dark outline so it reads clearly at 24 pixels"),
    "lever_issue": (64, f"{V}/timed_modifier_icons/modifier_coins_positive.dds",
                    "a crisp new share certificate with an ornate border and a red wax seal, a small brass bell ringing "
                    "above it, bold dark outline so it reads clearly at 24 pixels"),
}
# investor interest in a good, var:spec_word 1..6: one family of gold coins that heats up from Fleeing to Feverish
_OUTLINE = ", bold dark outline so it reads clearly at 24 pixels"
SLOTS.update({f"interest_{w}": (64, f"{V}/{fb}.dds", d + _OUTLINE) for w, fb, d in [
    ("fleeing", "generic_icons/down_down",
     "a tipped over leather coin purse with gold coins rolling and flying away from it to one side"),
    ("doubtful", "timed_modifier_icons/modifier_coins_negative",
     "a brass balance scale tipped steeply to one side, a single gold coin on the low pan and the high pan empty"),
    ("calm", "ai_attitude_icons/disinterested",
     "a brass balance scale hanging perfectly level with an equal small stack of gold coins on each pan"),
    ("keen", "timed_modifier_icons/modifier_coins_positive",
     "two short stacks of gold coins, the right one a little taller, one more coin dropping onto it"),
    ("eager", "generic_icons/up_up",
     "three stacks of gold coins rising like stairs from left to right with a green upward arrow climbing over them"),
    ("feverish", "timed_modifier_icons/modifier_fire_negative",
     "a copper kettle boiling over with gold coins on bright orange flames, coins and steam bursting from under the lid"),
]})

# the names an Exchange can be known for (centres.NAMES): Codex paints each (art/raw/name_<key>.png)
SLOTS.update({f"name_{k}": (128, f"{V}/{fb}.dds", d) for k, fb, d in [
    ("price", "invention_icons/international_exchange_standards", "a wooden auctioneer's gavel on a sack of grain with a price tag"),
    ("harbour", "invention_icons/banking", "a heavy dark-green iron safe with a brass anchor emblem"),
    ("companies", "invention_icons/stock_exchanges", "a bundle of share certificates tied with a red ribbon and wax seal"),
    ("floor", "building_icons/building_trade_center", "a brass hand bell on a wooden stand with order slips"),
    ("sound", "invention_icons/investment_banks", "an open ledger with a quill and a neat stack of gold coins"),
    ("pockets", "invention_icons/mutual_funds", "a fat leather money bag with gold coins spilling out"),
    ("door", "generic_icons/diplomatic_treaties", "a rolled treaty with ribbon and seal before a half-open door"),
]})


def has(name):
    return (ART / f"{name}.png").exists()


def path(name):
    """Texture path for a slot: the mod's own icon once painted, else its vanilla fallback (None means no icon)."""
    return f"{DIR}/{name}.dds" if has(name) else SLOTS[name][1]


TEXT_ICONS = [n for n in SLOTS if n.startswith(("interest_", "ending_"))]  # in loc as @spec_interest_<word>! and @spec_ending_<n>!


def texticons():
    """gui/spec_texticons.gui, sized like vanilla's goods text icons."""
    return "".join(f"""texticon = {{
	icon = spec_{n}
	iconsize = {{
		texture = "{path(n)}"
		size = {{ 22 22 }}
		offset = {{ 0 6 }}
		fontsize = 18
	}}
}}
""" for n in TEXT_ICONS)


# vanilla icons measured on opaque pixels (60 icons: inventions, goods, events, modifiers, buildings): mean saturation
# 0.33, luminance spread 47, mean luminance 115. The paintings averaged 0.50 / 52 / 105, so every one loses the same
# share of saturation (a gold icon stays gold, just less loud) and is brought to vanilla's contrast and brightness.
SAT_CUT = 0.72
VANILLA_SPREAD, VANILLA_MEAN = 47, 115


def opaque_stats(im):
    px = [p for p in im.resize((96, 96)).getdata() if p[3] > 200]
    lum = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _ in px]
    sat = [(max(p[:3]) - min(p[:3])) / max(max(p[:3]), 1) for p in px]
    mean = sum(lum) / len(lum)
    spread = (sum((x - mean) ** 2 for x in lum) / len(lum)) ** 0.5
    return sum(sat) / len(sat), spread, mean


def grade(im):
    """Bring a painting's saturation, contrast and brightness to vanilla's, never pushing them up much."""
    sat, spread, mean = opaque_stats(im)
    alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(SAT_CUT)
    # contrast about the object's own mean: ImageEnhance.Contrast would count the transparent background too
    m = round(mean)
    rgb = Image.blend(Image.new("RGB", rgb.size, (m, m, m)), rgb, min(1.0, max(0.75, VANILLA_SPREAD / spread)))
    rgb = ImageEnhance.Brightness(rgb).enhance(min(1.25, max(0.95, VANILLA_MEAN / mean)))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


# Boom Ending tiers: the medallion's tint (generate.UNWINDS severity), from ochre to deep red, as vanilla's acceptance
# tiers tint theirs, and the numeral badge of its commander ranks
TIER_TINT = {0: (64, 104, 84), 1: (150, 118, 52), 2: (156, 84, 38), 3: (132, 40, 32)}
NUMERALS = {1: "I", 2: "II", 3: "III"}
NUMERAL_FONT = "G:/SteamLibrary/steamapps/common/Victoria 3/game/fonts/EBGaramond/EBGaramond-Bold.ttf"
BRONZE, DARK, CREAM = (176, 140, 78), (28, 24, 20), (246, 238, 220)


def medallion(obj, tier, side=512):
    """The painted object on a round tinted medallion with a bronze rim, and the tier's numeral in a badge below right."""
    out = Image.new("RGBA", (side, side))
    disc = Image.new("RGBA", (side, side))
    d = ImageDraw.Draw(disc)
    r, c = side * 0.46, side / 2
    tint = TIER_TINT[tier]
    for i in range(60, 0, -1):  # darker toward the rim
        k = 0.45 + 0.55 * (1 - i / 60) ** 0.6
        rr = r * i / 60
        d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=tuple(round(v * k) for v in tint) + (255,))
    d.ellipse((c - r, c - r, c + r, c + r), outline=DARK, width=round(side * 0.022))
    d.ellipse((c - r + side * 0.018, c - r + side * 0.018, c + r - side * 0.018, c + r - side * 0.018),
              outline=BRONZE, width=round(side * 0.012))
    out.alpha_composite(disc)
    o = obj.copy()
    o.thumbnail((round(side * 0.76), round(side * 0.76)), Image.LANCZOS)
    out.alpha_composite(o, ((side - o.width) // 2, round(side * 0.47 - o.height / 2)))
    if not tier:  # no risk: no numeral
        return out
    b, bc = side * 0.14, (side * 0.79, side * 0.79)
    d = ImageDraw.Draw(out)
    d.ellipse((bc[0] - b, bc[1] - b, bc[0] + b, bc[1] + b), fill=DARK, outline=BRONZE, width=round(side * 0.014))
    font = ImageFont.truetype(NUMERAL_FONT, round(side * (0.17 if tier < 3 else 0.13)))
    d.text(bc, NUMERALS[tier], font=font, fill=CREAM, anchor="mm")
    return out


def build(mod):
    out = []
    for name, (size, *_) in SLOTS.items():
        if not has(name):
            continue
        im = grade(Image.open(ART / f"{name}.png").convert("RGBA"))
        im = im.crop(im.getbbox() or (0, 0, *im.size))
        side = max(im.size)
        sq = Image.new("RGBA", (side, side))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        # a little breathing room like vanilla icons, then down to the size the game uses
        pad = round(side * 0.06)
        canvas = Image.new("RGBA", (side + 2 * pad, side + 2 * pad))
        canvas.paste(sq, (pad, pad))
        if name.startswith("ending_"):
            canvas = medallion(canvas, int(name[-1]))
        dest = mod / DIR / f"{name}.dds"
        dest.parent.mkdir(parents=True, exist_ok=True)
        canvas.resize((size, size), Image.LANCZOS).save(dest)
        out.append(name)
    gui = mod / "gui/spec_texticons.gui"
    gui.parent.mkdir(parents=True, exist_ok=True)
    gui.write_text(texticons(), encoding="utf-8-sig", newline="\n")
    return out
