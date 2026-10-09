#!/usr/bin/env python3
"""The Colors Song: Maple and Domi sing about colors (our own song: our words, our tune).

    python3 make_song.py              # output/colors_song_test.mp4: the first part (about 28 seconds), a test
    python3 make_song.py --preview    # only still pictures (fast)

The singing needs pyworld (pip install pyworld), so the song cannot be made on Windows.

The song: the chorus has an easy "sol-mi" tune (the one children sing everywhere in their games), and in
the verses Domi sings back what Maple sings, so kids at home can sing back too. The color word comes
again and again, and its colors pop up on the screen when it is sung.
"""
import argparse

from kidsvid import rig, song, sound
from kidsvid.episode import OUT, VOICE
from kidsvid.lessons import plinks
from kidsvid.show import FPS, Actor, Letters, Show, contact_sheet

BPM = 100
BEAT = 60 / BPM
TITLE = "The Colors Song!"
INTRO_TUNE = [(0, 67, 1), (1, 64, 1), (2, 67, 1), (3, 64, 1), (4, 69, 1), (5, 67, 1), (6, 64, 2)]  # bells
LINES = [  # (who, words on the screen, notes: (beat, syllable, MIDI note, beats))
    ("both", "Colors, colors, everywhere!",
     [(8, "col-", 67, 1), (9, "ors", 64, 1), (10, "col-", 67, 1), (11, "ors", 64, 1),
      (12, "ev-", 69, 1), (13, "ery-", 67, 1), (14, "where", 64, 2)]),
    ("both", "Colors, colors, here and there!",
     [(16, "col-", 67, 1), (17, "ors", 64, 1), (18, "col-", 67, 1), (19, "ors", 64, 1),
      (20, "here", 62, 1), (21, "and", 64, 1), (22, "there", 60, 2)]),
    ("puppy", "I see red!", [(24, "I", 64, 1), (25, "see", 67, 1), (26, "red", 72, 2)]),
    ("kitten", "I see red!", [(28, "I", 64, 1), (29, "see", 67, 1), (30, "red", 72, 2)]),
    ("puppy", "A red, red car!",
     [(32, "uh", 67, 0.5), (32.5, "red", 69, 0.5), (33, "red", 67, 1), (34, "car", 64, 2)]),
    ("kitten", "A red, red car!",
     [(36, "uh", 67, 0.5), (36.5, "red", 69, 0.5), (37, "red", 67, 1), (38, "car", 64, 2)]),
    ("both", "Yay!", [(40, "yay", 72, 2)]),
]
CHORDS = [(0, "C", 4), (4, "G", 4),                                                    # intro
          (8, "C", 4), (12, "F", 2), (14, "C", 2), (16, "C", 4), (20, "G", 2), (22, "C", 2),  # chorus
          (24, "C", 8), (32, "F", 2), (34, "C", 2), (36, "G", 2), (38, "C", 2),        # red
          (40, "C", 4)]                                                                # the end
END = 44  # beats
RAINBOW = ["red", "orange", "yellow", "green", "blue", "purple", "pink"]


def cast():
    """Maple and Domi, bigger than in the episodes: they are the singers."""
    return (rig.Character("puppy", "golden", voice_pitch=3, seed=1, home=(560, 1050), size=0.85),
            rig.Character("kitten", "tuxedo", voice_pitch=6, seed=2, home=(1360, 1050), size=0.85))


def build(voice, sing=True):
    length = END * BEAT + 1.5
    show = Show(voice, mascot=False)
    for character in cast():
        show.join(character)
    tune = [(b, note, n) for _, _, notes in LINES for b, _, note, n in notes]
    show.music = song.band(BEAT, length, CHORDS, INTRO_TUNE + tune)
    show.music_level, show.duck, show.fade = 0.09, 1.0, 0.6  # the singing is about 7 dB louder
    if sing:
        parts = song.vocals(voice, LINES, BEAT, length)
        show.voices.append((0.0, song.mix_vocals(parts)))
        for name, part in parts.items():
            show.cast[name].talking.append((0.0, sound.mouth_levels(part, FPS)))
    show.add(song.Karaoke(LINES, BEAT))

    def at(beat):
        return beat * BEAT

    # Intro: the title falls in, Maple and Domi wave.
    show.add(Letters(show.title(TITLE, 140), at(0.3), at(7.4), 960, 400))
    plinks(show, at(0.3), TITLE)
    for who in ("puppy", "kitten"):
        show.act(who, "wave", at(1), seconds=at(5))

    # Chorus: seven color friends pop up, one on every syllable, then jump on every syllable.
    first, second = [b for b, *_ in LINES[0][2]], [b for b, *_ in LINES[1][2]]
    for k, color in enumerate(RAINBOW):
        spr, anc = show.splat(color)
        show.add(Actor(spr, anc, at(first[k]), at(24), 330 + 210 * k, 420, scale=0.3, bob=6, wobble=3, phase=k,
                       jumps=[at(second[k])]))
        show.sfx(at(first[k]), sound.sfx_pop(), 0.18)
    for who in ("puppy", "kitten"):
        show.act(who, "dance", at(8), seconds=at(16))

    # Verse: Maple sings, Domi sings it back. The color and the thing pop up when they are sung.
    spr, anc = show.splat("red")
    show.add(Actor(spr, anc, at(26), at(END) + 1, 760, 360, scale=0.5, bob=8, wobble=3, jumps=[at(30), at(37)]))
    show.sfx(at(26), sound.sfx_pop(), 0.3)
    spr, anc = show.thing("car", "red")
    show.add(Actor(spr, anc, at(34), at(END) + 1, 1160, 370, scale=0.55, bob=8, wobble=3, phase=1, jumps=[at(38)]))
    show.sfx(at(34), sound.sfx_pop(), 0.3)
    for beat, singer, listener in ((24, "puppy", "kitten"), (28, "kitten", "puppy"), (32, "puppy", "kitten"),
                                   (36, "kitten", "puppy")):
        show.act(singer, "happy", at(beat))
        show.act(listener, "wag_tail" if listener == "puppy" else "swish_tail", at(beat), seconds=at(3))

    # The end: "Yay!", arms up, confetti.
    show.cheer(at(40), (960, 360), n=110, move="happy")
    show.sfx(at(40), sound.sfx_chime(), 0.4)

    show.snap(at(4), "intro")
    show.snap(at(14.5), "chorus")
    show.snap(at(27), "red")
    show.snap(at(35), "car")
    show.snap(at(40.6), "yay")
    show.t = length
    return show


def main():
    ap = argparse.ArgumentParser(description="Make the Colors Song (the first part, a test).")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast, without singing)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    voice = sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json")
    show = build(voice, sing=not args.preview)
    stills = show.preview() if args.preview else show.render(OUT / "colors_song_test.mp4")
    contact_sheet(list(stills.values()), OUT / "colors_song_preview.jpg")
    print("Done.")


if __name__ == "__main__":
    main()
