# -*- coding: utf-8 -*-
"""
v3 scene: "severe" -- EXTREME WEATHER, HOMESTEAD ENDURING
Flat-shade layered countryside for the M5Paper (540x320, mode L).
Heavy scud walls press in from both margins with slashing rain; the
center sky stays clean for the storm glyph.  A farmhouse battened down
on the right -- shutters closed, one small lit window.  Trees bowed hard
right, a snapped branch down in the yard, power lines sagging between
leaning poles, one line down.  Dark, held-breath mood.  No people.

Contract:
  - glyph zone x 160..380, y 30..220 stays >= 225
  - date strip y 0..28 stays >= 225
  - >=4 distance planes, far lightest -> foreground darkest
  - deterministic (random.Random(SEED))
"""

import math
import os
import random
from PIL import Image, ImageDraw

W, H = 540, 320
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\severe.png"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
SEED = 13
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK     = 40    # darkest line work / trunks / roof
FORE    = 52    # foreground ground band (darkest plane)
HOUSE   = 96    # farmhouse body
SCUD    = 112   # storm cloud walls in the margins
BAND_D  = 70    # dark cloud streaks
NEARF   = 104   # near field
MIDHILL = 152   # mid hill
FARHILL = 204   # far hill (lightest plane)
RAIN    = 178   # pale slashing rain over dark scud
GLOW    = 250   # the one lit window

# safety fences (glyph zone x160..380 y30..220, date strip y0..28)
LM, RM = 156, 384

# ================================================================ SCUD WALLS
# Solid dark frames from the date strip down to the hill line, with a
# ragged, wind-torn inner edge streaming toward the center.

def scud_wall(inner_pts, box):
    d.polygon(inner_pts, fill=SCUD)
    # dark streak wedges inside, long and horizontal (wind-stretched)
    x0, x1 = box
    for yy, th in [(46, 9), (70, 7), (96, 10), (124, 8), (152, 9), (180, 7), (206, 8)]:
        jag = R.uniform(-4, 4)
        d.polygon([(x0 - 20, yy + jag), (x1, yy - 3 + jag),
                   (x1 - 14, yy + th + jag), (x0 - 20, yy + th + 3 + jag)],
                  fill=BAND_D)

# left wall: ragged inner edge around x 120..154
left_edge = [(0, 31), (154, 31)]
y = 31
edge = []
while y < 228:
    y += R.uniform(12, 22)
    edge.append((R.uniform(116, 154), min(y, 228)))
scud_wall([(0, 31), (150, 31)] + edge + [(0, 228)], (0, 154))

# right wall: ragged inner edge around x 388..426
y = 31
edge = []
while y < 226:
    y += R.uniform(12, 22)
    edge.append((R.uniform(388, 424), min(y, 226)))
scud_wall([(540, 31), (392, 31)] + edge + [(540, 226)],
          (400, 560))

# shred tails torn off the walls into the sky margins (kept off glyph zone)
for x0, y0, ln in [(120, 58, 30), (128, 108, 24), (110, 158, 36), (124, 196, 26)]:
    d.line([(x0, y0), (min(x0 + ln, 154), y0 - 3)], fill=SCUD, width=4)
for x0, y0, ln in [(408, 66, 26), (396, 122, 30), (404, 176, 26)]:
    d.line([(max(x0 - ln, 386), y0 - 3), (x0 + 30, y0)], fill=SCUD, width=4)

# ================================================================ SLASHING RAIN over the scud (pale, hard diagonal)
def rain_band(x_lo, x_hi, y_lo, y_hi, n, fill, wid):
    for _ in range(n):
        x = R.uniform(x_lo, x_hi - 24)
        y = R.uniform(y_lo, y_hi)
        ln = R.uniform(14, 26)
        d.line([(x, y), (x + ln, y + ln / 2.2)], fill=fill, width=wid)

rain_band(2, 150, 36, 200, 34, RAIN, 2)
rain_band(392, 538, 36, 195, 30, RAIN, 2)

# ================================================================ PLANE 1: far hill (lightest)
d.polygon([(0, 233), (60, 227), (150, 231), (260, 226), (360, 230),
           (450, 225), (540, 231), (540, 246), (0, 246)], fill=FARHILL)
d.line([(0, 233), (60, 227), (150, 231), (260, 226), (360, 230),
        (450, 225), (540, 231)], fill=165, width=2)

# ================================================================ PLANE 2: mid hill
d.polygon([(0, 248), (80, 241), (180, 248), (300, 240), (420, 248),
           (540, 241), (540, 264), (0, 264)], fill=MIDHILL)
d.line([(0, 248), (80, 241), (180, 248), (300, 240), (420, 248),
        (540, 241)], fill=104, width=2)

# small distant trees on the mid hill, all bowed the same way
for tx in (52, 246, 332, 366):
    d.line([(tx, 247), (tx + 7, 237)], fill=78, width=3)
    d.ellipse([tx + 1, 230, tx + 23, 240], fill=78)
    d.ellipse([tx + 18, 233, tx + 30, 240], fill=78)

# ================================================================ PLANE 3: near field
d.polygon([(0, 266), (90, 259), (210, 267), (340, 258), (460, 266),
           (540, 259), (540, 290), (0, 290)], fill=NEARF)
d.line([(0, 266), (90, 259), (210, 267), (340, 258), (460, 266),
        (540, 259)], fill=60, width=2)
# leaning fence posts crossing the near field (a run of them, wires gone)
for fx in (178, 214, 252, 292, 330, 362):
    top = 258 + 3 * math.sin(fx / 40.0)
    d.line([(fx, top + 16), (fx + 5, top)], fill=INK, width=3)

# ================================================================ POWER LINES (left, poles leaning hard)
def pole(x, ytop, ybot, lean):
    d.line([(x, ybot), (x + lean, ytop)], fill=INK, width=5)
    xt = x + lean
    d.line([(xt - 11, ytop + 6), (xt + 11, ytop + 6)], fill=INK, width=3)
    return (xt, ytop + 6)

p2 = pole(14, 188, 268, 9)
# second pole snapped off mid-height: splintered stub
d.line([(134, 268), (137, 234)], fill=INK, width=5)
d.line([(133, 236), (137, 228)], fill=INK, width=2)
d.line([(137, 236), (140, 230)], fill=INK, width=2)

def span(a, b, sag, wid=2):
    pts = []
    for i in range(0, 21):
        t = i / 20.0
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t + sag * 4 * t * (1 - t)
        pts.append((x, y))
    d.line(pts, fill=INK, width=wid)

# lines from the standing pole droop all the way to the ground by the
# snapped stub -- the span is down
span((p2[0] - 8, p2[1]), (126, 264), 14)
span((p2[0] + 8, p2[1]), (142, 260), 18)

# ================================================================ FARMHOUSE (right, battened down)
hx = 398
# main body
d.rectangle([hx, 208, hx + 100, 272], fill=HOUSE)
d.rectangle([hx, 208, hx + 100, 272], outline=INK, width=2)
# gable roof with deep windward overhang
d.polygon([(hx - 16, 210), (hx + 46, 174), (hx + 112, 210)], fill=INK)
# chimney -- smoke torn flat sideways the instant it leaves
d.rectangle([hx + 72, 182, hx + 82, 200], fill=INK)
d.line([(hx + 82, 184), (hx + 118, 180)], fill=150, width=3)
d.line([(hx + 86, 189), (hx + 130, 186)], fill=150, width=2)
# shuttered windows: dark, planked
for wx in (hx + 12, hx + 66):
    d.rectangle([wx, 224, wx + 22, 252], fill=INK)
    d.line([(wx + 11, 224), (wx + 11, 252)], fill=96, width=2)
    d.line([(wx, 233), (wx + 22, 233)], fill=96, width=1)
    d.line([(wx, 243), (wx + 22, 243)], fill=96, width=1)
# the one lit window, small, in the gable
d.rectangle([hx + 39, 190, hx + 53, 203], fill=GLOW)
d.rectangle([hx + 39, 190, hx + 53, 203], outline=INK, width=2)
d.line([(hx + 46, 190), (hx + 46, 203)], fill=INK, width=1)
# braced door
d.rectangle([hx + 42, 240, hx + 58, 272], fill=INK)
d.line([(hx + 42, 243), (hx + 58, 269)], fill=110, width=2)
d.line([(hx + 42, 269), (hx + 58, 243)], fill=110, width=2)

# ================================================================ PLANE 4: FOREGROUND ground band (darkest)
def ground_top(x):
    return 290 + 5.0 * math.sin(x / 47.0 + 1.3) + 3.0 * math.sin(x / 19.0 + 4.0)
pts = [(x, ground_top(x)) for x in range(0, W + 1, 4)]
d.polygon([(0, H)] + pts + [(W, H)], fill=FORE)

# ================================================================ BENT TREES (foreground, bowed hard right)
def bent_tree(bx, by, s, canopy=True):
    """Tapered trunk rooted at (bx,by), bowed right; streaming canopy."""
    spine = []
    for i in range(0, 13):
        t = i / 12.0
        x = bx + s * (46 * t * t)
        y = by - s * (66 * t)
        spine.append((x, y))
    # tapered trunk polygon
    left, right = [], []
    for i, (x, yv) in enumerate(spine):
        t = i / 12.0
        w = s * (5.5 * (1 - t) + 1.2)
        left.append((x - w, yv))
        right.append((x + w, yv))
    d.polygon(left + right[::-1], fill=INK)
    tipx, tipy = spine[-1]
    if canopy:
        # single streaming teardrop canopy with a ragged trailing edge
        c = [(tipx - 12 * s, tipy + 2 * s), (tipx - 7 * s, tipy - 11 * s),
             (tipx + 6 * s, tipy - 15 * s), (tipx + 20 * s, tipy - 11 * s),
             (tipx + 33 * s, tipy - 6 * s), (tipx + 42 * s, tipy - 1 * s),
             (tipx + 33 * s, tipy + 1 * s), (tipx + 40 * s, tipy + 5 * s),
             (tipx + 28 * s, tipy + 6 * s), (tipx + 34 * s, tipy + 10 * s),
             (tipx + 19 * s, tipy + 9 * s), (tipx + 5 * s, tipy + 8 * s)]
        d.polygon(c, fill=INK)
    # whipping branches off the lee side
    for t, ln in ((0.5, 18), (0.7, 22), (0.85, 15)):
        i = int(t * 12)
        x0, y0 = spine[i]
        d.line([(x0, y0), (x0 + s * ln, y0 - s * 5)], fill=INK, width=max(2, int(2 * s)))
    # torn leaves streaming downwind of the canopy
    for _ in range(int(7 * s)):
        lx = tipx + s * R.uniform(46, 62)
        ly = tipy + s * R.uniform(-8, 10)
        if lx < 150 or lx > RM:
            d.ellipse([lx, ly, lx + 5, ly + 3], fill=INK)
    return tipx, tipy

# big windward tree, left foreground, drawn over the pole (canopy < x=156)
bent_tree(48, 310, 1.1)
# smaller tree at the right edge, same bow, canopy streaming off-canvas
bent_tree(500, 296, 0.9, canopy=True)

# ================================================================ SNAPPED BRANCH down in the yard (center-bottom)
bx0, by0 = 200, 302
# faint flattened-grass shadow under it
d.ellipse([bx0 - 8, by0 - 4, bx0 + 92, by0 + 8], fill=34)
d.line([(bx0, by0), (bx0 + 84, by0 - 8)], fill=INK, width=6)
d.line([(bx0 + 28, by0 - 3), (bx0 + 54, by0 - 22)], fill=INK, width=4)
d.line([(bx0 + 54, by0 - 5), (bx0 + 76, by0 - 18)], fill=INK, width=3)
d.line([(bx0 + 12, by0 - 2), (bx0 + 26, by0 - 16)], fill=INK, width=3)
# jagged break at the butt
d.line([(bx0, by0), (bx0 - 8, by0 - 9)], fill=INK, width=4)
d.line([(bx0, by0), (bx0 - 5, by0 + 6)], fill=INK, width=3)
# leaves still clinging
for lx, ly in [(252, 281), (266, 288), (240, 284), (274, 285)]:
    d.ellipse([lx, ly, lx + 8, ly + 5], fill=INK)

# ================================================================ WIND-TORN GRASS FRINGE (bottom edge, streaming right)
for x in range(0, W, 4):
    gy = ground_top(x) - R.uniform(0, 3)
    ln = R.uniform(6, 16)
    d.line([(x, gy + 3), (x + ln, gy - ln * 0.4)], fill=FORE, width=2)
# paler grass strokes inside the dark band for texture
for x in range(3, W, 8):
    gy = ground_top(x) + R.uniform(7, 16)
    ln = R.uniform(7, 13)
    d.line([(x, gy), (x + ln, gy - ln * 0.35)], fill=90, width=1)

# ================================================================ flying debris in the margins
for _ in range(9):
    x = R.uniform(8, 138)
    y = R.uniform(232, 262)
    d.line([(x, y), (x + R.uniform(7, 14), y - R.uniform(1, 4))], fill=INK, width=2)
for _ in range(5):
    x = R.uniform(386, 396) if R.random() < 0.4 else R.uniform(504, 526)
    y = R.uniform(230, 252)
    d.line([(x, y), (x + R.uniform(7, 14), y - R.uniform(1, 4))], fill=INK, width=2)

# ================================================================ SAFETY SCRUB: force glyph zone + date strip white
px = img.load()
for y in range(0, 29):
    for x in range(W):
        if px[x, y] < 225:
            px[x, y] = 255
for y in range(29, 223):
    for x in range(158, 383):
        if px[x, y] < 225:
            px[x, y] = 255

img.save(OUT_PATH)

# ================================================================ VERIFY
chk = Image.open(OUT_PATH)
assert chk.mode == "L"
assert chk.size == (540, 320)
assert chk.crop((160, 30, 380, 220)).getextrema()[0] >= 225, "glyph zone dirty"
assert chk.crop((0, 0, 540, 28)).getextrema()[0] >= 225, "date strip dirty"
print("VERIFY OK")
