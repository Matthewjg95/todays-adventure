# -*- coding: utf-8 -*-
"""
v3 scene: "storm" -- LIGHTHOUSE CLIFF
Flat-shade layered seascape for the M5Paper (540x320, mode L).
A lighthouse rides a dark headland on the right, its beam wedges sweeping
away from the glyph zone toward the right edge.  Keeper's cottage with a
lit window, storm-bent tree streaming in the wind, fence posts, wave spray
bursting white against the rocks, a small boat running for home under a
storm jib, gulls fighting the gale, one lightning fork in the left scud.
Dramatic darks, no people.

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
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\storm.png"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
SEED = 7
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK     = 56    # darkest line work
FORE    = 60    # foreground sea band (darkest plane)
ROCK    = 62
CLIFF   = 80
NEAR    = 118   # near sea band
SCUD    = 132   # storm cloud panels
BAND_D  = 88    # dark cloud streaks
MID     = 176   # mid sea band
FAR     = 208   # far sea band
HEADLND = 214   # distant headland (lightest plane)
TOWER   = 232
GLOW    = 246
BEAM    = 240
SPRAY   = 244

# safety fences (glyph zone x160..380 y30..220, date strip y0..28)
LM = 156        # dark allowed left of this when y < 223
RM = 384        # dark allowed right of this when y < 223
CY = 223        # dark allowed everywhere at/below this
TY = 31         # dark allowed at/below this in the margins

ph = [R.uniform(0, math.tau) for _ in range(8)]

# ================================================================ SKY GLOOM PANELS (wind-torn scud, margins only)
# left panel: ragged inner + bottom edge
d.polygon([(0, 32), (44, 34), (92, 31), (136, 34), (150, 32),
           (154, 52), (146, 74), (152, 96), (142, 118), (148, 134),
           (128, 146), (96, 150), (64, 142), (30, 152), (0, 144)],
          fill=SCUD)
# darker streak bands inside (lenticular scud)
d.ellipse([4, 42, 122, 60], fill=BAND_D)
d.ellipse([16, 76, 142, 92], fill=BAND_D)
d.ellipse([0, 106, 110, 124], fill=BAND_D)
# wind-shred tails off the band ends
for x0, y0 in [(118, 50), (136, 84), (104, 114)]:
    d.line([(x0, y0), (min(x0 + 34, 154), y0 - 2)], fill=BAND_D, width=3)
# pale wind streaks tearing through
d.line([(10, 66), (56, 64)], fill=210, width=2)
d.line([(100, 100), (146, 98)], fill=210, width=2)
d.line([(6, 132), (48, 130)], fill=204, width=2)

# right panel: gloom runs all the way down to the cliff top so the beams
# have something dark to cut through
d.polygon([(392, 33), (440, 31), (492, 34), (540, 31),
           (540, 150), (524, 153), (500, 150), (474, 152), (450, 150),
           (428, 152), (408, 148), (394, 140), (388, 116), (393, 98),
           (386, 80), (392, 60), (387, 46)],
          fill=SCUD)
d.ellipse([396, 38, 520, 52], fill=BAND_D)
d.ellipse([410, 58, 540, 74], fill=BAND_D)
d.ellipse([388, 82, 482, 96], fill=BAND_D)
d.ellipse([402, 104, 540, 118], fill=BAND_D)
d.line([(400, 66), (466, 63)], fill=210, width=2)
d.line([(420, 92), (500, 89)], fill=204, width=2)
d.line([(396, 122), (452, 120)], fill=204, width=2)

# detached scud shreds below the left panel
d.line([(58, 160), (122, 157)], fill=SCUD, width=4)
d.line([(24, 176), (70, 174)], fill=170, width=3)

# ================================================================ LIGHTNING (in the left scud)
d.line([(88, 50), (76, 82)], fill=248, width=4)
d.line([(76, 82), (90, 90)], fill=248, width=4)
d.line([(90, 90), (72, 124)], fill=248, width=3)
d.line([(72, 124), (79, 127)], fill=248, width=3)
d.line([(79, 127), (68, 138)], fill=248, width=2)
d.line([(76, 82), (60, 104)], fill=248, width=2)   # fork
d.line([(60, 104), (52, 118)], fill=248, width=1)

# ================================================================ PLANE 1: distant headland + far sea
d.polygon([(0, 206), (26, 201), (54, 207), (76, 213), (90, 222), (0, 222)],
          fill=HEADLND)
d.line([(0, 206), (26, 201), (54, 207), (76, 213), (90, 222)], fill=190, width=1)

d.rectangle([0, 224, W, H], fill=FAR)              # far sea base
d.line([(0, 224), (W, 224)], fill=186, width=1)    # horizon

def b1(x): return 250 + 3.0 * math.sin(x / 41.0 + ph[0])
def b2(x): return 277 + 4.0 * math.sin(x / 33.0 + ph[1])
def b3(x): return 301 + 3.5 * math.sin(x / 26.0 + ph[2])

def band(fn, fill):
    pts = [(x, fn(x)) for x in range(0, W + 1, 4)]
    d.polygon([(0, H)] + pts + [(W, H)], fill=fill)

band(b2, MID)     # mid sea
band(b3, NEAR)    # near sea
# leave FORE for after the rocks so it laps in front

# far-band wave dashes (light chop far out)
for _ in range(26):
    x = R.uniform(4, W - 24)
    y = R.uniform(228, 246)
    ln = R.uniform(8, 20)
    d.line([(x, y), (x + ln, y)], fill=R.choice([190, 226]), width=1)

# ================================================================ BOAT running for home (storytelling)
d.polygon([(94, 234), (130, 234), (124, 242), (100, 242)], fill=62)   # hull
d.line([(112, 234), (121, 210)], fill=62, width=2)                    # heeled mast
d.polygon([(113, 230), (119, 213), (126, 227)], fill=226)             # storm jib
d.line([(113, 230), (119, 213), (126, 227), (113, 230)], fill=62, width=1)
d.ellipse([119, 207, 123, 211], fill=248)                             # masthead light
d.ellipse([118, 206, 124, 212], outline=140, width=1)
d.line([(86, 240), (94, 239)], fill=235, width=2)                     # wake
d.line([(80, 243), (90, 242)], fill=235, width=1)
d.line([(128, 233), (134, 229)], fill=238, width=1)                   # bow spray

# ================================================================ mid-band chop + buoy
for _ in range(30):
    x = R.uniform(4, W - 24)
    y = R.uniform(254, 274)
    ln = R.uniform(10, 24)
    d.line([(x, y), (x + ln, y + R.uniform(-1, 1))], fill=R.choice([150, 205]), width=1)
# long wind streak on the water
d.line([(60, 268), (168, 265)], fill=228, width=1)
d.line([(300, 271), (420, 268)], fill=228, width=1)

# tilted channel buoy (clear of the spray clutter)
d.polygon([(262, 263), (274, 263), (272, 250), (266, 249)], fill=74)
d.line([(264, 257), (273, 258)], fill=230, width=2)                   # day band
d.ellipse([267, 245, 272, 250], fill=240)                             # light
d.arc([256, 259, 280, 269], 200, 340, fill=210, width=1)              # bob rings
d.arc([258, 262, 278, 271], 200, 340, fill=210, width=1)

# ================================================================ BEAMS (before the lighthouse, after the clouds)
d.polygon([(472, 64), (540, 31), (540, 57), (473, 74)], fill=241)     # upper sweep
d.polygon([(472, 74), (540, 96), (540, 132), (473, 82)], fill=238)    # lower sweep
# beam glint skating on the water below the sweep
d.line([(500, 240), (538, 236)], fill=235, width=2)
d.line([(478, 248), (508, 245)], fill=230, width=1)

# ================================================================ PLANE 4: CLIFF headland (dark)
def ctop(x):
    return 146 + 3.5 * math.sin(x / 27.0 + 0.7) + 1.8 * math.sin(x / 11.0)

cliff = [(338, 270), (348, 260), (342, 252), (356, 244), (350, 236),
         (364, 230), (360, 225), (385, 222), (390, 206), (386, 192),
         (392, 176), (388, 162), (393, ctop(393))]
cliff += [(x, ctop(x)) for x in range(396, 541, 6)]
cliff += [(540, 286), (460, 290), (400, 286), (360, 280)]
d.polygon(cliff, fill=CLIFF)
# strata ticks on the face
for _ in range(22):
    x = R.uniform(394, 530)
    y = R.uniform(156, 214)
    d.line([(x, y), (x + R.uniform(5, 11), y + R.uniform(-1, 1))], fill=102, width=1)
for _ in range(16):
    x = R.uniform(352, 528)
    y = R.uniform(228, 278)
    d.line([(x, y), (x + R.uniform(5, 11), y)], fill=102, width=1)
# crack lines
d.line([(402, 162), (398, 186), (404, 208)], fill=INK, width=1)
d.line([(470, 154), (466, 178), (472, 198), (468, 222)], fill=INK, width=1)
d.line([(510, 152), (514, 178), (508, 200)], fill=INK, width=1)
# switchback path from the cottage down the cliff face
d.line([(420, 154), (404, 168), (418, 184), (400, 202), (412, 218),
        (398, 232), (408, 246)], fill=118, width=2)
# waterline shadow at the base (a shade lighter than the rocks)
d.polygon([(342, 268), (386, 258), (444, 266), (540, 262), (540, 286),
           (400, 286), (360, 280)], fill=74)

# ================================================================ ROCKS at the base (spray targets)
d.polygon([(322, 268), (336, 252), (352, 258), (366, 248), (382, 262),
           (374, 276), (336, 278)], fill=ROCK)
d.line([(336, 252), (352, 258), (366, 248)], fill=104, width=1)  # wet-top edge
d.polygon([(296, 284), (312, 272), (330, 278), (336, 290), (304, 292)], fill=INK)
d.polygon([(400, 284), (414, 272), (432, 278), (428, 292), (404, 292)], fill=54)
d.line([(404, 276), (418, 274)], fill=110, width=1)   # wet-top highlight
# driftwood beached on the small rock
d.line([(306, 272), (328, 268)], fill=112, width=2)
d.line([(324, 269), (330, 264)], fill=112, width=1)

# ================================================================ SPRAY bursting on the rocks / cliff face
# tall spray fan climbing the cliff face (right margin, so it may rise high)
d.polygon([(386, 250), (390, 224), (387, 208), (394, 194), (400, 206),
           (398, 226), (404, 252)], fill=SPRAY)
d.polygon([(392, 210), (396, 198), (399, 208)], fill=250)
# burst fans rising off the rock tops, leaning with the wind
d.polygon([(350, 248), (354, 234), (359, 226), (365, 235), (361, 250)], fill=SPRAY)
d.polygon([(330, 256), (334, 242), (339, 235), (344, 244), (341, 258)], fill=SPRAY)
# one clean burst arc cupping the impact
d.arc([332, 236, 372, 260], 190, 330, fill=SPRAY, width=2)
# wind-driven spray dashes streaming up-right off the crests
for x0, y0 in [(340, 240), (352, 232), (364, 229), (374, 242), (334, 250),
               (386, 246)]:
    d.line([(x0, y0), (x0 + R.uniform(5, 9), y0 - R.uniform(3, 6))],
           fill=SPRAY, width=2)
# spray droplets clustered tight around the fans and the cliff-face plume
for _ in range(14):
    x = R.uniform(332, 404)
    y = R.uniform(227, 250)
    r = R.uniform(1, 2)
    d.ellipse([x - r, y - r, x + r, y + r], fill=SPRAY)
for _ in range(12):
    x = R.uniform(387, 404)
    y = R.uniform(196, 224)
    r = R.uniform(1, 1.8)
    d.ellipse([x - r, y - r, x + r, y + r], fill=SPRAY)
# foam wash where sea meets rock (broken, angled)
d.line([(300, 283), (314, 281)], fill=238, width=2)
d.line([(318, 280), (330, 279)], fill=238, width=1)
d.line([(368, 273), (380, 271)], fill=238, width=2)
d.line([(384, 271), (396, 272)], fill=238, width=1)

# ================================================================ KEEPER'S COTTAGE (structure 2)
d.rectangle([398, 128, 438, 152], fill=205)          # walls
d.rectangle([398, 128, 438, 152], outline=INK, width=2)
d.polygon([(393, 129), (443, 129), (418, 111)], fill=62)   # gable roof
d.line([(393, 129), (418, 111), (443, 129)], fill=INK, width=2)
d.rectangle([424, 104, 432, 121], fill=58)           # chimney
# wind-torn smoke streaming right (drawn before the tower: slips behind it)
d.line([(428, 102), (440, 99)], fill=196, width=2)
d.line([(442, 100), (452, 98)], fill=196, width=1)
d.line([(430, 96), (438, 95)], fill=206, width=1)
# lit window (the keeper keeps watch)
d.rectangle([403, 134, 413, 145], fill=GLOW, outline=INK, width=1)
d.line([(408, 134), (408, 145)], fill=INK, width=1)
d.line([(403, 139), (413, 139)], fill=INK, width=1)
# door
d.rectangle([421, 136, 431, 152], fill=84, outline=INK, width=1)

# ================================================================ LIGHTHOUSE (structure 1)
# tapered tower
d.polygon([(447, 152), (477, 152), (471, 90), (453, 90)], fill=TOWER)
d.line([(447, 152), (453, 90)], fill=INK, width=2)
d.line([(477, 152), (471, 90)], fill=INK, width=2)
def tw(y):   # tower half-width at height y
    t = (152 - y) / 62.0
    return 15 - 6 * t
# two dark day-mark bands
for y0, y1 in [(100, 112), (124, 136)]:
    cx = 462
    d.polygon([(cx - tw(y1), y1), (cx + tw(y1), y1),
               (cx + tw(y0), y0), (cx - tw(y0), y0)], fill=70)
# gallery + railing
d.rectangle([445, 84, 479, 90], fill=62)
d.line([(445, 79), (479, 79)], fill=62, width=2)
for x in range(447, 479, 5):
    d.line([(x, 79), (x, 84)], fill=62, width=1)
# lantern room
d.rectangle([452, 62, 472, 79], fill=GLOW)
d.rectangle([452, 62, 472, 79], outline=INK, width=2)
d.line([(462, 62), (462, 79)], fill=INK, width=1)
# roof + finial
d.polygon([(449, 62), (475, 62), (462, 45)], fill=INK)
d.line([(462, 45), (462, 38)], fill=INK, width=2)
d.ellipse([460, 34, 464, 38], fill=INK)

# ================================================================ FENCE + BENT TREE + TUFTS (cliff-top props)
for x in (482, 490, 498):                       # fence posts (tower to tree)
    yt = ctop(x)
    d.line([(x, yt - 8), (x, yt + 2)], fill=INK, width=2)
d.line([(482, ctop(482) - 6), (498, ctop(498) - 6)], fill=INK, width=1)
# gull hunkered on the last post
d.ellipse([495, ctop(498) - 14, 503, ctop(498) - 7], fill=70)
d.line([(503, ctop(498) - 11), (506, ctop(498) - 10)], fill=INK, width=1)

# storm-bent tree streaming right (bigger, silhouetted on the gloom)
tb = ctop(506)
d.line([(505, tb + 2), (509, tb - 9), (517, tb - 17), (528, tb - 23),
        (538, tb - 25)], fill=52, width=4)
d.line([(513, tb - 13), (528, tb - 11)], fill=52, width=2)   # low branch
d.line([(517, tb - 17), (532, tb - 16)], fill=52, width=2)
d.line([(522, tb - 21), (536, tb - 19)], fill=52, width=2)
d.line([(526, tb - 25), (538, tb - 31)], fill=52, width=2)
d.line([(530, tb - 28), (539, tb - 36)], fill=52, width=2)
# streaming foliage tufts
for x0, y0 in [(524, tb - 27), (530, tb - 20), (533, tb - 31), (536, tb - 24),
               (528, tb - 14), (535, tb - 16)]:
    d.line([(x0, y0), (min(x0 + 6, 539), y0 - 1)], fill=52, width=2)
# leaves torn loose upwind of the crown
d.line([(534, tb - 40), (538, tb - 41)], fill=70, width=1)
d.line([(528, tb - 44), (531, tb - 45)], fill=70, width=1)

# wind-bent grass tufts along the cliff top
for x in [396, 420, 444, 486, 502, 520, 532]:
    yt = ctop(x) + 1
    for k in range(3):
        d.line([(x + k, yt), (x + k + R.uniform(3, 6), yt - R.uniform(3, 7))],
               fill=INK, width=1)

# ================================================================ GULLS fighting the wind (margins)
def gull(bx, by, s=1.0, col=60):
    d.arc([bx - 9 * s, by - 5 * s, bx, by + 3 * s], 200, 340, fill=col, width=2)
    d.arc([bx, by - 6 * s, bx + 9 * s, by + 2 * s], 190, 330, fill=col, width=2)

gull(52, 172)
gull(92, 156, 1.2)
gull(34, 196, 0.9)
gull(128, 184, 1.0)

# ================================================================ NEAR BAND whitecaps
for _ in range(9):
    x = R.uniform(16, W - 30)
    y = R.uniform(282, 298)
    d.arc([x, y - 6, x + 22, y + 5], 180, 360, fill=242, width=2)
    d.line([(x + 22, y), (x + 27, y - 3)], fill=242, width=1)
for _ in range(16):
    x = R.uniform(6, W - 26)
    y = R.uniform(280, 298)
    d.line([(x, y), (x + R.uniform(8, 18), y + R.uniform(-1, 1))], fill=84, width=1)

# ================================================================ FOREGROUND wave band (darkest, laps over rocks)
def b4(x):
    return 300 + 4.5 * math.sin(x / 24.0 + ph[3]) + 2.0 * math.sin(x / 9.0 + ph[4])
pts4 = [(x, b4(x)) for x in range(0, W + 1, 3)]
d.polygon([(0, H)] + pts4 + [(W, H)], fill=FORE)
d.line(pts4, fill=46, width=1)
# foam riding the crest line (varied, gappy — not a machine scallop)
for x in range(6, W - 12, 13):
    if R.random() < 0.3:
        continue
    y = b4(x) + R.uniform(-1, 1)
    wd = R.uniform(9, 18)
    d.arc([x, y - R.uniform(4, 6), x + wd, y + 4], 180, 360, fill=225,
          width=R.choice([1, 2, 2]))
for _ in range(20):
    x = R.uniform(4, W - 4)
    y = R.uniform(304, 316)
    d.line([(x, y), (x + R.uniform(4, 9), y)], fill=R.choice([88, 108]), width=1)

# ================================================================ RAIN (sample-aware slashes, zone-safe, wind-driven)
def zone_clear(x, y):
    if y <= 30:
        return False
    if 152 <= x <= 390 and y <= 226:
        return False
    return True

made = 0
attempts = 0
while made < 200 and attempts < 6000:
    attempts += 1
    x0 = R.uniform(2, W - 12)
    y0 = R.uniform(33, 296)
    ln = R.uniform(12, 20)
    x1 = x0 + ln * 0.5          # wind out of the west: rain drives right
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

# ================================================================ BOTTOM FRINGE: churned spume chop
for x in range(0, W, 3):
    hgt = R.uniform(4, 13)
    d.line([(x, H), (x + R.uniform(-2, 3), H - hgt)], fill=R.choice([46, 50, 54]), width=1)
for x in range(1, W, 7):
    d.line([(x, H), (x + 1, H - R.uniform(2, 7))], fill=R.choice([180, 214]), width=1)

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
