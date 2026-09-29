#!/usr/bin/env python3
"""Yumizoo channel intro, 3 tunes to choose from.

    python3 make_intro.py
    -> output/intro_1_chant.mp4, intro_2_rising.mp4, intro_3_wobbly.mp4 and intro_all.mp4 (all 3 in a row)
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

from kidsvid import intro, sound

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"


def main():
    OUT.mkdir(exist_ok=True)
    voice = sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json")
    shout = intro.group_shout(voice)  # the same "Yumizoo!" in every version, so only the tune is different
    files = []
    for k, tune in enumerate(intro.TUNES, 1):
        path = OUT / f"intro_{k}_{tune}.mp4"
        stills = intro.build(voice, tune, shout, label=str(k)).render(path)
        if k == 1:
            next(iter(stills.values())).save(OUT / "intro_frame.jpg", quality=92)
        files.append(path)
        print("made", path.name)
    listing = OUT / "intro_list.txt"
    listing.write_text("".join(f"file '{f.name}'\n" for f in files))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(OUT / "intro_all.mp4")], check=True)
    listing.unlink()
    print("made intro_all.mp4")


if __name__ == "__main__":
    main()
