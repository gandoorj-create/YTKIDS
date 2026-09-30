#!/usr/bin/env python3
"""Yumizoo channel intro: "Peek-a-boo! Yu-mi-zoo!" (about 4.6 seconds).

    python3 make_intro.py              # output/intro_boo.mp4, intro_late.mp4, intro_flip.mp4
                                       # and intro_all.mp4 (all 3 in a row, with numbers, to compare)
    python3 make_intro.py --preview    # only still pictures (fast)

The tune is the same in every version; only the small surprise (the "gag") changes.
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg

from kidsvid import intro, sound
from kidsvid.show import contact_sheet

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"


def main():
    ap = argparse.ArgumentParser(description="Make the channel intro.")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    voice = sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json")
    sung = intro.voices(voice)  # the same singing in every version
    files, stills = [], []
    for k, gag in enumerate(intro.GAGS, 1):
        if args.preview:
            stills += intro.build(voice, gag, label=str(k), sung=sung).preview().values()
            continue
        intro.build(voice, gag, sung=sung).render(OUT / f"intro_{gag}.mp4")  # the one to use
        path = OUT / f"intro_{k}_{gag}_numbered.mp4"
        stills += intro.build(voice, gag, label=str(k), sung=sung).render(path).values()
        files.append(path)
        print(f"{k} {gag}: {intro.GAGS[gag]}")
    contact_sheet(stills, OUT / "intro_preview.jpg", cols=2)
    if args.preview:
        return
    listing = OUT / "intro_list.txt"
    listing.write_text("".join(f"file '{f.name}'\n" for f in files))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(OUT / "intro_all.mp4")], check=True)
    listing.unlink()
    for f in files:
        f.unlink()
    print("made intro_all.mp4")


if __name__ == "__main__":
    main()
