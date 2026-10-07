"""Pure input state machines: side button and touch. No hardware here.

The device sampler (device_io.py) feeds raw levels with a monotonic
millisecond clock; these classes turn them into the few events the
app understands. Everything is deterministic so desktop tests can
replay exact timings.

Side button (G38, the wheel push). On the M5Paper this is ALSO the
power-on button: with the board fully off, pressing it closes the
power path long enough (~2 s per M5Stack's docs) for the ESP32 to boot
and latch G2. While the firmware runs, G2 is held high, so a press or
hold no longer changes power; it is just a GPIO. Two consequences:

- The press that wakes the board from deep sleep (ext0) is often still
  held when Python starts. The tracker is DISARMED until it has seen
  the button released, so that wake press never counts as a hold.
- The Home hold threshold should stay clearly below the ~2 s power-on
  gesture so the two are not confused. config.HOME_HOLD_MS is clamped
  to HOLD_MIN_MS..HOLD_MAX_MS.
"""

PRESS = "press"         # short press, reported on release
HOLD = "hold"           # reported once, the moment the threshold is reached
TAP = "tap"
STROKE_START = "stroke_start"
STROKE_POINT = "stroke_point"
STROKE_END = "stroke_end"

HOLD_MIN_MS = 400
HOLD_MAX_MS = 1900
DEFAULT_HOLD_MS = 1000


def clamp_hold_ms(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return DEFAULT_HOLD_MS
    return max(HOLD_MIN_MS, min(HOLD_MAX_MS, value))


class ButtonTracker:
    """Debounced press/hold separation for one active-low button.

    feed(pressed, now_ms) returns a list of events. A hold fires as
    soon as the threshold is crossed (the user gets feedback without
    letting go) and suppresses the short press on release.
    """

    def __init__(self, hold_ms=DEFAULT_HOLD_MS, debounce_ms=30,
                 armed=False):
        self.hold_ms = clamp_hold_ms(hold_ms)
        self.debounce_ms = debounce_ms
        self.armed = armed           # False until a release is observed
        self._stable = None          # debounced level
        self._candidate = None
        self._candidate_since = 0
        self._down_at = None
        self._held = False

    def feed(self, pressed, now_ms):
        pressed = bool(pressed)
        if pressed != self._candidate:
            self._candidate = pressed
            self._candidate_since = now_ms
        events = []
        if self._stable is None:
            # First sample: accept immediately; a held level stays disarmed.
            self._stable = pressed
            if not pressed:
                self.armed = True
            elif self.armed:
                self._down_at = now_ms
            return events
        if pressed != self._stable and \
                now_ms - self._candidate_since >= self.debounce_ms:
            self._stable = pressed
            if pressed:
                if self.armed:
                    # Debounce delays acceptance; date the press from the edge.
                    self._down_at = self._candidate_since
                    self._held = False
            else:
                if self.armed and self._down_at is not None \
                        and not self._held:
                    events.append(PRESS)
                self.armed = True
                self._down_at = None
                self._held = False
        # A release still settling (candidate up) is not a hold: the
        # user let go before the threshold, debounce merely lags.
        if self._stable and self._candidate and self._down_at is not None \
                and not self._held and now_ms - self._down_at >= self.hold_ms:
            self._held = True
            events.append(HOLD)
        return events

    @property
    def is_down(self):
        return bool(self._stable)


class TouchTracker:
    """Single-finger touch -> taps and strokes.

    feed(point_or_None, now_ms). A contact that ends quickly without
    moving is a TAP; anything else is a stroke. Stroke points are
    emitted as they arrive (not at lift-off), so a slow redraw never
    holds the only copy of the ink.
    """

    def __init__(self, tap_ms=350, tap_px=14):
        self.tap_ms = tap_ms
        self.tap_px = tap_px
        self._down = None            # (x, y, t)
        self._moved = False
        self._stroking = False
        self._last = None
        self._pending = []           # points seen before tap/stroke is known

    def feed(self, point, now_ms):
        events = []
        if point is not None:
            x, y = int(point[0]), int(point[1])
            if self._down is None:
                self._down = (x, y, now_ms)
                self._moved = False
                self._stroking = False
                self._last = (x, y)
                self._pending = []
                return events
            if not self._stroking and (x, y) != self._last:
                self._pending.append((x, y, now_ms))
            if not self._moved and (abs(x - self._down[0]) > self.tap_px
                                    or abs(y - self._down[1]) > self.tap_px
                                    or now_ms - self._down[2] > self.tap_ms):
                self._moved = True
                self._stroking = True
                events.append((STROKE_START, self._down[0], self._down[1],
                               self._down[2]))
                # Nothing seen before the stroke was recognized is lost.
                for px, py, pt in self._pending:
                    events.append((STROKE_POINT, px, py, pt))
                self._pending = []
            elif self._stroking and (x, y) != self._last:
                events.append((STROKE_POINT, x, y, now_ms))
            self._last = (x, y)
            return events
        if self._down is not None:
            if self._stroking:
                events.append((STROKE_END, self._last[0], self._last[1],
                               now_ms))
            else:
                events.append((TAP, self._down[0], self._down[1], now_ms))
            self._down = None
            self._stroking = False
        return events
