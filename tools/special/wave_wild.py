"""wave_wild.py -- The Great Wave off Kanagawa (Hokusai, 1831), wild-card take.

Vertical hanging-scroll recomposition for a 540x960 portrait 16-gray e-ink
panel. The wave is exaggerated into a full-height tower: it climbs the whole
left flank of the scroll, breaks at the top, and its claw crest hangs over a
small, calm Fuji tucked in the dip below. Two oshiokuri boats work the swells
underneath. Flat fills, bold woodblock line, no dither.

Deterministic: random.Random(1831) only.
"""

import math
import os
import random

from PIL import Image, ImageDraw

W, H = 540, 960

# ---- palette (Prussian blue -> dark grays, cream -> light grays) ----
INK = 42        # boldest line work
DEEP = 76       # deep water body
DEEPER = 62     # foreground water
DARKST = 54     # dark stripe groove
MIDW = 118      # mid water stripe
PALE = 162      # pale water stripe
FOAM = 246      # foam / snow / cream
SKY = 236       # sky base
FUJI_BODY = 106
HULL = 58
FIG = 46        # rowers

rng = random.Random(1831)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "scenes", "special", "wave_wild.png")


# ---------------------------------------------------------------- helpers
def bez(ps, n=80):
    """Sample a bezier with arbitrary control points (de Casteljau)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        pp = list(ps)
        while len(pp) > 1:
            pp = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1])
                  for a, b in zip(pp[:-1], pp[1:])]
        pts.append(pp[0])
    return pts


def chain(segs, n=80):
    """Join bezier segments into one polyline."""
    out = []
    for s in segs:
        p = bez(s, n)
        if out:
            p = p[1:]
        out += p
    return out


def normals(pts):
    ns = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        ns.append((-ty / l, tx / l))
    return ns


def tangents(pts):
    ts = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        ts.append((tx / l, ty / l))
    return ts


def offset(pts, ns, d):
    return [(p[0] + n[0] * d, p[1] + n[1] * d) for p, n in zip(pts, ns)]


def resample_idx(pts, step):
    idxs = [0]
    acc = 0.0
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if acc >= step:
            idxs.append(i)
            acc = 0.0
    return idxs


def inward_sign(pts, ns, mask):
    """+1 if +normal points into the mask, else -1 (majority vote)."""
    votes = 0
    step = max(1, (len(pts) - 20) // 15)
    for i in range(10, len(pts) - 10, step):
        for s, w in ((1, 1), (-1, -1)):
            x = int(pts[i][0] + s * ns[i][0] * 12)
            y = int(pts[i][1] + s * ns[i][1] * 12)
            if 0 <= x < W and 0 <= y < H and mask.getpixel((x, y)) > 0:
                votes += w
    return 1 if votes >= 0 else -1


def inside(mask, x, y):
    return 0 <= x < W and 0 <= y < H and mask.getpixel((int(x), int(y))) > 0


def draw_clipped(d, pts, mask, color, width):
    """Draw a polyline only where it stays inside the mask."""
    run = []
    for p in pts:
        if inside(mask, p[0], p[1]):
            run.append(p)
        else:
            if len(run) > 2:
                d.line(run, fill=color, width=width, joint="curve")
            run = []
    if len(run) > 2:
        d.line(run, fill=color, width=width, joint="curve")


def talon(d, p, t, n_out, L, wdt, up=0.42, fwd=1.05, ink=INK, lw=2):
    """One foam finger: crescent talon rooted at p, hooking along +t.

    up/fwd weight the tip's reach along the outward normal vs the tangent:
    high up = finger hangs away from the crest, high fwd = lies along it.
    """
    tip = (p[0] + n_out[0] * L * up + t[0] * L * fwd,
           p[1] + n_out[1] * L * up + t[1] * L * fwd)
    r1 = (p[0] - t[0] * wdt * 0.55, p[1] - t[1] * wdt * 0.55)
    r2 = (p[0] + t[0] * wdt * 0.75, p[1] + t[1] * wdt * 0.75)
    c1 = (r1[0] + n_out[0] * L * min(1.0, up + 0.5) + t[0] * L * 0.12,
          r1[1] + n_out[1] * L * min(1.0, up + 0.5) + t[1] * L * 0.12)
    c2 = (r2[0] + n_out[0] * L * up * 0.62 + t[0] * L * fwd * 0.45,
          r2[1] + n_out[1] * L * up * 0.62 + t[1] * L * fwd * 0.45)
    s1 = bez([r1, c1, tip], 20)     # outer convex edge
    s2 = bez([r2, c2, tip], 20)     # inner concave edge
    d.polygon(s1 + s2[::-1], fill=FOAM)
    d.line(s1, fill=ink, width=lw, joint="curve")
    d.line(s2, fill=ink, width=lw, joint="curve")


def boat(d, prow, stern, sag=24, depth=19, nrow=5):
    """Oshiokuri-bune: slim banana hull, upswept prow, hunched rowers."""
    mx = ((prow[0] + stern[0]) / 2, (prow[1] + stern[1]) / 2 + sag)
    sheer = bez([prow, mx, stern], 40)
    keel = []
    n = len(sheer)
    for i, p in enumerate(sheer):
        dep = depth * math.sin(math.pi * i / (n - 1)) ** 0.7 + 3
        keel.append((p[0], p[1] + dep))
    tdx, tdy = prow[0] - mx[0], prow[1] - mx[1]
    tl = math.hypot(tdx, tdy) or 1.0
    tip = (prow[0] + tdx / tl * 20, prow[1] + tdy / tl * 20 - 5)
    hull = [tip] + sheer + keel[::-1]
    d.polygon(hull, fill=HULL)
    d.line([tip] + sheer, fill=INK, width=3, joint="curve")
    d.line(keel, fill=INK, width=2, joint="curve")
    d.line([(p[0], p[1] + 4) for p in sheer[3:-3]], fill=205, width=3,
           joint="curve")
    lean = 1 if prow[0] < stern[0] else -1
    for f in [0.24 + k * (0.58 / max(1, nrow - 1)) for k in range(nrow)]:
        p = sheer[int(f * (n - 1))]
        hx, hy = p[0] - lean * 4, p[1] - 11
        d.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=FIG)
        d.line([(hx + lean * 2, hy + 3), (p[0] + lean * 8, p[1] + 1)],
               fill=FIG, width=5)
        d.line([(p[0] + lean * 5, p[1] + 4),
                (p[0] + lean * 18, p[1] + 17)], fill=FIG, width=2)


# ---------------------------------------------------------------- canvas
img = Image.new("L", (W, H), SKY)
d = ImageDraw.Draw(img)

# ---- banded sky (hanging-scroll bands, flat) ----
for y0, y1, v in [(0, 44, 206), (58, 96, 221), (110, 132, 224),
                  (460, 478, 221)]:
    d.rectangle([0, y0, W, y1], fill=v)

# ---------------------------------------------------------------- Fuji
apex = (355, 425)
bl, br = (258, 548), (455, 548)
left_e = bez([apex, (312, 480), bl], 30)
right_e = bez([apex, (400, 480), br], 30)
d.polygon(left_e + [bl, br] + right_e[::-1], fill=FUJI_BODY)
d.line(left_e, fill=INK, width=3, joint="curve")
d.line(right_e, fill=INK, width=3, joint="curve")
snow = [apex, (394, 473), (378, 458), (366, 474), (355, 459),
        (343, 475), (330, 457), (317, 473)]
d.polygon(snow, fill=FOAM)
d.line(snow + [apex], fill=INK, width=2, joint="curve")

# ---------------------------------------------------------------- sea
S1 = chain([[(540, 542), (448, 512), (352, 552)],
            [(352, 552), (280, 585), (206, 600)]], 40)
sea_poly = S1 + [(150, 700), (150, H), (540, H)]
d.polygon(sea_poly, fill=DEEP)

sea_mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(sea_mask).polygon(sea_poly, fill=255)

for pts, col, wd in [
        (bez([(210, 644), (330, 612), (470, 642), (540, 630)], 40), MIDW, 4),
        (bez([(230, 692), (360, 660), (540, 678)], 40), MIDW, 3),
        (bez([(300, 724), (420, 700), (540, 714)], 40), PALE, 2)]:
    draw_clipped(d, pts, sea_mask, col, wd)

# ---- swell 1: foam crest with small leftward claws ----
s1n = normals(S1)
sgn = inward_sign(S1, s1n, sea_mask)
s1out = [(-sgn * n[0], -sgn * n[1]) for n in s1n]
s1t = tangents(S1)          # travel: right -> left
d.line(offset(S1, s1out, 4), fill=FOAM, width=10, joint="curve")
d.line(S1, fill=INK, width=2, joint="curve")
for i in resample_idx(S1, 42)[1:-1]:
    L = rng.uniform(20, 34)
    talon(d, offset([S1[i]], [s1out[i]], 1)[0], s1t[i], s1out[i],
          L, L * 0.24, up=0.28, fwd=1.15)

# ---------------------------------------------------------------- boat 1
boat(d, (256, 648), (474, 708), sag=24, depth=19, nrow=5)
for _ in range(4):  # splash at the prow
    x = 247 + rng.uniform(-9, 10)
    y = 654 + rng.uniform(-6, 10)
    r = rng.uniform(2, 3.6)
    d.ellipse([x - r, y - r, x + r, y + r], fill=FOAM, outline=INK, width=1)

# ---- swell 2: foreground crest; boat 2 rides half-hidden behind it ----
S2 = chain([[(0, 776), (90, 748), (200, 762)],
            [(200, 762), (300, 786), (420, 812)],
            [(420, 812), (480, 818), (540, 806)]], 40)
fg_poly = S2 + [(540, H), (0, H)]
fg_mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(fg_mask).polygon(fg_poly, fill=255)

boat(d, (110, 716), (306, 758), sag=20, depth=17, nrow=4)   # boat 2

d.polygon(fg_poly, fill=DEEPER)          # swell fill covers its lower hull
for pts in [bez([(60, 870), (220, 840), (420, 880), (540, 862)], 40),
            bez([(0, 920), (180, 900), (380, 930), (540, 916)], 40)]:
    draw_clipped(d, pts, fg_mask, 104, 3)

s2n = normals(S2)
sgn2 = inward_sign(S2, s2n, fg_mask)
s2out = [(-sgn2 * n[0], -sgn2 * n[1]) for n in s2n]
s2t = tangents(S2)          # travel: left -> right, so hook along -t
d.line(offset(S2, s2out, 4), fill=FOAM, width=11, joint="curve")
d.line(S2, fill=INK, width=2, joint="curve")
for i in resample_idx(S2, 48)[1:-1]:
    L = rng.uniform(18, 30)
    talon(d, offset([S2[i]], [s2out[i]], 1)[0],
          (-s2t[i][0], -s2t[i][1]), s2out[i], L, L * 0.24,
          up=0.28, fwd=1.15)

# ---------------------------------------------------------------- GREAT WAVE
A = [(0, 565), (42, 448), (88, 300), (210, 172)]
B = [(210, 172), (300, 80), (430, 74), (478, 162)]
C = [(478, 162), (500, 228), (458, 294), (386, 308)]
D = [(386, 308), (300, 332), (233, 398), (205, 470)]
E = [(205, 470), (172, 560), (178, 645), (225, 700)]
crest = chain([A, B, C, D, E])                    # 401 pts, 80 per segment
base = [(170, 800), (120, 960), (0, 960)]
wave_poly = crest + base

wave_mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(wave_mask).polygon(wave_poly, fill=255)

d.polygon(wave_poly, fill=DEEP)

cn = normals(crest)
sgnw = inward_sign(crest, cn, wave_mask)
n_in = [(sgnw * n[0], sgnw * n[1]) for n in cn]
n_out = [(-n[0], -n[1]) for n in n_in]
ct = tangents(crest)

# ---- interior: streamlines that sweep up the tower and spiral into the eye
EYE = (352, 205)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


curl_ks = [0.07, 0.16, 0.26, 0.36, 0.46, 0.56]
for j, k in enumerate(curl_ks):
    use = (A, B, C, D) if k < 0.34 else (A, B, C)   # inner bands stop early
    segs = []
    for seg in use:
        segs.append([lerp(p, EYE, k) for p in seg])
    pts = chain(segs, 50)
    col = [MIDW, DARKST][j % 2] if j % 3 != 2 else PALE
    draw_clipped(d, pts, wave_mask, col, 5 if j % 2 == 0 else 4)

# base flow: water being drawn up into the tower
for j in range(7):
    p0 = (6 + j * 24, 958)
    p1 = (22 + j * 22, 800 - j * 10)
    p2 = (118 + j * 16, 600 + j * 40)
    pts = bez([p0, p1, p2], 50)
    col = PALE if j == 3 else [MIDW, DARKST][j % 2]
    draw_clipped(d, pts, wave_mask, col, 4)

# thin foam streamers running down the concave face
for p0, p1, p2 in [((305, 330), (256, 420), (246, 528)),
                   ((262, 364), (226, 460), (226, 560)),
                   ((228, 404), (206, 496), (214, 590))]:
    d.line(bez([p0, p1, p2], 30), fill=FOAM, width=2, joint="curve")

# ---- foam crest: back-slope edge, scallops over the top, then the claws
d.line(offset(crest[:81], n_out[:81], 4), fill=FOAM, width=9, joint="curve")
BC_top = crest[70:165]      # over the apex
BC_out = n_out[70:165]
d.line(offset(BC_top, BC_out, 5), fill=FOAM, width=13, joint="curve")
for i in [70 + j for j in resample_idx(BC_top, 30)]:
    r = rng.uniform(7, 12)
    p = offset([crest[i]], [n_out[i]], 6)[0]
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
              fill=FOAM, outline=INK, width=2)
d.line(offset(BC_top, BC_out, 4), fill=FOAM, width=11, joint="curve")
d.line(offset(crest[150:321], n_out[150:321], 3), fill=FOAM, width=9,
       joint="curve")
d.line(crest[:321], fill=INK, width=2, joint="curve")

# claws over the top of the breaking crest, thrown forward
for i in [88 + j for j in resample_idx(crest[88:150], 30)]:
    L = rng.uniform(20, 30)
    talon(d, offset([crest[i]], [n_out[i]], 3)[0], ct[i], n_out[i],
          L, L * 0.24)

# the claws: a dense fringe of small talons plus long feature claws
fringe = [i for i in resample_idx(crest, 20) if 150 <= i <= 314]
for i in fringe:
    frac = (i - 150) / 164
    L = 14 + 24 * math.sin(math.pi * frac) ** 1.2 + rng.uniform(-2, 2)
    talon(d, offset([crest[i]], [n_out[i]], 2)[0], ct[i], n_out[i],
          L, L * 0.17, up=0.55, fwd=0.90)
claw_zone = [i for i in resample_idx(crest, 58)
             if 190 <= i <= 300]
for i in claw_zone:
    frac = (i - 150) / 164
    L = 44 + 20 * math.sin(math.pi * frac) ** 1.1 + rng.uniform(-3, 3)
    talon(d, offset([crest[i]], [n_out[i]], 3)[0], ct[i], n_out[i],
          L, L * 0.16, up=0.68, fwd=0.80)

# base edge against the sea + ink face line
d.line([(225, 700)] + base[:2], fill=INK, width=3, joint="curve")
d.line(crest[320:], fill=INK, width=3, joint="curve")

# ---------------------------------------------------------------- spray
def dot(x, y, r):
    if inside(wave_mask, x, y):
        return
    d.ellipse([x - r, y - r, x + r, y + r], fill=FOAM, outline=INK, width=1)


for _ in range(50):        # burst off the curl tip, outside the body only
    x = rng.gauss(500, 34)
    y = rng.gauss(244, 58)
    if 0 <= x < W - 4 and 20 <= y < 424:
        dot(x, y, rng.uniform(2, 4))
for _ in range(12):        # flecks above the apex
    dot(rng.uniform(280, 450), rng.uniform(30, 68), rng.uniform(1.8, 3.5))
for _ in range(8):         # flecks drifting over the back slope
    dot(rng.uniform(130, 290), rng.uniform(64, 130), rng.uniform(1.6, 3))
for i in claw_zone:        # droplets shed below the hanging claw tips
    if i < 238:
        continue
    p = crest[i]
    for k in range(2):
        dot(p[0] + n_out[i][0] * (74 + k * 18) + rng.uniform(-7, 7),
            p[1] + n_out[i][1] * (74 + k * 18) + rng.uniform(-7, 7),
            rng.uniform(2, 3.6))

# ---------------------------------------------------------------- cartouche
cx0, cy0, cx1, cy1 = 494, 26, 532, 156
d.rectangle([cx0, cy0, cx1, cy1], fill=FOAM, outline=INK, width=3)
gy = cy0 + 13
while gy < cy1 - 12:                      # abstract brush glyphs
    gx = (cx0 + cx1) / 2 + rng.uniform(-2.5, 2.5)
    gw = rng.uniform(9, 15)
    tilt = rng.uniform(-2.5, 2.5)
    d.line([(gx - gw / 2, gy - tilt), (gx + gw / 2, gy + tilt)],
           fill=INK, width=3)
    if rng.random() < 0.7:                # falling diagonal tick
        d.line([(gx + rng.uniform(-4, 2), gy + 2),
                (gx + rng.uniform(2, 6), gy + rng.uniform(7, 10))],
               fill=INK, width=2)
    if rng.random() < 0.5:                # vertical stem
        sx = gx + rng.uniform(-3, 3)
        d.line([(sx, gy - 4), (sx, gy + 5)], fill=INK, width=2)
    gy += 17
d.rectangle([500, 164, 526, 190], outline=150, width=3)   # artist's seal

# ---------------------------------------------------------------- save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)

chk = Image.open(OUT)
assert chk.mode == "L", chk.mode
assert chk.size == (W, H), chk.size
print("mode:", chk.mode, "size:", chk.size, "extrema:", chk.getextrema())
print("VERIFY OK")
