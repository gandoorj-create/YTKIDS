#!/usr/bin/env python3
"""Episode 1: "Learn Colors for Kids" (about 5 minutes).

    python3 make_episode1.py              # full video -> output/episode1_learn_colors.mp4 (about 12 minutes)
    python3 make_episode1.py --preview    # only still pictures (fast)

Also makes: episode1_thumbnail.jpg, episode1_preview.jpg and episode1_youtube.txt (title, description, chapters).
"""
import argparse
from pathlib import Path

from kidsvid import art, lessons, sound
from kidsvid.anim import place
from kidsvid.show import Show, contact_sheet

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
VOICE = ROOT / "assets" / "voices" / "jenny"

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
Let's learn colors with our little lamb! In this video, kids learn red, blue, yellow and green,
find the right color, and play a fun guessing game. Kids can shout the answers!
For toddlers and preschool kids (2-5 years).

CHAPTERS
{chapters}

TAGS
learn colors, colors for kids, toddler learning video, preschool learning, guess the color, kids quiz

SETTINGS
Audience: Yes, it's made for kids
"""


def build(voice):
    show = Show(voice)
    lessons.intro(show, ("Let's Learn", "Colors!"), HOOK)
    for color, things, find, odd, quizzes in LESSONS:
        lessons.color_lesson(show, color, things, find, odd, quizzes)
    lessons.guessing_game(show, GAME)
    lessons.final_challenge(show, ["red", "blue", "yellow", "green"], BONUS)
    lessons.goodbye(show, PARADE)
    return show


def thumbnail(path):
    img = art.background(1920, 1080)
    for spr, anchor, dx in art.title_letters("Learn Colors!", 200):
        place(img, spr, 960 + dx, 290, anchor=anchor)
    for thing, color, x, y, s, rot in (("balloon", "red", 960, 640, 0.72, 6), ("star", "yellow", 1330, 600, 0.62, -8),
                                       ("frog", "green", 1690, 700, 0.56, 4), ("fish", "blue", 1180, 900, 0.55, -5),
                                       ("apple", "red", 1580, 950, 0.45, 8)):
        spr, anc = art.THINGS[thing](art.COLORS[color])
        place(img, spr, x, y, s, rot=rot, anchor=anc)
    place(img, art.lamb("happy", 3), 380, 1070, 1.45, anchor=art.LAMB_FEET)
    img.resize((1280, 720), resample=3).save(path, quality=92)


def main():
    ap = argparse.ArgumentParser(description="Make episode 1: Learn Colors for Kids.")
    ap.add_argument("--preview", action="store_true", help="only still pictures (fast)")
    ap.add_argument("--out", default=str(OUT / "episode1_learn_colors.mp4"))
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    show = build(sound.Voice(VOICE / "voice.onnx", VOICE / "voice.json"))
    print(f"Length: {show.t / 60:.1f} min\n{show.chapters_text()}")
    stills = show.preview() if args.preview else show.render(Path(args.out))
    contact_sheet(list(stills.values()), OUT / "episode1_preview.jpg")
    (OUT / "episode1_youtube.txt").write_text(YOUTUBE.format(chapters=show.chapters_text()))
    thumbnail(OUT / "episode1_thumbnail.jpg")
    print("Done.")


if __name__ == "__main__":
    main()
