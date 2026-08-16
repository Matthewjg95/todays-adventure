# -*- coding: utf-8 -*-
"""
v3 scene: "cloudy" -- VIADUCT VALLEY
Flat-shade layered landscape for the M5Paper (540x320, mode L).
A five-arch stone viaduct spans the valley between two hills; a tiny steam
train is just crossing from the left, puffing back over the hillside.
Whitewashed cottage on the left hill, drystone-walled sheep pasture on the
right with a shepherd and dog, country lane through one arch, a stream
through another. Soft gray day: layered flat-bottom clouds, no sun.

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
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\cloudy.png"
SEED = 31
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK     = 60    # darkest line work
FG      = 96    # foreground meadow band
FG_DK   = 66
FG_LT   = 124
HILL    = 178   # flanking hills
HILL_TX = 156
HILL_DK = 128
VIA     = 155   # viaduct masonry
VIA_LT  = 176   # parapet
RING    = 72    # arch ring stones
FAR     = 212   # distant valley side (seen through arches)
FAR_DET = 192
MID     = 184   # nearer valley floor through arches
MID_DET = 164
LANE    = 200
STREAM  = 218
SHEEP   = 238

DECK_T  = 222   # parapet top (just below glyph zone)
DECK_B  = 228
SPRING  = 260   # arch springing line
HWA     = 22    # arch half-width
BOT     = 308   # pier bottoms (hidden by foreground)
VX0, VX1 = 100, 415
ARCHES = [152 + 56 * i for i in range(5)]   # arch centre x

# ================================================================ SKY
def cloud(cx, cy, s, fill):
    lobes = [(-1.5, 0.1, 0.9), (-0.4, -0.5, 1.15), (0.7, -0.2, 1.0), (1.6, 0.2, 0.75)]
    for lx, ly, lr in lobes:
        r = s * lr
        d.ellipse([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r],
                  fill=fill)
    d.rectangle([cx - 2.1 * s, cy + 0.35 * s, cx + 2.2 * s, cy + 0.9 * s], fill=fill)
    d.line([(cx - 2.0 * s, cy + 0.9 * s), (cx + 2.1 * s, cy + 0.9 * s)], fill=150, width=2)

# left panel stack (x extents kept < 158)
cloud(80, 74, 15, 214)
cloud(120, 104, 10, 222)
for wx0, wx1, wy in [(20, 66, 122), (86, 148, 130), (36, 104, 48)]:
    d.line([(wx0, wy), (wx1, wy)], fill=198, width=2)

# right panel stack (x extents kept > 384)
cloud(456, 66, 13, 218)
cloud(497, 98, 9, 224)
for wx0, wx1, wy in [(398, 442, 118), (462, 522, 126), (430, 500, 44)]:
    d.line([(wx0, wy), (wx1, wy)], fill=198, width=2)

# rooks in the right panel
for bx, by in [(392, 140), (406, 133), (418, 144)]:
    d.line([(bx - 4, by), (bx, by - 3), (bx + 4, by)], fill=INK, width=2)

# ================================================================ VIADUCT body
d.rectangle([VX0, DECK_T, VX1, BOT], fill=VIA)

# ---- arch openings: through-view of the valley beyond -----------------
for i, cx in enumerate(ARCHES):
    # opening = semicircle + shaft, filled with the far valley side
    d.pieslice([cx - HWA, SPRING - HWA, cx + HWA, SPRING + HWA], 180, 360, fill=FAR)
    d.rectangle([cx - HWA, SPRING, cx + HWA, BOT - 1], fill=FAR)
    # nearer valley floor inside the opening, wavy divide
    pts = [(x, 268 + 3.0 * math.sin(x * 0.19 + i * 1.9))
           for x in range(cx - HWA, cx + HWA + 1, 3)]
    d.polygon(pts + [(cx + HWA, BOT - 1), (cx - HWA, BOT - 1)], fill=MID)
    # tiny hedge dashes on each plane
    for _ in range(2):
        hx = R.uniform(cx - 16, cx + 12)
        d.line([(hx, 262 + R.uniform(-3, 2)), (hx + R.uniform(4, 8), 262)], fill=FAR_DET, width=1)
    for _ in range(2):
        hx = R.uniform(cx - 16, cx + 12)
        hy = R.uniform(278, 290)
        d.line([(hx, hy), (hx + R.uniform(4, 7), hy)], fill=MID_DET, width=1)
    # soffit shadow under the arch head + inner left shadow
    d.arc([cx - HWA, SPRING - HWA, cx + HWA, SPRING + HWA], 188, 305, fill=112, width=5)
    d.line([(cx - HWA + 2, SPRING + 2), (cx - HWA + 2, 300)], fill=124, width=2)

# stream flows out through arch 1
scx = ARCHES[1]
spts_l, spts_r = [], []
for k in range(9):
    t = k / 8.0
    yy = 268 + t * (BOT - 1 - 268)
    xc = scx + 3.5 * math.sin(t * 3.0)
    hw = 3 + 5 * t
    spts_l.append((xc - hw, yy)); spts_r.append((xc + hw, yy))
d.polygon(spts_l + spts_r[::-1], fill=222)
d.line(spts_l, fill=150, width=1); d.line(spts_r, fill=150, width=1)

# country lane runs out through arch 3
lcx = ARCHES[3]
lpts_l, lpts_r = [], []
for k in range(9):
    t = k / 8.0
    yy = 268 + t * (BOT - 1 - 268)
    xc = lcx + 2.5 * math.sin(t * 2.2 + 1.0)
    hw = 4 + 6 * t
    lpts_l.append((xc - hw, yy)); lpts_r.append((xc + hw, yy))
d.polygon(lpts_l + lpts_r[::-1], fill=206)
d.line(lpts_l, fill=140, width=1); d.line(lpts_r, fill=140, width=1)

# ---- arch rings + voussoirs + pier edges -----------------------------
for cx in ARCHES:
    d.arc([cx - HWA - 4, SPRING - HWA - 4, cx + HWA + 4, SPRING + HWA + 4],
          180, 360, fill=RING, width=3)
    for adeg in range(202, 339, 27):                 # voussoir ticks
        a = math.radians(adeg)
        x1 = cx + math.cos(a) * (HWA + 1); y1 = SPRING + math.sin(a) * (HWA + 1)
        x2 = cx + math.cos(a) * (HWA + 5); y2 = SPRING + math.sin(a) * (HWA + 5)
        d.line([(x1, y1), (x2, y2)], fill=100, width=1)
    d.line([(cx - HWA - 4, SPRING + 2), (cx - HWA - 4, 300)], fill=118, width=1)
    d.line([(cx + HWA + 4, SPRING + 2), (cx + HWA + 4, 300)], fill=118, width=1)

# string course + spandrel stone ticks
d.line([(VX0, 237), (VX1, 237)], fill=120, width=1)
for _ in range(52):
    tx = R.uniform(VX0 + 6, VX1 - 8)
    ty = R.uniform(229, 235)
    d.line([(tx, ty), (tx + R.uniform(3, 7), ty)], fill=R.choice([134, 172]), width=1)
# pier / abutment stone ticks
pier_bands = [(VX0 + 2, ARCHES[0] - HWA - 5)] + \
             [(ARCHES[i] + HWA + 5, ARCHES[i + 1] - HWA - 5) for i in range(4)] + \
             [(ARCHES[4] + HWA + 5, VX1 - 2)]
for bx0, bx1 in pier_bands:
    if bx1 - bx0 < 6:        # slender piers: rings already define them, no ticks
        continue
    for _ in range(6):
        tx = R.uniform(bx0, max(bx0 + 1, bx1 - 4))
        ty = R.uniform(244, 296)
        d.line([(tx, ty), (tx + R.uniform(2, 5), ty)], fill=R.choice([134, 172]), width=1)

# ================================================================ TRAIN (before parapet: wall hides wheels)
# third coach, mostly hidden behind the left hill (drawn later)
d.rectangle([86, 210, 108, 226], fill=68)
# coach 2
d.rectangle([110, 210, 131, 226], fill=68)
for wx in (114, 120, 126):
    d.rectangle([wx, 213, wx + 3, 217], fill=208)
d.line([(131, 220), (136, 220)], fill=INK, width=1)   # coupling
# locomotive: cab + boiler + funnel + dome
d.rectangle([136, 206, 145, 226], fill=INK)
d.rectangle([145, 212, 156, 226], fill=INK)
d.rectangle([151, 203, 154, 212], fill=INK)
d.ellipse([145, 208, 150, 213], fill=INK)
d.rectangle([138, 209, 141, 213], fill=208)           # cab window

# ================================================================ PARAPET (over train wheels)
d.rectangle([VX0, DECK_T, VX1, DECK_B], fill=VIA_LT)
d.line([(VX0, DECK_T), (VX1, DECK_T)], fill=RING, width=2)
d.line([(VX0, DECK_B), (VX1, DECK_B)], fill=110, width=1)
for px in range(VX0 + 4, VX1, 9):                     # coping stones
    d.line([(px, DECK_T + 1), (px, DECK_B - 1)], fill=142, width=1)

# ================================================================ LEFT HILL
lh = [(0, 148), (24, 146), (48, 154), (68, 166), (84, 182), (96, 200),
      (102, 212), (106, 224), (110, 242), (108, 264), (103, 286),
      (98, 306), (94, 320), (0, 320)]
d.polygon(lh, fill=HILL)
d.line(lh[:9], fill=HILL_DK, width=2)                 # crest edge
for _ in range(26):                                   # contour strokes
    sx = R.uniform(4, 96)
    # keep strokes inside the hill: below the crest curve, above y=300
    ymin = 150 + sx * 0.8
    sy = R.uniform(min(ymin, 292), 298)
    d.line([(sx, sy), (sx + R.uniform(5, 10), sy - R.uniform(1, 3))], fill=HILL_TX, width=1)
# gorse clumps
for gx, gy2, gr in [(58, 192, 7), (38, 174, 6), (78, 214, 6)]:
    d.ellipse([gx - gr, gy2 - gr * 0.6, gx + gr, gy2 + gr * 0.6], fill=150)

# --- whitewashed cottage on the slope ---
d.rectangle([34, 184, 64, 206], fill=212)
d.rectangle([34, 184, 64, 206], outline=70)
d.polygon([(30, 184), (49, 168), (68, 184)], fill=78)                 # roof
d.rectangle([55, 163, 60, 175], fill=78)                              # chimney
d.rectangle([37, 194, 44, 206], fill=84)                              # door
d.rectangle([50, 190, 58, 197], fill=90)                              # window
d.line([(54, 190), (54, 197)], fill=212, width=1)
# chimney smoke drifting left
for smx, smy, smr in [(55, 156, 3), (49, 149, 4), (42, 142, 4)]:
    d.ellipse([smx - smr, smy - smr, smx + smr, smy + smr], fill=224)
    d.ellipse([smx - smr, smy - smr, smx + smr, smy + smr], outline=160)
# footpath from the door down the slope (dashed)
ppts = [(46, 207), (52, 214), (60, 222), (69, 231), (78, 241),
        (86, 251), (92, 261), (97, 271)]
for k in range(0, len(ppts) - 1, 2):
    d.line([ppts[k], ppts[k + 1]], fill=200, width=2)

# --- trees on the left hill ---
def oak(bx, base, s, fill):
    d.line([(bx, base), (bx, base - int(2.2 * s))], fill=76, width=3)
    for lx, ly, lr in [(-0.8, -2.6, 1.0), (0.2, -3.1, 1.2), (1.0, -2.5, 0.9)]:
        r = s * lr
        d.ellipse([bx + lx * s - r, base + ly * s - r, bx + lx * s + r, base + ly * s + r],
                  fill=fill)
    d.ellipse([bx - int(0.5 * s), base - int(3.1 * s), bx + int(0.4 * s),
               base - int(2.2 * s)], fill=max(60, fill - 20))

oak(88, 182, 10, 138)
oak(16, 148, 8, 146)

# ================================================================ RIGHT HILL
rh = [(396, 258), (398, 238), (402, 224), (408, 212), (420, 196), (436, 180),
      (456, 166), (478, 155), (500, 148), (520, 144), (540, 142),
      (540, 320), (400, 320)]
d.polygon(rh, fill=HILL)
d.line(rh[:11], fill=HILL_DK, width=2)
for _ in range(26):                                   # contour strokes
    sx = R.uniform(408, 534)
    ymin = 230 - (sx - 408) * 0.55
    sy = R.uniform(max(ymin, 200) + 14, 292)
    d.line([(sx, sy), (sx + R.uniform(5, 10), sy - R.uniform(1, 3))], fill=HILL_TX, width=1)

# drystone field walls running along the slope
d.line([(404, 238), (448, 226), (492, 215), (540, 207)], fill=108, width=2)
d.line([(402, 274), (452, 261), (500, 250), (540, 243)], fill=108, width=2)

# --- scattered sheep between the walls ---
def sheep(sx, sy, s=1.0, flip=False):
    bw, bh = 5 * s, 3.2 * s
    hd = 1 if flip else -1
    d.ellipse([sx - bw, sy - bh, sx + bw, sy + bh], fill=SHEEP, outline=96)
    hx = sx + hd * bw
    d.ellipse([hx - 1.7 * s, sy - 2 * s, hx + 1.7 * s, sy + 1.2 * s], fill=70)
    d.line([(sx - 2 * s, sy + bh), (sx - 2 * s, sy + bh + 3 * s)], fill=70, width=1)
    d.line([(sx + 2.4 * s, sy + bh), (sx + 2.4 * s, sy + bh + 3 * s)], fill=70, width=1)

for k, (sx, sy) in enumerate([(416, 252), (436, 246), (455, 240), (476, 233),
                              (497, 227), (515, 222), (526, 250)]):
    sheep(sx, sy, flip=(k % 3 == 1))
sheep(444, 257, 0.7)                                   # lamb
sheep(430, 285, 1.25, flip=True)                       # two nearer sheep
sheep(472, 279, 1.2)

# --- shepherd + dog, watching the train go by ---
d.ellipse([449, 252, 455, 258], fill=INK)              # head
d.line([(452, 258), (452, 269)], fill=INK, width=3)    # coat
d.line([(452, 260), (446, 255)], fill=INK, width=2)    # arm raised at train
d.line([(450, 269), (449, 275)], fill=INK, width=2)    # legs
d.line([(454, 269), (455, 275)], fill=INK, width=2)
d.line([(458, 256), (458, 272)], fill=132, width=1)    # crook
d.arc([455, 253, 461, 259], 180, 340, fill=132, width=1)
d.ellipse([463, 267, 470, 272], fill=INK)              # dog body
d.ellipse([468, 264, 472, 268], fill=INK)              # head, looking up at shepherd
d.line([(464, 272), (464, 275)], fill=INK, width=1)    # legs
d.line([(468, 272), (468, 275)], fill=INK, width=1)
d.line([(463, 269), (460, 267)], fill=INK, width=1)    # tail

# hawthorn + crest tree on the right hill
oak(526, 152, 8, 140)
d.line([(412, 208), (414, 198)], fill=76, width=2)
d.ellipse([408, 192, 420, 201], fill=144)

# --- signal post at the viaduct end ---
d.line([(394, DECK_T), (394, 197)], fill=70, width=2)
d.rectangle([395, 199, 407, 203], fill=70)
d.rectangle([403, 200, 405, 202], fill=220)
# crow perched on the parapet near the right end (outside glyph zone)
d.ellipse([384, 217, 389, 222], fill=INK)
d.line([(389, 219), (392, 218)], fill=INK, width=1)
d.line([(384, 221), (381, 222)], fill=INK, width=1)

# ================================================================ STEAM (after hills: trails over the slope)
# drawn big-to-small so overlaps merge into one plume ending at the funnel
for smx, smy, smr in [(103, 183, 8), (116, 185, 7), (128, 189, 6),
                      (138, 193, 5), (146, 198, 4), (151, 202, 3)]:
    d.ellipse([smx - smr, smy - smr, smx + smr, smy + smr], fill=228)
    d.ellipse([smx - smr, smy - smr, smx + smr, smy + smr], outline=150)

# ================================================================ FOREGROUND meadow band
p1, p2v = R.uniform(0, math.tau), R.uniform(0, math.tau)
def yfg(x):
    return 297 + 4 * math.sin(x / 47.0 + p1) + 3 * math.sin(x / 23.0 + p2v)

fpts = [(x, yfg(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H + 2)] + fpts + [(W, H + 2)], fill=FG)
d.line(fpts, fill=FG_DK, width=2)
for x in range(2, W, 7):                              # crest tufts
    y = yfg(x)
    hgt = R.uniform(3, 6)
    d.line([(x, y), (x - 1, y - hgt)], fill=FG_DK, width=1)
    d.line([(x + 2, y), (x + 3, y - hgt + 1)], fill=FG_DK, width=1)
for _ in range(48):                                   # mixed grass strokes
    gx = R.uniform(3, W - 3)
    gyy = R.uniform(yfg(gx) + 8, H - 4)
    v = FG_LT if R.random() < 0.5 else FG_DK
    d.line([(gx, gyy), (gx + R.uniform(-1, 1), gyy - R.uniform(3, 6))], fill=v, width=1)
for _ in range(18):                                   # wildflower dots
    fx = R.uniform(12, 150) if R.random() < 0.6 else R.uniform(455, 532)
    fy = R.uniform(yfg(fx) + 8, H - 8)
    d.ellipse([fx - 1, fy - 1, fx + 1, fy + 1], fill=240)

# ================================================================ STREAM continues into the foreground
sl, sr = [], []
for k in range(11):
    t = k / 10.0
    yy = yfg(scx) - 3 + t * (H + 2 - (yfg(scx) - 3))
    xc = scx + 24 * t * math.sin(2.4 * t)
    hw = 5 + 10 * t
    sl.append((xc - hw, yy)); sr.append((xc + hw, yy))
d.polygon(sl + sr[::-1], fill=STREAM)
d.line(sl, fill=64, width=1); d.line(sr, fill=64, width=1)
for k in (3, 6, 8):                                   # flow dashes
    (x1, y1), (x2, y2) = sl[k], sr[k]
    d.line([(x1 * 0.6 + x2 * 0.4, y1), (x1 * 0.4 + x2 * 0.6, y1)], fill=185, width=1)
for st in range(3):                                   # stepping stones
    (x1, y1), (x2, y2) = sl[5], sr[5]
    px = x1 + (x2 - x1) * (0.2 + 0.3 * st)
    d.ellipse([px - 2, y1 - 1, px + 2, y1 + 2], fill=230)
# cattails on the banks
for cx2, bb in [(172, 300), (177, 303), (137, 306), (131, 309)]:
    hh = R.uniform(10, 15)
    d.line([(cx2, bb + 6), (cx2 + R.uniform(-2, 2), bb - hh)], fill=INK, width=1)
    d.ellipse([cx2 - 1.5, bb - hh, cx2 + 1.5, bb - hh + 5], fill=INK)
# pair of ducks drifting down the stream
for dxc, dyc in [(219, 306), (231, 313)]:
    d.ellipse([dxc - 3, dyc - 2, dxc + 3, dyc + 1], fill=INK)
    d.ellipse([dxc + 2, dyc - 5, dxc + 5, dyc - 2], fill=INK)
    d.line([(dxc + 5, dyc + 2), (dxc + 10, dyc + 2)], fill=170, width=1)

# ================================================================ LANE continues into the foreground
ll, lr2 = [], []
for k in range(11):
    t = k / 10.0                                      # t=0 at arch, 1 at bottom
    yy = yfg(lcx) - 3 + t * (H + 2 - (yfg(lcx) - 3))
    xc = lcx + 30 * t * math.sin(2.0 * t + 0.4)
    hw = 5 + 13 * t
    ll.append((xc - hw, yy)); lr2.append((xc + hw, yy))
d.polygon(ll + lr2[::-1], fill=LANE)
d.line(ll, fill=128, width=1); d.line(lr2, fill=128, width=1)
for k in range(2, 10, 2):                             # wheel ruts
    (x1, y1), (x2, y2) = ll[k], lr2[k]
    d.line([(x1 * 0.68 + x2 * 0.32, y1), (x1 * 0.66 + x2 * 0.34, y1 + 3)], fill=162, width=1)
    d.line([(x1 * 0.32 + x2 * 0.68, y1), (x1 * 0.34 + x2 * 0.66, y1 + 3)], fill=162, width=1)

# ================================================================ FENCE + GATE across the meadow
WOOD = 190                                            # weathered wood pops on dark grass
def post(px, hgt=13, wdt=2):
    top = yfg(px) + 5
    d.line([(px, top), (px, top + hgt)], fill=WOOD, width=wdt)
    return top

prev = None
for px in list(range(238, 302, 21)) + list(range(372, 452, 21)):
    top = post(px)
    if prev and px - prev[0] <= 23:
        d.line([(prev[0], prev[1] + 3), (px, top + 3)], fill=WOOD, width=1)
        d.line([(prev[0], prev[1] + 8), (px, top + 8)], fill=WOOD, width=1)
    prev = (px, top)
# five-bar gate straddling the lane
gt1 = post(312, 16, 3)
gt2 = post(350, 16, 3)
for fr in (0.15, 0.45, 0.75):
    d.line([(312, gt1 + 16 * fr), (350, gt2 + 16 * fr)], fill=WOOD, width=1)
d.line([(312, gt1 + 14), (350, gt2 + 1)], fill=WOOD, width=1)
# crow on the gate post
d.ellipse([309, gt1 - 6, 314, gt1 - 1], fill=INK)
d.line([(314, gt1 - 4), (317, gt1 - 3)], fill=INK, width=1)
d.line([(309, gt1 - 2), (306, gt1)], fill=INK, width=1)

# milestone by the lane
d.rectangle([358, 297, 365, 308], fill=228, outline=70)
d.pieslice([358, 293, 365, 301], 180, 360, fill=228, outline=70)
d.line([(360, 300), (363, 300)], fill=70, width=1)
d.line([(360, 303), (363, 303)], fill=70, width=1)

# corner bushes
for bx2, by2, brx, bry, v in [(12, 310, 12, 8, 68), (30, 314, 9, 6, 104),
                              (532, 312, 10, 7, 72), (514, 315, 8, 5, 106)]:
    d.ellipse([bx2 - brx, by2 - bry, bx2 + brx, by2 + bry], fill=v)

# ================================================================ BOTTOM FRINGE
def on_water_or_lane(x):
    return 210 <= x <= 238 or 323 <= x <= 357      # stream / lane run off-frame
for x in range(0, W, 3):
    hgt = R.uniform(2, 5) if on_water_or_lane(x) else R.uniform(4, 13)
    v = R.choice([58, 64, 70])
    if on_water_or_lane(x) and R.random() < 0.6:
        continue
    d.line([(x, H), (x + R.uniform(-2, 2), H - hgt)], fill=v, width=1)
for x in range(1, W, 9):
    if on_water_or_lane(x):
        continue
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
