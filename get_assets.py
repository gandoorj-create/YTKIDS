#!/usr/bin/env python3
"""Download the AI voice and the font. They are not kept in git.

Voice: Piper "jenny_dioco" (British English, female), packed as a Go module (amitybell/piper-voice-jenny).
Font:  Fredoka (SIL Open Font License), from the @fontsource/fredoka npm package.
"""
import io
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

import zstandard
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
VOICE_ZIP = ("https://proxy.golang.org/github.com/amitybell/piper-voice-jenny/"
             "@v/v0.0.0-20231118093224-dcf0d49e46b7.zip")
FONT_TGZ = "https://registry.npmjs.org/@fontsource/fredoka/-/fredoka-5.3.0.tgz"


def download(url):
    for attempt in range(4):
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        if data:  # the Go proxy sometimes sends an empty answer the first time
            return data
        time.sleep(2 ** attempt)
    raise SystemExit(f"Could not download {url}")


def get_voice():
    out = ROOT / "assets" / "voices" / "jenny"
    if (out / "voice.onnx").exists():
        return
    print("Downloading the voice (58 MB)...")
    z = zipfile.ZipFile(io.BytesIO(download(VOICE_ZIP)))
    packed = z.read(next(n for n in z.namelist() if n.endswith("/dist.tzst")))
    tar = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(packed)).read()
    out.mkdir(parents=True, exist_ok=True)
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(out)


def get_font():
    out = ROOT / "assets" / "fonts"
    if (out / "Fredoka-700.ttf").exists():
        return
    print("Downloading the font...")
    out.mkdir(parents=True, exist_ok=True)
    tgz = tarfile.open(fileobj=io.BytesIO(download(FONT_TGZ)))
    for weight in (500, 600, 700):
        font = TTFont(io.BytesIO(tgz.extractfile(f"package/files/fredoka-latin-{weight}-normal.woff2").read()))
        font.flavor = None  # woff2 -> ttf
        font.save(out / f"Fredoka-{weight}.ttf")
    (out / "OFL.txt").write_bytes(tgz.extractfile("package/LICENSE").read())


if __name__ == "__main__":
    get_voice()
    get_font()
    print("Assets ready.")
