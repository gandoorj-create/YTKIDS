"""A small engine for kids' learning videos.

A Show is a timeline. Building blocks (see lessons.py) put pictures, voice lines and sound effects on it.
Then the Show draws every frame, mixes the sound and saves the video.
"""
import math
import random
import re
import subprocess
from dataclasses import dataclass, field

import imageio_ffmpeg
import numpy as np
from PIL import Image

from . import art, sound
from .anim import ease_in_back, ease_out_back, ease_out_bounce, ease_out_quad, place, progress

W, H, FPS = 1920, 1080, 30
MASCOT = (270, 1046)  # where the lamb's feet are
COUNT_STEP = 1.0      # seconds for each countdown number (3, 2, 1)


@dataclass
class Actor:
    """A picture on screen from `start` to `end`. It pops in, floats a little, and pops out."""
    sprite: Image.Image
    anchor: tuple
    start: float
    end: float
    x: float
    y: float
    scale: float = 1.0
    bob: float = 0.0          # floating up and down (pixels)
    wobble: float = 0.0       # turning left and right (degrees)
    jumps: list = field(default_factory=list)  # times of happy jumps
    shrink_at: float = None   # time when it gets smaller (a wrong answer)
    z: int = 1                # drawing order: bigger is in front
    phase: float = 0.0

    def draw(self, fr, t):
        if not self.start <= t < self.end:
            return
        age = t - self.start
        s = (self.scale * ease_out_back(progress(t, self.start, 0.5), 2.0)
             * (1 - ease_in_back(progress(t, self.end - 0.4, 0.4))))
        y = self.y + self.bob * math.sin(2 * math.pi * 0.55 * age + self.phase)
        rot = self.wobble * math.sin(2 * math.pi * 0.4 * age + self.phase)
        sx = sy = s
        for j in self.jumps:
            if j <= t < j + 0.8:
                h = abs(math.sin(2 * math.pi * (t - j) / 0.8))
                y -= 70 * self.scale * h
                sy *= 1 + 0.07 * h
                sx /= math.sqrt(1 + 0.07 * h)
        if self.shrink_at is not None and t >= self.shrink_at:
            k = 1 - 0.3 * ease_out_quad(progress(t, self.shrink_at, 0.3))
            sx, sy = sx * k, sy * k
        place(fr, self.sprite, self.x, y, sx, sy, rot, self.anchor)


@dataclass
class Letters:
    """A title: every letter falls down and bounces, then they fly up and away at `leave`."""
    letters: list
    start: float
    leave: float
    x: float
    y: float
    z: int = 5

    def draw(self, fr, t):
        if t < self.start or t > self.leave + 0.5 + 0.02 * len(self.letters):
            return
        for i, (spr, anchor, dx) in enumerate(self.letters):
            ts = self.start + i * 0.05
            q = progress(t, self.leave + i * 0.02, 0.45)
            if t < ts or q >= 1:
                continue
            y = -200 + (self.y + 200) * ease_out_bounce(progress(t, ts, 0.7))
            y += 10 * math.sin(2 * math.pi * 1.1 * t - i * 0.55) * progress(t, ts + 0.7, 0.3)
            y -= (self.y + 250) * ease_in_back(q)
            place(fr, spr, self.x + dx, y, anchor=anchor)


@dataclass
class Countdown:
    """3, 2, 1 in an orange badge, starting at `start`."""
    badges: list
    start: float
    x: float
    y: float
    z: int = 6

    def draw(self, fr, t):
        k = math.floor((t - self.start) / COUNT_STEP)
        if 0 <= k < 3:
            tk = self.start + k * COUNT_STEP
            s = ease_out_back(progress(t, tk, 0.3), 2.5) * (1 - 0.1 * progress(t, tk + 0.6, 0.4))
            place(fr, self.badges[k], self.x, self.y, s)


class Show:
    def __init__(self, voice, seed=1, mascot=True):
        self.voice = voice
        self.mascot = mascot     # True: the lamb in the corner talks (older videos)
        self.cast = {}           # characters that talk and move, by name (see rig.py and join)
        self.music = None        # own music track (numpy array); None = the normal background music
        self.music_level = 0.075
        self.duck = 0.35         # how much the music goes down while someone talks
        self.t = 0.0             # where the next part starts
        self.actors = []
        self.voices = []         # (time, clip)
        self.effects = []        # (time, sound, gain)
        self.cheers = []         # happy moments: the characters (or the lamb) jump for joy
        self.bursts = []         # confetti: (time, origin, pieces)
        self.chapters = []       # (time, name)
        self.snaps = []          # (time, name): moments for the preview pictures
        self.questions = []      # (start, end, thing, color) of every quiz question (make_shorts.py uses them)
        self.loud_music = []     # (start, end): parts where the music melody plays loud
        self.happy_from = None   # from this time the lamb keeps happy eyes
        self.fade = 0.8          # seconds of fading to black at the end
        self.rnd = random.Random(seed)
        self._clips, self._sprites = {}, {}
        self.badges = [art.badge(str(n)) for n in (3, 2, 1)]
        self.stage = art.stage()
        self.ring = art.ring()
        self.confetti = art.confetti_sprites()

    # ----- putting things on the timeline -----

    def join(self, character):
        """Put a character (see rig.Character) in the show. Lines and movements can then use its name."""
        self.cast[character.kind] = character
        self.add(character)

    def say(self, text, at, who=None):
        """Voice line at time `at`, said by `who` (a character's name). Returns the time when it ends.

        Without that character in the show, the normal voice says it (and the lamb's mouth moves).
        """
        speaker = self.cast.get(who)
        key = (who if speaker else None, text)
        if key not in self._clips:
            self._clips[key] = speaker.say(self.voice, text) if speaker else self.voice.say(text)
        clip = self._clips[key]
        self.voices.append((at, clip))
        if speaker:
            speaker.talking.append((at, sound.mouth_levels(clip, FPS)))
        return at + len(clip) / sound.SR

    def act(self, who, move, at, seconds=None):
        """A movement of a character (a name from rig.MOVES), if that character is in the show."""
        if who in self.cast:
            self.cast[who].act(move, at, seconds)

    def sfx(self, at, sig, gain=0.4):
        self.effects.append((at, sig, gain))

    def add(self, actor):
        self.actors.append(actor)
        return actor

    def _cached(self, key, make):
        if key not in self._sprites:
            self._sprites[key] = make()
        return self._sprites[key]

    def thing(self, name, color):
        return self._cached(("thing", name, color), lambda: art.THINGS[name](art.COLORS[color]))

    def splat(self, color):
        return self._cached(("splat", color), lambda: art.splat(art.COLORS[color], seed=len(self._sprites)))

    def text(self, words, size, color=art.WHITE, **kw):
        if color == art.WHITE:
            kw.setdefault("inner", None)
        key = ("text", words, size, color, tuple(sorted(kw.items())))
        return self._cached(key, lambda: art.text_sprite(words, size, color, **kw))

    def title(self, words, size=160):
        return self._cached(("title", words, size), lambda: art.title_letters(words, size))

    def cheer(self, at, origin=None, n=70, move=None):
        """Happy moment: the characters jump for joy, and confetti flies from `origin`.

        move: what the characters do (a name from rig.MOVES). None: "happy" and "jump", taking turns.
        """
        self.cheers.append(at)
        for k, who in enumerate(self.cast):
            self.act(who, move or ("happy", "jump")[(len(self.cheers) + k) % 2], at)
        if origin is None:
            return
        pieces = []
        for _ in range(n):
            a, v = self.rnd.uniform(0, 2 * math.pi), self.rnd.uniform(500, 1300)
            pieces.append((v * math.cos(a), v * math.sin(a) - 450, self.rnd.randrange(len(self.confetti)),
                           self.rnd.uniform(1.1, 1.7)))
        self.bursts.append((at, origin, pieces))

    def chapter(self, name):
        self.chapters.append((self.t, name))

    def snap(self, at, name):
        self.snaps.append((at, name))

    def chapters_text(self, offset=0.0):
        """Chapters for YouTube. offset: seconds of video before this show (like the channel intro).
        The first chapter always starts at 0:00."""
        times = [0.0] + [t + offset for t, _ in self.chapters[1:]]
        return "\n".join(f"{int(t // 60)}:{int(t % 60):02d} {name}" for t, (_, name) in zip(times, self.chapters))

    # ----- drawing -----

    def _prepare(self):
        self.duration = self.t
        self.n_frames = int(self.duration * FPS)
        self.mouth = np.zeros(self.n_frames + 1, int)
        for at, clip in self.voices:
            levels = sound.mouth_levels(clip, FPS)
            f0 = int(round(at * FPS))
            part = self.mouth[f0:f0 + len(levels)]
            part[:] = np.maximum(part, levels[:len(part)])
        rnd = random.Random(11)
        self.blinks, t = [], 1.8
        while t < self.duration:
            self.blinks.append(t)
            t += rnd.uniform(2.2, 4.2)
        self.bg = art.background(W, H)
        self.clouds = [(art.cloud(s), x0, y, v) for x0, y, s, v in
                       ((150, 120, 1.0, 14), (820, 70, 0.7, 9), (1350, 190, 0.85, 11), (1720, 95, 0.6, 7))]
        if self.mascot:
            self.lamb = {(e, m): art.lamb(e, m) for e in ("open", "blink", "happy") for m in range(6)}
        self.layers = sorted(self.actors, key=lambda a: a.z)

    def _confetti(self, fr, t):
        for t0, (x0, y0), pieces in self.bursts:
            age = t - t0
            if not 0 <= age < 1.8:
                continue
            drift = (1 - math.exp(-2 * age)) / 2  # air slows the pieces down
            for vx, vy, k, life in pieces:
                if age >= life:
                    continue
                spr = self.confetti[k][0 if age < life * 0.6 else 1 if age < life * 0.85 else 2]
                x, y = x0 + vx * drift, y0 + vy * drift + 450 * age * age
                fr.paste(spr, (round(x - spr.width / 2), round(y - spr.height / 2)), spr)

    def _mascot(self, fr, t, i):
        if t < 0.15:
            return
        x, y = MASCOT
        sx = sy = 1.0
        eyes = "open"
        if t < 1.15:  # hops in from the left
            p = t - 0.15
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
        if self.happy_from is not None and t >= self.happy_from:
            eyes = "happy"
        breath = math.sin(2 * math.pi * 0.8 * t)
        m = int(self.mouth[i]) if i < len(self.mouth) else 0
        sy *= (1 + 0.012 * breath) * (1 + 0.006 * m)
        sx *= 1 - 0.008 * breath
        if eyes == "open" and any(b <= t < b + 0.13 for b in self.blinks):
            eyes = "blink"
        place(fr, self.lamb[(eyes, m)], x, y, sx, sy, anchor=art.LAMB_FEET)

    def frame(self, i):
        t = i / FPS
        fr = self.bg.copy()
        for spr, x0, y, v in self.clouds:
            fr.paste(spr, (round((x0 + v * t) % (W + spr.width) - spr.width), y), spr)
        for actor in self.layers:
            actor.draw(fr, t)
        self._confetti(fr, t)
        if self.mascot:
            self._mascot(fr, t, i)
        fade = progress(t, self.duration - self.fade, self.fade) if self.fade else 0
        if fade > 0:
            fr = Image.blend(fr, Image.new("RGB", fr.size), fade)
        return fr

    def _melody_level(self, t):
        return 1.0 if any(a <= t < b for a, b in self.loud_music) else 0.4

    # ----- output -----

    def preview(self):
        """Only the snap moments, as pictures (fast)."""
        self._prepare()
        return {name: self.frame(int(t * FPS)) for t, name in self.snaps}

    def render(self, out):
        """Make the whole video. Returns the snap moments as pictures."""
        self._prepare()
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        wav = out.with_suffix(".wav")
        music = self.music if self.music is not None else sound.music(self.duration, self._melody_level)
        sound.write_wav(wav, sound.mix(self.duration, self.voices, self.effects, music, self.music_level, self.duck))
        # YouTube plays videos at about -14 LUFS and never makes quiet videos louder, so we do it here.
        # The limiter stops the few loudest peaks from breaking.
        gain = -14.0 - loudness(ffmpeg, wav)
        cmd = [ffmpeg, "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=5:release=50:level=0",
               "-c:a", "aac", "-b:a", "192k", "-ar", str(sound.SR), "-shortest", "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        keep = {int(t * FPS): name for t, name in self.snaps}
        stills = {}
        for i in range(self.n_frames):
            fr = self.frame(i)
            proc.stdin.write(fr.tobytes())
            if i in keep:
                stills[keep[i]] = fr
            if i % 1800 == 0:
                print(f"  {i / FPS / 60:.1f} / {self.duration / 60:.1f} min", flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit("ffmpeg failed")
        wav.unlink()
        return stills


def loudness(ffmpeg, path):
    """Loudness of a sound file in LUFS (the unit YouTube uses), measured by ffmpeg."""
    log = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])


def contact_sheet(images, path, cols=3):
    """Small copies of pictures in a grid, in one image."""
    w, h = W // cols, H // cols
    rows = -(-len(images) // cols)
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * h + (rows + 1) * 12), (255, 255, 255))
    for k, img in enumerate(images):
        sheet.paste(img.resize((w, h), Image.LANCZOS), (12 + (k % cols) * (w + 12), 12 + (k // cols) * (h + 12)))
    sheet.save(path, quality=90)
