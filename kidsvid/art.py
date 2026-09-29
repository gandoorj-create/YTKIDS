"""Cartoon art for the videos, drawn with code.

Every sprite is drawn SS times bigger and then scaled down, so the edges look smooth.
All coordinates in this file are in final pixels.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SS = 3

WHITE = (255, 255, 255)
NAVY = (43, 45, 94)
EYE = (45, 40, 62)
MOUTH = (126, 44, 66)
TONGUE = (255, 128, 148)
BLUSH = (255, 120, 150, 120)

RED = (239, 68, 68)
ORANGE = (255, 146, 43)
YELLOW = (255, 200, 30)
GREEN = (92, 199, 84)
BLUE = (64, 140, 245)
PURPLE = (163, 98, 230)
PINK = (255, 105, 180)
RAINBOW = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK]


def font(size, weight=700):
    return ImageFont.truetype(str(ASSETS / "fonts" / f"Fredoka-{weight}.ttf"), size)


def shade(color, k):
    """k < 1 makes a color darker, k > 1 makes it lighter."""
    if k <= 1:
        return tuple(round(v * k) for v in color[:3])
    return tuple(round(v + (255 - v) * (k - 1)) for v in color[:3])


class Canvas:
    """Transparent drawing surface. Inside it is SS times bigger, for smooth edges."""

    def __init__(self, w, h, ss=SS):
        self.w, self.h, self.s = w, h, ss
        self.img = Image.new("RGBA", (round(w * ss), round(h * ss)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _xy(self, pts):
        return [(x * self.s, y * self.s) for x, y in pts]

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        s = self.s
        box = [(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s]
        self.d.ellipse(box, fill=fill, outline=outline, width=round(width * s))

    def circle(self, cx, cy, r, **kw):
        self.ellipse(cx, cy, r, r, **kw)

    def polygon(self, pts, fill):
        self.d.polygon(self._xy(pts), fill=fill)

    def line(self, pts, fill, width, caps=True):
        self.d.line(self._xy(pts), fill=fill, width=max(1, round(width * self.s)), joint="curve")
        if caps:
            for x, y in (pts[0], pts[-1]):
                self.circle(x, y, width / 2, fill=fill)

    def arc(self, cx, cy, rx, ry, start, end, fill, width):
        """Arc with round ends. Degrees, clockwise from 3 o'clock (0..180 is the bottom half)."""
        steps = 32
        angles = [math.radians(start + (end - start) * i / steps) for i in range(steps + 1)]
        self.line([(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in angles], fill, width)

    def rounded_rect(self, x0, y0, x1, y1, r, fill):
        s = self.s
        self.d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=r * s, fill=fill)

    def layer(self):
        return Canvas(self.w, self.h, self.s)

    def paste(self, other, mask=None):
        """Put another canvas on top. With a mask canvas, only where the mask is painted."""
        top = other.img
        if mask is not None:
            top = top.copy()
            top.putalpha(ImageChops.multiply(top.getchannel("A"), mask.img.getchannel("A")))
        self.img.alpha_composite(top)

    def result(self):
        return self.img.resize((round(self.w), round(self.h)), Image.LANCZOS)


# ---------- shape helpers ----------

def blob(c, ellipses, fill, outline, border):
    """Several ellipses joined into one shape, with one outline around all of them."""
    for cx, cy, rx, ry in ellipses:
        c.ellipse(cx, cy, rx + border, ry + border, fill=outline)
    for cx, cy, rx, ry in ellipses:
        c.ellipse(cx, cy, rx, ry, fill=fill)


def outlined(c, pts, fill, outline, border, rounding=0):
    """Polygon with an outline. `rounding` makes the corners round."""
    closed = pts + pts[:2]
    c.line(closed, outline, rounding + 2 * border, caps=False)
    c.polygon(pts, fill)
    if rounding:
        c.line(closed, fill, rounding, caps=False)


def ellipse_pts(cx, cy, rx, ry, angle=0, n=64):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def rect_pts(cx, cy, hw, hh, angle):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]


def star_pts(cx, cy, r_out, r_in, n=5):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(-90 + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------- faces ----------

def eyes(c, cx, cy, gap, rx, ry, mode="open"):
    for x in (cx - gap, cx + gap):
        if mode == "open":
            c.ellipse(x, cy, rx, ry, fill=EYE)
            c.circle(x - rx * 0.3, cy - ry * 0.38, rx * 0.42, fill=WHITE)
            c.circle(x + rx * 0.34, cy + ry * 0.4, rx * 0.2, fill=WHITE)
        elif mode == "blink":
            c.arc(x, cy, rx * 1.1, ry * 0.5, 15, 165, EYE, rx * 0.45)
        else:  # "happy": ^ ^
            c.arc(x, cy + ry * 0.45, rx * 1.1, ry * 0.8, 195, 345, EYE, rx * 0.45)


def blush(c, spots, color=BLUSH):
    layer = c.layer()
    for x, y, rx, ry in spots:
        layer.ellipse(x, y, rx, ry, fill=color)
    c.paste(layer)


def blush_color(color):
    """Pink cheeks. On blue or green things they must be stronger, or they look brown."""
    r, g, b = color[:3]
    return (255, 140, 175, 215) if (b > r or g > r + 40) else BLUSH


def smile(c, cx, cy, w, h, width, color=MOUTH):
    c.arc(cx, cy - h * 0.5, w / 2, h, 25, 155, color, width)


def open_mouth(c, cx, cy, rx, ry):
    c.ellipse(cx, cy, rx, ry, fill=MOUTH)
    if ry > rx * 0.5:
        c.ellipse(cx, cy + ry * 0.45, rx * 0.6, ry * 0.42, fill=TONGUE)


# ---------- the mascot: a little lamb ----------

WOOL_LINE = (196, 206, 232)
FACE = (255, 233, 214)
FACE_LINE = (226, 184, 160)
EAR_IN = (255, 176, 190)
LEG = (92, 86, 116)
LEG_BACK = (70, 64, 94)
NOSE = (232, 140, 150)

LAMB_SIZE = (420, 440)
LAMB_FEET = (210, 432)


def lamb(eyes_mode="open", mouth=0):
    """`eyes_mode`: open / blink / happy. `mouth`: 0 = smile, 1..5 = more and more open (talking)."""
    c = Canvas(*LAMB_SIZE)
    for x, color in ((130, LEG_BACK), (290, LEG_BACK), (178, LEG), (242, LEG)):
        c.rounded_rect(x - 19, 320, x + 19, 432, 18, color)
    body = [(210, 272, 128, 72)]
    body += [(210 + 128 * math.cos(a), 272 + 70 * math.sin(a), 44, 44)
             for a in (2 * math.pi * i / 12 for i in range(12))]
    blob(c, body, WHITE, WOOL_LINE, 5)
    for side in (-1, 1):
        outlined(c, ellipse_pts(210 + side * 110, 176, 48, 22, side * 28), FACE, FACE_LINE, 3)
        c.polygon(ellipse_pts(210 + side * 114, 178, 30, 11, side * 28), EAR_IN)
    c.ellipse(210, 170, 100, 84, fill=FACE, outline=FACE_LINE, width=5)
    tuft = [(160, 104, 30, 30), (186, 86, 34, 34), (214, 78, 36, 36), (244, 88, 34, 34), (266, 106, 29, 29)]
    blob(c, tuft, WHITE, WOOL_LINE, 5)
    eyes(c, 210, 172, 38, 15, 20, eyes_mode)
    blush(c, [(146, 205, 18, 11), (274, 205, 18, 11)])
    c.ellipse(210, 197, 9, 6, fill=NOSE)
    if mouth == 0:
        smile(c, 210, 216, 26, 12, 4.5)
    else:
        open_mouth(c, 210, 212 + 2.2 * mouth, 8 + 2 * mouth, 3 + 3.4 * mouth)
    return c.result()


# ---------- things to guess (each returns sprite, anchor point) ----------

def balloon(color):
    c = Canvas(440, 580)
    line = shade(color, 0.72)
    cx, cy, rx, ry = 220, 235, 165, 195
    body = []
    for i in range(96):
        t = 2 * math.pi * i / 96
        body.append((cx + rx * math.cos(t) * (1 - 0.12 * math.sin(t)), cy + ry * math.sin(t)))
    c.line([(220 + 9 * math.sin((y - 440) / 26), y) for y in range(440, 568, 4)], (120, 120, 140), 4)
    outlined(c, [(220, 424), (200, 452), (240, 452)], shade(color, 0.85), line, 3, rounding=8)
    outlined(c, body, color, line, 4)
    shine = c.layer()
    shine.polygon(ellipse_pts(158, 150, 24, 50, 25), (255, 255, 255, 150))
    c.paste(shine)
    eyes(c, 220, 236, 46, 18, 23)
    blush(c, [(146, 282, 23, 14), (294, 282, 23, 14)], blush_color(color))
    smile(c, 220, 288, 58, 28, 7)
    return c.result(), (220, 235)


def star(color):
    c = Canvas(520, 520)
    outlined(c, star_pts(260, 272, 200, 104), color, shade(color, 0.78), 5, rounding=44)
    shine = c.layer()
    shine.polygon(ellipse_pts(222, 150, 12, 30, 20), (255, 255, 255, 150))
    c.paste(shine)
    eyes(c, 260, 270, 50, 20, 26)
    blush(c, [(186, 322, 24, 14), (334, 322, 24, 14)], blush_color(color))
    smile(c, 260, 330, 62, 30, 8)
    return c.result(), (260, 272)


def frog(color):
    c = Canvas(540, 500)
    line = shade(color, 0.7)
    for side in (-1, 1):
        outlined(c, ellipse_pts(270 + side * 105, 440, 72, 32), shade(color, 0.85), line, 4)
    blob(c, [(270, 300, 220, 145), (165, 160, 76, 76), (375, 160, 76, 76)], color, line, 6)
    for x, look in ((165, 6), (375, -6)):
        c.circle(x, 158, 50, fill=WHITE, outline=line, width=3)
        c.circle(x + look, 166, 26, fill=EYE)
        c.circle(x + look - 9, 156, 10, fill=WHITE)
    c.circle(250, 250, 5, fill=line)
    c.circle(290, 250, 5, fill=line)
    blush(c, [(140, 330, 28, 16), (400, 330, 28, 16)], blush_color(color))
    smile(c, 270, 320, 190, 70, 9)
    return c.result(), (270, 290)


def fish(color):
    c = Canvas(560, 440)
    line = shade(color, 0.7)
    fin = shade(color, 0.85)
    outlined(c, [(400, 220), (520, 112), (492, 220), (520, 328)], fin, line, 5, rounding=30)
    outlined(c, [(185, 118), (250, 52), (335, 72), (330, 125)], fin, line, 5, rounding=24)
    outlined(c, [(235, 330), (270, 392), (310, 328)], fin, line, 5, rounding=20)
    body = c.layer()
    body.ellipse(250, 222, 178, 126, fill=color)
    c.ellipse(250, 222, 183, 131, fill=line)
    c.paste(body)
    belly = c.layer()
    belly.ellipse(235, 300, 150, 62, fill=shade(color, 1.45))
    c.paste(belly, mask=body)
    outlined(c, ellipse_pts(290, 250, 42, 20, -20), fin, line, 4)
    c.circle(150, 196, 40, fill=WHITE, outline=line, width=3)
    c.circle(144, 200, 23, fill=EYE)
    c.circle(136, 190, 9, fill=WHITE)
    c.circle(152, 210, 4, fill=WHITE)
    blush(c, [(128, 262, 18, 11)], blush_color(color))
    smile(c, 96, 256, 34, 18, 5)
    return c.result(), (280, 222)


# ---------- scenery and small things ----------

def background(w, h):
    top, bottom = (112, 196, 255), (200, 236, 255)
    horizon = int(h * 0.8)
    col = Image.new("RGB", (1, h))
    col.putdata([tuple(round(top[k] + (bottom[k] - top[k]) * min(y, horizon) / horizon) for k in range(3))
                 for y in range(h)])
    img = col.resize((w, h))
    c = Canvas(w, h, ss=2)
    c.ellipse(330, 1010, 720, 250, fill=(168, 224, 134))
    c.ellipse(1560, 990, 820, 240, fill=(168, 224, 134))
    c.ellipse(420, 1160, 1120, 330, fill=(116, 202, 98))
    c.ellipse(1680, 1190, 920, 320, fill=(116, 202, 98))
    rnd = random.Random(4)
    for _ in range(40):
        x, y = rnd.uniform(30, w - 30), rnd.uniform(940, 1065)
        petal = rnd.choice([WHITE, (255, 182, 213), (255, 236, 140)])
        for k in range(5):
            a = 2 * math.pi * k / 5
            c.circle(x + 7 * math.cos(a), y + 7 * math.sin(a), 6, fill=petal)
        c.circle(x, y, 5, fill=(255, 170, 40))
    hills = c.result()
    img.paste(hills, (0, 0), hills)
    return img


def cloud(scale=1.0):
    s = scale
    c = Canvas(380 * s, 200 * s)
    parts = [(95, 120, 62), (170, 88, 78), (250, 100, 68), (310, 128, 52)]
    for color, dy in (((228, 240, 252), 8), (WHITE, 0)):
        for x, y, r in parts:
            c.circle(x * s, (y + dy) * s, r * s, fill=color)
        c.rounded_rect(40 * s, (110 + dy) * s, 345 * s, (178 + dy) * s, 34 * s, color)
    return c.result()


def stage(r=320):
    size = 2 * r + 40
    c = Canvas(size, size)
    c.circle(size / 2, size / 2, r + 10, fill=(255, 255, 255, 90))
    c.circle(size / 2, size / 2, r, fill=(255, 255, 255, 170))
    return c.result()


def bubble(r=18):
    c = Canvas(2 * r + 8, 2 * r + 8)
    m = r + 4
    c.circle(m, m, r, fill=(255, 255, 255, 70), outline=(255, 255, 255, 220), width=3)
    c.circle(m - r * 0.35, m - r * 0.35, r * 0.25, fill=(255, 255, 255, 230))
    return c.result()


def confetti_sprites(seed=3):
    """Each item: the same piece in 3 sizes (big, middle, small)."""
    rnd = random.Random(seed)
    out = []
    for color in RAINBOW:
        for kind in ("dot", "strip", "star"):
            angle = rnd.uniform(0, 180)
            sizes = []
            for s in (1.0, 0.65, 0.35):
                c = Canvas(44, 44)
                if kind == "dot":
                    c.circle(22, 22, 10 * s, fill=color)
                elif kind == "strip":
                    c.polygon(rect_pts(22, 22, 15 * s, 6 * s, angle), color)
                else:
                    c.polygon(star_pts(22, 22, 15 * s, 7 * s), color)
                sizes.append(c.result())
            out.append(sizes)
    return out


# ---------- text ----------

def text_sprite(text, size, fill, outline=NAVY, outline_w=None, inner=WHITE, inner_w=None,
                shadow=True, anchor="mm"):
    """Cartoon text: color fill, white inner line, navy outer line, soft shadow.

    Returns (sprite, anchor point inside the sprite).
    """
    f = font(size)
    text = text.replace(" ", "  ")  # thick outlines eat the spaces, so make them wider
    ow = round(size * 0.09) if outline_w is None else outline_w
    iw = round(size * 0.05) if inner_w is None else inner_w
    left, top, right, bottom = f.getbbox(text, stroke_width=ow, anchor=anchor)
    pad = 12 + round(size * 0.08)
    img = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
    ox, oy = pad - left, pad - top
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ink = (25, 25, 70, 120)
        ImageDraw.Draw(sh).text((ox, oy + size * 0.05), text, font=f, anchor=anchor, fill=ink,
                                stroke_width=ow, stroke_fill=ink)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.03)))
    d = ImageDraw.Draw(img)
    d.text((ox, oy), text, font=f, anchor=anchor, fill=outline, stroke_width=ow, stroke_fill=outline)
    if inner:
        d.text((ox, oy), text, font=f, anchor=anchor, fill=inner, stroke_width=iw, stroke_fill=inner)
    d.text((ox, oy), text, font=f, anchor=anchor, fill=fill)
    return img, (ox, oy)


def title_letters(text, size, colors=RAINBOW):
    """One sprite per letter (so each letter can jump by itself).

    Returns a list of (sprite, anchor, x offset from the middle of the word).
    """
    f = font(size)
    gap = size * 0.06  # extra space between letters, for the thick outlines
    total = f.getlength(text) + gap * (len(text) - 1)
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        dx = f.getlength(text[:i]) + gap * i + f.getlength(ch) / 2 - total / 2
        spr, anchor = text_sprite(ch, size, colors[len(out) % len(colors)], anchor="ms")
        out.append((spr, anchor, dx))
    return out


def badge(label):
    """Round orange countdown badge with a big number."""
    c = Canvas(270, 270)
    c.circle(135, 135, 115, fill=NAVY)
    c.circle(135, 135, 107, fill=WHITE)
    c.circle(135, 135, 96, fill=ORANGE)
    img = c.result()
    text, (ax, ay) = text_sprite(label, 165, WHITE, outline_w=10, inner=None, shadow=False)
    img.alpha_composite(text, (max(0, round(135 - ax)), max(0, round(140 - ay))))
    return img


# ---------- more things to guess (for the full episodes) ----------

BROWN = (140, 94, 58)
LEAF_GREEN = (92, 199, 84)
GLASS, GLASS_LINE = (196, 232, 255), (120, 170, 210)
BEAK, BEAK_LINE = (255, 160, 40), (210, 110, 20)


def leaf_pts(cx, cy, length, width, angle, n=24):
    """A leaf (pointed at both ends), turned by `angle` degrees."""
    half = []
    for i in range(n + 1):
        s = -1 + 2 * i / n
        half.append((s * length / 2, width / 2 * (1 - s * s) ** 0.8))
    pts = [(x, -y) for x, y in half] + [(x, y) for x, y in reversed(half[1:-1])]
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def cute_face(c, color, cx, cy, gap, eye_rx, eye_ry, cheek_dx, cheek_dy, smile_w):
    eyes(c, cx, cy, gap, eye_rx, eye_ry)
    blush(c, [(cx - cheek_dx, cy + cheek_dy, eye_rx * 1.3, eye_rx * 0.75),
              (cx + cheek_dx, cy + cheek_dy, eye_rx * 1.3, eye_rx * 0.75)], blush_color(color))
    smile(c, cx, cy + cheek_dy + eye_ry * 0.25, smile_w, smile_w * 0.48, max(4, eye_rx * 0.38))


def shine(c, cx, cy, rx, ry, angle, alpha=145):
    layer = c.layer()
    layer.polygon(ellipse_pts(cx, cy, rx, ry, angle), (255, 255, 255, alpha))
    c.paste(layer)


def apple(color):
    c = Canvas(480, 500)
    c.line([(238, 150), (246, 112), (256, 78)], BROWN, 16)
    outlined(c, leaf_pts(304, 94, 104, 48, -20), LEAF_GREEN, shade(LEAF_GREEN, 0.7), 3)
    blob(c, [(180, 292, 142, 162), (300, 292, 142, 162)], color, shade(color, 0.72), 5)
    shine(c, 128, 228, 22, 48, 20)
    cute_face(c, color, 240, 290, 48, 18, 23, 76, 46, 58)
    return c.result(), (240, 290)


def car(color):
    c = Canvas(600, 430)
    line = shade(color, 0.7)
    outlined(c, [(170, 200), (225, 96), (385, 96), (455, 200)], color, line, 5, rounding=40)
    c.rounded_rect(56, 186, 544, 330, 52, line)
    c.rounded_rect(61, 191, 539, 325, 47, color)
    outlined(c, [(206, 190), (240, 122), (298, 122), (298, 190)], GLASS, GLASS_LINE, 3, rounding=14)
    outlined(c, [(318, 190), (318, 122), (372, 122), (418, 190)], GLASS, GLASS_LINE, 3, rounding=14)
    c.ellipse(528, 236, 14, 18, fill=(255, 236, 140), outline=line, width=3)
    c.rounded_rect(58, 222, 78, 256, 6, (255, 140, 60))
    for x in (170, 430):
        c.circle(x, 330, 62, fill=(58, 58, 78))
        c.circle(x, 330, 26, fill=(205, 210, 225))
        c.circle(x, 330, 9, fill=(150, 155, 175))
    eyes(c, 300, 240, 34, 14, 18)
    smile(c, 300, 276, 44, 20, 6)
    return c.result(), (300, 250)


def ball(color):
    c = Canvas(460, 460)
    body = c.layer()
    body.circle(230, 230, 196, fill=color)
    c.circle(230, 230, 201, fill=shade(color, 0.72))
    c.paste(body)
    stripe = c.layer()
    stripe.ellipse(230, 640, 340, 300, outline=(255, 255, 255, 235), width=34)
    c.paste(stripe, mask=body)
    shine(c, 138, 132, 24, 46, 40)
    cute_face(c, color, 230, 205, 50, 19, 24, 78, 44, 58)
    return c.result(), (230, 230)


def bird(color):
    c = Canvas(500, 470)
    line = shade(color, 0.7)
    wing = shade(color, 0.85)
    for side in (-1, 1):
        outlined(c, ellipse_pts(250 + side * 158, 262, 58, 88, side * -22), wing, line, 5)
        outlined(c, ellipse_pts(250 + side * 45, 434, 28, 13), BEAK, BEAK_LINE, 3)
    for dx, a in ((-26, -20), (0, 0), (26, 20)):
        outlined(c, ellipse_pts(250 + dx, 84, 14, 34, a), wing, line, 4)
    body = c.layer()
    body.ellipse(250, 250, 168, 172, fill=color)
    c.ellipse(250, 250, 173, 177, fill=line)
    c.paste(body)
    belly = c.layer()
    belly.ellipse(250, 335, 112, 92, fill=shade(color, 1.45))
    c.paste(belly, mask=body)
    eyes(c, 250, 206, 56, 19, 25)
    blush(c, [(168, 256, 24, 14), (332, 256, 24, 14)], blush_color(color))
    outlined(c, [(226, 246), (274, 246), (250, 280)], BEAK, BEAK_LINE, 3, rounding=12)
    return c.result(), (250, 250)


def banana(color):
    c = Canvas(540, 430)
    line = shade(color, 0.72)
    stem = (140, 100, 50)
    outer = [(270 + 235 * math.cos(math.radians(a)), 70 + 300 * math.sin(math.radians(a))) for a in range(18, 163, 4)]
    inner = [(270 + 190 * math.cos(math.radians(a)), 22 + 238 * math.sin(math.radians(a))) for a in range(162, 17, -4)]
    outlined(c, [(470, 150), (505, 92), (522, 102), (492, 158)], stem, shade(stem, 0.7), 3, rounding=8)
    outlined(c, outer + inner, color, line, 5, rounding=16)
    c.circle(60, 135, 10, fill=(110, 80, 40))
    eyes(c, 270, 306, 40, 15, 19)
    blush(c, [(208, 330, 20, 12), (332, 330, 20, 12)], blush_color(color))
    smile(c, 270, 340, 46, 22, 6)
    return c.result(), (270, 300)


def duck(color):
    c = Canvas(540, 450)
    line = shade(color, 0.72)
    outlined(c, [(405, 150), (492, 162), (480, 196), (402, 192)], BEAK, BEAK_LINE, 4, rounding=18)
    blob(c, [(240, 305, 195, 118), (80, 245, 52, 42), (330, 158, 98, 98)], color, line, 6)
    outlined(c, ellipse_pts(220, 300, 88, 48, -12), shade(color, 0.88), line, 4)
    c.ellipse(358, 132, 16, 22, fill=EYE)
    c.circle(352, 124, 6.5, fill=WHITE)
    c.circle(363, 140, 3, fill=WHITE)
    blush(c, [(378, 180, 20, 12)], blush_color(color))
    return c.result(), (260, 270)


def leaf(color):
    c = Canvas(500, 500)
    angle = -35
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    cx, cy = 250, 260
    base = (cx - 205 * ux, cy - 205 * uy)
    c.line([base, (base[0] - 40 * ux - 8, base[1] - 40 * uy + 22)], shade(color, 0.6), 12)
    outlined(c, leaf_pts(cx, cy, 410, 250, angle), color, shade(color, 0.68), 5)
    vein = shade(color, 0.8)
    c.line([(cx - 185 * ux, cy - 185 * uy), (cx - 95 * ux, cy - 95 * uy)], vein, 6)
    c.line([(cx + 105 * ux, cy + 105 * uy), (cx + 180 * ux, cy + 180 * uy)], vein, 6)
    cute_face(c, color, cx, 250, 46, 18, 23, 76, 42, 56)
    return c.result(), (cx, cy)


def tree(color):
    c = Canvas(500, 580)
    c.rounded_rect(208, 300, 292, 548, 26, (115, 75, 45))
    c.rounded_rect(213, 305, 287, 543, 22, (160, 110, 70))
    blob(c, [(250, 215, 160, 150), (125, 265, 92, 88), (375, 265, 92, 88), (160, 145, 92, 88),
             (340, 145, 92, 88), (250, 100, 104, 90)], color, shade(color, 0.7), 6)
    cute_face(c, color, 250, 222, 50, 19, 24, 80, 46, 58)
    return c.result(), (250, 290)


def orange_fruit(color):
    c = Canvas(460, 480)
    c.line([(230, 100), (236, 60)], BROWN, 12)
    outlined(c, leaf_pts(284, 70, 92, 40, -15), LEAF_GREEN, shade(LEAF_GREEN, 0.7), 3)
    body = c.layer()
    body.circle(230, 272, 182, fill=color)
    c.circle(230, 272, 187, fill=shade(color, 0.72))
    c.paste(body)
    dots = c.layer()
    rnd = random.Random(5)
    for _ in range(40):
        x, y = rnd.uniform(70, 390), rnd.uniform(110, 430)
        if not (140 < x < 320 and 215 < y < 345):
            dots.circle(x, y, 4, fill=shade(color, 1.3) + (200,))
    c.paste(dots, mask=body)
    shine(c, 150, 170, 22, 42, 35)
    cute_face(c, color, 230, 262, 50, 19, 24, 80, 46, 58)
    return c.result(), (230, 272)


def grapes(color):
    c = Canvas(460, 540)
    line = shade(color, 0.7)
    c.line([(230, 112), (240, 42)], BROWN, 14)
    outlined(c, leaf_pts(302, 70, 120, 56, -25), LEAF_GREEN, shade(LEAF_GREEN, 0.7), 4)
    rows = [(150, (110, 190, 270, 350)), (228, (150, 230, 310)), (306, (190, 270)), (384, (230,))]
    for k, (y, xs) in enumerate(rows):
        for x in xs:
            c.circle(x, y, 53, fill=line)
            c.circle(x, y, 48, fill=color)
            if k != 1:
                c.circle(x - 16, y - 18, 10, fill=shade(color, 1.5))
    cute_face(c, color, 230, 222, 34, 13, 17, 58, 34, 38)
    return c.result(), (230, 260)


def splat(color, seed=0):
    """A round paint splash with a happy face: the "color friend"."""
    c = Canvas(600, 560)
    line = shade(color, 0.72)
    rnd = random.Random(seed)
    parts = [(300, 280, 190, 180)]
    for k in range(9):
        a = 2 * math.pi * (k + rnd.uniform(-0.25, 0.25)) / 9
        d, r = rnd.uniform(150, 195), rnd.uniform(42, 68)
        parts.append((300 + d * math.cos(a), 280 + 0.9 * d * math.sin(a), r, r))
    blob(c, parts, color, line, 6)
    for k in range(4):
        a = 2 * math.pi * (k + 0.5 + rnd.uniform(-0.2, 0.2)) / 4
        x, y, r = 300 + 262 * math.cos(a), 280 + 238 * math.sin(a), rnd.uniform(11, 17)
        c.circle(x, y, r + 5, fill=line)
        c.circle(x, y, r, fill=color)
    shine(c, 212, 182, 26, 50, 35, 120)
    cute_face(c, color, 300, 262, 56, 21, 27, 90, 50, 66)
    return c.result(), (300, 280)


def ring(r=200):
    """Golden circle that shows the right answer."""
    size = 2 * r + 60
    c = Canvas(size, size)
    m = size / 2
    c.circle(m, m, r + 20, fill=(255, 236, 120, 110))
    c.circle(m, m, r + 8, fill=(255, 205, 40))
    c.circle(m, m, r - 6, fill=(255, 255, 255, 160))
    return c.result()


COLORS = {"red": RED, "orange": ORANGE, "yellow": YELLOW, "green": GREEN,
          "blue": BLUE, "purple": PURPLE, "pink": PINK}
THINGS = {"balloon": balloon, "star": star, "frog": frog, "fish": fish, "apple": apple, "car": car,
          "ball": ball, "bird": bird, "banana": banana, "duck": duck, "leaf": leaf, "tree": tree,
          "orange": orange_fruit, "grapes": grapes}


# ---------- mascot ideas: food characters ----------

JELLY_SIZE, JELLY_BOTTOM = (520, 520), (260, 486)


def jelly(color, eyes_mode="open", mouth=0):
    """A shiny, wobbly jelly on a plate. It can be any color."""
    c = Canvas(*JELLY_SIZE)
    line = shade(color, 0.72)
    c.ellipse(260, 466, 215, 34, fill=(236, 244, 255), outline=(190, 205, 230), width=4)
    top = [(260 + 165 * math.cos(math.radians(a)), 250 + 160 * math.sin(math.radians(a))) for a in range(180, 361, 6)]
    body = c.layer()
    outlined(body, top + [(445, 448), (75, 448)], color, line, 6, rounding=40)
    c.paste(body)
    light = c.layer()
    light.ellipse(260, 165, 150, 95, fill=shade(color, 1.4) + (130,))
    c.paste(light, mask=body)
    dark = c.layer()
    dark.ellipse(260, 485, 240, 95, fill=shade(color, 0.85) + (150,))
    c.paste(dark, mask=body)
    shine(c, 168, 190, 19, 56, 25, 190)
    dots = c.layer()
    for x, y, r in ((150, 268, 8), (346, 152, 7), (372, 240, 5), (120, 380, 5)):
        dots.circle(x, y, r, fill=(255, 255, 255, 190))
    c.paste(dots)
    blob(c, [(260, 96, 36, 30), (226, 108, 28, 24), (294, 108, 28, 24), (260, 68, 18, 16)],
         WHITE, (215, 220, 235), 4)
    eyes(c, 260, 300, 58, 20, 26, eyes_mode)
    blush(c, [(176, 342, 26, 15), (344, 342, 26, 15)], blush_color(color))
    if mouth == 0:
        smile(c, 260, 350, 60, 28, 7)
    else:
        open_mouth(c, 260, 346 + 2.5 * mouth, 10 + 2.4 * mouth, 4 + 3.8 * mouth)
    return c.result()


def marshmallow(color=(255, 247, 250), eyes_mode="open", mouth=0):
    """A soft marshmallow."""
    c = Canvas(480, 470)
    c.rounded_rect(84, 104, 396, 446, 76, (226, 205, 216))
    body = c.layer()
    body.rounded_rect(90, 110, 390, 440, 70, color)
    c.paste(body)
    soft = c.layer()
    soft.ellipse(240, 470, 200, 90, fill=shade(color, 0.93) + (170,))
    c.paste(soft, mask=body)
    c.ellipse(240, 142, 140, 32, fill=WHITE, outline=(238, 225, 232), width=3)
    shine(c, 130, 250, 14, 44, 10, 170)
    eyes(c, 240, 290, 56, 20, 26, eyes_mode)
    blush(c, [(160, 332, 26, 15), (320, 332, 26, 15)], (255, 140, 175, 170))
    if mouth == 0:
        smile(c, 240, 340, 56, 26, 7)
    else:
        open_mouth(c, 240, 336 + 2.5 * mouth, 10 + 2.4 * mouth, 4 + 3.8 * mouth)
    return c.result()


def cupcake(frosting=(255, 170, 205), cup=(130, 200, 250), eyes_mode="open", mouth=0):
    """A cupcake with a cherry and sprinkles."""
    c = Canvas(500, 500)
    outlined(c, [(112, 300), (388, 300), (352, 470), (148, 470)], cup, shade(cup, 0.7), 5, rounding=24)
    for k in range(1, 7):
        c.line([(112 + k * 276 / 7, 330), (148 + k * 204 / 7, 458)], shade(cup, 0.9), 6)
    for cx, cy, rx, ry in ((250, 292, 188, 50), (250, 236, 150, 48), (250, 184, 106, 44), (250, 140, 58, 34)):
        c.ellipse(cx, cy, rx + 5, ry + 5, fill=shade(frosting, 0.78))
        c.ellipse(cx, cy, rx, ry, fill=frosting)
    rnd = random.Random(8)
    for k in range(16):
        cx, cy, rx, ry = ((250, 292, 188, 50), (250, 236, 150, 48), (250, 184, 106, 44))[k % 3]
        x, y = cx + rnd.uniform(-0.7, 0.7) * rx, cy + rnd.uniform(-0.35, 0.25) * ry
        c.polygon(rect_pts(x, y, 9, 3.5, rnd.uniform(0, 180)), RAINBOW[k % len(RAINBOW)])
    c.line([(252, 98), (262, 66), (282, 50)], (90, 150, 70), 5)
    c.circle(250, 100, 24, fill=(200, 30, 50))
    c.circle(250, 100, 20, fill=(235, 50, 70))
    c.circle(242, 92, 6, fill=(255, 190, 200))
    eyes(c, 250, 388, 50, 17, 22, eyes_mode)
    blush(c, [(178, 420, 20, 12), (322, 420, 20, 12)], (255, 130, 165, 190))
    if mouth == 0:
        smile(c, 250, 428, 46, 22, 6)
    else:
        open_mouth(c, 250, 424 + 2 * mouth, 8 + 2 * mouth, 3 + 3 * mouth)
    return c.result()


# ---------- the foal (baby horse) ----------

FOAL_SIZE, FOAL_FEET = (540, 640), (270, 616)
FOAL_COLORS = {  # Mongolian horse colors: body, mane, muzzle
    "zeerd": ((214, 128, 78), (160, 80, 44), (250, 216, 184)),     # chestnut
    "khaliun": ((234, 190, 122), (62, 50, 54), (252, 232, 204)),   # buckskin
    "saaral": ((232, 233, 240), (150, 156, 178), (246, 226, 230)),  # grey
}
HOOF = (96, 74, 66)


def leg(c, x, top, bottom, half_w, color, line):
    c.rounded_rect(x - half_w - 4, top - 4, x + half_w + 4, bottom + 4, half_w, line)
    c.rounded_rect(x - half_w, top, x + half_w, bottom, half_w - 3, color)
    c.rounded_rect(x - half_w, bottom - 30, x + half_w, bottom, 12, HOOF)


def foal(colors="zeerd", eyes_mode="open", mouth=0):
    """A cute baby horse with a white star on its forehead."""
    body, mane, muzzle = FOAL_COLORS[colors] if isinstance(colors, str) else colors
    line, mane_line = shade(body, 0.7), shade(mane, 0.7)
    c = Canvas(*FOAL_SIZE)
    blob(c, [(402, 388, 40, 34), (428, 428, 36, 40), (440, 476, 30, 38), (430, 520, 22, 28)], mane, mane_line, 5)
    for x in (192, 348):
        leg(c, x, 460, 604, 22, shade(body, 0.86), line)
    blob(c, [(270, 425, 145, 92)], body, line, 5)
    for x in (228, 312):
        leg(c, x, 460, 616, 24, body, line)
    blob(c, [(398, 212, 34, 50), (408, 282, 30, 46), (398, 346, 26, 40)], mane, mane_line, 5)
    for x, angle in ((172, -110), (368, -70)):
        outlined(c, leaf_pts(x, 108, 112, 60, angle), body, line, 5)
        c.polygon(leaf_pts(x + (-7 if x < 270 else 7), 94, 62, 28, angle), (255, 190, 200))
    blob(c, [(270, 225, 145, 130), (270, 300, 112, 84)], body, line, 5)
    c.ellipse(270, 318, 100, 64, fill=muzzle, outline=shade(muzzle, 0.85), width=3)
    blob(c, [(240, 120, 38, 30), (276, 110, 42, 32), (310, 124, 34, 28), (318, 154, 20, 24)], mane, mane_line, 4)
    c.polygon(star_pts(270, 180, 20, 9), WHITE)
    eyes(c, 270, 234, 58, 21, 28, eyes_mode)
    if eyes_mode == "open":  # eyelashes, curling up and out
        for side in (-1, 1):
            x = 270 + side * 58
            for a in (-62, -32):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                x0, y0 = x + side * 21 * ca, 234 + 28 * sa
                c.line([(x0, y0), (x0 + side * 13 * ca, y0 + 13 * sa - 3)], EYE, 4.5)
    blush(c, [(190, 284, 24, 14), (350, 284, 24, 14)], blush_color(body))
    for x in (246, 294):
        c.ellipse(x, 316, 7, 9, fill=shade(muzzle, 0.55))
    if mouth == 0:
        smile(c, 270, 350, 46, 22, 6)
    else:
        open_mouth(c, 270, 346 + 2.2 * mouth, 9 + 2.2 * mouth, 3 + 3.2 * mouth)
    return c.result()
