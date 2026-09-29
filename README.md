# Yumizoo: kids' video maker

Cartoon learning videos for kids, made with code: pictures, voice, music, sound effects, and a 3D character.
No camera and no drawing app are needed.

## The channel

- Name: **Yumizoo** (yummy + zoo).
- Main character: **Maple**, a chestnut foal (baby horse) with a white star on its forehead.
- Friends: **Wobbaloo** (a jelly that can be any color), Cupcake and Marshmallow.
- Pictures of all of them are in `designs/`.

## Episode 1: "Learn Colors for Kids" (about 5 minutes)

| Time | Part |
| --- | --- |
| 0:00 | Intro: things pop up at once (hook), "Let's Learn Colors!", the lamb says hello |
| 0:11 | Red: meet the color, 3 red things, "Find the red one!", "Which one is not red?", 2 quiz rounds |
| 0:55 | Blue (same parts) |
| 1:38 | Yellow |
| 2:22 | Green |
| 3:06 | Guessing game: 10 questions, all colors mixed |
| 4:28 | Final challenge: kids say every color, then 2 new colors for next time (orange, purple) |
| 4:55 | Goodbye |

Kids get time to answer: the countdown is 3 seconds, and after "Can you say red?" there is a pause.
The times move a little each time we make the video, because the AI voice is a little different each time.

## How to use

```bash
pip install -r requirements.txt
python3 get_assets.py                # downloads the voice and the font
python3 make_episode1.py             # makes output/episode1_learn_colors.mp4 (about 12 minutes)
python3 make_episode1.py --preview   # only still pictures (fast)
```

`make_episode1.py` also makes `episode1_thumbnail.jpg` (the YouTube picture) and `episode1_youtube.txt`
(title, description, chapters).

To make a new episode, copy `make_episode1.py` and change the lists at the top (colors, things, questions).
To add a new thing (for example a car), add a drawing function to `kidsvid/art.py` and put it in `THINGS`.

## Channel intro

`python3 make_intro.py` makes 3 versions of the 6-second intro (tunes: chant, rising, wobbly) and
`intro_all.mp4` with all 3 in a row. The logo letters land on the notes, and at the end kids shout "Yumizoo!".
Maple gallops in and "sings" every note; Wobbaloo and Cupcake join.

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
| `make_intro.py` | The channel intro (3 tunes to choose from) |
| `foal3d.py` | The foal in 3D (Blender) |
| `kidsvid/lessons.py` | Building blocks: intro, color lesson, quiz round, guessing game, final challenge, goodbye |
| `kidsvid/intro.py` | The intro: tunes, the singing jelly, the logo |
| `kidsvid/show.py` | The engine: timeline, talking lamb, confetti, making the video file |
| `kidsvid/art.py` | Drawings: foal, lamb, jelly, cupcake, marshmallow, 14 things, background, text |
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
