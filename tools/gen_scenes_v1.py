"""Generate the weather scene art (desktop-side).

Layered grayscale landscapes, 540x320, one per condition. Design
rules the renderer depends on:
  - sky band (y 0..~200) stays light: the date overlays at the top
    and the animated vector glyph lives at (270, 140)
  - foreground art (hills, trees) occupies y ~200..320
  - full grayscale is fine: the panel shows 16 real grays

Run:  python tools/gen_scenes.py   -> writes scenes/*.png
"""

import math
import os
import random

from PIL import Image, ImageDraw

W, H = 540, 320
OUT = os.path.join(os.path.dirname(__file__), "..", "scenes", "v1")

WHITE = 255


def _hill(draw, y_base, amp, phase, wavelen, shade, y_lift=0):
    """One rolling-hill layer: a filled sine ridge down to the bottom."""
    pts = [(0, H)]
    for x in range(0, W + 1, 4):
        y = y_base - amp * math.sin((x + phase) / wavelen) \
            - amp * 0.4 * math.sin((x * 1.7 + phase * 2) / wavelen) - y_lift
        pts.append((x, y))
    pts.append((W, H))
    draw.polygon(pts, fill=shade)


def _bare_tree(draw, x, y, size, shade, seed=7):
    """Recursive winter tree: trunk with forking branches."""
    rng = random.Random(seed)

    def branch(x0, y0, angle, length, depth):
        if depth == 0 or length < 3:
            return
        x1 = x0 + length * math.sin(angle)
        y1 = y0 - length * math.cos(angle)
        w = max(1, depth - 1)
        draw.line([(x0, y0), (x1, y1)], fill=shade, width=w)
        n = 2 if depth > 2 else rng.choice((1, 2))
        for _ in range(n):
            branch(x1, y1, angle + rng.uniform(-0.7, 0.7),
                   length * rng.uniform(0.6, 0.75), depth - 1)

    branch(x, y, rng.uniform(-0.08, 0.08), size * 0.42, 6)


def _pine(draw, x, y, size, shade):
    """Simple pine: stacked triangles + trunk."""
    draw.rectangle([x - 2, y - size * 0.15, x + 2, y], fill=shade)
    tiers = 4
    for i in range(tiers):
        t = i / tiers
        top = y - size * (0.15 + 0.85 * (1 - t))
        base = y - size * (0.15 + 0.85 * (1 - t) * 0.62)
        half = size * 0.30 * (0.35 + 0.65 * t)
        draw.polygon([(x, top), (x - half, base), (x + half, base)],
                     fill=shade)


def _canopy_tree(draw, x, y, size, trunk_shade, leaf_shade, seed=3):
    """Summer tree: trunk plus a cluster of overlapping leaf blobs."""
    rng = random.Random(seed)
    draw.line([(x, y), (x, y - size * 0.45)], fill=trunk_shade, width=4)
    draw.line([(x, y - size * 0.25), (x - size * 0.12, y - size * 0.4)],
              fill=trunk_shade, width=2)
    cx, cy = x, y - size * 0.58
    for _ in range(9):
        dx = rng.uniform(-size * 0.22, size * 0.22)
        dy = rng.uniform(-size * 0.16, size * 0.12)
        r = rng.uniform(size * 0.12, size * 0.2)
        draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                     fill=leaf_shade)


def _fence(draw, x0, x1, y, shade):
    for x in range(x0, x1, 26):
        draw.line([(x, y - 14), (x, y)], fill=shade, width=3)
    draw.line([(x0, y - 10), (x1 - 12, y - 10)], fill=shade, width=2)


def _birds(draw, spots, shade=90):
    for (x, y, s) in spots:
        draw.arc([x - s, y - s // 2, x, y + s // 2], 200, 340, fill=shade)
        draw.arc([x, y - s // 2, x + s, y + s // 2], 200, 340, fill=shade)


def _base(shades=(205, 165, 115), lifts=(0, 0, 0)):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _hill(d, 262, 16, 40, 95, shades[0], lifts[0])
    _hill(d, 284, 14, 260, 120, shades[1], lifts[1])
    _hill(d, 308, 12, 520, 150, shades[2], lifts[2])
    return img, d


def scene_clear():
    img, d = _base((200, 158, 108))
    _canopy_tree(d, 445, 292, 120, 70, 150, seed=5)
    _fence(d, 30, 200, 300, 95)
    _birds(d, [(90, 60, 9), (120, 72, 7)])
    return img


def scene_partly():
    img, d = _base((205, 162, 112))
    _canopy_tree(d, 90, 296, 105, 75, 160, seed=11)
    _fence(d, 330, 520, 302, 100)
    _birds(d, [(430, 66, 8)])
    return img


def scene_cloudy():
    img, d = _base((210, 170, 122))
    _bare_tree(d, 460, 268, 120, 85, seed=9)
    _fence(d, 40, 190, 298, 110)
    return img


def scene_rain():
    img, d = _base((212, 172, 124))
    _bare_tree(d, 80, 272, 115, 80, seed=4)
    # puddle hints on the foreground hill
    for (px, pw) in ((300, 46), (380, 30)):
        d.ellipse([px, 306, px + pw, 312], fill=228)
    return img


def scene_storm():
    img, d = _base((190, 148, 96))
    _bare_tree(d, 470, 266, 125, 60, seed=13)
    # wind-bent grass strokes
    for x in range(60, 240, 22):
        d.arc([x, 296, x + 18, 310], 180, 300, fill=120)
    return img


def scene_snow():
    img, d = _base((235, 222, 205))
    for (x, s) in ((70, 95), (105, 70), (460, 110), (498, 80)):
        _pine(d, x, 300, s, 130)
    # snowman, small, left of center
    d.ellipse([210, 292, 234, 314], outline=140, width=2)
    d.ellipse([215, 278, 229, 293], outline=140, width=2)
    return img


def scene_fog():
    img, d = _base((215, 180, 140))
    _bare_tree(d, 420, 270, 110, 120, seed=6)
    # fog banks: soft white bands erasing the middle distance
    for (y, h) in ((236, 14), (262, 10), (286, 8)):
        d.rectangle([0, y, W, y + h], fill=242)
    return img


def scene_moon():
    img, d = _base((150, 110, 70))
    for (x, s) in ((95, 90), (455, 100)):
        _pine(d, x, 300, s, 55)
    # stars: little four-point sparks high in the sky corners
    rng = random.Random(2)
    for _ in range(14):
        x = rng.randint(15, W - 15)
        y = rng.randint(14, 95)
        if 150 < x < 390:
            continue          # keep the glyph/date zone clean
        s = rng.choice((2, 3))
        d.line([(x - s, y), (x + s, y)], fill=60)
        d.line([(x, y - s), (x, y + s)], fill=60)
    return img


SCENES = {
    "clear": scene_clear,
    "partly": scene_partly,
    "cloudy": scene_cloudy,
    "rain": scene_rain,
    "storm": scene_storm,
    "snow": scene_snow,
    "fog": scene_fog,
    "moon": scene_moon,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in SCENES.items():
        img = fn()
        path = os.path.join(OUT, "%s.png" % name)
        img.save(path, optimize=True)
        print("%s.png  %5d bytes" % (name, os.path.getsize(path)))


if __name__ == "__main__":
    main()
