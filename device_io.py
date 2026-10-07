"""M5Paper input sampling (device only; desktop imports are harmless).

A periodic machine.Timer samples the side button, the rocker and the
GT911 touch panel into a bounded queue. The main loop drains it.
Sampling is therefore independent of how long the loop spends
composing or pushing a frame: pen points and button edges keep being
recorded while Python code runs.

Hardware limits (see docs/INTERACTIVE_MODULES.md):
- ESP32 MicroPython timer callbacks are *soft*: they run between
  Python bytecodes. While a single long C call blocks (an e-ink push,
  a socket read), samples pause and resume afterwards. Strokes are not
  dropped by the redraw itself, but a contact made AND lifted entirely
  inside one blocking call can be missed. Needs measurement on the
  panel.
- Pins (M5Stack M5Paper v1.1 pin map): G38 wheel push (also the
  power-on button), G37 / G39 wheel rocked right / left, G36 touch
  interrupt, touch on I2C G21/G22. Rocker direction is configurable.
"""

import time

import config
import input_events as ie

SIDE_PIN = 38
MAX_QUEUE = 512
SAMPLE_MS = 15


class Sampler:
    def __init__(self, hold_ms=None):
        from machine import Pin
        hold_ms = ie.clamp_hold_ms(
            hold_ms if hold_ms is not None else getattr(config, "HOME_HOLD_MS", ie.DEFAULT_HOLD_MS))
        self.side = Pin(SIDE_PIN, Pin.IN)
        self.next_pin = Pin(getattr(config, "ROCKER_NEXT_PIN", 37), Pin.IN)
        self.back_pin = Pin(getattr(config, "ROCKER_BACK_PIN", 39), Pin.IN)
        self.side_tracker = ie.ButtonTracker(hold_ms)        # disarmed until released
        self.next_tracker = ie.ButtonTracker(5000)
        self.back_tracker = ie.ButtonTracker(5000)
        self.touch = ie.TouchTracker()
        self.queue = []
        self.dropped = 0
        self._ms = 0
        self._tick = time.ticks_ms()
        self._timer = None
        self._busy = False
        import M5
        self._m5 = M5

    def now_ms(self):
        t = time.ticks_ms()
        self._ms += time.ticks_diff(t, self._tick)
        self._tick = t
        return self._ms

    def _push(self, event):
        if len(self.queue) >= MAX_QUEUE:
            self.dropped += 1
            return
        self.queue.append(event)

    def _touch_point(self):
        try:
            self._m5.update()
            if self._m5.Touch.getCount() <= 0:
                return None
            x, y = self._m5.Touch.getX(), self._m5.Touch.getY()
        except Exception:
            return None
        if getattr(config, "TOUCH_SWAP_XY", False):
            x, y = y, x
        if getattr(config, "TOUCH_FLIP_X", False):
            x = 539 - x
        if getattr(config, "TOUCH_FLIP_Y", False):
            y = 959 - y
        return (x, y)

    def sample(self, _timer=None):
        if self._busy:
            return
        self._busy = True
        try:
            now = self.now_ms()
            for e in self.side_tracker.feed(self.side.value() == 0, now):
                self._push(("button", e, now))
            for e in self.next_tracker.feed(self.next_pin.value() == 0, now):
                if e == ie.PRESS:
                    self._push(("rocker", 1, now))
            for e in self.back_tracker.feed(self.back_pin.value() == 0, now):
                if e == ie.PRESS:
                    self._push(("rocker", -1, now))
            for e in self.touch.feed(self._touch_point(), now):
                self._push(("touch", e, now))
        finally:
            self._busy = False

    def start(self):
        try:
            from machine import Timer
            self._timer = Timer(0)
            self._timer.init(period=SAMPLE_MS, mode=Timer.PERIODIC,
                             callback=self.sample)
        except Exception:
            self._timer = None          # fall back to polling from drain()

    def stop(self):
        if self._timer is not None:
            try:
                self._timer.deinit()
            except Exception:
                pass
            self._timer = None

    def drain(self):
        if self._timer is None:
            self.sample()
        events, self.queue = self.queue, []
        return events

    def side_is_down(self):
        return self.side.value() == 0
