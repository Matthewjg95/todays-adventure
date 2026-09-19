"""Coordinate regressions for the photographed adventure/list collision."""
import unittest
from unittest import mock

import config
import main
import ui_renderer as ui


class RecordingCanvas(ui.TextCanvas):
    def show(self):
        pass


class TestAdventureSpacing(unittest.TestCase):
    def check_layout(self, big, adventure, wonder, activities):
        ctx = main.demo_context()
        ctx["adventure"] = adventure
        cv = RecordingCanvas()
        with mock.patch.object(config, "BIG_TEXT", big):
            ui.render(cv, ctx, "OPEN THE WINDOWS TODAY", activities, wonder)
        rows = {text: (y, size) for y, x, text, size in cv.lines}
        if adventure:
            y, size = rows[adventure]
            self.assertGreaterEqual(rows[activities[0]][0] - (y + size), 12)
        for first, second in zip(activities, activities[1:]):
            y, size = rows[first]
            self.assertGreaterEqual(rows[second][0] - (y + size), 8)
        y, size = rows[activities[-1]]
        self.assertLessEqual(y + size, 832 if big else 808)

    def test_photo_content_both_font_modes(self):
        for big in (False, True):
            with self.subTest(big=big):
                self.check_layout(big, "Chittenango Falls",
                                  "Let a little of today inside.",
                                  ["Sunset Walk", "Eat Dinner Outside"])

    def test_long_adventure_name(self):
        for big in (False, True):
            self.check_layout(big, "Labrador Hollow boardwalk",
                              "Let a little of today inside.",
                              ["Sunset Walk", "Eat Dinner Outside"])

    def test_long_wonder_keeps_list_above_sun(self):
        self.check_layout(True, "Chittenango Falls",
                          "Take a moment to notice the changing light and the "
                          "quiet beauty of the world outside your window today.",
                          ["Sunset Walk", "Eat Dinner Outside"])

    def test_three_suggestions_without_adventure(self):
        for big in (False, True):
            self.check_layout(big, None, "Let a little of today inside.",
                              ["Sunset Walk", "Eat Dinner Outside", "Read A Book"])
