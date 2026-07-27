"""Minimal line-art weather glyphs, drawn with canvas primitives.

Every function takes (canvas, cx, cy, size) where canvas provides:
  circle(x, y, r), fill_circle(x, y, r), line(x0, y0, x1, y1),
  arc-free primitives only — keeps us portable across e-ink drivers.

Style: thin outlines, lots of whitespace. Kindle, not dashboard.
"""


def _thick_line(cv, x0, y0, x1, y1, w=2):
    for i in range(w):
        cv.line(x0, y0 + i, x1, y1 + i)


def sun(cv, cx, cy, size):
    r = size // 3
    for rr in (r, r - 1, r - 2):
        cv.circle(cx, cy, rr)
    gap = r + size // 8
    ray = size // 6
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for off in (0, 1):
            cv.line(cx + dx * gap + (off if dy else 0),
                    cy + dy * gap + (off if dx else 0),
                    cx + dx * (gap + ray) + (off if dy else 0),
                    cy + dy * (gap + ray) + (off if dx else 0))
    d = int(gap * 0.707)
    dr = int((gap + ray) * 0.707)
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for off in (0, 1):
            cv.line(cx + dx * d + off, cy + dy * d,
                    cx + dx * dr + off, cy + dy * dr)


def _cloud_shape(cv, cx, cy, size):
    """One clean cloud silhouette: outline circles, then erase the
    interior arcs with white fills so the lobes merge into one shape
    (three raw circles read as Mickey Mouse ears on screen)."""
    r = size // 4
    lobes = ((cx - r, cy, r), (cx + r, cy, r),
             (cx, cy - r // 2, int(r * 1.2)))
    for x, y, rr in lobes:
        cv.circle(x, y, rr)
        cv.circle(x, y, rr - 1)
    for x, y, rr in lobes:
        cv.fill_circle_white(x, y, rr - 2)
    # flat base
    _thick_line(cv, cx - 2 * r, cy + r - 1, cx + 2 * r, cy + r - 1, 3)


def cloud(cv, cx, cy, size):
    _cloud_shape(cv, cx, cy, size)


def partly(cv, cx, cy, size):
    sun(cv, cx - size // 4, cy - size // 4, int(size * 0.6))
    _cloud_shape(cv, cx + size // 8, cy + size // 6, int(size * 0.8))


def rain(cv, cx, cy, size):
    _cloud_shape(cv, cx, cy - size // 6, size)
    r = size // 4
    drop_top = cy + r + size // 12
    for dx in (-r, 0, r):
        cv.line(cx + dx, drop_top, cx + dx - size // 12,
                drop_top + size // 5)


def snow(cv, cx, cy, size):
    _cloud_shape(cv, cx, cy - size // 6, size)
    r = size // 4
    fy = cy + r + size // 8
    for dx in (-r, 0, r):
        _flake(cv, cx + dx, fy + (size // 10 if dx == 0 else 0), size // 10)


def _flake(cv, x, y, r):
    cv.line(x - r, y, x + r, y)
    cv.line(x, y - r, x, y + r)
    d = int(r * 0.7)
    cv.line(x - d, y - d, x + d, y + d)
    cv.line(x - d, y + d, x + d, y - d)


def storm(cv, cx, cy, size):
    _cloud_shape(cv, cx, cy - size // 6, size)
    r = size // 4
    top = cy + r
    # lightning bolt
    cv.line(cx + size // 12, top, cx - size // 12, top + size // 6)
    cv.line(cx - size // 12, top + size // 6, cx + size // 12,
            top + size // 6)
    cv.line(cx + size // 12, top + size // 6, cx - size // 12,
            top + size // 3)


def fog(cv, cx, cy, size):
    w = size // 2
    for i, dy in enumerate((-size // 5, 0, size // 5)):
        shrink = abs(i - 1) * size // 10
        _thick_line(cv, cx - w + shrink, cy + dy, cx + w - shrink,
                    cy + dy, 2)


def moon(cv, cx, cy, size):
    """Solid crescent: black disc with a white 'bite' out of it."""
    r = size // 3
    cv.fill_circle(cx, cy, r)
    cv.fill_circle_white(cx - r // 2, cy - r // 4, r)


GLYPHS = {
    "clear": sun,
    "partly": partly,
    "cloudy": cloud,
    "rain": rain,
    "storm": storm,
    "snow": snow,
    "fog": fog,
    "moon": moon,
}


def draw(cv, condition, cx, cy, size, is_night=False):
    if is_night and condition == "clear":
        condition = "moon"
    GLYPHS.get(condition, cloud)(cv, cx, cy, size)
