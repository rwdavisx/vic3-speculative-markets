"""Workshop thumbnail (mod/thumbnail.png, 800x800): the title over the market map mode, with the Market Confidence
panel and the Exchange score and Trust block from the Finance tabs. Shots: build_scratch/gallery_src/shots (4K, UI 1.5).
    py -3 workshop/make_thumbnail.py"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "build_scratch/gallery_src/shots"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
FONTS = "file:///G:/SteamLibrary/steamapps/common/Victoria%203/game/fonts"
OUT = ROOT / "mod/thumbnail.png"
S = 800
CROPS = {  # name: (shot, 4K box)
    "map": ("map_panic", (920, 462, 2120, 1662)),             # western Europe: France in panic, contagion stripes
    "conf": ("spec_tall", (2, 70, 843, 565)),                  # Mania: Market Confidence, mood bar, pressures, risks
    "exch": ("trading_tall", (2, 168, 843, 568)),              # Exchange score, Standings, Trust
}

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; }}
.map {{ position: absolute; inset: 0; width: {S}px; height: {S}px; filter: saturate(1.15) contrast(1.05); }}
.shade {{ position: absolute; inset: 0; background: linear-gradient(rgba(8,9,13,.8) 0%, rgba(8,9,13,.35) 26%, rgba(8,9,13,0) 40%),
  radial-gradient(ellipse at 50% 55%, rgba(0,0,0,0) 55%, rgba(8,9,13,.6) 100%); }}
h1 {{ position: absolute; left: 40px; top: 22px; margin: 0; font: 112px/0.9 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }}
.panel {{ position: absolute; border: 3px solid #b8924a; box-shadow: 0 0 0 3px #0b0d12, 0 14px 40px rgba(0,0,0,.85); }}
.conf {{ left: 26px; top: 236px; width: 480px; }}
.exch {{ right: 26px; bottom: 26px; width: 450px; }}
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in CROPS.items():
            Image.open(SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        page, shot = tmp / "thumb.html", tmp / "thumb.png"
        page.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<img class="map" src="map.png"><div class="shade"></div><h1>Speculative<br>Markets</h1>
<img class="panel conf" src="conf.png"><img class="panel exch" src="exch.png"></body></html>""", encoding="utf-8")
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
