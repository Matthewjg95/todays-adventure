# -*- coding: utf-8 -*-
"""
v3 scene: "fog" -- HARBOR MIST
Flat-shade layered landscape for the M5Paper (540x320, mode L).
A timber pier runs across the foreground; a dark sloop is moored on the
left beside a net shed, a paler sloop rides further out on the right, and
a third boat is almost dissolved in the fog off the center -- each lighter
than the last. A buoy nods in the middle water, a gull stands on a tall
piling, a cat on the planks watches it, and soft horizontal fog bands
erase the middle distance. A lighthouse on the far breakwater is cut in
half by the mist. Mysterious calm.

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
OUT_PATH = r"C:\Users\matth\Today's Adventure  M5Paper1.1\scenes\v3\fog.png"
SEED = 47
R = random.Random(SEED)

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- palette
INK        = 58
DECK       = 90    # pier planking
SEAM       = 62    # plank seams
FRINGE     = 70    # bottom fringe band
TUFT       = 56    # dock-grass tufts
BOAT1      = 84    # near sloop (darkest)
BOAT2      = 168   # mid sloop
BOAT3      = 206   # far sloop (almost fog)
WATER_FAR  = 214
WATER_MID  = 194
WATER_NEAR = 170
FOG_HI     = 240   # crosses glyph zone -> must be >= 225
FOG_FINGER = 234   # touches glyph zone -> must be >= 225
FOG_C      = 230   # below glyph zone
FOG_D      = 227   # below glyph zone
LHOUSE     = 202
HEADLAND   = 210

# ---------------------------------------------------------------- helpers
def wavy_poly(y_top, y_bot, amp, freq, phase, x0=0, x1=W):
    """Polygon between two wavy horizontal edges."""
    top = [(x, y_top + amp * math.sin(x * freq + phase)
               + 0.5 * amp * math.sin(x * 0.011 + phase * 1.7))
           for x in range(x0, x1 + 1, 6)]
    bot = [(x, y_bot + amp * math.sin(x * freq * 0.8 + phase + 2.1)
               + 0.5 * amp * math.sin(x * 0.013 + phase * 0.6))
           for x in range(x1, x0 - 1, -6)]
    return top + bot

def strokes(y0, y1, x0, x1, n, color, lmin=8, lmax=24, wid=1):
    for _ in range(n):
        x = R.uniform(x0, x1 - lmax)
        y = R.uniform(y0, y1)
        d.line([(x, y), (x + R.uniform(lmin, lmax), y)], fill=color, width=wid)

def sag_rope(a, b, sagpx, color, wid=1):
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0 + 2 * sagpx
    pts = []
    for k in range(17):
        t = k / 16.0
        x = (1 - t) ** 2 * a[0] + 2 * t * (1 - t) * cx + t ** 2 * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * cy + t ** 2 * b[1]
        pts.append((x, y))
    d.line(pts, fill=color, width=wid)

def hull(x0, x1, y_top, y_wl, body, stripe, dark):
    """Chunky sloop hull, bow to the left."""
    d.polygon([(x0 + 8, y_top), (x1 - 3, y_top),
               (x1 - 10, y_wl), (x0 + 18, y_wl)], fill=body)
    d.line([(x0 + 8, y_top + 2), (x1 - 4, y_top + 2)], fill=stripe, width=2)
    d.line([(x0 + 16, y_wl - 1), (x1 - 9, y_wl - 1)], fill=dark, width=3)

# ================================================================ SKY
# pale sun disc lost in the fog (right panel)
d.ellipse([440, 44, 478, 82], fill=244)
# high haze streaks (>=225, may cross glyph zone)
for sy, sx0, sx1 in [(40, 30, 250), (52, 300, 520), (78, 120, 380),
                     (96, 220, 460), (118, 40, 200), (128, 350, 530)]:
    yy = sy + R.uniform(-2, 2)
    d.line([(sx0, yy), (sx1, yy)], fill=FOG_HI, width=2)

# ================================================================ FAR PLANE
# low headland far left, soft trees on its back
d.polygon([(0, 234), (0, 218), (14, 213), (30, 216), (44, 221),
           (54, 227), (58, 234)], fill=HEADLAND)
for tx, th in [(10, 7), (20, 9), (31, 7), (41, 5)]:
    d.line([(tx, 216 + (tx % 3)), (tx, 216 + (tx % 3) - th)], fill=188, width=2)

# breakwater + lighthouse far right (fog will cut its waist)
d.polygon([(492, 236), (496, 228), (540, 226), (540, 236)], fill=LHOUSE)
d.polygon([(508, 229), (511, 176), (521, 176), (524, 229)], fill=LHOUSE)  # tower
d.rectangle([509, 168, 523, 177], fill=188)      # lamp room
d.polygon([(508, 168), (516, 161), (524, 168)], fill=188)  # cap
d.rectangle([513, 170, 519, 175], fill=240)      # lamp glow
d.line([(510, 190), (522, 190)], fill=186, width=2)
d.line([(509, 206), (523, 206)], fill=186, width=2)

# ================================================================ WATER: FAR
def water_fill(y_base, amp, phase, fill):
    top = [(x, y_base + amp * math.sin(x * 0.030 + phase)
              + 1.2 * math.sin(x * 0.011 + phase * 2.0))
           for x in range(0, W + 1, 6)]
    d.polygon(top + [(W, H), (0, H)], fill=fill)

water_fill(231, 2.0, 0.7, WATER_FAR)          # top edge 228..234, glyph-safe
strokes(238, 250, 6, 534, 22, 200)
strokes(236, 248, 6, 534, 10, 228)

# drowned old pilings, mid-left water (storytelling remains)
for px, pt in [(214, 245), (226, 250), (237, 256)]:
    d.rectangle([px - 2, pt, px + 2, 266], fill=188)
    d.ellipse([px - 3, pt - 2, px + 3, pt + 2], fill=178)

# fog fingers chewing the horizon line (>=225: may touch glyph zone)
for fx, fy, fw, fh in [(62, 226, 130, 10), (172, 229, 110, 9),
                       (398, 222, 130, 13), (120, 233, 120, 9)]:
    d.polygon(wavy_poly(fy, fy + fh, 2.5, 0.05, R.uniform(0, 6),
                        x0=fx, x1=fx + fw), fill=FOG_FINGER)

# high fog band across everything far (>=225)
d.polygon(wavy_poly(198, 222, 3.5, 0.023, 1.3), fill=FOG_HI)

# far sloop, a pale ghost in front of the fog (fully below y=221)
hull(296, 356, 226, 240, 196, 210, 182)
d.rectangle([314, 222, 338, 226], fill=196)     # low cabin
d.line([(325, 221), (325, 226)], fill=196, width=2)  # mast stub -> fog
d.line([(306, 243), (322, 243)], fill=200, width=1)  # ghost reflection
d.line([(330, 245), (344, 245)], fill=200, width=1)

# ================================================================ WATER: MID
water_fill(254, 2.2, 2.3, WATER_MID)
strokes(258, 272, 6, 534, 20, 176)
strokes(256, 268, 6, 534, 8, 212)

# fog band C erases the far/mid seam (below glyph zone)
d.polygon(wavy_poly(241, 257, 3.0, 0.027, 4.1), fill=FOG_C)
# lighthouse reflection ghost + fresh ripples poking through the fog
for yy, lx0, lx1 in [(242, 508, 526), (247, 511, 522)]:
    d.line([(lx0, yy), (lx1, yy)], fill=210, width=1)
strokes(246, 256, 20, 520, 10, 186, 10, 22)

# ---- mid sloop, right panel (lighter than the near one) ----------------
d.line([(437, 98), (437, 250)], fill=140, width=2)            # mast
hull(398, 480, 244, 262, BOAT2, 190, 140)
d.rectangle([424, 236, 456, 244], fill=176)                    # cabin
d.ellipse([430, 238, 434, 242], fill=228)
d.ellipse([444, 238, 448, 242], fill=228)
d.line([(437, 232), (470, 232)], fill=150, width=2)            # boom
d.polygon([(437, 226), (468, 229), (437, 232)], fill=154)      # furled sail
for tx in (446, 456, 464):
    d.line([(tx, 227), (tx, 232)], fill=120, width=1)
d.line([(437, 98), (404, 244)], fill=150, width=1)             # forestay
d.line([(437, 98), (474, 244)], fill=150, width=1)             # backstay
d.polygon([(437, 98), (448, 102), (437, 106)], fill=140)       # pennant
for k in range(4):                                             # reflection
    yy = 266 + k * 3
    strokes(yy, yy, 410, 470, 2, 186, 6, 14)

# ================================================================ WATER: NEAR
water_fill(276, 2.0, 4.6, WATER_NEAR)
strokes(281, 300, 6, 534, 16, 148)
strokes(279, 294, 6, 534, 7, 196)

# lowest fog ribbon, thin (below glyph zone)
d.polygon(wavy_poly(266, 275, 2.2, 0.031, 0.4), fill=FOG_D)
# water re-asserts itself below/through the low fog
strokes(276, 282, 10, 530, 12, 150, 10, 26)
strokes(268, 274, 10, 530, 6, 176, 8, 18)

# ---- buoy --------------------------------------------------------------
bx, by = 192, 250
d.polygon([(bx - 7, by + 16), (bx - 5, by), (bx + 5, by), (bx + 7, by + 16)],
          fill=104)
d.rectangle([bx - 6, by + 6, bx + 6, by + 10], fill=INK)       # dark band
d.line([(bx, by - 6), (bx, by)], fill=INK, width=2)            # top mark
d.ellipse([bx - 2, by - 9, bx + 2, by - 5], fill=INK)
d.arc([bx - 13, by + 12, bx + 13, by + 22], 15, 165, fill=140, width=1)
d.arc([bx - 18, by + 14, bx + 18, by + 28], 20, 160, fill=150, width=1)
strokes(by + 22, by + 26, bx - 14, bx + 14, 2, 130, 6, 12)

# ================================================================ NEAR SLOOP (left panel, darkest)
d.line([(101, 50), (101, 252)], fill=INK, width=3)             # mast
d.polygon([(101, 50), (114, 54), (101, 58)], fill=INK)         # pennant
hull(62, 148, 250, 278, BOAT1, 128, 52)
d.rectangle([88, 240, 122, 250], fill=100)                     # cabin
d.ellipse([93, 243, 98, 248], fill=214)                        # portholes
d.ellipse([108, 243, 113, 248], fill=214)
d.line([(101, 234), (138, 234)], fill=70, width=3)             # boom
d.polygon([(101, 226), (136, 230), (101, 234)], fill=110)      # furled sail
for tx in (110, 120, 129):
    d.line([(tx, 227), (tx, 234)], fill=52, width=1)
d.line([(101, 52), (68, 252)], fill=76, width=1)               # forestay
d.line([(101, 52), (143, 252)], fill=76, width=1)              # backstay
d.ellipse([64, 258, 71, 265], fill=136)                        # fenders
d.ellipse([130, 259, 137, 266], fill=136)
for k in range(3):                                             # reflection
    yy = 281 + k * 2
    strokes(yy, yy, 72, 140, 2, 120, 5, 12)

# gulls flying in the left panel sky
for gx, gy, gs in [(64, 66, 5), (94, 55, 6), (124, 74, 4)]:
    d.arc([gx - 2 * gs, gy - gs, gx, gy + gs], 195, 340, fill=82, width=2)
    d.arc([gx, gy - gs, gx + 2 * gs, gy + gs], 200, 345, fill=82, width=2)

# ================================================================ PIER
# deck with stepped plank top edge
edge = []
x = 0
ytop = 286
plank_x = []
while x < W:
    ytop = 284 + R.choice([-3, -2, 0, 1, 2])
    nx = min(W, x + R.randint(20, 32))
    edge += [(x, ytop), (nx, ytop)]
    plank_x.append(nx)
    x = nx
d.polygon(edge + [(W, H), (0, H)], fill=DECK)
for i in range(0, len(edge) - 1, 2):                           # top highlight
    d.line([edge[i], edge[i + 1]], fill=124, width=2)
for px in plank_x[:-1]:                                        # seams
    d.line([(px, 288), (px, H)], fill=SEAM, width=2)
for _ in range(26):                                            # wood grain
    gx = R.uniform(6, 520)
    gy = R.uniform(292, 314)
    d.line([(gx, gy), (gx + R.uniform(6, 14), gy)], fill=76, width=1)

# tall pilings: left (boat1 mooring) and right (gull's perch)
d.rectangle([148, 210, 156, 292], fill=66)
d.ellipse([147, 207, 157, 213], fill=52)
d.rectangle([390, 200, 400, 292], fill=66)
d.ellipse([389, 197, 401, 203], fill=52)
d.line([(390, 214), (400, 212)], fill=48, width=2)             # rope scars
d.line([(148, 224), (156, 222)], fill=48, width=2)

# gull standing on the right piling
d.ellipse([388, 184, 410, 196], fill=242)                      # body
d.ellipse([388, 184, 410, 196], outline=68, width=1)
d.polygon([(392, 186), (404, 194), (390, 194)], fill=120)      # folded wing
d.ellipse([404, 178, 412, 186], fill=242)                      # head
d.ellipse([404, 178, 412, 186], outline=68, width=1)
d.polygon([(411, 181), (417, 183), (411, 185)], fill=INK)      # beak
d.ellipse([408, 180, 410, 182], fill=INK)                      # eye
d.polygon([(388, 188), (382 + 4, 192), (390, 194)], fill=110)  # tail tip
d.line([(396, 196), (396, 200)], fill=INK, width=1)            # legs
d.line([(401, 196), (401, 200)], fill=INK, width=1)

# center bollards with a sagging rope between them
for cx2, ct in [(202, 250), (263, 252), (330, 251)]:
    d.rectangle([cx2 - 5, ct, cx2 + 5, 292], fill=72)
    d.ellipse([cx2 - 6, ct - 3, cx2 + 6, ct + 3], fill=56)
    d.line([(cx2 - 5, ct + 8), (cx2 + 5, ct + 8)], fill=52, width=2)
sag_rope((202, 254), (263, 256), 5, 60, 2)
sag_rope((263, 256), (330, 255), 5, 60, 2)

# lantern on a hook post beside the third bollard (lit)
d.rectangle([352, 246, 356, 292], fill=66)
d.line([(352, 248), (344, 248)], fill=66, width=2)             # arm
d.line([(345, 248), (345, 252)], fill=66, width=1)
d.polygon([(340, 252), (350, 252), (349, 266), (341, 266)], fill=INK)
d.rectangle([343, 255, 347, 263], fill=236)                    # glow
d.line([(341, 266), (349, 266)], fill=INK, width=2)

# mooring ropes (bow of boat1 to deck, stern to piling; boat2 to piling)
sag_rope((70, 256), (44, 288), 6, 64, 2)
sag_rope((140, 256), (151, 226), 3, 64, 1)
sag_rope((406, 248), (395, 226), 3, 120, 1)

# net shed on the left end of the pier
d.polygon([(2, 254), (30, 238), (58, 254)], fill=INK)          # roof
d.rectangle([6, 254, 54, 298], fill=82)
d.rectangle([24, 266, 38, 298], fill=112)                      # door
d.line([(31, 266), (31, 298)], fill=70, width=1)
d.rectangle([12, 262, 20, 270], fill=214)                      # window
d.rectangle([12, 262, 20, 270], outline=52)
d.line([(46, 258), (46, 268)], fill=60, width=1)               # float line
d.ellipse([43, 268, 49, 274], fill=132)
d.ellipse([44, 276, 50, 282], fill=132)

# crab pots stacked at the right (lattice crates)
for (px0, py0, px1, py1) in [(478, 268, 516, 290), (483, 250, 511, 268)]:
    d.rectangle([px0, py0, px1, py1], fill=118)
    d.rectangle([px0, py0, px1, py1], outline=54, width=2)
    for lx in range(px0 + 6, px1 - 3, 8):
        d.line([(lx, py0 + 2), (lx, py1 - 2)], fill=64, width=1)
    d.line([(px0 + 2, (py0 + py1) // 2), (px1 - 2, (py0 + py1) // 2)],
           fill=64, width=1)

# rope coil on the planks (flat spiral of rings, seen at an angle)
d.ellipse([296, 293, 322, 305], outline=56, width=2)
d.ellipse([300, 295, 318, 303], outline=56, width=2)
d.ellipse([304, 297, 314, 301], outline=56, width=2)
d.line([(321, 296), (336, 291)], fill=56, width=2)
d.line([(336, 291), (341, 293)], fill=56, width=2)

# the cat, sitting on the planks, watching the gull
cx, cy = 436, 292                                              # base of cat
d.ellipse([cx - 12, cy - 18, cx + 10, cy], fill=INK)           # haunches
d.polygon([(cx - 11, cy), (cx - 12, cy - 20), (cx - 6, cy - 27),
           (cx + 1, cy - 20), (cx + 3, cy)], fill=INK)         # chest, leaning
d.ellipse([cx - 19, cy - 40, cx - 3, cy - 25], fill=INK)       # head (up-left)
d.polygon([(cx - 19, cy - 34), (cx - 21, cy - 45), (cx - 13, cy - 38)],
          fill=INK)                                            # ear L
d.polygon([(cx - 10, cy - 39), (cx - 7, cy - 46), (cx - 3, cy - 36)],
          fill=INK)                                            # ear R
d.arc([cx + 4, cy - 18, cx + 26, cy + 2], 175, 300, fill=INK, width=3)  # tail

# dock grass tufts along the bottom fringe
d.polygon(wavy_poly(313, 322, 2.5, 0.05, 1.9), fill=FRINGE)
tx = 8
while tx < 532:
    h0 = R.randint(7, 15)
    for k in (-3, 0, 3):
        lean = k + R.uniform(-1.5, 1.5)
        d.line([(tx + k, 320), (tx + k + lean, 320 - h0 + abs(k))],
               fill=TUFT, width=2)
    tx += R.randint(16, 30)

# ================================================================ SAVE + VERIFY
img.save(OUT_PATH)

from PIL import Image as _I
chk = _I.open(OUT_PATH)
assert chk.mode == "L" and chk.size == (540, 320)
z = chk.crop((160, 30, 380, 220))
assert z.getextrema()[0] >= 225, "glyph zone dirty: %d" % z.getextrema()[0]
t = chk.crop((0, 0, 540, 28))
assert t.getextrema()[0] >= 225, "date strip dirty: %d" % t.getextrema()[0]
print("VERIFY OK")
