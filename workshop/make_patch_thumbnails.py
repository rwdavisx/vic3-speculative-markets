"""Compatibility patch covers (800x800): the main thumbnail's map, art and title (make_thumbnail.py) without the
boom-and-bust cycle, and the partner mod's name over the dimmed map, in the main cover's fonts and colours.
    py -3 workshop/make_patch_thumbnails.py"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

import make_thumbnail as main_cover

ROOT = main_cover.ROOT
S = main_cover.S
PATCHES = {  # partner name -> cover path
    "CMF": ROOT / "workshop/new_items/cmf_preview.png",
    "Morgenröte": ROOT / "compatibility/morgenroete/preview.png",
    "Tech &amp; Res": ROOT / "compatibility/techres/preview.png",
}

CSS = main_cover.CSS + """
.dim { position: absolute; left: 14px; right: 14px; bottom: 14px; height: 520px;
  background: linear-gradient(rgba(8,9,13,0), rgba(8,9,13,.6) 35%, rgba(8,9,13,.8)); }
.box { position: absolute; left: 0; right: 0; top: 480px; text-align: center; }
.name { font: 128px/1 Victorian, serif; color: #fbf3df;
  text-shadow: 0 0 2px #000, 3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 8px 22px rgba(0,0,0,.9); }
.rule2 { width: 300px; height: 2px; margin: 18px auto 14px; background: linear-gradient(90deg, transparent, #d6b062, transparent); }
.sub2 { font: italic 600 40px/1.2 Garamond, serif; color: #f0d28a; text-shadow: 0 0 3px #000, 0 2px 6px #000; }
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (shot, box) in main_cover.CROPS.items():
            Image.open(main_cover.SHOTS / f"{shot}.png").convert("RGB").crop(box).save(tmp / f"{name}.png")
        for name in main_cover.PAINT:
            im = Image.open(main_cover.ART / f"{name}.png")
            im.thumbnail((1100, 1100))
            im.save(tmp / f"{name}.png")
        for name, out in PATCHES.items():
            page, shot = tmp / "p.html", tmp / "p.png"
            page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
                            f'{main_cover.BODY}<div class="dim"></div><div class="box"><div class="name">{name}</div>'
                            f'<div class="rule2"></div><div class="sub2">Compatibility Patch</div></div></body></html>',
                            encoding="utf-8")
            subprocess.run([main_cover.CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={S},{S}", "--allow-file-access-from-files",
                            "--virtual-time-budget=3000", f"--user-data-dir={tmp / 'chrome'}", f"--screenshot={shot}",
                            page.as_uri()], check=True, capture_output=True)
            im = Image.open(shot).convert("RGB").resize((S, S), Image.LANCZOS)
            im.save(out, optimize=True)
            if out.stat().st_size >= 1_000_000:  # Steam's preview limit is 1 MiB
                im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(out, optimize=True)
            print(out, out.stat().st_size)


if __name__ == "__main__":
    main()
