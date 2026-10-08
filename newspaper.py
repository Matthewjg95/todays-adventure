"""Daily Paper: one large fixed newspaper seen through a movable window.

The paper is PAPER_W x PAPER_H pixels, laid out once as a 3 x 3 grid
of article cells under a full-width masthead. The screen shows a
VIEW_W x VIEW_H window onto it; the bottom of the screen is a bar with
the position map. Next/back walk a serpentine reading route
(left-to-right, then right-to-left, then left-to-right), so every step
moves to a neighbouring cell and the two windows share an overlap
band: 80 px sideways, 100 px down. The overlap shows the edge of the
article just read and the head of the next one.

Nothing paper-sized is ever allocated: each frame typesets only the
blocks that intersect the window and draws them translated into the
normal screen buffer.

Content here is a clearly labelled SAMPLE edition. The only live
inputs are the task snapshot (itself a fixture for now), the cached
weather context (shown with its update time, or an explicit "no
weather cached" notice) and the local notebook index.
"""

VIEW_W, VIEW_H = 540, 860           # window onto the paper
BAR_Y = VIEW_H                      # screen rows below this are chrome
SCREEN_H = 960
STEP_X, STEP_Y = 460, 760           # route step; overlap = VIEW - STEP
COLS, ROWS = 3, 3
PAPER_W = VIEW_W + (COLS - 1) * STEP_X      # 1460
PAPER_H = VIEW_H + (ROWS - 1) * STEP_Y      # 2380
MARGIN = 50                         # cell inset inside its window
CELL_W = STEP_X - 2 * MARGIN + 80   # 440: leaves a 30 px neighbour peek
MAST_H = 240                        # masthead band on row 0

LINE = {18: 26, 24: 34, 40: 50, 56: 64}

# Serpentine reading route: (col, row, title)
ROUTE = (
    (0, 0, "Front page"),
    (1, 0, "Engineering"),
    (2, 0, "Project desk"),
    (2, 1, "Adventure & weather"),
    (1, 1, "Engineering, continued"),
    (0, 1, "Notes"),
    (0, 2, "Waiting & later"),
    (1, 2, "Field sketch"),
    (2, 2, "About this edition"),
)


def stop_origin(index):
    col, row, _ = ROUTE[index]
    return col * STEP_X, row * STEP_Y


def clamp_view(x, y):
    return (max(0, min(PAPER_W - VIEW_W, int(x))),
            max(0, min(PAPER_H - VIEW_H, int(y))))


def clamp_stop(index):
    try:
        index = int(index)
    except (TypeError, ValueError):
        return 0
    return max(0, min(len(ROUTE) - 1, index))


def nearest_stop(x, y):
    best, best_d = 0, None
    for i in range(len(ROUTE)):
        sx, sy = stop_origin(i)
        d = (sx - x) ** 2 + (sy - y) ** 2
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best


def overlap(a, b):
    """Shared area (px^2) of two window origins."""
    w = VIEW_W - abs(a[0] - b[0])
    h = VIEW_H - abs(a[1] - b[1])
    return max(0, w) * max(0, h)


def pan_frames(a, b, frames):
    """Intermediate window origins from a to b (exclusive of a, inclusive
    of b). frames=0 means a clean stepped redraw: just [b]."""
    out = []
    n = max(0, int(frames))
    for i in range(1, n + 1):
        f = i / (n + 1)
        # ease-out: big first move, settle gently
        f = 1 - (1 - f) * (1 - f)
        out.append((int(a[0] + (b[0] - a[0]) * f),
                    int(a[1] + (b[1] - a[1]) * f)))
    out.append(b)
    return out


def cell_rect(col, row):
    x = col * STEP_X + MARGIN
    top = row * STEP_Y + (MAST_H + 20 if row == 0 else 30)
    bottom = row * STEP_Y + 750
    return x, top, CELL_W, bottom - top


# --------------------------------------------------------------------------
# Edition content
# --------------------------------------------------------------------------

def _task_lines(snapshot, statuses, limit=6):
    if snapshot is None:
        return ["Task master unavailable."]
    rows = snapshot.tasks(statuses)
    if not rows:
        return ["Nothing here."]
    return ["%s  %s (%s)" % (t["id"], t["title"], t["status"])
            for t in rows[:limit]]


def _weather_items(ctx, wonder_text, adventure):
    if not ctx:
        return [("kicker", "ADVENTURE & WEATHER"),
                ("head", "No weather cached yet", 40),
                ("body", "This Paper has no saved weather update. The next "
                         "scheduled update will fill this panel. Nothing "
                         "here is guessed."),
                ]
    items = [("kicker", "ADVENTURE & WEATHER - LAST UPDATE %s"
              % ctx.get("time_str", "?")),
             ("art", ctx.get("condition", "cloudy")),
             ("head", "%d\xb0 and %s" % (round(ctx["temp"]), ctx["condition"]), 40),
             ("small", "High %d\xb0 / low %d\xb0. Rain chance %d%%. Wind %d mph."
              % (round(ctx["high"]), round(ctx["low"]), ctx["rain_prob"],
                 round(ctx["wind"])))]
    if wonder_text:
        items.append(("body", wonder_text))
    if adventure:
        items.append(("bullets", ["Today's adventure: " + adventure]))
    return items


SAMPLE_TITLES = tuple(t for _, _, t in ROUTE)
NEWS_TITLES = ("Front page", "Top story", "More top stories",
               "Adventure & weather", "World", "Notes", "Waiting & later",
               "Technology", "Local")
SECTION_NAMES = {"top": "TOP STORIES", "world": "WORLD", "tech": "TECHNOLOGY",
                 "local": "LOCAL"}


def route_titles(news=None):
    return NEWS_TITLES if news else SAMPLE_TITLES


def _sources(items):
    names = []
    for it in items:
        if it.get("source") and it["source"] not in names:
            names.append(it["source"])
    return ", ".join(names).upper()


def _news_cell(news, section, lead=False, skip=0, count=None):
    items = (news.get(section) or [])[skip:]
    if count is not None:
        items = items[:count]
    if not items:
        return [("kicker", SECTION_NAMES[section]),
                ("small", "No %s stories in this edition."
                 % SECTION_NAMES[section].lower())]
    out = [("kicker", "%s - %s" % (SECTION_NAMES[section] if not lead
                                   else "TOP STORY" if section == "top"
                                   else SECTION_NAMES[section], _sources(items)))]
    if lead:
        out.append(("head", items[0]["title"], 40))
        if items[0]["summary"]:
            out.append(("body", items[0]["summary"]))
        items = items[1:]
    for it in items:
        out.append(("brief", it["title"], it["summary"]))
    return out


def build_edition(snapshot=None, ctx=None, wonder_text=None, adventure=None,
                  notes=None, date_str=None, news=None, news_label=None,
                  stale=False):
    """Blocks: list of (id, x, y, w, h, items). Positions never depend
    on the content, so the paper keeps its shape edition to edition.

    news: validated edition sections (edition.validate), or None for
    the clearly labelled sample edition."""
    notes = notes or []
    titles = route_titles(news)
    if news:
        box = ("OLDER EDITION" if stale else "TODAY'S EDITION")
        lines = [news_label or "",
                 "Headlines and summaries from public news feeds. "
                 "Full stories are at the source."]
        if stale:
            lines.insert(1, "No newer edition has arrived; news may be out of date.")
    else:
        box = "SAMPLE EDITION"
        lines = ["Not live news. Stories and tasks are sample content."]
    blocks = [("masthead", 0, 0, PAPER_W, MAST_H, [
        ("masthead", date_str or "Undated edition", box, lines, titles[1:6])])]

    task_label = "SAMPLE TASKS (FIXTURE)"
    if snapshot is not None and not snapshot.is_fixture:
        task_label = "FROM YOUR TASK LIST"
    cells = {
        (0, 0): [("kicker", "PRIORITIES - " + task_label),
                 ("head", "Today's short list", 40),
                 ("bullets", _task_lines(snapshot, ("active", "next"))),
                 ("small", "Read from one task master snapshot. The Paper "
                           "never changes a task's status.")],
        (2, 1): _weather_items(ctx, wonder_text, adventure),
        (0, 1): [("kicker", "NOTES - FROM THIS PAPER'S NOTEBOOK"),
                 ("head", "Your pages", 40),
                 ("bullets", notes[:6] or ["No saved notes yet."]),
                 ("small", "Handwriting stays local. Transcription is a "
                           "later, optional step.")],
        (0, 2): [("kicker", "WAITING & LATER - " + task_label),
                 ("head", "Parked, not forgotten", 40),
                 ("bullets", _task_lines(snapshot, ("waiting", "later", "inbox")))],
    }
    if news:
        cells[(1, 0)] = _news_cell(news, "top", lead=True, count=1)
        cells[(2, 0)] = _news_cell(news, "top", skip=1)
        cells[(1, 1)] = _news_cell(news, "world", lead=True)
        cells[(1, 2)] = _news_cell(news, "tech")
        cells[(2, 2)] = _news_cell(news, "local")
        if len(news.get("top") or []) < 2:
            cells[(2, 0)] = [("kicker", "MORE TOP STORIES"),
                             ("small", "Only one top story in this edition.")]
    else:
        cells.update(_SAMPLE_CELLS)
    for (col, row), items in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        x, y, w, h = cell_rect(col, row)
        blocks.append(("c%d%d" % (col, row), x, y, w, h, items))
    return blocks


_SAMPLE_CELLS = {
    (1, 0): [("kicker", "ENGINEERING - SAMPLE ARTICLE"),
             ("head", "The button that waits for a release", 40),
             ("body", "The wheel push also switches this Paper on. "
                      "A Home hold stays shorter than that power-on "
                      "press, and the press that woke the board never "
                      "counts: the button is ignored until released."),
             ("small", "Continued below, two stops on.")],
    (2, 0): [("kicker", "PROJECT DESK - SAMPLE"),
             ("head", "A fridge companion grows a home screen", 40),
             ("body", "Four modules now share one launcher: the "
                      "adventure, this paper, a notebook and the "
                      "weather card. Hold the side button anywhere "
                      "to come home.")],
    (1, 1): [("kicker", "ENGINEERING, CONTINUED"),
             ("head", "Ink first, pixels later", 40),
             ("body", "Pen points are stored the moment they arrive, "
                      "before anything is drawn. A slow e-ink refresh "
                      "can delay the picture, but it cannot drop the "
                      "stroke. Saving writes a temporary file and "
                      "renames it, after checking free flash.")],
    (1, 2): [("kicker", "FIELD SKETCH"),
             ("art", "partly"),
             ("head", "Look up once today", 40),
             ("body", "An illustration slot. Future editions can carry "
                      "the day's scene here.")],
    (2, 2): [("kicker", "ABOUT THIS EDITION"),
             ("head", "Sample edition", 40),
             ("body", "Stories and tasks here are samples, not live "
                      "information. A real edition replaces this once the "
                      "Paper downloads one at a scheduled update."),
             ("small", "Next: short press, wheel or tap the right half. "
                       "Back: wheel or tap the left half. Hold the side "
                       "button for Home.")],
}


# --------------------------------------------------------------------------
# Typesetting (paper coordinates)
# --------------------------------------------------------------------------

def wrap(text, width, size, measure):
    lines, cur = [], ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if not cur or measure(cand, size) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _masthead_ops(item, by, measure):
    _, date_str, box, lines, titles = item
    ops = [("rule", 0, by + 18, PAPER_W, 2, "black"),
           ("text", MARGIN, by + 34, "THE DAILY", 56, "black"),
           ("text", MARGIN, by + 100, "PAPER", 56, "black"),
           ("text", MARGIN, by + 178, date_str.upper(), 18, "gray")]
    ox = STEP_X + MARGIN
    ops.append(("box", ox, by + 42, CELL_W, 64, "black"))
    ops.append(("text", ox + 16, by + 58, box, 24, "black"))
    y = by + 122
    for para in lines:
        for line in wrap(para, CELL_W, 18, measure):
            if y + 18 <= by + MAST_H - 14:
                ops.append(("text", ox, y, line, 18, "gray"))
            y += LINE[18]
    ox = 2 * STEP_X + MARGIN
    ops.append(("text", ox, by + 50, "IN THIS EDITION", 18, "gray"))
    for i, title in enumerate(titles):
        ops.append(("text", ox, by + 78 + i * LINE[18], title, 18, "black"))
    ops.append(("rule", 0, by + MAST_H - 10, PAPER_W, 2, "black"))
    ops.append(("rule", 0, by + MAST_H - 4, PAPER_W, 1, "black"))
    return ops


def _units(item, bx, y, bw, measure):
    """Split one item into units that are kept or dropped whole:
    (ops, y_after, cut_ok). Lines of running text are separate units
    so long text can end early; a brief or bullet stays together."""
    kind = item[0]
    units = []
    if kind == "kicker":
        ops = []
        for line in wrap(item[1], bw, 18, measure):
            ops.append(("text", bx, y, line, 18, "gray"))
            y += LINE[18]
        ops.append(("rule", bx, y + 2, bw, 1, "light"))
        units.append((ops, y + 14, False))
    elif kind == "head":
        size = item[2]
        ops = []
        for line in wrap(item[1], bw, size, measure):
            ops.append(("text", bx, y, line, size, "black"))
            y += LINE[size]
        units.append((ops, y + 8, False))
    elif kind in ("body", "small"):
        size, shade, gap = (24, "black", 12) if kind == "body" else (18, "gray", 10)
        lines = wrap(item[1], bw, size, measure)
        for i, line in enumerate(lines):
            y += LINE[size]
            units.append(([("text", bx, y - LINE[size], line, size, shade)],
                          y + (gap if i == len(lines) - 1 else 0), True))
    elif kind == "bullets":
        for entry in item[1]:
            ops = []
            for i, line in enumerate(wrap(entry, bw - 22, 24, measure)):
                if i == 0:
                    ops.append(("dot", bx + 5, y + 14, None, 4, "black"))
                ops.append(("text", bx + 22, y, line, 24, "black"))
                y += LINE[24]
            y += 6
            units.append((ops, y, False))
        if units:
            units[-1] = (units[-1][0], units[-1][1] + 8, False)
    elif kind == "brief":
        # Headline stays whole; its summary may end early with '...'.
        ops = [("rule", bx, y, 60, 2, "black")]
        y += 10
        for line in wrap(item[1], bw, 24, measure):
            ops.append(("text", bx, y, line, 24, "black"))
            y += LINE[24]
        summary = wrap(item[2] or "", bw, 18, measure)
        units.append((ops, y + (0 if summary else 16), False))
        for i, line in enumerate(summary):
            y += LINE[18]
            units.append(([("text", bx, y - LINE[18], line, 18, "gray")],
                          y + (16 if i == len(summary) - 1 else 0), True))
    elif kind == "art":
        units.append(([("art", bx + bw // 2, y + 80, item[1], 120, "black")],
                      y + 170, False))
    return units


def typeset(block, measure):
    """-> (ops, used_height). ops: (kind, x, y, payload, size, shade).

    Content that would run past the block's bottom is cut at a whole
    line (running text, ending in '...') or a whole story, never drawn
    over the next article."""
    bid, bx, by, bw, bh, items = block
    ops = []
    y = by
    limit = by + bh
    cut_ok_last = False         # previous kept unit was a cuttable text line
    for item in items:
        if item[0] == "masthead":
            ops.extend(_masthead_ops(item, by, measure))
            y = by + MAST_H
            continue
        stop = False
        for unit_ops, y_after, cut_ok in _units(item, bx, y, bw, measure):
            bottom = max([o[2] + o[4] for o in unit_ops if o[0] == "text"] or [y_after])
            if bottom > limit:
                if ops and ops[-1][0] == "text" and cut_ok_last:
                    k, x0, y0, text, size, shade = ops[-1]
                    ops[-1] = (k, x0, y0, _ellipsize(text, bw - (x0 - bx), size, measure),
                               size, shade)
                stop = True
                break
            ops.extend(unit_ops)
            y = y_after
            cut_ok_last = cut_ok
        if stop:
            break
        cut_ok_last = False
    # Column gutter rule on the right edge of each cell (not the last).
    if bid.startswith("c") and bx + bw + 40 < PAPER_W:
        ops.append(("vrule", bx + bw + 15, by, 1, bh, "light"))
    return ops, min(y, limit) - by


def _ellipsize(text, width, size, measure):
    words = text.split()
    while words:
        cand = " ".join(words) + "..."
        if measure(cand, size) <= width:
            return cand
        words.pop()
    return "..."


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

class Paper:
    """An edition plus a typeset cache. One per module open."""

    def __init__(self, blocks, titles=None):
        self.blocks = blocks
        self.titles = tuple(titles or SAMPLE_TITLES)
        self._ops = {}

    def ops_for(self, block, measure):
        cached = self._ops.get(block[0])
        if cached is None:
            cached = typeset(block, measure)[0]
            self._ops[block[0]] = cached
        return cached

    def visible_blocks(self, ox, oy):
        out = []
        for b in self.blocks:
            _, x, y, w, h, _ = b
            if x < ox + VIEW_W and x + w + 40 > ox and y < oy + VIEW_H and y + h > oy:
                out.append(b)
        return out

    def render_window(self, cv, ox, oy):
        """Draw the paper region at (ox, oy) into screen rows 0..VIEW_H."""
        import artwork
        measure = cv.text_width
        for block in self.visible_blocks(ox, oy):
            for kind, x, y, payload, size, shade in self.ops_for(block, measure):
                sx, sy = x - ox, y - oy
                if kind == "text":
                    if sy + size < 0 or sy > VIEW_H or sx > VIEW_W:
                        continue
                    if sx + cv.text_width(payload, size) < 0:
                        continue
                    cv.ink(shade)
                    cv.text(sx, sy, payload, size)
                elif kind == "rule":
                    cv.ink(shade)
                    x0, x1 = max(0, sx), min(VIEW_W, sx + payload)
                    if x1 > x0 and 0 <= sy < VIEW_H:
                        cv.fill_rect(x0, sy, x1 - x0, size)
                elif kind == "vrule":
                    cv.ink(shade)
                    y0, y1 = max(0, sy), min(VIEW_H, sy + size)
                    if y1 > y0 and 0 <= sx < VIEW_W:
                        cv.fill_rect(sx, y0, payload, y1 - y0)
                elif kind == "box":
                    if sx < VIEW_W and sx + payload > 0 and 0 <= sy < VIEW_H:
                        cv.ink(shade)
                        cv.rect(sx, sy, payload, size)
                elif kind == "dot":
                    if 0 <= sy < VIEW_H and 0 <= sx < VIEW_W:
                        cv.ink(shade)
                        cv.fill_circle(sx, sy, size)
                elif kind == "art":
                    if -size < sx < VIEW_W + size and -size < sy < VIEW_H - size // 2:
                        cv.ink(shade)
                        artwork.draw(cv, payload, sx, sy, size)

    def minimap_rects(self, map_x, map_y, scale):
        return [(map_x + b[1] // scale, map_y + b[2] // scale,
                 max(1, b[3] // scale), max(1, b[4] // scale))
                for b in self.blocks]


MAP_SCALE = 28
MAP_W, MAP_H = PAPER_W // MAP_SCALE, PAPER_H // MAP_SCALE     # 52 x 85


def render_bar(cv, paper, stop, ox, oy):
    """Bottom chrome: position, stop title, hints and the map."""
    cv.ink("white")
    cv.fill_rect(0, BAR_Y, VIEW_W, SCREEN_H - BAR_Y)
    cv.ink("black")
    cv.fill_rect(0, BAR_Y, VIEW_W, 2)
    cv.ink("gray")
    label = "TODAY'S EDITION" if paper.titles == NEWS_TITLES else "SAMPLE EDITION"
    cv.text(20, BAR_Y + 10, "%s  -  %d OF %d" % (label, stop + 1, len(ROUTE)), 18)
    cv.ink("black")
    cv.text(20, BAR_Y + 36, paper.titles[stop], 24)
    cv.ink("light")
    cv.text(20, BAR_Y + 70, "< BACK            NEXT >   HOLD: HOME", 18)
    mx, my = VIEW_W - 20 - MAP_W, BAR_Y + 6
    cv.ink("light")
    for (x, y, w, h) in paper.minimap_rects(mx, my, MAP_SCALE):
        cv.fill_rect(x, y, w, h)
    cv.ink("black")
    cv.rect(mx, my, MAP_W, MAP_H)
    vx, vy = mx + ox // MAP_SCALE, my + oy // MAP_SCALE
    vw, vh = VIEW_W // MAP_SCALE, VIEW_H // MAP_SCALE
    cv.rect(vx, vy, vw, vh)
    cv.rect(vx + 1, vy + 1, vw - 2, vh - 2)
