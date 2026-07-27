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

W, H = 540, 960


# --------------------------------------------------------------------------
# Canvas backends
# --------------------------------------------------------------------------

class UIFlow2Canvas:
    """UIFlow2.0 (MicroPython, M5GFX) backend for M5Paper v1.1."""

    BLACK = 0x000000
    WHITE = 0xFFFFFF

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
        self.lcd.setTextColor(self.BLACK, self.WHITE)
        self.lcd.fillScreen(self.WHITE)

    def _set_font(self, size):
        for pt in (72, 56, 40, 24, 18):
            if size >= pt or pt == 18:
                self.lcd.setFont(self._fonts[pt])
                return

    def text(self, x, y, s, size):
        self._set_font(size)
        self.lcd.drawString(s, x, y)

    def text_width(self, s, size):
        self._set_font(size)
        try:
            return self.lcd.textWidth(s)
        except AttributeError:
            return int(len(s) * size * 0.6)

    def line(self, x0, y0, x1, y1):
        self.lcd.drawLine(x0, y0, x1, y1, self.BLACK)

    def circle(self, x, y, r):
        self.lcd.drawCircle(x, y, r, self.BLACK)

    def fill_circle(self, x, y, r):
        self.lcd.fillCircle(x, y, r, self.BLACK)

    def fill_circle_white(self, x, y, r):
        self.lcd.fillCircle(x, y, r, self.WHITE)

    def show(self):
        # On e-paper, M5GFX buffers draws until an explicit push.
        for method in ("display", "update"):
            fn = getattr(self.lcd, method, None)
            if fn:
                try:
                    fn()
                except TypeError:
                    pass
                return


class M5PaperCanvas:
    """Legacy UIFlow 1.x (MicroPython) backend for M5Paper v1.1."""

    def __init__(self):
        from m5stack import lcd  # noqa: UIFlow M5Paper firmware
        self.lcd = lcd
        lcd.clear(lcd.WHITE)

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

    def text(self, x, y, s, size):
        self.lines.append((y, x, s, size))

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


def render(cv, ctx, score, headline_text, activities, wonder_text):
    """V2 layout: facts first, wonder second, lots of air.

    One centered column, five moments top to bottom:
      date -> score+headline -> weather glyph -> THE WONDER -> gentle
      suggestions -> one sun fact.
    """
    is_night = (ctx["now_minutes"] > ctx["sunset_minutes"]
                or ctx["now_minutes"] < 5 * 60)

    # --- Date ---------------------------------------------------------
    date_str = "%s, %s %d" % (ctx["weekday_name"], ctx["month_name"],
                              ctx["day"])
    _center(cv, 45, date_str.upper(), 18)

    # --- Score + headline ----------------------------------------------
    _center(cv, 115, "%d/100" % score, 72)
    _center(cv, 230, headline_text, 40)

    # --- Weather glyph, temp as quiet context ---------------------------
    artwork.draw(cv, ctx["condition"], W // 2, 380, 140, is_night)
    _center(cv, 470, "%d\xb0" % round(ctx["temp"]), 24)

    # --- The Wonder: today's one sentence worth reading ------------------
    cv.line(W // 3, 545, 2 * W // 3, 545)
    y = 585
    for line in _wrap(wonder_text, 32):
        _center(cv, y, line, 24)
        y += 40
    cv.line(W // 3, y + 12, 2 * W // 3, y + 12)

    # --- Gentle suggestions ----------------------------------------------
    y = 725
    for act in activities:
        _center(cv, y, act, 24)
        y += 52

    # --- One sun fact: the next one that matters --------------------------
    if ctx["now_minutes"] < ctx["sunset_minutes"]:
        sun_fact = "sunset %s" % ctx["sunset"]
    else:
        sun_fact = "sunrise %s" % ctx["sunrise"]
    _center(cv, 910, sun_fact.upper(), 18)

    cv.show()


