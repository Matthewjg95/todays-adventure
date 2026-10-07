"""Handwriting capture, local persistence and export. No hardware here.

A note is an ordered list of strokes; a stroke is the start time plus
flat (x, y, dt_ms) triples, so the order of every point survives and
timing is kept where the clock allows. Notes are JSON files under
NOTES_DIR, written atomically (temp file + rename) after a free-space
check. Failures raise NotebookError with a message short enough to
show on screen; the in-memory note stays dirty so nothing is lost
silently.

Export for a later AI/companion phase: export_bundle() gives the
original strokes, rasterize_pbm() a rendered 1-bit image. Neither
needs a network or an account.
"""

import json
import os

NOTES_DIR = "notes"
FORMAT = "ta-notebook/1"
SPACE_MARGIN = 16 * 1024        # keep this much flash free after a save
MAX_POINTS_PER_STROKE = 4000    # a runaway contact cannot eat the heap


class NotebookError(Exception):
    pass


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def free_bytes(path="."):
    """Free bytes on the filesystem holding path, or None if unknown."""
    try:
        st = os.statvfs(path)
        return st[0] * st[4]        # f_bsize * f_bavail
    except (AttributeError, OSError):
        return None


class Note:
    def __init__(self, note_id, width, height, created=None):
        self.id = note_id
        self.width = width
        self.height = height
        self.created = created
        self.updated = created
        self.strokes = []           # [{"t": epoch|None, "p": [x,y,dt,...]}]
        self.dirty = False
        self._open = None           # stroke being drawn
        self._open_t0 = 0

    # --- capture --------------------------------------------------------
    def begin_stroke(self, x, y, t_ms, wall=None):
        self.end_stroke()
        self._open = {"t": wall, "p": [int(x), int(y), 0]}
        self._open_t0 = t_ms
        self.strokes.append(self._open)
        self.dirty = True

    def add_point(self, x, y, t_ms):
        if self._open is None:
            self.begin_stroke(x, y, t_ms)
            return
        p = self._open["p"]
        if len(p) >= 3 * MAX_POINTS_PER_STROKE:
            return
        p.extend((int(x), int(y), max(0, int(t_ms - self._open_t0))))
        self.dirty = True

    def end_stroke(self):
        self._open = None

    @property
    def drawing(self):
        return self._open is not None

    def undo(self):
        self.end_stroke()
        if not self.strokes:
            return False
        self.strokes.pop()
        self.dirty = True
        return True

    def clear(self):
        self.end_stroke()
        if self.strokes:
            self.strokes = []
            self.dirty = True

    def point_count(self):
        return sum(len(s["p"]) // 3 for s in self.strokes)

    # --- serialization ----------------------------------------------------
    def to_dict(self):
        return {"format": FORMAT, "id": self.id, "w": self.width,
                "h": self.height, "created": self.created,
                "updated": self.updated, "strokes": self.strokes}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict) or d.get("format") != FORMAT:
            raise NotebookError("unknown note format")
        note = cls(d["id"], int(d["w"]), int(d["h"]), d.get("created"))
        note.updated = d.get("updated")
        for s in d.get("strokes", []):
            p = s.get("p") if isinstance(s, dict) else None
            if isinstance(p, list) and len(p) >= 3 and len(p) % 3 == 0:
                note.strokes.append({"t": s.get("t"), "p": [int(v) for v in p]})
        return note


class NotebookStore:
    def __init__(self, root=NOTES_DIR, free_fn=free_bytes):
        self.root = root
        self.free_fn = free_fn

    def _ensure_dir(self):
        if not _exists(self.root):
            try:
                os.mkdir(self.root)
            except OSError:
                raise NotebookError("CANNOT CREATE NOTES FOLDER")

    def path(self, note_id):
        return "%s/%s.json" % (self.root, note_id)

    def list_ids(self):
        try:
            names = os.listdir(self.root)
        except OSError:
            return []
        return sorted(n[:-5] for n in names
                      if n.endswith(".json") and n.startswith("n"))

    def new_id(self):
        top = 0
        for nid in self.list_ids():
            try:
                top = max(top, int(nid[1:]))
            except ValueError:
                pass
        return "n%04d" % (top + 1)

    def save(self, note, now=None):
        """Atomic write. Raises NotebookError; the note stays dirty then."""
        note.end_stroke()
        self._ensure_dir()
        note.updated = now
        data = json.dumps(note.to_dict())
        free = self.free_fn(self.root)
        if free is not None and free < len(data) + SPACE_MARGIN:
            raise NotebookError("STORAGE FULL: %d KB FREE" % (free // 1024))
        final = self.path(note.id)
        temporary = final + ".tmp"
        try:
            with open(temporary, "w") as f:
                f.write(data)
            replace = getattr(os, "replace", None)
            if replace:
                replace(temporary, final)
            else:                       # MicroPython rename won't overwrite
                if _exists(final):
                    os.remove(final)
                os.rename(temporary, final)
        except OSError as e:
            try:
                os.remove(temporary)
            except OSError:
                pass
            raise NotebookError("SAVE FAILED (%s)" % (e,))
        note.dirty = False
        return len(data)

    def load(self, note_id):
        try:
            with open(self.path(note_id)) as f:
                return Note.from_dict(json.load(f))
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise NotebookError("CANNOT OPEN %s (%s)" % (note_id, e))

    def recover_tmp(self):
        """A crash between write and rename leaves only *.json.tmp; keep it
        if the final file is missing and the temp parses."""
        recovered = []
        try:
            names = os.listdir(self.root)
        except OSError:
            return recovered
        for name in names:
            if not name.endswith(".json.tmp"):
                continue
            tmp = "%s/%s" % (self.root, name)
            final = tmp[:-4]
            try:
                if _exists(final):
                    os.remove(tmp)
                    continue
                with open(tmp) as f:
                    Note.from_dict(json.load(f))
                os.rename(tmp, final)
                recovered.append(name[:-9])
            except (OSError, ValueError, NotebookError, KeyError, TypeError):
                pass
        return recovered


# --- export interface (companion service, later phase) --------------------

def export_bundle(note):
    """Original strokes in drawing order, ready for a transcription
    service. Coordinates are canvas pixels; dt is ms since stroke start."""
    return {
        "format": FORMAT,
        "note_id": note.id,
        "canvas": {"width": note.width, "height": note.height},
        "created": note.created,
        "updated": note.updated,
        "strokes": [{"order": i, "started": s["t"],
                     "points": [[s["p"][j], s["p"][j + 1], s["p"][j + 2]]
                                for j in range(0, len(s["p"]), 3)]}
                    for i, s in enumerate(note.strokes)],
        "image": {"type": "image/x-portable-bitmap", "encoding": "P4"},
    }


def _plot(buf, stride, w, h, x, y, r):
    for yy in range(y - r, y + r + 1):
        if 0 <= yy < h:
            row = yy * stride
            for xx in range(x - r, x + r + 1):
                if 0 <= xx < w:
                    buf[row + (xx >> 3)] |= 0x80 >> (xx & 7)


def rasterize_pbm(note, thickness=1):
    """Render the note as a binary PBM (P4): 1 bit per pixel, ink = 1."""
    w, h = note.width, note.height
    stride = (w + 7) // 8
    buf = bytearray(stride * h)
    for s in note.strokes:
        p = s["p"]
        pts = [(p[j], p[j + 1]) for j in range(0, len(p), 3)]
        if len(pts) == 1:
            pts = pts * 2
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            dx, dy = abs(x1 - x0), -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            while True:
                _plot(buf, stride, w, h, x0, y0, thickness)
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    x0 += sx
                if e2 <= dx:
                    err += dx
                    y0 += sy
    return ("P4\n%d %d\n" % (w, h)).encode() + bytes(buf)


class CompanionExporter:
    """The seam for the later phase. `sink(bundle, image_bytes)` is
    whatever transport the companion uses (USB pull, HTTP POST...).
    The prototype's default sink writes two local files."""

    def __init__(self, sink=None, outdir="exports"):
        self.sink = sink
        self.outdir = outdir

    def export(self, note):
        bundle = export_bundle(note)
        image = rasterize_pbm(note)
        if self.sink is not None:
            return self.sink(bundle, image)
        if not _exists(self.outdir):
            os.mkdir(self.outdir)
        base = "%s/%s" % (self.outdir, note.id)
        with open(base + ".strokes.json", "w") as f:
            json.dump(bundle, f)
        with open(base + ".pbm", "wb") as f:
            f.write(image)
        return base
