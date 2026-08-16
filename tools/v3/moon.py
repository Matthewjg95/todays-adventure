# moon.py -- "CITY NIGHT" e-ink art scene for M5Paper (540x320, mode L)
# Skyscrapers on both margins with lit windows, low suspension bridge with
# cable lights, stars in the corners, one shooting star, park ridge with
# two pines and a bench (plus a cat on a boulder watching the sky).
# Contract: glyph zone x160..380 y30..220 stays >=225; date strip y0..28 >=225.
import os
import math
import random
from PIL import Image, ImageDraw

W, H = 540, 320
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_PATH = os.path.join(ROOT, "scenes", "v3", "moon.png")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

rng = random.Random(20260816)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------- palette (flat values) ----------------
V_FARSKY = 208    # distant low skyline
V_FILL = 158      # mid-distance filler blocks
V_RIVER = 196
V_RIPPLE = 174
V_GLOW = 246      # lamps / cable lights / reflections
V_WIN = 238       # lit windows
V_BRIDGE = 58
V_PARK = 54
V_DARKEST = 44

# glyph-safe margins
SAFE_L, SAFE_R = 156, 384  # main towers stay outside these


def smooth(t):
    return t * t * (3 - 2 * t)


# ---------------- sky: stars + one shooting star (drawn first; towers
# painted afterwards simply cover any overlap) ----------------
def sparkle(x, y, s, v=88, diag=False):
    d.line([(x - s, y), (x + s, y)], fill=v, width=1)
    d.line([(x, y - s), (x, y + s)], fill=v, width=1)
    if diag:
        q = s * 0.55
        d.line([(x - q, y - q), (x + q, y + q)], fill=v, width=1)
        d.line([(x - q, y + q), (x + q, y - q)], fill=v, width=1)

# left corner cluster
for (sx, sy, ss, sv) in [(14, 46, 3, 76), (30, 37, 2, 92), (66, 38, 2, 100),
                         (88, 52, 3, 80), (104, 40, 2, 96), (133, 72, 2, 88),
                         (148, 108, 2, 96)]:
    sparkle(sx, sy, ss, sv)
for (sx, sy) in [(8, 70), (46, 41), (120, 60), (152, 90)]:
    d.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=104)

# right corner cluster
for (sx, sy, ss, sv) in [(392, 64, 2, 92), (400, 110, 2, 96), (430, 48, 3, 80),
                         (470, 80, 2, 96), (508, 50, 3, 76), (526, 60, 2, 92),
                         (534, 44, 2, 100)]:
    sparkle(sx, sy, ss, sv)
for (sx, sy) in [(388, 44), (416, 40), (536, 66), (522, 36)]:
    d.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=104)

# shooting star: tapering tail, bright sparkle head, bound lower-right
# (kept clear of tower F's spire and tower H's water tank)
d.line([(444, 33), (470, 45)], fill=140, width=1)
d.line([(470, 45), (491, 53)], fill=92, width=2)
d.line([(442, 38), (456, 44)], fill=182, width=1)   # secondary wisp
d.point((460, 40), fill=140)
d.point((480, 49), fill=140)
sparkle(496, 56, 5, 56, diag=True)

# ---------------- plane 1: distant low skyline across the center ----------
# (tops kept >= 226 so the glyph zone stays clean)
x = 0
far_tops = []
while x < W:
    bw = rng.randint(18, 40)
    top = rng.randint(226, 242)
    d.rectangle((x, top, x + bw, 258), fill=V_FARSKY)
    far_tops.append((x, x + bw, top))
    if rng.random() < 0.4:
        ax = x + rng.randint(4, max(5, bw - 4))
        d.line([(ax, top), (ax, top - 4)], fill=V_FARSKY, width=1)
    x += bw + rng.randint(0, 3)
# sparse tiny lit windows on the distant blocks
for (bx0, bx1, btop) in far_tops:
    for i in range(rng.randint(1, 3)):
        wx = rng.uniform(bx0 + 3, bx1 - 5)
        wy = rng.uniform(btop + 4, 252)
        d.rectangle((wx, wy, wx + 2, wy + 2), fill=V_WIN)

# ---------------- plane 2: the river ----------------
d.line([(0, 255), (540, 255)], fill=150, width=1)   # far shore line
d.rectangle((0, 256, 540, 306), fill=V_RIVER)
for i in range(60):
    rx = rng.uniform(6, 528)
    ry = rng.uniform(259, 300)
    ln = rng.uniform(5, 13)
    d.line([(rx, ry), (rx + ln, ry)], fill=rng.choice([V_RIPPLE, 184, 214]), width=1)
# soft moon-shimmer on the water, below the (on-device) moon
for yy in range(258, 296, 4):
    t = (yy - 258) / 38.0
    halfw = 8 + 28 * t
    for i in range(2 + int(t * 3)):
        cx = 270 + rng.uniform(-halfw, halfw)
        ln = rng.uniform(3, 6) + 9 * t
        d.line([(cx - ln / 2, yy), (cx + ln / 2, yy)], fill=242, width=2)

# ---------------- plane 3: suspension bridge (low, mid-distance) ----------
# cable geometry: control x at midpoints keeps x(t) linear -> easy sampling
def main_cable_y(cx):
    t = (cx - 195.0) / 150.0
    return (1 - t) ** 2 * 226 + 2 * (1 - t) * t * 260 + t * t * 226

def side_cable_y(cx, x0, x2, y0):
    t = (cx - x0) / float(x2 - x0)
    return (1 - t) ** 2 * y0 + 2 * (1 - t) * t * 229 + t * t * 226

# deck (ends tuck behind the margin towers)
d.rectangle((120, 246, 420, 251), fill=V_BRIDGE)
d.line([(120, 246), (420, 246)], fill=132, width=1)
# piers into the water + broken reflections
for px in (195, 345):
    d.rectangle((px - 6, 251, px + 6, 274), fill=52)
    for i in range(3):
        ry = 277 + i * 4
        d.line([(px - 4 + rng.uniform(-2, 2), ry), (px + 4 + rng.uniform(-2, 2), ry)],
               fill=148, width=1)
# pylons (twin legs + crossbars), tops safely below the glyph zone
for px in (195, 345):
    d.rectangle((px - 6, 225, px - 2, 246), fill=48)
    d.rectangle((px + 2, 225, px + 6, 246), fill=48)
    d.rectangle((px - 6, 229, px + 6, 231), fill=48)
    d.rectangle((px - 6, 238, px + 6, 240), fill=48)
# main span cable
pts = [(cx, main_cable_y(cx)) for cx in range(195, 346, 3)]
d.line(pts, fill=48, width=2)
# side span cables
ptsl = [(cx, side_cable_y(cx, 135, 195, 247)) for cx in range(135, 196, 3)]
ptsr = [(cx, side_cable_y(cx, 405, 345, 247)) for cx in range(405, 344, -3)]
d.line(ptsl, fill=48, width=2)
d.line(ptsr, fill=48, width=2)
# suspender cables
for sx in range(207, 334, 12):
    d.line([(sx, main_cable_y(sx)), (sx, 246)], fill=104, width=1)
for sx in range(147, 190, 12):
    d.line([(sx, side_cable_y(sx, 135, 195, 247)), (sx, 246)], fill=104, width=1)
for sx in range(393, 350, -12):
    d.line([(sx, side_cable_y(sx, 405, 345, 247)), (sx, 246)], fill=104, width=1)
# cable lights: bright beads along all three cable runs
bead_xs = []
for bx in range(137, 404, 14):
    if bx < 195:
        by = side_cable_y(bx, 135, 195, 247)
    elif bx <= 345:
        by = main_cable_y(bx)
    else:
        by = side_cable_y(bx, 405, 345, 247)
    d.ellipse((bx - 2, by - 2, bx + 2, by + 2), fill=V_GLOW)
    bead_xs.append(bx)
# deck lamps
for lx in range(152, 400, 25):
    d.line([(lx, 246), (lx, 243)], fill=48, width=1)
    d.ellipse((lx - 1.4, 241.2, lx + 1.4, 244), fill=V_GLOW)
# light reflections dancing under the bridge (center span only)
for bx in bead_xs[::2]:
    if 162 <= bx <= 378:
        ry = 257 + rng.uniform(0, 7)
        d.line([(bx, ry), (bx, ry + rng.uniform(4, 10))], fill=244, width=1)

# ---------------- plane 4: mid-distance filler blocks on the flanks ------
for (fx0, ftop, fx1) in [(28, 162, 62), (108, 150, 140), (0, 178, 20),
                         (398, 172, 430), (468, 166, 504), (522, 182, 540)]:
    d.rectangle((fx0, ftop, fx1, 268), fill=V_FILL)
    for i in range(rng.randint(3, 6)):
        wx = rng.uniform(fx0 + 3, fx1 - 6)
        wy = rng.uniform(ftop + 5, 250)
        d.rectangle((wx, wy, wx + 2, wy + 3), fill=V_WIN)

# ---------------- plane 5: main skyscrapers, both margins ----------------
def windows(x0, y0, x1, y1, gx=7, gy=9, wx=3, wy=4, lit=0.55):
    yy = y0 + 6
    while yy + wy < y1 - 6:
        row_on = rng.random() > 0.18       # occasional dark floor
        xx = x0 + 4
        while xx + wx <= x1 - 3:
            if row_on and rng.random() < lit:
                d.rectangle((xx, yy, xx + wx, yy + wy), fill=V_WIN)
            xx += gx
        yy += gy

# left group ------------------------------------------------------------
d.rectangle((0, 78, 36, 266), fill=90)          # A
windows(0, 78, 36, 266)
d.rectangle((40, 46, 80, 266), fill=74)          # B (tallest left)
windows(40, 46, 80, 266, gx=8, gy=10, lit=0.5)
d.line([(60, 46), (60, 34)], fill=60, width=2)   # antenna
d.ellipse((58.5, 33, 61.5, 36), fill=60)
d.rectangle((86, 100, 120, 266), fill=96)        # C
windows(86, 100, 120, 266, gy=8, wy=3)
# water tank on C's roof
d.rectangle((94, 90, 108, 100), fill=70)
d.polygon([(92, 90), (110, 90), (101, 83)], fill=70)
d.rectangle((124, 132, 156, 266), fill=104)      # D (short, near center)
windows(124, 132, 156, 266, gx=8, lit=0.6)
d.rectangle((132, 124, 148, 132), fill=104)      # stepped crown
d.rectangle((137, 118, 143, 124), fill=104)

# right group -----------------------------------------------------------
d.rectangle((384, 142, 414, 266), fill=100)      # E (short, near center)
windows(384, 142, 414, 266, lit=0.6)
# rooftop billboard on E, glowing face
d.rectangle((388, 118, 410, 133), fill=232, outline=70, width=1)
d.line([(392, 124), (403, 124)], fill=120, width=2)
d.line([(392, 128), (399, 128)], fill=120, width=2)
d.line([(391, 133), (391, 142)], fill=70, width=2)
d.line([(407, 133), (407, 142)], fill=70, width=2)
d.rectangle((418, 58, 458, 266), fill=76)        # F (tallest right)
windows(418, 58, 458, 266, gx=8, gy=10, lit=0.5)
d.polygon([(434, 58), (442, 58), (438, 36)], fill=76)   # spire
d.rectangle((462, 92, 498, 266), fill=88)        # G
windows(462, 92, 498, 266, gy=8, wy=3)
d.rectangle((470, 84, 490, 92), fill=88)         # art-deco crown
d.rectangle((475, 76, 485, 84), fill=88)
d.rectangle((479, 68, 481, 76), fill=88)
d.rectangle((502, 76, 540, 266), fill=94)        # H
windows(502, 76, 540, 266, gx=8, lit=0.55)
d.rectangle((512, 66, 526, 76), fill=68)         # water tank on H
d.polygon([(510, 66), (528, 66), (519, 59)], fill=68)

# waterfront quay under both tower groups + window-light reflections
d.rectangle((0, 266, SAFE_L, 270), fill=96)
d.rectangle((SAFE_R, 266, 540, 270), fill=96)
for qx in [18, 52, 70, 148, 396, 430, 446, 476, 516, 532]:
    ry = 272 + rng.uniform(0, 5)
    d.line([(qx, ry), (qx, ry + rng.uniform(4, 9))], fill=240, width=1)

# little night ferry crossing the river, left flank (extra life)
d.polygon([(112, 282), (140, 282), (136, 288), (116, 288)], fill=66)   # hull
d.rectangle((118, 276, 130, 282), fill=66)                             # cabin
for wx in (120, 124, 128):
    d.rectangle((wx, 278, wx + 1, 280), fill=V_WIN)
d.line([(134, 272), (134, 282)], fill=66, width=1)                     # mast
d.ellipse((133, 270.5, 135.5, 273), fill=V_GLOW)
d.line([(102, 286), (110, 286)], fill=214, width=1)                    # wake
d.line([(142, 285), (150, 285)], fill=214, width=1)

# ---------------- plane 6: the park ridge (darkest foreground) -----------
park_keys = [(0, 297), (90, 293), (180, 289), (270, 286), (360, 289),
             (450, 293), (540, 298)]

def park_top(px):
    for i in range(len(park_keys) - 1):
        x0, y0 = park_keys[i]
        x1, y1 = park_keys[i + 1]
        if x0 <= px <= x1:
            t = smooth((px - x0) / float(x1 - x0))
            return y0 + (y1 - y0) * t + 1.8 * math.sin(px * 0.11) + 1.0 * math.sin(px * 0.31 + 1)
    return 295

park_pts = [(px, park_top(px)) for px in range(0, W + 1, 3)]
d.polygon(park_pts + [(W, H + 20), (0, H + 20)], fill=V_PARK)

# bushes poking above the crest (drawn just after the band so grass and
# props layer over them)
for (bx, by, br) in [(84, 290, 13), (102, 292, 10), (446, 290, 12), (463, 292, 9)]:
    d.ellipse((bx - br, by - br * 0.62, bx + br, by + br * 0.62), fill=50)

# grass fringe along the crest
for gx in range(0, W, 5):
    gy = park_top(gx)
    for b in range(rng.randint(2, 3)):
        dx = rng.uniform(-2, 2)
        hh = rng.uniform(3, 8)
        d.line([(gx + dx, gy + 2), (gx + dx * 1.7, gy - hh)], fill=V_PARK, width=1)

# texture strokes inside the band + mottled bottom fringe (no hard edge)
for i in range(160):
    tx = rng.uniform(2, 538)
    ty = rng.uniform(min(park_top(tx) + 5, 316), 317)
    ln = rng.uniform(3, 8)
    ang = rng.uniform(-1.0, -0.3)
    v = rng.choice([44, 48, 66, 78])
    d.line([(tx, ty), (tx + ln * math.cos(ang), ty + ln * math.sin(ang))], fill=v, width=1)
for i in range(70):
    tx = rng.uniform(0, 540)
    ty = rng.uniform(310, 319)
    d.line([(tx, ty), (tx + rng.uniform(2, 6), ty + rng.uniform(-2, 2))],
           fill=rng.choice([40, 42, 70]), width=1)

# gravel path from the bottom edge up to the bench
path_l = [(238, 320), (247, 310), (252, 300), (259, 292)]
path_r = [(292, 320), (288, 309), (284, 300), (281, 292)]
d.polygon(path_l + path_r[::-1], fill=118)
for i in range(16):
    px = rng.uniform(248, 288)
    py = rng.uniform(295, 318)
    d.point((px, py), fill=88)

# two pines (clear of the bridge pylons at x=195/345)
def pine(cx, tipy, basey, hw, v=48):
    h = basey - tipy
    d.polygon([(cx, tipy), (cx - hw * 0.55, tipy + h * 0.42),
               (cx + hw * 0.55, tipy + h * 0.42)], fill=v)
    d.polygon([(cx, tipy + h * 0.22), (cx - hw * 0.8, tipy + h * 0.68),
               (cx + hw * 0.8, tipy + h * 0.68)], fill=v)
    d.polygon([(cx, tipy + h * 0.45), (cx - hw, basey - 2), (cx + hw, basey - 2)], fill=v)
    d.rectangle((cx - 2, basey - 4, cx + 2, basey + 4), fill=V_DARKEST)

pine(224, 228, 296, 16)
pine(330, 233, 297, 14)

# park bench on the crest, silhouetted against the river
d.rectangle((262, 276, 265, 288), fill=46)   # legs
d.rectangle((285, 276, 288, 288), fill=46)
d.rectangle((258, 272, 292, 276), fill=46)   # seat
d.rectangle((261, 258, 263, 272), fill=46)   # back posts
d.rectangle((287, 258, 289, 272), fill=46)
d.rectangle((258, 259, 292, 261), fill=46)   # slats
d.rectangle((258, 265, 292, 267), fill=46)

# boulder beside the path with the cat on top, whole silhouette on water
d.ellipse((296, 278, 316, 292), fill=86)
d.ellipse((300, 266, 311, 278), fill=V_DARKEST)                    # body
d.ellipse((302, 257, 310, 265), fill=V_DARKEST)                    # head
d.polygon([(302, 259), (303.5, 253.5), (305.5, 258)], fill=V_DARKEST)  # ears
d.polygon([(306.5, 258), (308.5, 253.5), (310, 259.5)], fill=V_DARKEST)
d.line([(310, 275), (316, 279), (317, 286)], fill=V_DARKEST, width=2)  # tail

# park lamppost with a warm glow (right of the boulder)
d.rectangle((361, 254, 363, 292), fill=46)
d.line([(362, 255), (357, 252), (353, 256)], fill=46, width=2)
d.ellipse((349, 255, 357, 263), outline=56, width=1, fill=V_GLOW)
d.ellipse((348, 288, 376, 296), fill=108)     # pool of light on the grass

# reed tuft near the right bushes (flora)
for i in range(5):
    ox = 430 + (i - 2) * 3 + rng.uniform(-1, 1)
    hh = rng.uniform(14, 22)
    d.line([(ox, 295), (ox + rng.uniform(-2, 2), 295 - hh)], fill=48, width=2)
    if rng.random() < 0.6:
        d.ellipse((ox - 1.5, 295 - hh - 5, ox + 1.5, 295 - hh + 1), fill=48)

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
