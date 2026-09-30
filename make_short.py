#!/usr/bin/env python3
"""Make YouTube Shorts (1080x1920) from a video: drop a video, get 2-3 Shorts.

    python3 make_short.py VIDEO                                  # picks 2-3 good parts by itself
    python3 make_short.py VIDEO --start 3:09 --end 3:50 --title "Guess the color!"   # one part you choose

On Windows: drag a video onto make_short.bat.

How the parts are picked: if the video has chapters (in the file, or in a .txt file next to it with lines
like "0:16 Red", such as episode1_youtube.txt), whole chapters of 20-60 seconds become Shorts, and the chapter
name is the title. Other videos: 2-3 parts of about 40 seconds, spread over the video, cut where nobody talks.

Each Short: the whole video in the middle, a big blurry copy of it behind, the title above the video and the
Yumizoo logo below it (not where the YouTube app puts its buttons and words). The Shorts are saved next to
the video.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from kidsvid import art
from kidsvid.anim import place

W, H = 1080, 1920
MAX_SECONDS = 180               # YouTube Shorts can be up to 3 minutes (under 60 seconds is best)
APP_TOP, APP_BOTTOM = 300, 1620  # the YouTube app covers the parts above and below these lines
GAP = 50                        # between the video and the title / logo
STEP = 0.05                     # seconds: how often the sound level is measured


def seconds(text):
    """ "3:09" -> 189, "1:02:03" -> 3723, "75" -> 75."""
    value = 0.0
    for part in text.strip().split(":"):
        value = value * 60 + float(part)
    return value


def clock(s):
    s = round(s, 1)
    return f"{int(s // 60)}:{s % 60:04.1f}"


def video_info(ffmpeg, video):
    """(seconds, width, height, chapters) of a video. chapters: [(start, name)] from the file itself."""
    log = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True,
                         errors="ignore").stderr
    length = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    size = re.search(r"Stream #.*Video:.*?(\d{2,5})x(\d{2,5})", log)
    if not (length and size):
        sys.exit(f"This is not a video file: {video.name}")
    h, m, s = length.groups()
    chapters = [(float(start), name.strip()) for start, name in
                re.findall(r"Chapter #\d+:\d+: start ([\d.]+),.*?\n\s+Metadata:\n\s+title\s+: ([^\n]+)", log)]
    return int(h) * 3600 + int(m) * 60 + float(s), int(size[1]), int(size[2]), chapters


def chapters_from_text(video):
    """Chapters from a .txt file next to the video (like episode1_youtube.txt): lines like "0:16 Red"."""
    if "no_intro" in video.stem:  # the chapter times are for the video with the intro
        return []
    prefix = video.stem.split("_")[0].lower()
    for txt in sorted(video.parent.glob("*.txt")):
        if not txt.stem.lower().startswith(prefix):
            continue
        lines = re.findall(r"^(\d+(?::\d{2}){1,2}) (.+)$", txt.read_text(errors="ignore"), re.M)
        if len(lines) >= 3 and seconds(lines[0][0]) == 0:
            return [(seconds(t), name.strip()) for t, name in lines]
    return []


def sound_levels(ffmpeg, video):
    """How loud the video is, every STEP seconds."""
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-map", "0:a:0?", "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float)
    n = int(8000 * STEP)
    if len(x) < 8000:  # no sound
        return np.zeros(0)
    return np.sqrt(np.mean(x[:len(x) // n * n].reshape(-1, n) ** 2, axis=1))


def quiet_moments(levels):
    """Moments inside quiet parts (0.3 seconds or more, nobody talking): good places to cut."""
    if not len(levels):
        return []
    quiet = levels <= np.percentile(levels, 30)
    moments, run = [], 0
    for k, q in enumerate(np.append(quiet, False)):
        if q:
            run += 1
            continue
        if run * STEP >= 0.3:  # the moments k-run ... k-1 are quiet: take them, but not the edges
            moments += [i * STEP for i in range(k - run + 2, k - 2)]
        run = 0
    return moments


def quietest(levels, a, b):
    """The quietest moment between a and b seconds."""
    i, j = max(0, round(a / STEP)), min(len(levels), round(b / STEP))
    return (i + int(np.argmin(levels[i:j]))) * STEP if j > i else a


def pick_parts(total, chapters, levels, wanted=3, length=40.0):
    """2-3 parts (start, end, title) for Shorts."""
    if chapters:
        ends = [t for t, _ in chapters[1:]] + [total]
        spans = [(a, b, name) for (a, name), b in zip(chapters, ends)][:-1]  # the last chapter is the goodbye
        for shortest in (30, 20):  # chapters of 30-60 seconds make the best Shorts
            good = [(a, b, name if name[-1:] in "!?." else name + "!") for a, b, name in spans
                    if shortest <= b - a <= 60]
            if len(good) >= wanted:
                break
        if len(good) >= 2:
            if len(good) > wanted:  # spread them over the video
                good = [good[round(k * (len(good) - 1) / (wanted - 1))] for k in range(wanted)]
            if all(t == int(t) for t, _ in chapters):
                # Whole seconds (like 1:42 in a .txt): the chapter really starts a little later, somewhere in
                # that second. So cut at the quietest moment of that second (just before the next words), and
                # end at the quietest moment of the second before the next chapter.
                good = [(quietest(levels, a, a + 1) if a else 0.0, quietest(levels, b - 1, b), name)
                        for a, b, name in good]
            return good
    quiet = quiet_moments(levels)
    first, last = min(10.0, total * 0.05), total - min(15.0, total * 0.08)  # not the start and the end
    count = 3 if last - first >= 150 else 2 if last - first >= 70 else 1
    length = min(length, (last - first) / count)
    parts = []
    for k in range(count):
        mid = first + (k + 0.5) * (last - first) / count
        start = min(quiet, key=lambda q: abs(q - (mid - length / 2)), default=mid - length / 2)
        ends = [q for q in quiet if start + 0.7 * length <= q <= start + 1.4 * length]
        end = min(ends, key=lambda q: abs(q - (start + length)), default=start + length)
        parts.append((max(0.0, start), min(total, end), ""))
    return parts


def words_picture(text, width=1000):
    """The words in Yumizoo's rainbow letters (a color name in its own color), as big as fits
    (two lines if it is long)."""
    color = art.COLORS.get(text.strip(" !?.").lower())
    colors = [color] if color else art.RAINBOW
    lines = [text]
    for size in range(120, 44, -4):
        if max(art.font(size).getlength(line) for line in lines) * 1.12 <= width:
            break
        if size <= 72 and len(lines) == 1 and " " in text:  # too long: break it in the middle
            words = text.split()
            cut = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(text) / 2))
            lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    img = Image.new("RGBA", (W, int(size * 1.35 * len(lines) + 40)), (0, 0, 0, 0))
    for k, line in enumerate(lines):
        for spr, anchor, dx in art.title_letters(line, size, colors):
            place(img, spr, W / 2 + dx, size * 1.1 + k * size * 1.3, anchor=anchor)
    return img.crop(img.getbbox())


def make_short(ffmpeg, video, start, end, title, out, size):
    """One Short from `start` to `end` seconds. size: (width, height) of the video."""
    scale = min(W / size[0], H / size[1])
    fw, fh = round(size[0] * scale / 2) * 2, round(size[1] * scale / 2) * 2  # the video in the Short
    top, bottom = (H - fh) // 2, (H + fh) // 2
    pictures = []  # (picture, y)
    if title:
        words = words_picture(title)
        y = max(APP_TOP, top - GAP - words.height)
        if y + words.height <= top:  # (a tall video leaves no room)
            pictures.append((words, y))
    logo = words_picture("Yumizoo", width=520)
    if bottom + GAP + logo.height <= APP_BOTTOM:
        pictures.append((logo, bottom + GAP))
    length = end - start
    fade = min(0.3, length / 4)
    graph = ["[0:v]split=2[back][front]",
             f"[back]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
             f"scale={W // 4}:{H // 4},boxblur=8:2,scale={W}:{H},eq=brightness=-0.06,setsar=1[blur]",
             f"[front]scale={fw}:{fh}[small]",
             "[blur][small]overlay=(W-w)/2:(H-h)/2[v0]"]
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-stats",
           "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(video)]
    with tempfile.TemporaryDirectory() as tmp:
        for k, (picture, y) in enumerate(pictures, 1):
            path = Path(tmp) / f"{k}.png"
            picture.save(path)
            cmd += ["-i", str(path)]
            graph.append(f"[v{k - 1}][{k}:v]overlay=(W-w)/2:{y}[v{k}]")
        cmd += ["-filter_complex", ";".join(graph), "-map", f"[v{len(pictures)}]", "-map", "0:a?",
                "-af", f"afade=t=in:d={fade},afade=t=out:st={length - fade:.3f}:d={fade}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Make YouTube Shorts (1080x1920) from a video.")
    ap.add_argument("video", help="the video file")
    ap.add_argument("--start", help="make one Short from here, like 3:09 (with --end)")
    ap.add_argument("--end", help="where that Short ends, like 3:50")
    ap.add_argument("--title", help="words on top (default: the chapter name, if there are chapters)")
    args = ap.parse_args()
    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"No such video: {video}")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    total, w, h, chapters = video_info(ffmpeg, video)
    print(f"Video: {video.name} ({clock(total)} long, {w}x{h})")
    if args.start and args.end:
        start, end = seconds(args.start), min(seconds(args.end), total)
        if not 0 <= start < end or end - start > MAX_SECONDS:
            sys.exit(f"The end must come after the start, and at most {MAX_SECONDS} seconds later.")
        parts = [(start, end, args.title or "")]
    else:
        chapters = chapters or chapters_from_text(video)
        if chapters:
            print(f"Chapters: {', '.join(name for _, name in chapters)}")
        else:
            print("No chapters: cutting where nobody talks.")
        parts = pick_parts(total, chapters, sound_levels(ffmpeg, video))
        title = args.title
        if title is None and not any(t for _, _, t in parts) and sys.stdin.isatty():
            title = input("\nWords on top of the Shorts, in English (or just press Enter for none): ").strip()
        if title is not None:
            parts = [(a, b, title) for a, b, _ in parts]
    for n, (start, end, title) in enumerate(parts, 1):
        out = video.with_name(f"{video.stem}_short{n}.mp4")
        print(f"\nShort {n} of {len(parts)}: {clock(start)} - {clock(end)} ({end - start:.0f} seconds) {title}")
        make_short(ffmpeg, video, start, end, title, out, (w, h))
        print(f"Saved: {out.name}")
    made = "1 Short is" if len(parts) == 1 else f"{len(parts)} Shorts are"
    print(f"\nDone! {made} next to the video, in {video.resolve().parent}")


if __name__ == "__main__":
    main()
