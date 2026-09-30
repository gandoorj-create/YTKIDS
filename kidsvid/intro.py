"""The Yumizoo channel intro: "Peek-a-boo! Yu-mi-zoo!" (about 4.6 seconds).

The puppy and the kitten hide behind a hill. Their ears peek out, then their eyes ("Peek-a..."),
then they jump up ("...BOO!"). Kids answer with the channel name: "Yu-mi-ZOO!".

Why it is made like this (research notes are in the README, "Channel intro"):
- short: a branded intro should be about 3-5 seconds, the first seconds decide if people stay;
- a 6-note tune with the channel name in it: a melody and the name make a sound logo easy to remember;
- peekaboo, the favorite game of little kids: hiding, then a happy surprise at the expected moment;
- call and answer: the characters sing "Peek-a-boo!", kids answer "Yu-mi-zoo!", so kids at home learn
  to shout the answer (children join in more when a video leaves them a part);
- the tune never changes (so kids know it at once), but a small surprise can change in every episode
  (GAGS), so the intro stays fun to watch.
"""
import math

import numpy as np

from . import art, rig, sing, sound
from .anim import clamp, ease_out_back, ease_out_quad, place
from .show import Actor, Show

BPM = 120
BEAT = 60 / BPM
LENGTH = 4.6
NAME = "Yumizoo"
SYLLABLES = [(0, 2), (2, 4), (4, 7)]  # letters of "Yu", "mi", "zoo"
LANDS = (0.3, 0.45, 0.6)              # when each syllable of the logo lands

# The sound logo: (beat, syllable, MIDI note, beats). "uh" is the "a" of "peek-a-boo".
CALL = [(2, "peek", 64, 0.45), (2.5, "uh", 67, 0.45), (3, "boo", 72, 0.9)]   # E G C: the puppy and the kitten
ANSWER = [(4, "you", 69, 0.45), (4.5, "me", 67, 0.45), (5, "zoo", 72, 2.0)]  # A G C: the kids answer
PEEK, BOO, ZOO = 2 * BEAT, 3 * BEAT, 5 * BEAT
# The kids who answer: (voice size, cents out of tune, seconds late, loudness)
KIDS = [(1.25, -10, 0.020, 0.7), (1.32, 12, 0.034, 0.6), (1.2, 5, 0.046, 0.55), (1.38, -6, 0.028, 0.5)]

GAGS = {  # the small surprise; the tune is always the same
    "boo": "both jump up together",
    "late": "the kitten comes up late and gets a surprise",
    "flip": "both do a flip in the air",
}

HILL = (960, 1300, 1250, 470)  # the hill in front: an oval (middle x, middle y, half width, half height)
SIZE = 0.9
SPOTS = {"puppy": 660, "kitten": 1260}
EARS = {"puppy": 200, "kitten": 150}  # how much shows when only the ears peek (y in the character picture)
LOGO = (960, 330, 250)                # x, y of the letters' bottom line, letter size


def hill_top(x):
    cx, cy, rx, ry = HILL
    return cy - ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))


def hill():
    """The grassy hill in front. Returns (picture, top-left corner)."""
    cx, cy, rx, ry = HILL
    c = art.Canvas(1920, 1080, ss=2)
    c.ellipse(cx, cy, rx, ry, fill=(88, 170, 78))                # dark edge
    c.ellipse(cx, cy + 12, rx - 5, ry - 5, fill=(126, 208, 104))  # grass
    rnd = np.random.default_rng(3)
    for _ in range(26):
        x = rnd.uniform(80, 1840)
        y = rnd.uniform(hill_top(x) + 45, 1070)
        petal = [art.WHITE, (255, 182, 213), (255, 236, 140)][rnd.integers(3)]
        for k in range(5):
            a = 2 * math.pi * k / 5
            c.circle(x + 8 * math.cos(a), y + 8 * math.sin(a), 7, fill=petal)
        c.circle(x, y, 6, fill=(255, 170, 40))
    img = c.result()
    box = img.getbbox()
    return img.crop(box), box[:2]


class Still:
    """A picture that does not move."""

    def __init__(self, sprite, corner, z):
        self.sprite, self.corner, self.z = sprite, corner, z

    def draw(self, fr, t):
        fr.paste(self.sprite, self.corner, self.sprite)


def wobble(t, impacts):
    """Jelly squash after landings: returns (x scale, y scale)."""
    sx = sy = 1.0
    for when, amount in impacts:
        tau = t - when
        if 0 <= tau < 1.5:
            w = amount * math.exp(-5 * tau) * math.cos(2 * math.pi * 6 * tau)
            sy *= 1 - w
            sx *= 1 + 0.8 * w
    return sx, sy


class Logo:
    """ "Yumizoo": the syllables drop in, then each one bounces when the kids sing it."""
    z = 2

    def __init__(self, x, y, size):
        self.letters = art.title_letters(NAME, size)
        self.x, self.y = x, y

    def draw(self, fr, t):
        for g, (a, b) in enumerate(SYLLABLES):
            land, sung = LANDS[g], ANSWER[g][0] * BEAT
            if t < land - 0.3:
                continue
            for i in range(a, b):
                spr, anchor, dx = self.letters[i]
                sx = sy = 1.0
                if t < land:  # falling
                    p = (t - (land - 0.3)) / 0.3
                    y = -150 + (self.y + 150) * p * p
                else:
                    y = self.y
                    sx, sy = wobble(t, [(land, 0.25), (sung + 0.25, 0.12)])
                    if 0 <= t - sung < 0.3:
                        y -= 45 * math.sin(math.pi * (t - sung) / 0.3)
                    tj = ZOO + 0.04 * i  # everybody jumps on "ZOO!"
                    if 0 <= t - tj < 0.45:
                        y -= 60 * math.sin(math.pi * (t - tj) / 0.45)
                place(fr, spr, self.x + dx, y, sx, sy, anchor=anchor)


class Peeker(rig.Character):
    """The puppy or the kitten behind the hill.

    ears_at: when the ears pop up. up_at: when it jumps up ("BOO!"). flip: a flip in that jump.
    """

    def __init__(self, kind, colors, seed, ears_at, up_at=BOO, flip=False):
        x = SPOTS[kind]
        super().__init__(kind, colors, 0, seed=seed, home=(x, hill_top(x) + 8), size=SIZE)
        self.ears_at, self.up_at, self.flip = ears_at, up_at, flip
        top = self.ground - 8
        # Where the feet are (screen y) for: hidden, only the ears, peeking eyes, standing on the hill.
        self.stage = {"hidden": top + 650, "ears": top + (588 - EARS[kind]) * SIZE,
                      "peek": top + (588 - 290) * SIZE, "up": self.ground}
        self.land = up_at + 0.45

    def feet(self, t):
        s = self.stage
        if t < self.ears_at:
            return s["hidden"]
        if t < PEEK:  # the ears pop up (a little too far, then back)
            return s["hidden"] + (s["ears"] - s["hidden"]) * ease_out_back(clamp((t - self.ears_at) / 0.25), 2.0)
        if t < self.up_at:  # the eyes peek over the hill, then duck a little before "BOO!"
            y = s["ears"] + (s["peek"] - s["ears"]) * ease_out_quad(clamp((t - PEEK) / 0.15))
            return y + 24 * math.sin(math.pi * clamp((t - (self.up_at - 0.25)) / 0.25))
        u = t - self.up_at
        apex = s["up"] - 170
        if u < 0.22:  # jump up...
            return s["peek"] + (apex - s["peek"]) * ease_out_quad(u / 0.22)
        if u < 0.45:  # ...and land on the hill
            return apex + (s["up"] - apex) * ((u - 0.22) / 0.23) ** 2
        y = s["up"]
        for when, height, length in ((ANSWER[0][0] * BEAT, 24, 0.2), (ANSWER[1][0] * BEAT, 24, 0.2),
                                     (ZOO, 90, 0.45)):
            if when >= self.land and 0 <= t - when < length:  # hops on "Yu", "mi" and a jump on "ZOO!"
                y -= height * math.sin(math.pi * (t - when) / length)
        return y

    def pose(self, t):
        p = super().pose(t)  # breathing, blinking, the mouth (singing) and rig movements (like "wave")
        p.y += (self.feet(t) - self.ground) / self.size  # rig movements are in full-size pixels
        u = t - self.up_at
        if self.ears_at <= t < PEEK:  # wiggly ears
            w = math.sin(2 * math.pi * 4 * t)
            p.ear_l, p.ear_r = p.ear_l + 16 * w, p.ear_r - 16 * w
            p.head_rot += 4 * w
        if 0 <= u < 0.5:  # "BOO!": arms up, big eyes, then happy
            p.arm_l = p.arm_r = 0.0
            p.eyes = "wide" if u < 0.15 else "happy"
            q = math.sin(math.pi * clamp(u / 0.45))
            p.sy *= 1 + 0.06 * q
            p.sx *= 1 - 0.04 * q
            if self.flip:
                p.pivot = rig.ROLL_PIVOT
                p.rot += (360 if self.side == "right" else -360) * rig.smooth(u / 0.45)
        if 0 <= t - self.land < 0.2:  # squash when landing
            q = math.sin(math.pi * (t - self.land) / 0.2)
            p.sy *= 1 - 0.12 * q
            p.sx *= 1 + 0.1 * q
        if 0 <= t - ZOO < 0.6 and ZOO >= self.land:  # "ZOO!": arms up again
            p.arm_l = p.arm_r = 0.0
            p.eyes = "happy"
        return p


def jingle():
    """The music under the singing: bass, plucked chords, drums and bells. Loudness (RMS) = 1."""
    out = np.zeros(int((LENGTH + 1) * sound.SR))

    def add(sig, beat, gain):
        sound.add(out, sig, beat * BEAT, gain)

    add(sound.pluck(48, 0.4), 1.2, 0.3)  # tiptoe while the ears peek
    add(sound.pluck(55, 0.4), 1.6, 0.3)
    add(sound.bass(36), 2, 0.4)
    for k in range(4):
        add(sound.shaker(), 2 + k / 2, 0.06)
    chords = {3: (36, (60, 64, 67, 72)), 4: (41, (60, 65, 69, 72)), 5: (36, (60, 64, 67, 72, 76))}
    for beat, (root, notes) in chords.items():
        add(sound.bass(root, 0.9), beat, 0.55)
        add(sound.kick(), beat, 0.5)
        for j, n in enumerate(notes):
            add(sound.pluck(n, 1.4), beat + 0.02 * j, 0.09)
    add(sound.clap(), 3.5, 0.18)
    add(sound.clap(), 4.5, 0.18)
    add(sound.bass(36, 0.9), 4.5, 0.35)
    for beat, _, note, beats in CALL + ANSWER:  # bells play the tune with the singers
        add(sound.marimba(note + 12, 0.35 + beats * BEAT), beat, 0.16)
    for k in range(4):
        add(sound.shaker(), 5 + k / 2, 0.05)
    out = out[:int(LENGTH * sound.SR)]
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-9)


def voices(voice):
    """The singing. Returns (all voices mixed, the puppy's part, the kitten's part)."""
    call = [(b * BEAT, s, n, d * BEAT) for b, s, n, d in CALL]
    answer = [(b * BEAT, s, n, d * BEAT) for b, s, n, d in ANSWER]
    puppy = sing.sing(voice, call, LENGTH, formant=2 ** (3 / 12)) \
        + 0.6 * sing.sing(voice, answer, LENGTH, formant=2 ** (3 / 12))
    kitten = sing.sing(voice, call, LENGTH, formant=2 ** (6 / 12), detune=8, late=0.012) \
        + 0.6 * sing.sing(voice, answer, LENGTH, formant=2 ** (6 / 12), detune=8, late=0.012)
    kids = sum(gain * sing.sing(voice, answer, LENGTH, formant=f, detune=c, late=late) for f, c, late, gain in KIDS)
    kids = kids / np.max(np.abs(kids))
    mix = puppy + 0.85 * kitten + 1.1 * kids
    level = sound.smooth(np.abs(mix), int(0.01 * sound.SR))
    mix = mix * np.clip((0.3 / (level + 1e-4)) ** 0.4, 0.6, 2.0)  # a gentle compressor: even and clear
    return 0.9 * mix / np.max(np.abs(mix)), puppy, kitten


def whistle_drop(seconds=0.28):
    """A little falling whistle (the logo letters drop in)."""
    t = sound.t_axis(seconds)
    f = 1400 - 700 * (t / seconds) ** 1.5
    return np.sin(2 * np.pi * np.cumsum(f) / sound.SR) * np.minimum(1, t / 0.02) * np.minimum(1, (seconds - t) / 0.05)


def bloop(factor):
    """A bubbly "bloop" (the ears popping up)."""
    t = sound.t_axis(0.16)
    f = factor * (260 + 700 * np.minimum(t / 0.09, 1))
    return np.sin(2 * np.pi * np.cumsum(f) / sound.SR) * sound.env(len(t), 0.003, 0.045)


def build(voice, gag="boo", label=None, sung=None):
    """One intro. `sung` comes from voices(voice) (made once, used for every gag)."""
    group, puppy_part, kitten_part = sung or voices(voice)
    show = Show(voice, mascot=False)
    show.music = jingle()
    show.music_level, show.duck = 0.09, 1.0
    show.fade = 0.3
    show.voices.append((0.0, group))
    late = gag == "late"
    puppy = Peeker("puppy", "golden", 1, ears_at=0.62, flip=gag == "flip")
    kitten = Peeker("kitten", "tuxedo", 2, ears_at=0.8, up_at=ANSWER[1][0] * BEAT if late else BOO,
                    flip=gag == "flip")
    for ch, part in ((puppy, puppy_part), (kitten, kitten_part)):
        ch.talking.append((0.0, sound.mouth_levels(part, 30)))
        ch.act("wave", ZOO + 0.55, seconds=LENGTH)
        show.add(ch)
    if late:
        puppy.act("head_tilt", puppy.land + 0.05, seconds=0.7)  # "Where is the kitten?"
        kitten.act("surprised", kitten.up_at, seconds=1.0)
    show.add(Logo(*LOGO))
    sprite, corner = hill()
    show.add(Still(sprite, corner, z=4))
    show.sfx(0.02, whistle_drop(), 0.1)
    for land, note in zip(LANDS, (84, 88, 91)):
        show.sfx(land, sound.marimba(note, 0.5), 0.3)
    show.sfx(puppy.ears_at, bloop(1.0), 0.35)
    show.sfx(kitten.ears_at, bloop(1.35), 0.35)
    for ch in (puppy, kitten):
        show.sfx(ch.up_at, sound.sfx_pop(), 0.35)
        show.sfx(ch.land, sound.sfx_thump(), 0.3)
    show.sfx(BOO - 0.35, sound.sfx_whoosh(0.4), 0.1)
    for k, n in enumerate((84, 88, 91, 96)):  # sparkle on "ZOO!"
        show.sfx(ZOO + 0.06 * k, sound.marimba(n, 0.5), 0.14)
    for when, note, gain in ((7 * BEAT, 67, 0.2), (7.25 * BEAT, 72, 0.24)):  # "ta-da" at the end
        show.sfx(when, sound.pluck(note, 1.0), gain)
    show.sfx(7.25 * BEAT, sound.kick(), 0.3)
    show.sfx(7.25 * BEAT, sound.bass(36, 1.0), 0.35)
    show.cheer(ZOO, (LOGO[0], LOGO[1] - 90), n=90)
    if label:
        show.add(Actor(art.badge(label), None, 0.1, LENGTH + 1, 110, 110, scale=0.5, z=9))
    show.snap(BOO + 0.2, f"{gag}: boo")
    show.snap(ZOO + 0.3, f"{gag}: zoo")
    show.t = LENGTH
    return show
