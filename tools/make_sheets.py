"""Build 540x960 on-device test screens: all 8 scenes of a set at
once (2 cols x 4 rows, labeled), pushable straight to the panel.

Run:  python tools/make_sheets.py [v1 v2 v3 ...]
Writes scenes/sheet_<set>.png for each set that has images.
"""

import os
import sys

from PIL import Image, ImageDraw

W, H = 540, 960
CELL_W, CELL_H = 258, 153           # 540x320 at ~0.478 scale
BASE = os.path.join(os.path.dirname(__file__), "..", "scenes")
ORDER = ["clear", "partly", "cloudy", "rain",
         "storm", "snow", "fog", "moon"]


def build(setname):
    src = os.path.join(BASE, setname)
    if not os.path.isdir(src):
        return None
    sheet = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), "SCENE SET %s" % setname.upper(), fill=0)
    d.line([(10, 26), (W - 10, 26)], fill=120)
    for i, name in enumerate(ORDER):
        path = os.path.join(src, "%s.png" % name)
        col, row = i % 2, i // 2
        x = 8 + col * (CELL_W + 10)
        y = 36 + row * (CELL_H + 28)
        if os.path.exists(path):
            img = Image.open(path).resize((CELL_W, CELL_H),
                                          Image.LANCZOS)
            sheet.paste(img, (x, y))
            d.rectangle([x - 1, y - 1, x + CELL_W, y + CELL_H],
                        outline=150)
        else:
            d.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1],
                        outline=200)
            d.text((x + 90, y + 70), "(missing)", fill=180)
        d.text((x + 2, y + CELL_H + 4), name.upper(), fill=60)
    out = os.path.join(BASE, "sheet_%s.png" % setname)
    sheet.save(out, optimize=True)
    return out


def main():
    sets = sys.argv[1:] or ["v1", "v2", "v3"]
    for s in sets:
        out = build(s)
        print("%s -> %s" % (s, out and "%s  %d bytes"
                            % (out, os.path.getsize(out)) or "skipped"))


if __name__ == "__main__":
    main()
