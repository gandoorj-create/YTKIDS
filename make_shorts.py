#!/usr/bin/env python3
"""YouTube Shorts from Episode 1: the guessing game, 5 questions in each Short (about 40 seconds).

    python3 make_shorts.py            # output/shorts/short_1.mp4, short_2.mp4 and shorts_youtube.txt
    python3 make_shorts.py --preview  # only still pictures (fast)

Shorts are tall (1080x1920). The episode is made again from the same building blocks and drawn like
this: a title on top, the questions in a "TV" in the middle, and Maple and Domi big at the bottom.
They move and talk exactly as in the episode.
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import make_episode1
from kidsvid import art, rig, sound
from kidsvid.anim import place
from kidsvid.show import FPS, Letters, loudness

OUT = make_episode1.OUT / "shorts"
SW, SH = 1080, 1920                    # a Short, standing up
CROP = (300, 0, 1620, 1080)            # the part of the episode picture that goes into the TV
TV = (40, 300, 1000)                   # x, y, width of the TV picture
PER_SHORT = 5                          # questions in each Short
TITLE = "Guess the color!"
YOUTUBE = """SHORT {n}: {file}
Title: Guess the Color! Can You Say It? | Maple & Domi #shorts
Description:
Can you guess the color? Say it out loud with Maple the puppy and Domi the kitten!
For toddlers and preschool kids (2-5 years). The full video "Learn Colors for Kids" is on our channel.
#learncolors #toddlerlearning #kidsvideos
Audience: Yes, it's made for kids
"""


def background():
    """Sky, and a grassy hill for Maple and Domi to stand on."""
    img = Image.new("RGB", (SW, SH))
    top, bottom = (112, 196, 255), (200, 236, 255)
    img.putdata([tuple(round(top[k] + (bottom[k] - top[k]) * min(y, 1500) / 1500) for k in range(3))
                 for y in range(SH) for _ in range(SW)])
    c = art.Canvas(SW, SH, ss=2)
    c.ellipse(250, 1690, 700, 260, fill=(168, 224, 134))
    c.ellipse(900, 1720, 640, 250, fill=(168, 224, 134))
    c.ellipse(540, 2000, 1000, 380, fill=(116, 202, 98))
    rnd = np.random.default_rng(5)
    for _ in range(26):
        x, y = rnd.uniform(30, SW - 30), rnd.uniform(1720, SH - 30)
        petal = [art.WHITE, (255, 182, 213), (255, 236, 140)][rnd.integers(3)]
        for k in range(5):
            a = 2 * np.pi * k / 5
            c.circle(x + 8 * np.cos(a), y + 8 * np.sin(a), 7, fill=petal)
        c.circle(x, y, 6, fill=(255, 170, 40))
    hills = c.result()
    img.paste(hills, (0, 0), hills)
    return img


def tv_frame(w, h):
    """A white rounded frame with a soft shadow (the TV), and the mask for its round corners."""
    pad, r = 14, 36
    c = art.Canvas(w + 2 * pad + 20, h + 2 * pad + 26)
    c.rounded_rect(10, 22, w + 2 * pad + 10, h + 2 * pad + 22, r + pad, (20, 30, 80, 70))
    c.rounded_rect(10, 10, w + 2 * pad + 10, h + 2 * pad + 10, r + pad, art.WHITE)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return c.result(), mask, pad + 10


class Short:
    """One Short: a piece of the episode (start..end seconds), drawn standing up."""

    def __init__(self, show, start, end):
        self.show, self.start, self.end = show, start, end
        x, y, w = TV
        self.tv_w, self.tv_h = w, round(w * (CROP[3] - CROP[1]) / (CROP[2] - CROP[0]))
        self.bg = background()
        self.frame_img, self.mask, self.frame_pad = tv_frame(self.tv_w, self.tv_h)
        self.title = Letters(art.title_letters(TITLE, 96), 0.1, 10 ** 6, SW / 2, 230)
        self.logo = art.title_letters("Yumizoo", 58)
        self.cast = []  # Maple and Domi again, big, doing the same things as in the episode
        for (who, ch), x_home in zip(show.cast.items(), (280, 770)):
            big = rig.Character(who, "golden" if who == "puppy" else "tuxedo", 0, home=(x_home, 1880), size=1.1)
            big.moves, big.talking, big.blinks, big.phase = ch.moves, ch.talking, ch.blinks, ch.phase
            self.cast.append(big)

    def frame(self, t):
        """Picture at `t` seconds into the Short."""
        te = self.start + t  # time in the episode
        fr = self.bg.copy()
        episode = self.show.frame(int(round(te * FPS))).crop(CROP).resize((self.tv_w, self.tv_h), Image.LANCZOS)
        x, y, _ = TV
        fr.paste(self.frame_img, (x - self.frame_pad, y - self.frame_pad), self.frame_img)
        fr.paste(episode, (x, y), self.mask)
        for spr, anchor, dx in self.logo:
            place(fr, spr, SW / 2 + dx, 110, anchor=anchor)
        self.title.draw(fr, t)
        for ch in self.cast:
            ch.draw(fr, te)
        return fr

    def sound(self, mix):
        a, b = int(self.start * sound.SR), int(self.end * sound.SR)
        clip = mix[a:b].copy()
        f = int(0.25 * sound.SR)
        clip[:f] *= np.linspace(0, 1, f)
        clip[-f:] *= np.linspace(1, 0, f)
        return clip

    def render(self, path, mix):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        wav = path.with_suffix(".wav")
        sound.write_wav(wav, self.sound(mix))
        gain = -14.0 - loudness(ffmpeg, wav)
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
               "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-pix_fmt", "yuv420p", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=5:release=50:level=0",
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(int((self.end - self.start) * FPS)):
            proc.stdin.write(self.frame(i / FPS).tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit("ffmpeg failed")
        wav.unlink()


def pieces(show):
    """(start, end) of each Short: the guessing game, PER_SHORT questions each."""
    names = [name for _, name in show.chapters]
    game = show.chapters[names.index("Guessing game")][0]
    after = show.chapters[names.index("Guessing game") + 1][0]
    rounds = [q for q in show.questions if game <= q[0] < after]
    out = []
    for k in range(0, len(rounds), PER_SHORT):
        group = rounds[k:k + PER_SHORT]
        out.append((game if k == 0 else group[0][0], group[-1][1]))  # the first one starts with the game's title
    return out


def main():
    ap = argparse.ArgumentParser(description="Make YouTube Shorts from Episode 1 (the guessing game).")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    voice = sound.Voice(make_episode1.VOICE / "voice.onnx", make_episode1.VOICE / "voice.json")
    show = make_episode1.build(voice)
    show._prepare()
    show.layers = [a for a in show.layers if not isinstance(a, rig.Character)]  # they are drawn big below the TV
    shorts = [Short(show, a, b) for a, b in pieces(show)]
    if args.preview:
        stills = [s.frame(t) for s in shorts for t in (1.0, 6.0, 12.0)]
        sheet = Image.new("RGB", (len(stills) * 370 + 10, 660), art.WHITE)  # tall pictures side by side
        for k, img in enumerate(stills):
            sheet.paste(img.resize((360, 640), Image.LANCZOS), (10 + k * 370, 10))
        sheet.save(OUT / "shorts_preview.jpg", quality=90)
        print("made", OUT / "shorts_preview.jpg")
        return
    mix = sound.mix(show.duration, show.voices, show.effects, sound.music(show.duration, show._melody_level),
                    show.music_level, show.duck)
    text = []
    for n, s in enumerate(shorts, 1):
        path = OUT / f"short_{n}.mp4"
        print(f"short {n}: {s.end - s.start:.1f} seconds")
        s.render(path, mix)
        text.append(YOUTUBE.format(n=n, file=path.name))
    (OUT / "shorts_youtube.txt").write_text("\n".join(text))
    print("Done.")


if __name__ == "__main__":
    main()
