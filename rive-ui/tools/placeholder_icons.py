#!/usr/bin/env python3
"""Draws the generic sample icons and album cover the theme previews use.

    python3 tools/placeholder_icons.py

The previews (and the README screenshots) show made-up apps, never a real
install: plain coloured tiles with a simple white symbol. Writes icons/<key>.png
(192 px) and art/cover.png (160 px). The real app always shows the TV's own apps.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
S = 192  # icon size; glyphs are drawn at 4x and scaled down for smooth edges
K = 4
W = "white"


def canvas(c1, c2):
    im = Image.new("RGBA", (S * K, S * K))
    d = ImageDraw.Draw(im)
    for y in range(S * K):  # vertical gradient
        t = y / (S * K)
        d.line([(0, y), (S * K, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    mask = Image.new("L", im.size)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S * K - 1, S * K - 1], 40 * K, fill=255)
    im.putalpha(mask)
    return im, d


def p(*xy):
    return [v * K for v in xy]


def movies(d):
    d.rounded_rectangle(p(46, 80, 146, 146), 8 * K, fill=W)
    d.polygon(p(46, 58, 140, 40, 144, 62, 50, 80), fill=W)
    for x in (66, 94, 122):
        d.polygon(p(x, 52, x + 12, 50, x + 4, 68, x - 8, 70), fill=(230, 80, 70))


def shows(d):
    d.rounded_rectangle(p(40, 54, 152, 128), 12 * K, outline=W, width=10 * K)
    d.rectangle(p(86, 128, 106, 144), fill=W)
    d.rounded_rectangle(p(66, 140, 126, 150), 5 * K, fill=W)


def music(d):
    d.ellipse(p(52, 112, 88, 144), fill=W)
    d.ellipse(p(104, 100, 140, 132), fill=W)
    d.rectangle(p(78, 50, 88, 128), fill=W)
    d.rectangle(p(130, 40, 140, 116), fill=W)
    d.polygon(p(78, 50, 140, 36, 140, 56, 78, 70), fill=W)


def photos(d):
    d.rounded_rectangle(p(40, 50, 152, 142), 12 * K, outline=W, width=9 * K)
    d.polygon(p(52, 132, 88, 88, 112, 116, 124, 102, 142, 132), fill=W)
    d.ellipse(p(116, 64, 136, 84), fill=W)


def games(d):
    d.rounded_rectangle(p(34, 70, 158, 132), 30 * K, fill=W)
    c = (60, 70, 160)
    d.rectangle(p(58, 96, 86, 106), fill=c)
    d.rectangle(p(67, 87, 77, 115), fill=c)
    d.ellipse(p(114, 86, 128, 100), fill=c)
    d.ellipse(p(128, 100, 142, 114), fill=c)


def browser(d):
    d.ellipse(p(44, 44, 148, 148), outline=W, width=9 * K)
    d.ellipse(p(78, 44, 114, 148), outline=W, width=7 * K)
    d.rectangle(p(44, 92, 148, 100), fill=W)


def podcasts(d):
    d.rounded_rectangle(p(78, 40, 114, 112), 18 * K, fill=W)
    d.arc(p(60, 70, 132, 132), 0, 180, fill=W, width=8 * K)
    d.rectangle(p(92, 130, 100, 150), fill=W)


def radio(d):
    d.rounded_rectangle(p(38, 70, 154, 146), 14 * K, fill=W)
    d.line(p(60, 70, 130, 40), fill=W, width=7 * K)
    c = (200, 110, 60)
    d.ellipse(p(54, 86, 100, 132), fill=c)
    d.rounded_rectangle(p(112, 88, 140, 100), 4 * K, fill=c)


def news(d):
    d.rounded_rectangle(p(44, 44, 148, 148), 10 * K, fill=W)
    c = (90, 100, 120)
    d.rectangle(p(58, 60, 134, 76), fill=c)
    for y in (88, 104, 120):
        d.rectangle(p(58, y, 134, y + 7), fill=c)


def weather(d):
    d.ellipse(p(84, 40, 140, 96), fill=(255, 214, 90))
    d.ellipse(p(44, 92, 96, 140), fill=W)
    d.ellipse(p(76, 76, 136, 136), fill=W)
    d.rounded_rectangle(p(44, 112, 152, 142), 15 * K, fill=W)


def sports(d):
    d.ellipse(p(46, 46, 146, 146), fill=W)
    c = (40, 120, 70)
    d.arc(p(46, 46, 146, 146), 0, 360, fill=c, width=3 * K)
    d.line(p(96, 46, 96, 146), fill=c, width=5 * K)
    d.arc(p(20, 46, 120, 146), -60, 60, fill=c, width=5 * K)
    d.arc(p(72, 46, 172, 146), 120, 240, fill=c, width=5 * K)


def kids(d):
    import math
    pts = []
    for i in range(10):
        r = 54 if i % 2 == 0 else 24
        a = -math.pi / 2 + i * math.pi / 5
        pts += [96 + r * math.cos(a), 100 + r * math.sin(a)]
    d.polygon(p(*pts), fill=W)


def files(d):
    d.rounded_rectangle(p(40, 58, 96, 80), 6 * K, fill=W)
    d.rounded_rectangle(p(40, 70, 152, 140), 10 * K, fill=W)


def store(d):
    d.rounded_rectangle(p(46, 74, 146, 150), 12 * K, fill=W)
    d.arc(p(70, 44, 122, 100), 180, 360, fill=W, width=8 * K)


def arcade(d):
    d.rounded_rectangle(p(46, 118, 146, 146), 10 * K, fill=W)
    d.rectangle(p(91, 70, 101, 120), fill=W)
    d.ellipse(p(76, 42, 116, 82), fill=(240, 90, 90))


ICONS = {  # key: (glyph, top colour, bottom colour)
    "movies": (movies, (70, 60, 90), (40, 34, 56)),
    "shows": (shows, (90, 130, 230), (60, 90, 190)),
    "music": (music, (240, 120, 150), (200, 80, 120)),
    "photos": (photos, (80, 190, 170), (40, 150, 140)),
    "games": (games, (120, 130, 240), (80, 90, 210)),
    "browser": (browser, (70, 160, 230), (40, 120, 200)),
    "podcasts": (podcasts, (170, 100, 220), (130, 70, 190)),
    "radio": (radio, (250, 170, 90), (230, 130, 60)),
    "news": (news, (200, 210, 225), (160, 172, 190)),
    "weather": (weather, (110, 180, 240), (70, 140, 220)),
    "sports": (sports, (90, 190, 110), (50, 150, 80)),
    "kids": (kids, (250, 200, 80), (240, 160, 60)),
    "files": (files, (240, 190, 90), (220, 150, 60)),
    "store": (store, (240, 110, 90), (210, 80, 70)),
    "arcade": (arcade, (60, 60, 80), (30, 30, 46)),
}


def cover():
    """A made-up album cover: hills under a sunset."""
    n = 160 * K
    im = Image.new("RGBA", (n, n))
    d = ImageDraw.Draw(im)
    for y in range(n):
        t = y / n
        d.line([(0, y), (n, y)], fill=(int(250 - 60 * t), int(170 - 90 * t), int(120 + 30 * t)))
    d.ellipse([n * 0.3, n * 0.25, n * 0.7, n * 0.65], fill=(255, 220, 130))
    d.ellipse([-n * 0.3, n * 0.55, n * 0.8, n * 1.4], fill=(70, 60, 110))
    d.ellipse([n * 0.3, n * 0.62, n * 1.4, n * 1.5], fill=(45, 40, 80))
    return im.resize((160, 160), Image.LANCZOS)


if __name__ == "__main__":
    for key, (glyph, c1, c2) in ICONS.items():
        im, d = canvas(c1, c2)
        glyph(d)
        im.resize((S, S), Image.LANCZOS).save(ROOT / "icons" / f"{key}.png")
    cover().save(ROOT / "art" / "cover.png")
    print(f"{len(ICONS)} icons and a cover written")
