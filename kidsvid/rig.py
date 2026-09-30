"""Moving characters (cut-out animation).

The puppy and the kitten are made of parts (tail, body, paws, arms, head, ears). A movement such as
"jump" or "wave" moves the parts over time. MOVES lists every movement a scene file can use.
"""
import math
import random
from dataclasses import dataclass, field

from . import art, sound
from .anim import clamp, ease_out_back, place
from .show import FPS, W

GROUND = 1000
NAMES = {"puppy": "Maple", "kitten": "Domi"}  # written on their collar tags
HOME = {"puppy": 660, "kitten": 1260}  # where each character stands
MARK_SPOT = (540, 40)    # above the right ear: where "!", "?" and "Zzz" go (in the character picture)
ROLL_PIVOT = (300, 330)  # the middle of the whole character (head and body), for somersaults
SIDE = {"puppy": "left", "kitten": "right"}


@dataclass
class Pose:
    """Where every part of a character is at one moment."""
    x: float
    y: float                   # feet
    sx: float = 1.0            # squash and stretch
    sy: float = 1.0
    rot: float = 0.0           # whole body, degrees (counter-clockwise)
    pivot: tuple = None        # the point the whole body turns around (None = the belly)
    head_rot: float = 0.0
    head_dy: float = 0.0
    ear_l: float = 0.0
    ear_r: float = 0.0
    tail: float = 0.0
    paw_dy: tuple = (0.0, 0.0)
    arm_l: float = None        # None = paw on the ground, a number = arm up at that angle
    arm_r: float = None
    tag: float = 0.0           # the name tag swings (degrees)
    eyes: str = "open"
    mouth: int = 0
    marks: list = field(default_factory=list)  # ("zzz" / "!" / "?" / "hearts", seconds)


def turn(pt, center, deg):
    """Turn a point around a center, the same way PIL turns pictures (counter-clockwise)."""
    a = math.radians(deg)
    dx, dy = pt[0] - center[0], pt[1] - center[1]
    return center[0] + dx * math.cos(a) + dy * math.sin(a), center[1] - dx * math.sin(a) + dy * math.cos(a)


def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def edges(s, d, k=0.25):
    """1 in the middle of a movement, going to 0 at its start and end (so it starts and stops softly)."""
    return clamp(min(s / k, (d - s) / k))


_MARKS = {}


def marks():
    if not _MARKS:
        _MARKS["z"] = [art.text_sprite("Z", size, (120, 150, 255)) for size in (64, 84, 108)]
        _MARKS["!"] = art.text_sprite("!", 130, art.YELLOW)
        _MARKS["?"] = art.text_sprite("?", 130, (120, 190, 255))
        _MARKS["heart"] = art.heart()
    return _MARKS


class Character:
    """The puppy or the kitten, doing the movements it was given."""
    z = 3

    def __init__(self, kind, colors, voice_pitch, seed=0, home=None, size=1.0, name=None):
        """home: (x, y) of the feet on the screen. size: 1.0 = full size (about 500 pixels tall).
        name: written on the tag of its collar (None: its name from NAMES, "": no collar)."""
        self.kind = kind
        self.name = NAMES[kind] if name is None else name
        self.collar = art.collar_parts(kind, self.name) if self.name else None
        self.parts = art.puppy_parts(colors) if kind == "puppy" else art.kitten_parts(colors)
        self.pivots = art.PUPPY_PIVOTS if kind == "puppy" else art.KITTEN_PIVOTS
        self.home, self.ground = home if home else (HOME[kind], GROUND)
        self.side, self.size = SIDE[kind], size
        self.pitch = voice_pitch
        self.moves = []    # (start, end, name, options)
        self.talking = []  # (start, mouth opening for every frame)
        rnd = random.Random(seed)
        self.phase = rnd.uniform(0, 2 * math.pi)
        self.blinks, t = [], rnd.uniform(1.0, 2.5)
        while t < 3600:
            self.blinks.append(t)
            t += rnd.uniform(2.4, 4.4)

    def say(self, voice, text):
        """This character's voice: the AI voice made higher, at normal speed."""
        return voice.say(text, slow=1.05 * 2 ** (self.pitch / 12), pitch=self.pitch)

    def add(self, start, end, name, options):
        self.moves.append((start, end, name, options))

    def act(self, move, at, seconds=None, options=()):
        """Do a movement (a name from MOVES) at time `at`. Returns the time when it ends."""
        end = at + (seconds or MOVES[move].length)
        self.add(at, end, move, list(options))
        return end

    def visible(self, t):
        walks = sorted(m for m in self.moves if m[2] in ("walk_in", "walk_out"))
        before = [m for m in walks if m[0] <= t]
        if before:
            start, end, name, _ = before[-1]
            return not (name == "walk_out" and t >= end)
        first = min(self.moves, default=None)
        return not (first and first[2] == "walk_in")

    def pose(self, t):
        p = Pose(self.home, self.ground)
        breath = math.sin(2 * math.pi * 0.9 * t + self.phase)
        p.sy *= 1 + 0.012 * breath
        p.sx *= 1 - 0.008 * breath
        p.tail = 6 * math.sin(2 * math.pi * 0.7 * t + self.phase)
        if any(b <= t < b + 0.13 for b in self.blinks):
            p.eyes = "blink"
        for start, end, name, options in self.moves:
            if start <= t < end:
                MOVES[name].pose(self, p, t - start, end - start, options)
        # The tag hangs down when the body rocks a little, and swings softly.
        p.tag = 4 * math.sin(2 * math.pi * 0.9 * t + self.phase) - (0.7 * p.rot if abs(p.rot) < 30 else 0)
        for start, levels in self.talking:
            k = int((t - start) * FPS)
            if 0 <= k < len(levels) and levels[k]:
                p.mouth = max(p.mouth, int(levels[k]))
                p.head_rot += 2.5 * math.sin(2 * math.pi * 3 * t)
        return p

    def draw(self, fr, t):
        if self.visible(t):
            self.draw_pose(fr, self.pose(t))

    def draw_pose(self, fr, p):
        k = self.size
        sx, sy = p.sx * k, p.sy * k
        # Movements are in full-size pixels; a smaller character moves less.
        px, py = self.home + (p.x - self.home) * k, self.ground + (p.y - self.ground) * k
        feet, center = art.PET_FEET, p.pivot or art.PET_BODY_CENTER
        spin = (feet[0] + (center[0] - feet[0]) * sx, feet[1] + (center[1] - feet[1]) * sy)

        def world(pt):  # a point of the character picture -> a point on the screen
            x = feet[0] + (pt[0] - feet[0]) * sx
            y = feet[1] + (pt[1] - feet[1]) * sy
            x, y = turn((x, y), spin, p.rot)
            return x - feet[0] + px, y - feet[1] + py

        head_pivot = self.pivots["head"]

        def on_head(pt):  # a point that moves with the head
            x, y = turn(pt, head_pivot, p.head_rot)
            return x, y + p.head_dy

        def put(part, pivot, at, rot=0.0):  # `at`: where the part's pivot is in the character picture
            x, y = world(at)
            place(fr, part.img, x, y, sx, sy, p.rot + rot, part.anchor(pivot))

        raised = []  # arms that are up go in front of the head and ears
        for name in art.PART_ORDER:
            if name not in self.parts:
                continue  # the kitten's ears are part of its head
            pivot = self.pivots[name]
            if name == "head":
                if self.collar:  # the collar goes around the neck, under the head
                    collar, tag = self.collar
                    put(collar, art.COLLAR_PIVOT, art.COLLAR_PIVOT)
                    put(tag, art.TAG_PIVOT, art.TAG_PIVOT, p.tag)
                put(self.parts["head"][(p.eyes, p.mouth)], pivot, (pivot[0], pivot[1] + p.head_dy), p.head_rot)
            elif name.startswith("ear"):
                put(self.parts[name], pivot, on_head(pivot), p.head_rot + (p.ear_l if name == "ear_l" else p.ear_r))
            elif name.startswith("paw"):
                side = name[-1]
                arm = p.arm_l if side == "l" else p.arm_r
                if arm is None:
                    put(self.parts[name], pivot, (pivot[0], pivot[1] + p.paw_dy[0 if side == "l" else 1]))
                else:
                    raised.append(("arm_" + side, arm))
            else:
                put(self.parts[name], pivot, pivot, p.tail if name == "tail" else 0.0)
        for name, arm in raised:
            put(self.parts[name], self.pivots[name], self.pivots[name], arm)
        self.draw_marks(fr, p, world(on_head((300, 80))), world(on_head(MARK_SPOT)))

    def draw_marks(self, fr, p, top, spot):
        m, k = marks(), self.size
        big = 0.4 + 0.6 * k  # marks shrink less than the character, so they stay easy to see
        for kind, age in p.marks:
            if kind == "zzz":
                for i, (spr, anchor) in enumerate(m["z"]):
                    a = age - i * 0.55
                    if a < 0:
                        continue
                    a %= 1.65
                    grow = (0.4 + 0.6 * clamp(a / 0.5)) * (1 - clamp((a - 1.2) / 0.45))
                    place(fr, spr, spot[0] + k * (40 * a + 12 * math.sin(3 * a)), spot[1] - k * 80 * a, big * grow,
                          anchor=anchor)
            elif kind in ("!", "?"):
                spr, anchor = m[kind]
                place(fr, spr, spot[0], spot[1] + k * 6 * math.sin(6 * age),
                      big * ease_out_back(clamp(age / 0.3), 2.5), rot=8 * math.sin(4 * age), anchor=anchor)
            elif kind == "hearts":
                for i in range(3):
                    a = age - i * 0.25
                    if 0 <= a < 1.2:
                        grow = (0.5 + 0.5 * clamp(a / 0.3)) * (1 - clamp((a - 0.8) / 0.4))
                        place(fr, m["heart"], top[0] + k * ((i - 1) * 100 + 20 * math.sin(3 * a + i)),
                              top[1] + k * (60 - 130 * a), big * grow)


# ---------- the movements ----------

def walk(entering):
    def pose(ch, p, s, d, options):
        side = next((o for o in options if o in ("left", "right")), ch.side)
        edge = -300 * ch.size if side == "left" else W + 300 * ch.size  # just off the screen
        far = ch.home + (edge - ch.home) / ch.size  # in full-size pixels, like all movements
        x0, x1 = (far, ch.home) if entering else (ch.home, far)
        u = clamp(s / d)
        p.x = x0 + (x1 - x0) * (1 - (1 - u) ** 2 if entering else u * u)
        swing = clamp((d - s) / 0.3) if entering else clamp(s / 0.3)
        step = 2 * math.pi * 2.2 * s  # a waddle: rock from side to side
        p.rot += 7 * math.sin(step) * swing
        p.y -= 16 * abs(math.sin(step)) * swing
        lift = 12 * math.sin(step) * swing
        p.paw_dy = (-max(0.0, lift), -max(0.0, -lift))
    return pose


def walk_sounds(ch, start, d, options):
    return [(start + k / 4.4, sound.sfx_step(), 0.25) for k in range(1, int(d * 4.4))]


def jump(ch, p, s, d, options):
    u = s / d
    if u < 0.2:  # get ready
        q = math.sin(math.pi * u / 0.2)
        p.sy *= 1 - 0.12 * q
        p.sx *= 1 + 0.1 * q
    elif u < 0.75:  # in the air, arms up
        q = math.sin(math.pi * (u - 0.2) / 0.55)
        p.y -= 190 * q
        p.sy *= 1 + 0.07 * q
        p.sx *= 1 - 0.05 * q
        p.ear_l, p.ear_r = -24 * q, 24 * q
        p.arm_l = p.arm_r = 0.0
        p.eyes, p.mouth = "happy", max(p.mouth, 3)
    else:  # land
        q = math.sin(math.pi * (u - 0.75) / 0.25)
        p.sy *= 1 - 0.1 * q
        p.sx *= 1 + 0.08 * q


def happy(ch, p, s, d, options):
    h = abs(math.sin(2 * math.pi * s / d))  # two little hops
    p.y -= 55 * h
    p.sy *= 1 + 0.05 * h
    p.sx *= 1 - 0.035 * h
    p.eyes, p.mouth = "happy", max(p.mouth, 2)
    p.tail = 28 * math.sin(2 * math.pi * 5 * s)
    p.marks.append(("hearts", s))


def surprised(ch, p, s, d, options):
    u = s / d
    p.eyes, p.mouth = "wide", max(p.mouth, 4 if u < 0.6 else 1)
    if s < 0.3:
        q = math.sin(math.pi * s / 0.3)
        p.y -= 60 * q
        p.sy *= 1 + 0.08 * q
    p.ear_l, p.ear_r = -30 * (1 - u), 30 * (1 - u)
    p.tail = 20 * (1 - u)
    p.marks.append(("!", s))


def sleep(ch, p, s, d, options):
    k = edges(s, d, 0.4)  # falls asleep, then wakes up
    if 0.25 < s < d - 0.25:
        p.eyes = "blink"
    b = math.sin(2 * math.pi * 0.45 * s)
    p.sy *= 1 + 0.03 * b * k
    p.sx *= 1 - 0.02 * b * k
    p.head_rot += 10 * k * (-1 if ch.side == "left" else 1)  # heads lean toward each other
    p.head_dy += 12 * k
    p.tail *= 0.3
    if 0.3 < s < d - 0.25:
        p.marks.append(("zzz", s - 0.3))


def dance(ch, p, s, d, options):
    k = edges(s, d, 0.2)
    p.rot += 9 * math.sin(2 * math.pi * s) * k
    p.y -= 26 * abs(math.sin(2 * math.pi * s)) * k
    wiggle = math.sin(2 * math.pi * 2 * s)  # both arms sway to one side, then to the other
    p.arm_l, p.arm_r = 8 + 20 * wiggle, -8 + 20 * wiggle
    p.head_rot += 7 * math.sin(2 * math.pi * 2 * s + 0.5) * k
    p.tail = 25 * math.sin(2 * math.pi * 4 * s)
    p.eyes, p.mouth = "happy", max(p.mouth, 2)


def roll(ch, p, s, d, options):
    u = s / d
    way = next((o for o in options if o in ("left", "right")), "left" if ch.side == "right" else "right")
    if u < 0.18:  # get ready
        q = math.sin(math.pi * u / 0.18)
        p.sy *= 1 - 0.12 * q
        p.sx *= 1 + 0.1 * q
    elif u < 0.82:  # a somersault in the air, curled up a little
        q = (u - 0.18) / 0.64
        tuck = 1 - 0.12 * math.sin(math.pi * q)
        p.sx *= tuck
        p.sy *= tuck
        p.pivot = ROLL_PIVOT
        p.y -= 220 * math.sin(math.pi * q)
        p.rot += (1 if way == "left" else -1) * 360 * smooth(q)
        p.eyes = "happy"
    else:  # land
        q = math.sin(math.pi * (u - 0.82) / 0.18)
        p.sy *= 1 - 0.1 * q
        p.sx *= 1 + 0.08 * q


def wag_tail(ch, p, s, d, options):
    k = edges(s, d, 0.2)
    p.tail = 34 * math.sin(2 * math.pi * 6 * s) * k
    p.rot += 2.5 * math.sin(2 * math.pi * 6 * s + 1.2) * k  # the whole bottom wiggles
    p.eyes, p.mouth = "happy", max(p.mouth, 2)


def swish_tail(ch, p, s, d, options):
    k = edges(s, d, 0.3)
    p.tail = 28 * math.sin(2 * math.pi * 1.4 * s) * k
    p.head_rot += 4 * math.sin(2 * math.pi * 1.4 * s - 1) * k


def flop_ears(ch, p, s, d, options):
    fade = 1 - s / d
    p.head_rot += 14 * math.sin(2 * math.pi * 5 * s) * fade  # shakes the head, the ears swing after it
    swing = -30 * math.sin(2 * math.pi * 5 * s - 0.9) * fade
    p.ear_l += swing
    p.ear_r += swing
    if s < 0.7 * d:
        p.eyes = "blink"


def head_tilt(ch, p, s, d, options):
    k = smooth(s / 0.35) * (1 - smooth((s - (d - 0.35)) / 0.35))
    p.head_rot += 16 * k * (-1 if ch.side == "left" else 1)
    if 0.3 < s < d - 0.2:
        p.marks.append(("?", s - 0.3))


def wave(ch, p, s, d, options):
    angle = 22 * math.sin(2 * math.pi * 2.5 * s)
    if ch.side == "left":
        p.arm_l = angle
    else:
        p.arm_r = angle
    p.eyes, p.mouth = "happy", max(p.mouth, 2)
    p.head_rot += 5 * math.sin(2 * math.pi * 1.25 * s)


def talk(ch, p, s, d, options):
    pass  # the mouth follows the voice (see Character.pose)


@dataclass
class Move:
    pose: callable
    length: float          # seconds (for "say": as long as the voice)
    about: str             # what it looks like
    sounds: callable = None
    timed: bool = False    # the scene can give it a length, like "2s"


def at_parts(*items):
    """Sounds at parts of the movement: (0.75, sound, loudness) = when 75% of it is done."""
    return lambda ch, start, d, options: [(start + k * d, make(), gain) for k, make, gain in items]


def at_times(*items):
    """Sounds at seconds after the movement starts: (0.3, sound, loudness)."""
    return lambda ch, start, d, options: [(start + k, make(), gain) for k, make, gain in items]


MOVES = {
    "walk_in": Move(walk(True), 1.6, "waddles in from the side (left / right)", walk_sounds),
    "walk_out": Move(walk(False), 1.6, "waddles out to the side (left / right)", walk_sounds),
    "say": Move(talk, 0.0, 'talks: say "Hello!"'),
    "jump": Move(jump, 0.9, "jumps with both arms up",
                 at_parts((0.2, sound.sfx_boing, 0.3), (0.75, sound.sfx_thump, 0.35))),
    "happy": Move(happy, 1.4, "happy eyes, two little hops, hearts", at_times((0.0, sound.sfx_sparkle, 0.35))),
    "surprised": Move(surprised, 1.3, 'big eyes, jumps back, "!"',
                      at_times((0.0, sound.sfx_pop, 0.35), (0.03, lambda: sound.sfx_boop(84), 0.3))),
    "sleep": Move(sleep, 3.0, 'closes its eyes, "Zzz"',
                  at_times((0.0, lambda: sound.marimba(79, 0.9), 0.15), (0.3, lambda: sound.marimba(76, 0.9), 0.15),
                          (0.6, lambda: sound.marimba(72, 0.9), 0.15)), timed=True),
    "dance": Move(dance, 3.0, "sways and bounces, arms up",
                  lambda ch, start, d, o: [(start + k / 2, sound.clap(), 0.12) for k in range(int(d * 2))], timed=True),
    "roll": Move(roll, 1.2, "a somersault in the air (left / right)",
                 at_parts((0.18, sound.sfx_whoosh, 0.3), (0.82, sound.sfx_thump, 0.35))),
    "wag_tail": Move(wag_tail, 2.0, "wags its tail fast, happy", timed=True),
    "swish_tail": Move(swish_tail, 2.0, "swishes its tail slowly", timed=True),
    "flop_ears": Move(flop_ears, 1.2, "shakes its head, the ears swing",
                      lambda ch, start, d, o: [(start + 0.1 * k, sound.shaker(), 0.3) for k in range(5)]),
    "head_tilt": Move(head_tilt, 1.6, 'tilts its head, "?"',
                      at_times((0.1, lambda: sound.sfx_boop(76), 0.25), (0.28, lambda: sound.sfx_boop(81), 0.25))),
    "wave": Move(wave, 2.0, "waves a paw", timed=True),
}
