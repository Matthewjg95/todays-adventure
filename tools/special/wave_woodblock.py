"""The Great Wave off Kanagawa (Hokusai, 1831) -- flat woodblock minimal.

Portrait (hanging-scroll) recomposition for a 16-gray e-ink panel.
540x960, PIL mode "L", flat planes + bold keylines, deterministic.

The wave is a giant "C" opening to the right: concave back on the left,
a foam claw-arm reaching right past the body, a deep scoop under the tip,
and the mouth of the C holding the trough, a boat, the far swell, and a
small calm Fuji. Foam fingers hang from the arm like a dripping curtain.
"""
import math
import os
import random

from PIL import Image, ImageDraw

W, H = 540, 960
S = 2  # supersample factor (crisper keylines after LANCZOS downsize)
SEED = 1831
rng = random.Random(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "scenes", "special",
                                    "wave_woodblock.png"))

# ---- the flat planes (Prussian blue -> dark grays) -------------------------
INK = 40      # keyline
SEA = 70      # deep water
SEA2 = 118    # inner wave band (lighter blue)
FUJI = 100    # mountain body
DIST = 152    # distant water
BAND1 = 205   # top sky band
BAND2 = 224   # mid sky band
CREAM = 238   # paper sky
FOAM = 250    # foam / snow
HULL = 192    # boat wood
PALE = 206    # the wave's hollow breast (nearly sky, like the print)

HORIZON = 560

img = Image.new("L", (W * S, H * S), CREAM)
d = ImageDraw.Draw(img)


def sc(pts):
    return [(x * S, y * S) for (x, y) in pts]


def catmull(pts, n=16):
    if len(pts) < 3:
        return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def fill(pts, color):
    d.polygon(sc(pts), fill=color)


def stroke(pts, color, wd, smooth=True, n=16):
    q = catmull(pts, n) if smooth else list(pts)
    d.line(sc(q), fill=color, width=max(1, int(round(wd * S))), joint="curve")


def lobes(anchors, depth, sign=1.0):
    """Rounded scallop lobes bulging along the path normal."""
    out = [anchors[0]]
    for a, b in zip(anchors, anchors[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = sign * dy / L, -sign * dx / L
        for t in (0.25, 0.5, 0.75):
            bulge = depth * math.sin(math.pi * t)
            out.append((a[0] + dx * t + nx * bulge, a[1] + dy * t + ny * bulge))
        out.append(b)
    return out


def finger(base, aim_deg, length, width, curl):
    """Tapered foam finger polygon. aim in degrees, screen coords (y down)."""
    a = math.radians(aim_deg)
    steps = 12
    left, right = [], []
    x, y = base
    for i in range(steps + 1):
        t = i / steps
        hw = max(0.5, width * 0.5 * (1 - t) ** 0.7)
        nx, ny = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
        left.append((x + nx * hw, y + ny * hw))
        right.append((x - nx * hw, y - ny * hw))
        x += (length / steps) * math.cos(a)
        y += (length / steps) * math.sin(a)
        a += curl / steps
    return left + right[::-1]


def draw_finger(base, aim_deg, length, width, curl=-0.4):
    poly = finger(base, aim_deg, length, width, curl)
    q = catmull(poly, 5)
    d.polygon(sc(q), fill=FOAM)
    d.line(sc(q + [q[0]]), fill=INK, width=int(2.2 * S), joint="curve")


def boat(topline, botline, rower_xs, oar=26):
    hull = catmull(topline, 10) + catmull(botline, 10)
    d.polygon(sc(hull), fill=HULL)
    d.line(sc(hull + [topline[0]]), fill=INK, width=int(2.6 * S),
           joint="curve")
    top_pts = catmull(topline, 24)
    for rx in rower_xs:
        bx, by = min(top_pts, key=lambda p: abs(p[0] - rx))
        d.ellipse([(bx - 6) * S, (by - 11) * S, (bx + 6) * S, (by + 1) * S],
                  fill=45)
        d.line(sc([(bx, by - 2), (bx - oar, by + 16)]), fill=INK,
               width=int(2.2 * S))


# ============================================================= 1. SKY BANDS
# banded sky: dark strip up top, cream, then a wide gray field that the
# white claw and Fuji's snow can cut against (the print's bokashi sky)
d.rectangle([0, 0, W * S, 56 * S], fill=198)
d.rectangle([0, 100 * S, W * S, 140 * S], fill=BAND2)
d.rectangle([0, 190 * S, W * S, HORIZON * S], fill=216)

# ============================================================= 2. DISTANT SEA
d.rectangle([0, HORIZON * S, W * S, H * S], fill=DIST)

# ============================================================= 3. MOUNT FUJI
fl = [(410, 556), (429, 518), (445, 488), (456, 472), (469, 486),
      (487, 518), (504, 554)]
fill(catmull(fl, 14) + [(504, 556), (410, 556)], FUJI)
snow = [(435, 500), (445, 488), (456, 472), (469, 486), (475, 498),
        (467, 490), (461, 502), (453, 492), (447, 504), (441, 494)]
fill(snow, FOAM)
stroke(fl, INK, 3)
stroke([(410, 556), (504, 556)], INK, 2, smooth=False)

# ============================================================= 4. GREAT WAVE
back = [(0, 930), (30, 790), (48, 660), (58, 540), (64, 440), (76, 352),
        (94, 296), (122, 254), (162, 230), (204, 220)]
crest = (245, 216)
arm_outer = [(300, 216), (360, 222), (420, 244), (462, 278), (482, 320),
             (470, 398)]
tip = (442, 432)
arm_inner = [(438, 398), (430, 354), (406, 314), (370, 288), (328, 270),
             (290, 262)]
throat = (256, 264)
scoop = [(408, 464), (372, 506), (344, 552), (328, 600), (330, 648),
         (344, 684), (368, 712), (400, 728)]

# the arm's outer edge churns: rounded cumulus lobes, not glass
top_lobed = lobes([crest] + arm_outer + [tip], 8, sign=1.0)

sil = (catmull(back + [crest], 14) + catmull(top_lobed, 6)
       + catmull([tip] + scoop, 14)
       + [(418, 744), (428, 800), (432, 880), (432, 960), (0, 960)])
fill(sil, SEA2)  # the body core; dark and pale come in as planes

# bold dark bands (the Prussian blue) along the back
stroke([(12, 900), (40, 768), (54, 648), (64, 538), (72, 446), (86, 360),
        (106, 302), (140, 262), (180, 240)], SEA, 20)
stroke([(0, 940), (24, 820), (38, 700), (48, 580), (56, 500)], SEA, 12)
# parallel diagonals inside the shoulder (layered woodblock blues)
stroke([(148, 720), (164, 580), (176, 452), (194, 348), (224, 284)], SEA, 9)
stroke([(112, 800), (130, 660), (142, 530), (156, 420)], FOAM, 4)

# the hollow breast: nearly sky-pale, so the mouth reads as carved air
breast = [(262, 296), (300, 292), (340, 298), (378, 316), (410, 350),
          (428, 386), (434, 418), (408, 464), (372, 506), (344, 552),
          (328, 600), (330, 648), (344, 684), (368, 712), (400, 728),
          (372, 752), (330, 768), (292, 762), (272, 730), (262, 660),
          (258, 560), (258, 440), (258, 340)]
fill(catmull(breast + [(262, 296)], 8), PALE)

# darkest accent right under the lip (the deep blue beneath the curl)
stroke([(434, 412), (424, 368), (400, 324), (364, 294), (320, 278),
        (282, 274)], SEA, 13)

# streak trails arcing down the concave face
stroke([(300, 330), (320, 410), (326, 488), (312, 564), (300, 634),
        (310, 694)], SEA2, 9)
stroke([(272, 330), (290, 412), (296, 490), (284, 566), (276, 636)], FOAM, 6)
stroke([(330, 372), (348, 442), (350, 514), (336, 588), (330, 650),
        (344, 706)], FOAM, 5)
stroke([(396, 470), (362, 512), (336, 556), (322, 602), (324, 648),
        (338, 682), (360, 708)], SEA2, 7)

# --- foam: the claw arm only (the long back stays blue, like the print) -----
arm_under = lobes([tip] + arm_inner + [throat], 7, sign=1.0)
foam_poly = (catmull([(168, 246), (205, 230)] + top_lobed, 8)
             + catmull(arm_under, 8)
             + catmull([(220, 258), (192, 260)], 8)
             + [(168, 246)])
fill(foam_poly, FOAM)

# keylines
stroke(back + [crest], INK, 5)
stroke(top_lobed, INK, 5, n=6)
stroke(arm_under + [(220, 258), (192, 260)], INK, 3, n=8)
stroke([tip] + scoop, INK, 4)

# ragged claws trailing off the tip, continuing the curl
draw_finger((462, 396), 100, 26, 9, -0.5)
draw_finger((452, 416), 115, 20, 8, -0.5)

# --- claw fingers: a dripping curtain, all hanging down with a left hook ----
fingers = [
    ((434, 414), 128, 44, 11, -0.50),
    ((428, 366), 120, 84, 15, -0.45),
    ((410, 322), 115, 56, 15, -0.40),
    ((384, 296), 111, 106, 18, -0.38),
    ((350, 278), 107, 66, 16, -0.35),
    ((318, 266), 104, 94, 17, -0.32),
    ((288, 262), 100, 58, 14, -0.28),
    ((260, 266), 96, 40, 12, -0.25),
]
for base, aim, ln, wd, cu in fingers:
    draw_finger(base, aim, ln, wd, cu)
# tiny secondary drips between the big fingers
for base, aim, ln, wd, cu in [((422, 344), 117, 20, 7, -0.4),
                              ((368, 286), 109, 22, 7, -0.35),
                              ((336, 271), 105, 18, 6, -0.3),
                              ((275, 263), 98, 16, 6, -0.25)]:
    draw_finger(base, aim, ln, wd, cu)

# ============================================================= 5. SPRAY
for _ in range(7):
    ang = rng.uniform(-0.9, 1.4)
    r = rng.uniform(18, 48)
    cx = 498 + r * math.cos(ang) * 0.7
    cy = 416 + r * math.sin(ang)
    rad = rng.uniform(2.5, 5.0)
    d.ellipse([(cx - rad) * S, (cy - rad) * S, (cx + rad) * S,
               (cy + rad) * S], fill=FOAM, outline=INK, width=S)

# ============================================================= 6. FG SWELL
sw_top = [(540, 600), (508, 588), (478, 596), (452, 618), (424, 650),
          (394, 690), (352, 732), (300, 772), (240, 814), (196, 884),
          (182, 960)]
fill(catmull(sw_top, 14) + [(182, 960), (540, 960)], SEA)
swf_outer = [(540, 600), (508, 588), (478, 596), (452, 618), (432, 638)]
swf_inner = lobes([(432, 638), (468, 636), (504, 622), (540, 634)], 6,
                  sign=1.0)
fill(catmull(swf_outer, 12) + catmull(swf_inner, 8), FOAM)
stroke(sw_top, INK, 4)
stroke(swf_inner, INK, 2.4, n=8)
for base, aim, ln, wd in [((454, 626), 118, 26, 9),
                          ((436, 642), 105, 18, 8),
                          ((476, 606), 128, 20, 8)]:
    draw_finger(base, aim, ln, wd)

# ============================================================= 7. BOAT ONE
boat(topline=[(216, 724), (230, 736), (286, 740), (346, 734), (404, 718),
              (452, 694)],
     botline=[(452, 694), (430, 722), (360, 748), (280, 758), (232, 750),
              (216, 724)],
     rower_xs=[282, 322, 362, 400])
stroke([(232, 752), (288, 762), (368, 752), (430, 724)], FOAM, 4)

# ============================================================= 8. BOTTOM SWELL
bs_top = [(0, 824), (70, 800), (150, 814), (230, 852), (290, 900),
          (320, 960)]
fill(catmull(bs_top, 12) + [(320, 960), (0, 960)], SEA)
bsf_inner = lobes([(0, 848), (68, 824), (146, 838), (224, 874),
                   (280, 916)], 7, sign=-1.0)
fill(catmull(bs_top[:5], 12) + catmull(bsf_inner[::-1], 8) + [(0, 848)],
     FOAM)
stroke(bs_top, INK, 4)
stroke(bsf_inner, INK, 2.4, n=8)

# ============================================================= 9. BOAT TWO
boat(topline=[(52, 782), (64, 792), (112, 802), (162, 812), (210, 822),
              (248, 824)],
     botline=[(248, 824), (230, 842), (178, 850), (120, 838), (72, 818),
              (52, 782)],
     rower_xs=[104, 142, 180, 214], oar=20)

# ============================================================= 10. CARTOUCHE
d.rectangle([36 * S, 34 * S, 100 * S, 206 * S], fill=CREAM,
            outline=INK, width=int(3 * S))
for i in range(6):
    y = 58 + i * 25
    x0 = 48 + rng.randint(0, 6)
    x1 = 86 - rng.randint(0, 8)
    d.line(sc([(x0, y), (x1, y + rng.randint(-3, 3))]), fill=INK,
           width=int(3 * S))

# ============================================================= OUTPUT
img = img.resize((W, H), Image.LANCZOS)
img = img.point(lambda v: max(40, min(250, v)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)

chk = Image.open(OUT)
chk.load()
assert chk.mode == "L", chk.mode
assert chk.size == (540, 960), chk.size
lo, hi = chk.getextrema()
assert 40 <= lo and hi <= 250, (lo, hi)
print("VERIFY OK", chk.mode, chk.size, "extrema", (lo, hi))
