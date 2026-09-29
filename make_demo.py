#!/usr/bin/env python3
"""Make a demo episode for the kids' channel: "Guess the Color!"

    python3 make_demo.py              # full video -> output/guess_the_color_demo.mp4
    python3 make_demo.py --preview    # only a few still pictures (fast)
"""
import argparse
import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from kidsvid import art, sound
from kidsvid.anim import clamp, ease_in_back, ease_out_back, ease_out_bounce, ease_out_quad, place, progress

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"
W, H, FPS = 1920, 1080, 30

# The episode. Change this list to make a new episode.
ROUNDS = [("balloon", "red"), ("star", "yellow"), ("frog", "green"), ("fish", "blue")]

COLORS = {"red": art.RED, "orange": art.ORANGE, "yellow": art.YELLOW, "green": art.GREEN,
          "blue": art.BLUE, "purple": art.PURPLE, "pink": art.PINK}
DRAW = {"balloon": art.balloon, "star": art.star, "frog": art.frog, "fish": art.fish}
TITLE, OUTRO_TITLE = "Guess the Color!", "Great job!"

STAGE = (960, 530)     # where the thing to guess is shown
MASCOT = (270, 1046)   # where the lamb's feet are
COUNT_STEP = 0.85      # seconds for each countdown number
SCALE = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23]  # C major scale, for the letter "plinks"


@dataclass
class Round:
    thing: str
    color: str
    start: float = 0.0    # the thing pops in
    ask: float = 0.0      # "What color is this ...?"
    count: float = 0.0    # 3, 2, 1
    reveal: float = 0.0   # answer appears
    answer: float = 0.0   # "Red! It's a red balloon!"
    leave: float = 0.0    # everything flies away
    end: float = 0.0


def script(rounds):
    lines = {"intro": "Hi friends! Let's play a color game!",
             "outro": "Great job, friends! You know your colors! See you next time!"}
    for i, r in enumerate(rounds):
        lines[f"q{i}"] = f"What color is this {r.thing}?"
        lines[f"a{i}"] = f"{r.color.capitalize()}! It's a {r.color} {r.thing}!"
    return lines


class Episode:
    """When everything happens. Times come from the length of the voice lines."""

    def __init__(self, rounds, clips):
        def d(key):
            return len(clips[key]) / sound.SR

        self.rounds, self.clips = rounds, clips
        self.intro_say = 1.3
        self.title_out = self.intro_say + d("intro") + 0.5
        t = self.title_out + 0.45
        for i, r in enumerate(rounds):
            r.start = t
            r.ask = t + 0.6
            r.count = r.ask + d(f"q{i}") + 0.35
            r.reveal = r.count + 3 * COUNT_STEP
            r.answer = r.reveal + 0.3
            r.leave = r.answer + d(f"a{i}") + 0.75
            r.end = r.leave + 0.4
            t = r.end + 0.15
        self.outro = t
        self.outro_say = t + 0.9
        self.outro_done = self.outro_say + d("outro")
        self.duration = self.outro_done + 1.9

    def voice_events(self):
        keys = [(self.intro_say, "intro")]
        for i, r in enumerate(self.rounds):
            keys += [(r.ask, f"q{i}"), (r.answer, f"a{i}")]
        keys.append((self.outro_say, "outro"))
        return [(at, self.clips[k]) for at, k in keys]

    def sound_events(self):
        fx = [(0.15, sound.sfx_boing(), 0.35)]
        for i in range(len(TITLE.replace(" ", ""))):
            fx.append((0.5 + i * 0.05, sound.sfx_plink(72 + SCALE[i]), 0.2))
        fx.append((self.title_out, sound.sfx_whoosh(), 0.3))
        for r in self.rounds:
            fx.append((r.start, sound.sfx_pop(), 0.45))
            for k in range(3):
                fx.append((r.count + k * COUNT_STEP, sound.sfx_boop((72, 76, 79)[k]), 0.35))
            fx.append((r.reveal, sound.sfx_chime(), 0.5))
            fx.append((r.leave, sound.sfx_whoosh(), 0.3))
        for i in range(len(OUTRO_TITLE.replace(" ", ""))):
            fx.append((self.outro + 0.25 + i * 0.05, sound.sfx_plink(72 + SCALE[i]), 0.2))
        for i in range(len(self.rounds)):
            fx.append((self.outro + 0.4 + i * 0.22, sound.sfx_pop(), 0.4))
        fx.append((self.outro_done + 0.1, sound.sfx_chime(), 0.45))
        return fx

    def melody_level(self, t):
        return 1.0 if t < self.rounds[0].start or t > self.outro else 0.4


class Scene:
    """Draws one video frame for any time t."""

    def __init__(self, ep, mouth):
        self.ep, self.mouth = ep, mouth
        self.bg = art.background(W, H)
        self.clouds = [(art.cloud(s), x0, y, v) for x0, y, s, v in
                       ((150, 120, 1.0, 14), (820, 70, 0.7, 9), (1350, 190, 0.85, 11), (1720, 95, 0.6, 7))]
        self.stage = art.stage()
        self.things = {r.thing: DRAW[r.thing](COLORS[r.color]) for r in ep.rounds}
        self.title = art.title_letters(TITLE, 170)
        self.great = art.title_letters(OUTRO_TITLE, 170)
        self.question = art.text_sprite("What color is this?", 96, art.WHITE, inner=None)
        self.answers = [art.text_sprite(f"{r.color.capitalize()}!", 170, COLORS[r.color]) for r in ep.rounds]
        self.badges = [art.badge(str(n)) for n in (3, 2, 1)]
        self.lamb = {(e, m): art.lamb(e, m) for e in ("open", "blink", "happy") for m in range(6)}
        self.confetti = art.confetti_sprites()
        self.bubble = art.bubble()
        rnd = random.Random(11)
        self.blinks, t = [], 1.8
        while t < ep.duration:
            self.blinks.append(t)
            t += rnd.uniform(2.2, 4.2)
        self.cheers = [r.reveal for r in ep.rounds] + [ep.outro_done + 0.1]
        self.bursts = [self.burst(r.reveal, STAGE, rnd) for r in ep.rounds]
        self.bursts.append(self.burst(ep.outro + 0.3, (W / 2, 250), rnd, n=110))

    def burst(self, t0, origin, rnd, n=70):
        parts = []
        for _ in range(n):
            a, v = rnd.uniform(0, 2 * math.pi), rnd.uniform(500, 1300)
            parts.append((v * math.cos(a), v * math.sin(a) - 450, rnd.randrange(len(self.confetti)),
                          rnd.uniform(1.1, 1.7)))
        return t0, origin, parts

    # ----- pieces -----

    def draw_clouds(self, fr, t):
        for spr, x0, y, v in self.clouds:
            x = (x0 + v * t) % (W + spr.width) - spr.width
            fr.paste(spr, (round(x), y), spr)

    def draw_letters(self, fr, t, letters, t_in, t_out, cx, base_y):
        for i, (spr, anchor, dx) in enumerate(letters):
            ts = t_in + i * 0.05
            if t < ts:
                continue
            y = -200 + (base_y + 200) * ease_out_bounce(progress(t, ts, 0.7))
            y += 10 * math.sin(2 * math.pi * 1.1 * t - i * 0.55) * progress(t, ts + 0.7, 0.3)
            if t_out is not None:
                q = progress(t, t_out + i * 0.02, 0.45)
                if q >= 1:
                    continue
                y -= (base_y + 250) * ease_in_back(q)
            place(fr, spr, cx + dx, y, anchor=anchor)

    def draw_round(self, fr, t, i, r):
        if not r.start <= t < r.end:
            return
        cx, cy = STAGE
        out = 1 - ease_in_back(progress(t, r.leave, 0.4))
        place(fr, self.stage, cx, cy, ease_out_back(progress(t, r.start, 0.45)) * out)

        spr, anchor = self.things[r.thing]
        grow = ease_out_back(progress(t, r.start + 0.05, 0.55), 2.2) * out
        y = cy + 14 * math.sin(2 * math.pi * 0.55 * (t - r.start))
        rot = 4 * math.sin(2 * math.pi * 0.4 * (t - r.start))
        stretch = 1.0
        if r.reveal <= t < r.reveal + 0.8:  # happy jump
            h = abs(math.sin(2 * math.pi * (t - r.reveal) / 0.8))
            y -= 70 * h
            stretch = 1 + 0.07 * h
        if r.thing == "fish":
            for k in range(8):
                age = t - (r.start + 0.8 + k * 0.5)
                if 0 <= age < 2.2 and t < r.leave:
                    place(fr, self.bubble, cx - 175 + 12 * math.sin(age * 5 + k), y + 30 - 140 * age,
                          0.5 + 0.4 * clamp(age / 0.6))
        place(fr, spr, cx, y, grow / math.sqrt(stretch), grow * stretch, rot, anchor)

        qs, qa = self.question
        place(fr, qs, W / 2, 118, ease_out_back(progress(t, r.start + 0.35, 0.4)) * out, anchor=qa)

        for k in range(3):
            tk = r.count + k * COUNT_STEP
            if tk <= t < tk + COUNT_STEP and t < r.reveal:
                s = ease_out_back(progress(t, tk, 0.3), 2.5) * (1 - 0.1 * progress(t, tk + 0.5, 0.35))
                place(fr, self.badges[k], 1480, cy, s)

        if t >= r.reveal:
            spr_a, anc_a = self.answers[i]
            s = ease_out_back(progress(t, r.reveal, 0.45), 2.5) * out
            place(fr, spr_a, W / 2, 935, s, rot=3 * math.sin(2 * math.pi * 1.1 * (t - r.reveal)), anchor=anc_a)

    def draw_outro(self, fr, t):
        ep = self.ep
        if t < ep.outro:
            return
        self.draw_letters(fr, t, self.great, ep.outro + 0.1, None, W / 2, 250)
        n = len(ep.rounds)
        for i, r in enumerate(ep.rounds):
            tp = ep.outro + 0.4 + i * 0.22
            if t < tp:
                continue
            spr, anchor = self.things[r.thing]
            s = ease_out_back(progress(t, tp, 0.45), 2.2) * 0.44
            x = W / 2 + 100 + (i - (n - 1) / 2) * 290
            y = 600 + 18 * math.sin(2 * math.pi * 1.3 * t - i * 0.9)
            place(fr, spr, x, y, s, anchor=anchor)

    def draw_confetti(self, fr, t):
        for t0, (x0, y0), parts in self.bursts:
            age = t - t0
            if not 0 <= age < 1.8:
                continue
            drift = (1 - math.exp(-2 * age)) / 2  # air slows the pieces down
            for vx, vy, k, life in parts:
                if age >= life:
                    continue
                size = 0 if age < life * 0.6 else 1 if age < life * 0.85 else 2
                spr = self.confetti[k][size]
                x, y = x0 + vx * drift, y0 + vy * drift + 450 * age * age
                fr.paste(spr, (round(x - spr.width / 2), round(y - spr.height / 2)), spr)

    def draw_mascot(self, fr, t, i):
        if t < 0.15:
            return
        x, y = MASCOT
        sx = sy = 1.0
        eyes = "open"
        if t < 1.15:  # hops in from the left
            p = (t - 0.15) / 1.0
            x = -220 + (MASCOT[0] + 220) * ease_out_quad(p)
            h = abs(math.sin(3 * math.pi * p)) * (1 - 0.4 * p)
            y -= 70 * h
            sy, sx = 1 + 0.06 * h, 1 - 0.04 * h
        for c in self.cheers:
            if c <= t < c + 0.9:  # two happy jumps
                h = abs(math.sin(2 * math.pi * (t - c) / 0.9))
                y -= 55 * h
                sy, sx = 1 + 0.06 * h, 1 - 0.04 * h
            if c <= t < c + 1.3:
                eyes = "happy"
        if t >= self.ep.outro_done:
            eyes = "happy"
        breath = math.sin(2 * math.pi * 0.8 * t)
        sy *= 1 + 0.012 * breath
        sx *= 1 - 0.008 * breath
        m = int(self.mouth[i]) if i < len(self.mouth) else 0
        sy *= 1 + 0.006 * m
        if eyes == "open" and any(b <= t < b + 0.13 for b in self.blinks):
            eyes = "blink"
        place(fr, self.lamb[(eyes, m)], x, y, sx, sy, anchor=art.LAMB_FEET)

    # ----- whole frame -----

    def frame(self, i):
        t = i / FPS
        ep = self.ep
        fr = self.bg.copy()
        self.draw_clouds(fr, t)
        if t < ep.title_out + 1.0:
            self.draw_letters(fr, t, self.title, 0.25, ep.title_out, W / 2, 470)
        for k, r in enumerate(ep.rounds):
            self.draw_round(fr, t, k, r)
        self.draw_outro(fr, t)
        self.draw_confetti(fr, t)
        self.draw_mascot(fr, t, i)
        fade = progress(t, ep.duration - 0.8, 0.8)
        if fade > 0:
            fr = Image.blend(fr, Image.new("RGB", fr.size), fade)
        return fr


def contact_sheet(images, path, cols=3):
    w, h = W // cols, H // cols
    rows = -(-len(images) // cols)
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * h + (rows + 1) * 12), (255, 255, 255))
    for k, img in enumerate(images):
        sheet.paste(img.resize((w, h), Image.LANCZOS), (12 + (k % cols) * (w + 12), 12 + (k // cols) * (h + 12)))
    sheet.save(path, quality=90)


def main():
    ap = argparse.ArgumentParser(description="Make the 'Guess the Color!' demo video.")
    ap.add_argument("--preview", action="store_true", help="only save a few still pictures (fast)")
    ap.add_argument("--out", default=str(OUT / "guess_the_color_demo.mp4"))
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    rounds = [Round(thing, color) for thing, color in ROUNDS]
    voice = sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json")
    clips = {key: voice.say(text) for key, text in script(rounds).items()}
    ep = Episode(rounds, clips)
    n_frames = int(ep.duration * FPS)

    mouth = np.zeros(n_frames + 1, int)
    for at, clip in ep.voice_events():
        levels = sound.mouth_levels(clip, FPS)
        f0 = int(round(at * FPS))
        part = mouth[f0:f0 + len(levels)]
        part[:] = np.maximum(part, levels[:len(part)])

    scene = Scene(ep, mouth)
    r0, r1, r2 = rounds[0], rounds[1], rounds[2]
    key_times = [2.3, r0.ask + 1.0, r1.count + 0.3, r2.reveal + 0.55, rounds[-1].reveal + 0.9, ep.outro_done + 0.3]
    key_frames = {int(t * FPS): k for k, t in enumerate(key_times)}
    print(f"Episode length: {ep.duration:.1f} s, {n_frames} frames")

    if args.preview:
        stills = [scene.frame(f) for f in sorted(key_frames)]
        for k, img in enumerate(stills):
            img.save(OUT / f"still_{k}.png")
        contact_sheet(stills, OUT / "preview.jpg")
        return

    music = sound.music(ep.duration, ep.melody_level)
    audio = sound.mix(ep.duration, ep.voice_events(), ep.sound_events(), music)
    wav = OUT / "audio.wav"
    sound.write_wav(wav, audio)

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    stills = {}
    for i in range(n_frames):
        fr = scene.frame(i)
        proc.stdin.write(fr.tobytes())
        if i in key_frames:
            stills[i] = fr
        if i % 300 == 0:
            print(f"  frame {i}/{n_frames}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")
    contact_sheet([stills[f] for f in sorted(stills)], OUT / "preview.jpg")
    print("Done:", args.out)


if __name__ == "__main__":
    main()
