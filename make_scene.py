#!/usr/bin/env python3
"""Make a video from a scene file. One line = one movement, in order.

    python3 make_scene.py scenes/example.txt
    python3 make_scene.py scenes/catalog.txt --labels   # shows each movement's name on the screen
    python3 make_scene.py --moves                       # all movements you can use

A line:  <who> <movement> [options]
  who:      puppy, kitten or both        (or "wait 1s" for a pause)
  options:  a length like 2s, a side (left / right), or words in quotes for say: say "Hello!"
"""
import argparse
import shlex
import sys
from pathlib import Path

from kidsvid import rig, sound
from kidsvid.show import Actor, Show, contact_sheet

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"
GAP = 0.15  # seconds between two lines


class SceneError(Exception):
    pass


def parse(path):
    steps = []
    for n, raw in enumerate(Path(path).read_text().splitlines(), 1):
        try:
            words = shlex.split(raw, comments=True)
        except ValueError as e:
            raise SceneError(f"line {n}: {e} ({raw.strip()})")
        if not words:
            continue
        who = words[0].lower()
        if who == "wait":
            steps.append((n, "wait", None, words[1:]))
            continue
        if who not in ("puppy", "kitten", "both") or len(words) < 2:
            raise SceneError(f"line {n}: a line starts with puppy, kitten, both or wait: {raw.strip()}")
        move = words[1].lower()
        if move not in rig.MOVES:
            raise SceneError(f"line {n}: there is no movement '{words[1]}'. Movements: {', '.join(rig.MOVES)}")
        if move == "say" and len(words) < 3:
            raise SceneError(f'line {n}: say needs words in quotes, like: {who} say "Hello!"')
        steps.append((n, who, move, words[2:]))
    return steps


def seconds(options, default):
    for o in options:
        number = o[:-1] if o.lower().endswith("s") else o
        try:
            return float(number)
        except ValueError:
            continue
    return default


def build(steps, voice, labels):
    show = Show(voice, mascot=False)
    show.music_level = 0.06
    show.join(rig.Character("puppy", "golden", voice_pitch=3, seed=1))
    show.join(rig.Character("kitten", "tuxedo", voice_pitch=6, seed=2))
    cast = show.cast
    t = 0.4
    for n, who, move, options in steps:
        if who == "wait":
            t += seconds(options, 1.0)
            continue
        names = ["puppy", "kitten"] if who == "both" else [who]
        spec = rig.MOVES[move]
        if move == "say":
            d = max(show.say(options[0], t, name) for name in names) - t + 0.3
        else:
            d = seconds(options, spec.length) if spec.timed else spec.length
        for name in names:
            cast[name].add(t, t + d, move, options)
            if spec.sounds:
                for at, sig, gain in spec.sounds(cast[name], t, d, options):
                    show.sfx(at, sig, gain)
        if labels:
            sprite, anchor = show.text(f"{who}: {move}", 64)
            show.add(Actor(sprite, anchor, t, t + d + 0.1, 960, 110, z=8))
        show.snap(t + 0.5 * d, f"{n:02d} {who} {move}")
        t += d + GAP
    show.t = t + 0.8
    return show


def main():
    ap = argparse.ArgumentParser(description="Make a video from a scene file.")
    ap.add_argument("scene", nargs="?", help="the scene file, like scenes/example.txt")
    ap.add_argument("--labels", action="store_true", help="show each movement's name on the screen")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    ap.add_argument("--moves", action="store_true", help="list all movements")
    ap.add_argument("--out", help="video file (default: output/<scene name>.mp4)")
    args = ap.parse_args()
    if args.moves or not args.scene:
        for name, spec in rig.MOVES.items():
            length = "as long as the words" if name == "say" else f"{spec.length:g}s" + (" or your length" if spec.timed else "")
            print(f"  {name:11s} {spec.about}  ({length})")
        return
    try:
        steps = parse(args.scene)
    except SceneError as e:
        sys.exit(f"Scene error: {e}")
    OUT.mkdir(exist_ok=True)
    show = build(steps, sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json"), args.labels)
    out = Path(args.out) if args.out else OUT / f"{Path(args.scene).stem}.mp4"
    print(f"{len(steps)} lines, {show.t:.1f} seconds")
    stills = show.preview() if args.preview else show.render(out)
    contact_sheet(list(stills.values()), out.with_name(f"{out.stem}_preview.jpg"), cols=4)
    print("Done:", out if not args.preview else out.with_name(f"{out.stem}_preview.jpg"))


if __name__ == "__main__":
    main()
