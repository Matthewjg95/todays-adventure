# clear.py -- "LAKE MORNING" e-ink art scene for M5Paper (540x320, mode L)
# Flat-shade layered landscape, woodcut / vintage-poster feel.
# Contract: glyph zone x160..380 y30..220 stays >=225; date strip y0..28 >=225.
import os
import math
import random
from PIL import Image, ImageDraw

W, H = 540, 320
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_PATH = os.path.join(ROOT, "scenes", "v3", "clear.png")

rng = random.Random(20260815)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------- palette (flat values) ----------------
V_RIDGE1 = 206   # farthest ridge
V_RIDGE2 = 176   # second ridge
V_SHORE  = 148   # far shore treeline band
V_PINE   = 116
V_LAKE   = 226
V_RIPPLE = 203
V_SHINE  = 248
V_FG     = 70    # foreground shore band
V_WOOD   = 138
V_DARK   = 56

WATERLINE = 254
FG_DIP = 304     # deepest foreground top edge (center)

# glyph-safe clamp: for x in [150, 392] nothing above y=223
CL_L, CL_R = 150, 392


def smooth(t):
    return t * t * (3 - 2 * t)


def topline(y_center, y_left, y_right, amp_c, amp_f, phase):
    """Ridge silhouette: flat-ish (clamped) through the glyph span, rising at flanks."""
    pts = []
    for x in range(0, W + 1, 4):
        if x < CL_L:
            t = smooth((CL_L - x) / CL_L)
            base = y_center + (y_left - y_center) * t
            amp = amp_c + (amp_f - amp_c) * t
        elif x > CL_R:
            t = smooth((x - CL_R) / (W - CL_R))
            base = y_center + (y_right - y_center) * t
            amp = amp_c + (amp_f - amp_c) * t
        else:
            base, amp = y_center, amp_c
        y = base + amp * math.sin(x * 0.045 + phase) + 0.5 * amp * math.sin(x * 0.013 + 2.3 * phase)
        pts.append((x, y))
    return pts


def fill_below(pts, val):
    d.polygon(pts + [(W, H + 20), (0, H + 20)], fill=val)


def qbez(p0, p1, p2, n=18):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


# ---------------- sky: birds + wisps (outside glyph margins) ----------------
def bird(x, y, s=7, w=2, v=85):
    d.line([(x - s, y + s * 0.55), (x, y)], fill=v, width=w)
    d.line([(x, y), (x + s, y + s * 0.55)], fill=v, width=w)

bird(96, 52, 8)
bird(133, 40, 6)
bird(447, 62, 8)
bird(476, 80, 5)

d.arc((28, 44, 138, 62), 200, 340, fill=234, width=2)   # thin morning wisp, left
d.arc((402, 96, 508, 112), 200, 340, fill=234, width=2)  # wisp, right

# ---------------- distance plane 1: far ridge ----------------
fill_below(topline(227, 172, 188, 1.0, 7, 0.7), V_RIDGE1)

# ---------------- distance plane 2: nearer ridge ----------------
fill_below(topline(237, 212, 220, 1.4, 6, 2.1), V_RIDGE2)

# ---------------- distance plane 3: far shore treeline ----------------
shore_pts = topline(247, 238, 240, 1.6, 4, 4.4)
fill_below(shore_pts, V_SHORE)
# bumpy treeline lumps along the top of the shore band
for x in range(4, W, 9):
    yy = 247
    for (px, py) in shore_pts:
        if abs(px - x) <= 2:
            yy = py
            break
    r = rng.uniform(3, 6)
    d.ellipse((x - r, yy - r - 1, x + r, yy + r - 1), fill=V_SHORE)
# small pines on far shore (tops kept >= 226 for glyph safety)
for px in [28, 170, 208, 262, 305, 352, 496, 520]:
    h = rng.uniform(15, 21)
    hw = rng.uniform(4.5, 6.5)
    base = 252
    top = base - h
    d.polygon([(px, top), (px - hw, base - h * 0.35), (px + hw, base - h * 0.35)], fill=V_PINE)
    d.polygon([(px, top + h * 0.28), (px - hw * 1.25, base), (px + hw * 1.25, base)], fill=V_PINE)

# ---------------- cabin on the far shore, right flank ----------------
d.rectangle((402, 226, 462, 251), fill=166)                       # front wall
d.polygon([(394, 228), (432, 204), (470, 228)], fill=84)          # gable roof
d.rectangle((408, 233, 420, 251), fill=94)                        # door
d.rectangle((432, 232, 448, 244), fill=242, outline=90, width=1)  # window
d.line([(440, 232), (440, 244)], fill=90, width=1)
d.line([(432, 238), (448, 238)], fill=90, width=1)
d.rectangle((444, 201, 453, 215), fill=100)                       # chimney
d.line(qbez((449, 199), (456, 190), (450, 181)), fill=200, width=2)  # breakfast smoke
d.line(qbez((450, 181), (445, 172), (452, 163)), fill=214, width=2)

# ---------------- the lake ----------------
d.rectangle((0, WATERLINE, 540, FG_DIP + 4), fill=V_LAKE)

# reflections of shore / cabin (dark dashes just under waterline)
for i in range(26):
    x = rng.uniform(6, 534)
    y = rng.uniform(256, 264)
    ln = rng.uniform(4, 11)
    d.line([(x, y), (x + ln, y)], fill=185, width=1)
for i in range(9):
    x = rng.uniform(406, 462)
    y = rng.uniform(258, 274)
    d.line([(x, y), (x + rng.uniform(3, 7), y)], fill=172, width=1)

# sun-shimmer path (light dashes widening toward the viewer)
for yy in range(259, FG_DIP, 4):
    t = (yy - 259) / float(FG_DIP - 259)
    halfw = 12 + 32 * t
    nd = 3 + int(t * 4)
    for i in range(nd):
        cx = 385 + rng.uniform(-halfw, halfw)
        ln = rng.uniform(4, 7) + 14 * t
        d.line([(cx - ln / 2, yy), (cx + ln / 2, yy)], fill=V_SHINE, width=3)

# gentle ripples elsewhere
for i in range(26):
    x = rng.uniform(8, 520)
    y = rng.uniform(260, 300)
    if 340 < x < 432:      # keep the shimmer lane clean-ish
        continue
    ln = rng.uniform(6, 14)
    d.line([(x, y), (x + ln, y)], fill=V_RIPPLE, width=1)

# ---------------- ducks crossing calm water (storytelling) ----------------
def duck(x, y, s=1.0, v=62):
    d.ellipse((x - 8 * s, y - 3.5 * s, x + 7 * s, y + 3.5 * s), fill=v)          # body
    d.polygon([(x - 8 * s, y), (x - 12 * s, y - 4 * s), (x - 6 * s, y - 2 * s)], fill=v)  # tail
    d.ellipse((x + 3 * s, y - 9 * s, x + 10 * s, y - 2 * s), fill=v)             # head
    d.polygon([(x + 9 * s, y - 6 * s), (x + 14 * s, y - 5 * s), (x + 9 * s, y - 3.5 * s)], fill=v)  # beak
    d.line([(x - 17 * s, y + 3 * s), (x - 9 * s, y + 3 * s)], fill=200, width=1)  # wake

duck(110, 267, 1.1)
duck(134, 271, 0.62)
duck(148, 268, 0.62)

# ---------------- foreground shore band (darkest plane) ----------------
fg_keys = [(0, 292), (120, 297), (270, FG_DIP), (410, 298), (540, 291)]

def fg_top(x):
    for i in range(len(fg_keys) - 1):
        x0, y0 = fg_keys[i]
        x1, y1 = fg_keys[i + 1]
        if x0 <= x <= x1:
            t = smooth((x - x0) / (x1 - x0))
            return y0 + (y1 - y0) * t + 2.2 * math.sin(x * 0.09) + 1.2 * math.sin(x * 0.23 + 1)
    return 296

fg_pts = [(x, fg_top(x)) for x in range(0, W + 1, 3)]
fill_below(fg_pts, V_FG)

# grass fringe on top edge of the band
for x in range(0, W, 6):
    yt = fg_top(x)
    for b in range(rng.randint(2, 3)):
        dx = rng.uniform(-2.5, 2.5)
        hh = rng.uniform(4, 9)
        d.line([(x + dx, yt + 2), (x + dx * 1.6, yt - hh)], fill=64, width=1)

# texture strokes inside the band + mottled bottom edge
for i in range(150):
    x = rng.uniform(2, 538)
    y = rng.uniform(fg_top(x) + 4, 318)
    ln = rng.uniform(3, 8)
    ang = rng.uniform(-0.9, -0.3)
    v = rng.choice([50, 55, 92, 102])
    d.line([(x, y), (x + ln * math.cos(ang), y + ln * math.sin(ang))], fill=v, width=1)
for i in range(60):
    x = rng.uniform(0, 540)
    y = rng.uniform(311, 319)
    d.line([(x, y), (x + rng.uniform(2, 6), y + rng.uniform(-2, 2))], fill=48, width=1)

# stones on the shore
for (sx, sy, rx, ry) in [(155, 309, 10, 4), (330, 311, 8, 3.5), (438, 308, 6, 3)]:
    d.ellipse((sx - rx, sy - ry, sx + rx, sy + ry), fill=128, outline=84, width=1)

# ---------------- dock (built structure #1), chunky and readable ----------------
DX0, DY0 = 102, 303
DX1, DY1 = 248, 263

def dock_pt(t):
    return (DX0 + (DX1 - DX0) * t, DY0 + (DY1 - DY0) * t)

deck = [(DX0, DY0 - 7), (DX1, DY1 - 4), (DX1, DY1 + 4), (DX0, DY0 + 7)]
d.polygon(deck, fill=V_WOOD, outline=V_DARK)
d.line([(DX0, DY0 - 7), (DX1, DY1 - 4)], fill=190, width=2)   # sunlit top rail
# plank lines
t = 0.05
while t < 0.99:
    x = DX0 + (DX1 - DX0) * t
    y0 = (DY0 - 7) + ((DY1 - 4) - (DY0 - 7)) * t
    y1 = (DY0 + 7) + ((DY1 + 4) - (DY0 + 7)) * t
    d.line([(x, y0 + 1), (x, y1 - 1)], fill=76, width=1)
    t += 0.08
# posts + ripple rings at their feet (long enough to show against the water)
for tt in (0.42, 0.72, 1.0):
    x, y = dock_pt(tt)
    hw = 3.0 - 0.8 * tt
    ybot = y + 6 + 20 * (1 - 0.35 * tt)
    d.rectangle((x - hw, y + 3, x + hw, ybot), fill=46)
    d.arc((x - 9, ybot - 3, x + 9, ybot + 3), 15, 165, fill=210, width=1)

# ---------------- rowboat tied to the dock (built structure #2) ----------------
hull = [(258, 272), (270, 267), (322, 265), (338, 269), (333, 281),
        (318, 285), (276, 285), (263, 279)]
d.polygon(hull, fill=150, outline=V_DARK)
d.line([(258, 272), (270, 269), (322, 267), (338, 269)], fill=V_DARK, width=2)  # gunwale
d.line([(264, 279), (333, 281)], fill=V_DARK, width=2)                          # hull bottom band
d.line([(280, 269), (279, 284)], fill=V_DARK, width=1)                          # rib
d.line([(306, 267), (306, 284)], fill=V_DARK, width=1)                          # rib
d.line([(270, 273), (330, 271)], fill=76, width=2)                              # oar laid inside
# mooring rope: bow sagging back to the end dock post
d.line(qbez((259, 274), (252, 282), (247, 269)), fill=46, width=2)
# waterline ticks so the hull sits IN the water, plus reflection
d.line([(252, 283), (268, 283)], fill=V_RIPPLE, width=1)
d.line([(326, 284), (344, 284)], fill=V_RIPPLE, width=1)
for i in range(5):
    x = rng.uniform(264, 330)
    y = rng.uniform(289, 296)
    d.line([(x, y), (x + rng.uniform(5, 10), y)], fill=190, width=1)

# ---------------- reed clumps (flora) ----------------
def reeds(bx, by, n, hmax, lean=0.0):
    for i in range(n):
        ox = (i - n / 2) * 2.8 + rng.uniform(-1, 1)
        hh = rng.uniform(hmax * 0.55, hmax)
        tipx = bx + ox + lean * hh + rng.uniform(-2, 2)
        tipy = by - hh
        d.line([(bx + ox, by), (tipx, tipy)], fill=52, width=2)
        if rng.random() < 0.5:
            d.ellipse((tipx - 1.5, tipy - 1, tipx + 1.5, tipy + 7), fill=52)  # cattail head
        if rng.random() < 0.4:
            d.arc((bx + ox - 8, by - hh * 0.7, bx + ox + 8, by), 250, 340, fill=52, width=1)

reeds(86, 302, 5, 34, 0.10)      # between the tree and the dock base
reeds(362, 306, 5, 30, -0.12)
reeds(530, 298, 6, 38, 0.08)

# lily pads near the right reeds
for (lx, ly, lr) in [(496, 296, 6), (508, 301, 5), (484, 302, 4)]:
    d.ellipse((lx - lr, ly - lr * 0.45, lx + lr, ly + lr * 0.45), fill=105)
    d.line([(lx, ly), (lx + lr, ly - lr * 0.3)], fill=V_LAKE, width=2)

# bush on the right shore
d.ellipse((448, 286, 474, 299), fill=106)

# ---------------- fence on the right shore (built structure #3) ----------------
for fx in (482, 502, 522):
    d.rectangle((fx - 1, 272, fx + 2, 295), fill=54)
d.line([(478, 277), (534, 275)], fill=54, width=2)
d.line([(478, 286), (534, 284)], fill=54, width=2)

# ---------------- the big canopy tree, left side ----------------
d.polygon([(45, 318), (61, 318), (56, 202), (50, 202)], fill=60)   # trunk
for lx in (50, 54, 57):
    d.line([(lx, 310), (lx - 1, 226)], fill=46, width=1)           # bark lines
d.polygon([(36, 318), (48, 318), (46, 306)], fill=60)              # root flare
d.polygon([(58, 318), (72, 318), (60, 304)], fill=60)
d.line([(53, 206), (32, 162)], fill=60, width=4)                   # branches
d.line([(53, 204), (80, 156)], fill=60, width=4)
d.line([(55, 210), (98, 178)], fill=60, width=3)
d.line([(98, 178), (120, 148)], fill=60, width=3)

# canopy: heavily overlapped circles -> one merged silhouette
canopy = [(60, 104, 36), (90, 122, 30), (40, 132, 26), (82, 80, 27),
          (110, 100, 26), (114, 126, 23), (32, 106, 22), (70, 146, 24),
          (58, 162, 19), (90, 154, 19), (48, 78, 20)]
for (cx, cy, r) in canopy:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=112)
# shaded underside: chords hugging the lower silhouette (not floating balls)
for (cx, cy, r) in [(52, 158, 17), (84, 152, 16), (106, 130, 14), (34, 128, 13)]:
    d.pieslice((cx - r, cy - r, cx + r, cy + r), 20, 200, fill=86)
# leaf-texture arcs
for i in range(46):
    (cx, cy, r) = canopy[rng.randrange(len(canopy))]
    a = rng.uniform(0, 2 * math.pi)
    rr = rng.uniform(0.2, 0.8) * r
    px, py = cx + rr * math.cos(a), cy + rr * math.sin(a)
    if px > 144:
        continue
    s = rng.uniform(3, 6)
    a0 = rng.uniform(0, 360)
    d.arc((px - s, py - s, px + s, py + s), a0, a0 + 120, fill=74, width=1)

# ---------------- save + verify ----------------
img.save(OUT_PATH)

from PIL import Image
img = Image.open(OUT_PATH)
assert img.mode == "L" and img.size == (540, 320)
z = img.crop((160, 30, 380, 220))
assert z.getextrema()[0] >= 225, "glyph zone dirty: %d" % z.getextrema()[0]
t = img.crop((0, 0, 540, 28))
assert t.getextrema()[0] >= 225, "date strip dirty: %d" % t.getextrema()[0]
print("VERIFY OK")
