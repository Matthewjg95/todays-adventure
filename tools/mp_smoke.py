"""Run the pure interactive modules under MicroPython's unix port.

    micropython tools/mp_smoke.py <repo-root> <empty-scratch-dir>

CPython tests cannot catch MicroPython gaps (no os.replace, no
tempfile, smaller stdlib). This replays the milestone sequence through
home_app with the ASCII canvas: paper navigation, handwriting, hold to
Home, simulated restart, reopen, Adventure exit. No hardware involved.
"""

import os
import sys

root, work = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)
os.chdir(work)

import home_app  # noqa: E402
import input_events as ie  # noqa: E402
import newspaper  # noqa: E402
import notebook  # noqa: E402
import screens  # noqa: E402
import tasks  # noqa: E402
import ui_renderer  # noqa: E402


class Canvas(ui_renderer.TextCanvas):
    def show(self, mode=1):
        pass


def env():
    return home_app.Env(
        store=notebook.NotebookStore("notes"),
        tasks=tasks.TaskMaster(root + "/tasks_fixture.json", "proposals.json"),
        state_path="app_state.json", wall_time=lambda: 1791400000)


def tap(app, i):
    x, y, w, h = screens.tile_rect(i)
    app.touch((ie.TAP, x + w // 2, y + h // 2, 0), 0)


# Button separation, as the device sampler would feed it.
b = ie.ButtonTracker(1000)
seen = []
for t in range(0, 3000, 15):
    seen += b.feed(t < 2000, t)            # wake press: held from boot
for t in range(3000, 3400, 15):
    seen += b.feed(3015 <= t < 3200, t)    # short press
for t in range(3400, 5000, 15):
    seen += b.feed(t < 4800, t)            # hold
assert seen == [ie.PRESS, ie.HOLD], seen

app = home_app.App(env())
app.open(0)
tap(app, 1)
assert app.module == "paper"
for _ in range(4):
    app.button(ie.PRESS)
    cv = Canvas()
    app.render(cv)
assert app.stop == 4
app.button(ie.HOLD)
assert app.module == "home"

tap(app, 2)
app.touch((ie.STROKE_START, 100, 200, 10), 10)
for i in range(1, 20):
    app.touch((ie.STROKE_POINT, 100 + i * 5, 200 + i * 3, 10 + i * 15), 10 + i * 15)
app.touch((ie.STROKE_END, 195, 257, 400), 400)
app.render(Canvas())
app.button(ie.HOLD)                         # saves, then Home
assert app.module == "home" and not app.note.dirty

app = home_app.App(env())                   # "restart"
app.open(0)
tap(app, 2)
assert len(app.note.strokes) == 1 and app.note.point_count() == 20
app.button(ie.PRESS)                        # save while clean: no error
app.button(ie.HOLD)
tap(app, 1)
assert app.stop == 4, app.stop
app.button(ie.HOLD)
tap(app, 0)
assert app.exit_reason == "adventure"

img = notebook.rasterize_pbm(app.note)
assert img.startswith(b"P4\n540 790\n")
# Overwrite an existing note (the rename-over path MicroPython needs).
store = notebook.NotebookStore("notes")
app.note.add_point(1, 1, 999)
store.save(app.note)
assert store.load(app.note.id).point_count() == 21
print("mp_smoke OK", sys.implementation.name,
      "stops", len(newspaper.ROUTE), "notes", store.list_ids())
