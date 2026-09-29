"""Small animation helpers: easing curves and sprite placement."""
import math

from PIL import Image


def clamp(p):
    return 0.0 if p < 0 else 1.0 if p > 1 else p


def progress(t, start, duration):
    """0 before `start`, 1 after `start + duration`, smooth line in between."""
    return clamp((t - start) / duration)


def ease_out_quad(p):
    return 1 - (1 - p) ** 2


def ease_out_back(p, s=1.70158):
    """Grows a little too big, then settles (a "boing" feeling)."""
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def ease_in_back(p, s=1.70158):
    """Pulls back a little, then goes."""
    return p * p * ((s + 1) * p - s)


def ease_out_bounce(p):
    n, d = 7.5625, 2.75
    if p < 1 / d:
        return n * p * p
    if p < 2 / d:
        p -= 1.5 / d
        return n * p * p + 0.75
    if p < 2.5 / d:
        p -= 2.25 / d
        return n * p * p + 0.9375
    p -= 2.625 / d
    return n * p * p + 0.984375


def place(frame, sprite, x, y, sx=1.0, sy=None, rot=0.0, anchor=None):
    """Draw `sprite` on `frame` so its `anchor` point lands on (x, y).

    Scaling (sx, sy) and turning (rot, degrees, counter-clockwise) happen around the anchor.
    """
    sy = sx if sy is None else sy
    if sx <= 0.01 or sy <= 0.01:
        return
    w, h = sprite.size
    ax, ay = anchor if anchor else (w / 2, h / 2)
    vx, vy = (ax - w / 2) * sx, (ay - h / 2) * sy
    img = sprite
    if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        img = img.resize((max(1, round(w * sx)), max(1, round(h * sy))), Image.BICUBIC)
    if abs(rot) > 0.05:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
        a = math.radians(rot)
        vx, vy = vx * math.cos(a) + vy * math.sin(a), -vx * math.sin(a) + vy * math.cos(a)
    frame.paste(img, (round(x - vx - img.width / 2), round(y - vy - img.height / 2)), img)
