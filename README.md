# Yumizoo: kids' video maker

Cartoon learning videos for kids, made with code: pictures, voice, music, sound effects, and a 3D character.
No camera and no drawing app are needed.

## The channel

- Name: **Yumizoo** (yummy + zoo).
- Two main characters, both very chubby: **Maple**, a golden puppy with a red collar and a bone-shaped name tag,
  and **Domi**, a black-and-white (tuxedo) kitten with a pink collar and a fish-shaped name tag
  (see `designs/main_characters.jpg`). Their names are in `kidsvid/rig.py` (`NAMES`).
- Earlier ideas are still in the code and in `designs/`: the foal Maple (also in 3D), the jelly Wobbaloo,
  Cupcake, Marshmallow and the lamb.

## Episode 1: "Learn Colors for Kids" (about 5 minutes)

| Time | Part |
| --- | --- |
| 0:00 | Channel intro "Peek-a-boo! Yu-mi-zoo!" (4.6 s), then things pop up at once (hook), "Let's Learn Colors!", Maple and Domi walk in and say hello |
| 0:15 | Red: meet the color, 3 red things, "Find the red one!", "Which one is not red?", 2 quiz rounds |
| 0:59 | Blue (same parts) |
| 1:42 | Yellow |
| 2:25 | Green |
| 3:09 | Guessing game: 10 questions, all colors mixed |
| 4:31 | Final challenge: kids say every color, then 2 new colors for next time (orange, purple) |
| 4:57 | Goodbye: "Great job!", then the end card: "Thanks for watching!", Domi asks a grown-up to tap like and subscribe, a paw taps both buttons, and Maple and Domi wave bye-bye |

Maple the puppy (bottom left) and Domi the kitten (bottom right) take turns saying the lines. They jump for joy at every
right answer, tilt their heads while kids think, dance after the final challenge and wave goodbye.

The end card is drawn in the video (`kidsvid/endcard.py`), because "made for kids" videos have no clickable
end screens and no notification bell on YouTube. It asks a grown-up, not the child, to like and subscribe.

Kids get time to answer: the countdown is 3 seconds, and after "Can you say red?" there is a pause.
The times move a little each time we make the video, because the AI voice is a little different each time.

## Make it on your own computer (Windows)

1. Install Python 3.10 or newer from python.org (tick "Add Python to PATH").
2. On GitHub: the green **Code** button, then **Download ZIP**. Unzip it.
3. Double-click `setup_windows.bat`. It installs the libraries, downloads the voice and the font (only the
   first time), and makes Episode 1. The video is in the `output` folder at the end.

Making a video on your own computer does not use any Claude tokens. On a Mac, run the three commands below
in the Terminal instead.

The singing in the intro needs `pyworld`, which cannot be installed on Windows without a C++ compiler. So on
Windows the episode uses the ready-made intro in `assets/intro/`. To make intros yourself (Mac, Linux):
`pip install pyworld`.

## How to use

```bash
pip install -r requirements.txt
python3 get_assets.py                # downloads the voice and the font
python3 make_episode1.py             # makes output/episode1_learn_colors.mp4 (about 20 minutes)
python3 make_episode1.py --preview   # only still pictures (fast)
python3 make_episode1.py --no-intro  # without the channel intro at the start
```

`make_episode1.py` also makes `episode1_thumbnail.jpg` (the YouTube picture) and `episode1_youtube.txt`
(title, description, chapters; the chapter times include the intro). `episode1_no_intro.mp4` is the same episode
without the intro.

To make a new episode, copy `make_episode1.py` and change the lists at the top (colors, things, questions).
To add a new thing (for example a car), add a drawing function to `kidsvid/art.py` and put it in `THINGS`.

## Scenes: choose the movements

Write a scene file: one line = one movement, in order. Then make the video from it.

```text
puppy   walk_in   left
kitten  walk_in   right
puppy   say       "Hi friends!"
kitten  wave
both    jump
puppy   wag_tail  2s
kitten  dance     3s
both    sleep     2s
```

```bash
python3 make_scene.py scenes/example.txt            # makes output/example.mp4
python3 make_scene.py scenes/catalog.txt --labels   # every movement, with its name on the screen
python3 make_scene.py scenes/example.txt --preview  # only still pictures (fast)
python3 make_scene.py --moves                       # all movements
```

- Who: `puppy` (or `maple`), `kitten` (or `domi`), or `both`. `wait 1s` makes a pause.
- Movements: `walk_in`, `walk_out`, `say`, `jump`, `happy`, `surprised`, `sleep`, `dance`, `roll`, `wag_tail`,
  `swish_tail`, `flop_ears`, `head_tilt`, `wave`.
- Options: a length like `2s` (for `sleep`, `dance`, `wag_tail`, `swish_tail`, `wave`), a side `left` / `right`
  (for `walk_in`, `walk_out`, `roll`), and the words in quotes for `say`.
- `#` starts a note that the program does not read.

To add a new movement, write a function in `kidsvid/rig.py` that changes the pose, and add it to `MOVES`.

## Channel intro: "Peek-a-boo! Yu-mi-zoo!"

`python3 make_intro.py` makes the 4.6-second intro in 3 versions, and `intro_all.mp4` (all 3 in a row, numbered).
The tune is always the same. Only a small surprise changes, so each episode can use a different one:

| File | Surprise |
| --- | --- |
| `intro_boo.mp4` | both jump up together |
| `intro_late.mp4` | the kitten comes up late and gets a surprise (our favorite, number 2) |
| `intro_flip.mp4` | both do a flip in the air |

What happens: the logo drops in. The ears of the puppy and the kitten peek over a hill. They sing "Peek-a..."
with only their eyes showing, jump up on "BOO!", and kids answer "Yu-mi-ZOO!" (confetti, then they wave).
The singing is on real notes (E G C, A G C): the AI voice says each syllable, and WORLD (`pyworld`) puts it on
the note (`kidsvid/sing.py`).

Why it is made like this (research, September 2026):

- A branded intro works best at about 3-5 seconds; the first seconds decide if viewers stay
  ([teleprompter.com](https://www.teleprompter.com/blog/how-long-should-a-youtube-intro-be)).
- Sound logos are remembered better with a melody (about +20%) and with the brand name in them (about +15%).
  They usually have 3-6 notes, and 6 notes tested best
  ([mumbrella](https://mumbrella.com.au/melody-the-key-to-successful-audio-branding-729336),
  [University of Cambridge](https://www.repository.cam.ac.uk/items/903c50f3-6d66-4721-af94-7c037073b139)).
  Ours has 6 notes and sings the name.
- Kids learn a channel's first sound: children run to the screen at the first note of Cocomelon's intro
  (a child shouts the name there too).
- Peekaboo is funny because of surprise at an expected moment
  ([UCL](https://www.ucl.ac.uk/institute-of-advanced-studies/publications/2021/jan/ias-laughter-why-peekaboo-ultimate-baby-comedy)).
- Young children join in more when a video leaves them a part (call and answer, waiting for them)
  ([Disney Research](https://la.disneyresearch.com/publication/investigating-the-effects-of-interactive-features-for-preschool-television-programming/)).
- Parents are moving away from overstimulating videos, and the channels that grow are character-led
  ([Whizzy Studios](https://www.whizzystudios.com/post/kids-animation-trends-2026-whats-growing-on-youtube)):
  one clear action at a time, and a small new surprise that makes kids want to see what the characters do.

## Channel pictures

`python3 make_channel_art.py` makes the YouTube profile picture `channel_avatar.png` (800x800, YouTube shows it
as a circle) and the banner `channel_banner.png` (2560x1440). On the banner, the logo, the words and Maple and
Domi are in the middle part (1546x423) that phones show; computers show the full-width band, TVs everything.
`channel_banner_check.jpg` marks these parts. The finished pictures are also in `designs/`.

It also makes `channel_watermark.png` (a paw in a rainbow ring). Note: YouTube does not show the branding
watermark on "made for kids" videos.

Upload: YouTube Studio → Customization → Branding → Picture / Banner image / Video watermark.

## 3D foal

```bash
pip install bpy          # Blender as a Python module (about 370 MB)
python3 foal3d.py        # output/foal_3d.png, about 5 minutes on 4 CPU cores
python3 foal3d.py --preview
```

## What is where

| File | What it does |
| --- | --- |
| `make_episode1.py` | Episode 1: which parts, colors and things |
| `make_scene.py` | A video from a scene file (the movements you choose) |
| `scenes/` | Scene files: `example.txt`, `catalog.txt` (every movement) |
| `make_channel_art.py` | The YouTube profile picture and banner |
| `make_intro.py` | The channel intro, "Peek-a-boo! Yu-mi-zoo!" (3 surprises) |
| `foal3d.py` | The foal in 3D (Blender) |
| `kidsvid/lessons.py` | Building blocks: intro, color lesson, quiz round, guessing game, final challenge, goodbye |
| `kidsvid/endcard.py` | The end card: like and subscribe buttons, the tapping paw |
| `kidsvid/intro.py` | The intro: the tune, the hill, the peeking puppy and kitten, the logo |
| `kidsvid/sing.py` | Singing: puts the AI voice on musical notes (WORLD vocoder) |
| `kidsvid/show.py` | The engine: timeline, talking characters, confetti, making the video file |
| `kidsvid/rig.py` | The moving puppy and kitten: their parts, and every movement (`MOVES`) |
| `kidsvid/art.py` | Drawings: puppy and kitten (in parts), foal, lamb, jelly, cupcake, marshmallow, 14 things, background, text |
| `kidsvid/sound.py` | AI voice, music, sound effects, mixing |
| `kidsvid/anim.py` | Animation helpers (movement curves, placing pictures) |
| `make_demo.py` | The first 42-second demo (older code, made before the engine) |
| `get_assets.py` | Downloads the voice and the font |
| `designs/` | Character pictures, the 3D foal, the thumbnail |

## Licenses

- Font: Fredoka, SIL Open Font License (`assets/fonts/OFL.txt`). Free to use, also for business.
- Music and sound effects: made by our own code, so they belong to us.
- Blender (for the 3D foal) is free software; the pictures we make with it belong to us.
- Voice: the Piper "jenny_dioco" model. Its license was **not checked yet**
  (see https://github.com/dioco-group/jenny-tts-dataset). Check it before we post videos that earn money,
  or change to a paid AI voice that clearly allows business use.
