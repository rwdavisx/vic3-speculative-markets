"""Workshop thumbnail (mod/thumbnail.png, 800x800): the market map mode with the mod's rival-brokers event picture faded
into it, the title and subtitle, and the boom-and-bust cycle drawn
with the mood icons.
2026-11-22: the brokers moved 70px right (left 150 -> 220) so both faces clear the title, with a shorter left fade
(30% -> 14%) so the left broker stays solid. The result is ~999 KB: past 1,000,000 bytes it drops to 256 colours.
Shots: build_scratch/gallery_src/shots (4K, UI 1.5); art: art/raw.
    py -3 workshop/make_thumbnail.py"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "build_scratch/gallery_src/shots"
ART = ROOT / "art/raw"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
FONTS = "file:///G:/SteamLibrary/steamapps/common/Victoria%203/game/fonts"
OUT = ROOT / "mod/thumbnail.png"
S = 800
CROPS = {  # name: (shot, 4K box)
    "map": ("map_panic", (1544, 108, 2864, 1428)),    # France in panic, contagion stripes, booms
}
PAINT = ["picture_rival"]
STEPS = [  # icon, label, x, y, label above
    ("state_steady", "Steady", 92, 640, False),
    ("state_buoyant", "Buoyant", 236, 560, True),
    ("state_mania", "Mania", 400, 430, True),
    ("state_panic", "Panic", 560, 680, False),
    ("bank_rescue", "Rescue", 708, 585, True),
]

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; }}
.map {{ position: absolute; inset: 0; width: {S}px; height: {S}px; filter: saturate(1.2) brightness(1); }}
.event {{ position: absolute; left: 220px; top: 0; width: 800px; height: 360px; object-fit: cover; object-position: 50% 30%;
  filter: contrast(1.08) brightness(1.05);
  -webkit-mask-image: linear-gradient(#000 62%, transparent 100%), linear-gradient(90deg, transparent 0%, #000 14%);
  -webkit-mask-composite: source-in; mask-composite: intersect; }}
.shade {{ position: absolute; inset: 0; -webkit-mask-image: linear-gradient(#000 30%, transparent 45%);
  background: linear-gradient(90deg, rgba(8,9,13,.8) 0%, rgba(8,9,13,.55) 38%, rgba(8,9,13,0) 62%),
              radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 65%, rgba(8,9,13,.45) 100%); }}
.frame {{ position: absolute; inset: 12px; border: 2px solid rgba(214,176,98,.75); }}
h1 {{ position: absolute; left: 40px; top: 34px; margin: 0; font: 104px/0.9 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }}
.sub {{ position: absolute; left: 44px; top: 232px; width: 330px; font: italic 600 32px/1.22 Garamond, serif; color: #f0d28a;
  text-shadow: 0 0 3px #000, 0 0 8px #000, 0 2px 6px #000; }}
.rule {{ position: absolute; left: 44px; top: 218px; width: 220px; height: 2px; background: linear-gradient(90deg, #d6b062, transparent); }}
.band {{ position: absolute; left: 0; right: 0; bottom: 0; height: 470px;
  background: linear-gradient(rgba(8,9,13,0), rgba(8,9,13,.35) 45%, rgba(8,9,13,.55)); }}
svg {{ position: absolute; inset: 0; }}
.m {{ position: absolute; width: 92px; height: 92px; margin: -46px 0 0 -46px; border-radius: 50%; border: 3px solid #d6b062;
  background: #12141a center/86% no-repeat; box-shadow: 0 0 0 3px #0b0d12, 0 8px 18px rgba(0,0,0,.8); }}
.m.big {{ width: 118px; height: 118px; margin: -59px 0 0 -59px;
  box-shadow: 0 0 0 3px #0b0d12, 0 0 28px 10px rgba(243,210,122,.55), 0 8px 18px rgba(0,0,0,.8); }}
.l {{ position: absolute; width: 160px; margin-left: -80px; text-align: center; font: 30px Victorian, serif; color: #fbf3df;
  text-shadow: 0 2px 6px #000, 0 0 2px #000; }}
"""

BODY = """<img class="map" src="map.png"><img class="event" src="picture_rival.png"><div class="shade"></div><div class="band"></div>
<div class="frame"></div><h1>Speculative<br>Markets</h1><div class="rule"></div><div class="sub">Booms, banks, panics<br>and rival Exchanges</div>"""


def cycle():
    """The gold price line from Steady up to Mania, the crash into Panic, and the rescue."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3), (x4, y4) = [(x, y) for _, _, x, y, _ in STEPS]
    path = (f"M 24 690 C 50 670, 70 650, {x0} {y0} C 150 625, 190 590, {x1} {y1} C 290 525, 350 470, {x2} {y2} "
            f"C 450 470, 520 690, {x3} {y3} C 610 675, 660 610, {x4} {y4} L 776 560")
    out = [f'<svg width="{S}" height="{S}"><defs><linearGradient id="g" x1="0" x2="1">'
           '<stop offset="0" stop-color="#d6b062"/><stop offset=".55" stop-color="#f3d27a"/><stop offset=".62" stop-color="#d9563f"/>'
           '<stop offset=".8" stop-color="#d9563f"/><stop offset="1" stop-color="#d6b062"/></linearGradient></defs>'
           f'<path d="{path}" fill="none" stroke="#000" stroke-opacity=".7" stroke-width="12"/>'
           f'<path d="{path}" fill="none" stroke="url(#g)" stroke-width="6" stroke-linecap="round"/></svg>']
    for icon, label, x, y, above in STEPS:
        big = " big" if icon == "state_mania" else ""
        r = 59 if big else 46
        out.append(f'<div class="m{big}" style="left:{x}px;top:{y}px;background-image:url({icon}.png)"></div>')
        out.append(f'<div class="l" style="left:{x}px;top:{y - r - 42 if above else y + r + 6}px">{label}</div>')
    return "".join(out)



def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in CROPS.items():
            Image.open(SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        for name in PAINT + [s[0] for s in STEPS]:
            im = Image.open(ART / f"{name}.png")
            im.thumbnail((1100, 1100))
            im.save(tmp / f"{name}.png")
        page, shot = tmp / "thumb.html", tmp / "thumb.png"
        page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{BODY}{cycle()}</body></html>',
                        encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={S},{S}", "--allow-file-access-from-files", "--virtual-time-budget=3000",
                        f"--user-data-dir={tmp / 'chrome'}", f"--screenshot={shot}", page.as_uri()],
                       check=True, capture_output=True)
        im = Image.open(shot).convert("RGB").resize((S, S), Image.LANCZOS)
    im.save(OUT, optimize=True)
    if OUT.stat().st_size >= 1_000_000:  # Steam's preview limit is 1 MiB
        im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(OUT, optimize=True)
    print(OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
