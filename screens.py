"""Interactive screens: Home launcher, Notebook, Weather card, Paper.

Drawn through the same canvas API as ui_renderer (text, line, rects,
circles, ink shades), so they run on the panel, in the ASCII test
canvas and in the desktop PNG preview. One consistent grayscale
style: black for what you act on, gray for context, pale fills for
large touch targets.
"""

import artwork
import newspaper
import ui_renderer

W, H = 540, 960

# --- Home --------------------------------------------------------------------

MODULES = (
    ("adventure", "Today's Adventure", "Back to the fridge screen"),
    ("paper", "Daily Paper", "Sample edition to explore"),
    ("notebook", "Notebook", "Write or sketch a thought"),
    ("weather", "Weather Flashcard", "Today's weather facts"),
)
TILE_X, TILE_W = 24, W - 48
TILE_Y0, TILE_H, TILE_GAP = 150, 160, 24


def tile_rect(i):
    return TILE_X, TILE_Y0 + i * (TILE_H + TILE_GAP), TILE_W, TILE_H


def hit_tile(x, y):
    for i, m in enumerate(MODULES):
        tx, ty, tw, th = tile_rect(i)
        if tx <= x < tx + tw and ty <= y < ty + th:
            return m[0]
    return None


def _icon(cv, key, cx, cy):
    cv.ink("black")
    if key == "adventure":
        artwork.draw(cv, "partly", cx, cy, 70)
    elif key == "weather":
        artwork.draw(cv, "rain", cx, cy, 70)
    elif key == "paper":
        cv.rect(cx - 30, cy - 36, 60, 72)
        cv.fill_rect(cx - 22, cy - 28, 44, 8)
        for i in range(4):
            cv.line(cx - 22, cy - 8 + i * 10, cx + 22, cy - 8 + i * 10)
    elif key == "notebook":
        cv.rect(cx - 28, cy - 36, 56, 72)
        for i in range(3):
            cv.line(cx - 20, cy - 16 + i * 14, cx + 20, cy - 16 + i * 14)
        cv.line(cx + 6, cy + 30, cx + 34, cy - 4)
        cv.line(cx + 7, cy + 31, cx + 35, cy - 3)


def render_home(cv, date_str, status=None):
    cv.ink("gray")
    ui_renderer._center(cv, 28, (date_str or "").upper(), 18)
    cv.ink("black")
    ui_renderer._center3d(cv, 62, "TODAY'S ADVENTURE", 40, depth=2)
    for i, (key, title, sub) in enumerate(MODULES):
        x, y, w, h = tile_rect(i)
        cv.ink("pale")
        cv.fill_rect(x, y, w, h)
        cv.ink("black")
        cv.rect(x, y, w, h)
        cv.rect(x + 1, y + 1, w - 2, h - 2)
        _icon(cv, key, x + 70, y + h // 2)
        # One title size everywhere; long names take two lines.
        tx = x + 130
        if cv.text_width(title, 40) <= x + w - 12 - tx:
            cv.text(tx, y + 40, title, 40)
            sub_y = y + 100
        else:
            first, second = title.split(" ", 1)
            cv.text(tx, y + 14, first, 40)
            cv.text(tx, y + 62, second, 40)
            sub_y = y + 120
        cv.ink("gray")
        cv.text(tx, sub_y, sub, 18)
    cv.ink("light")
    ui_renderer._center(cv, 890, "TAP A MODULE", 18)
    ui_renderer._center(cv, 916, "HOLD THE SIDE BUTTON ANYWHERE FOR HOME", 18)
    if status:
        _status_bar(cv, status)


def _status_bar(cv, text):
    """Visible, inverted message: failures must not be silent."""
    cv.ink("black")
    cv.fill_rect(0, 838, W, 40)
    cv.ink("white")
    ui_renderer._center(cv, 846, text[:44], 18)
    cv.ink("black")


# --- Notebook ----------------------------------------------------------------

TOOLBAR_H = 96
AREA_Y = 100
AREA_H = 790
BUTTONS = ("new", "undo", "save", "clear")
CONFIRM_BUTTONS = ("confirm_clear", "cancel_clear")


def button_rect(i, n=4):
    w = W // n
    return i * w, 0, w, TOOLBAR_H


def hit_toolbar(x, y, confirming):
    if y >= TOOLBAR_H:
        return None
    names = CONFIRM_BUTTONS if confirming else BUTTONS
    i = min(len(names) - 1, x * len(names) // W)
    return names[i]


def in_writing_area(x, y):
    return 0 <= x < W and AREA_Y <= y < AREA_Y + AREA_H


def render_note_strokes(cv, note):
    cv.ink("black")
    for s in note.strokes:
        p = s["p"]
        if len(p) == 3:
            cv.fill_circle(p[0], p[1] + AREA_Y, 2)
            continue
        for j in range(0, len(p) - 3, 3):
            x0, y0, x1, y1 = p[j], p[j + 1] + AREA_Y, p[j + 3], p[j + 4] + AREA_Y
            cv.line(x0, y0, x1, y1)
            cv.line(x0, y0 + 1, x1, y1 + 1)


def render_notebook(cv, note, confirming=False, status=None, saved=True):
    if confirming:
        labels = ("YES, CLEAR", "KEEP PAGE")
    else:
        labels = ("NEW", "UNDO", "SAVE", "CLEAR")
    n = len(labels)
    for i, label in enumerate(labels):
        x, y, w, h = button_rect(i, n)
        cv.ink("black" if confirming and i == 0 else "pale")
        cv.fill_rect(x + 4, y + 6, w - 8, h - 12)
        cv.ink("black")
        cv.rect(x + 4, y + 6, w - 8, h - 12)
        if confirming and i == 0:
            cv.ink("white")
        tw = cv.text_width(label, 24)
        cv.text(x + (w - tw) // 2, y + 34, label, 24)
    cv.ink("black")
    cv.fill_rect(0, AREA_Y - 2, W, 2)
    # faint writing guides
    cv.ink("pale")
    for gy in range(AREA_Y + 70, AREA_Y + AREA_H, 70):
        cv.line(24, gy, W - 24, gy)
    render_note_strokes(cv, note)
    cv.ink("black")
    cv.fill_rect(0, AREA_Y + AREA_H, W, 2)
    if confirming:
        _status_bar(cv, "CLEAR THIS PAGE? TAP YES OR KEEP")
    elif status:
        _status_bar(cv, status)
    cv.ink("gray")
    if not note.strokes and saved:
        state = "EMPTY PAGE"
    else:
        state = "SAVED" if saved else "NOT SAVED YET"
    footer = "NOTE %s  -  %d STROKES  -  %s" % (
        note.id.upper(), len(note.strokes), state)
    cv.text(20, 906, footer, 18)
    cv.ink("light")
    cv.text(20, 932, "PRESS: SAVE    HOLD: SAVE AND GO HOME", 18)


# --- Weather -----------------------------------------------------------------

def render_weather(cv, ctx, status=None):
    if ctx is None:
        cv.ink("gray")
        ui_renderer._center(cv, 45, "TODAY, IN DETAIL", 18)
        cv.ink("black")
        ui_renderer._center(cv, 360, "No weather cached yet", 40)
        cv.ink("gray")
        for i, line in enumerate(("This Paper has not saved a weather",
                                  "update. Nothing is shown rather",
                                  "than guessed. Press the side button",
                                  "to try fetching one now.")):
            ui_renderer._center(cv, 440 + i * 34, line, 24)
        cv.ink("light")
        ui_renderer._center(cv, 912, "HOLD THE SIDE BUTTON FOR HOME", 18)
    else:
        ui_renderer.render_facts(
            cv, ctx, footer="PRESS: REFRESH    HOLD: HOME", show=False)
        cv.ink("light")
        ui_renderer._center(cv, 156, "FROM THE %s WEATHER UPDATE"
                            % str(ctx.get("time_str", "?")).upper(), 18)
    if status:
        _status_bar(cv, status)


# --- Paper -------------------------------------------------------------------

def render_paper(cv, paper, stop, origin, status=None):
    paper.render_window(cv, origin[0], origin[1])
    newspaper.render_bar(cv, paper, stop, origin[0], origin[1])
    if status:
        _status_bar(cv, status)
