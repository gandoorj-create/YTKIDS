#!/usr/bin/env python3
"""Episode 1: "Learn Colors for Kids" (about 5 minutes).

    python3 make_episode1.py              # full video -> output/episode1_learn_colors.mp4 (about 20 minutes)
    python3 make_episode1.py --preview    # only still pictures (fast)
    python3 make_episode1.py --no-intro   # without the channel intro at the start

Also makes: episode1_thumbnail.jpg, episode1_preview.jpg and episode1_youtube.txt (title, description, chapters).
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg

from kidsvid import art, endcard, intro, lessons, rig, sound
from kidsvid.anim import place
from kidsvid.show import Show, contact_sheet

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"
INTRO = "late"  # the channel intro at the start: the kitten comes up late (see make_intro.py)

HOOK = [("balloon", "red"), ("star", "yellow"), ("fish", "blue"), ("frog", "green"),
        ("grapes", "purple"), ("orange", "orange")]
LESSONS = [  # color, three things, "find it" choices, "not this color" choices, quiz things
    ("red", ["balloon", "apple", "car"], [("ball", "blue"), ("apple", "red"), ("banana", "yellow")],
     [("balloon", "red"), ("frog", "green"), ("car", "red")], ["bird", "ball"]),
    ("blue", ["ball", "fish", "bird"], [("frog", "green"), ("duck", "yellow"), ("car", "blue")],
     [("fish", "blue"), ("ball", "blue"), ("banana", "yellow")], ["balloon", "star"]),
    ("yellow", ["star", "banana", "duck"], [("apple", "red"), ("star", "yellow"), ("leaf", "green")],
     [("duck", "yellow"), ("car", "red"), ("banana", "yellow")], ["car", "bird"]),
    ("green", ["frog", "leaf", "tree"], [("balloon", "red"), ("ball", "blue"), ("apple", "green")],
     [("leaf", "green"), ("tree", "green"), ("fish", "blue")], ["ball", "car"]),
]
GAME = [("car", "blue"), ("apple", "green"), ("duck", "yellow"), ("star", "red"), ("leaf", "green"),
        ("banana", "yellow"), ("bird", "blue"), ("car", "red"), ("fish", "yellow"), ("balloon", "green")]
BONUS = [("orange", "orange", "Orange! Like an orange!"), ("grapes", "purple", "Purple! Like grapes!")]
PARADE = [("balloon", "red"), ("fish", "blue"), ("star", "yellow"), ("frog", "green"), ("grapes", "purple")]

YOUTUBE = """TITLE
Learn Colors for Kids | Guess the Color Game | Toddler Learning Video

DESCRIPTION
Let's learn colors with Maple the puppy and Domi the kitten! In this video, kids learn red, blue, yellow and green,
find the right color, and play a fun guessing game. Kids can shout the answers!
For toddlers and preschool kids (2-5 years).

CHAPTERS
{chapters}

TAGS
learn colors, colors for kids, toddler learning video, preschool learning, guess the color, kids quiz

SETTINGS
Audience: Yes, it's made for kids
"""


def cast():
    """The puppy (bottom left) and the kitten (bottom right)."""
    return (rig.Character("puppy", "golden", voice_pitch=3, seed=1, home=(240, 1064), size=0.65),
            rig.Character("kitten", "tuxedo", voice_pitch=6, seed=2, home=(1700, 1064), size=0.65))


def build(voice):
    show = Show(voice, mascot=False)
    for character in cast():
        show.join(character)
    lessons.intro(show, ("Let's Learn", "Colors!"), HOOK)
    for color, things, find, odd, quizzes in LESSONS:
        lessons.color_lesson(show, color, things, find, odd, quizzes)
    lessons.guessing_game(show, GAME)
    lessons.final_challenge(show, ["red", "blue", "yellow", "green"], BONUS)
    lessons.goodbye(show, PARADE)
    endcard.end_card(show)
    return show


def thumbnail(path):
    img = art.background(1920, 1080)
    for spr, anchor, dx in art.title_letters("Learn Colors!", 200):
        place(img, spr, 960 + dx, 290, anchor=anchor)
    for thing, color, x, y, s, rot in (("balloon", "red", 1130, 620, 0.66, 6), ("star", "yellow", 1460, 570, 0.6, -8),
                                       ("frog", "green", 1760, 720, 0.5, 4), ("fish", "blue", 1270, 900, 0.52, -5),
                                       ("apple", "red", 1620, 950, 0.45, 8)):
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


def main():
    ap = argparse.ArgumentParser(description="Make episode 1: Learn Colors for Kids.")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    ap.add_argument("--no-intro", action="store_true", help="without the channel intro at the start")
    ap.add_argument("--out", default=str(OUT / "episode1_learn_colors.mp4"))
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
    else:
        body, opening = OUT / "episode1_no_intro.mp4", OUT / f"intro_{INTRO}.mp4"
        stills = show.render(body)
        intro.build(voice, INTRO).render(opening)
        join([opening, body], Path(args.out))
    contact_sheet(list(stills.values()), OUT / "episode1_preview.jpg")
    (OUT / "episode1_youtube.txt").write_text(YOUTUBE.format(chapters=show.chapters_text(offset)))
    thumbnail(OUT / "episode1_thumbnail.jpg")
    print("Done.")


if __name__ == "__main__":
    main()
