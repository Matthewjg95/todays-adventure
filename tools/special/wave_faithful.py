# wave_faithful.py -- "The Great Wave off Kanagawa" (Hokusai, 1831)
# Faithful portrait study for M5Paper e-ink: 540x960, PIL mode "L".
# Vertical hanging-scroll recomposition: banded sky top, the great claw wave
# arching over a window where Fuji sits at the horizon, layered swells and
# three oshiokuri boats below. Flat fills + bold line work, no dither.
# Deterministic: random.Random(seed) only.
import os
import math
import random
from PIL import Image, ImageDraw, ImageChops

W, H = 540, 960
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "scenes", "special", "wave_faithful.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

rng = random.Random(1831)  # year of the print

# ---------------- palette (Prussian blue -> grays) ----------------
INK      = 44    # boldest keyblock line
SEA_DEEP = 50    # deepest prussian
SEA_DARK = 80
SEA_MID  = 118
SEA_LT   = 165
FOAM     = 250
FOAM_SHD = 198   # shading inside foam
SKY0     = 212   # top bokashi band
SKY1     = 228
SKY2     = 240
PAPER    = 246
SKYC     = 234   # cloud band near the crest (lets white spray read)
FUJI_V   = 102
SNOW     = 250
HULL     = 206
HULL_IN  = 152
CREW     = 52

img = Image.new("L", (W, H), PAPER)
d = ImageDraw.Draw(img)


# ---------------- geometry helpers ----------------
def qbez(p0, p1, p2, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def cbez(p0, p1, p2, p3, n=32):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out


def stroke(pts, val, w):
    d.line(pts, fill=val, width=w, joint="curve")


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for (x, y) in pts]


def normals(pts):
    """Unit inward normals (down-right of travel) for a l->r polyline."""
    out = []
    n = len(pts)
    for i in range(n):
        j = min(i + 1, n - 1)
        k = max(j - 1, 0)
        dx = pts[j][0] - pts[k][0]
        dy = pts[j][1] - pts[k][1]
        m = math.hypot(dx, dy) or 1.0
        out.append((-dy / m, dx / m))
    return out


def talon(base, ang_deg, length, width, curl=0.5, val=FOAM):
    """A foam claw-finger: curved tapering crescent from base, heading ang_deg
    (degrees, screen coords: 90 = straight down), tip curling by +curl rad."""
    ang = math.radians(ang_deg)
    ax, ay = base
    tx = ax + length * math.cos(ang + curl)
    ty = ay + length * math.sin(ang + curl)
    cx = ax + 0.62 * length * math.cos(ang)
    cy = ay + 0.62 * length * math.sin(ang)
    spine = qbez((ax, ay), (cx, cy), (tx, ty), n=14)
    s1, s2 = [], []
    for i, (px, py) in enumerate(spine):
        t = i / (len(spine) - 1)
        if i < len(spine) - 1:
            dx = spine[i + 1][0] - px
            dy = spine[i + 1][1] - py
        else:
            dx = px - spine[i - 1][0]
            dy = py - spine[i - 1][1]
        m = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / m, dx / m
        wd = width * (1 - t) ** 1.25
        s1.append((px + nx * wd, py + ny * wd))
        s2.append((px - nx * wd, py - ny * wd))
    d.polygon(s1 + s2[::-1], fill=val)


def foam_crown(edge, r_lo, r_hi, every=3, ride=0.1):
    """Scallop circles riding the outer silhouette (cloud crown)."""
    nrm = normals(edge)
    for i in range(0, len(edge), every):
        px, py = edge[i]
        nx, ny = nrm[i]
        r = r_lo + (r_hi - r_lo) * rng.random()
        cx = px - nx * r * ride
        cy = py - ny * r * ride
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=FOAM)


def scalloped_band(edge, d_lo, d_hi, waves=6, amp=0.45, val=FOAM):
    """Foam band between an edge and a scalloped inner offset. Returns inner."""
    nrm = normals(edge)
    inner = []
    n = len(edge)
    for i, (px, py) in enumerate(edge):
        t = i / (n - 1)
        dep = d_lo + (d_hi - d_lo) * t
        dep *= (1 - amp) + amp * math.sin(t * waves * 2 * math.pi)
        nx, ny = nrm[i]
        inner.append((px + nx * dep, py + ny * dep))
    d.polygon(edge + inner[::-1], fill=val)
    return inner


# ============================================================
# 1. SKY -- banded (bokashi) top, cream middle, cloud band near crest
# ============================================================
d.rectangle((0, 0, W, 64), fill=SKY0)
d.rectangle((0, 64, W, 118), fill=SKY1)
d.rectangle((0, 118, W, 168), fill=SKY2)
d.rectangle((0, 168, W, 252), fill=PAPER)
d.rectangle((0, 252, W, 470), fill=SKYC)

# ============================================================
# 2. CARTOUCHE (vertical title box, hanging-scroll style) + seal
# ============================================================
d.rectangle((30, 28, 92, 172), fill=FOAM)
stroke([(30, 28), (92, 28), (92, 172), (30, 172), (30, 28)], INK, 3)
marks = [
    [(46, 46), (76, 46)], [(61, 46), (61, 66)],
    [(46, 74), (76, 70)], [(48, 84), (74, 84)],
    [(50, 96), (72, 102)], [(61, 96), (58, 118)],
    [(46, 126), (76, 126)], [(52, 136), (70, 142)],
    [(48, 152), (74, 156)],
]
for m in marks:
    stroke(m, INK, 4)
d.rectangle((36, 184, 64, 212), fill=140)
stroke([(41, 191), (59, 191)], FOAM, 3)
stroke([(41, 200), (59, 205)], FOAM, 3)

# ============================================================
# 3. HORIZON BANDS (distant calm sea, visible in the window)
# ============================================================
d.rectangle((0, 470, W, 508), fill=SEA_LT)
d.rectangle((0, 508, W, 700), fill=140)
stroke([(0, 470), (W, 470)], 120, 2)

# ============================================================
# 4. FUJI -- small, calm, snow-capped, alone in the window dip
# ============================================================
fj_peak = (460, 390)
fj_bl = (394, 474)
fj_br = (532, 474)
slope_l = cbez(fj_bl, (422, 450), (442, 420), fj_peak, n=26)
slope_r = cbez(fj_peak, (486, 418), (508, 448), fj_br, n=26)
d.polygon(slope_l + slope_r + [(fj_br[0], 474), (fj_bl[0], 474)], fill=FUJI_V)
stroke(slope_l, 60, 2)
stroke(slope_r, 60, 2)
# snow cap with zigzag lower edge
snow_y = 424
sl = [p for p in slope_l if p[1] <= snow_y]
sr = [p for p in slope_r if p[1] <= snow_y]
if sl and sr:
    x0, x1 = sl[0][0], sr[-1][0]
    zig = []
    nteeth = 5
    for i in range(nteeth + 1):
        t = i / nteeth
        zx = x1 + (x0 - x1) * t
        zy = snow_y + (-7 if i % 2 else 7)
        zig.append((zx, zy))
    d.polygon(sl + sr + zig, fill=SNOW)

# ============================================================
# 5. THE GREAT WAVE -- body, then mask-clipped striations
# ============================================================
back = cbez((0, 585), (8, 470), (44, 396), (102, 352), n=30)
up   = cbez((102, 352), (148, 316), (190, 296), (238, 292), n=24)
lobe = cbez((238, 292), (300, 280), (350, 290), (388, 316), n=26)
hook = cbez((388, 316), (432, 340), (444, 376), (404, 398), n=22)
under = cbez((404, 398), (372, 416), (342, 436), (318, 462), n=14)
face = cbez((318, 462), (408, 520), (486, 560), (540, 606), n=40)

body = back + up + lobe + hook + under + face + [(540, 960), (0, 960)]
d.polygon(body, fill=SEA_MID)

# --- all interior detail is drawn clipped to the body polygon ---
body_mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(body_mask).polygon(body, fill=255)
detail = Image.new("L", (W, H), 0)
dmask = Image.new("L", (W, H), 0)
dd = ImageDraw.Draw(detail)
dm = ImageDraw.Draw(dmask)


def dstroke(pts, val, w):
    dd.line(pts, fill=val, width=w, joint="curve")
    dm.line(pts, fill=255, width=w, joint="curve")


def darc(bb, a0, a1, val, w):
    dd.arc(bb, a0, a1, fill=val, width=w)
    dm.arc(bb, a0, a1, fill=255, width=w)


# rhythmic striations on the back of the wave (parallel shifted curves)
back_up = back + up
for dx, dy, val, wd in [(18, 20, SEA_DEEP, 6), (38, 44, SEA_DARK, 4),
                        (60, 72, SEA_DEEP, 6), (84, 104, SEA_DARK, 4),
                        (110, 140, SEA_DEEP, 6), (138, 180, SEA_DARK, 4),
                        (168, 226, SEA_DEEP, 5), (200, 278, SEA_DARK, 4),
                        (234, 336, SEA_DEEP, 5)]:
    dstroke(shift(back_up, dx, dy), val, wd)

# concentric barrel striations on the face (arcs about the curl center);
# sweep kept off the wave's back
CURL = (352, 350)
for r, val, wd, a0, a1 in [(108, SEA_DEEP, 6, 44, 116), (136, FOAM_SHD, 3, 46, 112),
                           (166, SEA_DEEP, 5, 46, 110), (200, SEA_DARK, 5, 48, 106),
                           (236, SEA_DEEP, 5, 50, 104), (274, SEA_DARK, 4, 50, 102),
                           (314, SEA_DEEP, 4, 52, 100)]:
    bb = (CURL[0] - r, CURL[1] - r, CURL[0] + r, CURL[1] + r)
    darc(bb, a0, a1, val, wd)

# dark shadow band tucked under the crest overhang (claws pop against it)
dstroke(shift(lobe + hook, -8, 34), SEA_DEEP, 20)

final_mask = ImageChops.multiply(dmask, body_mask)
img.paste(detail, (0, 0), final_mask)

# --- bold keyblock outline of the silhouette ---
stroke(back + up + lobe + hook, INK, 4)
stroke(under + face, INK, 3)

# --- foam: deep scalloped band, long raking claw fingers, cloud crown ---
crest_edge = up[3:] + lobe + hook
inner = scalloped_band(crest_edge, 14, 44, waves=5, amp=0.5)

# bulk the crest tip so the hook is one solid foam mass
for cx, cy, r in [(400, 350, 17), (416, 368, 15), (408, 386, 13), (388, 332, 15)]:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=FOAM)

# claw fingers: a full fringe, straight down near the lobe,
# raking down-left toward the tip
n_fingers = 10
for i in range(n_fingers):
    t = 0.26 + 0.74 * i / (n_fingers - 1)
    idx = int(t * (len(inner) - 1))
    px, py = inner[idx]
    ang = 90 + 62 * t          # degrees: 90 = down, >90 tilts down-left
    ln = 20 + 52 * t + rng.random() * 6
    talon((px, py), ang, ln, 5 + 5 * t, curl=0.5)

# the terminal great claws spanning the barrel mouth
talon((404, 396), 140, 82, 12, curl=0.5)
talon((418, 376), 127, 66, 10, curl=0.5)
talon((390, 410), 152, 56, 8, curl=0.45)

# cloud crown of scallops riding the outer silhouette
foam_crown(crest_edge, 7, 14, every=3, ride=0.15)


# ============================================================
# 6. BOAT helper
# ============================================================
def boat(cx, cy, L, ang_deg):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)

    def xf(pts):
        return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for (x, y) in pts]

    def blob(cx0, cy0, rx, ry, val):
        pts = [(cx0 + rx * math.cos(2 * math.pi * i / 14),
                cy0 + ry * math.sin(2 * math.pi * i / 14)) for i in range(14)]
        d.polygon(xf(pts), fill=val)

    hl = L / 2.0
    bow = (-hl, -18)     # raised pointed bow (faces up-wave, i.e. left)
    stern = (hl, -8)
    gun = qbez(bow, (0, 4), stern, n=20)
    keel = qbez(bow, (0, 26), stern, n=20)
    hull = xf(gun + keel[::-1])
    d.polygon(hull, fill=HULL)
    stroke(hull + [hull[0]], INK, 3)
    stroke(xf(shift(gun[2:-2], 0, 5)), HULL_IN, 4)
    # rowers: hunched dark figures leaning toward the bow
    n_crew = 5
    for i in range(n_crew):
        x = -hl * 0.42 + (hl * 0.92) * i / (n_crew - 1)
        blob(x, -8, 6.5, 5.5, CREW)          # bent back
        blob(x - 7, -14, 3.6, 3.6, CREW)     # head, forward of body
    # oar strokes into the water
    for i in range(3):
        x = -hl * 0.28 + hl * 0.46 * i
        stroke([xf([(x, -2)])[0], xf([(x - 15, 26)])[0]], INK, 2)


# calm distant swell lines in the window (right of the face)
stroke(qbez((412, 532), (470, 526), (540, 530), n=12), SEA_MID, 2)
stroke(qbez((424, 560), (480, 554), (540, 558), n=12), SEA_MID, 2)

# boat 1: riding the great wave's face, fully inside the body of water
boat(474, 592, 134, 24)

# ============================================================
# 7. MID SWELL -- the Fuji-mimicking hump with its own foam cap
# ============================================================
mid_top = (cbez((0, 690), (60, 636), (130, 582), (205, 568), n=24) +
           cbez((205, 568), (272, 556), (330, 600), (378, 652), n=24) +
           cbez((378, 652), (430, 692), (500, 668), (540, 648), n=20))
d.polygon(mid_top + [(540, 960), (0, 960)], fill=94)
for dx, dy, val, wd in [(0, 18, SEA_DEEP, 5), (0, 46, SEA_DARK, 4),
                        (0, 78, SEA_DEEP, 4)]:
    stroke(shift(mid_top, dx, dy), val, wd)
stroke(mid_top, INK, 3)
cap = [p for p in mid_top if 105 <= p[0] <= 300]
cap_inner = scalloped_band(cap, 8, 18, waves=4, amp=0.4)
for ang, t in ((66, 0.25), (88, 0.5), (108, 0.72), (126, 0.9)):
    idx = int(t * (len(cap_inner) - 1))
    talon(cap_inner[idx], ang, 17 + 9 * rng.random(), 5, curl=0.5)
foam_crown(cap, 4, 9, every=4)

# boat 2: nestled in the trough between the swells
boat(185, 715, 168, -5)

# ============================================================
# 8. FOREGROUND SWELL
# ============================================================
fg_top = (cbez((0, 812), (80, 778), (170, 770), (260, 788), n=24) +
          cbez((260, 788), (350, 808), (430, 772), (540, 758), n=24))
d.polygon(fg_top + [(540, 960), (0, 960)], fill=126)
for dx, dy, val, wd in [(0, 20, SEA_DEEP, 6), (0, 54, SEA_DARK, 5),
                        (0, 92, SEA_DEEP, 4)]:
    stroke(shift(fg_top, dx, dy), val, wd)
stroke(fg_top, INK, 3)
lip_l = [p for p in fg_top if p[0] <= 185]
lip_r = [p for p in fg_top if p[0] >= 425]
scalloped_band(lip_l, 6, 12, waves=3, amp=0.4)
scalloped_band(lip_r, 6, 12, waves=2, amp=0.4)
for ang, t in ((58, 0.35), (84, 0.65), (110, 0.9)):
    idx = int(t * (len(lip_l) - 1))
    talon(lip_l[idx], ang, 15, 4, curl=0.5)

# boat 3: climbing the foreground swell
boat(330, 858, 182, 9)
for k in range(4):
    r = 5 + 3 * rng.random()
    d.ellipse((236 + k * 9 - r, 868 - k * 4 - r, 236 + k * 9 + r, 868 - k * 4 + r), fill=FOAM)

# ============================================================
# 9. BOTTOM TROUGH BAND
# ============================================================
bot = cbez((0, 908), (120, 884), (300, 902), (540, 874), n=30)
d.polygon(bot + [(540, 960), (0, 960)], fill=66)
stroke(bot, INK, 3)
stroke(shift(bot, 0, 22), SEA_DEEP, 5)
foam_crown([p for p in bot if 60 <= p[0] <= 200], 3, 7, every=5)

# ============================================================
# 10. SPRAY -- flecks torn off the claw only (kept tight)
# ============================================================
for _ in range(26):
    x = rng.uniform(348, 440)
    y = rng.uniform(286, 352)
    r = rng.uniform(1.4, 3.2)
    d.ellipse((x - r, y - r, x + r, y + r), fill=FOAM)
for _ in range(16):
    x = rng.uniform(280, 420)
    y = rng.uniform(414, 468)
    r = rng.uniform(1.0, 2.2)
    d.ellipse((x - r, y - r, x + r, y + r), fill=FOAM)
for _ in range(12):
    x = rng.uniform(90, 210)
    y = rng.uniform(266, 296)
    r = rng.uniform(1.2, 2.6)
    d.ellipse((x - r, y - r, x + r, y + r), fill=FOAM)

# ============================================================
# 9. RECOMPOSE -- close the dead sky band
# ============================================================
# The sky reserved y168..252 as empty paper, which read as a hole on
# the panel. Lift everything from the sea up into it and extend the
# deep foreground to fill behind, so the wave breathes into the top
# of the frame instead of floating below a blank strip.
LIFT = 74
SEA_TOP = 252

sea = img.crop((0, SEA_TOP, W, H))
img.paste(sea, (0, SEA_TOP - LIFT))

# extend the darkest foreground water into the gap left at the bottom
tail = img.crop((0, H - LIFT - 30, W, H - LIFT))
img.paste(tail.resize((W, LIFT + 30)), (0, H - LIFT - 30))
for i in range(3):
    y = H - LIFT + 6 + i * 22
    stroke(cbez((0, y), (150, y - 7), (380, y + 7), (W, y - 4), n=20),
           SEA_DEEP if i % 2 else SEA_DARK, 4)

# retune the sky bands to the new proportions
d.rectangle((0, 0, W, 58), fill=SKY0)
d.rectangle((0, 58, W, 104), fill=SKY1)
d.rectangle((0, 104, W, SEA_TOP - LIFT), fill=SKY2)

# redraw the cartouche + seal on top of the reworked sky
d.rectangle((30, 28, 92, 172), fill=FOAM)
stroke([(30, 28), (92, 28), (92, 172), (30, 172), (30, 28)], INK, 3)
for m in marks:
    stroke(m, INK, 4)
d.rectangle((36, 184, 64, 212), fill=140)
stroke([(41, 191), (59, 191)], FOAM, 3)
stroke([(41, 200), (59, 205)], FOAM, 3)

# ============================================================
# SAVE + VERIFY
# ============================================================
img.save(OUT)
chk = Image.open(OUT)
assert chk.mode == "L", f"mode {chk.mode}"
assert chk.size == (540, 960), f"size {chk.size}"
ext = chk.getextrema()
assert 40 <= ext[0] and ext[1] <= 250, f"extrema {ext}"
print(f"mode={chk.mode} size={chk.size} extrema={ext}")
print("VERIFY OK")
