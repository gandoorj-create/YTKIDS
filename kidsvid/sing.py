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
def said(voice, text, take=0):
    """The voice saying `text`. It says a word a little differently every time: each `take` is one way."""
    return voice.say(text, slow=1.0, pitch=0)


@lru_cache(maxsize=None)
def analyse(voice, text, take=0):
    """WORLD parts of the voice saying `text`: (pitch, voice color, breath), one row every FRAME ms."""
    x = said(voice, text, take)
    f0, times = pw.harvest(x, sound.SR, frame_period=FRAME)
    return f0, pw.cheaptrick(x, f0, times, sound.SR), pw.d4c(x, f0, times, sound.SR)


def split(f0, loud, n):
    """Where to cut a word into n syllables: frame numbers [0, cut, ..., end]. Each syllable has one vowel
    (a loud voiced part); the cut is at the quietest moment between two vowels. loud: log loudness per frame."""
    loud = np.convolve(loud, np.ones(5) / 5, mode="same")
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


def psola(x, cuts, notes, detune=0.0, vibrato=0.3):
    """A sung word, made with Praat's PSOLA (overlap-add): it keeps the voice's own sound waves and only moves
    them closer or further apart, so the consonants stay clear. `pip install praat-parselmouth`.

    x: the word (a sound); cuts: where its syllables start and end (frame numbers, see split);
    notes: [(seconds until the next syllable's beat, MIDI note)] for each syllable (for the last one: how long
    its note is). Every vowel lands on its beat and lasts until the next one; the consonants before a vowel
    come just before its beat. Returns (sound, when the first vowel starts)."""
    import parselmouth
    from parselmouth.praat import call
    sec = FRAME / 1000
    f0, _ = pw.harvest(x, sound.SR, frame_period=FRAME)
    dur = len(x) / sound.SR
    regions = []  # (start, vowel start, vowel end, end) of each syllable, in seconds of the spoken word
    for a, b in zip(cuts, cuts[1:]):
        idx = a + np.flatnonzero(f0[a:b] > 0)
        if len(idx) >= 12:
            regions.append((a * sec, (idx[0] + 4) * sec, (idx[-1] - 4) * sec, min(b * sec, dur)))
        else:  # (hardly any voice) the middle of it is the "vowel"
            regions.append((a * sec, (0.7 * a + 0.3 * b) * sec, (0.3 * a + 0.7 * b) * sec, min(b * sec, dur)))
    heads = [min(v0 - s0, MAX_HEAD) for s0, v0, _, _ in regions]
    tails = [min(e - v1, MAX_TAIL) for _, _, v1, e in regions]
    vowels = [max(0.05, gap - tails[k] - (heads[k + 1] if k + 1 < len(regions) else 0))
              for k, (gap, _) in enumerate(notes)]

    # Praat makes a sound at most 3 times as long as the one it gets, so add silence at the end first
    # (it is cut off again below).
    sung_length = sum(heads) + sum(vowels) + sum(tails) + (dur - regions[-1][3])
    x = np.concatenate([x, np.zeros(int(max(0.0, sung_length / 3 - dur + 0.1) * sound.SR))])
    snd = parselmouth.Sound(x, sound.SR)
    manip = call(snd, "To Manipulation", 0.01, 75, 900)
    pitch = call(snd, "To Pitch (ac)", 0.005, 75, 15, "no", 0.03, 0.25, 0.01, 0.35, 0.14, 900)
    call([manip, call([snd, pitch], "To PointProcess (cc)")], "Replace pulses")  # find the weak voiced parts too
    lengths = call("Create DurationTier", "lengths", 0, len(x) / sound.SR)
    call(lengths, "Add point", regions[-1][3] + 1e-4, 1.0)  # the end and the added silence: as they are
    tier = call("Create PitchTier", "pitch", 0, len(x) / sound.SR)
    for (s0, v0, v1, e), head, vowel, tail, (_, note) in zip(regions, heads, vowels, tails, notes):
        for t0, t1, k in ((s0, v0, head / max(v0 - s0, 1e-3)), (v0, v1, vowel / max(v1 - v0, 1e-3)),
                          (v1, e, tail / max(e - v1, 1e-3))):
            call(lengths, "Add point", t0 + 1e-4, k)
            call(lengths, "Add point", max(t0 + 2e-4, t1 - 1e-4), k)
        k = vowel / max(v1 - v0, 1e-3)
        long = vowel >= 0.45
        for u in np.arange(0, vowel, 0.005):  # u: seconds since the vowel started, in the sung word
            p = note + detune / 100 - 0.5 * np.exp(-u / 0.025)  # a tiny scoop up into the note
            if long:
                p += vibrato * np.sin(2 * np.pi * 5.5 * u) * np.clip((u - 0.25) / 0.2, 0, 1)
            call(tier, "Add point", v0 + u / k, float(sound.hz(p)))
        call(tier, "Add point", s0 + 1e-3, float(sound.hz(note - 0.5)))  # the consonants: on the note too
        call(tier, "Add point", e - 1e-3, float(sound.hz(note)))
    call([manip, tier], "Replace pitch tier")
    call([manip, lengths], "Replace duration tier")
    y = call(manip, "Get resynthesis (overlap-add)").values[0].astype(np.float64)[:int(sung_length * sound.SR)]
    f = int(0.012 * sound.SR)
    y[-f:] *= np.linspace(1, 0, f)
    return 0.9 * y / (np.max(np.abs(y)) + 1e-9), heads[0]


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


def sing(voice, notes, length, formant=1.0, detune=0.0, vibrato=0.3, late=0.0, take=0, engine="world"):
    """A sung line. notes: [(time, syllable, MIDI note, seconds), ...]. Returns a sound `length` seconds long.

    A word with more syllables is written with "-": "col-", "ors" is "colors", said once and cut in two.
    late: seconds this singer comes in after the others (for a choir).
    take: which way of saying the words (give every singer their own, so a choir is not one voice).
    engine: "world" (WORLD builds the voice again) or "psola" (Praat keeps the voice's own sound waves; for a
    smaller voice the word is played faster first, which makes the voice color and the pitch higher).
    """
    out = np.zeros(int(length * sound.SR))
    for word in words(notes):
        text = "".join(syl.rstrip("-") for _, syl, _, _ in word)
        if engine == "psola":
            x = said(voice, text, take)
            if formant != 1.0:
                x = sound.resample(x, round(len(x) / formant))
            f0, _ = pw.harvest(x, sound.SR, frame_period=FRAME)
            hop = int(sound.SR * FRAME / 1000)
            loud = np.log(np.array([np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12 for i in range(len(f0))]))
            cuts = split(f0, loud, len(word)) if len(word) > 1 else [0, len(f0)]
            gaps = [nxt[0] - at for (at, *_), nxt in zip(word, word[1:])] + [word[-1][3]]
            y, vowel = psola(x, cuts, [(gap, note) for gap, (_, _, note, _) in zip(gaps, word)], detune, vibrato)
            sound.add(out, y, word[0][0] + late - vowel)
            continue
        else:
            f0, sp, ap = analyse(voice, text, take)
            loud = np.log(sp.sum(axis=1) + 1e-12)
            cuts = split(f0, loud, len(word)) if len(word) > 1 else [0, len(f0)]
            pieces = [sung(f0[a:b], sp[a:b], ap[a:b], note, seconds, formant, detune,
                           vibrato if seconds >= 0.45 else 0.0)
                      for (_, _, note, seconds), a, b in zip(word, cuts, cuts[1:])]
        for (at, *_), (y, vowel) in zip(word, pieces):
            sound.add(out, y, at + late - vowel)  # singers put the vowel on the beat, the consonant before it
    return out
