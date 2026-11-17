"""Workshop thumbnail (mod/thumbnail.png, 800x800): the title over the market map mode, the mod's painted art for the
swing from Panic to Mania across the real mood bar, the World Centre laurel, the competitor moves, and the Exchange
score and Trust. Shots: build_scratch/gallery_src/shots (4K, UI 1.5); art: art/raw.
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
    "map": ("map_panic", (920, 300, 2120, 1500)),     # western Europe: France in panic, contagion stripes, booms
    "bar": ("spec_tall", (40, 310, 815, 380)),        # the mood bar, Shaken to Mania, the Panic line
    "exch": ("trading_tall", (2, 168, 843, 568)),     # Exchange score, Standings, Trust
}
PAINT = ["state_panic", "state_mania", "concept_financial_centre", "rival_raid", "rival_lure", "rival_press", "blue_chip"]

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; }}
.map {{ position: absolute; inset: 0; width: {S}px; height: {S}px; filter: saturate(1.2) contrast(1.05) brightness(.92); }}
.shade {{ position: absolute; inset: 0;
  background: linear-gradient(rgba(8,9,13,.85) 0%, rgba(8,9,13,.45) 24%, rgba(8,9,13,0) 38%, rgba(8,9,13,0) 62%, rgba(8,9,13,.75) 100%),
              radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 50%, rgba(8,9,13,.65) 100%); }}
.frame {{ position: absolute; inset: 10px; border: 2px solid rgba(214,176,98,.8); }}
h1 {{ position: absolute; left: 34px; top: 20px; margin: 0; font: 108px/0.88 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }}
.tag {{ position: absolute; left: 40px; top: 222px; font: italic 27px Garamond, serif; color: #f0d28a; text-shadow: 0 2px 6px #000, 0 0 2px #000; }}
.p {{ position: absolute; filter: drop-shadow(0 10px 14px rgba(0,0,0,.85)) drop-shadow(0 0 2px rgba(0,0,0,.7)); }}
.laurel {{ right: 22px; top: 16px; width: 228px; filter: drop-shadow(0 0 22px rgba(240,200,110,.45)) drop-shadow(0 10px 14px rgba(0,0,0,.85)); }}
.panic {{ left: 26px; top: 268px; width: 236px; }}
.mania {{ right: 22px; top: 262px; width: 250px; }}
.bar {{ position: absolute; left: 30px; top: 500px; width: 740px; border: 3px solid #b8924a;
  box-shadow: 0 0 0 3px #0b0d12, 0 12px 30px rgba(0,0,0,.85); }}
.vs {{ position: absolute; left: 270px; top: 352px; width: 260px; text-align: center; font: 64px/1 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 2px 2px 0 #000, -2px -2px 0 #000, 0 6px 16px #000; }}
.exch {{ position: absolute; right: 24px; bottom: 24px; width: 400px; border: 3px solid #b8924a;
  box-shadow: 0 0 0 3px #0b0d12, 0 12px 30px rgba(0,0,0,.85); }}
.raid {{ left: 18px; top: 612px; width: 150px; transform: rotate(-8deg); }}
.lure {{ left: 140px; top: 640px; width: 140px; transform: rotate(6deg); }}
.press {{ left: 252px; top: 616px; width: 140px; transform: rotate(-4deg); }}
.chip {{ right: 382px; top: 560px; width: 92px; transform: rotate(10deg); }}
"""

BODY = """<img class="map" src="map.png"><div class="shade"></div><div class="frame"></div>
<h1>Speculative<br>Markets</h1><div class="tag">Booms, banks, panics and rival Exchanges</div>
<img class="p laurel" src="concept_financial_centre.png">
<img class="p panic" src="state_panic.png"><img class="p mania" src="state_mania.png">
<div class="vs">Panic<br>or Mania</div>
<img class="bar" src="bar.png">
<img class="exch" src="exch.png">
<img class="p raid" src="rival_raid.png"><img class="p lure" src="rival_lure.png"><img class="p press" src="rival_press.png">
<img class="p chip" src="blue_chip.png">"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in CROPS.items():
            Image.open(SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        for name in PAINT:
            im = Image.open(ART / f"{name}.png").convert("RGBA")
            im.thumbnail((600, 600))
            im.save(tmp / f"{name}.png")
        page, shot = tmp / "thumb.html", tmp / "thumb.png"
        page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{BODY}</body></html>',
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
