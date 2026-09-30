"""The end of an episode: "Thanks for watching!", like and subscribe, then bye-bye.

On YouTube, "made for kids" videos have no clickable end screens and no notification bell, so the
buttons are drawn in the video. Domi asks a grown-up to tap them (the grown-up decides, not the child),
then a big paw taps both buttons to show how.
"""
import math

from PIL import ImageDraw

from . import art, sound
from .anim import ease_out_back, place, progress
from .show import Letters

RED, RED_LINE = (238, 46, 58), (168, 22, 36)
BLUE = (44, 128, 255)
GREY, GREY_LINE = (212, 214, 222), (140, 142, 156)
INK = (70, 72, 92)
LIKE_SPOT, SUB_SPOT = (630, 600), (1215, 600)  # middle of the buttons
TITLE = "Thanks for watching!"
ASK = ("kitten", "Did you have fun? Ask a grown-up to tap like and subscribe!")
FAREWELL = (("puppy", "See you in the next video!"), ("kitten", "Bye-bye!"))


# ---------- pictures ----------

def thumb(color):
    """A thumbs-up icon, drawn around (cx, cy) with half size s."""
    def draw(c, cx, cy, s):
        c.rounded_rect(cx - 0.35 * s, cy - 0.15 * s, cx + 0.75 * s, cy + 0.85 * s, 0.25 * s, color)  # fist
        c.rounded_rect(cx - 0.35 * s, cy - 0.95 * s, cx + 0.12 * s, cy + 0.1 * s, 0.23 * s, color)   # thumb
        c.rounded_rect(cx - 0.85 * s, cy - 0.1 * s, cx - 0.5 * s, cy + 0.85 * s, 0.1 * s, color)     # cuff
        for k in range(3):  # fingers
            y = cy + (0.12 + 0.24 * k) * s
            c.line([(cx + 0.22 * s, y), (cx + 0.68 * s, y)], art.WHITE, 0.07 * s)
    return draw


def check(color):
    """A check mark icon."""
    def draw(c, cx, cy, s):
        c.line([(cx - 0.7 * s, cy), (cx - 0.2 * s, cy + 0.5 * s), (cx + 0.75 * s, cy - 0.55 * s)], color, 0.28 * s)
    return draw


def pill(w, h, fill, line, text, ink, icon=None):
    """A round button with a shadow, a shine, a word, and maybe an icon on the left."""
    pad = 18
    c = art.Canvas(w + 2 * pad, h + 2 * pad + 12)
    x0, y0, x1, y1 = pad, pad, pad + w, pad + h
    r = h / 2
    c.rounded_rect(x0, y0 + 12, x1, y1 + 12, r, (20, 20, 60, 70))  # shadow
    c.rounded_rect(x0 - 6, y0 - 6, x1 + 6, y1 + 6, r + 6, line)     # outline
    c.rounded_rect(x0, y0, x1, y1, r, fill)
    shine = c.layer()
    shine.rounded_rect(x0 + r * 0.6, y0 + 12, x1 - r * 0.6, y0 + h * 0.34, h * 0.12, (255, 255, 255, 55))
    c.paste(shine)
    if icon:
        icon(c, x0 + h * 0.62, y0 + h / 2, h * 0.3)
    img = c.result()
    left = x0 + (h * 0.95 if icon else h * 0.3)
    right = x1 - h * 0.3
    size = int(h * 0.46)
    while art.font(size).getlength(text) > right - left and size > 20:
        size -= 2
    ImageDraw.Draw(img).text(((left + right) / 2, (y0 + y1) / 2 + 2), text, font=art.font(size), fill=ink,
                             anchor="mm")
    return img


def like_buttons():
    """(before, after) pictures of the like button."""
    return (pill(430, 180, art.WHITE, GREY_LINE, "LIKE", INK, thumb((150, 152, 168))),
            pill(430, 180, art.WHITE, BLUE, "LIKE", BLUE, thumb(BLUE)))


def subscribe_buttons():
    """(before, after) pictures of the subscribe button."""
    return (pill(670, 180, RED, RED_LINE, "SUBSCRIBE", art.WHITE),
            pill(670, 180, GREY, GREY_LINE, "SUBSCRIBED", INK, check(INK)))


def paw_cursor(size=175):
    """A big soft paw that taps the buttons (like a finger on a phone)."""
    fur, line, bean = (255, 238, 214), (176, 132, 100), (255, 170, 192)
    c = art.Canvas(size, size * 1.05)
    cx, cy = size * 0.5, size * 0.68
    toes = [(-0.33, -0.3), (-0.12, -0.46), (0.12, -0.46), (0.33, -0.3)]
    for grow, color in ((5, line), (0, fur)):  # the outline first, then the fur
        c.ellipse(cx, cy, size * 0.34 + grow, size * 0.28 + grow, fill=color)
        for dx, dy in toes:
            c.circle(cx + dx * size, cy + dy * size, size * 0.12 + grow, fill=color)
    c.ellipse(cx, cy + size * 0.03, size * 0.2, size * 0.15, fill=bean)
    for dx, dy in toes:
        c.circle(cx + dx * size, cy + dy * size, size * 0.065, fill=bean)
    return c.result()


# ---------- moving pictures ----------

class Button:
    """Pops in, softly pulses (tap me!), squashes when tapped at `tap`, then shows its "after" picture."""
    z = 6

    def __init__(self, pictures, start, tap, end, x, y):
        (self.before, self.after), self.start, self.tap, self.end, self.x, self.y = pictures, start, tap, end, x, y

    def draw(self, fr, t):
        if not self.start <= t < self.end:
            return
        s = ease_out_back(progress(t, self.start, 0.45), 2.2)
        if t < self.tap:
            s *= 1 + 0.035 * math.sin(2 * math.pi * 1.6 * (t - self.start)) * progress(t, self.start + 0.45, 0.3)
        else:  # pressed down, then springs back
            u = t - self.tap
            if u < 0.12:
                s *= 1 - 0.12 * math.sin(math.pi / 2 * u / 0.12)
            elif u < 0.5:
                s *= 0.88 + 0.12 * ease_out_back((u - 0.12) / 0.38, 3.0)
        place(fr, self.after if t >= self.tap + 0.06 else self.before, self.x, self.y, s)


class Paw:
    """A paw that glides between points and taps. keys: [(time, x, y)] of the paw's tip."""
    z = 7

    def __init__(self, sprite, keys, taps):
        self.sprite, self.keys, self.taps = sprite, keys, taps
        self.anchor = (sprite.width * 0.5, sprite.height * 0.1)  # the tip of the middle toes

    def draw(self, fr, t):
        keys = self.keys
        if not keys[0][0] <= t <= keys[-1][0]:
            return
        for (ta, xa, ya), (tb, xb, yb) in zip(keys, keys[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta) if tb > ta else 1.0
                u = u * u * (3 - 2 * u)
                x, y = xa + (xb - xa) * u, ya + (yb - ya) * u
                break
        s = 1.0
        for tap in self.taps:
            if 0 <= t - tap < 0.24:
                s *= 1 - 0.18 * math.sin(math.pi * (t - tap) / 0.24)
        place(fr, self.sprite, x, y, s, rot=-16, anchor=self.anchor)


# ---------- the block ----------

def end_card(show, ask=ASK, farewell=FAREWELL):
    """ "Thanks for watching!", a grown-up can tap like and subscribe, then bye-bye. This ends the show."""
    t0 = show.t
    show.add(Letters(show.title(TITLE, 116), t0 + 0.1, t0 + 600, 960, 260))  # stays until the video ends
    for i in range(len(TITLE.replace(" ", ""))):
        show.sfx(t0 + 0.35 + i * 0.05, sound.sfx_plink(72 + (0, 2, 4, 5, 7, 9, 11, 12)[i % 8]), 0.16)
    who, line = ask
    asked = show.say(line, t0 + 0.9, who)
    tap1, tap2 = asked + 0.75, asked + 1.6
    t = tap2 + 0.9
    bye = t
    for who, line in farewell:
        t = show.say(line, t, who) + 0.25
    end = t + 1.4
    show.add(Button(like_buttons(), t0 + 0.5, tap1, end + 1, *LIKE_SPOT))
    show.add(Button(subscribe_buttons(), t0 + 0.7, tap2, end + 1, *SUB_SPOT))
    show.sfx(t0 + 0.5, sound.sfx_pop(), 0.3)
    show.sfx(t0 + 0.7, sound.sfx_pop(), 0.3)
    like_tip, sub_tip = (LIKE_SPOT[0] - 10, LIKE_SPOT[1] + 10), (SUB_SPOT[0], SUB_SPOT[1] + 10)
    show.add(Paw(paw_cursor(), [(asked + 0.05, 960, 1260), (tap1 - 0.05, *like_tip), (tap1 + 0.3, *like_tip),
                                (tap2 - 0.05, *sub_tip), (tap2 + 0.35, *sub_tip), (tap2 + 0.9, 1560, 1280)],
                 [tap1, tap2]))
    show.sfx(asked + 0.05, sound.sfx_whoosh(0.5), 0.2)
    for tap in (tap1, tap2):
        show.sfx(tap, sound.sfx_pop(), 0.4)
    show.sfx(tap1 + 0.05, sound.sfx_boop(84), 0.3)
    show.sfx(tap2 + 0.05, sound.sfx_chime(), 0.45)
    for k, n in enumerate((84, 88, 91, 96)):
        show.sfx(tap2 + 0.1 + 0.06 * k, sound.marimba(n, 0.5), 0.14)
    show.cheer(tap1, LIKE_SPOT, n=40)
    show.cheer(tap2, SUB_SPOT, n=90)
    for who in show.cast:
        show.act(who, "wave", bye, seconds=end - bye)
    show.loud_music.append((tap2, end))
    show.snap(tap2 + 0.4, "end card")
    show.t = end
