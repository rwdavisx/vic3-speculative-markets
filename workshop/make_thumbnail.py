"""Workshop thumbnail (mod/thumbnail.png, 800x800), on one centred axis: the title, Panic and Mania in the mod's paintings
either side of a panicking France on the market map, the real mood bar between them, and the four Finance tabs as
their painted icons. Shots: build_scratch/gallery_src/shots (4K, UI 1.5); art: art/raw.
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
    "map": ("map_panic", (1224, 537, 2424, 1737)),    # France in panic at the centre, contagion stripes, booms
    "bar": ("spec_tall", (40, 310, 815, 380)),        # the mood bar, Shaken to Mania, the Panic line
}
TABS = [("interest_feverish", "Speculation"), ("bank_rescue", "Banking"),
        ("concept_financial_centre", "Exchanges"), ("rival_raid", "Competitors")]
PAINT = ["state_panic", "state_mania"] + [n for n, _ in TABS]

CSS = f"""
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
@font-face {{ font-family: Garamond; font-weight: 700; src: url("{FONTS}/EBGaramond/EBGaramond-Bold.ttf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; color: #f3ead3; }}
.map {{ position: absolute; inset: 0; width: {S}px; height: {S}px; filter: saturate(1.15) brightness(.9); }}
.shade {{ position: absolute; inset: 0;
  background: linear-gradient(rgba(8,9,13,.92) 0%, rgba(8,9,13,.55) 20%, rgba(8,9,13,.05) 34%, rgba(8,9,13,.05) 58%, rgba(8,9,13,.9) 74%, rgba(8,9,13,.96) 100%),
              radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(8,9,13,.6) 100%); }}
.frame {{ position: absolute; inset: 12px; border: 2px solid rgba(214,176,98,.75); }}
.c {{ position: absolute; left: 0; right: 0; text-align: center; }}
h1 {{ top: 34px; margin: 0; font: 96px/1 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }}
.tag {{ top: 136px; font: italic 28px Garamond, serif; color: #f0d28a; text-shadow: 0 2px 6px #000; }}
.p {{ position: absolute; filter: drop-shadow(0 10px 14px rgba(0,0,0,.85)) drop-shadow(0 0 2px rgba(0,0,0,.7)); }}
.panic {{ left: 34px; top: 196px; width: 250px; }}
.mania {{ right: 34px; top: 196px; width: 250px; }}
.bar {{ position: absolute; left: 40px; top: 470px; width: 720px; border: 3px solid #b8924a;
  box-shadow: 0 0 0 3px #0b0d12, 0 12px 30px rgba(0,0,0,.85); }}
.tabs {{ position: absolute; left: 40px; right: 40px; top: 590px; display: flex; justify-content: space-between; }}
.tabs div {{ width: 170px; text-align: center; }}
.tabs img {{ width: 112px; height: 112px; object-fit: contain; filter: drop-shadow(0 8px 10px rgba(0,0,0,.85)); }}
.tabs b {{ display: block; margin-top: 4px; font: 700 23px Garamond, serif; letter-spacing: 1px; color: #f0d28a; }}
"""

BODY = ('<img class="map" src="map.png"><div class="shade"></div><div class="frame"></div>'
        '<h1 class="c">Speculative Markets</h1><div class="c tag">Booms, banks, panics and rival Exchanges</div>'
        '<img class="p panic" src="state_panic.png"><img class="p mania" src="state_mania.png"><img class="bar" src="bar.png">'
        '<div class="tabs">' + "".join(f'<div><img src="{n}.png"><b>{t}</b></div>' for n, t in TABS) + "</div>")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in CROPS.items():
            Image.open(SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        for name in PAINT:
            im = Image.open(ART / f"{name}.png").convert("RGBA")
            im.thumbnail((560, 560))
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
