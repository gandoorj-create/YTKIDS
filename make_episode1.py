#!/usr/bin/env python3
"""Episode 1: "Learn Colors for Kids" (about 5 minutes).

    python3 make_episode1.py              # full video -> output/episode1_learn_colors.mp4 (about 20 minutes)
    python3 make_episode1.py --preview    # only still pictures (fast)
    python3 make_episode1.py --no-intro   # without the channel intro at the start

Also makes: episode1_thumbnail.jpg, episode1_preview.jpg and episode1_youtube.txt (title, description, chapters).
"""
from kidsvid import endcard, episode, lessons
from kidsvid.episode import OUT, VOICE  # noqa: F401 (make_shorts.py uses them)
from kidsvid.show import Show

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
THUMBNAIL = ("Learn Colors!", [("balloon", "red", 1130, 620, 0.66, 6), ("star", "yellow", 1460, 570, 0.6, -8),
                                ("frog", "green", 1760, 720, 0.5, 4), ("fish", "blue", 1270, 900, 0.52, -5),
                                ("apple", "red", 1620, 950, 0.45, 8)])

YOUTUBE = """TITLE
Learn Colors for Kids with Maple & Domi | Guess the Color Game | Toddler Learning Video

DESCRIPTION (copy all of it, the chapters too)
Let's learn colors with Maple the puppy and Domi the kitten!
In this video, kids learn red, blue, yellow and green, find the right color, and play a fun guessing game. Kids can shout the answers!
For toddlers and preschool kids (2-5 years).

{chapters}

Ask a grown-up to subscribe for more videos with Maple and Domi!

#learncolors #toddlerlearning #kidsvideos

TAGS
learn colors, colors for kids, toddler learning video, preschool learning, guess the color, kids quiz, Maple and Domi, Yumizoo

SETTINGS
Thumbnail: episode1_thumbnail.jpg
Audience: Yes, it's made for kids
Age restriction: No
Category: Education
Video language: English
Altered or synthetic content: No (a cartoon, nothing looks real)
Paid promotion: No
"""


def build(voice):
    show = Show(voice, mascot=False)
    for character in episode.cast():
        show.join(character)
    lessons.intro(show, ("Let's Learn", "Colors!"), HOOK)
    for color, things, find, odd, quizzes in LESSONS:
        lessons.color_lesson(show, color, things, find, odd, quizzes)
    lessons.guessing_game(show, GAME)
    lessons.final_challenge(show, ["red", "blue", "yellow", "green"], BONUS)
    lessons.goodbye(show, PARADE)
    endcard.end_card(show)
    return show


if __name__ == "__main__":
    episode.main("episode1", "episode1_learn_colors.mp4", "Make episode 1: Learn Colors for Kids.", build, YOUTUBE,
                 *THUMBNAIL)
