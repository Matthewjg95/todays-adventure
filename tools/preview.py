"""Desktop preview of the interactive prototype (no hardware).

Drives the REAL controller (home_app.App) through the physical test
sequence, feeding raw button levels and touch samples through the
same input state machines the device uses, and saves every frame:

  launcher -> newspaper navigation -> handwriting -> hold to Home
  -> "restart" -> reopen note -> paper resumes -> Adventure

    python tools/preview.py [outdir] [--edition edition.json]

Without --edition the Paper shows its labelled sample edition, as a
board that has not downloaded one yet would.

Weather in the preview is the synthetic demo day, labelled as such.
State and notes go to a temporary folder, never the repo.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from PIL import Image, ImageDraw  # noqa: E402

import adventures  # noqa: E402
import home_app  # noqa: E402
import input_events as ie  # noqa: E402
import main  # noqa: E402
import newspaper  # noqa: E402
import notebook  # noqa: E402
import recommendation_engine  # noqa: E402
import scoring_engine  # noqa: E402
import screens  # noqa: E402
import tasks  # noqa: E402
import ui_renderer  # noqa: E402
import wonder_engine  # noqa: E402
from preview_canvas import PILCanvas  # noqa: E402


EDITION = None          # (sections, label, stale) when --edition is given


def load_edition(path):
    import edition
    with open(path) as f:
        ed = edition.validate(json.load(f))
    import time
    t = time.localtime(ed["generated"])
    return (ed["sections"], time.strftime("Edition of %a, %b %d, %I:%M %p (desktop)", t),
            False)


def demo_weather():
    ctx = main.demo_context()
    ctx["score"] = scoring_engine.score_day(ctx)
    ctx["time_str"] = "9:00 AM DEMO"
    return ctx, wonder_engine.wonder(ctx), adventures.today(ctx)


class Rig:
    """Feeds the app the way session.py does, with a fake clock."""

    def __init__(self, workdir, outdir, weather=demo_weather):
        self.work = workdir
        self.out = outdir
        self.t = 0
        self.frames = []
        self.weather = weather
        self.boot()

    def boot(self):
        self.env = home_app.Env(
            store=notebook.NotebookStore(os.path.join(self.work, "notes")),
            tasks=tasks.TaskMaster(os.path.join(ROOT, "tasks_fixture.json"),
                                   os.path.join(self.work, "proposals.json")),
            state_path=os.path.join(self.work, "app_state.json"),
            weather=self.weather,
            date_str=lambda: "Wednesday, October 7 (desktop preview)",
            edition=lambda: EDITION,
            wall_time=lambda: 1791400000 + self.t // 1000)
        self.app = home_app.App(self.env)
        self.button = ie.ButtonTracker(1000)
        self.button.feed(False, self.t)     # released: the wake press is over
        self.touch_t = ie.TouchTracker()
        self.cv = PILCanvas()
        self.app.open(self.t)
        self.draw()

    def draw(self):
        if self.app.needs_frame and not self.app.exit_reason:
            self.cv.reset()
            self.app.render(self.cv)
            self.cv.show(1)
        ink = self.app.take_ink()
        if ink:
            self.cv.ink_segments(ink)

    def step(self, ms=15):
        self.t += ms

    def hold_side(self, ms):
        for _ in range(0, ms, 15):
            for e in self.button.feed(True, self.t):
                self.app.button(e, self.t)
            self.step()
        for _ in range(4):
            for e in self.button.feed(False, self.t):
                self.app.button(e, self.t)
            self.step()
        self.draw()

    def tap(self, x, y):
        for _ in range(5):
            for e in self.touch_t.feed((x, y), self.t):
                self.app.touch(e, self.t)
            self.step()
        for e in self.touch_t.feed(None, self.t):
            self.app.touch(e, self.t)
        self.step(200)
        self.draw()

    def stroke(self, pts):
        for p in pts:
            for e in self.touch_t.feed(p, self.t):
                self.app.touch(e, self.t)
            self.step()
        for e in self.touch_t.feed(None, self.t):
            self.app.touch(e, self.t)
        self.step(120)
        self.draw()

    def snap(self, name):
        path = os.path.join(self.out, "%02d_%s.png" % (len(self.frames) + 1, name))
        self.cv.save(path)
        self.frames.append(path)
        return path


def _seg(a, b, n=12):
    return [(int(a[0] + (b[0] - a[0]) * i / n), int(a[1] + (b[1] - a[1]) * i / n))
            for i in range(n + 1)]


def handwriting():
    """'Hi' plus a small sun sketch, as pen strokes in screen pixels."""
    strokes = [
        _seg((80, 220), (80, 360)),
        _seg((80, 290), (150, 290)),
        _seg((150, 220), (150, 360)),
        _seg((200, 280), (200, 360)),
    ]
    sun = []
    import math
    for i in range(41):
        a = 2 * math.pi * i / 40
        sun.append((int(380 + 50 * math.cos(a)), int(300 + 50 * math.sin(a))))
    strokes.append(sun)
    for k in range(8):
        a = 2 * math.pi * k / 8
        strokes.append(_seg((int(380 + 65 * math.cos(a)), int(300 + 65 * math.sin(a))),
                            (int(380 + 95 * math.cos(a)), int(300 + 95 * math.sin(a))), 4))
    strokes.append(_seg((80, 470), (460, 470), 30))
    return strokes


def paper_overview(path):
    """The whole paper with the reading route: a desktop-only picture."""
    ctx, wonder_text, adv = demo_weather()
    snap = tasks.TaskMaster(os.path.join(ROOT, "tasks_fixture.json")).snapshot()
    news, label, stale = EDITION or (None, None, False)
    paper = newspaper.Paper(newspaper.build_edition(
        snap, ctx, wonder_text, adv, ["Note N0001"], "Wednesday, October 7",
        news, label, stale), newspaper.route_titles(news))
    big = Image.new("L", (newspaper.PAPER_W, newspaper.PAPER_H), 255)
    for c in range(newspaper.COLS):
        for r in range(newspaper.ROWS):
            ox, oy = c * newspaper.STEP_X, r * newspaper.STEP_Y
            cv = PILCanvas(newspaper.VIEW_W, newspaper.VIEW_H)
            paper.render_window(cv, ox, oy)
            big.paste(cv.img, (ox, oy))
    d = ImageDraw.Draw(big)
    centers = []
    for i in range(len(newspaper.ROUTE)):
        x, y = newspaper.stop_origin(i)
        centers.append((x + newspaper.VIEW_W // 2, y + newspaper.VIEW_H - 60))
    d.line(centers, fill=0x77, width=6)
    for i, (cx, cy) in enumerate(centers):
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=0, outline=0)
        d.text((cx - 5, cy - 6), str(i + 1), fill=255)
    # the first window, as the screen would frame it
    d.rectangle((0, 0, newspaper.VIEW_W - 1, newspaper.VIEW_H - 1), outline=0, width=4)
    big.save(path)


def contact_sheet(paths, out, cols=5, scale=3):
    tiles = [Image.open(p) for p in paths]
    w, h = 540 // scale, 960 // scale
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("L", (cols * (w + 10) + 10, rows * (h + 34) + 10), 200)
    d = ImageDraw.Draw(sheet)
    for i, (img, p) in enumerate(zip(tiles, paths)):
        x = 10 + (i % cols) * (w + 10)
        y = 10 + (i // cols) * (h + 34)
        sheet.paste(img.resize((w, h)), (x, y))
        d.text((x, y + h + 4), os.path.basename(p)[:-4], fill=0)
    sheet.save(out)


def run(outdir):
    os.makedirs(outdir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="ta-preview-")
    try:
        rig = Rig(work, outdir)
        rig.snap("home")
        x, y, w, h = screens.tile_rect(1)
        rig.tap(x + w // 2, y + h // 2)                 # Daily Paper
        rig.snap("paper_front_page")
        rig.hold_side(200)                              # short press: next
        rig.snap("paper_engineering")
        rig.app.rocker(+1, rig.t)
        rig.draw()
        rig.snap("paper_project_desk")
        rig.tap(400, 500)                               # tap right half: next
        rig.snap("paper_adventure_weather")
        rig.tap(100, 500)                               # tap left half: back
        rig.tap(400, 500)
        rig.tap(400, 500)
        rig.snap("paper_engineering_continued")
        assert rig.app.stop == 4, rig.app.stop
        rig.hold_side(1200)                             # hold: Home
        rig.snap("home_after_hold")
        assert rig.app.module == "home"
        x, y, w, h = screens.tile_rect(2)
        rig.tap(x + w // 2, y + h // 2)                 # Notebook
        for s in handwriting():
            rig.stroke(s)
        rig.snap("notebook_handwriting_unsaved")
        rig.hold_side(1200)                             # hold: save + Home
        assert rig.app.module == "home"
        note_ids = rig.env.store.list_ids()
        assert note_ids, "note was not saved on Home hold"
        # --- simulated restart: a fresh controller over the same flash ----
        rig.boot()
        x, y, w, h = screens.tile_rect(2)
        rig.tap(x + w // 2, y + h // 2)
        rig.snap("notebook_reopened_after_restart")
        assert rig.app.note.strokes, "strokes not recovered"
        rig.hold_side(1200)
        x, y, w, h = screens.tile_rect(1)
        rig.tap(x + w // 2, y + h // 2)
        rig.snap("paper_resumed_same_stop")
        assert rig.app.stop == 4
        rig.hold_side(1200)
        x, y, w, h = screens.tile_rect(3)
        rig.tap(x + w // 2, y + h // 2)
        rig.snap("weather_flashcard")
        rig.hold_side(1200)
        x, y, w, h = screens.tile_rect(0)
        rig.tap(x + w // 2, y + h // 2)                 # Today's Adventure
        assert rig.app.exit_reason == "adventure"
        # The host now resumes the fridge cycle: the established render.
        ctx, wonder_text, _ = demo_weather()
        head = scoring_engine.headline(ctx, ctx["score"])
        ctx["adventure"] = adventures.today(ctx)
        acts = recommendation_engine.recommend(
            ctx, avoid=" ".join((head, wonder_text, ctx["adventure"] or "")))[:2]
        cv = PILCanvas()
        ui_renderer.render(cv, ctx, head, acts, wonder_text)
        rig.cv = cv
        rig.snap("adventure_fridge_screen")
        # Honest empty state: no cached weather.
        empty = Rig(tempfile.mkdtemp(prefix="ta-empty-"), outdir,
                    weather=lambda: (None, None, None))
        x, y, w, h = screens.tile_rect(3)
        empty.tap(x + w // 2, y + h // 2)
        empty.frames = rig.frames
        empty.snap("weather_no_cache")
        contact_sheet(rig.frames, os.path.join(outdir, "sequence.png"))
        paper_overview(os.path.join(outdir, "paper_overview.png"))
        print("preview: %d frames + sequence.png + paper_overview.png in %s"
              % (len(rig.frames), outdir))
        return rig.frames
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--edition" in args:
        i = args.index("--edition")
        EDITION = load_edition(args[i + 1])
        del args[i:i + 2]
    run(args[0] if args else os.path.join(ROOT, "preview"))
