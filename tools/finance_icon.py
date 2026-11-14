"""The side bar's Finance button: a stock ticker under its glass dome, painted (art/raw/finance_btn.png) and fitted
here to vanilla's main_hud icons (92x92, the picture about as large in it as powerblocs.dds's)."""
from pathlib import Path
from PIL import Image

PATH = "gfx/interface/main_hud/spec_finance_btn.dds"
N, FIT = 92, 72


def build(mod):
    im = Image.open(Path(__file__).parent.parent / "art/raw/finance_btn.png").convert("RGBA")
    im = im.crop(im.getbbox())
    im.thumbnail((FIT, FIT), Image.LANCZOS)
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.alpha_composite(im, ((N - im.width) // 2, (N - im.height) // 2))
    (mod / PATH).parent.mkdir(parents=True, exist_ok=True)
    out.save(mod / PATH)
