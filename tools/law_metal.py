"""Law icons in vanilla's own metal. Vanilla's law icons are flat emblems in one hand-painted rose-and-cream metal with
pale streaks running down. finish() takes our flat emblem (art/raw/emblem/<slot>.png, painted by art/paint.sh) and
fills it with that metal, borrowed from a vanilla law icon: the icon's holes, outline and engraved details are painted
over along its streaks, the icon placed where most of its own metal falls under our shape, and the edge vanilla's
(measured on its law icons). A filter imitating the metal and a Codex finishing pass were tried first; neither looked
painted enough."""
import functools
from pathlib import Path

import numpy
from PIL import Image, ImageChops, ImageFilter

LAWS = Path("G:/SteamLibrary/steamapps/common/Victoria 3/game/gfx/interface/icons/law_icons")
SIZE = 302  # vanilla's law icons; all widths below are its pixels
HIGHLIGHT = 214  # where the brightest tenth of vanilla's law icon metal starts


def blur(a, ry, rx):
    """Separable Gaussian blur of a float array (HxW or HxWxC), ry down and rx across."""
    for axis, r in ((0, ry), (1, rx)):
        x = numpy.arange(-int(3 * r), int(3 * r) + 1)
        k = numpy.exp(-x ** 2 / (2 * r * r))
        k /= k.sum()
        pad = len(x) // 2
        a = numpy.apply_along_axis(lambda v: numpy.convolve(numpy.pad(v, pad, mode="edge"), k, "valid"), axis, a)
    return a


def inpaint(rgb, known):
    """The unknown pixels filled from the known, coarse to fine, blurring far more down than across, so the metal's
    streaks run on through a filled hole instead of stopping at it."""
    out = numpy.where(known[..., None] > 0, rgb, (rgb * known[..., None]).sum((0, 1)) / known.sum())
    for ry, rx in ((60, 12), (30, 6), (16, 3), (8, 1.5), (4, 1), (2, 0.7)):
        num, den = blur(rgb * known[..., None], ry, rx), blur(known, ry, rx)[..., None]
        out = numpy.where(known[..., None] > 0, rgb, numpy.where(den > 0.02, num / numpy.maximum(den, 1e-4), out))
    return out


@functools.lru_cache(maxsize=1)
def sources(count=8):
    """The vanilla law icons with the most plain metal: (RGB, mask of where it is the icon's own metal, not a hole,
    outline or engraved detail)."""
    def inside(im):
        return im.getchannel("A").point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(11))
    ims = [im for im in (Image.open(p).convert("RGBA") for p in sorted(LAWS.glob("*.dds"))) if im.size == (SIZE, SIZE)]
    out = []
    for im in sorted(ims, key=lambda im: -inside(im).histogram()[255])[:count]:
        known = numpy.asarray(inside(im), dtype=float) / 255
        lum = numpy.asarray(im.convert("L"), dtype=float)
        local = blur(lum, 8, 8)
        detail = Image.fromarray((((lum < local - 18) | (lum > local + 45)) * 255).astype("uint8"))
        known *= 1 - numpy.asarray(detail.filter(ImageFilter.MaxFilter(7)), dtype=float) / 255
        out.append((numpy.asarray(im.convert("RGB"), dtype=float), known))
    return out


def place(shape):
    """The source, mirroring and offset putting the most of a source's own metal under our shape."""
    best = None
    for rgb, known in sources():
        for flip in (False, True):
            k = known[:, ::-1] if flip else known
            for dy in range(-40, 41, 8):
                for dx in range(-40, 41, 8):
                    cover = (numpy.roll(k, (dy, dx), (0, 1)) * shape).sum()
                    if best is None or cover > best[0]:
                        best = (cover, rgb, known, flip, dy, dx)
    _, rgb, known, flip, dy, dx = best
    if flip:
        rgb, known = rgb[:, ::-1], known[:, ::-1]
    return numpy.roll(rgb, (dy, dx), (0, 1)), numpy.roll(known, (dy, dx), (0, 1))


def outline(emblem):
    """The emblem's shape at SIZE, padded as vanilla's: its edge smoothed at full size, then shrunk, so it is clean."""
    # the emblem is one plain grey: keep only pixels near it, as Codex sometimes paints a transparency checkerboard
    # into the gaps instead of leaving them transparent
    lum = numpy.asarray(emblem.convert("L"), dtype=float)
    opaque = numpy.asarray(emblem.getchannel("A")) > 128
    fill = numpy.median(lum[opaque])
    a = Image.fromarray(((opaque & (abs(lum - fill) < 40)) * 255).astype("uint8"))
    a = a.crop(a.getbbox())
    a = a.filter(ImageFilter.GaussianBlur(a.width / 300)).point(lambda v: 255 if v > 128 else 0)
    side = max(a.size)
    pad = round(side * 0.06)
    canvas = Image.new("L", (side + 2 * pad, side + 2 * pad))
    canvas.paste(a, ((side - a.width) // 2 + pad, (side - a.height) // 2 + pad))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def finish(emblem):
    """A flat emblem (RGBA, any size) as a vanilla law icon, SIZE square."""
    alpha = outline(emblem)
    solid = alpha.point(lambda v: 255 if v > 128 else 0)
    inside = numpy.asarray(solid) > 0
    rgb, known = place(inside.astype(float))
    tex = inpaint(rgb, known)
    tex *= min(1.15, max(0.9, HIGHLIGHT / numpy.percentile((tex @ [0.299, 0.587, 0.114])[inside], 90)))
    # vanilla's edge: the edge pixel inked, a bright band 2-4 px in, the edges facing the top-left light catching it
    depth = numpy.zeros(inside.shape)
    cur = solid
    for _ in range(5):
        depth += numpy.asarray(cur, dtype=float) / 255
        cur = cur.filter(ImageFilter.MinFilter(3))
    tex *= numpy.select([depth < 1.5, depth < 4.5], [0.5, 1.06], 1.0)[..., None]
    lit = ImageChops.subtract(solid, ImageChops.offset(solid, 2, 2)).filter(ImageFilter.GaussianBlur(0.8))
    tex += ((numpy.asarray(lit, dtype=float) / 255) * (depth >= 1.5))[..., None] * 40
    shape = Image.fromarray(tex.clip(0, 255).astype("uint8")).convert("RGBA")
    shape.putalpha(alpha)
    # and a soft dark shadow round the shape, which also darkens the edges of its holes
    halo = solid.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(2.5))
    out = Image.new("RGBA", alpha.size, (28, 20, 17, 0))
    out.putalpha(halo.point(lambda v: round(v * 0.85)))
    out.alpha_composite(shape)
    return out


if __name__ == "__main__":  # self-check: a plain square comes out as a padded, metal-filled, vanilla-sized icon
    square = Image.new("RGBA", (600, 600))
    square.paste((200, 200, 200, 255), (100, 100, 500, 500))
    icon = finish(square)
    assert icon.size == (SIZE, SIZE)
    centre, corner = icon.getpixel((151, 151)), icon.getpixel((2, 2))
    assert centre[3] == 255 and corner[3] == 0, (centre, corner)
    assert abs(sum(centre[:3]) / 3 - 150) < 60, centre  # metal, not the emblem's grey or black
    print("ok")
