"""Desktop canvas that draws the device layouts into a Pillow image.

Same API as ui_renderer's canvases. Text uses DejaVu Sans, the family
behind the firmware's DejaVu18..72 fonts, so wrapping and widths are a
close desktop proxy. It is NOT a photograph of the panel: e-ink
contrast, ghosting, refresh flashes and exact glyph rasterization
still need the device. Output is quantized to the panel's 16 grays.
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 540, 960
SHADES = {"black": 0, "gray": 0x33, "light": 0x77, "pale": 0xBB, "white": 255}
_FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/DejaVuSans.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
    "DejaVuSans.ttf",
)
_FONTS = {}


def _font(size):
    pt = 18
    for p in (72, 56, 40, 24, 18):
        if size >= p:
            pt = p
            break
    if pt not in _FONTS:
        for path in _FONT_PATHS:
            try:
                _FONTS[pt] = ImageFont.truetype(path, pt)
                break
            except OSError:
                continue
        else:
            _FONTS[pt] = ImageFont.load_default()
    return _FONTS[pt]


class PILCanvas:
    def __init__(self, w=W, h=H):
        self.img = Image.new("L", (w, h), 255)
        self.d = ImageDraw.Draw(self.img)
        self._ink = 0
        self.pushes = []            # (mode,) per show(), for inspection

    def reset(self):
        self.d.rectangle((0, 0, self.img.width, self.img.height), fill=255)
        self._ink = 0

    def ink(self, shade):
        self._ink = SHADES.get(shade, 0)

    def text(self, x, y, s, size):
        self.d.text((x, y), s, font=_font(size), fill=self._ink)

    def text3d(self, x, y, s, size, depth=3):
        keep = self._ink
        for k in range(depth, 0, -1):
            self.d.text((x + k, y + k), s, font=_font(size), fill=SHADES["light"])
        self.d.text((x, y), s, font=_font(size), fill=0)
        self._ink = keep

    def text_width(self, s, size):
        return int(self.d.textlength(s, font=_font(size)))

    def line(self, x0, y0, x1, y1):
        self.d.line((x0, y0, x1, y1), fill=self._ink)

    def circle(self, x, y, r):
        self.d.ellipse((x - r, y - r, x + r, y + r), outline=self._ink)

    def fill_circle(self, x, y, r):
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=self._ink)

    def fill_circle_white(self, x, y, r):
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=255)

    def rect_white(self, x, y, w, h):
        self.d.rectangle((x, y, x + w - 1, y + h - 1), fill=255)

    def fill_rect(self, x, y, w, h):
        if w > 0 and h > 0:
            self.d.rectangle((x, y, x + w - 1, y + h - 1), fill=self._ink)

    def rect(self, x, y, w, h):
        self.d.rectangle((x, y, x + w - 1, y + h - 1), outline=self._ink)

    def arc(self, x, y, r, a0, a1):
        self.d.arc((x - r, y - r, x + r, y + r), a0, a1, fill=self._ink, width=3)

    def draw_png(self, path, x, y):
        local = path.replace("/flash/", ROOT + "/")
        art = Image.open(local).convert("L")
        self.img.paste(art, (x, y))

    def anim_mode(self, on):
        pass

    def ink_segments(self, segments):
        for x0, y0, x1, y1 in segments:
            self.d.line((x0, y0, x1, y1), fill=0, width=2)

    def show(self, mode=1):
        self.pushes.append(mode)

    def save(self, path):
        self.img.point(lambda v: (v // 17) * 17).save(path)
