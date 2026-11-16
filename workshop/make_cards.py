"""Builds the Workshop gallery as feature cards (1920x1080 JPEG, under 1 MB each) and thumbnail.png from the 4K, 150%
UI screenshots in raw/: a dimmed full-screen shot behind, the feature enlarged and framed, a headline in the game's
Victorian logo font and one line of plain text. Same style as the Map Mode Hotbar's cards (map-qol/workshop)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).parent
RAW = HERE / "raw"
OUT = HERE / "gallery_1.0"  # 0.8's cards stay in gallery/
FONTS = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game/fonts")
W, H = 1920, 1080
TITLE = ImageFont.truetype(str(FONTS / "ParadoxVictorian/ParadoxVictorian-Condensed.otf"), 112)
BODY = ImageFont.truetype(str(FONTS / "EBGaramond/EBGaramond-Medium.ttf"), 40)
CREAM = (250, 246, 236)
L, R = 84, 918  # the Market panel's left and right edge in the 4K shots
FINANCE_BUTTON = (35, 795, 42)  # centre and ring radius of the toolbar button in the full 4K shots
PANIC_BOX = [(1040, 500, 2810, 1700)]  # the event window in a 4K shot
MAP_BOX = (0, 0, 2392, 1420)  # all of map_world.png, a crop of a 4K shot that leaves out the game's panels
MAP_KEY = [("Mania", (235, 185, 40)), ("Buoyant", (60, 150, 110)), ("Steady", (150, 150, 135)), ("Wary", (95, 125, 165)),
           ("Panic", (170, 30, 35)), ("Hit from abroad", (95, 125, 165))]

# (file, headline, caption, scene, crops, side by side) where crops are (x0, y0, x1, y1) boxes in the 4K scene,
# shown enlarged and framed, stacked unless side by side; the scene behind is the whole screen, dimmed
CARDS = [
    ("01_finance", "The Finance Panel",
     "Open it with the Finance button on the left: Trading Floor, Speculation, Banking and Exchanges.",
     "", [("full_exchange", (0, 110, 916, 1300)), ("ui_speculation", (0, 0, 840, 1190)),
          ("ui_banking", (0, 0, 840, 1190)), ("ui_rankings", (0, 0, 840, 1190))], True, "full_exchange"),
    ("02_exchange", "Your Stock Exchange",
     "Rise from Provincial to World Centre, pick a Charter, and compete on the Paths to Renown.",
     "ui_exchange", [("full_exchange", (0, 110, 916, 1190)), (0, 900, 840, 1870)], True, "full_exchange"),
    ("03_speculation", "Booms, Manias and Panics",
     "Market Confidence, Investor Interest in every good, and the levers to cool a boom.",
     "ui_speculation", [("full_speculation", (0, 110, 916, 1050)), (0, 1130, 840, 1870)], True, "full_speculation"),
    ("04_banking", "Bank Credit",
     "Leverage speeds up your economy, until the loans go bad. See where the banks have lent.",
     "ui_banking", [("full_banking", (0, 110, 916, 1120)), (0, 830, 840, 1800)], True, "full_banking"),
    ("05_rankings", "The World's Leading Exchanges",
     "The top five gain prestige and cheaper loans. The top three are World Centres.",
     "ui_rankings", [("full_rankings", (0, 110, 916, 1225)), (0, 935, 840, 1870)], True, "full_rankings"),
    ("06_panic", "Financial Panic",
     "Output and taxes fall, loans are called in, and relief costs you every week. Rescue the banks?",
     "ev_panic", PANIC_BOX, False),
    ("07_mania", "Speculative Mania",
     "Ride it, warn investors, or make the speculators pay their share.",
     "ev_mania_opt3", [(1040, 500, 2810, 1790)], False),
    ("08_depression", "The Long Depression",
     "From 1870, a Great Power's crash can drag the whole world down.",
     "ev_depression_opt2", [(1040, 500, 2810, 1700)], False),
    ("09_journal", "A Journal for Your Markets",
     "Follow each boom and panic, watch the bubble build, and reform your banks.",
     "je_mania", [(L, 118, R, 1110), (L, 1110, R, 1640)], True),
    ("11_rule", "Choose Your Volatility",
     "Historical by default, or High for bigger booms and more frequent panics.",
     "rules_full", [(1206, 472, 2636, 1686)], False),
    ("12_tech", "Finance in the Tech Tree",
     "Each finance technology lists what it changes in your markets.",
     "tt_tech_central_banking", [(1310, 470, 2480, 1220)], False),
    # beta.12 cards: NEED SCREENSHOTS, see shot_list_beta12.md. The raw/ files below do not exist yet, so the script
    # stops at the first of these until they are taken; the crop boxes follow the ui_/full_/ev_ shots above and may
    # need fitting once the shots exist.
    ("13_rivals", "Competing Exchanges",
     "A tug of war every five years. Raid a competitor, lure its capital, hold the line or shore up.",
     "ui_rivals", [("full_rivals", (0, 110, 916, 1225)), (0, 935, 840, 1870)], True, "full_rivals"),
    ("14_bluechips", "Blue Chips",
     "Keep a company prosperous for two years. Blue chips help in contests. The world's best is Company of the Year.",
     "ev_coty", [("ui_bluechips", (0, 0, 840, 1190)), (1040, 500, 2810, 1700)], True, "full_speculation"),
    ("15_renown", "Paths to Renown",
     "Compete for specialities. The higher your place, the bigger the reward and its price.",
     "ui_renown", [("full_renown", (0, 110, 916, 1225)), (0, 935, 840, 1870)], True, "full_renown"),
]

def outlined(canvas, xy, text, font, fill=CREAM, anchor="mt", stroke=None):
    """Lettering with a dark outline and a soft shadow."""
    stroke = stroke or max(3, font.size // 18)
    layer = Image.new("L", canvas.size)
    ImageDraw.Draw(layer).text(xy, text, font=font, anchor=anchor, fill=255, stroke_width=stroke)
    canvas.paste((0, 0, 0), (3, 5), layer.filter(ImageFilter.GaussianBlur(7)))
    canvas.paste((22, 16, 12), (0, 0), layer)
    ImageDraw.Draw(canvas).text(xy, text, font=font, anchor=anchor, fill=fill)


def backdrop(scene, blur=2, brightness=0.5, box=None):
    im = Image.open(RAW / f"{scene}.png").convert("RGB").crop(box).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur)) \
        if box else Image.open(RAW / f"{scene}.png").convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    im = ImageEnhance.Brightness(im).enhance(brightness)
    # darker at the top, where the headline sits
    shade = Image.new("L", (W, H))
    for y in range(H):
        shade.paste(int(170 * max(0.0, 1 - y / 330)), (0, y, W, y + 1))
    return Image.composite(Image.new("RGB", (W, H)), im, shade)


def framed(canvas, piece, x, y):
    """A crop with a shadow, a dark rim and a thin gold line, like an in-game panel."""
    sh = Image.new("L", (piece.width + 80, piece.height + 80))
    ImageDraw.Draw(sh).rectangle((40, 40, piece.width + 40, piece.height + 40), fill=230)
    canvas.paste((0, 0, 0), (x - 40, y - 30), sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(canvas)
    d.rectangle((x - 6, y - 6, x + piece.width + 5, y + piece.height + 5), fill=(20, 16, 12))
    d.rectangle((x - 3, y - 3, x + piece.width + 2, y + piece.height + 2), outline=(176, 140, 78), width=2)
    canvas.paste(piece, (x, y))


def shot(name):
    """A raw shot; full-screen Finance shots get a gold ring around the Finance button on the left toolbar."""
    im = Image.open(RAW / f"{name}.png").convert("RGB")
    if name.startswith("full_"):
        x, y, r = FINANCE_BUTTON
        d = ImageDraw.Draw(im)
        d.ellipse((x - r - 4, y - r - 4, x + r + 4, y + r + 4), outline=(20, 16, 12), width=10)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(240, 200, 90), width=6)
    return im


def place_crops(canvas, scene, crops, side, top=290, bottom=1040):
    # a crop is a box in scene, or (shot, box) to take it from another shot
    pieces = [shot(c[0]).crop(c[1]) if isinstance(c[0], str) else shot(scene).crop(c) for c in crops]
    gap = 46
    if side:
        # one row, every piece the same height
        scale = min((bottom - top) / max(p.height for p in pieces),
                    (1760 - gap * (len(pieces) - 1)) / sum(p.width for p in pieces), 1.6)
    else:
        scale = min(1760 / max(p.width for p in pieces),
                    (bottom - top - gap * (len(pieces) - 1)) / sum(p.height for p in pieces), 1.6)
    pieces = [p.resize((round(p.width * scale), round(p.height * scale)), Image.LANCZOS) for p in pieces]
    if side:
        x = (W - sum(p.width for p in pieces) - gap * (len(pieces) - 1)) // 2
        for p in pieces:
            framed(canvas, p, x, top + (bottom - top - p.height) // 2)
            x += p.width + gap
    else:
        y = top + (bottom - top - gap * (len(pieces) - 1) - sum(p.height for p in pieces)) // 2
        for p in pieces:
            framed(canvas, p, (W - p.width) // 2, y)
            y += p.height + gap


def finish(canvas, name):
    ImageDraw.Draw(canvas).rectangle((0, 0, W - 1, H - 1), outline=(28, 20, 16), width=10)
    out = OUT / f"{name}.jpg"
    for q in (90, 86, 82, 78):
        canvas.save(out, quality=q, optimize=True)
        if out.stat().st_size < 1_000_000:
            break


def card(name, title, caption, scene, crops, side, behind=None):
    """behind swaps the dimmed scene for another shot, kept brighter and sharper so it reads as a picture of its own."""
    canvas = backdrop(behind, 0, 0.8, MAP_BOX) if behind == "map_world" else backdrop(behind or "full_speculation")  # a 1.0 screen, so the Finance button shows behind every card
    outlined(canvas, (W // 2, 46), title, TITLE)
    outlined(canvas, (W // 2, 182), caption, BODY, fill=(236, 228, 210), stroke=3)
    place_crops(canvas, scene, crops, side)
    finish(canvas, name)


def map_card():
    """The journal entry's world map with its key on the left. Its shot is a crop, not the whole screen, so it has its own layout."""
    name, title = "10_map", "A Map of the World's Markets"
    caption = "Open Financial Markets to see every market by stage, and watch a panic spread."
    canvas = backdrop("map_world")
    outlined(canvas, (W // 2, 46), title, TITLE)
    outlined(canvas, (W // 2, 182), caption, BODY, fill=(236, 228, 210), stroke=3)
    world = Image.open(RAW / "map_world.png").convert("RGB").crop(MAP_BOX)
    scale = 750 / world.height
    world = world.resize((round(world.width * scale), 750), Image.LANCZOS)
    x = W - world.width - 60
    framed(canvas, world, x, 290)
    key = ImageFont.truetype(str(FONTS / "EBGaramond/EBGaramond-Medium.ttf"), 36)
    d = ImageDraw.Draw(canvas)
    for n, (word, color) in enumerate(MAP_KEY):
        y = 330 + n * 74
        d.rectangle((58, y, 106, y + 48), fill=color, outline=(176, 140, 78), width=2)
        if word == "Hit from abroad":
            stripes = Image.new("RGB", (45, 45), color)
            for i in range(-45, 45, 15):
                ImageDraw.Draw(stripes).line((i, 45, i + 45, 0), fill=(45, 20, 25), width=5)
            canvas.paste(stripes, (60, y + 2))
        outlined(canvas, (122, y + 24), word, key, fill=(236, 228, 210), anchor="lm", stroke=2)
    finish(canvas, name)


def thumbnail(size=800):
    """The world's markets behind, the confidence card framed across the lower half, the title top left."""
    canvas = Image.open(RAW / "map_world.png").convert("RGB").crop((480, 0, 1900, 1420)).resize((size, size), Image.LANCZOS)
    canvas = ImageEnhance.Brightness(canvas).enhance(0.8)
    piece = Image.open(RAW / "ui_speculation.png").convert("RGB").crop((0, 40, 840, 690))
    scale = size * 0.86 / piece.width
    piece = piece.resize((round(piece.width * scale), round(piece.height * scale)), Image.LANCZOS)
    framed(canvas, piece, (size - piece.width) // 2, size - piece.height - 34)
    font = ImageFont.truetype(str(FONTS / "ParadoxVictorian/ParadoxVictorian-Condensed.otf"), int(size * 0.15))
    outlined(canvas, (int(size * 0.05), int(size * 0.02)), "Speculative", font, anchor="lt")
    outlined(canvas, (int(size * 0.05), int(size * 0.02 + font.size * 0.92)), "Markets", font, anchor="lt")
    ImageDraw.Draw(canvas).rectangle((0, 0, size - 1, size - 1), outline=(28, 20, 16), width=max(4, size // 120))
    canvas.save(OUT / "thumbnail.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for c in CARDS:
        card(*c)
    map_card()
    thumbnail()
    # every card fits Steam's preview limit
    assert all(p.stat().st_size < 1_000_000 for p in OUT.glob("*.jpg"))
