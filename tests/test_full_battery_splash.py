"""The wave is selected by full battery, not the charging heuristic."""
import unittest
from unittest import mock
import main


class TestFullBatterySplash(unittest.TestCase):
    def test_full_only_and_returns_to_adventure_below_full(self):
        with mock.patch.object(main, "battery_info") as battery, \
                mock.patch.object(main.ui_renderer, "render_splash") as splash, \
                mock.patch.object(main.ui_renderer, "render") as render, \
                mock.patch.object(main.weather_service, "_load_json", return_value={}), \
                mock.patch.object(main.weather_service, "_save_json"):
            for pct, charging, expected in ((99, True, False), (100, True, True),
                                             (100, False, True), (99, False, False)):
                with self.subTest(pct=pct, charging=charging):
                    battery.return_value = {"pct": pct, "mv": 4200, "charging": charging}
                    splash.reset_mock()
                    render.reset_mock()
                    main.update_display(main.demo_context(), force=True)
                    self.assertEqual(splash.call_count, int(expected))
                    self.assertEqual(render.call_count, int(not expected))
