# -*- coding: utf-8 -*-
"""
v3 scene: "snow" -- MOUNTAIN VILLAGE
Flat-shade layered alpine scene for the M5Paper (540x320, mode L).
Chalet cluster with thick snow caps and ONE lit window, an attached
open-front woodshed with stacked logs, a cable-car line climbing the
big right-hand peak to a stilted summit station, pines in four
distances, ski tracks curving down the slope and ending at a pair of
skis planted by the main chalet, chimney smoke drifting up the left
margin, a snowman, a buried fence with a raven.  Quiet and cold.

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
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\snow.png"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
SEED = 7
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK       = 58
PINE_FG   = 62    # foreground pines
PINE_MID  = 132
PINE_B    = 176   # pines on plane B
PINE_A    = 214   # tiny pines on far ridge
A_FILL    = 241   # plane A: far ridge (legal inside glyph zone)
A_LINE    = 233
B_FILL    = 233   # plane B: mid hills
B_LINE    = 214
C_FILL    = 229   # plane C: village slope
C_LINE    = 200
D_FILL    = 222   # plane D: foreground drift (kept below y 222)
D_LINE    = 196
PEAK_LIT  = 231
PEAK_SHD  = 205
ROCK_L    = 150
ROCK_S    = 120
SNOW      = 244   # roof caps / cornice
WALL1     = 134
WALL2     = 126
ROOF      = 86
LIT       = 243   # the one lit window

ph = [R.uniform(0, math.tau) for _ in range(8)]

def yA(x):
    e = max(0.0, (130 - x) / 130.0) + max(0.0, (x - 410) / 130.0)
    return 204 - 38 * e + 6 * math.sin(x / 47.0 + ph[0]) + 4 * math.sin(x / 19.0 + ph[1])

def yB(x):
    e = max(0.0, (150 - x) / 150.0) + max(0.0, (x - 400) / 140.0)
    return 238 - 50 * e + 4 * math.sin(x / 33.0 + ph[2])

def yC(x):
    e = max(0.0, (140 - x) / 140.0) + max(0.0, (x - 400) / 140.0)
    return 250 - 16 * e + 3 * math.sin(x / 26.0 + ph[3])

def yD(x):
    return 291 + 6 * math.sin(x / 34.0 + ph[4]) + 3 * math.sin(x / 13.0 + ph[5])

# ---------------------------------------------------------------- helpers
def pine(cx, base, h, tone, snow_shelf=True):
    """Layered fir with optional snow shelves on each tier."""
    n = 3 if h < 48 else 4
    top = base - h
    for i in range(n):
        t0 = top + i * h * 0.24
        b0 = t0 + h * 0.34
        hw = h * (0.09 + 0.065 * i)
        d.polygon([(cx, t0), (cx - hw, b0), (cx + hw, b0)], fill=tone)
        if snow_shelf and tone < 150:
            d.polygon([(cx, t0), (cx - hw * 0.45, t0 + h * 0.11),
                       (cx + hw * 0.45, t0 + h * 0.11)], fill=242)
    if tone < 200:
        d.rectangle([cx - 1, base - 3, cx + 1, base + 3], fill=max(60, tone - 40))

def snow_lumps(x0, y0, x1, y1, r0=3, r1=5, lift=2):
    """Lumpy snow blobs along a segment (zone-aware radius clamp)."""
    ln = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(ln / 6))
    for i in range(n + 1):
        t = i / float(n)
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t - lift
        r = R.uniform(r0, r1)
        if 154 <= cx <= 386:
            r = min(r, cy - 224)      # never rise into the glyph zone
        if r < 1.2:
            continue
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SNOW)

# ================================================================ SKY (quiet): flat cloud bars, margins only
def cloudbar(cx, cy, s):
    for lx, ly, lr in [(-1.5, 0.1, 0.7), (-0.4, -0.25, 1.0), (0.8, 0.0, 0.85), (1.7, 0.2, 0.6)]:
        r = s * lr
        d.ellipse([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r], fill=245)
    d.rectangle([cx - 2.0 * s, cy, cx + 2.2 * s, cy + 0.6 * s], fill=245)
    d.line([(cx - 1.9 * s, cy + 0.6 * s), (cx + 2.1 * s, cy + 0.6 * s)], fill=232, width=1)

cloudbar(78, 50, 13)
cloudbar(505, 50, 8)

# two distant ravens, top-left margin
for bx, by in [(66, 44), (92, 54)]:
    d.line([(bx - 5, by + 2), (bx, by)], fill=104, width=2)
    d.line([(bx, by), (bx + 5, by + 2)], fill=104, width=2)

# ================================================================ PLANE A: far ridge (faint, legal inside zone)
ptsA = [(x, yA(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H)] + ptsA + [(W, H)], fill=A_FILL)
d.line(ptsA, fill=A_LINE, width=1)
# tiny far pines on the left margin of the ridge
for px in (10, 22, 38, 52, 68, 86, 102):
    hh = R.uniform(9, 13)
    b = yA(px) + 4
    d.polygon([(px, b - hh), (px - hh * 0.34, b), (px + hh * 0.34, b)], fill=PINE_A)

# ================================================================ PLANE B: mid hills
ptsB = [(x, yB(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H)] + ptsB + [(W, H)], fill=B_FILL)
d.line(ptsB, fill=B_LINE, width=1)
# pine row on the left shoulder of plane B
for px in (10, 26, 44, 62, 80, 98, 116, 134, 148):
    hh = R.uniform(20, 30)
    pine(px, yB(px) + 8, hh, PINE_B, snow_shelf=False)

# ================================================================ BIG PEAK (right)  -- x >= 385, outside glyph zone
SUM = (455, 50)
d.polygon([(385, 272), SUM, (492, 272)], fill=PEAK_LIT)                 # lit face
d.polygon([SUM, (540, 196), (540, 272), (492, 272)], fill=202)          # shadow face
d.line([(385, 272), SUM], fill=150, width=2)                            # silhouette
d.line([SUM, (540, 196)], fill=150, width=2)
d.line([SUM, (492, 272)], fill=176, width=1)                            # spine
# rock wedges: outcrops breaking through the snow near the spine
d.polygon([(459, 96), (455, 112), (463, 150), (468, 128)], fill=192)
d.line([(459, 96), (455, 112), (463, 150)], fill=156, width=1)
d.polygon([(468, 160), (463, 178), (472, 218), (478, 192)], fill=192)
d.line([(468, 160), (463, 178), (472, 218)], fill=156, width=1)
d.polygon([(444, 140), (441, 154), (447, 182), (451, 162)], fill=204)
# steep crag strokes following the fall line (lit face)
for sx0, sy0, ln in [(448, 88, 12), (452, 118, 14), (440, 168, 12),
                     (430, 196, 11), (458, 200, 13), (446, 230, 10)]:
    d.line([(sx0, sy0), (sx0 - 2, sy0 + ln)], fill=164, width=2)
# crag strokes on the shadow face
for sx0, sy0, ln in [(472, 104, 12), (480, 140, 13), (476, 176, 11), (490, 200, 12)]:
    d.line([(sx0, sy0), (sx0 + 1, sy0 + ln)], fill=132, width=2)
# couloir streaks on the lit face
d.line([(447, 92), (441, 152)], fill=216, width=1)
d.line([(452, 122), (446, 192)], fill=216, width=1)
d.line([(434, 160), (428, 216)], fill=216, width=1)
# summit cornice (over the rock)
d.ellipse([446, 44, 466, 55], fill=SNOW)
d.line([(441, 58), (455, 48), (469, 56)], fill=SNOW, width=4)
d.line([(444, 60), (455, 52)], fill=ROCK_L, width=1)

# ================================================================ SUMMIT STATION (on the right shoulder, stilts downhill)
# platform + stilts
d.rectangle([494, 140, 539, 146], fill=92)
d.line([(530, 146), (530, 178)], fill=88, width=3)
d.line([(518, 146), (518, 160)], fill=88, width=2)
d.line([(530, 168), (518, 156)], fill=88, width=2)
# hut with snow-capped gable
d.rectangle([500, 118, 534, 140], fill=114)
d.polygon([(495, 122), (517, 106), (539, 122), (539, 127), (517, 111), (495, 127)], fill=ROOF)
snow_lumps(497, 118, 517, 104, 2, 3)
snow_lumps(517, 104, 537, 118, 2, 3)
d.rectangle([510, 126, 519, 135], fill=196)          # pale (not lit) window
d.rectangle([510, 126, 519, 135], outline=70)
# bull-wheel where the cable arrives
d.ellipse([492, 130, 503, 141], outline=74, width=2)
d.ellipse([496, 134, 499, 137], fill=74)

# ================================================================ PLANE C: village slope
ptsC = [(x, yC(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H)] + ptsC + [(W, H)], fill=C_FILL)
d.line(ptsC, fill=C_LINE, width=1)

# ================================================================ CABLE LINE (pylons, cables, cabin) -- all x >= 385
def cab_y(x):     # main cable from terminal tower to summit bull-wheel
    return 238 - (x - 436) * (102.0 / 62.0)

for px in (462, 480):
    cy = cab_y(px)
    d.line([(px, cy + 2), (px, cy + 30)], fill=76, width=3)      # post
    d.line([(px - 7, cy + 2), (px + 7, cy + 2)], fill=76, width=2)
    d.line([(px - 5, cy + 9), (px, cy + 3)], fill=76, width=1)
    d.line([(px + 5, cy + 9), (px, cy + 3)], fill=76, width=1)
    d.ellipse([px - 3, cy + 28, px + 3, cy + 33], fill=190)      # footing drift
d.line([(436, 238), (497, 137)], fill=92, width=1)               # up cable
d.line([(436, 243), (497, 142)], fill=166, width=1)              # return cable
# cabin on the line
d.line([(452, cab_y(452)), (452, cab_y(452) + 6)], fill=70, width=2)
d.rectangle([445, cab_y(452) + 6, 459, cab_y(452) + 18], fill=104, outline=INK)
d.rectangle([448, cab_y(452) + 9, 456, cab_y(452) + 13], fill=196)

# ================================================================ VALLEY TERMINAL (village end of the line)
d.rectangle([396, 238, 428, 270], fill=WALL2)                    # hall
d.polygon([(392, 232), (430, 232), (430, 241), (392, 241)], fill=90)
snow_lumps(394, 231, 428, 231, 2, 4)
d.rectangle([402, 248, 412, 262], fill=88)                       # hall window (dark)
d.rectangle([426, 222, 450, 270], fill=112)                      # cable tower
d.rectangle([422, 218, 452, 227], fill=88)
snow_lumps(424, 217, 450, 217, 2, 4)
d.rectangle([430, 240, 446, 262], fill=74)                       # dark cabin bay
d.rectangle([433, 248, 442, 258], fill=150)                      # parked cabin glint
d.line([(396, 270), (450, 270)], fill=70, width=2)

# trampled path from terminal toward the village
for t in range(9):
    tx = 396 - t * 6
    ty = 272 + t * 2.0
    d.line([(tx, ty), (tx - 4, ty + 1)], fill=205, width=1)

# ================================================================ field texture on plane C
for _ in range(26):
    sx = R.uniform(24, 516)
    sy = R.uniform(252, 286)
    d.line([(sx, sy), (sx + R.uniform(6, 14), sy)], fill=216, width=1)
for _ in range(8):        # sparkle crosses
    sx = R.uniform(30, 500)
    sy = R.uniform(254, 284)
    d.line([(sx - 2, sy), (sx + 2, sy)], fill=210, width=1)
    d.line([(sx, sy - 2), (sx, sy + 2)], fill=210, width=1)

# ================================================================ SKI TRACKS: down the peak flank, S-curving to the chalet
trk = [(446, 176), (432, 184), (424, 194), (431, 204), (420, 214),
       (408, 220), (396, 226), (386, 230),
       (372, 234), (352, 239), (326, 244), (298, 248), (268, 253),
       (240, 259), (214, 266), (196, 273), (182, 280), (172, 286)]
for i in range(len(trk) - 1):
    (x0, y0), (x1, y1) = trk[i], trk[i + 1]
    d.line([(x0, y0), (x1, y1)], fill=176, width=1)
    d.line([(x0, y0 + 4), (x1, y1 + 4)], fill=176, width=1)
# little spray chevrons where the turns bite
for tx, ty in [(408, 219), (352, 244), (268, 258), (196, 278)]:
    d.line([(tx - 3, ty + 2), (tx, ty)], fill=196, width=1)
    d.line([(tx, ty), (tx + 3, ty + 2)], fill=196, width=1)

# ================================================================ WOODSHED (attached, open front, stacked logs)
d.rectangle([42, 252, 88, 302], fill=WALL1)
d.polygon([(38, 246), (92, 252), (92, 258), (38, 252)], fill=ROOF)
snow_lumps(40, 244, 90, 250, 2, 4)
d.rectangle([48, 266, 82, 302], fill=80)                         # open front
for row, ly in enumerate((296, 289, 282, 275)):
    for li in range(5):
        lx = 52 + li * 6.4 + (3 if row % 2 else 0)
        if lx > 78:
            continue
        d.ellipse([lx - 2.6, ly - 2.6, lx + 2.6, ly + 2.6], fill=150, outline=62)

# ================================================================ MAIN CHALET (the one lit window, smoking chimney)
d.rectangle([88, 252, 168, 300], fill=WALL1)                     # wall
for py in range(258, 300, 6):
    d.line([(89, py), (167, py)], fill=116, width=1)             # plank lines
d.polygon([(88, 252), (128, 228), (168, 252)], fill=122)         # gable face
for gx in range(94, 166, 6):
    gy = 252 - max(0, (24 - abs(gx - 128) * 0.6))
    d.line([(gx, gy + 2), (gx, 252)], fill=104, width=1)
d.polygon([(78, 256), (128, 226), (178, 256), (178, 261), (128, 231), (78, 261)], fill=ROOF)
d.polygon([(80, 252), (128, 222), (176, 252), (176, 256), (128, 226), (80, 256)], fill=SNOW)
snow_lumps(82, 250, 128, 222, 3, 5)
snow_lumps(128, 222, 174, 250, 3, 5)
# icicles under both eaves
for ix in (84, 96, 110, 124, 140, 154, 166):
    hh = R.uniform(4, 8)
    d.polygon([(ix - 2, 261), (ix + 2, 261), (ix, 261 + hh)], fill=210)
# THE lit window (small panes) + shutters
d.rectangle([100, 264, 118, 284], fill=LIT)
d.rectangle([100, 264, 118, 284], outline=INK, width=2)
d.line([(109, 264), (109, 284)], fill=INK, width=1)
d.line([(100, 274), (118, 274)], fill=INK, width=1)
d.rectangle([94, 264, 99, 284], fill=84)
d.rectangle([119, 264, 124, 284], fill=84)
d.line([(96, 268), (96, 280)], fill=120, width=1)
d.line([(121, 268), (121, 280)], fill=120, width=1)
# dark second window + shutters
d.rectangle([132, 264, 146, 280], fill=96)
d.rectangle([132, 264, 146, 280], outline=INK, width=1)
d.line([(139, 264), (139, 280)], fill=INK, width=1)
d.rectangle([128, 264, 131, 280], fill=84)
d.rectangle([147, 264, 150, 280], fill=84)
# door
d.rectangle([152, 272, 166, 300], fill=88)
d.rectangle([152, 272, 166, 300], outline=INK, width=1)
d.rectangle([156, 276, 162, 282], fill=120)
d.ellipse([154, 286, 157, 289], fill=INK)
# chimney + snow dollop (dollop wider than the cap so no dark corners poke out)
d.rectangle([141, 226, 151, 244], fill=102)
d.rectangle([139, 222, 153, 227], fill=68)
d.ellipse([137, 218, 155, 225], fill=SNOW)
# smoke: serpentine plume drifting up-left, tapering into detached puffs
plume = []
for i in range(16):
    t = i / 15.0
    sx = 146 - 58 * t - 14 * math.sin(3.6 * t)
    sy = 215 - 92 * t
    sr = (2.2 + 6.2 * t) * (1 + 0.12 * math.sin(9 * t))
    plume.append((sx, sy, sr))
for sx, sy, sr in plume:                     # solid overlapping body
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=233)
for j, (sx, sy, sr) in enumerate(plume[3::3]):   # shaded arcs, alternating sides
    a0 = 110 if j % 2 == 0 else 300
    d.arc([sx - sr, sy - sr, sx + sr, sy + sr], a0, a0 + 130, fill=203, width=1)
d.arc([plume[-1][0] - plume[-1][2], plume[-1][1] - plume[-1][2],
       plume[-1][0] + plume[-1][2], plume[-1][1] + plume[-1][2]], 190, 360, fill=203, width=1)
for px2, py2, pr2 in [(86, 112, 5.0), (78, 103, 3.6)]:   # drift-away puffs
    d.ellipse([px2 - pr2, py2 - pr2, px2 + pr2, py2 + pr2], fill=235, outline=207)

# ================================================================ SECOND CHALET (dark, balcony)
d.rectangle([258, 262, 338, 302], fill=WALL2)
for py in range(268, 302, 6):
    d.line([(259, py), (337, py)], fill=108, width=1)
d.polygon([(258, 262), (298, 238), (338, 262)], fill=116)
for gx in range(264, 336, 6):
    d.line([(gx, 246 + abs(gx - 298) * 0.45), (gx, 262)], fill=100, width=1)
d.polygon([(248, 266), (298, 236), (348, 266), (348, 271), (298, 241), (248, 271)], fill=88)
d.polygon([(250, 262), (298, 232), (346, 262), (346, 266), (298, 236), (250, 266)], fill=SNOW)
snow_lumps(252, 260, 298, 232, 3, 5)
snow_lumps(298, 232, 344, 260, 3, 5)
for ix in (256, 270, 284, 300, 314, 328, 342):
    hh = R.uniform(4, 7)
    d.polygon([(ix - 2, 270), (ix + 2, 270), (ix, 270 + hh)], fill=204)
# gable vent + two dark windows
d.rectangle([293, 250, 303, 258], fill=94)
d.rectangle([268, 270, 282, 282], fill=94)
d.rectangle([268, 270, 282, 282], outline=INK, width=1)
d.line([(275, 270), (275, 282)], fill=INK, width=1)
d.rectangle([312, 270, 326, 282], fill=94)
d.rectangle([312, 270, 326, 282], outline=INK, width=1)
d.line([(319, 270), (319, 282)], fill=INK, width=1)
# balcony rail
d.line([(260, 286), (336, 286)], fill=66, width=2)
for bx in range(262, 336, 8):
    d.line([(bx, 286), (bx, 293)], fill=66, width=1)
d.line([(260, 293), (336, 293)], fill=66, width=2)
# door
d.rectangle([292, 288, 306, 302], fill=82)
d.rectangle([292, 288, 306, 302], outline=INK, width=1)

# ================================================================ SNOWMAN (on C, drift will lap his base)
d.ellipse([223, 268, 241, 286], fill=246, outline=150)
d.ellipse([226, 256, 238, 268], fill=246, outline=150)
d.line([(224, 274), (212, 265)], fill=70, width=2)               # stick arms
d.line([(240, 274), (252, 266)], fill=70, width=2)
d.ellipse([229, 260, 231, 262], fill=70)                         # eyes
d.ellipse([233, 260, 235, 262], fill=70)
d.line([(232, 263), (237, 265)], fill=130, width=2)              # carrot
d.line([(226, 268), (238, 268)], fill=92, width=2)               # scarf
d.line([(236, 268), (239, 274)], fill=92, width=2)

# ================================================================ PLANE D: foreground drift (laps every base)
ptsD = [(x, yD(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H)] + ptsD + [(W, H)], fill=D_FILL)
d.line(ptsD, fill=D_LINE, width=1)
for _ in range(16):
    sx = R.uniform(10, 530)
    sy = R.uniform(296, 314)
    d.line([(sx, sy), (sx + R.uniform(5, 12), sy)], fill=198, width=1)

# warm light spilling from the lit window onto the drift
d.polygon([(96, 300), (122, 300), (128, 314), (90, 314)], fill=238)

# footprints: door -> planted skis
for fx, fy in [(154, 298), (160, 296), (166, 294), (171, 292), (175, 290)]:
    d.line([(fx, fy), (fx + 2, fy)], fill=168, width=2)

# planted skis + crossed poles at the end of the tracks
d.line([(173, 254), (172, 290)], fill=70, width=2)
d.line([(180, 255), (179, 291)], fill=70, width=2)
d.arc([169, 250, 177, 258], 180, 300, fill=70, width=2)
d.arc([176, 251, 184, 259], 180, 300, fill=70, width=2)
d.line([(166, 262), (184, 292)], fill=96, width=1)
d.line([(188, 260), (168, 293)], fill=96, width=1)
d.ellipse([182, 289, 187, 294], outline=96)
d.ellipse([166, 290, 171, 295], outline=96)

# ================================================================ FENCE half-buried in the drift + raven
for i, fx in enumerate(range(192, 290, 16)):
    top = 296 + 2 * math.sin(i)
    d.line([(fx, top), (fx, 316)], fill=80, width=3)
    d.rectangle([fx - 2, top - 2, fx + 2, top], fill=242)        # snow cap
d.line([(192, 302), (288, 305)], fill=92, width=2)
d.line([(192, 309), (288, 311)], fill=92, width=1)
# raven hunched on the first post
d.ellipse([187, 288, 197, 295], fill=INK)
d.ellipse([193, 284, 200, 290], fill=INK)
d.line([(200, 287), (204, 288)], fill=INK, width=2)
d.line([(188, 291), (183, 294)], fill=INK, width=2)

# ================================================================ mid pines by the second chalet (drawn over D edge)
pine(354, 306, 48, 84)
pine(372, 300, 34, 96)

# ================================================================ FOREGROUND pines (darkest plane)
pine(30, 316, 62, 74)
pine(12, 326, 108, PINE_FG)
pine(492, 318, 52, 78)
pine(518, 326, 84, PINE_FG)

# ================================================================ BOTTOM FRINGE: dry grass + half-buried stones
for rx, rw in [(60, 14), (150, 10), (262, 16), (352, 12), (452, 15)]:
    d.ellipse([rx, H - 8, rx + rw, H + 6], fill=100)
for x in range(0, W, 3):
    hgt = R.uniform(4, 13)
    v = R.choice([58, 64, 74])
    d.line([(x, H), (x + R.uniform(-2, 2), H - hgt)], fill=v, width=1)
for x in range(1, W, 9):
    d.line([(x, H), (x + 1, H - R.uniform(2, 6))], fill=124, width=1)

# ================================================================ SNOWFALL (sample-aware, zone-safe)
def zone_clear(x, y):
    if y <= 30:
        return False
    if 152 <= x <= 388 and y <= 226:
        return False
    return True

made = 0
attempts = 0
while made < 150 and attempts < 6000:
    attempts += 1
    fx = R.uniform(3, W - 3)
    fy = R.uniform(33, 310)
    if not zone_clear(fx, fy):
        continue
    p = img.getpixel((int(fx), int(fy)))
    if p >= 232:
        col = 208
    elif p >= 120:
        col = 246
    else:
        col = 240
    d.rectangle([fx, fy, fx + 1, fy + 1], fill=col)
    made += 1
made = 0
attempts = 0
while made < 60 and attempts < 4000:
    attempts += 1
    fx = R.uniform(3, W - 3)
    fy = R.uniform(33, 300)
    if not zone_clear(fx, fy):
        continue
    p = img.getpixel((int(fx), int(fy)))
    col = 214 if p >= 232 else 244
    d.point((fx, fy), fill=col)
    made += 1

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
