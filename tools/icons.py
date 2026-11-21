"""The mod's own icons. Codex paints each one into art/raw/<name>.png; build() trims, squares and resizes it into a
DDS in the mod. A slot without art yet falls back to the vanilla icon it replaces (or to nothing), so the mod
always builds and each icon switches over as soon as its painting exists."""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

import law_metal

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
    ("futures", "building_icons/wheat_farm", "a sheaf of golden wheat bound with a paper futures contract and wax seal"),
    ("lender", "invention_icons/central_banking", "a bound government bond with a foreign crest beside a stack of gold coins"),
    ("railway", "invention_icons/railways", "a steam locomotive bursting through a share certificate"),
]})


def art(name):
    """A slot's painting; a law icon's is its flat emblem, which law_metal finishes."""
    return ART / ("emblem" if name.startswith("law_") else "") / f"{name}.png"


def has(name):
    return art(name).exists()


def path(name):
    """Texture path for a slot: the mod's own icon once painted, else its vanilla fallback (None means no icon)."""
    return f"{DIR}/{name}.dds" if has(name) else (SLOTS[name][1] if name in SLOTS else None)


# a blue chip company (companies.BLUE_*): its badge on the Companies rows, and @spec_blue_chip! in text
SLOTS["blue_chip"] = (64, f"{V}/company_charter_icons/investment_charter.dds",
                      "a round deep blue enamel medal with a polished gold rim and a small gold five-pointed star in its "
                      "centre, hanging from a short deep blue silk ribbon" + _OUTLINE)

# the Speculative Excess alert (journal.spec_bubble_alert), replacing vanilla's expensive goods
SLOTS["excess_alert"] = (100, f"{V}/alert_icons/expensive_goods.dds",
                         "a large iridescent soap bubble swelling up out of a heap of share certificates and gold coins, "
                         "a thin bright crack running across its skin as it is about to burst" + _OUTLINE)
# the Monetary Standard laws (monetary.py), in the style and size of vanilla's law icons
SLOTS.update({f"law_spec_{k}": (302, f"{V}/law_icons/{fb}.dds", d) for k, fb, d in [
    # layered, as vanilla's (laissez_faire's arrow behind its factory): every part apart from the next by a thin gap,
    # which law_metal inks and bevels, so the emblem has internal edges and is not one flat blob
    ("bimetallism", "mercantilism", "two round coins, the right one overlapping in front of the left one and separated "
     "from it by a thin transparent gap that follows its edge; each coin has a raised rim, shown by a thin transparent "
     "ring just inside its edge, and a plain round face with no hole; above them a small balance beam on a post, "
     "standing apart from the coins with a thin gap between"),
    ("gold_standard", "laissez_faire", "a trapezoid gold ingot seen from the front, its sloping top face drawn as a "
     "separate band split from the front face by a thin transparent gap, a small crown cut into the front face; an "
     "upward arrow standing behind the ingot, separated from it by a thin gap that follows the ingot's outline; a flat "
     "base bar under the ingot, apart from it by a thin gap"),
    ("fiat_money", "interventionism", "three rectangular banknotes fanned out, each lying in front of the one behind, "
     "separated by thin transparent gaps that follow the front note's edge; the front note has a thin transparent "
     "border line just inside its edge like an engraved frame, and a round seal in its middle with a raised rim shown "
     "by a thin transparent ring"),
]})
# vanilla's law icons are flat emblems: a silhouette with cut-out details, in one painted metal finish. paint.sh
# draws the emblem (art/raw/emblem/) and law_metal gives it vanilla's metal
LAW_EMBLEM = (" Draw it as a FLAT EMBLEM exactly like the attached law icons: one bold simple silhouette with cut-out "
              "holes and gaps for its details, no perspective, no shading, no outline drawing, a single plain light grey "
              "fill on a transparent background.")
# the Financial Integration power bloc principle (power_bloc.py), on vanilla's tier backgrounds as its principle icons
SLOTS["principle_financial_integration"] = (210, f"{V}/principles_icons/foreign_investment.dds",
                                            "three gold coins of different national mints linked together by a single gold chain, "
                                            "resting on a ledger, in the flat engraved style of vanilla's principle icons")
# Rival Exchanges (rivals.py): the action cards, the two parts' headers
SLOTS.update({f"rival_{k}": (96, f"{V}/{fb}.dds", d + _OUTLINE) for k, fb, d in [
    ("raid", "generic_icons/down_down", "a heavy dark bronze bear paw pressing a share certificate down, gold coins scattering from under it"),
    ("lure", "timed_modifier_icons/modifier_coins_positive", "a red and steel horseshoe magnet pulling a stream of gold coins out of a tipped leather purse"),
    ("press", "timed_modifier_icons/modifier_documents_negative", "a folded broadsheet newspaper with blank grey columns, a quill pen and a spilled ink pot on it"),
    ("shore", "generic_icons/map_list_lock", "a stout wall of timber posts and sandbags standing in front of a neat stack of gold coins"),
    ("hold", "lens_toolbar_icons/rivalry", "a gloved fist gripping a thick taut hemp rope, as in a tug of war, a gold coin tied into the rope beside it"),
    ("out", "lens_toolbar_icons/rivalry", "a gentleman's slim duelling sword pointing right across a single gold coin"),
    ("in", "lens_toolbar_icons/rivalry", "a round dented iron shield with a deep red stripe, a broken arrow glancing off it"),
]})
# event pictures (stories): the event window stretches its picture over the whole window, 1120 wide and about 650 to 750
# high (it grows with the text), so 1.65 to 1; made 2.1 to 1 the painting came out tall and thin (2026-11-16)
PICTURES = {"picture_rival": "two rival stockbrokers in top hats and frock coats glaring at each other across a crowded "
                             "19th century trading floor, torn share certificates and ticker tape in the air between them"}
PICTURE_SIZE = (1650, 1000)
GAME_GFX = "G:/SteamLibrary/steamapps/common/Victoria 3/game/"
RIVALRY = f"{DIR}/rival_out.dds"  # the painted "we rival" icon (SLOTS rival_out)
RIVALRY_OFF = f"{DIR}/rival_out_off.dds"
# the mod's concepts without an icon of their own (concepts.CONCEPTS): one painted object each, shown on the concept's
# tooltip and as @spec_<concept>! before its name, as vanilla's @aut! Authority
SLOTS.update({f"concept_{c}": (128, f"{V}/{fb}.dds", d + _OUTLINE) for c, fb, d in [
    ("credit_policy", "invention_icons/central_banking", "a large brass valve wheel on a short iron pipe, a thin trickle of gold coins falling from its spout"),
    ("outstanding_credit", "invention_icons/banking", "a long paper loan ledger unrolling from a brass spindle, a quill pen resting across it"),
    ("long_depression", "event_icons/event_trade", "a cold idle brick factory with smokeless chimneys behind a chained and padlocked iron gate, grey muted tones"),
    ("sound_finance", "invention_icons/investment_banks", "a solid granite classical column standing on three stacked gold ingots"),
    ("banking_reforms", "generic_icons/diplomatic_treaties", "a thick bound parliamentary report tied with a red ribbon, a quill and brass inkwell beside it"),
    ("intervention", "invention_icons/central_banking", "a gloved hand steadying a brass balance scale that holds a few gold coins"),
    ("market_conditions", "invention_icons/international_exchange_standards", "a round brass barometer with a cream dial and a black needle"),
    ("baseline", "invention_icons/investment_banks", "a brass and wood spirit level lying perfectly level on a short stack of gold coins"),
    ("market_mood", "invention_icons/stock_exchanges", "a brass weathervane with an arrow turning on top of a small copper cupola"),
    ("market_tie", "generic_icons/diplomatic_treaties", "two large gold coins linked together by a short heavy iron chain"),
    ("capital_flight", "invention_icons/mutual_funds", "a leather money bag with small white feathered wings flying away, a few coins falling from it"),
    ("war_news", "event_icons/event_trade", "a folded newspaper with blank grey columns beside a brass field telescope and a small cannon ball"),
    ("financial_centre", "building_icons/building_trade_center", "a small domed classical exchange building inside a gilded laurel wreath"),
    ("company_strength", "invention_icons/stock_exchanges", "an iron-bound oak strongbox with a brass company seal on its lid, share certificates tucked under it"),
    ("leverage", "invention_icons/banking", "a wooden lever on a brass fulcrum lifting a heavy stack of gold coins"),
    ("bad_debts", "timed_modifier_icons/modifier_coins_negative", "a heap of torn loan bills spilling from an open ledger, the whole object tinted dull red"),
    ("lending_standards", "invention_icons/investment_banks", "a banker's brass magnifying glass held over a loan bill with a red seal"),
    ("trust", "generic_icons/legitimacy", "a gentleman's firm handshake over a closed leather ledger with a brass clasp"),
    ("exchange", "invention_icons/stock_exchanges", "the columned front of a small classical stock exchange with a pediment and a flag on its roof"),
]})
# every concept's icon, painted or reused (concepts.CONCEPTS takes its texture from here)
CONCEPT_ICON = {"market_confidence": "je_markets", "speculative_mania": "state_mania", "financial_panic": "state_panic",
                "foreign_panic": "driver_foreign", "boom_end": "driver_crash", "correction": "ending_1", "bust": "ending_2",
                "collapse": "ending_3", "investor_interest": "driver_boom", "speculative_excess": "excess_alert",
                "blue_chip": "blue_chip", **{n[8:]: n for n in SLOTS if n.startswith("concept_")}}

TEXT_ICONS = [n for n in SLOTS if n.startswith(("interest_", "ending_", "blue_"))]  # in loc as @spec_<name>!


def texticons():
    """gui/spec_texticons.gui, sized like vanilla's goods text icons."""
    return "".join(f"""texticon = {{
	icon = spec_{n}
	iconsize = {{
		texture = "{path(slot)}"
		size = {{ 22 22 }}
		offset = {{ 0 6 }}
		fontsize = 18
	}}
}}
""" for n, slot in [(n, n) for n in TEXT_ICONS] + [(c, n) for c, n in CONCEPT_ICON.items() if c not in TEXT_ICONS])


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


def rings(mod, vanilla, colours):
    """The confidence ring in each map mode colour: vanilla's round progress texture (frame 1 the track, frame 2
    the fill) with the fill's light and shade kept and tinted. Returns the names written, ring_<stage>."""
    src = Image.open(vanilla).convert("RGBA")
    h = src.height
    fill = src.crop((h, 0, 2 * h, h))
    lum = fill.convert("L")
    mean = sum(v * n for v, n in enumerate(lum.histogram(fill.getchannel("A")))) / max(1, sum(lum.histogram(fill.getchannel("A"))))
    out = []
    for name, rgb in colours.items():
        c = [int(x) for x in re.findall(r"\d+", rgb)]
        # vanilla's fill shading, its grain strengthened, around a tone as muted as vanilla's own fills
        shade = lum.point(lambda v: min(255, round((v / mean) ** 1.6 * 128)))
        avg = sum(v * n for v, n in enumerate(shade.histogram(fill.getchannel("A")))) / max(1, sum(shade.histogram(fill.getchannel("A"))))
        tinted = Image.merge("RGB", [shade.point(lambda v, ch=ch: min(255, round(v / avg * ch * 0.5))) for ch in c])
        tinted.putalpha(fill.getchannel("A"))
        img = src.copy()
        img.paste(tinted, (h, 0))
        dest = mod / DIR / f"ring_{name}.dds"
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest)
        out.append(f"ring_{name}")
    return out




def build(mod):
    out = []
    for name, (size, *_) in SLOTS.items():
        if not has(name):
            continue
        im = Image.open(art(name)).convert("RGBA")
        if name.startswith("law_"):
            dest = mod / DIR / f"{name}.dds"
            dest.parent.mkdir(parents=True, exist_ok=True)
            law_metal.finish(im).resize((size, size), Image.LANCZOS).save(dest)
            out.append(name)
            continue
        im = grade(im)
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
        canvas = canvas.resize((size, size), Image.LANCZOS)
        dest = mod / DIR / f"{name}.dds"
        dest.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dest)
        out.append(name)
    # the rivalry button's off state: a silhouette of our "we rival" icon, as vanilla's subsidized_not (its colour and
    # teal), so the toggle reads off-but-clickable as the subsidize button does. Our icon is a round shield, whose flat
    # silhouette is a plain disc, so it keeps its own light and shade, tinted teal
    src = Image.open(mod / RIVALRY).convert("RGBA")
    grey = ImageOps.colorize(ImageOps.autocontrast(src.convert("L"), cutoff=2), (20, 40, 40), (130, 200, 200)).convert("RGBA")
    grey.putalpha(src.getchannel("A").point(lambda v: round(v * 0.8)))
    (mod / RIVALRY_OFF).parent.mkdir(parents=True, exist_ok=True)
    grey.save(mod / RIVALRY_OFF)
    out.append("rival_out_off")  # generate keeps only files it was told about
    for name in PICTURES:
        if not has(name):
            continue
        im = Image.open(ART / f"{name}.png").convert("RGB")
        w, h = PICTURE_SIZE
        # the painting whole, at full height on the left (the part the event's text panel leaves clear); behind and
        # right of it the same painting blurred and darkened, so nothing is cropped or stretched
        from PIL import ImageFilter
        k = max(w / im.width, h / im.height)
        back = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        back = back.crop(((back.width - w) // 2, (back.height - h) // 2, (back.width - w) // 2 + w, (back.height - h) // 2 + h))
        back = ImageEnhance.Brightness(back.filter(ImageFilter.GaussianBlur(40))).enhance(0.45)
        front = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        fade = Image.linear_gradient("L").rotate(-90, expand=True).resize((front.width // 5, h))  # the right edge fades into the blur
        mask = Image.new("L", front.size, 255)
        mask.paste(fade, (front.width - fade.width, 0))
        back.paste(front, (0, 0), mask)
        dest = mod / DIR / f"{name}.dds"
        dest.parent.mkdir(parents=True, exist_ok=True)
        back.save(dest)
        out.append(name)
    gui = mod / "gui/spec_texticons.gui"
    gui.parent.mkdir(parents=True, exist_ok=True)
    gui.write_text(texticons(), encoding="utf-8-sig", newline="\n")
    return out


# where vanilla sets a concept's icon before its name: the start of its own description, and a concept that opens a
# line or a #header/#title (tooltip heads, breakdown rows). Running text keeps plain links, as vanilla's does.
_LEAD = re.compile(r"(?:^|(?<=\n)|(?<=#header )|(?<=#title )|(?<=#bold ))"
                   r"(?=\[concept_spec_(\w+)\]|\[Concept\('concept_spec_(\w+)'|\$concept_spec_(\w+)\$)")
_LINK = re.compile(r"\[concept_spec_(\w+)\]|\[Concept\('concept_spec_(\w+)'")  # a link to a concept, in either form
ICON_TAG = re.compile(r"@spec_(\w+)! (?=\[concept_spec_|\[Concept\('concept_spec_|\$concept_spec_)")


# loc keys shown as panel text (generate.panel_keys): concept icons belong in tooltips only, where they tie a link to
# its picture; panel text keeps plain links
PANEL_KEYS = set()


def concept_icons(key, value, allow=None):
    """value with @spec_<concept>! set before each concept that leads a line or heading, and before the concept's
    own description. Idempotent; strip_concept_icons undoes it, so translations are matched on the plain English."""
    def lead(m):
        c = m[1] or m[2] or m[3]
        return f"@spec_{c}! " if c in CONCEPT_ICON and (allow is None or c in allow) else ""
    if key in PANEL_KEYS:
        return strip_concept_icons(value)
    own = re.fullmatch(r"concept_spec_(\w+)_desc", key)
    if own:  # a concept's text: no icon for itself, one before the first link to each other concept
        seen = {own[1]}

        def first(m):
            c = m[1] or m[2]
            if c in seen or c not in CONCEPT_ICON or (allow is not None and c not in allow):
                return m[0]
            seen.add(c)
            return f"@spec_{c}! {m[0]}"
        return _LINK.sub(first, strip_concept_icons(value))
    return _LEAD.sub(lead, strip_concept_icons(value))


def iconed(value):
    """The concepts concept_icons set an icon for in value, for a translation to get the same ones."""
    return set(re.findall(r"@spec_(\w+)! (?=\[concept_spec_|\[Concept\('concept_spec_|\$concept_spec_)", value))


def strip_concept_icons(value):
    value = ICON_TAG.sub(lambda m: "" if m[1] in CONCEPT_ICON else m[0], value)
    return re.sub(r"^@spec_(\w+)! ", lambda m: "" if m[1] in CONCEPT_ICON else m[0], value)


if __name__ == "__main__":
    t = concept_icons("x", "#header [concept_spec_leverage]#!\n[concept_spec_bad_debts]: #N -1%#!\nSee [concept_spec_exchange].")
    assert t == "#header @spec_leverage! [concept_spec_leverage]#!\n@spec_bad_debts! [concept_spec_bad_debts]: #N -1%#!\nSee [concept_spec_exchange].", t
    d = concept_icons("concept_spec_baseline_desc", "[concept_spec_baseline] is where [concept_spec_market_confidence] goes, [concept_spec_market_confidence] again")
    assert d == "[concept_spec_baseline] is where @spec_market_confidence! [concept_spec_market_confidence] goes, [concept_spec_market_confidence] again", d
    assert concept_icons("concept_spec_baseline_desc", d) == d and iconed(d) == {"market_confidence"}
    assert concept_icons("concept_spec_baseline_desc", d, allow=set()).count("@") == 0
    assert strip_concept_icons(d).count("@") == 0 and strip_concept_icons(t).count("@") == 0
    assert concept_icons("k", "@spec_interest_keen! #v Keen#!") == "@spec_interest_keen! #v Keen#!"
    print("icons ok")
