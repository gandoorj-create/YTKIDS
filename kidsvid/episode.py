"""What every episode file needs: Maple and Domi, the channel intro, the thumbnail, and making the files.

An episode file (like make_episode1.py) has its lists at the top, a build(voice) function that puts the
building blocks in order, and the YouTube text. Then it calls episode.main().
"""
import argparse
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg

from . import art, intro, rig, sound
from .anim import place
from .show import contact_sheet

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"
INTRO = "late"  # the channel intro at the start: the kitten comes up late (see make_intro.py)
READY_INTRO = ROOT / "assets" / "intro"  # ready-made intros, for computers without pyworld (like Windows)


def cast():
    """The puppy (bottom left) and the kitten (bottom right)."""
    return (rig.Character("puppy", "golden", voice_pitch=3, seed=1, home=(240, 1064), size=0.65),
            rig.Character("kitten", "tuxedo", voice_pitch=6, seed=2, home=(1700, 1064), size=0.65))


def thumbnail(path, title, things):
    """The YouTube picture: the title on top, things on the right, Maple and Domi cheering on the left.
    things: [(thing, color, x, y, scale, turn)]."""
    img = art.background(1920, 1080)
    for spr, anchor, dx in art.title_letters(title, 200):
        place(img, spr, 960 + dx, 290, anchor=anchor)
    for thing, color, x, y, s, rot in things:
        spr, anc = art.THINGS[thing](art.COLORS[color])
        place(img, spr, x, y, s, rot=rot, anchor=anc)
    for kind, colors, x in (("puppy", "golden", 290), ("kitten", "tuxedo", 740)):  # both cheering, arms up
        ch = rig.Character(kind, colors, 0, home=(x, 1085), size=0.92)
        ch.draw_pose(img, rig.Pose(x, 1085, arm_l=14, arm_r=-14, eyes="happy", mouth=3))
    img.resize((1280, 720), resample=3).save(path, quality=92)


def join(parts, out):
    """Videos one after another in one file (no new encoding: they are all made the same way)."""
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts))  # "/" works on Windows too
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    listing.unlink()


def make_intro(voice, path):
    """The channel intro. The singing needs pyworld; without it, the ready-made intro is used."""
    try:
        import pyworld  # noqa: F401
    except ImportError:
        print("(pyworld is not installed, so the ready-made intro is used)")
        shutil.copy(READY_INTRO / path.name, path)
        return
    intro.build(voice, INTRO).render(path)


def main(name, video, about, build, youtube, thumb_title, thumb_things):
    """Make an episode: the video (the channel intro, then the show), still pictures, the YouTube text and
    the thumbnail. name: the start of the file names, like "episode1"; video: like "episode1_learn_colors.mp4"."""
    ap = argparse.ArgumentParser(description=about)
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    ap.add_argument("--no-intro", action="store_true", help="without the channel intro at the start")
    ap.add_argument("--out", default=str(OUT / video))
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    voice = sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json")
    show = build(voice)
    offset = 0.0 if args.no_intro else intro.LENGTH
    print(f"Length: {(show.t + offset) / 60:.1f} min\n{show.chapters_text(offset)}")
    if args.preview:
        stills = show.preview()
    elif args.no_intro:
        stills = show.render(Path(args.out))
        show.add_chapters(Path(args.out))
    else:
        body, opening = OUT / f"{name}_no_intro.mp4", OUT / f"intro_{INTRO}.mp4"
        stills = show.render(body)
        make_intro(voice, opening)
        join([opening, body], Path(args.out))
        show.add_chapters(Path(args.out), offset)
        show.add_chapters(body)
    contact_sheet(list(stills.values()), OUT / f"{name}_preview.jpg")
    if not args.preview:  # the voice is a little different every time, so only the made video has true times
        (OUT / f"{name}_youtube.txt").write_text(youtube.format(chapters=show.chapters_text(offset)))
    thumbnail(OUT / f"{name}_thumbnail.jpg", thumb_title, thumb_things)
    print("Done.")
