"""Singing with the AI voice.

The voice says a word. WORLD (a voice analyser, `pip install pyworld`) takes it apart into pitch,
voice color and breath. A word with more syllables is cut at the quiet places between its vowels
("col-ors": at the "l"). Then each syllable goes on its musical note: the vowel gets as long as the
note, and the sound is built again. `formant` > 1 makes the voice "smaller" (like a child or a cartoon
animal).
"""
from functools import lru_cache

import numpy as np
import pyworld as pw

from . import sound

FRAME = 5.0                     # milliseconds per WORLD frame
MAX_HEAD, MAX_TAIL = 0.09, 0.07  # seconds: long consonants (like "zzz" in "zoo") are made shorter


def warp(sp, factor):
    """Move the voice color (formants) up by `factor`, like a smaller throat."""
    bins = np.arange(sp.shape[1], dtype=float)
    return np.array([np.interp(bins / factor, bins, row) for row in sp])


def stretch_map(voiced, n_out):
    """For every output frame, which input frame to use.

    The consonants before and after the vowel stay short, and the vowel gets as long as the note.
    """
    n_in = len(voiced)
    idx = np.flatnonzero(voiced)
    if len(idx) < 12:
        return np.linspace(0, n_in - 1, n_out)
    a, b = idx[0] + 4, idx[-1] - 4  # the attack and the release of the vowel go with the consonants
    head = min(a, int(MAX_HEAD * 1000 / FRAME))
    tail = min(n_in - b, int(MAX_TAIL * 1000 / FRAME))
    middle = n_out - head - tail
    if middle < 2:
        return np.linspace(0, n_in - 1, n_out)
    return np.concatenate([np.linspace(0, a - 1, head), np.linspace(a, b - 1, middle), np.linspace(b, n_in - 1, tail)])


def take(rows, pos):
    """Rows at fractional positions (mixing the two nearest rows)."""
    i = np.floor(pos).astype(int)
    j = np.minimum(i + 1, len(rows) - 1)
    w = (pos - i)[:, None]
    return rows[i] * (1 - w) + rows[j] * w


@lru_cache(maxsize=None)
def analyse(voice, text, take=0):
    """WORLD parts of the voice saying `text`: (pitch, voice color, breath), one row every FRAME ms.
    The voice says a word a little differently every time: each `take` is one way of saying it."""
    x = voice.say(text, slow=1.0, pitch=0)
    f0, times = pw.harvest(x, sound.SR, frame_period=FRAME)
    return f0, pw.cheaptrick(x, f0, times, sound.SR), pw.d4c(x, f0, times, sound.SR)


def split(f0, sp, n):
    """Where to cut a word into n syllables: frame numbers [0, cut, ..., end]. Each syllable has one vowel
    (a loud voiced part); the cut is at the quietest moment between two vowels."""
    loud = np.convolve(np.log(sp.sum(axis=1) + 1e-12), np.ones(5) / 5, mode="same")
    level = np.where(f0 > 0, loud, -np.inf)
    peaks = []
    for _ in range(n):
        if not np.isfinite(level.max()):
            return list(np.linspace(0, len(f0), n + 1).astype(int))  # (should not happen) equal parts
        k = int(np.argmax(level))
        peaks.append(k)
        level[max(0, k - 12):k + 12] = -np.inf  # not again within 60 ms
    peaks.sort()
    return [0] + [a + int(np.argmin(loud[a:b])) for a, b in zip(peaks, peaks[1:])] + [len(f0)]


def sung(f0, sp, ap, note, seconds, formant=1.0, detune=0.0, vibrato=0.0):
    """One syllable (WORLD parts) on MIDI `note` for `seconds`. Returns (sound, when the vowel starts).

    detune: cents (1/100 of a semitone), so a choir does not sound like one voice.
    vibrato: semitones of wobble, it starts after 0.25 s (like real singers).
    """
    n_out = max(4, int(seconds * 1000 / FRAME))
    pos = stretch_map(f0 > 0, n_out)
    voiced = f0[np.round(pos).astype(int)] > 0
    sp, ap = take(sp, pos), take(ap, pos)
    ap[voiced] **= 1.6  # less breath noise in the vowels: a cleaner, cartoon singing voice
    if formant != 1.0:
        sp = warp(sp, formant)
    first = np.argmax(voiced) if voiced.any() else 0
    t = np.maximum(0, np.arange(n_out) - first) * FRAME / 1000  # seconds since the vowel started
    pitch = note + detune / 100 - 0.5 * np.exp(-t / 0.025)      # a tiny scoop up into the note
    pitch = pitch + vibrato * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.25) / 0.2, 0, 1)
    f0_out = np.where(voiced, sound.hz(pitch), 0.0)
    y = pw.synthesize(f0_out, np.ascontiguousarray(sp), np.ascontiguousarray(ap), sound.SR, FRAME)
    f = int(0.012 * sound.SR)
    y[-f:] *= np.linspace(1, 0, f)
    return 0.9 * y / (np.max(np.abs(y)) + 1e-9), first * FRAME / 1000


def syllable(voice, text, note, seconds, formant=1.0, detune=0.0, vibrato=0.0):
    """One sung syllable: `text` on MIDI `note` for `seconds`. Returns (sound, when the vowel starts)."""
    return sung(*analyse(voice, text), note, seconds, formant, detune, vibrato)


def words(notes):
    """Notes grouped into words: a syllable that ends with "-" goes on in the next note."""
    group = []
    for note in notes:
        group.append(note)
        if not note[1].endswith("-"):
            yield group
            group = []
    if group:
        yield group


def sing(voice, notes, length, formant=1.0, detune=0.0, vibrato=0.3, late=0.0, take=0):
    """A sung line. notes: [(time, syllable, MIDI note, seconds), ...]. Returns a sound `length` seconds long.

    A word with more syllables is written with "-": "col-", "ors" is "colors", said once and cut in two.
    late: seconds this singer comes in after the others (for a choir).
    take: which way of saying the words (give every singer their own, so a choir is not one voice).
    """
    out = np.zeros(int(length * sound.SR))
    for word in words(notes):
        f0, sp, ap = analyse(voice, "".join(text.rstrip("-") for _, text, _, _ in word), take)
        cuts = split(f0, sp, len(word)) if len(word) > 1 else [0, len(f0)]
        for (at, _, note, seconds), a, b in zip(word, cuts, cuts[1:]):
            wobble = vibrato if seconds >= 0.45 else 0.0
            y, vowel = sung(f0[a:b], sp[a:b], ap[a:b], note, seconds, formant, detune, wobble)
            sound.add(out, y, at + late - vowel)  # singers put the vowel on the beat, the consonant before it
    return out
