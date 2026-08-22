"""Desktop unit tests for the pure logic.

These cover exactly what a month of debugging taught us to distrust:
time math, day/night gating, deduplication, and the fingerprint.

Run from the repo root:  python -m unittest discover tests -v
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main
import recommendation_engine as rec
import scheduler
import scoring_engine
import weather_service as ws
import wonder_engine


def ctx(**over):
    c = main.demo_context()
    c["score"] = 80
    c.update(over)
    return c


class TestQuietHours(unittest.TestCase):
    def test_window_wraps_midnight(self):
        for h in (23, 0, 1, 2, 3, 4):
            self.assertTrue(main.is_quiet_hour(h), h)
        for h in (5, 6, 12, 19, 22):
            self.assertFalse(main.is_quiet_hour(h), h)

    def test_unknown_clock_is_not_quiet(self):
        # An unset clock must never strand the device dark all night.
        self.assertFalse(main.is_quiet_hour(None))


class TestNightEventMath(unittest.TestCase):
    def test_sleeps_land_on_event_hours(self):
        events = set(config.NIGHT_WAKE_HOURS) | {config.QUIET_END}
        with mock.patch("time.localtime",
                        return_value=(2026, 8, 22, 0, 0, 0, 5, 234)):
            for h in (23, 0, 1, 2, 3, 4):
                secs = main._seconds_to_next_night_event(h)
                target = (h + secs // 3600) % 24
                self.assertIn(target, events, "from hour %d" % h)
                self.assertLessEqual(secs, 4 * 3600)
                self.assertGreaterEqual(secs, 600)


class TestSchedulerRollover(unittest.TestCase):
    def test_undershoot_rolls_to_next_hour(self):
        # 40s before the hour: this wake already did the hour's work.
        with mock.patch("time.time", return_value=3600 * 100 - 40):
            secs = scheduler.seconds_until_next_update()
        self.assertGreater(secs, 3000)

    def test_normal_wake_targets_top_of_hour(self):
        with mock.patch("time.time", return_value=3600 * 100 + 300):
            secs = scheduler.seconds_until_next_update()
        self.assertEqual(secs, 3300)


class TestFingerprint(unittest.TestCase):
    def test_stable_for_identical_content(self):
        a = main._fingerprint(ctx(), "H", ["a"], "w")
        b = main._fingerprint(ctx(), "H", ["a"], "w")
        self.assertEqual(a, b)

    def test_small_temp_drift_ignored_big_change_not(self):
        # buckets are round(temp/3): 69.0 and 69.9 share bucket 23
        base = main._fingerprint(ctx(temp=69.0), "H", ["a"], "w")
        self.assertEqual(base, main._fingerprint(ctx(temp=69.9), "H", ["a"], "w"))
        self.assertNotEqual(base, main._fingerprint(ctx(temp=76.0), "H", ["a"], "w"))

    def test_after_midnight_counts_as_night(self):
        night = main._fingerprint(ctx(now_minutes=60), "H", ["a"], "w")
        day = main._fingerprint(ctx(now_minutes=600), "H", ["a"], "w")
        self.assertIn("night", night.split("|"))
        self.assertIn("day", day.split("|"))


class TestWonderEngine(unittest.TestCase):
    def _pool(self, night):
        msgs = set()
        for w in wonder_engine.WONDERS:
            if w.night == night:
                msgs.update(w.messages)
        return msgs

    def test_night_watch_only_speaks_night(self):
        c = ctx(is_night_watch=True, hour=1, now_minutes=60)
        self.assertIn(wonder_engine.wonder(c), self._pool(night=True))

    def test_day_never_speaks_night(self):
        for cond in ("clear", "rain", "snow", "cloudy"):
            c = ctx(condition=cond)
            self.assertIn(wonder_engine.wonder(c), self._pool(night=False))

    def test_deterministic_within_a_day(self):
        c = ctx()
        self.assertEqual(wonder_engine.wonder(c), wonder_engine.wonder(c))

    def test_night_wakes_vary_by_hour(self):
        seeds = {wonder_engine._day_seed(ctx(is_night_watch=True, hour=h))
                 for h in (23, 1, 3)}
        self.assertEqual(len(seeds), 3)


class TestRecommendations(unittest.TestCase):
    def test_same_concept_stems(self):
        sc = rec._same_concept
        tok = rec._tokens
        self.assertTrue(sc(tok("Take A Short Walk"), tok("GREAT DAY FOR A WALK")))
        self.assertTrue(sc(tok("Read A Book"), tok("PERFECT READING WEATHER")))
        self.assertTrue(sc(tok("Stargazing Tonight"), tok("The stars will be out.")))
        self.assertFalse(sc(tok("Hot Chocolate"), tok("GREAT DAY FOR A WALK")))

    def test_avoid_filters_repeats(self):
        c = ctx(hour=10, now_minutes=600)
        acts = rec.recommend(c, avoid="GREAT DAY FOR A WALK")
        joined = " ".join(acts).lower()
        self.assertNotIn("walk", joined)
        self.assertEqual(len(acts), rec.MAX_ACTIVITIES)

    def test_hour_window_wraps_midnight(self):
        r = rec.Rule("x", when=lambda c: True, gives=["y"], hours=(22, 5))
        self.assertTrue(r.active(ctx(hour=23)))
        self.assertTrue(r.active(ctx(hour=2)))
        self.assertFalse(r.active(ctx(hour=12)))

    def test_night_watch_gets_night_suggestions(self):
        c = ctx(is_night_watch=True, hour=1)
        self.assertIn("Back To Bed", rec.recommend(c))


class TestScoringHeadline(unittest.TestCase):
    def test_score_bounds(self):
        for over in ({}, {"feels_like": -10.0, "wind": 40.0, "rain_prob": 100,
                          "condition": "storm", "cloud_cover": 100}):
            s = scoring_engine.score_day(ctx(**over))
            self.assertTrue(1 <= s <= 100, s)

    def test_night_watch_headline(self):
        c = ctx(is_night_watch=True)
        self.assertEqual(scoring_engine.headline(c, 90), "WHILE THE WORLD SLEEPS")

    def test_every_ctx_gets_a_headline(self):
        self.assertTrue(scoring_engine.headline(ctx(), 10))


class TestWeatherService(unittest.TestCase):
    def test_condition_buckets(self):
        self.assertEqual(ws._condition_from_code(0), "clear")
        self.assertEqual(ws._condition_from_code(63), "rain")
        self.assertEqual(ws._condition_from_code(75), "snow")
        self.assertEqual(ws._condition_from_code(95), "storm")
        self.assertEqual(ws._condition_from_code(999), "cloudy")  # unknown

    def test_time_formatting(self):
        self.assertEqual(ws._fmt_12h(0, 5), "12:05 AM")
        self.assertEqual(ws._fmt_12h(12, 0), "12:00 PM")
        self.assertEqual(ws._fmt_12h(20, 30), "8:30 PM")

    def test_days_between_handles_month_boundary(self):
        self.assertEqual(ws._days_between("2026-07-31", "2026-08-01"), 1)
        self.assertEqual(ws._days_between("2026-12-31", "2027-01-01"), 1)
        self.assertEqual(ws._days_between("garbage", "2026-08-01"), -1)

    def test_moon_phase_in_range(self):
        for d in (1, 10, 20, 28):
            p = ws.moon_phase(2026, 8, d)
            self.assertTrue(0.0 <= p < 1.0)


class TestBattery(unittest.TestCase):
    def test_desktop_returns_placeholder(self):
        self.assertIsNone(main.battery_info())
        self.assertEqual(main.battery_log_str(), "?")

    def test_charging_string(self):
        b = {"pct": 100, "mv": 4270, "charging": True}
        self.assertEqual(main.battery_log_str(b), "chg 4270mV")
        b = {"pct": 53, "mv": 3692, "charging": False}
        self.assertEqual(main.battery_log_str(b), "53% 3692mV")


if __name__ == "__main__":
    unittest.main()
