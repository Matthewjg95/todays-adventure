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


def sun(cv, cx, cy, size, ray_scale=1.0):
    r = size // 3
    for rr in (r, r - 1, r - 2):
        cv.circle(cx, cy, rr)
    gap = r + size // 8
    ray = int(size // 6 * ray_scale)
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
    """Clipped circle outline. Uses hardware drawArc when the canvas
    has it (a handful of panel writes instead of hundreds of tiny
    segments), else falls back to chained segments. Additive black
    only, so it renders the same in every EPD mode."""
    if getattr(cv, "arc", None):
        step = 4
        n = 360 // step
        ok = []
        for i in range(n):
            a = math.radians(i * step)
            ok.append(not (skip and skip(x + r * math.cos(a),
                                         y + r * math.sin(a))))
        if all(ok):
            cv.arc(x, y, r, 0, 360)
            return
        try:
            start = ok.index(False)
        except ValueError:
            start = 0
        idx = 0
        while idx < n:
            if ok[(start + idx) % n]:
                a0 = idx
                while idx < n and ok[(start + idx) % n]:
                    idx += 1
                cv.arc(x, y, r, (start + a0) * step,
                       (start + idx) * step)
            else:
                idx += 1
        return
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


# --------------------------------------------------------------------------
# Animation: only the moving parts redraw each frame (a small white
# rect-erase plus a handful of primitives), so partial refresh stays
# cheap and localized. Lively weather moves; calm skies stay still.
# --------------------------------------------------------------------------

def _drop_zone(cx, cy, size):
    r = size // 4
    top = (cy - size // 6) + r + size // 12
    return (cx - r - 24, top - 2, 2 * r + 48, size // 5 + 22), top


def _drop(cv, x, y, size):
    for off in (0, 1):  # 2px thick so every drop reads clearly
        cv.line(x + off, y, x - size // 12 + off, y + size // 8)


def _anim_rain(cv, cx, cy, size, t):
    box, top = _drop_zone(cx, cy, size)
    cv.rect_white(*box)
    r = size // 4
    span = size // 5 + 8
    for i, dx in enumerate((-r + 6, 0, r - 2)):
        yy = top + int((t * 26 + i * 9) % span)
        _drop(cv, cx + dx, yy, size)


def _anim_storm(cv, cx, cy, size, t):
    box, top = _drop_zone(cx, cy, size)
    cv.rect_white(*box)
    r = size // 4
    span = size // 5 + 8
    for i, dx in enumerate((-r + 6, r - 2)):
        yy = top + int((t * 26 + i * 11) % span)
        _drop(cv, cx + dx, yy, size)
    if int(t * 2) % 4 != 3:          # bolt blinks off now and then
        cv.line(cx + size // 12, top, cx - size // 12, top + size // 6)
        cv.line(cx - size // 12, top + size // 6,
                cx + size // 12, top + size // 6)
        cv.line(cx + size // 12, top + size // 6,
                cx - size // 12, top + size // 3)


def _anim_snow(cv, cx, cy, size, t):
    box, top = _drop_zone(cx, cy, size)
    cv.rect_white(*box)
    r = size // 4
    span = size // 5 + 12
    for i, dx in enumerate((-r, 0, r)):
        yy = top + int((t * 12 + i * 13) % span)
        sway = int(6 * math.sin(t * 2.0 + i))
        _flake(cv, cx + dx + sway, yy + 4, size // 10)


def _anim_clear(cv, cx, cy, size, t):
    pad = size * 2 // 3
    cv.rect_white(cx - pad, cy - pad, 2 * pad, 2 * pad)
    sun(cv, cx, cy, size, 1.0 + 0.25 * math.sin(t * 2.2))


def _anim_fog(cv, cx, cy, size, t):
    w = size // 2
    cv.rect_white(cx - w - 14, cy - size // 4 - 6,
                  2 * w + 28, size // 2 + 12)
    for i, dy in enumerate((-size // 5, 0, size // 5)):
        shrink = abs(i - 1) * size // 10
        drift = int(8 * math.sin(t * 1.6 + i * 2.1))
        _thick_line(cv, cx - w + shrink + drift, cy + dy,
                    cx + w - shrink + drift, cy + dy, 2)


_ANIMATORS = {
    "rain": _anim_rain,
    "storm": _anim_storm,
    "snow": _anim_snow,
    "clear": _anim_clear,
    "fog": _anim_fog,
    # partly / cloudy / moon: calm skies hold still
}


def animate(cv, condition, cx, cy, size, is_night, seconds,
            after_frame=None):
    """Run the glyph's motion for `seconds`, then settle at rest.
    `after_frame(cv)` repaints anything the erase zone may clip (the
    medallion ring). Returns False when this weather has no motion."""
    import time
    if is_night and condition == "clear":
        condition = "moon"
    anim = _ANIMATORS.get(condition)
    if anim is None:
        return False
    t, dt = 0.0, 0.30
    while t < seconds:
        anim(cv, cx, cy, size, t)
        if after_frame:
            after_frame(cv)
        time.sleep(0.10)
        t += dt
    anim(cv, cx, cy, size, 0.0)      # rest pose
    if after_frame:
        after_frame(cv)
    return True
