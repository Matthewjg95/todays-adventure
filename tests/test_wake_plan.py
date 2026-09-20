import copy
import datetime
import unittest
from unittest import mock
import main
import scheduler
import wake_plan


def epoch(date):
    return int(datetime.datetime.fromisoformat(date).replace(
        tzinfo=datetime.timezone.utc).timestamp())


RAW = {"utc_offset_seconds": -14400, "daily": {
    "time": ["2026-09-20", "2026-09-21"],
    "sunrise": ["2026-09-20T07:00", "2026-09-21T07:00"],
    "sunset": ["2026-09-20T19:00", "2026-09-21T19:00"]}}


class TestSlots(unittest.TestCase):
    def test_five_day_two_night(self):
        slots = [s for s in wake_plan.slots(epoch("2026-09-20T16:00"), RAW)
                 if s[0].startswith("2026-09-20-")]
        self.assertEqual(len(slots), 7)
        self.assertEqual(sum(s[2] for s in slots), 2)
        self.assertEqual(slots[0][1], epoch("2026-09-20T11:15"))
        self.assertEqual(slots[-1][1], epoch("2026-09-21T07:00"))

    def test_early_reset_does_not_repeat(self):
        now = epoch("2026-09-20T11:12")
        due, future = wake_plan.choose(now, RAW)
        self.assertTrue(due[0].endswith("-d0"))
        self.assertGreater(future[1] - now, 2 * 3600)
        self.assertIsNone(wake_plan.choose(now + 60, RAW, attempted=[due[0]])[0])
        self.assertIsNone(wake_plan.choose(now + 240, RAW, attempted=[due[0]])[0])

    def test_late_boot_coalesces(self):
        due, future = wake_plan.choose(epoch("2026-09-20T20:10"), RAW)
        self.assertTrue(due[0].endswith("-d3"))
        self.assertTrue(future[0].endswith("-d4"))

    def test_two_day_simulation_with_early_wakes(self):
        attempted = []
        now = epoch("2026-09-20T11:15")
        for _ in range(14):
            due, future = wake_plan.choose(now, RAW, attempted=attempted)
            self.assertIsNotNone(due)
            self.assertNotIn(due[0], attempted)
            attempted.append(due[0])
            self.assertIsNone(wake_plan.choose(now + 30, RAW, attempted=attempted)[0])
            now = future[1] - 120
        for date in ("2026-09-20", "2026-09-21"):
            self.assertEqual(sum(s.startswith(date) for s in attempted), 7)

    def test_fallback_missing_or_polar_data(self):
        for raw in ({}, {"daily": {"time": ["2026-09-20"],
                                  "sunrise": [None], "sunset": [None]}}):
            schedule = wake_plan.slots(epoch("2026-09-20T12:00"), raw)
            self.assertEqual(len([s for s in schedule if s[0].startswith("2026-09-20")]), 7)

    def test_year_rollover(self):
        due, future = wake_plan.choose(epoch("2026-12-31T23:59"))
        self.assertGreater(future[1], epoch("2027-01-01T00:00"))
        self.assertTrue(due[0].startswith("2026-12-31"))

    def test_offset_change_preserves_local_slot_identity(self):
        before = {"utc_offset_seconds": -14400}
        after = {"utc_offset_seconds": -18000}
        a = [s for s in wake_plan.slots(epoch("2026-11-01T17:00"), before)
             if s[0] == "2026-11-01-d2"][0]
        b = [s for s in wake_plan.slots(epoch("2026-11-01T17:00"), after)
             if s[0] == a[0]][0]
        self.assertEqual(b[1] - a[1], 3600)
        self.assertIsNone(wake_plan.choose(b[1], after, attempted=[a[0]])[0])

    def test_plugged_hourly(self):
        due, future = wake_plan.choose(epoch("2026-09-20T16:00"), RAW, "plugged")
        self.assertEqual(future[1] - due[1], 3600)

    def test_legacy_sleep_no_longer_clamps(self):
        with mock.patch.object(scheduler.time, "time", return_value=7140), \
                mock.patch.object(scheduler, "sleep_for") as sleep:
            scheduler.sleep_until_next_update()
            sleep.assert_called_once_with(3660)


class TestCycle(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.patches = [
            mock.patch.object(main.time, "time", return_value=epoch("2026-09-20T11:15")),
            mock.patch.object(main, "battery_info", return_value={"pct": 60, "mv": 3800, "charging": False}),
            mock.patch.object(main.weather_service, "_load_json", side_effect=self.load),
            mock.patch.object(main, "_save_schedule", side_effect=self.save),
            mock.patch.object(main, "update_display"),
            mock.patch.object(main, "_maybe_ota"),
            mock.patch.object(main, "_sleep_to"),
            mock.patch.object(main, "log_wake"),
            mock.patch.object(main.config, "POWER_MODE", "fridge")]
        self.mocks = [p.start() for p in self.patches]
        self.addCleanup(mock.patch.stopall)

    def load(self, path):
        return copy.deepcopy(RAW if path == main.config.CACHE_FILE else self.state)

    def save(self, value):
        self.state = copy.deepcopy(value)

    def test_claim_before_render_and_complete_before_ota(self):
        def render(**kwargs):
            self.assertEqual(self.state["last"]["status"], "attempted")
        def ota():
            self.assertEqual(self.state["last"]["status"], "completed")
        self.mocks[4].side_effect = render
        self.mocks[5].side_effect = ota
        main.scheduled_cycle()
        self.assertEqual(self.state["last"]["status"], "completed")
        main.scheduled_cycle()
        self.assertEqual(self.mocks[4].call_count, 1)
        self.assertEqual(self.mocks[5].call_count, 1)

    def test_fetch_failure_does_not_retry_slot(self):
        self.mocks[4].side_effect = OSError("offline")
        main.scheduled_cycle()
        self.assertEqual(self.state["last"]["status"], "failed")
        main.scheduled_cycle()
        self.assertEqual(self.mocks[4].call_count, 1)
        self.mocks[5].assert_not_called()

    def test_critical_battery_skips_network_even_if_charging_flag_lies(self):
        self.mocks[1].return_value = {"pct": 8, "mv": 3374, "charging": True}
        main.scheduled_cycle(True)
        self.mocks[4].assert_not_called()
        self.mocks[5].assert_not_called()
        self.assertEqual(self.mocks[6].call_args.args[1], "critical")

    def test_actual_sleep_matches_intent(self):
        self.patches[6].stop()
        with mock.patch.object(main, "wifi_off"), mock.patch.object(main, "_stage"), \
                mock.patch.object(scheduler, "note_expected_wake") as intent, \
                mock.patch.object(scheduler, "sleep_for") as sleep:
            main._sleep_to(epoch("2026-09-20T14:00"), "next")
            self.assertEqual(intent.call_args.args, sleep.call_args.args)
            sleep.assert_called_once_with(9900)
