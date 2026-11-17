"""Workshop thumbnail (mod/thumbnail.png, 800x800): the market map mode with the mod's rival-brokers event picture faded
into it, the title and subtitle, the Speculation tab, and a few pieces of the mod's painted art.
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
    "map": ("map_panic", (1060, 330, 2380, 1650)),    # France in panic, contagion stripes, booms
    "spec": ("spec_tall", (0, 0, 845, 740)),          # the Speculation tab: Mania, the mood bar, pressures, risks, history
}
PAINT = ["picture_rival", "state_mania", "crash_risk_bubble"]

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; }}
.map {{ position: absolute; inset: 0; width: {S}px; height: {S}px; filter: saturate(1.15) brightness(.88); }}
.event {{ position: absolute; right: -40px; top: -20px; width: 560px; opacity: .92; filter: sepia(.15) contrast(1.05);
  -webkit-mask-image: radial-gradient(ellipse 62% 60% at 62% 40%, #000 35%, transparent 100%); }}
.shade {{ position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(8,9,13,.88) 0%, rgba(8,9,13,.55) 34%, rgba(8,9,13,0) 58%),
              linear-gradient(rgba(8,9,13,0) 55%, rgba(8,9,13,.7) 100%); }}
.frame {{ position: absolute; inset: 12px; border: 2px solid rgba(214,176,98,.75); }}
h1 {{ position: absolute; left: 40px; top: 34px; margin: 0; font: 104px/0.9 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }}
.sub {{ position: absolute; left: 44px; top: 232px; width: 330px; font: italic 28px/1.25 Garamond, serif; color: #f0d28a;
  text-shadow: 0 2px 6px #000, 0 0 2px #000; }}
.rule {{ position: absolute; left: 44px; top: 218px; width: 220px; height: 2px; background: linear-gradient(90deg, #d6b062, transparent); }}
.spec {{ position: absolute; right: 34px; bottom: 34px; width: 440px; border: 3px solid #b8924a;
  box-shadow: 0 0 0 3px #0b0d12, 0 16px 40px rgba(0,0,0,.9); }}
.p {{ position: absolute; filter: drop-shadow(0 10px 14px rgba(0,0,0,.85)) drop-shadow(0 0 2px rgba(0,0,0,.7)); }}
.chest {{ left: 30px; bottom: 34px; width: 270px; }}
.bubble {{ left: 262px; top: 352px; width: 92px; opacity: .95; }}
"""

BODY = """<img class="map" src="map.png"><img class="event" src="picture_rival.png"><div class="shade"></div><div class="frame"></div>
<h1>Speculative<br>Markets</h1><div class="rule"></div><div class="sub">Booms, banks, panics<br>and rival Exchanges</div>
<img class="spec" src="spec.png"><img class="p chest" src="state_mania.png"><img class="p bubble" src="crash_risk_bubble.png">"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in CROPS.items():
            Image.open(SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        for name in PAINT:
            im = Image.open(ART / f"{name}.png")
            im.thumbnail((1100, 1100))
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
