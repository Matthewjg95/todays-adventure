"""Minimal line-art weather glyphs, drawn with canvas primitives.

Every function takes (canvas, cx, cy, size) where canvas provides:
  circle(x, y, r), fill_circle(x, y, r), line(x0, y0, x1, y1),
  arc-free primitives only — keeps us portable across e-ink drivers.

Style: thin outlines, lots of whitespace. Kindle, not dashboard.
"""

import math


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


def _dotted_circle(cv, x, y, r, skip=None):
    """Circle outline as chained short segments; `skip(px, py)` clips
    arcs away. Additive black only, so it renders the same in every
    EPD mode (white-erase tricks fail in the fast modes) — and each
    segment is one panel write, so fewer segments = faster e-ink."""
    steps = max(24, int(math.pi * r / 2))   # ~4px per segment
    prev = None
    for i in range(steps + 1):
        a = 2.0 * math.pi * i / steps
        px = x + r * math.cos(a)
        py = y + r * math.sin(a)
        if skip and skip(px, py):
            prev = None
            continue
        if prev:
            for off in (0, 1):
                cv.line(int(prev[0]), int(prev[1]) + off,
                        int(px), int(py) + off)
        prev = (px, py)


def _lobes(cx, cy, size):
    r = size // 4
    return ((cx - r, cy, r), (cx + r, cy, r),
            (cx, cy - r // 2, int(r * 1.2))), cy + r


def _cloud_shape(cv, cx, cy, size):
    """One cloud silhouette: each lobe's outline, minus any point that
    falls inside a neighboring lobe or below the flat base."""
    lobes, base = _lobes(cx, cy, size)

    def clipped(px, py, me):
        if py > base - 2:
            return True
        for lb in lobes:
            if lb is not me and \
                    (px - lb[0]) ** 2 + (py - lb[1]) ** 2 \
                    < (lb[2] - 2) ** 2:
                return True
        return False

    for lb in lobes:
        _dotted_circle(cv, lb[0], lb[1], lb[2],
                       skip=lambda px, py, lb=lb: clipped(px, py, lb))
    r = size // 4
    _thick_line(cv, cx - 2 * r, base - 1, cx + 2 * r, base - 1, 3)


def cloud(cv, cx, cy, size):
    _cloud_shape(cv, cx, cy, size)


def partly(cv, cx, cy, size):
    """Sun peeking from behind the cloud, clipped so nothing crosses
    the cloud's interior (no white-erase available)."""
    csize = int(size * 0.8)
    ccx, ccy = cx + size // 8, cy + size // 6
    lobes, _ = _lobes(ccx, ccy, csize)

    def in_cloud(px, py):
        for x0, y0, rr in lobes:
            if (px - x0) ** 2 + (py - y0) ** 2 < (rr + 3) ** 2:
                return True
        return False

    scx, scy = cx - size // 4, cy - size // 4
    sr = size // 5
    _dotted_circle(cv, scx, scy, sr, skip=in_cloud)
    gap = sr + size // 10
    ray = size // 7
    for dx, dy in ((0, -1), (-1, 0), (1, 0),
                   (-0.707, -0.707), (0.707, -0.707), (-0.707, 0.707)):
        x1 = scx + dx * (gap + ray)
        y1 = scy + dy * (gap + ray)
        if in_cloud(x1, y1):
            continue
        for off in (0, 1):
            cv.line(int(scx + dx * gap) + off, int(scy + dy * gap),
                    int(x1) + off, int(y1))

    _cloud_shape(cv, ccx, ccy, csize)


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
    """Crescent outline: the moon's edge plus the bite's edge, each
    clipped to the visible sliver. Additive black only."""
    r = size // 3
    bx, by, br = cx - r // 2, cy - r // 4, r
    _dotted_circle(cv, cx, cy, r,
                   skip=lambda px, py:
                   (px - bx) ** 2 + (py - by) ** 2 < (br - 1) ** 2)
    _dotted_circle(cv, bx, by, br,
                   skip=lambda px, py:
                   (px - cx) ** 2 + (py - cy) ** 2 > (r - 1) ** 2)


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
