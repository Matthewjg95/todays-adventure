"""Daily Paper: one fixed layout, bounded viewport, overlapping route."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import main
import newspaper as np
import tasks
import ui_renderer

try:
    from preview_canvas import PILCanvas
except ImportError:          # Pillow missing: font-metric checks skip
    PILCanvas = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edition(**kw):
    snap = tasks.TaskMaster(os.path.join(ROOT, "tasks_fixture.json")).snapshot()
    return np.build_edition(snap, kw.get("ctx"), kw.get("wonder"), kw.get("adv"),
                            kw.get("notes"), "Wednesday, October 7")


class TestGeometry(unittest.TestCase):
    def test_paper_is_larger_than_screen_in_both_directions(self):
        self.assertGreater(np.PAPER_W, 2 * np.VIEW_W)
        self.assertGreater(np.PAPER_H, 2 * np.VIEW_H)

    def test_every_stop_is_inside_the_paper(self):
        for i in range(len(np.ROUTE)):
            x, y = np.stop_origin(i)
            self.assertEqual(np.clamp_view(x, y), (x, y))

    def test_route_visits_every_cell_once(self):
        cells = [(c, r) for c, r, _ in np.ROUTE]
        self.assertEqual(len(set(cells)), np.COLS * np.ROWS)

    def test_consecutive_stops_overlap_for_orientation(self):
        for i in range(len(np.ROUTE) - 1):
            a, b = np.stop_origin(i), np.stop_origin(i + 1)
            shared = np.overlap(a, b)
            # at least an 80 px shared band in the direction of travel
            self.assertGreaterEqual(shared, 80 * np.VIEW_W, (i, a, b))
            self.assertLess(shared, np.VIEW_W * np.VIEW_H)  # it does move

    def test_clamps(self):
        self.assertEqual(np.clamp_view(-50, 99999),
                         (0, np.PAPER_H - np.VIEW_H))
        self.assertEqual(np.clamp_stop(-3), 0)
        self.assertEqual(np.clamp_stop(99), len(np.ROUTE) - 1)
        self.assertEqual(np.clamp_stop("junk"), 0)
        self.assertEqual(np.nearest_stop(*np.stop_origin(5)), 5)

    def test_pan_frames_stay_in_bounds_and_end_on_target(self):
        a, b = np.stop_origin(2), np.stop_origin(3)
        self.assertEqual(np.pan_frames(a, b, 0), [b])
        frames = np.pan_frames(a, b, 3)
        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[-1], b)
        for f in frames:
            self.assertEqual(np.clamp_view(*f), f)

    def test_block_positions_do_not_depend_on_content(self):
        rects = lambda blocks: [b[:5] for b in blocks]
        bare = edition()
        full = edition(ctx=main.demo_context(), wonder="A long wonder " * 5,
                       adv="Somewhere", notes=["Note N0001", "Note N0002"])
        self.assertEqual(rects(bare), rects(full))
        for bid, x, y, w, h, _ in bare:
            self.assertTrue(0 <= x and x + w <= np.PAPER_W and 0 <= y
                            and y + h <= np.PAPER_H, bid)

    def test_only_visible_blocks_are_drawn(self):
        paper = np.Paper(edition())
        ids = {b[0] for b in paper.visible_blocks(*np.stop_origin(0))}
        self.assertIn("c00", ids)
        self.assertNotIn("c22", ids)
        self.assertNotIn("c02", ids)

    def test_minimap_fits_in_the_bar(self):
        self.assertLessEqual(np.MAP_H + 6, ui_renderer.H - np.BAR_Y)


class TestTypography(unittest.TestCase):
    def check_fits(self, measure):
        for ctx in (None, main.demo_context()):
            for block in edition(ctx=ctx, wonder="Only a few days each year are this nice.",
                                 adv="Highland Forest trails"):
                if block[0] == "masthead":
                    continue
                ops, used = np.typeset(block, measure)
                self.assertLessEqual(used, block[4], block[0])
                for kind, x, y, payload, size, _ in ops:
                    if kind == "text":
                        self.assertLessEqual(x + measure(payload, size),
                                             block[1] + block[3] + 2, payload)

    def test_fits_with_conservative_estimate(self):
        self.check_fits(ui_renderer.TextCanvas().text_width)

    @unittest.skipIf(PILCanvas is None, "Pillow not installed")
    def test_fits_with_dejavu_metrics(self):
        self.check_fits(PILCanvas().text_width)

    def test_body_type_is_readable(self):
        for block in edition():
            for item in block[5]:
                if item[0] == "head":
                    self.assertGreaterEqual(item[2], 40)
        self.assertGreaterEqual(np.CELL_W, 400)    # roughly 30 chars of 24pt


class TestRender(unittest.TestCase):
    def test_sample_labelled_and_bar_drawn(self):
        paper = np.Paper(edition())
        cv = ui_renderer.TextCanvas()
        paper.render_window(cv, *np.stop_origin(0))
        np.render_bar(cv, paper, 0, *np.stop_origin(0))
        text = " ".join(s for _, _, s, _ in cv.lines)
        self.assertIn("SAMPLE", text)
        self.assertIn("1 OF 9", text)
        for y, x, s, size in cv.lines:
            self.assertLess(y, ui_renderer.H)

    def test_no_weather_is_never_invented(self):
        blocks = dict((b[0], b[5]) for b in edition(ctx=None))
        heads = [i[1] for i in blocks["c21"] if i[0] == "head"]
        self.assertEqual(heads, ["No weather cached yet"])


if __name__ == "__main__":
    unittest.main()
