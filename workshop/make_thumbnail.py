"""Workshop thumbnail (mod/thumbnail.png, 800x800): the mod's own rival-brokers painting under the title.
    py -3 workshop/make_thumbnail.py"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
FONTS = "file:///G:/SteamLibrary/steamapps/common/Victoria%203/game/fonts"
ART = (ROOT / "art/raw/picture_rival.png").as_uri()
OUT = ROOT / "mod/thumbnail.png"
S = 800

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Victorian; src: url("{FONTS}/ParadoxVictorian/ParadoxVictorian-Condensed.otf"); }}
@font-face {{ font-family: Garamond; font-style: italic; src: url("{FONTS}/EBGaramond/EBGaramond-Italic.ttf"); }}
@font-face {{ font-family: Garamond; font-weight: 700; src: url("{FONTS}/EBGaramond/EBGaramond-Bold.ttf"); }}
html, body {{ margin: 0; }}
body {{ position: relative; width: {S}px; height: {S}px; overflow: hidden; background: #0b0d12; }}
.art {{ position: absolute; inset: 0; background: url("{ART}") center 22% / cover; filter: saturate(1.05) contrast(1.05); }}
.shade {{ position: absolute; inset: 0;
  background: radial-gradient(ellipse at 50% 30%, rgba(0,0,0,0) 35%, rgba(6,7,10,.55) 100%),
              linear-gradient(rgba(6,7,10,.25) 0%, rgba(6,7,10,0) 22%, rgba(6,7,10,0) 42%, rgba(6,7,10,.86) 66%, rgba(6,7,10,.97) 100%); }}
.frame {{ position: absolute; inset: 16px; border: 2px solid rgba(214,176,98,.85); box-shadow: inset 0 0 0 6px rgba(6,7,10,.35), inset 0 0 0 8px rgba(214,176,98,.35); }}
.text {{ position: absolute; left: 0; right: 0; bottom: 58px; text-align: center; color: #f3ead3; }}
h1 {{ margin: 6px 0 0; font: 128px/0.92 Victorian, serif; color: #f6e2a8;
  text-shadow: 0 4px 0 #3a2a10, 0 0 30px rgba(0,0,0,.9), 0 6px 18px rgba(0,0,0,.9); }}
.rule {{ display: flex; align-items: center; justify-content: center; gap: 14px; margin: 18px auto 12px; width: 420px; }}
.rule i {{ flex: 1; height: 2px; background: linear-gradient(90deg, transparent, #d6b062); }}
.rule i:last-child {{ background: linear-gradient(90deg, #d6b062, transparent); }}
.rule b {{ width: 12px; height: 12px; transform: rotate(45deg); border: 2px solid #d6b062; }}
.tag {{ font: italic 34px Garamond, serif; color: #efe3c4; text-shadow: 0 2px 8px #000; }}
</style></head><body>
<div class="art"></div><div class="shade"></div><div class="frame"></div>
<div class="text"><h1>Speculative<br>Markets</h1>
<div class="rule"><i></i><b></b><i></i></div><div class="tag">Booms, banks, panics and rival Exchanges</div></div>
</body></html>"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "thumb.html", Path(tmp) / "thumb.png"
        page.write_text(HTML, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={S},{S}", "--allow-file-access-from-files", "--virtual-time-budget=3000",
                        f"--user-data-dir={Path(tmp) / 'chrome'}", f"--screenshot={shot}", page.as_uri()],
                       check=True, capture_output=True)
        im = Image.open(shot).convert("RGB").resize((S, S), Image.LANCZOS)
    im.save(OUT, optimize=True)
    if OUT.stat().st_size >= 1_000_000:  # Steam's preview limit is 1 MiB
        im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(OUT, optimize=True)
    print(OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
