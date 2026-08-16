# -*- coding: utf-8 -*-
"""
v3 scene: "partly" -- FARMSTEAD
Flat-shade layered landscape for the M5Paper (540x320, mode L).
Barn + silo, windmill, curved crop rows on the hill contours, tiny tractor
with crows following the fresh-turned row, windbreak trees, farm pond with
ducks and cattails, dirt track, fence, mailbox.

Contract:
  - glyph zone x 160..380, y 30..220 stays >= 225
  - date strip y 0..28 stays >= 225
  - >=4 distance planes, far lightest -> foreground darkest
  - deterministic (random.Random(SEED))
"""

import math
import random
from PIL import Image, ImageDraw

W, H = 540, 320
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\partly.png"
SEED = 47
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK      = 60    # darkest line work
FG       = 92    # foreground band
FG_DK    = 66
FG_LT    = 118
P3_FILL  = 148   # mid field (crop rows)
ROW      = 104
P2_FILL  = 178   # second plane
P2_TEX   = 158
FAR_FILL = 206   # far ridge
FAR_DET  = 186
WATER    = 214
PATH     = 202

# ---------------------------------------------------------------- ridges
ph = [R.uniform(0, math.tau) for _ in range(8)]

def far(x):  return 232 + 4 * math.sin(x / 95.0 + ph[0]) + 2 * math.sin(x / 41.0 + ph[1])
def p2(x):   return 247 + 5 * math.sin(x / 70.0 + ph[2]) + 2 * math.sin(x / 33.0 + ph[3])
def p3(x):   return 262 + 4 * math.sin(x / 88.0 + ph[4]) + 2 * math.sin(x / 37.0 + ph[5])
def fg(x):   return 300 + 3 * math.sin(x / 60.0 + ph[6]) + 2 * math.sin(x / 28.0 + ph[7])

def ridge_pts(fn, x0=0, x1=W, step=3):
    return [(x, fn(x)) for x in range(x0, x1 + 1, step)]

def fill_band(fn, fill):
    pts = ridge_pts(fn)
    d.polygon([(0, H + 2)] + pts + [(W, H + 2)], fill=fill)

# ================================================================ SKY
# (curation: no sun in the art — the device renders the "partly"
# sun-and-cloud glyph in the center sky, and two suns read wrong)

# --- flat-bottom clouds ---
def cloud(cx, cy, s, fill, outline=None):
    lobes = [(-1.5, 0.1, 0.9), (-0.4, -0.5, 1.15), (0.7, -0.2, 1.0), (1.6, 0.2, 0.75)]
    for lx, ly, lr in lobes:
        r = s * lr
        d.ellipse([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r],
                  fill=fill, outline=outline)
    d.rectangle([cx - 2.1 * s, cy + 0.35 * s, cx + 2.2 * s, cy + 0.9 * s], fill=fill)
    d.line([(cx - 2.0 * s, cy + 0.9 * s), (cx + 2.1 * s, cy + 0.9 * s)], fill=160, width=2)

cloud(86, 84, 14, 218)
cloud(455, 58, 12, 224)

# --- birds (right panel) ---
for bx, by in [(470, 92), (487, 84), (500, 96)]:
    d.line([(bx - 4, by), (bx, by - 3), (bx + 4, by)], fill=INK, width=2)

# ================================================================ PLANE 1: far ridge
fill_band(far, FAR_FILL)
d.line(ridge_pts(far), fill=182, width=1)
# distant farm cluster on the ridge, tucked in the LEFT panel (x < 154)
bx = 112
byl = far(bx)
d.polygon([(bx - 10, byl + 2), (bx - 10, byl - 5), (bx - 5, byl - 9),
           (bx, byl - 5), (bx, byl + 2)], fill=FAR_DET)          # tiny gable
d.rectangle([bx + 3, byl - 11, bx + 7, byl + 2], fill=FAR_DET)   # tiny silo
d.ellipse([bx + 2, byl - 14, bx + 8, byl - 9], fill=FAR_DET)
d.ellipse([bx - 22, byl - 6, bx - 14, byl + 1], fill=FAR_DET)    # hedge blobs
# hedgerow dashes below the ridge line (full width, safely below zone)
for _ in range(26):
    hx = R.uniform(6, W - 6)
    hy = far(hx) + R.uniform(4, 9)
    d.line([(hx, hy), (hx + R.uniform(4, 9), hy)], fill=190, width=1)

# ================================================================ PLANE 2
fill_band(p2, P2_FILL)
d.line(ridge_pts(p2), fill=150, width=1)
for _ in range(46):                                   # light field strokes
    tx = R.uniform(4, W - 8)
    ty = R.uniform(p2(tx) + 3, p3(tx) - 3)
    d.line([(tx, ty), (tx + R.uniform(4, 8), ty)], fill=P2_TEX, width=1)

# --- round hay bales dotting plane 2 ---
for hbx, hbr in ((200, 4), (231, 5), (260, 4)):
    hby = p2(hbx) + 7
    d.ellipse([hbx - hbr - 2, hby + hbr - 2, hbx + hbr + 2, hby + hbr + 2], fill=132)
    d.ellipse([hbx - hbr, hby - hbr, hbx + hbr, hby + hbr], fill=152, outline=118, width=1)
    d.ellipse([hbx - hbr + 2, hby - hbr + 2, hbx + hbr - 2, hby + hbr - 2], outline=126)

# --- windbreak line of trees (right panel, on plane 2) ---
def poplar(cx, h, rx, fill):
    base = p2(cx) + 4
    top = base - h
    d.line([(cx, base), (cx, top + rx)], fill=95, width=3)
    d.ellipse([cx - rx, top, cx + rx, top + int(h * 0.55)], fill=fill)
    d.ellipse([cx - int(rx * 0.82), top + int(h * 0.34), cx + int(rx * 0.82),
               top + int(h * 0.74)], fill=fill)
    d.line([(cx, top + 4), (cx, base - int(h * 0.34))], fill=max(55, fill - 30), width=1)

for cx, h, rx, f in [(444, 78, 13, 152), (466, 92, 15, 144), (490, 84, 14, 156),
                     (513, 96, 15, 146), (533, 74, 12, 158)]:
    poplar(cx, h, rx, f)

# ================================================================ BARN + SILO (left panel)
gy = int(p2(78)) + 7          # barn ground line
# gambrel roof
d.polygon([(24, gy - 62), (38, gy - 92), (74, gy - 110), (110, gy - 92), (124, gy - 62)],
          fill=80)
d.line([(24, gy - 62), (38, gy - 92), (74, gy - 110), (110, gy - 92), (124, gy - 62)],
       fill=INK, width=2)
d.line([(38, gy - 92), (110, gy - 92)], fill=INK, width=1)
# wall
d.rectangle([32, gy - 64, 120, gy], fill=125)
for vx in range(36, 119, 7):                          # plank lines
    d.line([(vx, gy - 62), (vx, gy - 1)], fill=108, width=1)
d.line([(32, gy - 64), (32, gy), (120, gy), (120, gy - 64)], fill=INK, width=2)
# loft door
d.rectangle([66, gy - 58, 86, gy - 42], fill=72)
d.line([(66, gy - 58), (86, gy - 42)], fill=INK, width=1)
d.line([(66, gy - 42), (86, gy - 58)], fill=INK, width=1)
# main sliding door with X brace
d.rectangle([62, gy - 32, 90, gy], fill=88, outline=INK, width=2)
d.line([(62, gy - 32), (90, gy)], fill=INK, width=2)
d.line([(62, gy), (90, gy - 32)], fill=INK, width=2)
# windows
for wx in (40, 100):
    d.rectangle([wx, gy - 28, wx + 11, gy - 16], fill=208, outline=INK, width=1)
    d.line([(wx + 5, gy - 28), (wx + 5, gy - 16)], fill=INK, width=1)
    d.line([(wx, gy - 22), (wx + 11, gy - 22)], fill=INK, width=1)
# weathervane rooster on the peak
d.line([(74, gy - 110), (74, gy - 120)], fill=INK, width=2)
d.line([(68, gy - 118), (80, gy - 118)], fill=INK, width=1)
d.ellipse([72, gy - 125, 78, gy - 119], fill=INK)
d.polygon([(72, gy - 124), (68, gy - 127), (72, gy - 120)], fill=INK)
# silo
d.rectangle([126, gy - 96, 152, gy], fill=160)
for hy in range(gy - 88, gy - 4, 11):
    d.line([(126, hy), (152, hy)], fill=132, width=1)
d.line([(130, gy - 90), (130, gy - 4)], fill=182, width=1)   # highlight seam
d.line([(126, gy - 96), (126, gy)], fill=INK, width=2)
d.line([(152, gy - 96), (152, gy)], fill=INK, width=2)
d.pieslice([126, gy - 107, 152, gy - 85], 180, 360, fill=120, outline=INK, width=1)
d.rectangle([137, gy - 111, 141, gy - 104], fill=INK)

# ================================================================ PLANE 3: crop field
fill_band(p3, P3_FILL)
d.line(ridge_pts(p3), fill=118, width=2)
# curved crop rows following the contour, spacing opens toward the viewer
for dy, wdt in [(5, 1), (10, 1), (16, 2), (23, 2), (31, 3), (40, 3), (50, 3)]:
    seg = []
    for x in range(4, W - 3, 4):
        y = p3(x) + dy + 2.0 * math.sin(x / 23.0 + dy)
        if y < fg(x) - 3:
            seg.append((x, y))
        else:
            if len(seg) > 1:
                d.line(seg, fill=ROW, width=wdt)
            seg = []
    if len(seg) > 1:
        d.line(seg, fill=ROW, width=wdt)

# ================================================================ WINDMILL (right, base in plane 3)
wmx = 414
wb = p3(wmx) + 8
d.line([(wmx - 12, wb), (wmx - 2, 154)], fill=85, width=2)
d.line([(wmx + 12, wb), (wmx + 2, 154)], fill=85, width=2)
for fr, yy in [(0.30, 0), (0.58, 0), (0.82, 0)]:
    ly = 154 + (wb - 154) * fr
    lw = 2 + 10 * fr
    d.line([(wmx - lw, ly), (wmx + lw, ly)], fill=85, width=1)
d.rectangle([wmx - 4, 148, wmx + 4, 156], fill=85)
d.line([(wmx, 150), (wmx + 18, 144)], fill=85, width=2)     # tail
d.polygon([(wmx + 14, 140), (wmx + 22, 144), (wmx + 14, 148)], fill=85)
for k in range(8):                                          # fan wheel
    a = k * math.tau / 8 + 0.2
    d.line([(wmx, 148), (wmx + math.cos(a) * 13, 148 + math.sin(a) * 13)], fill=85, width=2)
d.ellipse([wmx - 15, 133, wmx + 15, 163], outline=85, width=2)
d.ellipse([wmx - 2, 146, wmx + 2, 150], fill=INK)

# ================================================================ TRACTOR + crows (storytelling)
tx = 288
ty = p3(tx) + 18
d.line([(tx - 34, ty + 1), (tx + 20, ty + 1)], fill=88, width=3)   # fresh-turned row
d.rectangle([tx - 13, ty - 16, tx + 13, ty - 7], fill=68)          # body
d.polygon([(tx + 13, ty - 16), (tx + 17, ty - 9), (tx + 13, ty - 7)], fill=68)
d.rectangle([tx - 13, ty - 27, tx - 1, ty - 15], fill=68)          # cab
d.rectangle([tx - 10, ty - 24, tx - 4, ty - 18], fill=190)         # cab window
d.ellipse([tx - 9, ty - 23, tx - 5, ty - 19], fill=INK)            # driver
d.line([(tx + 6, ty - 16), (tx + 6, ty - 25)], fill=68, width=2)   # exhaust stack
d.ellipse([tx + 3, ty - 31, tx + 8, ty - 26], fill=170)            # puff
d.ellipse([tx + 8, ty - 35, tx + 12, ty - 31], fill=190)
d.ellipse([tx - 15, ty - 14, tx - 1, ty], fill=INK)                # rear wheel
d.ellipse([tx - 10, ty - 9, tx - 6, ty - 5], fill=150)
d.ellipse([tx + 7, ty - 8, tx + 15, ty], fill=INK)                 # front wheel
# crows swooping down onto the fresh row
for cx, cy in [(tx - 32, ty - 16), (tx - 44, ty - 10)]:
    d.line([(cx - 4, cy), (cx, cy - 3), (cx + 4, cy)], fill=INK, width=2)
d.ellipse([tx - 28, ty - 3, tx - 22, ty + 1], fill=INK)            # crow pecking
d.line([(tx - 22, ty - 2), (tx - 19, ty - 1)], fill=INK, width=1)

# ================================================================ FOREGROUND
fill_band(fg, FG)
d.line(ridge_pts(fg), fill=FG_DK, width=2)
for x in range(2, W, 7):                              # tuft fringe on the crest
    y = fg(x)
    hgt = R.uniform(3, 6)
    d.line([(x, y), (x - 1, y - hgt)], fill=FG_DK, width=1)
    d.line([(x + 2, y), (x + 3, y - hgt + 1)], fill=FG_DK, width=1)
for _ in range(55):                                   # mixed grass strokes
    gx = R.uniform(3, W - 3)
    gyy = R.uniform(fg(gx) + 8, H - 4)
    v = FG_LT if R.random() < 0.5 else FG_DK
    d.line([(gx, gyy), (gx + R.uniform(-1, 1), gyy - R.uniform(3, 6))], fill=v, width=1)

# ================================================================ DIRT TRACK to the barn
lpts, rpts = [], []
for yy in range(H, 250, -6):
    t = (H - yy) / float(H - 250)
    cx = 92 + 20 * math.sin(t * 2.6 + 0.4)
    wd = 26 - 21 * t
    lpts.append((cx - wd, yy))
    rpts.append((cx + wd, yy))
d.polygon(lpts + rpts[::-1], fill=PATH)
d.line(lpts, fill=124, width=1)
d.line(rpts, fill=124, width=1)
for i in range(0, len(lpts) - 1, 2):                  # wheel ruts
    (x1, y1), (x2, y2) = lpts[i], rpts[i]
    d.line([(x1 * 0.68 + x2 * 0.32, y1), (x1 * 0.66 + x2 * 0.34, y1 + 3)], fill=150, width=1)
    d.line([(x1 * 0.32 + x2 * 0.68, y1), (x1 * 0.34 + x2 * 0.66, y1 + 3)], fill=150, width=1)

# mailbox by the track
d.line([(122, 312), (122, 299)], fill=INK, width=2)
d.rectangle([116, 293, 129, 300], fill=70, outline=INK)
d.line([(127, 293), (127, 288)], fill=INK, width=1)

# ================================================================ POND + ducks + cattails
d.ellipse([400, 297, 514, 319], fill=WATER, outline=90, width=2)
d.line([(418, 306), (448, 306)], fill=176, width=1)
d.line([(458, 312), (494, 312)], fill=176, width=1)
for dx, dy2 in [(434, 307), (470, 311)]:              # ducks
    d.ellipse([dx - 3, dy2 - 2, dx + 3, dy2 + 1], fill=INK)
    d.ellipse([dx + 2, dy2 - 5, dx + 5, dy2 - 2], fill=INK)
    d.line([(dx + 5, dy2 + 2), (dx + 10, dy2 + 2)], fill=170, width=1)
for cx2 in (404, 410, 500, 507, 512):                 # cattails
    hh = R.uniform(12, 20)
    bb = 301 if cx2 < 450 else 305
    d.line([(cx2, bb + 8), (cx2 + R.uniform(-2, 2), bb - hh)], fill=INK, width=1)
    d.ellipse([cx2 - 2, bb - hh, cx2 + 2, bb - hh + 7], fill=INK)

# bush cluster, bottom-left
for bx2, by2, brx, bry, v in [(18, 307, 16, 9, 72), (40, 310, 14, 8, 108), (30, 303, 12, 7, 80)]:
    d.ellipse([bx2 - brx, by2 - bry, bx2 + brx, by2 + bry], fill=v)

# ================================================================ FENCE across the yard
prev = None
for px in range(168, 392, 26):
    top = fg(px) - 14
    d.line([(px, top), (px, top + 16)], fill=INK, width=2)
    if prev:
        d.line([(prev[0], prev[1] + 4), (px, top + 4)], fill=INK, width=1)
        d.line([(prev[0], prev[1] + 9), (px, top + 9)], fill=INK, width=1)
    prev = (px, top)

# ================================================================ BOTTOM FRINGE
for x in range(0, W, 3):
    hgt = R.uniform(4, 13)
    v = R.choice([58, 64, 70])
    d.line([(x, H), (x + R.uniform(-2, 2), H - hgt)], fill=v, width=1)
for x in range(1, W, 9):
    d.line([(x, H), (x + 1, H - R.uniform(2, 6))], fill=100, width=1)

# ================================================================ save + verify
img.save(OUT_PATH)

from PIL import Image as _I
img = _I.open(OUT_PATH)
assert img.mode == "L" and img.size == (540, 320)
z = img.crop((160, 30, 380, 220))
assert z.getextrema()[0] >= 225, "glyph zone dirty: %d" % z.getextrema()[0]
t = img.crop((0, 0, 540, 28))
assert t.getextrema()[0] >= 225, "date strip dirty: %d" % t.getextrema()[0]
print("VERIFY OK")
