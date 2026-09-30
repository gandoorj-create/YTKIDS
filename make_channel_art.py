#!/usr/bin/env python3
"""YouTube channel pictures: the profile picture (800x800) and the banner (2560x1440).

    python3 make_channel_art.py

Makes output/channel_avatar.png, output/channel_banner.png, output/channel_banner_check.jpg
(the banner with the parts that phones, computers and TVs show) and output/channel_watermark.png.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

from kidsvid import art, rig
from kidsvid.anim import place

OUT = Path(__file__).resolve().parent / "output"
BANNER = (2560, 1440)
SAFE = (1546, 423)  # always visible, also on phones (in the middle)
TAGLINE = "Learn and play with Maple & Domi!"


def sky(w, h):
    """The sky of the background, without hills."""
    top, bottom = (112, 196, 255), (200, 236, 255)
    col = Image.new("RGB", (1, h))
    col.putdata([tuple(round(top[k] + (bottom[k] - top[k]) * y / h) for k in range(3)) for y in range(h)])
    return col.resize((w, h))


def avatar(path, size=800):
    """Maple and Domi, cheek to cheek. YouTube shows it as a circle, so they stay in the middle."""
    img = sky(size, size)
    d = ImageDraw.Draw(img)
    for r, color in ((370, (150, 214, 255)), (300, (175, 225, 255))):  # soft rings behind the heads
        d.ellipse((size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r), fill=color)
    for kind, colors, x in (("kitten", "tuxedo", 528), ("puppy", "golden", 300)):  # the puppy in front
        ch = rig.Character(kind, colors, 0, home=(x, 850), size=1.1)
        ch.draw_pose(img, rig.Pose(x, 850, eyes="happy", mouth=2, head_rot=6 if kind == "puppy" else -6,
                                   tail=80))  # the tail goes behind the body
    img.save(path)
    return img


def banner(path):
    w, h = BANNER
    img = art.background(w, h)  # sky, hills and flowers (the hills are made for 1080 pixels high)
    flowers = art.Canvas(w, h, ss=2)  # more flowers on the grass below (only TVs show it)
    rnd = random.Random(8)
    for _ in range(90):
        x, y = rnd.uniform(20, w - 20), rnd.uniform(1080, h - 20)
        petal = rnd.choice([art.WHITE, (255, 182, 213), (255, 236, 140)])
        for k in range(5):
            a = 2 * math.pi * k / 5
            flowers.circle(x + 9 * math.cos(a), y + 9 * math.sin(a), 8, fill=petal)
        flowers.circle(x, y, 6, fill=(255, 170, 40))
    layer = flowers.result()
    img.paste(layer, (0, 0), layer)
    top = sky(w, 560)
    img.paste(top.resize((w, 560)), (0, 0))
    for x, y, s in ((180, 150, 1.3), (900, 90, 1.0), (1700, 180, 1.2), (2300, 110, 1.1), (420, 1150, 0.0)):
        if s:
            cloud = art.cloud(s)
            img.paste(cloud, (x, y), cloud)
    for name, color, x, y, s, rot in (("balloon", "red", 330, 640, 0.45, 8), ("star", "yellow", 2240, 600, 0.42, -10),
                                      ("fish", "blue", 2330, 830, 0.36, 6), ("frog", "green", 250, 900, 0.36, -4),
                                      ("grapes", "purple", 120, 700, 0.3, 10), ("apple", "red", 2470, 700, 0.3, -8)):
        spr, anc = art.THINGS[name](art.COLORS[color])
        place(img, spr, x, y, s, rot=rot, anchor=anc)
    cy = h // 2
    for spr, anchor, dx in art.title_letters("Yumizoo", 165):
        place(img, spr, w / 2 + dx, cy + 25, anchor=anchor)
    tag, tag_anchor = art.text_sprite(TAGLINE, 50, art.WHITE, inner=None)
    place(img, tag, w / 2, cy + 130, anchor=tag_anchor)
    for kind, colors, x, pose in (("puppy", "golden", 700, rig.Pose(700, 925, arm_l=10, eyes="happy", mouth=2)),
                                  ("kitten", "tuxedo", 1855, rig.Pose(1855, 925, arm_r=-10, eyes="happy", mouth=2))):
        ch = rig.Character(kind, colors, 0, home=(x, 925), size=0.68)
        ch.draw_pose(img, pose)
    img.save(path)
    return img


def watermark(path, size=600):
    """A round badge with a paw (YouTube: square, at least 150x150, under 1 MB). Transparent around it."""
    c = art.Canvas(size, size)
    m, r = size / 2, size * 0.46
    ring = size * 0.06
    for k, color in enumerate(art.RAINBOW):  # a rainbow ring, like the Yumizoo letters
        angles = [math.radians(-90 + (k + i / 16) * 360 / 7) for i in range(17)]
        outer = [(m + (r + ring / 2) * math.cos(a), m + (r + ring / 2) * math.sin(a)) for a in angles]
        inner = [(m + (r - ring / 2) * math.cos(a), m + (r - ring / 2) * math.sin(a)) for a in reversed(angles)]
        c.polygon(outer + inner, color)
    c.circle(m, m, r - ring / 2, fill=art.WHITE)
    fur, line, bean = (255, 236, 208), (176, 132, 100), (255, 162, 186)
    cy = m + size * 0.07
    toes = [(-0.19, -0.17), (-0.07, -0.265), (0.07, -0.265), (0.19, -0.17)]
    for grow, color in ((size * 0.012, line), (0, fur)):
        c.ellipse(m, cy, size * 0.2 + grow, size * 0.165 + grow, fill=color)
        for dx, dy in toes:
            c.circle(m + dx * size, cy + dy * size, size * 0.07 + grow, fill=color)
    c.ellipse(m, cy + size * 0.02, size * 0.12, size * 0.09, fill=bean)
    for dx, dy in toes:
        c.circle(m + dx * size, cy + dy * size, size * 0.038, fill=bean)
    img = c.result()
    img.save(path)
    return img


def check(img, path):
    """The banner, with boxes: phone (the safe middle) and computer (the full-width band)."""
    w, h = BANNER
    sw, sh = SAFE
    view = img.copy()
    d = ImageDraw.Draw(view)
    d.rectangle(((w - sw) / 2, (h - sh) / 2, (w + sw) / 2, (h + sh) / 2), outline=(255, 0, 0), width=6)
    d.rectangle((0, (h - sh) / 2, w - 1, (h + sh) / 2), outline=(255, 255, 0), width=6)
    d.text(((w - sw) / 2 + 12, (h - sh) / 2 + 6), "phone", fill=(255, 0, 0), font=art.font(40))
    d.text((12, (h - sh) / 2 + 6), "computer", fill=(255, 255, 0), font=art.font(40))
    d.text((12, 12), "TV: everything", fill=(255, 255, 255), font=art.font(40))
    view.resize((1280, 720)).save(path, quality=90)


def main():
    OUT.mkdir(exist_ok=True)
    avatar(OUT / "channel_avatar.png")
    check(banner(OUT / "channel_banner.png"), OUT / "channel_banner_check.jpg")
    watermark(OUT / "channel_watermark.png")
    print("made channel_avatar.png, channel_banner.png, channel_banner_check.jpg, channel_watermark.png")


if __name__ == "__main__":
    main()
