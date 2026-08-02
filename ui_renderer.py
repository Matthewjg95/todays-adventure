"""Render the day onto the M5Paper (540 x 960, portrait, 16-gray e-ink).

All layout lives here. The renderer draws through a small Canvas
abstraction so the same layout code runs on:
  - the real M5Paper (UIFlow MicroPython firmware)
  - desktop simulation (prints a text mockup, for development)

E-ink notes:
  - We do ONE full refresh per update (hourly). At that cadence a full
    refresh is better than partial: it erases ghosting and the flash is
    a non-issue once an hour.
"""

import artwork
import config

W, H = 540, 960

# BIG_TEXT experiment: bump every font one step up the DejaVu ladder.
_UPSIZE = {18: 24, 24: 40, 40: 56, 56: 72, 72: 72}


def S(size):
    if getattr(config, "BIG_TEXT", False):
        return _UPSIZE.get(size, size)
    return size


# --------------------------------------------------------------------------
# Canvas backends
# --------------------------------------------------------------------------

class UIFlow2Canvas:
    """UIFlow2.0 (MicroPython, M5GFX) backend for M5Paper v1.1."""

    BLACK = 0x000000
    WHITE = 0xFFFFFF
    SHADES = {"black": 0x000000, "gray": 0x333333, "light": 0x777777}

    def __init__(self):
        import M5
        from M5 import Widgets
        M5.begin()
        self.lcd = M5.Lcd
        # Force portrait 540x960 regardless of the panel's native
        # rotation.
        for rot in range(4):
            self.lcd.setRotation(rot)
            if self.lcd.width() == W and self.lcd.height() == H:
                break
        self._fonts = {
            72: Widgets.FONTS.DejaVu72,
            56: Widgets.FONTS.DejaVu56,
            40: Widgets.FONTS.DejaVu40,
            24: Widgets.FONTS.DejaVu24,
            18: Widgets.FONTS.DejaVu18,
        }
        self._ink = self.BLACK
        self.lcd.setTextColor(self.BLACK, self.WHITE)
        # This binding pushes every primitive straight to the panel,
        # and its default EPD mode (1, "quality") does a full flash per
        # draw call — clouds flashed 4-5 times. Instead: one clean
        # quality-mode wipe to white (also erases ghosting), then
        # mode 3 ("fast") for content: quiet partial updates that keep
        # grayscale. (Mode 4 is 1-bit — it dithers text and grays into
        # washed-out speckle.)
        try:
            self.lcd.setEpdMode(1)
        except Exception:
            pass
        self.lcd.fillScreen(self.WHITE)
        try:
            self.lcd.setEpdMode(3)
        except Exception:
            pass

    def ink(self, shade):
        self._ink = self.SHADES.get(shade, self.BLACK)
        self.lcd.setTextColor(self._ink, self.WHITE)

    def _set_font(self, size):
        for pt in (72, 56, 40, 24, 18):
            if size >= pt or pt == 18:
                self.lcd.setFont(self._fonts[pt])
                return

    def text(self, x, y, s, size):
        self._set_font(size)
        self.lcd.drawString(s, x, y)

    def text3d(self, x, y, s, size, depth=3):
        """Blocky drop-shadow lettering: gray shadow, black face."""
        self._set_font(size)
        keep = self._ink
        self.lcd.setTextColor(self.SHADES["light"], self.WHITE)
        for d in range(depth, 0, -1):
            self.lcd.drawString(s, x + d, y + d)
        self.lcd.setTextColor(self.BLACK, self.WHITE)
        self.lcd.drawString(s, x, y)
        self.lcd.setTextColor(keep, self.WHITE)

    def text_width(self, s, size):
        self._set_font(size)
        try:
            return self.lcd.textWidth(s)
        except AttributeError:
            return int(len(s) * size * 0.6)

    def line(self, x0, y0, x1, y1):
        self.lcd.drawLine(x0, y0, x1, y1, self._ink)

    def circle(self, x, y, r):
        self.lcd.drawCircle(x, y, r, self._ink)

    def fill_circle(self, x, y, r):
        self.lcd.fillCircle(x, y, r, self._ink)

    def fill_circle_white(self, x, y, r):
        self.lcd.fillCircle(x, y, r, self.WHITE)

    def rect_white(self, x, y, w, h):
        self.lcd.fillRect(x, y, w, h, self.WHITE)

    def arc(self, x, y, r, a0, a1):
        """Arc band ~3px thick. Present only when the binding has
        drawArc — artwork falls back to segments otherwise."""
        self.lcd.drawArc(x, y, r + 1, r - 1, a0, a1, self._ink)

    def anim_mode(self, on):
        # Fastest (binary) partial updates during motion; the glyphs
        # are pure black line art so nothing is lost.
        try:
            self.lcd.setEpdMode(4 if on else 1)
        except Exception:
            pass

    def show(self):
        # Draws already reached the panel (no display() in this
        # binding); just restore quality mode for whoever draws next.
        try:
            self.lcd.setEpdMode(1)
        except Exception:
            pass


class M5PaperCanvas:
    """Legacy UIFlow 1.x (MicroPython) backend for M5Paper v1.1."""

    def __init__(self):
        from m5stack import lcd  # noqa: UIFlow M5Paper firmware
        self.lcd = lcd
        lcd.clear(lcd.WHITE)

    def ink(self, shade):
        pass  # legacy backend draws everything in black

    def text3d(self, x, y, s, size, depth=3):
        self.text(x, y, s, size)

    def rect_white(self, x, y, w, h):
        pass

    def anim_mode(self, on):
        pass

    def text(self, x, y, s, size):
        # UIFlow bundles DejaVu fonts at fixed sizes; pick nearest.
        lcd = self.lcd
        if size >= 72:
            lcd.font(lcd.FONT_DejaVu72)
        elif size >= 40:
            lcd.font(lcd.FONT_DejaVu40)
        elif size >= 24:
            lcd.font(lcd.FONT_DejaVu24)
        else:
            lcd.font(lcd.FONT_DejaVu18)
        lcd.print(s, x, y, lcd.BLACK)

    def text_width(self, s, size):
        # DejaVu is roughly 0.6em average advance.
        return int(len(s) * size * 0.6)

    def line(self, x0, y0, x1, y1):
        self.lcd.line(x0, y0, x1, y1, self.lcd.BLACK)

    def circle(self, x, y, r):
        self.lcd.circle(x, y, r, self.lcd.BLACK)

    def fill_circle(self, x, y, r):
        self.lcd.circle(x, y, r, self.lcd.BLACK, self.lcd.BLACK)

    def fill_circle_white(self, x, y, r):
        self.lcd.circle(x, y, r, self.lcd.WHITE, self.lcd.WHITE)

    def show(self):
        pass  # UIFlow lcd draws straight to the panel


class TextCanvas:
    """Desktop simulation: renders an ASCII mockup to stdout."""

    def __init__(self):
        self.lines = []

    def ink(self, shade):
        pass

    def text(self, x, y, s, size):
        self.lines.append((y, x, s, size))

    def text3d(self, x, y, s, size, depth=3):
        self.text(x, y, s, size)

    def rect_white(self, *a):
        pass

    def anim_mode(self, on):
        pass

    def text_width(self, s, size):
        return int(len(s) * size * 0.6)

    def line(self, *a):
        pass

    def circle(self, *a):
        pass

    def fill_circle(self, *a):
        pass

    def fill_circle_white(self, *a):
        pass

    def show(self):
        cols = 44
        print("+" + "-" * cols + "+")
        for y, x, s, size in sorted(self.lines):
            frac = (x + self.text_width(s, size) / 2) / W  # center of text
            pad = int(frac * cols - len(s) / 2)
            pad = max(0, min(cols - len(s), pad))
            marker = "#" if size >= 60 else " "
            print("|" + " " * pad + s + " " * (cols - pad - len(s)) + "|",
                  marker if size >= 60 else "")
        print("+" + "-" * cols + "+")


def make_canvas():
    try:
        return UIFlow2Canvas()
    except ImportError:
        pass
    try:
        return M5PaperCanvas()
    except ImportError:
        return TextCanvas()


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

def _center(cv, y, s, size):
    x = (W - cv.text_width(s, size)) // 2
    cv.text(max(0, x), y, s, size)


def _center3d(cv, y, s, size, depth=3):
    x = (W - cv.text_width(s, size)) // 2
    cv.text3d(max(0, x), y, s, size, depth)


def _wrap(text, max_chars):
    """Greedy word wrap."""
    lines, cur = [], ""
    for word in text.split():
        candidate = (cur + " " + word).strip()
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


GLYPH = (W // 2, 165, 120)      # medallion center — shared with animation


def _is_night(ctx):
    return (ctx["now_minutes"] > ctx["sunset_minutes"]
            or ctx["now_minutes"] < 5 * 60)


MEDALLION_R = 80


def _ring(cv):
    cv.ink("light")
    cv.circle(GLYPH[0], GLYPH[1], MEDALLION_R)
    cv.circle(GLYPH[0], GLYPH[1], MEDALLION_R - 1)
    cv.ink("black")


def animate_glyph(cv, ctx, seconds):
    """Post-render glyph motion (device only). Safe no-op for calm
    conditions and for canvases without animation support."""
    if ctx.get("is_night_watch"):
        return
    try:
        cv.anim_mode(True)
        artwork.animate(cv, ctx["condition"], GLYPH[0], GLYPH[1],
                        GLYPH[2], _is_night(ctx), seconds,
                        after_frame=_ring)
    finally:
        cv.anim_mode(False)


def _headline(cv, text):
    """Fit the headline, biggest first: one line at the largest size
    that fits, else two balanced 40pt lines, else 24pt."""
    max_w = W - 28
    for size in (S(40), 40):
        if cv.text_width(text, size) <= max_w:
            _center3d(cv, 296 - (size - 40) // 2, text, size, depth=3)
            return
    words = text.split()
    best = None
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        wid = max(cv.text_width(l1, 40), cv.text_width(l2, 40))
        if best is None or wid < best[0]:
            best = (wid, l1, l2)
    if best and best[0] <= max_w:
        _center3d(cv, 260, best[1], 40, depth=3)
        _center3d(cv, 310, best[2], 40, depth=3)
    else:
        _center3d(cv, 304, text, 24, depth=2)


def _sun_arc(cv, ctx):
    """Dotted horizon arc with the sun at its real position along the
    day. At night the arc rests empty and the moon phase takes over."""
    import math

    big = S(18) != 18
    cx, cy, r = W // 2, 916 if big else 912, 64 if big else 84
    is_day = ctx["sunrise_minutes"] <= ctx["now_minutes"] \
        <= ctx["sunset_minutes"]

    # dotted arc
    cv.ink("light")
    for i in range(25):
        a = math.pi * i / 24.0
        cv.fill_circle(int(cx + r * math.cos(a)),
                       int(cy - r * math.sin(a)), 2)
    # horizon line
    cv.line(cx - r - 46, cy, cx - r - 6, cy)
    cv.line(cx + r + 6, cy, cx + r + 46, cy)

    if is_day:
        span = max(1, ctx["sunset_minutes"] - ctx["sunrise_minutes"])
        p = (ctx["now_minutes"] - ctx["sunrise_minutes"]) / span
        a = math.pi * (1.0 - p)
        sx = int(cx + r * math.cos(a))
        sy = int(cy - r * math.sin(a))
        cv.ink("black")
        cv.fill_circle(sx, sy, 8)
    else:
        cv.ink("gray")
        _center(cv, cy - 52, ctx["moon_name"].upper(), S(18))

    # times anchored to the arc's feet (fixed margins when big)
    cv.ink("gray")
    lx = 60 if big else cx - r - 46
    cv.text(lx, cy + 14, ctx["sunrise"], S(18))
    sw = cv.text_width(ctx["sunset"], S(18))
    # keep clear of the "upd" stamp in the bottom-right corner
    rmargin = 150 if getattr(config, "SHOW_LAST_UPDATED", False) else 60
    rx = (W - rmargin - sw) if big else (cx + r + 46 - sw)
    cv.text(rx, cy + 14, ctx["sunset"], S(18))


def render(cv, ctx, headline_text, activities, wonder_text):
    """V2 layout: facts first, wonder second, lots of air.

    Grayscale hierarchy: black for what matters (headline, wonder,
    suggestions), soft gray for context (date, temp, times). No score
    — every day has a reason to be beautiful.
    """
    is_night = _is_night(ctx)

    # --- Date ---------------------------------------------------------
    date_str = "%s, %s %d" % (ctx["weekday_name"], ctx["month_name"],
                              ctx["day"])
    cv.ink("gray")
    _center(cv, 40, date_str.upper(), S(18))

    # --- Medallion: the moon at night, the weather by day ----------------
    # (No score: every day has a reason to be beautiful.)
    night_watch = ctx.get("is_night_watch")
    mx, my, mr = W // 2, 165, 80
    cv.ink("light")
    cv.circle(mx, my, mr)
    cv.circle(mx, my, mr - 1)
    cv.ink("black")
    if night_watch:
        artwork.moon(cv, mx, my, 120)
    else:
        artwork.draw(cv, ctx["condition"], GLYPH[0], GLYPH[1], GLYPH[2],
                     is_night)

    # --- Headline ---------------------------------------------------------
    cv.ink("black")
    _headline(cv, headline_text)

    # --- Temperature, and how today compares to yesterday ----------------
    cv.ink("gray")
    _center(cv, 396, "%d\xb0" % round(ctx["temp"]), S(24))
    delta = ctx.get("temp_delta")
    if delta is not None and abs(delta) >= 4:
        note = "%d\xb0 %s than yesterday" % (
            abs(int(round(delta))),
            "warmer" if delta > 0 else "cooler")
        cv.ink("light")
        _center(cv, 396 + S(24) + 10, note, 18)

    # --- The Wonder: today's one sentence worth reading ------------------
    cv.ink("light")
    cv.line(W // 3, 475, 2 * W // 3, 475)
    cv.ink("black")
    wsize = S(24)
    max_chars = int(470 / (wsize * 0.6))
    lines = _wrap(wonder_text, max_chars)
    if len(lines) > 2 and wsize > 24:
        wsize = 24                      # long wonder: big doesn't fit
        lines = _wrap(wonder_text, 32)
    y = 500
    for line in lines:
        _center(cv, y, line, wsize)
        y += wsize + 14
    cv.ink("light")
    cv.line(W // 3, y + 8, 2 * W // 3, y + 8)

    # --- Gentle suggestions, dotted -------------------------------------
    asize = S(24)
    y = max(620, y + 18)
    if y > 740:
        asize = 24                      # crowded screen: keep them small
    step = asize + (24 if asize == 24 else 8)
    for act in activities:
        tw = cv.text_width(act, asize)
        x0 = (W - (tw + 22)) // 2
        cv.ink("black")
        cv.fill_circle(x0 + 4, y + int(asize * 0.55), 4)
        cv.text(x0 + 22, y, act, asize)
        y += step

    # --- Sun arc horizon --------------------------------------------------
    _sun_arc(cv, ctx)

    # --- Prototyping: when this frame was rendered ------------------------
    _upd_stamp(cv, ctx)

    cv.show()


def _upd_stamp(cv, ctx):
    if getattr(config, "SHOW_LAST_UPDATED", False) and "time_str" in ctx:
        cv.ink("light")
        stamp = "upd %s" % ctx["time_str"]
        cv.text(W - 12 - cv.text_width(stamp, 18), 934, stamp, 18)


_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _day_of_year(ctx):
    leap = ctx["year"] % 4 == 0 and (ctx["year"] % 100 != 0
                                     or ctx["year"] % 400 == 0)
    doy = sum(_DAYS_IN_MONTH[:ctx["month"] - 1]) + ctx["day"]
    if leap and ctx["month"] > 2:
        doy += 1
    return doy, 366 if leap else 365


def render_facts(cv, ctx):
    """The flashcard's back side: today, in plain facts. Shown when
    the side button (not the RTC) woke the device; flips back to the
    adventure side after a minute."""

    cv.ink("gray")
    _center(cv, 45, "TODAY, IN DETAIL", S(18))
    cv.ink("black")
    date_str = "%s, %s %d" % (ctx["weekday_name"], ctx["month_name"],
                              ctx["day"])
    _center(cv, 90, date_str, S(24))
    cv.ink("light")
    cv.line(W // 4, 148, 3 * W // 4, 148)

    daylight = ctx["sunset_minutes"] - ctx["sunrise_minutes"]
    tom = ctx.get("tomorrow")
    rows = [
        ("Temperature", "%d\xb0 (feels %d\xb0)"
            % (round(ctx["temp"]), round(ctx["feels_like"]))),
        ("High / Low", "%d\xb0 / %d\xb0"
            % (round(ctx["high"]), round(ctx["low"]))),
        ("Sky", ctx["condition"]),
        ("Cloud cover", "%d%%" % ctx["cloud_cover"]),
        ("Rain chance", "%d%%" % ctx["rain_prob"]),
        ("Humidity", "%d%%" % ctx["humidity"]),
        ("Wind", "%d mph" % round(ctx["wind"])),
        ("Sunrise", ctx["sunrise"]),
        ("Sunset", ctx["sunset"]),
        ("Daylight", "%dh %02dm" % (daylight // 60, daylight % 60)),
        ("Moon", ctx["moon_name"]),
    ]
    if tom:
        rows.append(("Tomorrow", "%d\xb0/%d\xb0, %d%% rain"
                     % (round(tom["high"]), round(tom["low"]),
                        tom["rain_prob"])))
    # (rows stay 24pt even in BIG_TEXT — 40pt values collide with
    # their labels, and this card is meant to be read up close)
    y = 185
    for label, value in rows:
        cv.ink("gray")
        cv.text(70, y + 5, label.upper(), 18)
        cv.ink("black")
        vw = cv.text_width(value, 24)
        cv.text(W - 70 - vw, y, value, 24)
        y += 52

    doy, total = _day_of_year(ctx)
    cv.ink("gray")
    _center(cv, y + 20, "Day %d of %d" % (doy, total), 18)
    cv.ink("light")
    _center(cv, 912, "BACK TO THE ADVENTURE IN A MINUTE", 18)
    _upd_stamp(cv, ctx)

    cv.show()


