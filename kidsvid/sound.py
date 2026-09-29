"""Sound for the videos: the AI voice, the music and the sound effects. Everything is made with code."""
import wave
from functools import lru_cache

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)


def t_axis(seconds):
    return np.arange(int(seconds * SR)) / SR


def hz(note):
    """MIDI note number -> frequency (60 = middle C)."""
    return 440.0 * 2 ** ((note - 69) / 12)


def add(buf, sig, at, gain=1.0):
    """Add `sig` into `buf` starting at `at` seconds."""
    i = int(round(at * SR))
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf) or len(sig) == 0:
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def env(n, attack, decay):
    """Fast rise over `attack` seconds, then fade out (bigger `decay` = longer sound)."""
    e = np.exp(-np.arange(n) / SR / decay)
    a = max(1, int(attack * SR))
    e[:a] *= np.linspace(0, 1, a)
    return e


def smooth(x, k):
    """Moving average over k samples (keeps the same length)."""
    c = np.cumsum(np.concatenate([[0.0], x]))
    y = (c[k:] - c[:-k]) / k
    left = k // 2
    return np.concatenate([np.full(left, y[0]), y, np.full(len(x) - len(y) - left, y[-1])])


# ---------- instruments ----------

@lru_cache(maxsize=None)
def marimba(note, seconds=0.9):
    t = t_axis(seconds)
    f = hz(note)
    x = (np.sin(2 * np.pi * f * t)
         + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.04)
         + 0.1 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t / 0.012))
    return x * env(len(t), 0.002, 0.3)


@lru_cache(maxsize=None)
def pluck(note, seconds=1.1):
    """Soft ukulele-like string."""
    t = t_axis(seconds)
    f = hz(note)
    x = sum(k ** -1.3 * np.sin(2 * np.pi * k * f * t) * np.exp(-t * (2.5 + 2.0 * k)) for k in range(1, 7))
    return x * env(len(t), 0.003, 100)


@lru_cache(maxsize=None)
def bass(note, seconds=0.6):
    t = t_axis(seconds)
    f = hz(note)
    x = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)
    return x * env(len(t), 0.005, 0.2)


@lru_cache(maxsize=None)
def kick():
    t = t_axis(0.3)
    f = 48 + 100 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.1)


def shaker():
    n = int(0.09 * SR)
    return np.diff(RNG.uniform(-1, 1, n + 1)) * env(n, 0.004, 0.02)


def clap():
    n = int(0.25 * SR)
    x = np.convolve(np.diff(RNG.uniform(-1, 1, n + 1)), np.ones(4) / 4, mode="same")
    return x * env(n, 0.002, 0.07)


# ---------- music: a happy loop in C major (original, made here) ----------

BPM = 112
BEAT = 60 / BPM
CHORDS = {  # bass note, then the notes of the strummed chord
    "C": (48, (60, 64, 67, 72)),
    "G": (43, (59, 62, 67, 71)),
    "Am": (45, (60, 64, 69, 72)),
    "F": (41, (60, 65, 69, 72)),
}
BARS = ["C", "G", "Am", "F", "C", "F", "G", "C",   # part A
        "F", "G", "C", "Am", "F", "G", "C", "C"]   # part B
MELODY = [  # (note, length in 1/8 notes) for each bar
    [(76, 1), (79, 1), (76, 1), (72, 1), (74, 2), (76, 2)],
    [(74, 1), (71, 1), (67, 2), (74, 1), (76, 1), (74, 2)],
    [(72, 1), (76, 1), (81, 2), (79, 1), (76, 1), (72, 2)],
    [(69, 1), (72, 1), (77, 2), (76, 1), (74, 1), (72, 2)],
    [(76, 1), (79, 1), (84, 2), (79, 1), (76, 1), (79, 2)],
    [(77, 1), (76, 1), (74, 1), (72, 1), (69, 2), (72, 2)],
    [(71, 1), (74, 1), (79, 2), (77, 1), (74, 1), (71, 2)],
    [(72, 2), (76, 1), (79, 1), (84, 4)],
    [(72, 2), (69, 1), (72, 1), (77, 2), (76, 2)],
    [(74, 2), (71, 1), (74, 1), (79, 4)],
    [(76, 1), (74, 1), (72, 1), (74, 1), (76, 2), (79, 2)],
    [(81, 2), (79, 1), (76, 1), (72, 4)],
    [(77, 1), (76, 1), (77, 1), (81, 1), (79, 2), (77, 2)],
    [(74, 1), (76, 1), (79, 2), (83, 2), (79, 2)],
    [(84, 2), (79, 1), (76, 1), (79, 2), (76, 2)],
    [(72, 4), (67, 2), (72, 2)],
]
STRUM = [0, 2, 3, 5, 6]  # where the chord is strummed, in 1/8 notes


def music(duration, melody_level=lambda t: 1.0):
    """Background music, `duration` seconds long, with loudness (RMS) = 1."""
    out = np.zeros(int((duration + 2) * SR))
    bar = 4 * BEAT
    for b in range(int(duration / bar) + 1):
        t0 = b * bar
        root, notes = CHORDS[BARS[b % len(BARS)]]
        add(out, bass(root), t0, 0.5)
        add(out, bass(root + 7), t0 + 2 * BEAT, 0.4)
        for i, pos in enumerate(STRUM):
            for j, note in enumerate(notes):
                add(out, pluck(note), t0 + pos * BEAT / 2 + j * 0.011, 0.07 if i == 0 else 0.05)
        t = t0
        for note, length in MELODY[b % len(MELODY)]:
            add(out, marimba(note), t, 0.22 * melody_level(t))
            t += length * BEAT / 2
        add(out, kick(), t0, 0.5)
        add(out, kick(), t0 + 2 * BEAT, 0.45)
        add(out, clap(), t0 + BEAT, 0.12)
        add(out, clap(), t0 + 3 * BEAT, 0.12)
        for k in range(8):
            add(out, shaker(), t0 + k * BEAT / 2, 0.07 if k % 2 else 0.04)
    out = out[: int(duration * SR)]
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-9)


# ---------- sound effects ----------

def sfx_pop():
    t = t_axis(0.14)
    f = 300 + 900 * np.minimum(t / 0.08, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.035)


def sfx_boop(note):
    t = t_axis(0.4)
    f = hz(note)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(len(t), 0.003, 0.1)


def sfx_plink(note):
    return marimba(note, 0.6)


def sfx_chime():
    """Happy bell + quick sparkle, for the right answer."""
    t = t_axis(1.6)
    out = np.zeros(len(t))
    for ratio, amp, decay in ((1, 1, 0.9), (2.0, 0.45, 0.6), (3.01, 0.25, 0.4), (4.2, 0.15, 0.25), (5.4, 0.1, 0.18)):
        out += amp * np.sin(2 * np.pi * hz(84) * ratio * t) * np.exp(-t / decay)
    out *= env(len(t), 0.002, 100)
    for k, note in enumerate((84, 88, 91, 96)):
        add(out, marimba(note, 0.5), 0.05 + k * 0.06, 0.5)
    return out * 0.5


def sfx_whoosh(seconds=0.45):
    n = int(seconds * SR)
    x = RNG.uniform(-1, 1, n)
    p = np.arange(n) / n
    a = 1 - np.exp(-2 * np.pi * (300 + 4500 * np.sin(np.pi * p) ** 2) / SR)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):  # low-pass filter that opens and closes
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y * np.sin(np.pi * p) ** 1.5 * 2.2


def sfx_boing():
    t = t_axis(0.55)
    f = (200 + 250 * (1 - np.exp(-t / 0.1))) * (1 + 0.07 * np.sin(2 * np.pi * 16 * t) * np.exp(-t / 0.35))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.004, 0.2)


# ---------- voice ----------

def resample(x, n_out):
    """Change the number of samples (clean, FFT based). Used to go up to 48 kHz."""
    spec = np.fft.rfft(x)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    k = min(len(spec), len(out))
    out[:k] = spec[:k]
    return np.fft.irfft(out, n_out) * (n_out / len(x))


def trim(x, pad=0.04, thresh=0.02):
    """Cut silence at the start and end."""
    loud = np.flatnonzero(np.abs(x) > thresh * np.max(np.abs(x)))
    if len(loud) == 0:
        return x
    a, b = max(0, loud[0] - int(pad * SR)), min(len(x), loud[-1] + int(pad * SR))
    y = x[a:b].copy()
    f = int(0.005 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


class Voice:
    """Offline AI voice (Piper)."""

    def __init__(self, model, config):
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(model), config_path=str(config))

    def say(self, text, slow=1.18, pitch=2.0):
        """`slow` > 1 talks slower. `pitch` (semitones) makes the voice higher, more like a cartoon."""
        from piper import SynthesisConfig
        chunks = list(self.voice.synthesize(text, syn_config=SynthesisConfig(length_scale=slow)))
        sr = chunks[0].sample_rate
        x = np.pad(np.concatenate([c.audio_float_array for c in chunks]).astype(np.float64), int(0.05 * sr))
        y = trim(resample(x, round(len(x) * SR / (sr * 2 ** (pitch / 12)))))
        return 0.92 * y / (np.max(np.abs(y)) + 1e-9)


def mouth_levels(clip, fps):
    """How open the mouth is (0..5) for each video frame of a voice clip."""
    hop = SR // fps
    n = -(-len(clip) // hop)
    rms = np.sqrt((np.pad(clip, (0, n * hop - len(clip))).reshape(n, hop) ** 2).mean(axis=1))
    loud = rms[rms > 0.02]
    v = rms / (np.percentile(loud, 80) if len(loud) else 1.0)
    return np.where(v < 0.18, 0, np.clip(np.round(1 + v * 4), 1, 5)).astype(int)


# ---------- mixing ----------

def mix(duration, voices, effects, music_track, music_level=0.075, duck=0.35):
    """voices: [(time, clip)], effects: [(time, sound, gain)]. Music gets quieter while someone talks."""
    n = int(duration * SR)
    voice, fx, gate = np.zeros(n), np.zeros(n), np.zeros(n)
    for at, clip in voices:
        add(voice, clip, at)
        a, b = int((at - 0.1) * SR), int((at + len(clip) / SR + 0.15) * SR)
        gate[max(0, a):max(0, b)] = 1
    for at, sig, gain in effects:
        add(fx, sig, at, gain)
    m = music_track[:n] * music_level * (1 - (1 - duck) * smooth(gate, int(0.2 * SR)))
    fade_in, fade_out = int(0.4 * SR), int(1.5 * SR)
    m[:fade_in] *= np.linspace(0, 1, fade_in)
    m[-fade_out:] *= np.linspace(1, 0, fade_out)
    out = voice + m + fx
    peak = np.max(np.abs(out))
    return out * (0.97 / peak) if peak > 0.97 else out


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
