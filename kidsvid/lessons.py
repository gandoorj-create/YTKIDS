"""Building blocks for episodes: intro, color lesson, quiz round, guessing game, final challenge, goodbye.

Each block starts at `show.t`, puts its pictures and sounds on the timeline, and moves `show.t` forward.
"""
from . import art, sound
from .show import COUNT_STEP, Actor, Countdown, Letters

STAGE = (960, 520)                            # one big thing in the middle
SLOTS = [(640, 500), (1020, 500), (1400, 500)]  # three things in a row
TOP = (960, 118)                              # question text
SCALE = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23]  # C major scale, for the letter "plinks"
PRAISE = ["You got it!", "Great job!", "Well done!", "Awesome!", "Super!"]


def a_or_an(word):
    return "an" if word[0] in "aeiou" else "a"


def plinks(show, at, words):
    """One happy note for every letter of a falling title."""
    for i in range(len(words.replace(" ", ""))):
        show.sfx(at + 0.25 + i * 0.05, sound.sfx_plink(72 + SCALE[i % len(SCALE)]), 0.2)


def countdown(show, at, x, y):
    show.add(Countdown(show.badges, at, x, y))
    for k in range(3):
        show.sfx(at + k * COUNT_STEP, sound.sfx_boop((72, 76, 79)[k]), 0.35)
    return at + 3 * COUNT_STEP


def intro(show, title_lines, hook, lines=("Hello kids!", "Baa! I'm a little lamb!", "Today we are learning colors!",
                                          "Red, blue, yellow and green!", "Are you ready? Let's go!")):
    """Strong start: colorful things pop up at once, the title falls in, the lamb says hello."""
    show.chapter("Intro")
    t0 = show.t
    t = t0 + 0.5
    for line in lines:
        last = t
        t = show.say(line, t) + 0.2
    show.cheer(last)
    end = max(t + 0.7, t0 + 11)  # YouTube chapters must be 10+ seconds
    spots = [(330, 170), (800, 150), (1590, 170), (1580, 820), (1180, 850), (780, 840)]
    for k, ((name, color), (x, y)) in enumerate(zip(hook, spots)):
        spr, anc = show.thing(name, color)
        show.add(Actor(spr, anc, t0 + 0.08 * k, end, x, y, scale=0.36, bob=10, wobble=5, phase=k))
        show.sfx(t0 + 0.08 * k, sound.sfx_pop(), 0.25)
    rows, sizes = ([470], [170]) if len(title_lines) == 1 else ([400, 630], [150, 190])
    for k, (words, y, size) in enumerate(zip(title_lines, rows, sizes)):
        start = t0 + 0.15 + 0.4 * k
        show.add(Letters(show.title(words, size), start, end - 0.6, 960, y))
        plinks(show, start, words)
    show.sfx(0.1, sound.sfx_boing(), 0.35)
    show.sfx(end - 0.6, sound.sfx_whoosh(), 0.3)
    show.loud_music.append((t0, end))
    show.snap(t0 + 2.2, "intro")
    show.t = end + 0.2


def quiz_round(show, thing, color, answer):
    """One thing in the middle: "What color is this ...?" 3, 2, 1, then the answer."""
    t0 = show.t
    q_end = show.say(f"What color is this {thing}?", t0 + 0.6)
    reveal = countdown(show, q_end + 0.35, 1480, 520)
    end = show.say(answer, reveal + 0.3) + 0.75
    spr, anc = show.thing(thing, color)
    show.add(Actor(show.stage, None, t0, end, *STAGE, z=0))
    show.add(Actor(spr, anc, t0 + 0.05, end, *STAGE, bob=14, wobble=4, jumps=[reveal]))
    q, qa = show.text("What color is this?", 96)
    show.add(Actor(q, qa, t0 + 0.35, end, *TOP))
    word, wa = show.text(f"{color.capitalize()}!", 170, art.COLORS[color])
    show.add(Actor(word, wa, reveal, end, 960, 935, wobble=3))
    show.sfx(t0, sound.sfx_pop(), 0.45)
    show.sfx(reveal, sound.sfx_chime(), 0.5)
    show.cheer(reveal, STAGE)
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.t = end + 0.15
    return reveal


def pick_one(show, choices, right, ask_text, ask_line, answer_line):
    """Three things in a row. Kids choose one; after 3, 2, 1 the right one jumps in a golden circle."""
    t0 = show.t
    reveal = countdown(show, show.say(ask_line, t0 + 0.6) + 0.3, 1720, 500)
    end = show.say(answer_line, reveal + 0.3) + 0.8
    for k, (thing, color) in enumerate(choices):
        spr, anc = show.thing(thing, color)
        ok = k == right
        show.add(Actor(spr, anc, t0 + 0.12 * k, end, *SLOTS[k], scale=0.6, bob=8, wobble=3, phase=k,
                       jumps=[reveal] if ok else [], shrink_at=None if ok else reveal, z=2))
        show.sfx(t0 + 0.12 * k, sound.sfx_pop(), 0.3)
    show.add(Actor(show.ring, None, reveal, end, *SLOTS[right], scale=0.95, z=1))
    q, qa = show.text(ask_text, 90)
    show.add(Actor(q, qa, t0 + 0.3, end, *TOP))
    show.sfx(reveal, sound.sfx_chime(), 0.5)
    show.cheer(reveal, SLOTS[right])
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.t = end + 0.1
    return reveal


def color_lesson(show, color, things, find, odd, quiz_things):
    """About 55 seconds: meet the color, see 3 things, find it, odd one out, then quiz rounds."""
    name = color.capitalize()
    rgb = art.COLORS[color]
    show.chapter(name)

    # 1. Meet the color: a paint splash with a face. Kids can say the color.
    t0 = show.t
    t1 = show.say(f"This is {color}!", t0 + 0.5)
    t2 = show.say(f"Can you say {color}?", t1 + 0.25)
    t3 = t2 + 1.8  # time for kids to say it
    end = show.say(f"{name}!", t3) + 0.9
    spr, anc = show.splat(color)
    show.add(Actor(spr, anc, t0, end, 960, 500, bob=10, wobble=2, jumps=[t3]))
    word, wa = show.text(name, 170, rgb)
    show.add(Actor(word, wa, t0 + 0.5, end, 960, 900, wobble=3, jumps=[t3]))
    say_it, sa = show.text("Can you say it?", 90)
    show.add(Actor(say_it, sa, t1 + 0.25, t3 + 0.3, *TOP))
    show.sfx(t0, sound.sfx_pop(), 0.45)
    show.sfx(t3, sound.sfx_chime(), 0.45)
    show.cheer(t3, (960, 500))
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.snap(t3 + 0.5, f"{color}: meet")

    # 2. Three things with this color, one by one.
    t = end + 0.1
    starts = []
    for thing in things:
        starts.append(t)
        show.sfx(t, sound.sfx_pop(), 0.35)
        t = show.say(f"{a_or_an(color).capitalize()} {color} {thing}!", t + 0.35) + 0.3
    together = t + 0.1
    end = show.say(f"They are all {color}!", together) + 0.8
    for k, thing in enumerate(things):
        spr, anc = show.thing(thing, color)
        show.add(Actor(spr, anc, starts[k], end, *SLOTS[k], scale=0.6, bob=8, wobble=3, phase=k,
                       jumps=[together]))
        label, la = show.text(thing, 64, rgb)  # the voice says the color; long labels would touch
        show.add(Actor(label, la, starts[k] + 0.35, end, SLOTS[k][0], 730))
    show.sfx(together, sound.sfx_chime(), 0.35)
    show.cheer(together)
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.snap(together + 0.9, f"{color}: things")

    # 3. Find it: three things, only one has this color.
    show.t = end + 0.1
    right = next(k for k, (_, c) in enumerate(find) if c == color)
    reveal = pick_one(show, find, right, f"Find the {color} one!", f"Can you find the {color} one?",
                      f"Here it is! The {color} {find[right][0]}!")
    show.snap(reveal + 0.5, f"{color}: find")

    # 4. Odd one out: two things have this color, one does not.
    right = next(k for k, (_, c) in enumerate(odd) if c != color)
    thing, other = odd[right]
    pick_one(show, odd, right, f"Which one is not {color}?", f"Which one is not {color}?",
             f"The {thing} is not {color}! It's {other}!")

    # 5. Quiz rounds.
    for k, thing in enumerate(quiz_things):
        answer = f"{name}! Great job!" if k % 2 == 0 else f"{name}! It's {a_or_an(color)} {color} {thing}!"
        reveal = quiz_round(show, thing, color, answer)
        if k == 0:
            show.snap(reveal + 0.6, f"{color}: quiz")


def guessing_game(show, items):
    """A title card, then one quiz round for each (thing, color)."""
    show.chapter("Guessing game")
    t0 = show.t
    end = show.say("Can you guess the color?", show.say("Now let's play a guessing game!", t0 + 0.6) + 0.2) + 0.7
    show.add(Letters(show.title("Guessing Game!", 160), t0 + 0.1, end - 0.4, 960, 500))
    plinks(show, t0 + 0.1, "Guessing Game!")
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.snap(t0 + 1.6, "game: title")
    show.t = end + 0.2
    for k, (thing, color) in enumerate(items):
        name = color.capitalize()
        if k % 2 == 0:
            answer = f"{name}! It's {a_or_an(color)} {color} {thing}!"
        else:
            answer = f"{name}! {PRAISE[(k // 2) % len(PRAISE)]}"
        reveal = quiz_round(show, thing, color, answer)
        if k == 0:
            show.snap(reveal + 0.6, "game: round 1")


def final_challenge(show, colors, bonus):
    """Kids say every color they learned. Then two new colors for next time."""
    show.chapter("Final challenge")
    t0 = show.t
    end = show.say("Final challenge! Can you remember all the colors?", t0 + 0.6) + 0.7
    show.add(Letters(show.title("Final Challenge!", 160), t0 + 0.1, end - 0.4, 960, 500))
    plinks(show, t0 + 0.1, "Final Challenge!")
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)

    t = end + 0.2
    xs = [1020 + (k - (len(colors) - 1) / 2) * 330 for k in range(len(colors))]
    starts, reveals = [], []
    for color in colors:
        starts.append(t)
        show.sfx(t, sound.sfx_pop(), 0.35)
        reveals.append(t + 2.2)  # time for kids to say it
        show.sfx(t + 2.2, sound.sfx_plink(84), 0.3)
        t = show.say(f"{color.capitalize()}!", t + 2.2) + 0.35
    wow = t + 0.1
    end = show.say("Wow! You remember them all!", wow) + 0.9
    for k, color in enumerate(colors):
        spr, anc = show.splat(color)
        show.add(Actor(spr, anc, starts[k], end, xs[k], 470, scale=0.45, bob=6, wobble=3, phase=k,
                       jumps=[reveals[k], wow]))
        word, wa = show.text(color.capitalize(), 84, art.COLORS[color])
        show.add(Actor(word, wa, reveals[k], end, xs[k], 690))
    q, qa = show.text("Say the color!", 90)
    show.add(Actor(q, qa, starts[0], end, *TOP))
    show.sfx(wow, sound.sfx_chime(), 0.5)
    show.cheer(wow, (1020, 470), n=110)
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.snap(wow + 0.6, "final")

    # Bonus: two new colors, so kids want to watch the next episode.
    t0 = end + 0.1
    t = show.say("And here are two new colors!", t0 + 0.5)
    spots = [(760, 500), (1260, 500)]
    shown = []
    for thing, color, line in bonus:
        shown.append((thing, color, t + 0.3))
        show.sfx(t + 0.3, sound.sfx_pop(), 0.4)
        t = show.say(line, t + 0.6)
    nxt = show.say("We will learn them next time!", t + 0.3)
    end = nxt + 0.9
    for (thing, color, at), (x, y) in zip(shown, spots):
        spr, anc = show.thing(thing, color)
        show.add(Actor(spr, anc, at, end, x, y, scale=0.7, bob=10, wobble=4, phase=x))
        word, wa = show.text(color.capitalize(), 110, art.COLORS[color])
        show.add(Actor(word, wa, at + 0.3, end, x, 800))
    q, qa = show.text("New colors!", 90)
    show.add(Actor(q, qa, t0 + 0.3, end, *TOP))
    show.sfx(end - 0.4, sound.sfx_whoosh(), 0.3)
    show.snap(nxt, "bonus")
    show.t = end + 0.1


def goodbye(show, parade, lines=("Great job, friends! You know your colors!", "See you in the next video! Bye-bye!"),
            title="Great job!"):
    """Title, a row of happy things, and the lamb says goodbye. This ends the show."""
    show.chapter("Goodbye")
    t0 = show.t
    t = t0 + 0.9
    for line in lines:
        t = show.say(line, t) + 0.3
    last = t - 0.3
    end = max(last + 3.0, t0 + 11)
    show.add(Letters(show.title(title, 170), t0 + 0.1, end + 5, 960, 250))
    plinks(show, t0 + 0.1, title)
    n = len(parade)
    for k, (thing, color) in enumerate(parade):
        at = t0 + 0.4 + 0.18 * k
        spr, anc = show.thing(thing, color)
        show.add(Actor(spr, anc, at, end + 5, 1100 + (k - (n - 1) / 2) * 260, 600, scale=0.44, bob=18,
                       phase=-0.9 * k))
        show.sfx(at, sound.sfx_pop(), 0.3)
    show.happy_from = last
    show.cheer(last + 0.1, (960, 250), n=110)
    show.sfx(last + 0.1, sound.sfx_chime(), 0.45)
    show.loud_music.append((t0, end + 1))
    show.snap(last + 0.5, "goodbye")
    show.t = end
