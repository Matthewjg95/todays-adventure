# -*- coding: utf-8 -*-
"""
v3 scene: "rain" -- RAINY STREET CORNER
Flat-shade layered streetscape for the M5Paper (540x320, mode L).
Shopfront row on the left margin, lamppost + bus shelter on the right,
distant apartment block with a water tank, park wall with railing,
wet-street reflection strokes, puddles with rain rings, a bicycle
leaning on the lamppost with a wrapped parcel on its rack, and a cat
curled up dry on the shelter bench.  Cozy urban rain, no people.

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
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\rain.png"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
SEED = 11
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK      = 60    # darkest line work
ASPHALT  = 96    # foreground street (darkest plane)
CURBFACE = 138
SIDEWALK = 170
JOINT    = 146
WALL_MID = 186   # plane-2 park wall
SHRUB    = 174
SKYLINE  = 212   # plane-1 far roofs
BLOCK    = 220   # distant apartment block
GLASS    = 230
GLOW     = 233
SPILL    = 205
PUDDLE   = 209
REFL_A   = 168   # reflection strokes on asphalt
REFL_S   = 198   # reflection strokes on sidewalk

# ---------------------------------------------------------------- helpers
ph = [R.uniform(0, math.tau) for _ in range(6)]

def sk(x):       # far skyline top edge (center gap) - keep >= 226
    return 233 + 2.0 * math.sin(x / 57.0 + ph[0]) + 1.5 * math.sin(x / 23.0 + ph[1])

def swtop(x):    # sidewalk top edge
    return 252 + 1.5 * math.sin(x / 50.0 + ph[2])

CURB_Y = 281     # curb line; asphalt below

def refl_column(cx, y0, y1, col, seg=(4, 8)):
    """Broken wiggly vertical strokes = wet reflection."""
    y = y0
    while y < y1:
        ln = R.uniform(*seg)
        d.line([(cx + R.uniform(-1.2, 1.2), y),
                (cx + R.uniform(-1.2, 1.2), min(y + ln, y1))], fill=col, width=1)
        y += ln + R.uniform(2, 5)

# ================================================================ SKY: low rain clouds (margins only)
def cloudband(cx, cy, s, fill):
    for lx, ly, lr in [(-1.6, 0.15, 0.8), (-0.5, -0.3, 1.05), (0.7, -0.1, 0.95), (1.7, 0.2, 0.7)]:
        r = s * lr
        d.ellipse([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r], fill=fill)
    d.rectangle([cx - 2.2 * s, cy, cx + 2.3 * s, cy + 0.75 * s], fill=fill)

cloudband(468, 42, 11, 236)     # over the distant block
cloudband(60, 34, 8, 238)       # sliver behind the shop parapet

# ================================================================ PLANE 1a: distant apartment block (right margin)
d.rectangle([400, 118, 538, 262], fill=BLOCK)
d.line([(400, 118), (538, 118)], fill=192, width=2)
d.line([(400, 118), (400, 262)], fill=196, width=1)
# window grid (some lit on the rainy afternoon)
for wy in range(128, 246, 15):
    for wx in range(410, 532, 17):
        lit = R.random() < 0.22
        d.rectangle([wx, wy, wx + 6, wy + 9], fill=238 if lit else 203)
# rooftop water tank + legs
d.line([(500, 118), (503, 104)], fill=196, width=2)
d.line([(524, 118), (521, 104)], fill=196, width=2)
d.rectangle([496, 92, 528, 105], fill=207)
d.polygon([(494, 92), (530, 92), (512, 84)], fill=200)
d.line([(496, 92), (496, 105)], fill=188, width=1)
d.line([(528, 92), (528, 105)], fill=188, width=1)
# antenna
d.line([(420, 118), (420, 96)], fill=196, width=1)
d.line([(415, 101), (425, 101)], fill=196, width=1)
d.line([(416, 108), (424, 108)], fill=196, width=1)

# ================================================================ PLANE 1b: far skyline band (center gap)
pts = [(x, sk(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, 268)] + pts + [(W, 268)], fill=SKYLINE)
d.line(pts, fill=192, width=1)
# tiny roof furniture poking above the band (all tops >= 222)
for cx, wd, hh in [(196, 5, 6), (243, 4, 7), (296, 6, 5), (332, 4, 6), (368, 5, 6)]:
    top = max(sk(cx) - hh, 223)
    d.rectangle([cx - wd // 2, top, cx + wd // 2, sk(cx) + 2], fill=196)
# tiny water tank on the center skyline
d.rectangle([310, 224, 318, 232], fill=196)
d.polygon([(308, 224), (320, 224), (314, 220 + 3)], fill=196)

# ================================================================ PLANE 2: park wall + railing + shrubs (center)
for bx in range(168, 420, 38):     # shrubs behind the railing
    rx = R.uniform(9, 14)
    d.ellipse([bx - rx, 231, bx + rx, 247], fill=SHRUB)
d.rectangle([155, 240, 424, 258], fill=WALL_MID)
d.line([(155, 240), (424, 240)], fill=156, width=2)
for px in range(160, 424, 12):     # railing pickets
    d.line([(px, 233), (px, 240)], fill=150, width=1)
d.line([(158, 233), (422, 233)], fill=150, width=1)

# ================================================================ PLANE 3: sidewalk
swp = [(x, swtop(x)) for x in range(0, W + 1, 4)]
d.polygon([(0, CURB_Y + 2)] + swp + [(W, CURB_Y + 2)], fill=SIDEWALK)
d.line(swp, fill=140, width=1)

# warm shop glow spilling onto the wet sidewalk (drawn before joints)
d.polygon([(14, 254), (78, 254), (96, 280), (2, 280)], fill=SPILL)
d.polygon([(96, 254), (150, 254), (166, 280), (86, 280)], fill=SPILL)

for jx in range(20, W, 34):        # paving joints (converge slightly)
    d.line([(jx, swtop(jx) + 2), (jx - 4, CURB_Y)], fill=JOINT, width=1)
d.line([(255, 262), (300, 268)], fill=JOINT, width=1)   # crack
d.line([(300, 268), (322, 264)], fill=JOINT, width=1)

# ================================================================ PLANE 4: curb + asphalt (darkest)
d.rectangle([0, CURB_Y, W, CURB_Y + 5], fill=CURBFACE)
d.line([(0, CURB_Y), (W, CURB_Y)], fill=70, width=2)
d.rectangle([0, CURB_Y + 5, W, H], fill=ASPHALT)
for _ in range(40):                # asphalt tone dashes
    ax = R.uniform(4, W - 10)
    ay = R.uniform(CURB_Y + 8, H - 4)
    d.line([(ax, ay), (ax + R.uniform(4, 9), ay)], fill=R.choice([92, 112]), width=1)
# dulled lane dashes near the bottom edge
for lx in range(10, W, 58):
    d.line([(lx, 304), (lx + 26, 304)], fill=168, width=3)
# horizontal wet sheen near the curb
for lx in range(14, W, 46):
    d.line([(lx, 288), (lx + R.uniform(12, 22), 288)], fill=148, width=1)

# storm drain grate at the curb (rain gurgling in)
d.rectangle([228, CURB_Y + 6, 262, CURB_Y + 13], fill=70)
for gx in range(232, 260, 6):
    d.line([(gx, CURB_Y + 7), (gx, CURB_Y + 12)], fill=118, width=1)

# ================================================================ wet reflections under everything
for cx in (24, 46, 68, 104, 132):          # shop glow, on the asphalt
    refl_column(cx, CURB_Y + 7, H - 8, REFL_A)
refl_column(397, CURB_Y + 6, H - 6, REFL_A)     # lamppost
refl_column(400, 258, CURB_Y - 1, REFL_S)       # lamppost on sidewalk
for cx in (426, 522):                      # shelter posts
    refl_column(cx, CURB_Y + 6, H - 10, REFL_A)
refl_column(370, CURB_Y + 6, 308, REFL_A)       # bicycle
refl_column(533, CURB_Y + 6, 306, REFL_A)       # bin
# lit shop windows shimmering in the sidewalk spill pools
for cx in (18, 31, 44, 66):
    refl_column(cx, 258, 279, 224, seg=(3, 6))
for cx in (101, 121, 139):
    refl_column(cx, 258, 279, 224, seg=(3, 6))

# ================================================================ puddles + rain rings
def puddle(x0, y0, x1, y1, rings):
    d.ellipse([x0, y0, x1, y1], fill=PUDDLE, outline=84, width=1)
    for _ in range(rings):
        rr = R.uniform(3, 7)
        rcx = R.uniform(x0 + rr + 4, x1 - rr - 4)
        rcy = (y0 + y1) / 2 + R.uniform(-2, 2)
        ry = rr * 0.45
        d.ellipse([rcx - rr, rcy - ry, rcx + rr, rcy + ry], outline=162)
        d.ellipse([rcx - 1, rcy - 1, rcx + 1, rcy + 1], outline=150)

puddle(188, 296, 282, 314, 3)
puddle(300, 303, 374, 317, 2)
puddle(438, 292, 502, 303, 2)
puddle(102, 268, 142, 277, 1)     # small one on the sidewalk

# gutter stream: downpipe water crosses the sidewalk and runs to the drain
d.line([(155, 258), (158, 266), (156, 272), (161, 280)], fill=198, width=2)
d.line([(162, 284), (196, 288), (228, 291)], fill=156, width=2)
for gx in (170, 184, 200):
    d.line([(gx, 286), (gx + 5, 287)], fill=182, width=1)
# paper boat sailing the gutter stream toward the drain
d.polygon([(206, 297), (222, 297), (218, 291), (210, 291)], fill=246)
d.polygon([(210, 291), (218, 291), (214, 283)], fill=246)
d.line([(206, 297), (210, 291), (214, 283), (218, 291), (222, 297), (206, 297)],
       fill=60, width=1)
d.line([(199, 294), (204, 297)], fill=150, width=1)     # wake
d.line([(198, 299), (203, 300)], fill=150, width=1)
d.line([(206, 298), (222, 298)], fill=62, width=1)      # dark waterline
refl_column(214, 300, 312, REFL_A, seg=(2, 4))

# splash ticks on the pavement
for _ in range(14):
    sx = R.uniform(6, W - 6)
    sy = R.uniform(CURB_Y + 8, H - 6)
    d.line([(sx - 2, sy), (sx, sy - 3)], fill=176, width=1)
    d.line([(sx, sy - 3), (sx + 2, sy)], fill=176, width=1)
for _ in range(8):
    sx = R.uniform(160, 420)
    sy = R.uniform(258, 276)
    d.line([(sx - 2, sy), (sx, sy - 3)], fill=142, width=1)
    d.line([(sx, sy - 3), (sx + 2, sy)], fill=142, width=1)

# ================================================================ SHOPFRONT ROW (left margin, x 4..157)
GND = 256
# ---- Shop A (bookshop) x 4..84
d.rectangle([4, 46, 84, GND], fill=132)
for _ in range(26):                 # brick ticks
    bx = R.uniform(7, 80)
    by = R.uniform(50, 126)
    d.line([(bx, by), (bx + R.uniform(3, 6), by)], fill=116, width=1)
d.rectangle([4, 38, 84, 46], fill=88)               # cornice
for tx in range(8, 82, 7):
    d.line([(tx, 40), (tx, 44)], fill=140, width=1)
d.rectangle([16, 32, 28, 38], fill=84)              # chimney on the parapet
d.line([(15, 32), (29, 32)], fill=INK, width=2)
d.line([(4, 38), (84, 38)], fill=INK, width=2)
d.line([(4, 38), (4, GND)], fill=INK, width=2)
# upstairs sash windows: one dark with rain-sky sheen, one lit with a plant
d.rectangle([14, 62, 34, 106], fill=112, outline=INK, width=2)
d.line([(24, 62), (24, 106)], fill=150, width=1)
d.line([(14, 84), (34, 84)], fill=150, width=1)
d.line([(17, 74), (25, 66)], fill=160, width=2)         # sheen
d.line([(20, 80), (30, 70)], fill=160, width=1)
d.rectangle([48, 62, 68, 106], fill=GLOW, outline=INK, width=2)
d.line([(58, 62), (58, 106)], fill=150, width=1)
d.line([(48, 84), (68, 84)], fill=150, width=1)
d.rectangle([51, 97, 58, 105], fill=96)                 # plant pot on the sill
d.line([(54, 97), (54, 89)], fill=96, width=1)
d.line([(54, 92), (50, 88)], fill=96, width=1)
d.line([(54, 94), (58, 89)], fill=96, width=1)
d.line([(14, 108), (34, 108)], fill=88, width=2)        # sills
d.line([(48, 108), (68, 108)], fill=88, width=2)
# sign board
d.rectangle([8, 128, 80, 148], fill=76, outline=INK, width=2)
d.line([(14, 135), (44, 135)], fill=212, width=3)
d.line([(14, 142), (58, 142)], fill=212, width=2)
# awning: stripes + scallops
d.rectangle([6, 152, 82, 170], fill=198)
for i, sxx in enumerate(range(6, 82, 10)):
    if i % 2 == 0:
        d.rectangle([sxx, 152, min(sxx + 10, 82), 170], fill=118)
for i, sxx in enumerate(range(6, 78, 10)):
    col = 118 if i % 2 == 0 else 198
    d.ellipse([sxx, 164, sxx + 11, 177], fill=col)
d.line([(6, 152), (82, 152)], fill=INK, width=2)
# display window (lit) + goods
d.rectangle([10, 186, 52, 244], fill=GLOW, outline=INK, width=2)
d.line([(31, 186), (31, 244)], fill=INK, width=1)
d.line([(10, 214), (52, 214)], fill=150, width=1)   # shelf
for gx, gw, gh in [(14, 5, 9), (22, 4, 7), (36, 6, 10), (45, 4, 8)]:
    d.rectangle([gx, 214 - gh, gx + gw, 214], fill=90)      # books upper shelf
for gx, gw, gh in [(13, 6, 8), (24, 5, 10), (34, 4, 7), (43, 6, 9)]:
    d.rectangle([gx, 244 - gh, gx + gw, 244], fill=90)
# door with lit transom
d.rectangle([58, 178, 78, 186], fill=GLOW, outline=INK, width=1)
d.rectangle([58, 190, 78, GND], fill=96, outline=INK, width=2)
d.rectangle([62, 196, 74, 220], fill=220)
d.ellipse([73, 228, 76, 231], fill=INK)
# planter box + flowers under the window
d.rectangle([10, 246, 52, 254], fill=80)
for fx in range(13, 51, 5):
    fh = R.uniform(4, 8)
    d.line([(fx, 246), (fx + R.uniform(-1, 1), 246 - fh)], fill=104, width=1)
    d.ellipse([fx - 2, 240 - fh + 2, fx + 2, 244 - fh + 2], fill=R.choice([210, 150]))

# ---- alley seam
d.line([(85, 62), (85, GND)], fill=80, width=2)

# ---- Shop B (bakery) x 86..157
d.rectangle([86, 62, 157, GND], fill=148)
d.rectangle([86, 54, 157, 62], fill=92)             # cornice
for tx in range(90, 155, 7):
    d.line([(tx, 56), (tx, 60)], fill=146, width=1)
d.line([(86, 54), (157, 54)], fill=INK, width=2)
d.line([(157, 54), (157, GND)], fill=INK, width=2)
# upstairs window with half-drawn blind
d.rectangle([98, 74, 144, 108], fill=124, outline=INK, width=2)
d.rectangle([100, 76, 142, 88], fill=178)           # blind
d.line([(121, 88), (121, 108)], fill=INK, width=1)
d.line([(98, 98), (144, 98)], fill=INK, width=1)
# sign board
d.rectangle([90, 116, 152, 134], fill=70, outline=INK, width=2)
d.line([(96, 123), (128, 123)], fill=208, width=3)
d.line([(96, 129), (140, 129)], fill=208, width=2)
# awning
d.rectangle([88, 140, 156, 158], fill=190)
for i, sxx in enumerate(range(88, 156, 9)):
    if i % 2 == 0:
        d.rectangle([sxx, 140, min(sxx + 9, 156), 158], fill=104)
for i, sxx in enumerate(range(88, 145, 9)):
    col = 104 if i % 2 == 0 else 190
    d.ellipse([sxx, 152, sxx + 10, 165], fill=col)
d.line([(88, 140), (156, 140)], fill=INK, width=2)
# bakery window: cake stands
d.rectangle([94, 174, 150, 240], fill=228, outline=INK, width=2)
d.line([(94, 210), (150, 210)], fill=150, width=1)
d.ellipse([100, 198, 116, 208], fill=94)            # domed cake
d.line([(98, 208), (118, 208)], fill=70, width=2)
d.rectangle([126, 200, 142, 208], fill=94)          # loaf
d.ellipse([126, 197, 142, 203], fill=94)
d.ellipse([101, 228, 113, 236], fill=94)            # pie below
d.ellipse([124, 226, 134, 234], fill=94)
d.line([(94, 240), (150, 240)], fill=INK, width=2)
d.rectangle([94, 240, 150, GND], fill=110)          # brick base
# potted shrub by the bakery
d.polygon([(146, 256), (156, 256), (154, 246), (148, 246)], fill=78)
d.ellipse([144, 232, 158, 248], fill=96)
d.ellipse([147, 227, 156, 238], fill=96)
# downpipe on the end wall, gushing at the base
d.line([(153, 62), (153, 252)], fill=88, width=3)
d.line([(150, 70), (156, 70)], fill=70, width=2)
d.line([(150, 160), (156, 160)], fill=70, width=2)
d.ellipse([149, 250, 158, 256], fill=190)
for _ in range(5):
    ex = R.uniform(148, 160)
    d.line([(ex, 256), (ex + R.uniform(-2, 2), 259)], fill=196, width=1)

# awning drip lines
for dx in range(10, 80, 11):
    d.line([(dx, 179), (dx, 179 + R.uniform(4, 8))], fill=152, width=1)
for dx in range(92, 154, 11):
    d.line([(dx, 167), (dx, 167 + R.uniform(4, 8))], fill=152, width=1)

# A-frame chalkboard on the sidewalk (today's special, braving the rain)
d.polygon([(117, 278), (124, 250), (136, 250), (143, 278)], fill=86)
d.line([(124, 250), (117, 278)], fill=INK, width=2)
d.line([(136, 250), (143, 278)], fill=INK, width=2)
d.line([(123, 250), (137, 250)], fill=INK, width=2)
d.line([(125, 256), (135, 256)], fill=216, width=1)     # chalk lines
d.line([(124, 261), (137, 261)], fill=216, width=1)
d.ellipse([127, 265, 134, 271], outline=216)            # chalk bun doodle
d.line([(128, 274), (133, 274)], fill=216, width=1)

# ================================================================ BUS SHELTER (right)
# back glass
d.rectangle([430, 158, 518, 268], fill=GLASS)
d.rectangle([430, 158, 518, 268], outline=140, width=1)
d.line([(474, 158), (474, 268)], fill=150, width=1)
d.line([(438, 172), (452, 158)], fill=240, width=2)     # sheen
d.line([(448, 186), (470, 164)], fill=240, width=1)
# bench + curled cat (dry and smug)
d.rectangle([436, 240, 512, 246], fill=84)
d.line([(442, 241), (442, 245)], fill=130, width=1)
d.line([(475, 241), (475, 245)], fill=130, width=1)
d.line([(508, 241), (508, 245)], fill=130, width=1)
d.line([(442, 246), (442, 272)], fill=70, width=2)
d.line([(506, 246), (506, 272)], fill=70, width=2)
d.ellipse([454, 226, 486, 241], fill=62)                # cat body (curled bun)
d.ellipse([472, 216, 488, 232], fill=62)                # head
d.polygon([(473, 220), (476, 211), (480, 218)], fill=62)  # ears
d.polygon([(481, 218), (486, 212), (488, 220)], fill=62)
d.arc([448, 230, 470, 246], 80, 260, fill=62, width=3)  # tail curled round the front
d.ellipse([451, 236, 457, 242], fill=62)                # tail tip
d.line([(476, 226), (480, 227)], fill=130, width=1)     # closed eye
# roof + posts
d.rounded_rectangle([418, 138, 530, 154], radius=6, fill=78)
d.line([(421, 140), (527, 140)], fill=148, width=1)
d.line([(430, 154), (438, 162)], fill=70, width=2)      # roof struts
d.line([(518, 154), (510, 162)], fill=70, width=2)
d.rectangle([424, 148, 428, 274], fill=70)
d.rectangle([520, 148, 524, 274], fill=70)
# roof drip beads
for dx in range(424, 526, 12):
    d.line([(dx, 157), (dx, 157 + R.uniform(3, 7))], fill=180, width=1)
# timetable sign on the right post
d.rectangle([526, 176, 539, 204], fill=236, outline=84, width=2)
d.line([(529, 182), (536, 182)], fill=140, width=1)
d.line([(529, 188), (536, 188)], fill=140, width=1)
d.line([(529, 194), (536, 194)], fill=140, width=1)
# litter bin beside the shelter
d.rectangle([527, 248, 539, 276], fill=98, outline=70, width=1)
d.rectangle([525, 244, 539, 249], fill=70)
d.line([(531, 252), (531, 272)], fill=122, width=1)
d.line([(535, 252), (535, 272)], fill=122, width=1)

# ================================================================ LAMPPOST (soft halo first: fill >= 225 keeps zone legal)
d.ellipse([373, 36, 421, 78], fill=242)
d.ellipse([381, 42, 413, 72], fill=246)
# pole + plinth
d.rectangle([391, 268, 403, 276], fill=70)
d.line([(397, 268), (397, 66)], fill=70, width=3)
d.line([(388, 74), (406, 74)], fill=70, width=2)        # crossarm
d.arc([388, 74, 396, 82], 180, 270, fill=70, width=1)   # scrolls
d.arc([398, 74, 406, 82], 270, 360, fill=70, width=1)
# lantern
d.rectangle([391, 48, 403, 64], fill=238, outline=INK, width=2)
d.polygon([(388, 48), (406, 48), (397, 40)], fill=INK)
d.ellipse([395, 35, 399, 39], fill=INK)
d.line([(391, 64), (403, 64)], fill=INK, width=2)
# hanging flower basket on the crossarm
d.line([(404, 76), (404, 88)], fill=70, width=1)
d.pieslice([396, 84, 414, 100], 0, 180, fill=84)
for fx, fy in [(399, 82), (404, 80), (409, 82), (401, 85), (407, 85)]:
    d.ellipse([fx - 2, fy - 2, fx + 2, fy + 2], fill=R.choice([205, 150, 95]))
d.line([(400, 100), (398, 106)], fill=110, width=1)     # trailing vine
d.line([(408, 100), (411, 107)], fill=110, width=1)

# ================================================================ BICYCLE leaning on the lamppost
BY = 272
d.ellipse([340, BY + 11, 366, BY + 16], fill=78)                # contact shadows
d.ellipse([380, BY + 11, 406, BY + 16], fill=78)
d.ellipse([339, BY - 13, 365, BY + 13], outline=66, width=2)    # rear wheel
d.ellipse([379, BY - 13, 405, BY + 13], outline=66, width=2)    # front wheel
for ang in (0.3, 1.1, 1.9, 2.6):
    for hx in (352, 392):
        d.line([(hx - math.cos(ang) * 11, BY - math.sin(ang) * 11),
                (hx + math.cos(ang) * 11, BY + math.sin(ang) * 11)], fill=132, width=1)
d.ellipse([350, BY - 2, 354, BY + 2], fill=66)
d.ellipse([390, BY - 2, 394, BY + 2], fill=66)
d.arc([337, BY - 15, 367, BY + 15], 200, 340, fill=66, width=2)  # rear fender
d.arc([377, BY - 15, 407, BY + 15], 200, 340, fill=66, width=2)  # front fender
# frame
d.line([(352, BY), (368, BY - 2)], fill=66, width=2)
d.line([(368, BY - 2), (362, 250)], fill=66, width=2)   # seat tube
d.line([(362, 250), (386, 252)], fill=66, width=2)      # top tube
d.line([(386, 252), (392, BY)], fill=66, width=2)       # head tube / fork
d.line([(368, BY - 2), (386, 252)], fill=66, width=2)   # down tube
d.line([(352, BY), (362, 250)], fill=66, width=1)       # seat stay
d.ellipse([365, BY - 5, 371, BY + 1], outline=66, width=2)   # chainring
d.rectangle([357, 245, 366, 248], fill=66)              # saddle
d.line([(386, 252), (381, 245)], fill=66, width=2)      # handlebar stem
d.line([(381, 245), (376, 246)], fill=66, width=2)
# wrapped parcel on the rear rack
d.line([(340, 257), (360, 257)], fill=66, width=2)
d.line([(342, 257), (352, BY - 4)], fill=66, width=1)
d.rectangle([341, 247, 358, 256], fill=104, outline=60, width=1)
d.line([(349, 247), (349, 256)], fill=150, width=1)
d.line([(341, 251), (358, 251)], fill=150, width=1)

# rain bouncing off the shelter roof and shop parapets
for bx in range(426, 522, 16):
    d.line([(bx - 2, 137), (bx, 134)], fill=196, width=1)
    d.line([(bx, 134), (bx + 2, 137)], fill=196, width=1)
for bx in range(10, 80, 14):
    d.line([(bx - 2, 36), (bx, 33)], fill=200, width=1)
    d.line([(bx, 33), (bx + 2, 36)], fill=200, width=1)
for bx in range(92, 152, 14):
    d.line([(bx - 2, 52), (bx, 49)], fill=200, width=1)
    d.line([(bx, 49), (bx + 2, 52)], fill=200, width=1)

# puffed-up pigeons riding out the rain on the shelter roof
for px2 in (448, 466):
    d.line([(px2 - 7, 130), (px2 - 12, 127)], fill=88, width=2)   # tail
    d.ellipse([px2 - 7, 126, px2 + 5, 137], fill=88)              # body
    d.ellipse([px2 + 1, 122, px2 + 9, 130], fill=88)              # head
    d.line([(px2 + 9, 125), (px2 + 12, 126)], fill=60, width=1)   # beak

# ================================================================ RAIN (sample-aware streaks, zone-safe)
def zone_clear(x, y):
    if y <= 29:
        return False
    if 152 <= x <= 390 and y <= 226:
        return False
    return True

made = 0
attempts = 0
while made < 275 and attempts < 5000:
    attempts += 1
    x0 = R.uniform(2, W - 2)
    y0 = R.uniform(31, 300)
    ln = R.uniform(10, 17)
    x1 = x0 - ln * 0.22
    y1 = y0 + ln
    if not (zone_clear(x0, y0) and zone_clear(x1, y1) and
            zone_clear((x0 + x1) / 2, (y0 + y1) / 2)):
        continue
    if not (0 <= x1 < W and y1 < H):
        continue
    p = img.getpixel((int((x0 + x1) / 2), int((y0 + y1) / 2)))
    col = max(150, p - 62) if p >= 168 else min(200, p + 58)
    d.line([(x0, y0), (x1, y1)], fill=col, width=1)
    made += 1

# ================================================================ BOTTOM FRINGE (weeds through the cracked edge)
for x in range(0, W, 3):
    hgt = R.uniform(4, 13)
    v = R.choice([56, 62, 70])
    d.line([(x, H), (x + R.uniform(-2, 2), H - hgt)], fill=v, width=1)
for x in range(1, W, 9):
    d.line([(x, H), (x + 1, H - R.uniform(2, 6))], fill=118, width=1)

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
