"""Generate the weather scene art (desktop-side). v2: 2x detail.

Layered grayscale landscapes, 540x320, one per condition. Design
rules the renderer depends on:
  - the GLYPH ZONE (x 160..380, y 30..220) stays clear: the date and
    the animated vector glyph live there
  - foreground art fills the band's lower third; sky details (wisps,
    birds, stars) keep to the margins
  - the bottom edge gets a grass fringe so the band doesn't cut a
    hard line against the page

Run:  python tools/gen_scenes.py   -> writes scenes/*.png
"""

import math
import os
import random

from PIL import Image, ImageDraw

W, H = 540, 320
OUT = os.path.join(os.path.dirname(__file__), "..", "scenes", "v2")

WHITE = 255


# ----------------------------------------------------------------------
# terrain
# ----------------------------------------------------------------------

def _ridge(x, y_base, amp, phase, wavelen):
    return y_base - amp * math.sin((x + phase) / wavelen) \
        - amp * 0.4 * math.sin((x * 1.7 + phase * 2) / wavelen)


def _hill(draw, y_base, amp, phase, wavelen, shade):
    pts = [(0, H)]
    for x in range(0, W + 1, 4):
        pts.append((x, _ridge(x, y_base, amp, phase, wavelen)))
    pts.append((W, H))
    draw.polygon(pts, fill=shade)
    return (y_base, amp, phase, wavelen)


def _contours(draw, hill, shade, seed=1, n=26):
    """Short curved strokes following the hill's slope: field texture."""
    rng = random.Random(seed)
    y_base, amp, phase, wavelen = hill
    for _ in range(n):
        x = rng.randint(8, W - 24)
        top = _ridge(x, y_base, amp, phase, wavelen)
        y = rng.uniform(top + 8, H - 8)
        ln = rng.randint(8, 22)
        bow = rng.uniform(2, 5)
        draw.arc([x, y - bow, x + ln, y + bow], 200, 340, fill=shade)


def _grass_edge(draw, shade, seed=2):
    """Tuft fringe along the bottom so the band ends softly."""
    rng = random.Random(seed)
    for x in range(4, W - 4, 7):
        h = rng.randint(4, 11)
        lean = rng.randint(-3, 3)
        draw.line([(x, H), (x + lean, H - h)], fill=shade, width=1)


def _path(draw, x_at_bottom, hill, shade):
    """A lane narrowing toward the ridge: leads the eye in."""
    y_base, amp, phase, wavelen = hill
    top_x = x_at_bottom - 60
    top_y = _ridge(top_x, y_base, amp, phase, wavelen) + 6
    pts = [(x_at_bottom - 26, H), (x_at_bottom + 26, H),
           (top_x + 4, top_y), (top_x - 4, top_y)]
    draw.polygon(pts, fill=shade)


# ----------------------------------------------------------------------
# flora
# ----------------------------------------------------------------------

def _bare_tree(draw, x, y, size, shade, seed=7):
    rng = random.Random(seed)

    def branch(x0, y0, angle, length, depth):
        if depth == 0 or length < 3:
            return
        x1 = x0 + length * math.sin(angle)
        y1 = y0 - length * math.cos(angle)
        draw.line([(x0, y0), (x1, y1)], fill=shade,
                  width=max(1, depth - 1))
        n = 2 if depth > 2 else rng.choice((1, 2))
        for _ in range(n):
            branch(x1, y1, angle + rng.uniform(-0.7, 0.7),
                   length * rng.uniform(0.6, 0.75), depth - 1)

    branch(x, y, rng.uniform(-0.08, 0.08), size * 0.42, 6)


def _pine(draw, x, y, size, shade):
    draw.rectangle([x - 2, y - size * 0.15, x + 2, y], fill=shade)
    tiers = 5
    for i in range(tiers):
        t = i / tiers
        top = y - size * (0.15 + 0.85 * (1 - t))
        base = y - size * (0.15 + 0.85 * (1 - t) * 0.66)
        half = size * 0.30 * (0.35 + 0.65 * t)
        draw.polygon([(x, top), (x - half, base), (x + half, base)],
                     fill=shade)


def _canopy_tree(draw, x, y, size, trunk_shade, leaf_shade, seed=3):
    rng = random.Random(seed)
    draw.line([(x, y), (x, y - size * 0.45)], fill=trunk_shade, width=4)
    draw.line([(x, y - size * 0.25), (x - size * 0.12, y - size * 0.4)],
              fill=trunk_shade, width=2)
    draw.line([(x, y - size * 0.33), (x + size * 0.1, y - size * 0.45)],
              fill=trunk_shade, width=2)
    cx, cy = x, y - size * 0.58
    for _ in range(14):
        dx = rng.uniform(-size * 0.24, size * 0.24)
        dy = rng.uniform(-size * 0.18, size * 0.13)
        r = rng.uniform(size * 0.10, size * 0.19)
        draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                     fill=leaf_shade)
    # canopy shading: darker blobs along the underside
    for _ in range(5):
        dx = rng.uniform(-size * 0.18, size * 0.18)
        r = rng.uniform(size * 0.07, size * 0.12)
        draw.ellipse([cx + dx - r, cy + size * 0.06 - r,
                      cx + dx + r, cy + size * 0.06 + r],
                     fill=min(255, leaf_shade - 35))


def _reeds(draw, x, y, shade, seed=5, n=5):
    rng = random.Random(seed)
    for i in range(n):
        rx = x + i * 6 + rng.randint(-2, 2)
        h = rng.randint(16, 30)
        draw.line([(rx, y), (rx + rng.randint(-3, 3), y - h)],
                  fill=shade, width=1)
        draw.ellipse([rx - 2, y - h - 7, rx + 2, y - h], fill=shade)


def _flowers(draw, hill, shade, seed=8, n=12):
    rng = random.Random(seed)
    y_base, amp, phase, wavelen = hill
    for _ in range(n):
        x = rng.randint(10, W - 10)
        top = _ridge(x, y_base, amp, phase, wavelen)
        y = rng.uniform(top + 10, H - 12)
        draw.line([(x, y), (x, y - 6)], fill=shade, width=1)
        for a in range(0, 360, 90):
            fx = x + 2.6 * math.cos(math.radians(a + 45))
            fy = y - 6 + 2.6 * math.sin(math.radians(a + 45))
            draw.ellipse([fx - 1.4, fy - 1.4, fx + 1.4, fy + 1.4],
                         outline=shade)


# ----------------------------------------------------------------------
# structures & sky
# ----------------------------------------------------------------------

def _fence(draw, x0, x1, y, shade, broken=None):
    posts = list(range(x0, x1, 26))
    for i, x in enumerate(posts):
        if broken is not None and i == broken:
            draw.line([(x, y - 6), (x + 8, y)], fill=shade, width=3)
            continue
        draw.line([(x, y - 14), (x, y)], fill=shade, width=3)
    draw.line([(x0, y - 10), (x1 - 12, y - 10)], fill=shade, width=2)
    draw.line([(x0, y - 4), (x1 - 12, y - 4)], fill=shade, width=1)


def _cabin(draw, x, y, s, shade, lit_window=False, smoke=True):
    w, h = s, int(s * 0.62)
    draw.rectangle([x, y - h, x + w, y], fill=shade)
    draw.polygon([(x - s * 0.12, y - h), (x + w + s * 0.12, y - h),
                  (x + w * 0.5, y - h - s * 0.42)],
                 fill=max(0, shade - 30))
    wx, wy = x + w * 0.62, y - h * 0.55
    draw.rectangle([wx, wy, wx + w * 0.22, wy + h * 0.34],
                   fill=245 if lit_window else max(0, shade - 25))
    if lit_window:
        draw.line([(wx + w * 0.11, wy), (wx + w * 0.11, wy + h * 0.34)],
                  fill=shade, width=1)
    draw.rectangle([x + w * 0.16, y - h * 0.55, x + w * 0.38, y],
                   fill=max(0, shade - 25))
    if smoke:
        cx = x + w * 0.82
        draw.rectangle([cx - 3, y - h - s * 0.34, cx + 3, y - h - s * 0.16],
                       fill=shade)
        for i in range(3):
            r = 4 + i * 2
            sx = cx + (4 + i * 7) * math.sin(i * 1.8)
            sy = y - h - s * 0.42 - i * 13
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], outline=175)


def _windmill(draw, x, y, s, shade):
    draw.polygon([(x - s * 0.08, y), (x + s * 0.08, y),
                  (x + s * 0.04, y - s), (x - s * 0.04, y - s)],
                 fill=shade)
    hx, hy = x, y - s
    for a in (35, 125, 215, 305):
        bx = hx + s * 0.42 * math.cos(math.radians(a))
        by = hy + s * 0.42 * math.sin(math.radians(a))
        draw.line([(hx, hy), (bx, by)], fill=shade, width=2)
        px = hx + s * 0.30 * math.cos(math.radians(a - 10))
        py = hy + s * 0.30 * math.sin(math.radians(a - 10))
        draw.line([(bx, by), (px, py)], fill=shade, width=1)
    draw.ellipse([hx - 3, hy - 3, hx + 3, hy + 3], fill=shade)


def _hay(draw, x, y, s, shade):
    draw.ellipse([x - s, y - s, x + s, y + s], fill=shade)
    draw.arc([x - s * 0.7, y - s, x + s * 0.2, y + s], 90, 270,
             fill=max(0, shade - 35))
    draw.arc([x - s * 0.2, y - s, x + s * 0.7, y + s], 270, 90,
             fill=max(0, shade - 35))


def _birds(draw, spots, shade=90):
    for (x, y, s) in spots:
        draw.arc([x - s, y - s // 2, x, y + s // 2], 200, 340, fill=shade)
        draw.arc([x, y - s // 2, x + s, y + s // 2], 200, 340, fill=shade)


def _wisp(draw, x, y, s, shade=234):
    for (dx, dy, r) in ((0, 0, s), (s * 0.7, s * 0.1, s * 0.75),
                        (-s * 0.7, s * 0.15, s * 0.6)):
        draw.ellipse([x + dx - r, y + dy - r * 0.45,
                      x + dx + r, y + dy + r * 0.45], fill=shade)


def _stars(draw, seed, n, shade=60, y_max=100):
    rng = random.Random(seed)
    for _ in range(n):
        x = rng.randint(15, W - 15)
        y = rng.randint(14, y_max)
        if 150 < x < 390:
            continue                   # glyph/date zone stays clean
        s = rng.choice((2, 2, 3))
        draw.line([(x - s, y), (x + s, y)], fill=shade)
        draw.line([(x, y - s), (x, y + s)], fill=shade)


def _shooting_star(draw, x, y, ln, shade=110):
    draw.line([(x, y), (x + ln, y + ln * 0.35)], fill=shade, width=1)
    draw.line([(x + ln * 0.75, y + ln * 0.26),
               (x + ln, y + ln * 0.35)], fill=60, width=2)


# ----------------------------------------------------------------------
# scenes
# ----------------------------------------------------------------------

def _base(shades=(205, 165, 115), extra_far=None):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    if extra_far is not None:
        _hill(d, 246, 20, 700, 170, extra_far)
    far = _hill(d, 262, 16, 40, 95, shades[0])
    mid = _hill(d, 284, 14, 260, 120, shades[1])
    fore = _hill(d, 308, 12, 520, 150, shades[2])
    return img, d, far, mid, fore


def scene_clear():
    img, d, far, mid, fore = _base((200, 158, 108), extra_far=228)
    _path(d, 400, mid, 230)
    _canopy_tree(d, 448, 292, 125, 70, 150, seed=5)
    _hay(d, 130, 296, 12, 140)
    _hay(d, 158, 300, 9, 150)
    _fence(d, 24, 200, 300, 95)
    _flowers(d, fore, 90, seed=8)
    _contours(d, fore, 135, seed=1)
    _birds(d, [(80, 56, 9), (110, 68, 7), (455, 40, 8)])
    _wisp(d, 60, 90, 26)
    _wisp(d, 480, 60, 22)
    _grass_edge(d, 130)
    return img


def scene_partly():
    img, d, far, mid, fore = _base((205, 162, 112), extra_far=230)
    _path(d, 150, mid, 232)
    _canopy_tree(d, 88, 294, 110, 75, 160, seed=11)
    _canopy_tree(d, 470, 300, 78, 80, 168, seed=17)
    _hay(d, 395, 300, 11, 145)
    _fence(d, 300, 452, 304, 100)
    _contours(d, fore, 138, seed=3)
    _birds(d, [(430, 62, 8), (462, 74, 6)])
    _wisp(d, 90, 60, 24)
    _grass_edge(d, 132)
    return img


def scene_cloudy():
    img, d, far, mid, fore = _base((210, 170, 122), extra_far=232)
    _windmill(d, 96, 288, 72, 105)
    _bare_tree(d, 462, 268, 122, 85, seed=9)
    _fence(d, 210, 400, 302, 110)
    _birds(d, [(500, 96, 7)])
    _contours(d, fore, 142, seed=4)
    _wisp(d, 70, 70, 28, 228)
    _wisp(d, 470, 52, 24, 228)
    _grass_edge(d, 138)
    return img


def scene_rain():
    img, d, far, mid, fore = _base((212, 172, 124), extra_far=234)
    _bare_tree(d, 78, 270, 118, 80, seed=4)
    # puddles with rings
    for (px, pw) in ((296, 50), (382, 32), (452, 24)):
        d.ellipse([px, 304, px + pw, 312], fill=230)
        d.arc([px + pw * 0.3, 305, px + pw * 0.62, 310], 0, 360, fill=180)
    _reeds(d, 490, 310, 100, seed=5)
    _reeds(d, 240, 314, 110, seed=9, n=4)
    d.rectangle([158, 288, 162, 306], fill=95)      # mailbox post
    d.rectangle([150, 280, 172, 290], fill=95)
    _contours(d, fore, 142, seed=6, n=18)
    _grass_edge(d, 135)
    return img


def scene_storm():
    img, d, far, mid, fore = _base((190, 148, 96), extra_far=224)
    _bare_tree(d, 472, 264, 128, 60, seed=13)
    for x in range(48, 250, 18):                     # wind-flattened grass
        d.arc([x, 294, x + 20, 310], 190, 300, fill=110)
    _fence(d, 60, 216, 302, 90, broken=3)
    _birds(d, [(70, 60, 10)])
    _contours(d, fore, 118, seed=7)
    _grass_edge(d, 110)
    return img


def scene_snow():
    img, d, far, mid, fore = _base((235, 222, 205), extra_far=242)
    for (x, s) in ((62, 100), (100, 72), (452, 118), (496, 84)):
        _pine(d, x, 300, s, 130)
    _cabin(d, 210, 302, 46, 120, smoke=True)
    # snowman with hat and stick arms
    d.ellipse([392, 290, 418, 314], outline=140, width=2)
    d.ellipse([397, 274, 413, 291], outline=140, width=2)
    d.rectangle([400, 266, 410, 274], fill=120)
    d.line([(396, 282), (386, 274)], fill=120, width=1)
    d.line([(414, 282), (424, 276)], fill=120, width=1)
    # drift shadows
    for (x, wd) in ((140, 60), (320, 48)):
        d.arc([x, 306, x + wd, 316], 180, 360, fill=215)
    _grass_edge(d, 190)
    return img


def scene_fog():
    img, d, far, mid, fore = _base((215, 180, 140), extra_far=235)
    # trees dissolving with distance: lighter the farther back
    _bare_tree(d, 100, 252, 84, 190, seed=21)
    _bare_tree(d, 200, 262, 96, 160, seed=22)
    _bare_tree(d, 430, 272, 112, 110, seed=6)
    _fence(d, 290, 396, 306, 165)
    for (y, h, s) in ((232, 16, 244), (258, 12, 240), (282, 9, 238),
                      (300, 7, 236)):
        d.rectangle([0, y, W, y + h], fill=s)
    _grass_edge(d, 165)
    return img


def scene_moon():
    img, d, far, mid, fore = _base((150, 110, 70), extra_far=200)
    for (x, s) in ((88, 96), (128, 66), (460, 108)):
        _pine(d, x, 300, s, 55)
    _cabin(d, 350, 304, 52, 70, lit_window=True, smoke=True)
    _stars(d, seed=2, n=22, y_max=105)
    _shooting_star(d, 402, 38, 46)
    _contours(d, fore, 62, seed=10, n=14)
    _grass_edge(d, 58)
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
