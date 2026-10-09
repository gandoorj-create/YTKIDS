"""Songs: sung lines on a beat, the band that plays with them, and the words on the screen.

A song line is (who, words, notes):
- who: "puppy", "kitten" or "both";
- words: what the screen shows, like "Colors, colors, everywhere!";
- notes: [(beat, syllable, MIDI note, beats)]. A word with more syllables is written with "-": "col-", "ors".
  Every word on the screen has its notes, in the same order.
The singing needs pyworld (see sing.py).
"""
import math

import numpy as np

from . import art, sound
from .anim import ease_out_back, place, progress

SINGERS = {  # how each character sings: voice size, cents out of tune, seconds late, which take
    "puppy": dict(formant=2 ** (3 / 12)),
    "kitten": dict(formant=2 ** (6 / 12), detune=8, take=1),
}
CHORDS = {  # bass note, then the notes of the chord
    "C": (36, (60, 64, 67)), "F": (41, (60, 65, 69)), "G": (43, (59, 62, 67)), "Am": (45, (60, 64, 69)),
    "Dm": (38, (62, 65, 69)), "Em": (40, (59, 64, 67)),
}
HIGHLIGHT = (255, 214, 40)  # a word that is being sung (color words: in their own color)


def singers(who):
    return ["puppy", "kitten"] if who == "both" else [who]


def vocals(voice, lines, beat, length, engine="world", clean=False):
    """The singing of every character: {name: sound}. Lines for "both" are sung by both.

    clean: when both sing, they say the words the same way (one take) at the same moment, so the consonants
    do not come twice (the first test had them a little apart: that made the words blurry)."""
    from . import sing  # needs pyworld
    parts = {}
    for who, _, notes in lines:
        timed = [(b * beat, text, note, n * beat) for b, text, note, n in notes]
        for name in singers(who):
            style = dict(SINGERS[name])
            if clean:
                style["take"] = 0
            late = 0.012 if who == "both" and name == "kitten" and not clean else 0.0
            y = sing.sing(voice, timed, length, late=late, engine=engine, **style)
            parts[name] = parts.get(name, 0) + (0.85 if who == "both" else 1.0) * y
    return parts


def mix_vocals(parts, compress=True):
    """All singing in one track. compress: a fast compressor makes it even (the first test used it)."""
    mix = sum(parts.values())
    if compress:
        level = sound.smooth(np.abs(mix), int(0.01 * sound.SR))
        mix = mix * np.clip((0.3 / (level + 1e-4)) ** 0.4, 0.6, 2.0)
    return 0.9 * mix / np.max(np.abs(mix))


def band(beat, length, chords, melody=()):
    """The music: bass and kick on beats 1 and 3, chords and claps on 2 and 4, a shaker, and bells that
    play the tune an octave higher. chords: [(beat, chord name, beats)]; melody: [(beat, MIDI note, beats)].
    Loudness (RMS) = 1."""
    out = np.zeros(int((length + 2) * sound.SR))

    def add(sig, at, gain):
        sound.add(out, sig, at * beat, gain)

    for start, name, beats in chords:
        root, notes = CHORDS[name]
        for k in range(int(round(beats))):
            b = start + k
            if b % 2 == 0:  # beats 1 and 3 of the bar
                add(sound.bass(root + (7 if b % 4 == 2 else 0), 0.9 * beat), b, 0.5)
                add(sound.kick(), b, 0.45)
            else:
                for j, n in enumerate(notes):
                    add(sound.pluck(n, 0.9 * beat), b + 0.015 * j, 0.1)
                add(sound.clap(), b, 0.16)
            for half in (0, 0.5):
                add(sound.shaker(), b + half, 0.04 + 0.02 * (half > 0))
    for b, note, beats in melody:
        add(sound.marimba(note + 12, 0.25 + beats * beat), b, 0.12)
    out = out[:int(length * sound.SR)]
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-9)


def word_color(word):
    return art.COLORS.get(word.strip(",.!?").lower(), HIGHLIGHT)


class Karaoke:
    """The words of the line being sung, at the top. Each word lights up when it is sung."""
    z = 8

    def __init__(self, lines, beat, y=150, size=88):
        from .sing import words  # (only groups the notes: needs no pyworld)
        self.y, self.rows = y, []
        starts = [notes[0][0] * beat for _, _, notes in lines]
        pad = 12 + round(size * 0.08)  # the empty edge of a text picture (see art.text_sprite)
        for k, (_, text, notes) in enumerate(lines):
            groups, shown = list(words(notes)), text.split()
            assert len(groups) == len(shown), f"{text!r}: {len(shown)} words, but {len(groups)} sung words"
            sprites = [(art.text_sprite(w, size, art.WHITE, inner=None, anchor="ms"),
                        art.text_sprite(w, size, word_color(w), anchor="ms")) for w in shown]
            widths = [plain[0].width - 2 * pad for plain, _ in sprites]
            gap = size * 0.3
            x = 960 - (sum(widths) + gap * (len(widths) - 1)) / 2
            placed = []
            for (plain, lit), width, group in zip(sprites, widths, groups):
                placed.append((plain, lit, x + width / 2, group[0][0] * beat))
                x += width + gap
            end = starts[k + 1] if k + 1 < len(starts) else (notes[-1][0] + notes[-1][3]) * beat + 1.0
            self.rows.append((starts[k] - 0.35, end - 0.1, placed))

    def draw(self, fr, t):
        for start, end, placed in self.rows:
            if not start <= t < end:
                continue
            s = ease_out_back(progress(t, start, 0.3), 2.0) * (1 - progress(t, end - 0.15, 0.15))
            for plain, lit, x, sung in placed:
                on = t >= sung
                bounce = 1 + 0.14 * math.sin(math.pi * progress(t, sung, 0.25)) if on else 1
                spr, anchor = lit if on else plain
                place(fr, spr, 960 + (x - 960) * s, self.y, s * bounce, anchor=anchor)
