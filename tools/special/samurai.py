# samurai.py -- "THE DUEL AT SUNDOWN" e-ink art scene for M5Paper (540x320, mode L)
# Two samurai facing off before an enormous low sun. Vintage woodcut drama.
# SPECIAL scene: exempt from glyph-zone / date-strip rules (full canvas owned).
import os
import math
import random
from PIL import Image, ImageDraw

W, H = 540, 320
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_PATH = os.path.join(ROOT, "scenes", "special", "samurai.png")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

rng = random.Random(1600)   # Sekigahara

img = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(img)

# ---------------- palette (flat values) ----------------
V_SUN    = 228
V_SUNRIM = 202
V_MIST   = 247
V_RIDGE1 = 206
V_RIDGE2 = 180
V_FIELD  = 148
V_FG     = 96
V_FIG    = 55
V_LEAF   = 98


def smooth(t):
    return t * t * (3 - 2 * t)


def qbez(p0, p1, p2, n=20):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


def fill_below(pts, val):
    d.polygon(pts + [(W, H + 20), (0, H + 20)], fill=val)


def ridge(y_base, amp, phase, freq=0.02):
    pts = []
    for x in range(0, W + 1, 4):
        y = y_base + amp * math.sin(x * freq + phase) + 0.5 * amp * math.sin(x * freq * 2.7 + 2.1 * phase)
        pts.append((x, y))
    return pts


# ---------------- the enormous low sun ----------------
SCX, SCY, SR = 272, 164, 124
d.ellipse((SCX - SR, SCY - SR, SCX + SR, SCY + SR), fill=V_SUN, outline=V_SUNRIM, width=3)

# ---------------- mist bands slicing across the disc ----------------
def mist_band(x0, x1, yc, hh, phase):
    top, bot = [], []
    for x in range(int(x0), int(x1) + 1, 6):
        w = math.sin((x - x0) / (x1 - x0) * math.pi)         # taper the ends
        e = hh * (0.35 + 0.65 * w)
        y = yc + 2.2 * math.sin(x * 0.03 + phase)
        top.append((x, y - e))
        bot.append((x, y + e))
    d.polygon(top + bot[::-1], fill=V_MIST)

mist_band(58, 470, 122, 7, 0.6)
mist_band(120, 540, 196, 8, 2.9)
mist_band(150, 400, 92, 4, 4.2)

# ---------------- birds, upper left ----------------
def bird(x, y, s=7, w=2, v=90):
    d.line([(x - s, y + s * 0.55), (x, y)], fill=v, width=w)
    d.line([(x, y), (x + s, y + s * 0.55)], fill=v, width=w)

bird(64, 56, 8)
bird(94, 42, 6)
bird(116, 60, 5)

# ---------------- distance plane 1: far ridge (buries sun bottom) ----------------
r1 = ridge(230, 5, 0.8)
fill_below(r1, V_RIDGE1)

# pagoda on the far ridge, left flank (built structure #1)
def pagoda(bx, by, s, v):
    # three tiers of flared roofs + spire, chunky silhouette
    for i, (hw, yr) in enumerate([(15, 0), (12, 11), (9, 21)]):
        yy = by - yr * s
        hws = hw * s
        d.polygon([(bx - hws, yy), (bx + hws, yy),
                   (bx + hws * 0.55, yy - 6 * s), (bx - hws * 0.55, yy - 6 * s)], fill=v)
        d.line([(bx - hws, yy), (bx - hws - 2 * s, yy - 2 * s)], fill=v, width=2)  # upturned eave
        d.line([(bx + hws, yy), (bx + hws + 2 * s, yy - 2 * s)], fill=v, width=2)
        if i < 2:
            d.rectangle((bx - hw * 0.5 * s, yy - 11 * s, bx + hw * 0.5 * s, yy - 6 * s), fill=v)
    d.line([(bx, by - 27 * s), (bx, by - 33 * s)], fill=v, width=2)               # spire
    d.ellipse((bx - 1.5, by - 35 * s, bx + 1.5, by - 32 * s), fill=v)

pagoda(62, 232, 1.0, 172)

# ---------------- distance plane 2: nearer ridge with small pines ----------------
r2 = ridge(246, 4, 2.4, 0.025)
fill_below(r2, V_RIDGE2)
for px in (22, 128, 205, 335, 432, 516):
    base = 250 + 2 * math.sin(px * 0.025 + 2.4)
    h = rng.uniform(11, 16)
    hw = rng.uniform(3.5, 5)
    d.polygon([(px, base - h), (px - hw, base - h * 0.35), (px + hw, base - h * 0.35)], fill=168)
    d.polygon([(px, base - h * 0.7), (px - hw * 1.3, base), (px + hw * 1.3, base)], fill=168)

# ---------------- distance plane 3: field band ----------------
r3 = ridge(260, 2.5, 4.9, 0.035)
fill_below(r3, V_FIELD)
# field texture: sparse row strokes
for i in range(60):
    x = rng.uniform(4, 536)
    y = rng.uniform(263, 276)
    ln = rng.uniform(3, 8)
    d.line([(x, y), (x + ln, y)], fill=132, width=1)

# torii gate standing in the field, right flank (built structure #2)
def torii(bx, by, s, v):
    hw = 13 * s
    ht = 24 * s
    d.line([(bx - hw, by), (bx - hw + 1.5 * s, by - ht)], fill=v, width=3)         # posts, slight lean-in
    d.line([(bx + hw, by), (bx + hw - 1.5 * s, by - ht)], fill=v, width=3)
    d.line([(bx - hw - 4 * s, by - ht), (bx + hw + 4 * s, by - ht)], fill=v, width=4)   # kasagi
    d.line([(bx - hw - 4 * s, by - ht), (bx - hw - 5 * s, by - ht - 2.5 * s)], fill=v, width=3)  # upturned tips
    d.line([(bx + hw + 4 * s, by - ht), (bx + hw + 5 * s, by - ht - 2.5 * s)], fill=v, width=3)
    d.line([(bx - hw - 1 * s, by - ht + 6 * s), (bx + hw + 1 * s, by - ht + 6 * s)], fill=v, width=3)  # nuki
    d.line([(bx, by - ht + 6 * s), (bx, by - ht)], fill=v, width=2)                # gakuzuka strut

torii(488, 272, 1.05, 84)

# low mist over the field
mist_band(30, 350, 256, 4, 1.4)

# ---------------- foreground ground band ----------------
def fg_top(x):
    return 276 + 3.0 * math.sin(x * 0.045 + 1.2) + 1.6 * math.sin(x * 0.11 + 4.0)

fg_pts = [(x, fg_top(x)) for x in range(0, W + 1, 3)]
fill_below(fg_pts, V_FG)

# texture strokes inside the band
for i in range(130):
    x = rng.uniform(2, 538)
    y = rng.uniform(fg_top(x) + 3, 316)
    ln = rng.uniform(3, 8)
    ang = rng.uniform(-1.0, -0.4)
    v = rng.choice([72, 80, 118, 126])
    d.line([(x, y), (x + ln * math.cos(ang), y + ln * math.sin(ang))], fill=v, width=1)

# irregular dark fringe along the bottom edge
for i in range(90):
    x = rng.uniform(0, 540)
    y = rng.uniform(308, 319)
    d.line([(x, y), (x + rng.uniform(2, 7), y + rng.uniform(-3, 2))], fill=62, width=1)
for i in range(26):
    x = rng.uniform(0, 540)
    r = rng.uniform(2, 4.5)
    d.ellipse((x - r, 316 - r * 0.7, x + r, 320 + r), fill=58)

# ---------------- the great windswept pine, right edge (big anchor) ----------------
trunk = qbez((522, 312), (516, 210), (492, 118), n=26)
for i in range(len(trunk) - 1):
    t = i / (len(trunk) - 1)
    wdt = int(9 - 6 * t)
    d.line([trunk[i], trunk[i + 1]], fill=58, width=max(2, wdt))
d.polygon([(510, 312), (536, 312), (526, 296)], fill=58)     # root flare
# branches sweep left with the wind
d.line(qbez((508, 170), (472, 158), (446, 160)), fill=58, width=4)
d.line(qbez((498, 138), (462, 120), (428, 118)), fill=58, width=4)
d.line(qbez((492, 118), (474, 96), (452, 88)), fill=58, width=3)
# canopy pads: flat wind-sheared ellipses, overlapped into masses
PADS = [(452, 84, 42, 12), (488, 100, 38, 11), (432, 114, 36, 10),
        (464, 124, 30, 9), (474, 158, 28, 9), (506, 112, 24, 8)]
for (cx, cy, rx, ry) in PADS:
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=60)
# needle texture ticks under the pads
for i in range(40):
    (cx, cy, rx, ry) = rng.choice(PADS)
    px = cx + rng.uniform(-rx, rx)
    py = cy + ry + rng.uniform(-1, 3)
    d.line([(px, py), (px - rng.uniform(1, 3), py + rng.uniform(3, 6))], fill=64, width=1)

# ---------------- ground shadows beneath the duelists ----------------
d.ellipse((84, 280, 182, 296), fill=78)
d.ellipse((342, 282, 466, 298), fill=78)

# ---------------- LEFT SAMURAI: jodan stance, sword raised overhead ----------------
# hakama: wide stance, two flared legs
d.polygon([(112, 214), (152, 214), (176, 286), (146, 286), (133, 252),
           (118, 286), (84, 286)], fill=V_FIG)
# feet
d.rectangle((80, 284, 114, 291), fill=V_FIG)
d.rectangle((144, 284, 180, 291), fill=V_FIG)
# torso, broad-shouldered, leaning toward the foe (overlaps hakama top)
d.polygon([(116, 222), (152, 222), (162, 168), (126, 168)], fill=V_FIG)
# scabbard jutting behind the waist
d.line([(126, 210), (82, 242)], fill=V_FIG, width=5)
# neck
d.rectangle((134, 156, 147, 172), fill=V_FIG)
# arms raised nearly vertical to the high grip (clear of the head)
d.line([(140, 178), (162, 124)], fill=V_FIG, width=9)
d.line([(152, 182), (170, 128)], fill=V_FIG, width=8)
d.ellipse((159, 113, 173, 127), fill=V_FIG)                  # hands
# head + topknot proud of the arm line
d.ellipse((129, 141, 151, 163), fill=V_FIG)
d.ellipse((133, 133, 146, 143), fill=V_FIG)
# headband tail fluttering off the bun, S-curved so it reads as cloth
rib = qbez((134, 139), (120, 130), (112, 137), n=12) + qbez((112, 137), (104, 144), (95, 140), n=12)
d.line(rib, fill=V_FIG, width=3)
d.line(qbez((134, 142), (124, 141), (117, 147)), fill=V_FIG, width=2)
# katana: hilt, tsuba, long blade angled back over the head
d.line([(174, 130), (160, 118)], fill=V_FIG, width=5)
d.ellipse((151, 108, 161, 118), fill=V_FIG)
d.line(qbez((153, 109), (127, 86), (102, 66)), fill=V_FIG, width=4)
d.polygon([(104, 70), (102, 66), (97, 63)], fill=V_FIG)

# ---------------- RIGHT SAMURAI: seigan stance, blade leveled at the foe ----------------
d.polygon([(394, 222), (432, 222), (462, 290), (430, 290), (414, 252),
           (394, 290), (342, 290), (374, 248)], fill=V_FIG)
# feet
d.rectangle((336, 288, 374, 295), fill=V_FIG)
d.rectangle((428, 288, 466, 295), fill=V_FIG)
# torso leaning into the guard
d.polygon([(396, 226), (432, 226), (418, 174), (390, 174)], fill=V_FIG)
# scabbard behind
d.line([(428, 220), (458, 244)], fill=V_FIG, width=4)
# neck
d.rectangle((392, 162, 405, 178), fill=V_FIG)
# arms thrust forward to the grip
d.line([(392, 184), (358, 196)], fill=V_FIG, width=9)
d.line([(406, 190), (362, 202)], fill=V_FIG, width=8)
d.ellipse((348, 190, 364, 206), fill=V_FIG)                  # hands
# head + topknot + headband tail streaming off the bun
d.ellipse((386, 148, 408, 170), fill=V_FIG)
d.ellipse((391, 140, 404, 150), fill=V_FIG)
rib2 = qbez((401, 145), (414, 136), (422, 142), n=12) + qbez((422, 142), (430, 148), (438, 143), n=12)
d.line(rib2, fill=V_FIG, width=3)
d.line(qbez((401, 148), (411, 147), (418, 152)), fill=V_FIG, width=2)
# katana: hilt, tsuba, blade pointing at the opponent
d.line([(362, 202), (348, 196)], fill=V_FIG, width=5)
d.ellipse((340, 189, 350, 199), fill=V_FIG)
d.line(qbez((339, 190), (301, 181), (262, 172)), fill=V_FIG, width=4)
d.polygon([(266, 175), (262, 172), (257, 169)], fill=V_FIG)

# ---------------- storytelling: a straw hat knocked off, lying between them ----------------
d.ellipse((230, 286, 282, 302), fill=124, outline=66, width=1)
d.polygon([(240, 292), (256, 278), (272, 292)], fill=124)
d.line([(240, 292), (256, 280), (272, 292)], fill=66, width=1)
d.line([(256, 280), (256, 290)], fill=66, width=1)

# ---------------- tall wind-blown grass (all leaning left) ----------------
def grass_clump(bx, n, hmax):
    for i in range(n):
        x = bx + (i - n / 2) * rng.uniform(3, 5)
        y0 = fg_top(x) + rng.uniform(0, 4)
        h = rng.uniform(hmax * 0.45, hmax)
        lean = rng.uniform(0.3, 0.5)
        mid = (x - lean * h * 0.4, y0 - h * 0.6)
        tip = (x - lean * h, y0 - h)
        d.line(qbez((x, y0), mid, tip), fill=rng.choice([48, 54, 62]), width=2)

grass_clump(30, 7, 30)
grass_clump(72, 5, 22)
grass_clump(210, 6, 26)
grass_clump(258, 5, 20)
grass_clump(305, 6, 28)
grass_clump(480, 6, 24)
grass_clump(528, 5, 30)
# short scattered blades along the whole edge
for x in range(6, 540, 11):
    y0 = fg_top(x) + 1
    h = rng.uniform(6, 13)
    lean = rng.uniform(0.25, 0.45)
    d.line([(x, y0), (x - lean * h, y0 - h)], fill=58, width=1)

# ---------------- falling leaves drifting on the wind ----------------
def leaf(x, y, s, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(2.6 * s, 0), (0, 1.1 * s), (-2.6 * s, 0), (0, -1.1 * s)]
    d.polygon([(x + px * ca - py * sa, y + px * sa + py * ca) for (px, py) in pts], fill=V_LEAF)
    d.line([(x + 2.6 * s * ca, y + 2.6 * s * sa),
            (x + 3.8 * s * ca, y + 3.8 * s * sa)], fill=V_LEAF, width=1)

for (lx, ly, ls, la) in [(198, 68, 2.4, 0.5), (238, 106, 1.9, -0.4), (176, 132, 2.2, 0.9),
                         (302, 64, 2.1, -0.7), (332, 122, 1.8, 0.3), (220, 162, 2.0, -0.2),
                         (112, 100, 1.9, 0.7), (330, 200, 1.8, -0.5)]:
    leaf(lx, ly, ls, la)

# ---------------- save + verify (special scene: mode/size only) ----------------
img.save(OUT_PATH)

from PIL import Image
img = Image.open(OUT_PATH)
assert img.mode == "L" and img.size == (540, 320)
print("VERIFY OK")
