#!/usr/bin/env python3
"""Episode 2: "Learn Colors for Kids Part 2": orange, purple and pink (about 5 minutes).

    python3 make_episode2.py              # full video -> output/episode2_more_colors.mp4 (about 20 minutes)
    python3 make_episode2.py --preview    # only still pictures (fast)
    python3 make_episode2.py --no-intro   # without the channel intro at the start

Also makes: episode2_thumbnail.jpg, episode2_preview.jpg and episode2_youtube.txt (title, description, chapters).
Episode 1 ended with "orange and purple next time", so this one starts with them.
"""
from kidsvid import endcard, episode, lessons
from kidsvid.lessons import FRIEND, HOST
from kidsvid.show import Show

INTRO_LINES = ((HOST, "Hello kids! I'm Maple the puppy! Woof woof!"), (FRIEND, "And I'm Domi the kitten! Meow!"),
               (HOST, "Today we are learning new colors!"), (FRIEND, "Orange, purple and pink!"),
               (HOST, "Are you ready? Let's go!"))
HOOK = [("carrot", "orange"), ("grapes", "purple"), ("pig", "pink"), ("pumpkin", "orange"),
        ("flower", "purple"), ("cupcake", "pink")]
LESSONS = [  # color, three things, "find it" choices, "not this color" choices, quiz things
    ("orange", ["carrot", "pumpkin", "fish"], [("ball", "blue"), ("leaf", "orange"), ("apple", "red")],
     [("carrot", "orange"), ("frog", "green"), ("fish", "orange")], ["ball", "car"]),
    ("purple", ["grapes", "flower", "balloon"], [("star", "yellow"), ("car", "purple"), ("leaf", "green")],
     [("ball", "purple"), ("grapes", "purple"), ("fish", "orange")], ["star", "bird"]),
    ("pink", ["pig", "cupcake", "ball"], [("frog", "green"), ("fish", "blue"), ("flower", "pink")],
     [("balloon", "pink"), ("duck", "yellow"), ("star", "pink")], ["fish", "car"]),
]
GAME = [("fish", "orange"), ("balloon", "purple"), ("pig", "pink"), ("apple", "red"), ("carrot", "orange"),
        ("flower", "purple"), ("car", "blue"), ("star", "pink"), ("frog", "green"), ("duck", "yellow")]
ALL_COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "pink"]  # the final challenge: all 7
PARADE = [("carrot", "orange"), ("grapes", "purple"), ("pig", "pink"), ("pumpkin", "orange"), ("flower", "pink")]
GOODBYE_LINES = ((HOST, "Great job, friends! Now you know seven colors!"),)
THUMBNAIL = ("New Colors!", [("pig", "pink", 1150, 640, 0.62, 5), ("carrot", "orange", 1470, 590, 0.6, -8),
                             ("grapes", "purple", 1760, 720, 0.5, 6), ("pumpkin", "orange", 1290, 920, 0.5, -4),
                             ("cupcake", "pink", 1630, 940, 0.48, 7)])

YOUTUBE = """TITLE
Learn Colors for Kids Part 2 | Orange, Purple & Pink with Maple & Domi | Toddler Learning Video

DESCRIPTION (copy all of it, the chapters too)
Let's learn new colors with Maple the puppy and Domi the kitten!
In this video, kids learn orange, purple and pink, find the right color, play a fun guessing game, and say all seven colors. Kids can shout the answers!
For toddlers and preschool kids (2-5 years).

{chapters}

Watch Part 1 to learn red, blue, yellow and green!
Ask a grown-up to subscribe for more videos with Maple and Domi!

#learncolors #toddlerlearning #kidsvideos

TAGS
learn colors, colors for kids, orange purple pink, learn colors part 2, toddler learning video, preschool learning, guess the color, Maple and Domi, Yumizoo

SETTINGS
Thumbnail: episode2_thumbnail.jpg
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
    lessons.intro(show, ("Let's Learn", "New Colors!"), HOOK, INTRO_LINES)
    for color, things, find, odd, quizzes in LESSONS:
        lessons.color_lesson(show, color, things, find, odd, quizzes)
    lessons.guessing_game(show, GAME)
    lessons.final_challenge(show, ALL_COLORS)
    lessons.goodbye(show, PARADE, GOODBYE_LINES)
    endcard.end_card(show)
    return show


if __name__ == "__main__":
    episode.main("episode2", "episode2_more_colors.mp4", "Make episode 2: Learn Colors Part 2.", build, YOUTUBE,
                 *THUMBNAIL)
