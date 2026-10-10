"""The interactive companion: Home launcher plus three on-screen modules.

Pure controller. It receives input events, updates state and tells
its host what to draw; it never touches hardware, sleeps or networks
by itself. The device host is session.py; the desktop host is
tools/preview.py. Both call:

    app.open()                 -> first frame
    app.button(event)          -> side button: "press" / "hold"
    app.rocker(+1 / -1)        -> wheel rocked next / back
    app.touch(event)           -> input_events tap/stroke tuples
    app.tick(now_ms)           -> idle check
    app.render(cv)             -> draw the full current screen
    app.take_ink()             -> pen segments drawn since last frame
    app.close(reason)          -> save + persist before leaving

Hold -> Home works from every module and is handled before anything
else, after saving unfinished handwriting. Choosing "Today's
Adventure" (or going idle) sets exit_reason; the host then resumes
the established fridge cycle.
"""

import json
import os

import input_events as ie
import newspaper
import notebook
import screens

STATE_FILE = "app_state.json"
ROCKER_GUARD_MS = 250
MODULES = ("home", "paper", "notebook", "weather")


class Env:
    """What the controller needs from its host. Defaults are inert."""

    def __init__(self, store=None, tasks=None, state_path=STATE_FILE,
                 weather=None, refresh_weather=None, date_str=None,
                 wall_time=None, idle_ms=180000, pan_frames=0, log=None,
                 edition=None):
        self.store = store or notebook.NotebookStore()
        self.tasks = tasks
        self.state_path = state_path
        self.weather = weather or (lambda: (None, None, None))
        self.refresh_weather = refresh_weather
        self.date_str = date_str or (lambda: None)
        self.wall_time = wall_time or (lambda: None)
        self.idle_ms = idle_ms
        self.pan_frames = pan_frames
        self.log = log or (lambda msg: None)
        # -> (sections, label, stale) for a downloaded edition, or None
        self.edition = edition or (lambda: None)


def load_state(path):
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save_state(path, data):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f)
        replace = getattr(os, "replace", None)
        if replace:
            replace(tmp, path)
        else:
            try:
                os.remove(path)
            except OSError:
                pass
            os.rename(tmp, path)
        return True
    except OSError:
        return False


class App:
    def __init__(self, env):
        self.env = env
        self.state = load_state(env.state_path)
        self.module = "home"
        self.status = None
        self.exit_reason = None
        self.frames = []            # pending window origins (paper pans)
        self.needs_frame = True
        self._ink = []
        self._last_input = None
        self.paper = None
        self.stop = newspaper.clamp_stop(self.state.get("paper_stop", 0))
        self.note = None
        self.confirming = False
        self.weather_ctx = None
        self._footer_says_saved = False
        self._last_rocker = None

    # --- lifecycle -------------------------------------------------------
    def open(self, now_ms=0):
        self._last_input = now_ms
        try:
            recovered = self.env.store.recover_tmp()
            if recovered:
                self.env.log("notes recovered from temp: %s" % ",".join(recovered))
        except Exception:
            pass
        self.go("home")

    def go(self, module):
        if module == "adventure":
            self.close("adventure")
            return
        if module not in MODULES:
            return
        if self.module == "notebook" and module != "notebook":
            self._save_note(quiet=True)
        self.confirming = False
        self.module = module
        if module == "paper":
            self._open_paper()
        elif module == "notebook":
            self._open_note()
        elif module == "weather":
            self.weather_ctx = self.env.weather()[0]
        self.frames = []
        self.needs_frame = True
        self._persist()

    def close(self, reason):
        """Leave the interactive session. Unfinished handwriting first."""
        if self.note is not None and self.note.dirty and self.note.strokes:
            self._save_note(quiet=True)
        self._persist()
        self.exit_reason = reason
        self.env.log("session exit: %s" % reason)

    def _persist(self):
        self.state["module"] = self.module
        self.state["paper_stop"] = self.stop
        self.state["paper_view"] = list(newspaper.stop_origin(self.stop))
        if self.note is not None:
            self.state["note_id"] = self.note.id
        if not save_state(self.env.state_path, self.state):
            self.status = "COULD NOT SAVE POSITION"

    # --- input -----------------------------------------------------------
    def _touched(self, now_ms):
        if now_ms is not None:
            self._last_input = now_ms

    def button(self, event, now_ms=None):
        self._touched(now_ms)
        if event == ie.HOLD:
            # Global Home, from everywhere. go() saves unfinished
            # handwriting first; a failed save stays visible on Home.
            if self.module != "notebook":
                self.status = None
            self.go("home")
            return
        if event != ie.PRESS:
            return
        if self.module == "paper":
            self.turn(+1)
        elif self.module == "notebook":
            self._save_note()
        elif self.module == "weather":
            self._refresh_weather()

    def rocker(self, direction, now_ms=None):
        # One physical rock can chatter into several clean presses; a step
        # closer than ROCKER_GUARD_MS to the previous one is contact bounce,
        # not intent (a page turn takes about a second to show anyway).
        if now_ms is not None and self._last_rocker is not None \
                and now_ms - self._last_rocker < ROCKER_GUARD_MS:
            return
        if now_ms is not None:
            self._last_rocker = now_ms
        self._touched(now_ms)
        if self.module == "paper":
            self.turn(direction)

    def touch(self, event, now_ms=None):
        self._touched(now_ms if now_ms is not None else event[3])
        kind, x, y = event[0], event[1], event[2]
        if self.module == "home":
            if kind == ie.TAP:
                target = screens.hit_tile(x, y)
                if target:
                    self.status = None
                    self.go(target)
        elif self.module == "paper":
            if kind == ie.TAP:
                self.slide(+1 if x >= screens.W // 2 else -1)
        elif self.module == "notebook":
            self._note_touch(kind, x, y, event[3])
        elif self.module == "weather":
            pass

    def tick(self, now_ms):
        if self.exit_reason or self._last_input is None:
            return self.exit_reason
        idle = self.env.idle_ms
        if self.module == "notebook" and self.note is not None and self.note.drawing:
            return None                 # pen down: never idle out mid-stroke
        if now_ms - self._last_input >= idle:
            self.close("idle")
        return self.exit_reason

    # --- paper -----------------------------------------------------------
    def _open_paper(self):
        snapshot = None
        if self.env.tasks is not None:
            try:
                snapshot = self.env.tasks.snapshot()
            except Exception as e:
                self.env.log("task snapshot failed: %r" % (e,))
        ctx, wonder_text, adventure = self.env.weather()
        notes = []
        for nid in self.env.store.list_ids()[-6:]:
            notes.append("Note %s" % nid.upper())
        news = label = None
        stale = False
        try:
            got = self.env.edition()
            if got:
                news, label, stale = got
        except Exception as e:
            self.env.log("edition unavailable: %r" % (e,))
        self.paper = newspaper.Paper(newspaper.build_edition(
            snapshot, ctx, wonder_text, adventure, notes, self.env.date_str(),
            news, label, stale), newspaper.route_titles(news))
        self.stop = newspaper.clamp_stop(self.state.get("paper_stop", self.stop))
        view = self.state.get("paper_view")
        if isinstance(view, list) and len(view) == 2:
            # Re-anchor if the route changed since the position was saved.
            x, y = newspaper.clamp_view(view[0], view[1])
            if (x, y) != newspaper.stop_origin(self.stop):
                self.stop = newspaper.nearest_stop(x, y)

    def origin(self):
        return newspaper.stop_origin(self.stop)

    def turn(self, direction):
        target = newspaper.clamp_stop(self.stop + direction)
        if target == self.stop:
            self.status = "END OF EDITION" if direction > 0 else "FRONT PAGE"
            self.needs_frame = True
            return
        self._go_stop(target)

    def slide(self, direction):
        """Sideways to the neighbouring column, same row."""
        target = newspaper.sideways(self.stop, direction)
        if target is None:
            self.status = "RIGHT EDGE OF THE PAGE" if direction > 0 else "LEFT EDGE OF THE PAGE"
            self.needs_frame = True
            return
        self._go_stop(target)

    def _go_stop(self, target):
        a = self.origin()
        self.stop = target
        self.status = None
        self.frames = newspaper.pan_frames(a, self.origin(), self.env.pan_frames)
        self.needs_frame = True
        self._persist()

    # --- notebook --------------------------------------------------------
    def _open_note(self):
        if self.note is not None:
            return
        nid = self.state.get("note_id")
        if nid:
            try:
                self.note = self.env.store.load(nid)
                return
            except notebook.NotebookError as e:
                if nid in self.env.store.list_ids():
                    self.status = str(e)[:44]
        self.note = notebook.Note(nid or self.env.store.new_id(), screens.W,
                                  screens.AREA_H, self.env.wall_time())

    def _save_note(self, quiet=False):
        if self.note is None:
            return True
        if not self.note.dirty:
            if not quiet:
                self.status = "ALREADY SAVED"
                self.needs_frame = True
            return True
        if not self.note.strokes and self.note.id not in self.env.store.list_ids():
            self.note.dirty = False
            return True                  # nothing worth a file
        try:
            size = self.env.store.save(self.note, self.env.wall_time())
            self.env.log("note %s saved: %d strokes, %d bytes"
                         % (self.note.id, len(self.note.strokes), size))
            self.status = None if quiet else "SAVED %s" % self.note.id.upper()
            self.needs_frame = True
            return True
        except notebook.NotebookError as e:
            self.status = str(e)[:44]
            self.env.log("note save failed: %s" % e)
            self.needs_frame = True
            return False

    def _note_touch(self, kind, x, y, t_ms):
        note = self.note
        if kind == ie.TAP and y < screens.TOOLBAR_H:
            action = screens.hit_toolbar(x, y, self.confirming)
            self._note_action(action)
            return
        if kind == ie.STROKE_START and y < screens.AREA_Y:
            return
        if self.confirming and kind in (ie.TAP, ie.STROKE_START):
            self.confirming = False
            self.needs_frame = True
        if not screens.in_writing_area(x, y):
            if kind == ie.STROKE_END:
                note.end_stroke()
            elif kind == ie.STROKE_POINT and note.drawing:
                # Clamp to the edge rather than lose the stroke's path.
                y = max(screens.AREA_Y, min(screens.AREA_Y + screens.AREA_H - 1, y))
                x = max(0, min(screens.W - 1, x))
            else:
                return
        ly = y - screens.AREA_Y
        if kind == ie.TAP:
            note.begin_stroke(x, ly, t_ms, self.env.wall_time())
            note.end_stroke()
            self._ink.append((x, y, x + 1, y))
        elif kind == ie.STROKE_START:
            note.begin_stroke(x, ly, t_ms, self.env.wall_time())
        elif kind == ie.STROKE_POINT and note.drawing:
            p = note.strokes[-1]["p"]
            px, py = p[-3], p[-2] + screens.AREA_Y
            note.add_point(x, ly, t_ms)
            self._ink.append((px, py, x, y))
        elif kind == ie.STROKE_END:
            note.end_stroke()
        if kind in (ie.TAP, ie.STROKE_END) and self._footer_says_saved:
            # The ink fast path never touches the footer; repaint once so
            # the screen stops claiming this page is saved.
            self.needs_frame = True
        if self.status and self.status.startswith("SAVED"):
            self.status = None

    def _note_action(self, action):
        note = self.note
        self.needs_frame = True
        if action == "undo":
            self.status = None if note.undo() else "NOTHING TO UNDO"
        elif action == "save":
            self._save_note()
        elif action == "clear":
            if note.strokes:
                self.confirming = True
            else:
                self.status = "PAGE IS ALREADY EMPTY"
        elif action == "confirm_clear":
            note.clear()
            self.confirming = False
            self.status = "PAGE CLEARED - UNDO NOT AVAILABLE"
        elif action == "cancel_clear":
            self.confirming = False
            self.status = None
        elif action == "new":
            if not self._save_note(quiet=True):
                return                    # keep the unsaved page on screen
            self.note = notebook.Note(self.env.store.new_id(), screens.W,
                                      screens.AREA_H, self.env.wall_time())
            self.status = "NEW PAGE %s" % self.note.id.upper()
            self._persist()

    def take_ink(self):
        ink, self._ink = self._ink, []
        return ink

    # --- weather ---------------------------------------------------------
    def _refresh_weather(self):
        self.needs_frame = True
        if self.env.refresh_weather is None:
            self.status = "REFRESH NOT AVAILABLE HERE"
            return
        try:
            ok = self.env.refresh_weather()
        except Exception as e:
            ok = False
            self.env.log("weather refresh failed: %r" % (e,))
        self.weather_ctx = self.env.weather()[0]
        self.status = None if ok else "REFRESH FAILED - SHOWING CACHE"

    # --- drawing ---------------------------------------------------------
    def render(self, cv, origin=None):
        """Draw the whole current screen into a cleared canvas."""
        self.needs_frame = False
        self._ink = []                   # a full frame includes all ink
        if self.module == "home":
            screens.render_home(cv, self.env.date_str(), self.status)
        elif self.module == "paper":
            screens.render_paper(cv, self.paper, self.stop,
                                 origin or self.origin(), self.status)
        elif self.module == "notebook":
            screens.render_notebook(cv, self.note, self.confirming,
                                    self.status, not self.note.dirty)
            self._footer_says_saved = not self.note.dirty
        elif self.module == "weather":
            screens.render_weather(cv, self.weather_ctx, self.status)
