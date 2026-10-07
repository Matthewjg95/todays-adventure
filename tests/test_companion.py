"""Home launcher, module navigation, notebook persistence, tasks, session."""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import home_app
import input_events as ie
import newspaper
import notebook
import screens
import tasks
import ui_renderer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Canvas(ui_renderer.TextCanvas):
    def show(self, mode=1):
        pass


def tile_center(i):
    x, y, w, h = screens.tile_rect(i)
    return x + w // 2, y + h // 2


class Harness(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.free = None
        self.log = []
        self.boot()

    def boot(self):
        self.env = home_app.Env(
            store=notebook.NotebookStore(os.path.join(self.dir, "notes"),
                                         free_fn=lambda p: self.free),
            tasks=tasks.TaskMaster(os.path.join(ROOT, "tasks_fixture.json"),
                                   os.path.join(self.dir, "proposals.json")),
            state_path=os.path.join(self.dir, "app_state.json"),
            wall_time=lambda: 1791400000, idle_ms=180000, log=self.log.append)
        self.app = home_app.App(self.env)
        self.app.open(0)

    def tap(self, x, y, t=100):
        self.app.touch((ie.TAP, x, y, t), t)

    def open_module(self, index):
        self.tap(*tile_center(index))

    def write(self, pts, t=1000):
        self.app.touch((ie.STROKE_START, pts[0][0], pts[0][1], t), t)
        for i, (x, y) in enumerate(pts[1:]):
            self.app.touch((ie.STROKE_POINT, x, y, t + 15 * (i + 1)), t + 15 * (i + 1))
        self.app.touch((ie.STROKE_END, pts[-1][0], pts[-1][1], t + 500), t + 500)


class TestHome(Harness):
    def test_starts_on_home_with_four_modules(self):
        self.assertEqual(self.app.module, "home")
        self.assertEqual([m[0] for m in screens.MODULES],
                         ["adventure", "paper", "notebook", "weather"])
        cv = Canvas()
        self.app.render(cv)
        text = " ".join(s for _, _, s, _ in cv.lines)
        for word in ("Today's", "Daily Paper", "Notebook", "Weather"):
            self.assertIn(word, text)

    def test_tiles_are_large_touch_targets(self):
        for i in range(4):
            x, y, w, h = screens.tile_rect(i)
            self.assertGreaterEqual(h, 120)
            self.assertGreaterEqual(w, 400)
            self.assertLessEqual(y + h, 880)

    def test_hold_returns_home_from_every_module(self):
        for i, name in ((1, "paper"), (2, "notebook"), (3, "weather")):
            self.open_module(i)
            self.assertEqual(self.app.module, name)
            self.app.button(ie.HOLD, 200)
            self.assertEqual(self.app.module, "home", name)

    def test_adventure_tile_exits_to_fridge_cycle(self):
        self.open_module(0)
        self.assertEqual(self.app.exit_reason, "adventure")

    def test_idle_exits_and_input_resets_the_timer(self):
        self.open_module(1)
        self.assertIsNone(self.app.tick(179000))
        self.app.button(ie.PRESS, 170000)
        self.assertIsNone(self.app.tick(300000))
        self.assertEqual(self.app.tick(350001), "idle")


class TestPaper(Harness):
    def test_press_and_rocker_move_hold_does_not(self):
        self.open_module(1)
        self.assertEqual(self.app.stop, 0)
        self.app.button(ie.PRESS)
        self.assertEqual(self.app.stop, 1)
        self.app.rocker(+1)
        self.assertEqual(self.app.stop, 2)
        self.app.rocker(-1)
        self.assertEqual(self.app.stop, 1)
        self.app.button(ie.HOLD)                # Home, not "next"
        self.assertEqual(self.app.module, "home")
        self.assertEqual(self.app.stop, 1)

    def test_taps_turn_and_ends_clamp(self):
        self.open_module(1)
        self.tap(100, 400)
        self.assertEqual(self.app.stop, 0)
        self.assertEqual(self.app.status, "FRONT PAGE")
        for _ in range(20):
            self.tap(400, 400)
        self.assertEqual(self.app.stop, len(newspaper.ROUTE) - 1)
        self.assertEqual(self.app.status, "END OF EDITION")

    def test_viewport_resumes_after_leaving_and_after_restart(self):
        self.open_module(1)
        for _ in range(4):
            self.app.button(ie.PRESS)
        self.app.button(ie.HOLD)
        self.open_module(1)
        self.assertEqual(self.app.stop, 4)
        self.boot()                               # power cycle
        self.open_module(1)
        self.assertEqual(self.app.stop, 4)
        self.assertEqual(self.app.origin(), newspaper.stop_origin(4))

    def test_corrupt_saved_position_is_bounded(self):
        with open(self.env.state_path, "w") as f:
            json.dump({"paper_stop": 999, "paper_view": [-40, 99999]}, f)
        self.boot()
        self.open_module(1)
        self.assertEqual(self.app.origin(), newspaper.clamp_view(*self.app.origin()))
        self.assertTrue(0 <= self.app.stop < len(newspaper.ROUTE))

    def test_pan_frames_when_enabled(self):
        self.env.pan_frames = 2
        self.open_module(1)
        self.app.button(ie.PRESS)
        self.assertEqual(len(self.app.frames), 3)
        self.assertEqual(self.app.frames[-1], newspaper.stop_origin(1))

    def test_renders_every_stop(self):
        self.open_module(1)
        for _ in newspaper.ROUTE:
            cv = Canvas()
            self.app.render(cv)
            self.assertTrue(cv.lines)
            self.app.button(ie.PRESS)


class TestNotebook(Harness):
    STROKE = [(100, 200), (110, 210), (130, 230), (160, 260)]

    def test_save_on_home_hold_and_reopen_after_restart(self):
        self.open_module(2)
        self.write(self.STROKE)
        self.tap(300, 500, t=2000)                # a dot is a stroke too
        self.assertTrue(self.app.note.dirty)
        self.app.button(ie.HOLD)
        self.assertEqual(self.app.module, "home")
        nid = self.app.note.id
        self.assertIn(nid, self.env.store.list_ids())
        self.boot()
        self.open_module(2)
        note = self.app.note
        self.assertEqual(note.id, nid)
        self.assertEqual(len(note.strokes), 2)
        p = note.strokes[0]["p"]
        pts = [(p[i], p[i + 1] + screens.AREA_Y) for i in range(0, len(p), 3)]
        self.assertEqual(pts, self.STROKE)        # coordinates and order
        dts = [p[i + 2] for i in range(0, len(p), 3)]
        self.assertEqual(dts, sorted(dts))        # timing kept
        self.assertEqual(note.strokes[0]["t"], 1791400000)
        self.assertFalse(note.dirty)

    def test_short_press_saves(self):
        self.open_module(2)
        self.write(self.STROKE)
        self.app.button(ie.PRESS)
        self.assertFalse(self.app.note.dirty)
        self.assertTrue(self.app.status.startswith("SAVED"))

    def test_idle_exit_saves(self):
        self.open_module(2)
        self.write(self.STROKE)
        self.assertEqual(self.app.tick(10 ** 7), "idle")
        self.assertIn(self.app.note.id, self.env.store.list_ids())

    def test_pen_down_never_idles(self):
        self.open_module(2)
        self.app.touch((ie.STROKE_START, 100, 200, 10), 10)
        self.assertIsNone(self.app.tick(10 ** 7))

    def test_ink_is_recorded_before_any_redraw(self):
        self.open_module(2)
        self.app.render(Canvas())
        self.write(self.STROKE)
        # No frame drawn yet, but the model already holds every point.
        self.assertEqual(self.app.note.point_count(), len(self.STROKE))
        self.assertEqual(len(self.app.take_ink()), len(self.STROKE) - 1)

    def test_undo_and_clear_needs_confirmation(self):
        self.open_module(2)
        self.write(self.STROKE)
        self.write(self.STROKE, t=3000)
        self.tap(*self._button("undo"))
        self.assertEqual(len(self.app.note.strokes), 1)
        self.tap(*self._button("clear"))
        self.assertTrue(self.app.confirming)
        self.assertEqual(len(self.app.note.strokes), 1)
        self.tap(screens.W * 3 // 4, 40)          # KEEP
        self.assertFalse(self.app.confirming)
        self.assertEqual(len(self.app.note.strokes), 1)
        self.tap(*self._button("clear"))
        self.tap(screens.W // 4, 40)              # YES, CLEAR
        self.assertEqual(self.app.note.strokes, [])

    def test_new_saves_previous_and_starts_fresh(self):
        self.open_module(2)
        self.write(self.STROKE)
        first = self.app.note.id
        self.tap(*self._button("new"))
        self.assertNotEqual(self.app.note.id, first)
        self.assertIn(first, self.env.store.list_ids())
        self.assertEqual(self.app.note.strokes, [])

    def test_full_storage_is_visible_and_keeps_the_ink(self):
        self.free = 1024
        self.open_module(2)
        self.write(self.STROKE)
        self.app.button(ie.HOLD)
        self.assertEqual(self.app.module, "home")
        self.assertIn("STORAGE FULL", self.app.status)
        cv = Canvas()
        self.app.render(cv)
        self.assertTrue(any("STORAGE FULL" in s for _, _, s, _ in cv.lines))
        self.assertTrue(self.app.note.dirty)
        self.assertEqual(self.env.store.list_ids(), [])
        self.free = None                         # space freed: retry works
        self.open_module(2)
        self.app.button(ie.PRESS)
        self.assertFalse(self.app.note.dirty)

    def test_new_refuses_to_discard_unsaved_page(self):
        self.free = 10
        self.open_module(2)
        self.write(self.STROKE)
        nid = self.app.note.id
        self.tap(*self._button("new"))
        self.assertEqual(self.app.note.id, nid)
        self.assertTrue(self.app.note.strokes)

    def _button(self, name):
        i = screens.BUTTONS.index(name)
        x, y, w, h = screens.button_rect(i)
        return x + w // 2, y + h // 2


class TestNotebookStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.store = notebook.NotebookStore(os.path.join(self.dir, "notes"))

    def note(self):
        n = notebook.Note("n0001", 540, 790, 1)
        n.begin_stroke(10, 10, 0, 1791400000)
        n.add_point(20, 25, 16)
        n.end_stroke()
        return n

    def test_write_failure_is_reported_and_leaves_no_temp(self):
        n = self.note()
        with mock.patch("builtins.open", side_effect=OSError(28, "No space")):
            with self.assertRaises(notebook.NotebookError):
                self.store.save(n)
        self.assertTrue(n.dirty)
        self.assertEqual(os.listdir(os.path.join(self.dir, "notes")), [])

    def test_interrupted_save_is_recovered(self):
        self.store.save(self.note())
        os.rename(self.store.path("n0001"), self.store.path("n0001") + ".tmp")
        self.assertEqual(self.store.recover_tmp(), ["n0001"])
        self.assertEqual(len(self.store.load("n0001").strokes), 1)

    def test_free_space_probe_works_here(self):
        self.assertIsNotNone(notebook.free_bytes(self.dir))

    def test_export_bundle_and_image(self):
        n = self.note()
        bundle = notebook.export_bundle(n)
        self.assertEqual(bundle["strokes"][0]["points"], [[10, 10, 0], [20, 25, 16]])
        img = notebook.rasterize_pbm(n)
        header = b"P4\n540 790\n"
        self.assertTrue(img.startswith(header))
        self.assertEqual(len(img), len(header) + (540 + 7) // 8 * 790)
        self.assertTrue(any(img[len(header):]))
        out = notebook.CompanionExporter(outdir=os.path.join(self.dir, "x")).export(n)
        self.assertTrue(os.path.exists(out + ".pbm"))

    def test_rejects_unknown_format(self):
        with self.assertRaises(notebook.NotebookError):
            notebook.Note.from_dict({"format": "other"})


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.master = tasks.TaskMaster(os.path.join(ROOT, "tasks_fixture.json"),
                                       os.path.join(self.dir, "p.json"))

    def test_fixture_covers_every_status_with_stable_ids(self):
        snap = self.master.snapshot()
        self.assertTrue(snap.is_fixture)
        self.assertEqual({t["status"] for t in snap.tasks()}, set(tasks.STATUSES))
        self.assertEqual(tasks.STATUSES, ("inbox", "next", "active", "waiting",
                                          "later", "done", "dropped"))

    def test_proposal_never_changes_status(self):
        before = self.master.snapshot().get("T-0002")
        p = self.master.propose("T-0002", "done", "note:n0001")
        self.assertEqual(p["state"], "proposed")
        self.assertEqual(self.master.snapshot().get("T-0002"), before)
        self.assertEqual(len(self.master.proposals()), 1)

    def test_snapshot_is_a_copy(self):
        snap = self.master.snapshot()
        snap.tasks()[0]["status"] = "done"
        self.assertNotEqual(snap.tasks()[0]["status"], "done")

    def test_validation(self):
        with self.assertRaises(tasks.TaskError):
            self.master.propose("T-0002", "finished", "x")
        with self.assertRaises(tasks.TaskError):
            self.master.propose("T-9999", "done", "x")
        with self.assertRaises(tasks.TaskError):
            tasks.Snapshot({"tasks": [{"id": "a", "title": "x", "status": "next"},
                                      {"id": "a", "title": "y", "status": "next"}]})


class FakeSampler:
    """Replays scripted events; stands in for device_io.Sampler."""

    script = []

    def __init__(self):
        self.queue = []
        self.dropped = 0
        self._timer = object()
        self.t = 0
        self.side_tracker = ie.ButtonTracker(1000)
        self.drains = 0

    def start(self):
        pass

    def stop(self):
        pass

    def now_ms(self):
        return self.t

    def drain(self):
        self.drains += 1
        self.t += 50
        if FakeSampler.script:
            return [FakeSampler.script.pop(0)]
        return []


class TestSessionLoop(unittest.TestCase):
    """The device loop: Home until Adventure/idle, never sleeping inside."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, self.cwd)
        shutil.copy(os.path.join(ROOT, "tasks_fixture.json"), self.dir)
        fake = types.ModuleType("device_io")
        fake.Sampler = FakeSampler
        patcher = mock.patch.dict(sys.modules, {"device_io": fake})
        patcher.start()
        self.addCleanup(patcher.stop)

    def host(self):
        self.calls = []
        return {"feed": lambda: self.calls.append("feed"),
                "log": lambda m: self.calls.append(m),
                "stage": lambda s: None,
                "wifi_off": lambda: None, "sync_clock": lambda: None,
                "battery": lambda: {"pct": 70, "charging": False},
                "battery_str": lambda: "70%"}

    def run_session(self, script):
        import scheduler
        import session
        FakeSampler.script = list(script)
        cv = Canvas()
        with mock.patch.object(session.time, "sleep_ms", create=True), \
                mock.patch.object(session.ui_renderer, "make_canvas", return_value=cv), \
                mock.patch.object(scheduler, "sleep_for") as sleep:
            reason = session.run(self.host())
            sleep.assert_not_called()
        return reason

    def test_paper_hold_then_adventure(self):
        px, py = tile_center(1)
        ax, ay = tile_center(0)
        reason = self.run_session([
            ("touch", (ie.TAP, px, py, 50), 50),
            ("button", ie.PRESS, 100),
            ("button", ie.HOLD, 150),
            ("touch", (ie.TAP, ax, ay, 200), 200),
        ])
        self.assertEqual(reason, "adventure")
        self.assertIn("feed", self.calls)
        state = json.load(open("app_state.json"))
        self.assertEqual(state["paper_stop"], 1)

    def test_idle_timeout_ends_session(self):
        with mock.patch("config.INTERACTIVE_IDLE_SECONDS", 1):
            self.assertEqual(self.run_session([]), "idle")


class TestMainIntegration(unittest.TestCase):
    def test_button_wake_runs_session_before_fridge_cycle(self):
        import main
        order = []
        with mock.patch.object(main, "MICROPYTHON", True), \
                mock.patch.object(main, "battery_info", return_value={"pct": 60, "mv": 3800, "charging": False}), \
                mock.patch.object(main, "establish_time", return_value="system"), \
                mock.patch.object(main.scheduler, "woke_by_timer", return_value=False), \
                mock.patch.object(main, "log_wake"), \
                mock.patch.object(main, "run_interactive", side_effect=lambda w: order.append("session")), \
                mock.patch.object(main, "show_flashcard", side_effect=lambda: order.append("card")), \
                mock.patch.object(main, "scheduled_cycle", side_effect=lambda b: (order.append(("cycle", b)), (_ for _ in ()).throw(StopIteration))[0]), \
                mock.patch.dict(sys.modules, {"machine": None, "esp32": None}):
            with self.assertRaises(StopIteration):
                main.run_forever()
        self.assertEqual(order, ["session", ("cycle", True)])

    def test_flashcard_fallback_is_configurable(self):
        import main
        order = []
        with mock.patch.object(main.config, "BUTTON_WAKE_ACTION", "flashcard"), \
                mock.patch.object(main, "MICROPYTHON", True), \
                mock.patch.object(main, "battery_info", return_value={"pct": 60, "mv": 3800, "charging": False}), \
                mock.patch.object(main, "establish_time", return_value="system"), \
                mock.patch.object(main.scheduler, "woke_by_timer", return_value=False), \
                mock.patch.object(main, "log_wake"), \
                mock.patch.object(main, "run_interactive", side_effect=lambda w: order.append("session")), \
                mock.patch.object(main, "show_flashcard", side_effect=lambda: order.append("card")), \
                mock.patch.object(main, "scheduled_cycle", side_effect=StopIteration), \
                mock.patch.dict(sys.modules, {"machine": None, "esp32": None}):
            with self.assertRaises(StopIteration):
                main.run_forever()
        self.assertEqual(order, ["card"])


if __name__ == "__main__":
    unittest.main()
