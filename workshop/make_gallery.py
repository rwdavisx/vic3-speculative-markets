"""Workshop gallery cards (1920x1080 JPEG): painted game backdrop, title column with numbered points,
and the whole in-game panel unfolded into side-by-side columns with matching pins.
The panel is a tall image stitched from scrolled 4K shots of the dev game (UI scale 1.5).
    py -3 workshop/make_gallery.py <shots_dir> <art_dir> [card ...]"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
FONTS = "file:///G:/SteamLibrary/steamapps/common/Victoria%203/game/fonts"
OUT = Path(__file__).parent / "gallery"

# layout (card pixels): the panel fills the right of the card
PANEL_X, PANEL_R, PANEL_H, COL_GAP, SKIP_H = 700, 1830, 960, 34, 44

# name: backdrop, eyebrow, title, lead, tall image, columns of pieces, points.
# A piece is (y0, y1) from the tall image, or a string drawn as a small "skipped" divider.
# A point is (title, text, column, y in the tall image) and gets a numbered pin there.
CARDS = {
    "speculation": dict(
        bg="load_0", eyebrow="Speculation", title="Booms, Bubbles<br>and Panics",
        lead="Investors chase rising prices until one bad turn brings it all down.",
        tall="v12_spec_tall",  # 1.2: full_effects (y 385-1655) over full_speculation (y 575-1910), x 78-923
        cols=[[(0, 1270)], [(1270, 2605)]],
        points=[("Market Confidence", "From Panic to Mania. Booms push it up; crashes, debt and lost wars pull it down.", 0, 120),
                ("Effects on Our Economy", "What the market is doing to your investment, output, construction and trade right now.", 0, 805),
                ("Interest, Trend and Risk", "Sort goods by how keen investors are, which way they are moving, or what a crash would cost.", 1, 1462, 0.5),
                ("Interventions", "Restrain hot goods, Encourage cold ones, or float a Great Issue.", 1, 1695, 0.9),
                ("Sectors", "Goods grouped by sector, with headers you can fold away.", 1, 2080)]),
    "stances": dict(
        bg="load_5", eyebrow="Interest Groups", title="Every Group<br>Has Its Goods",
        lead="Interest groups care how the goods they favor fare on the market.",
        shots=[("v12_ig_stances_industrialists", (75, 135, 915, 1450))],
        points=[("Favored Goods", "Each group favors a few traded goods, rolled for every country.", 0, 0.17, 0.84),
                ("Booms Win Approval", "A boom in those goods lifts the group's approval. A bust or a Restrain sours it.", 0, 0.03, 0.47),
                ("Clout Matters", "Powerful groups react twice as strongly. Marginalized groups do not react.", 0, 0.3, 0.31)]),
    "monetary": dict(
        bg="load_9", eyebrow="New Law Group", title="The Monetary<br>Standard",
        lead="Bimetallism, the Gold Standard or Fiat Money: each changes how panics play out.",
        shots=[("v12_law_monetary", (100, 230, 1900, 1060)), ("v12_law_monetary", (3040, 1160, 3760, 1480), 0.42)],
        points=[("Bimetallism", "Cheaper bank rescues, but boom endings hit harder.", 0, 0.4, 0.125),
                ("Gold Standard", "Cuts loan interest and trust losses, but panics last longer.", 1, 0.05, 0.12),
                ("Fiat Money", "Cheaper rescues and shorter panics, but it feeds speculation.", 0, 0.4, 0.48)]),
    "trading": dict(
        bg="load_4", eyebrow="Trading Floor", title="Your Exchange<br>on the World Stage",
        lead="Every country has an Exchange. Grow it, charter it and make it famous.",
        tall="trading_tall",
        cols=[[(0, 1180)], [(1180, 2395)]],
        points=[("Standing", "Grow from Provincial to National and International. The top three are World Centres.", 0, 300),
                ("Trust", "Steady markets and blue chips build it. Panics wear it down.", 0, 470),
                ("Exchange Charter", "A Commodity Exchange for booms, a Money Market for trust, a Share Market for credit.", 0, 780),
                ("Specialities", "Higher standing unlocks more. Each one changes how your markets behave.", 0, 1070),
                ("Paths to Renown", "Race other Exchanges in your Specialities. Higher places pay more, but every path has a drawback.", 1, 1300)]),
    "banking": dict(
        bg="load_8", eyebrow="Banking", title="Credit, Leverage<br>and Rescue",
        lead="Credit grows your economy, until a panic comes to collect it.",
        tall="banking_tall",
        cols=[[(0, 920)], [(920, 1990)]],
        points=[("Where the Banks Have Lent", "See which booms your banks are riding, good by good.", 0, 180, -0.035),
                ("Credit Leverage", "Each month of leverage adds throughput, but past 3 months panics hit harder.", 0, 560, -0.035),
                ("Credit Policy and Standards", "Set how freely banks lend. Standards drift looser in good times.", 1, 1000, -0.035),
                ("Bad Debts", "Panics leave bad loans that drag on output for years. Buy them up to clear them.", 1, 1494, -0.035),
                ("Bank Rescue", "Lend to the Banks to shorten a panic, or pledge a cheaper rescue in advance.", 1, 1700)]),
    "exchanges": dict(
        bg="load_6", eyebrow="Exchanges", title="Compete for<br>the World's Capital",
        lead="Rank against every Exchange, pick your competitors and fight for the top.",
        tall="exchanges3_tall",
        cols=[[(0, 1260), "and every other Exchange"], [(1890, 2822)]],
        points=[("Leading Exchanges", "Every Exchange at National standing or above, ranked by score.", 0, 240),
                ("Contest Slots", "One, plus one per Standing above Provincial. Start a contest from the list or the map.", 1, 2010),
                ("Moves Against Us", "Every competitor move on you, and how long it lasts.", 1, 2175, -0.035),
                ("Contests", "A five-year tug of war. A decisive win at 75% takes part of the loser's income.", 1, 2470, 0.22),
                ("Competitor Actions", "Bear Raid, Lure, Press Campaign, Hold the Line or Shore Up, once a year each.", 1, 2470, 0.68)]),
    "panic": dict(
        bg="load_3", eyebrow="Financial Panics", title="When the<br>Boom Breaks",
        lead="Let confidence fall too far and the whole market runs for the door.",
        shots=[("panic_event", (1049, 391, 2801, 1764)), ("st_panic_0", (75, 340, 915, 1000), 0.42)],
        points=[("A General Panic", "The largest boom to end takes the rest of the market down with it.", 0, 0.36, 0.035),
                ("Loans Called In", "Banks pull credit, private construction halves and bad debts drag for years.", 0, 0.488, 0.4),
                ("Your Response", "Let the market find its floor, rescue the banks, or blame the speculators.", 0, 0.488, 0.83),
                ("Confidence Crashes", "Market Confidence drops to the bottom, then climbs back month by month.", 1, 0.06, 0.2)]),
    "map": dict(
        bg="load_1", eyebrow="Market Map", title="Panics Spread<br>Across Borders",
        lead="The Financial Markets journal entry opens a map of every market in the world.",
        shots=[("map_panic", (930, 110, 3180, 2030))],
        points=[("Panic", "Countries in a Financial Panic stand out in red.", 0, 0.41, 0.48),
                ("Contagion", "Stripes mark a country a foreign panic has just reached.", 0, 0.286, 0.668),
                ("Booms", "Every other market is coloured by its mood, from steady to mania.", 0, 0.337, 0.318)]),
    "title": dict(
        bg="load_7", eyebrow="A Victoria 3 Mod", title="Speculative<br>Markets",
        lead="Booms, bank lending and market crashes, with an Exchange for every country.",
        shots=[("map_panic", (930, 110, 3180, 2030)), ("panic_event", (1049, 391, 2801, 1764), 0.5)],
        points=[("Trading Floor", "Grow your Exchange from Provincial to World Centre."),
                ("Speculation", "Ride the boom, and survive the bust."),
                ("Banking", "Credit, leverage, bad debts and rescues."),
                ("Exchanges", "Rank and compete against every Exchange in the world."),
                ("Blue Chips", "Your most prosperous companies steady the market.")]),
}

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-weight: 700; src: url("{FONTS}/EBGaramond/EBGaramond-Bold.ttf"); }}
@font-face {{ font-family: Garamond; font-weight: 400; src: url("{FONTS}/EBGaramond/EBGaramond-Regular.ttf"); }}
@font-face {{ font-family: Garamond; font-weight: 400; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #0b0d12; font-family: Garamond, Georgia, serif; color: #f3ead3; }}
.bg {{ position: absolute; inset: -20px; background-size: cover; background-position: center;
       filter: sepia(.3) saturate(.9) brightness(.8) blur(1.5px); }}
.shade {{ position: absolute; inset: 0;
          background: linear-gradient(90deg, rgba(8,9,13,.95) 0%, rgba(8,9,13,.86) 30%, rgba(8,9,13,.45) 55%, rgba(8,9,13,.6) 100%),
                      radial-gradient(ellipse at 65% 50%, transparent 40%, rgba(0,0,0,.55) 100%); }}
.col {{ position: absolute; left: 90px; top: 64px; width: 560px; }}
.eyebrow {{ font: 700 22px Garamond; letter-spacing: .42em; text-transform: uppercase; color: #c9a35a; }}
h1 {{ font: 84px/0.98 Victorian, serif; margin: 18px 0 22px; color: #f6efdc; text-shadow: 0 4px 18px rgba(0,0,0,.7); }}
.rule {{ display: flex; align-items: center; gap: 14px; width: 360px; margin-bottom: 26px; }}
.rule i {{ flex: 1; height: 1px; background: linear-gradient(90deg, #c9a35a, rgba(201,163,90,.15)); }}
.rule i:first-child {{ flex: 0 0 50px; background: #c9a35a; }}
.rule b {{ width: 10px; height: 10px; transform: rotate(45deg); border: 1px solid #c9a35a; }}
.lead {{ font: 400 27px/1.38 Garamond; color: #d9cfb6; margin-bottom: 28px; }}
.pt {{ display: flex; gap: 22px; margin-bottom: 16px; }}
.num, .pin {{ border-radius: 50%; display: grid; place-items: center; font-family: Victorian; }}
.num {{ flex: 0 0 44px; height: 44px; border: 2px solid #c9a35a; font-size: 29px; color: #f0d28a; background: rgba(201,163,90,.08); }}
.pt b {{ display: block; font: 700 28px/1.1 Garamond; color: #f0d28a; margin: 4px 0 5px; }}
.pt span {{ display: block; font: 400 22px/1.3 Garamond; color: #cfc5ad; }}
.frame {{ position: absolute; display: flex; gap: {COL_GAP}px; padding: 8px; background: #16181a; border: 1px solid #c9a35a;
          box-shadow: 0 24px 60px rgba(0,0,0,.75), 0 0 0 5px rgba(10,10,12,.6), 0 0 0 6px rgba(201,163,90,.4); }}
.pcol {{ position: relative; display: flex; flex-direction: column; }}
.pcol + .pcol::before {{ content: ""; position: absolute; left: -{COL_GAP // 2}px; top: 10px; bottom: 10px; width: 1px;
        background: linear-gradient(transparent, #c9a35a 15%, #c9a35a 85%, transparent); }}
.pcol img {{ display: block; width: 100%; }}
.skip {{ height: {SKIP_H}px; display: flex; align-items: center; gap: 14px; font: italic 400 21px Garamond; color: #b9ad90; letter-spacing: .06em; }}
.skip i {{ flex: 1; border-top: 1px dashed rgba(201,163,90,.55); }}
.pin {{ position: absolute; width: 44px; height: 44px; font-size: 29px; color: #1a140a; transform: translate(-50%, -50%);
        background: radial-gradient(circle at 35% 30%, #ffe7a8, #c9a35a 60%, #8a6a2e); box-shadow: 0 4px 12px rgba(0,0,0,.7), 0 0 0 3px rgba(10,10,12,.85); }}
.mark {{ position: absolute; left: 90px; bottom: 40px; font: 700 18px Garamond; letter-spacing: .36em; text-transform: uppercase; color: rgba(201,163,90,.7); }}
"""


def screens(name, c, shots, tmp):
    """Free-standing shots: the first fills the panel area, later ones are insets over its lower left.
    A shot is (file, 4K box, inset width as a share of the main shot's); a point's pin is (shot, x, y) as shares."""
    placed = []
    for i, (file, box, *frac) in enumerate(c["shots"]):
        im = Image.open(shots / f"{file}.png").convert("RGB").crop(box)
        f = tmp / f"{name}_s{i}.png"
        im.save(f)
        if not i:
            s = min(PANEL_H / im.height, (PANEL_R - PANEL_X) / im.width)
            w, h = im.width * s, im.height * s
            x, y = PANEL_X + (PANEL_R - PANEL_X - w) / 2, (1080 - h) / 2
        else:
            mx, my, mw, mh = placed[0][1:]
            w = mw * frac[0]
            h = im.height * w / im.width
            x, y = mx + 30, my + mh - h + 30
        placed.append((f, x, y, w, h))
    html = "".join(f'<div class="frame" style="left:{x - 9:.0f}px;top:{y - 9:.0f}px"><img style="width:{w:.0f}px;display:block" src="{f.as_uri()}"></div>'
                   for f, x, y, w, h in placed)
    pins = [f'<div class="pin" style="left:{placed[si][1] + fx * placed[si][3]:.0f}px;top:{placed[si][2] + fy * placed[si][4]:.0f}px">{i}</div>'
            for i, (_, _, *pin) in enumerate(c["points"], 1) if pin for si, fx, fy in [pin]]
    return html, pins


def card(name, c, shots, art, tmp):
    if "shots" in c:
        panel, pins = screens(name, c, shots, tmp)
    else:
        panel, pins = columns(name, c, shots, tmp)
    pts = "".join(f'<div class="pt"><div class="num">{i}</div><div><b>{t}</b><span>{x}</span></div></div>'
                  for i, (t, x, *_) in enumerate(c["points"], 1))
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="bg" style="background-image:url('{(art / (c['bg'] + '.png')).as_uri()}')"></div><div class="shade"></div>
<div class="col"><div class="eyebrow">{c['eyebrow']}</div><h1>{c['title']}</h1><div class="rule"><i></i><b></b><i></i></div>
<div class="lead">{c['lead']}</div>{pts}</div>
{panel}
{"".join(pins)}
<div class="mark">Speculative Markets &nbsp;·&nbsp; Victoria 3</div></body></html>"""
    hp = tmp / f"{name}.html"
    hp.write_text(html, encoding="utf-8")
    png = tmp / f"{name}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--window-size=1920,1080", "--allow-file-access-from-files", "--virtual-time-budget=3000",
                    f"--screenshot={png}", hp.as_uri()], check=True, capture_output=True)
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{name}.jpg"
    Image.open(png).convert("RGB").resize((1920, 1080), Image.LANCZOS).save(out, quality=90, optimize=True)
    print(out, out.stat().st_size // 1024, "KB")


def columns(name, c, shots, tmp):
    """The whole panel, stitched tall and unfolded into side-by-side columns."""
    tall = Image.open(shots / f"{c['tall']}.png").convert("RGB")
    tw = tall.width
    n = len(c["cols"])
    s = min([(PANEL_H - SKIP_H * sum(isinstance(p, str) for p in col)) / sum(p[1] - p[0] for p in col if not isinstance(p, str))
             for col in c["cols"]] + [(PANEL_R - PANEL_X - COL_GAP * (n - 1)) / (n * tw)])
    cw = round(tw * s)
    top = (1080 - max(sum((p[1] - p[0]) * s if not isinstance(p, str) else SKIP_H for p in col) for col in c["cols"])) / 2
    cols, where = [], {}
    for ci, col in enumerate(c["cols"]):
        y, parts = top, []
        for pi, piece in enumerate(col):
            if isinstance(piece, str):
                parts.append(f'<div class="skip"><i></i>{piece}<i></i></div>')
                y += SKIP_H
                continue
            f = tmp / f"{name}_{ci}_{pi}.png"
            tall.crop((0, piece[0], tw, piece[1])).save(f)
            parts.append(f'<img src="{f.as_uri()}">')
            where.setdefault(ci, []).append((piece, y))
            y += (piece[1] - piece[0]) * s
        cols.append(f'<div class="pcol" style="width:{cw}px">{"".join(parts)}</div>')
    pins = []
    for i, (_, _, ci, ty, *fx) in enumerate(c["points"], 1):
        (y0, _), py = next((p, py) for p, py in where[ci] if p[0] <= ty < p[1])
        pins.append(f'<div class="pin" style="left:{PANEL_X + ci * (cw + COL_GAP) + (fx[0] * cw if fx else 0):.0f}px;top:{py + (ty - y0) * s:.0f}px">{i}</div>')
    frame = f'<div class="frame" style="left:{PANEL_X - 9}px;top:{top - 9:.0f}px">{"".join(cols)}</div>'
    return frame, pins


if __name__ == "__main__":
    shots, art = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory(dir=shots) as tmp:  # beside the 4K shots, cleaned up afterwards
        for n in sys.argv[3:] or CARDS:
            card(n, CARDS[n], shots, art, Path(tmp))
