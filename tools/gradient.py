"""The confidence bar's texture: vanilla's white bar (its shading and rounded ends) tinted along a gradient
from panic red, through teal for normal times and green for credit, to gold for a mania."""
from PIL import Image

STOPS = [(0, (0.66, 0.22, 0.20)), (20, (0.58, 0.28, 0.25)), (45, (0.22, 0.46, 0.52)), (62, (0.22, 0.50, 0.42)),
         (80, (0.24, 0.54, 0.30)), (100, (0.88, 0.64, 0.22))]


def colour(t):
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if t <= b:
            f = (t - a) / (b - a)
            return [x + (y - x) * f for x, y in zip(ca, cb)]
    return list(STOPS[-1][1])


def make(white, out, width=512):
    src = Image.open(white).convert("RGBA")
    w, h = src.size
    ref = max(sum(src.getpixel((w // 2, y))[:3]) / 3 for y in range(h))
    img = Image.new("RGBA", (width, h))
    for x in range(width):
        # keep the vanilla bar's rounded ends, stretch its middle column
        sx = x if x < w // 2 else w - (width - x) if x >= width - w // 2 else w // 2
        c = colour(100 * x / (width - 1))
        for y in range(h):
            r, g, b, a = src.getpixel((sx, y))
            shade = (r + g + b) / 3 / ref
            img.putpixel((x, y), tuple(min(255, int(255 * ch * shade * 1.15)) for ch in c) + (a,))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def glow(out, size=128):
    """A white disc fading out from the centre, tinted in the GUI: the map mode's heat spot behind each badge."""
    img = Image.new("RGBA", (size, size))
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            r = min(1.0, ((x - c) ** 2 + (y - c) ** 2) ** 0.5 / c)
            img.putpixel((x, y), (255, 255, 255, int(255 * (1 - r) ** 1.6)))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
