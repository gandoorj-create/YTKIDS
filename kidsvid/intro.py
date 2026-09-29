"""The Yumizoo channel intro (jingle).

Wobbaloo the jelly falls in and "sings" the name: the tune plays "Yu-mi-zoo" three times, the logo
letters land on the notes, and at the end everybody shouts "Yumizoo!".
"""
import math

import numpy as np

from . import art, sound
from .anim import place
from .show import FPS, Actor, Show

BPM = 124
BEAT = 60 / BPM
START = 0.5                  # the music starts when Wobbaloo has landed
SHOUT_BEAT = 6.5             # "Yumizoo!"
LENGTH = START + 8 * BEAT + 1.4
PINK = (255, 110, 170)       # Wobbaloo's own color
NAME = "Yumizoo"
SYLLABLES = [(0, 2), (2, 4), (4, 7)]  # letters of "Yu", "mi", "zoo"

CHORDS = {"C": (48, (60, 64, 67, 72)), "F": (41, (60, 65, 69, 72)), "G": (43, (59, 62, 67, 71)),
          "Dm": (38, (62, 65, 69, 74))}

# Three tunes for "Yu-mi-zoo". A note: (beat, MIDI note, length in beats[, slide to note]).
# Every phrase is 3 notes: "Yu", "mi", "zoo". The last "zoo" is the high, long one.
TUNES = {
    "chant": dict(sound="marimba", chords=[(0, "C"), (2, "F"), (4, "G"), (5, "C")], notes=[
        (0, 79, .5), (.5, 76, .5), (1, 79, 1),
        (2, 81, .5), (2.5, 79, .5), (3, 76, 1),
        (4, 79, .5), (4.5, 81, .5), (5, 84, 1.5)]),
    "rising": dict(sound="pop", chords=[(0, "C"), (2, "Dm"), (4, "C")], notes=[
        (0, 72, .5), (.5, 76, .5), (1, 79, 1),
        (2, 74, .5), (2.5, 77, .5), (3, 81, 1),
        (4, 76, .5), (4.5, 79, .5), (5, 84, 1.5)]),
    "wobbly": dict(sound="whistle", chords=[(0, "C"), (2, "F"), (4, "G"), (5, "C")], notes=[
        (0, 72, .5), (.5, 72, .5), (1, 76, 1, 79),
        (2, 81, .5), (2.5, 81, .5), (3, 79, 1, 76),
        (4, 74, .5), (4.5, 76, .5), (5, 72, 1.5, 84)]),
}


def at(beat):
    return START + beat * BEAT


def mixed(*parts):
    """Add sounds of different lengths: mixed((sound, gain), ...)."""
    out = np.zeros(max(len(s) for s, _ in parts))
    for s, gain in parts:
        out[:len(s)] += gain * s
    return out


# ---------- melody instruments ----------

def pop_tone(note, seconds):
    """Bright, bubbly synth with a little "blip" at the start."""
    t = sound.t_axis(seconds + 0.25)
    f = sound.hz(note) * (1 + 0.6 * np.exp(-t / 0.012))
    ph = 2 * np.pi * np.cumsum(f) / sound.SR
    x = sum(np.sin(k * ph) / k for k in (1, 3, 5, 7))
    return 0.8 * x * sound.env(len(t), 0.004, 0.12 + 0.35 * seconds)


def whistle(note, seconds, slide_to=None):
    """Slide whistle: can glide from one note to another, and wobbles more and more (like jelly)."""
    t = sound.t_axis(seconds)
    target = note if slide_to is None else slide_to
    p = np.clip(t / (0.6 * seconds), 0, 1)
    pitch = note + (target - note) * p * p * (3 - 2 * p)
    pitch += (0.08 + 0.35 * t / seconds) * np.sin(2 * np.pi * 6.5 * t)
    ph = 2 * np.pi * np.cumsum(sound.hz(pitch)) / sound.SR
    x = np.sin(ph) + 0.12 * np.sin(2 * ph)
    e = np.minimum(1, t / 0.025) * np.minimum(1, (seconds - t) / 0.06)
    return 0.8 * x * e


def lead(kind, note, beats, slide_to=None):
    seconds = beats * BEAT
    if kind == "marimba":  # marimba + a quiet bell one octave higher
        return mixed((sound.marimba(note, max(0.9, seconds + 0.4)), 1.0), (sound.marimba(note + 12, 0.6), 0.3))
    if kind == "pop":
        return pop_tone(note, seconds)
    return whistle(note, seconds * 0.95, slide_to)


def crash(seconds=1.6):
    n = int(seconds * sound.SR)
    return np.diff(sound.RNG.uniform(-1, 1, n + 1)) * sound.env(n, 0.002, 0.45)


def fall_whistle(seconds=0.45):
    """Cartoon "falling" sound: a whistle going down."""
    t = sound.t_axis(seconds)
    f = 1300 * (300 / 1300) ** (t / seconds)
    return np.sin(2 * np.pi * np.cumsum(f) / sound.SR) * np.minimum(1, (seconds - t) / 0.05) * 0.7


def jingle_music(tune):
    """Backing (bass, ukulele, drums) + the tune. Loudness (RMS) = 1."""
    spec = TUNES[tune]
    out = np.zeros(int((LENGTH + 1) * sound.SR))

    def chord(b):
        return CHORDS[[name for start, name in spec["chords"] if start <= b][-1]]

    for k in range(12):  # 1/8 notes, beats 0 .. 5.5
        b = k / 2
        root, notes = chord(b)
        if k % 2 == 0:
            sound.add(out, sound.bass(root if k % 4 == 0 else root + 7), at(b), 0.45)
            sound.add(out, sound.kick() if k % 4 == 0 else sound.clap(), at(b), 0.45 if k % 4 == 0 else 0.14)
        for j, n in enumerate(notes):
            sound.add(out, sound.pluck(n), at(b) + 0.01 * j, 0.06 if k % 2 == 0 else 0.04)
        sound.add(out, sound.shaker(), at(b), 0.05)
    root, notes = CHORDS["C"]  # big last chord, then quiet for the shout
    sound.add(out, sound.bass(root), at(6), 0.55)
    sound.add(out, sound.kick(), at(6), 0.55)
    sound.add(out, crash(), at(6), 0.12)
    for j, n in enumerate(notes + (76, 79)):
        sound.add(out, sound.pluck(n), at(6) + 0.015 * j, 0.08)
    for note in spec["notes"]:
        beat, n, beats = note[:3]
        sound.add(out, lead(spec["sound"], n, beats, *note[3:]), at(beat), 0.32)
    for k, n in enumerate((84, 88, 91)):  # little sparkle at the very end
        sound.add(out, sound.marimba(n, 0.6), at(8) + 0.07 * k, 0.12)
    out = out[:int(LENGTH * sound.SR)]
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-9)


KIDS = [(5, 1.0, 0.0), (6.5, 0.6, 0.014), (3.5, 0.55, 0.026), (8, 0.45, 0.038), (4.5, 0.5, 0.05)]  # (semitones higher, loudness, delay s)


def kid_voice(voice, text, pitch, speed=0.95):
    """A child-like voice: the AI voice made higher (this also makes it sound like a small child),
    a little faster, brighter and "shouty"."""
    x = voice.say(text, slow=speed * 2 ** (pitch / 12), pitch=pitch)
    level = sound.smooth(np.abs(x), int(0.01 * sound.SR))
    x = x * np.clip((0.35 / (level + 1e-4)) ** 0.5, 0.5, 4.0)  # compressor: quiet parts louder
    x = x + 0.5 * (x - sound.smooth(x, 8))  # brighter
    x = np.tanh(3.0 * x) / np.tanh(3.0)       # louder, like shouting
    return x / np.max(np.abs(x))


def group_shout(voice, text=f"{NAME}!"):
    """A lead child and four friends shout together (a little after each other, with different voices).

    Returns (group sound, lead voice only) - the lead voice moves Wobbaloo's mouth.
    """
    parts, lead = [], None
    for pitch, gain, delay in KIDS:
        x = kid_voice(voice, text, pitch)
        lead = x if lead is None else lead
        parts.append((np.pad(x, (int(delay * sound.SR), 0)), gain))
    out = mixed(*parts)
    return 0.92 * out / np.max(np.abs(out)), lead


# ---------- moving pictures ----------

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


class Wobbaloo:
    """The jelly: falls in, wobbles, hops on every "zoo", opens its mouth on every note."""
    z = 3

    def __init__(self, x, y, scale, land, notes, shout_at, shout_levels, color=PINK):
        self.x, self.y, self.scale, self.land = x, y, scale, land
        self.sprites = {(e, m): art.jelly(color, e, m) for e in ("open", "blink", "happy") for m in range(6)}
        self.sing = [(at(n[0]), n[2] * BEAT) for n in notes]
        zoo = [(at(n[0]), n[2]) for k, n in enumerate(notes) if k % 3 == 2]  # every third note is "zoo"
        self.hops = [(t, 120 if beats > 1 else 60, 0.5 if beats > 1 else 0.36) for t, beats in zoo]
        self.impacts = [(land, 0.22)] + [(t + d, 0.12) for t, _, d in self.hops]
        self.shout_at, self.shout_levels = shout_at, shout_levels

    def mouth(self, t):
        k = int((t - self.shout_at) * FPS)
        if 0 <= k < len(self.shout_levels):
            return int(self.shout_levels[k])
        for start, length in self.sing:
            if start <= t < start + 0.9 * length:
                p = (t - start) / length
                return 5 if p < 0.35 else 4 if p < 0.65 else 2
        return 0

    def draw(self, fr, t):
        if t < self.land - 0.45:
            return
        y = self.y
        if t < self.land:  # falling, a little stretched
            p = (t - (self.land - 0.45)) / 0.45
            y = -350 + (self.y + 350) * p * p
            sx, sy = 0.9, 1.12
        else:
            sx, sy = wobble(t, self.impacts)
            for start, height, length in self.hops:
                if 0 <= t - start < length:
                    y -= height * math.sin(math.pi * (t - start) / length)
            jiggle = 0.012 * math.sin(2 * math.pi * 1.7 * t)
            sx, sy = sx * (1 - jiggle), sy * (1 + jiggle)
        eyes = "happy" if t >= self.shout_at else "blink" if 2.2 <= t < 2.33 else "open"
        place(fr, self.sprites[(eyes, self.mouth(t))], self.x, y, self.scale * sx, self.scale * sy,
              anchor=art.JELLY_BOTTOM)


class Logo:
    """ "Yumizoo" letters: each syllable falls and lands on its note, then bounces on the next ones."""
    z = 4

    def __init__(self, notes, x, y, size, jump_at):
        self.letters = art.title_letters(NAME, size)
        self.x, self.y, self.jump_at = x, y, jump_at
        times = [at(n[0]) for n in notes]
        self.lands = times[:3]                                   # first "Yu", "mi", "zoo"
        self.bounces = [(t, k % 3) for k, t in enumerate(times) if k >= 3]

    def draw(self, fr, t):
        for g, (a, b) in enumerate(SYLLABLES):
            land = self.lands[g]
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
                    sx, sy = wobble(t, [(land, 0.25)])
                    for when, group in self.bounces:
                        if group == g and 0 <= t - when < 0.3:
                            y -= 40 * math.sin(math.pi * (t - when) / 0.3)
                    tj = self.jump_at + 0.04 * i
                    if 0 <= t - tj < 0.45:
                        y -= 70 * math.sin(math.pi * (t - tj) / 0.45)
                place(fr, spr, self.x + dx, y, sx, sy, anchor=anchor)


def build(voice, tune, shout, label=None):
    """One intro with one tune. `shout` comes from group_shout() (made once, used for every tune)."""
    group, main = shout
    notes = TUNES[tune]["notes"]
    show = Show(voice, mascot=False)
    show.music = jingle_music(tune)
    show.music_level, show.duck = 0.1, 0.2  # music below the voice, and very quiet for the shout
    shout_at = at(SHOUT_BEAT)
    show.voices.append((shout_at, group))
    show.sfx(0.0, fall_whistle(), 0.3)
    show.sfx(START - 0.05, sound.sfx_boing(), 0.4)
    show.add(Wobbaloo(960, 1010, 1.0, START - 0.05, notes, shout_at, sound.mouth_levels(main, FPS)))
    show.add(Logo(notes, 960, 330, 210, shout_at))
    zoo_end = at(notes[-1][0])
    for (thing, bottom), x, beat in (((art.cupcake(), (250, 470)), 470, notes[3][0]),
                                     ((art.marshmallow(), (240, 446)), 1450, notes[5][0])):
        show.add(Actor(thing, bottom, at(beat), LENGTH + 1, x, 1000, scale=0.72, jumps=[zoo_end, shout_at]))
        show.sfx(at(beat), sound.sfx_pop(), 0.35)
    for k, n in enumerate((84, 88, 91)):  # short sparkle (a long bell would ring under the shout)
        show.sfx(zoo_end + 0.06 * k, sound.marimba(n, 0.5), 0.2)
    show.cheer(shout_at, (960, 330), n=110)
    if label:
        show.add(Actor(art.badge(label), None, 0.1, LENGTH + 1, 110, 110, scale=0.55, z=9))
    show.snap(at(8) + 0.3, tune)
    show.t = LENGTH
    return show
