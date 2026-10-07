"""Side-button press/hold separation and touch classification."""
import unittest

import input_events as ie


def run(tracker, timeline, step=5):
    """timeline: [(pressed, duration_ms)] -> [(event, t)]"""
    out, t = [], 0
    for pressed, dur in timeline:
        end = t + dur
        while t < end:
            out += [(e, t) for e in tracker.feed(pressed, t)]
            t += step
    return out


class TestButton(unittest.TestCase):
    def armed(self, hold=1000):
        b = ie.ButtonTracker(hold)
        b.feed(False, 0)
        return b

    def test_short_press_is_press_only(self):
        events = run(self.armed(), [(False, 50), (True, 300), (False, 100)])
        self.assertEqual([e for e, _ in events], [ie.PRESS])

    def test_hold_fires_once_at_threshold_and_never_presses(self):
        events = run(self.armed(), [(False, 50), (True, 3000), (False, 100)])
        self.assertEqual([e for e, _ in events], [ie.HOLD])
        t = events[0][1]
        # pressed at 50, debounce accepted later but dated from the edge
        self.assertGreaterEqual(t - 50, 1000)
        self.assertLess(t - 50, 1000 + 10)

    def test_release_just_before_threshold_is_press(self):
        events = run(self.armed(), [(False, 50), (True, 990), (False, 100)])
        self.assertEqual([e for e, _ in events], [ie.PRESS])

    def test_wake_press_still_held_at_boot_is_ignored(self):
        b = ie.ButtonTracker(1000)            # disarmed: first sample is "held"
        events = run(b, [(True, 2500), (False, 100)])
        self.assertEqual(events, [])
        # ...and the next real gesture works normally
        events = run(b, [(True, 1200), (False, 100)])
        self.assertEqual([e for e, _ in events], [ie.HOLD])

    def test_bounce_is_filtered(self):
        events = run(self.armed(), [(False, 50), (True, 10), (False, 10),
                                    (True, 10), (False, 200)])
        self.assertEqual(events, [])

    def test_threshold_is_configurable_and_clamped(self):
        for hold in (600, 1500):
            events = run(self.armed(hold), [(False, 20), (True, hold - 60), (False, 60)])
            self.assertEqual([e for e, _ in events], [ie.PRESS], hold)
            events = run(self.armed(hold), [(False, 20), (True, hold + 60), (False, 60)])
            self.assertEqual([e for e, _ in events], [ie.HOLD], hold)
        self.assertEqual(ie.clamp_hold_ms(5000), ie.HOLD_MAX_MS)
        self.assertLess(ie.HOLD_MAX_MS, 2000)  # below the power-on press
        self.assertEqual(ie.clamp_hold_ms(50), ie.HOLD_MIN_MS)
        self.assertEqual(ie.clamp_hold_ms("x"), ie.DEFAULT_HOLD_MS)

    def test_config_default_is_valid(self):
        import config
        self.assertEqual(ie.clamp_hold_ms(config.HOME_HOLD_MS), config.HOME_HOLD_MS)


class TestTouch(unittest.TestCase):
    def feed(self, samples):
        t = ie.TouchTracker()
        out = []
        for i, p in enumerate(samples):
            out += t.feed(p, i * 15)
        return out

    def test_tap(self):
        ev = self.feed([(100, 100), (102, 101), None])
        self.assertEqual([e[0] for e in ev], [ie.TAP])

    def test_stroke_keeps_every_point_in_order(self):
        pts = [(100, 100), (104, 104), (108, 108), (130, 130), (160, 160)]
        ev = self.feed(pts + [None])
        self.assertEqual(ev[0][0], ie.STROKE_START)
        self.assertEqual(ev[-1][0], ie.STROKE_END)
        got = [(e[1], e[2]) for e in ev if e[0] in (ie.STROKE_START, ie.STROKE_POINT)]
        self.assertEqual(got, pts)

    def test_long_stationary_contact_is_a_dot_stroke(self):
        ev = self.feed([(50, 50)] * 40 + [None])
        self.assertEqual([e[0] for e in ev], [ie.STROKE_START, ie.STROKE_END])


if __name__ == "__main__":
    unittest.main()
