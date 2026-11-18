#!/usr/bin/env python3
"""Draws the Scopa theme's table dressing into scene.rml.

Three Neapolitan court cards lie face up on the felt (Fante di Denari, Cavallo
di Spade, Re di Coppe), each figure alive with looping animation; a face-down
deck whose top card now and then flips to the Asso di Denari; a faint card-back
lattice woven into the felt; and a decorative band for the divider.

Everything is generated into marked regions of scene.rml, so the art can be
tuned here and re-run:  python3 gen_figures.py   (from this folder)

Draw order: Rive draws the FIRST-declared child on top, so the helpers below
take children back-to-front (painter's order) and reverse them when writing.
"""
import math
import re
from pathlib import Path

INK, IVORY, CREAM = "FF1C1A17", "FFFDFBF4", "FFF7EFD9"
RED, DKRED, GOLD, DKGOLD = "FFD92A2F", "FFA31E22", "FFF2C318", "FFD9A514"
BLUE, GREEN, SKIN, BROWN = "FF2B3A8C", "FF2F8A4C", "FFF5D3B0", "FF8A5A3C"
DKBROWN, HORSE, HORSE2, STEEL = "FF5A3A26", "FFE8C178", "FFD3A75E", "FFD5DCE6"

_next = [1]


def nid():
    _next[0] += 1
    return f"8:{_next[0]}"


# ---- geometry ---------------------------------------------------------------
def _attrs(**kw):
    out = []
    for k, v in kw.items():
        if v is None or (k in ("x", "y", "rotation") and v == 0):
            continue
        if isinstance(v, float):
            v = f"{v:.4f}".rstrip("0").rstrip(".")
        out.append(f'{k}="{v}"')
    return " ".join(out)


def rect(w, h, x=0, y=0, r=0, rot=0):
    return f'<Rectangle {_attrs(x=x, y=y, rotation=rot, width=w, height=h, cornerRadiusTL=r or None)} name="R"/>'


def ell(w, h=None, x=0, y=0, rot=0):
    return f'<Ellipse {_attrs(x=x, y=y, rotation=rot, width=w, height=h if h is not None else w)} name="E"/>'


def tri(w, h, x=0, y=0, rot=0):
    return f'<Triangle {_attrs(x=x, y=y, rotation=rot, width=w, height=h)} name="T"/>'


def star(n, w, inner=0.5, x=0, y=0):
    return f'<Star {_attrs(x=x, y=y, points=n, width=w, height=w, innerRadius=inner)} name="S"/>'


def shape(paths, fill=None, stroke=INK, sw=2.5, name="Shape", x=0, y=0, rot=0, id=None, opacity=None):
    """A Shape: its paths share one fill and one stroke."""
    if isinstance(paths, str):
        paths = [paths]
    a = _attrs(x=x, y=y, rotation=rot, opacity=opacity)
    lines = [f'<Shape {a} name="{name}"{f" id=\"{id}\"" if id else ""}>'.replace("  ", " ")]
    lines += ["    " + p for p in paths]
    if fill:
        lines.append(f'    <Fill name="F"><SolidColor colorValue="{fill}" name="C"/></Fill>')
    if stroke and sw:
        lines.append(f'    <Stroke thickness="{sw}" name="S"><SolidColor colorValue="{stroke}" name="C"/></Stroke>')
    lines.append("</Shape>")
    return "\n".join(lines)


def node(children, name="Node", x=0, y=0, rot=0, sx=None, sy=None, id=None, opacity=None):
    """A group. `children` is back-to-front; written front-first for Rive."""
    a = _attrs(x=x, y=y, rotation=rot, scaleX=sx, scaleY=sy, opacity=opacity)
    lines = [f'<Node {a} name="{name}"{f" id=\"{id}\"" if id else ""}>'.replace("  ", " ")]
    for c in reversed(children):
        lines += ["    " + ln for ln in c.split("\n")]
    lines.append("</Node>")
    return "\n".join(lines)


# ---- animation ----------------------------------------------------------------
EASE = '<CubicEaseInterpolator x1="0.42" y1="0" x2="0.58" y2="1"/>'


def keys(prop, frames):
    """frames: [(frame, value, interp)] with interp in hold/linear/ease."""
    out = [f'    <KeyedProperty property="{prop}">']
    for f, v, how in frames:
        if how == "ease":
            out.append(f'        <KeyFrameDouble frame="{f}" value="{v}" interpolationType="cubic">{EASE}</KeyFrameDouble>')
        else:
            out.append(f'        <KeyFrameDouble frame="{f}" value="{v}" interpolationType="{how}"/>')
    out.append("    </KeyedProperty>")
    return out


def anim(name, id, duration, tracks, loop=True):
    """tracks: {object_id: {prop: frames}}"""
    lp = ' loopValue="loop"' if loop else ""
    out = [f'<LinearAnimation duration="{duration}"{lp} name="{name}" id="{id}">']
    for oid, props in tracks.items():
        out.append(f'    <KeyedObject objectId="{oid}">')
        for prop, frames in props.items():
            out += ["    " + ln for ln in keys(prop, frames)]
        out.append("    </KeyedObject>")
    out.append("</LinearAnimation>")
    return "\n".join(out)


def swing(period, a, b, phase=0):
    """A smooth back-and-forth a→b→a over `period` frames (eased), starting at `phase`."""
    h = period // 2
    pts = [(0, a), (h, b), (period, a)]
    if phase:
        pts = [(0, a), (phase, a), (phase + h, b), (phase + period, a)]
    return [(f, v, "ease") for f, v in pts]


def blink(duration, at, prop_rest=1):
    return [(0, prop_rest, "hold"), (at, prop_rest, "linear"), (at + 5, 0.1, "linear"),
            (at + 10, prop_rest, "hold"), (duration, prop_rest, "hold")]


# ================================================================================
# Figures. Design space: a court card 220x340 centred on 0,0, y down.
# ================================================================================
ID = {}


def king():
    for k in ("KingHead", "KingEyes", "KingCrown", "Sceptre"):
        ID[k] = nid()
    collar_dots = [ell(4, 4, x, -32) for x in (-30, -15, 0, 15, 30)]
    cup = node([
        shape(ell(26, 8, 0, 28), GOLD, name="Base"),
        shape(rect(6, 18, 0, 17), GOLD, sw=2, name="Stem"),
        shape(ell(42, 30, 0, 0), GOLD, name="Bowl"),
        shape(ell(42, 9, 0, -12), DKGOLD, sw=2, name="Lip"),
        shape(ell(8, 8, -8, 2), RED, sw=0, name="Gem"),
    ], name="Cup", x=-60, y=4)
    sceptre = node([
        shape(rect(22, 60, 8, 28, 11, -0.25), RED, name="Arm"),
        shape(rect(7, 132, 18, 6), GOLD, sw=2, name="Rod"),
        shape(star(6, 30, 0.5, 18, -64), GOLD, sw=2, name="Finial"),
        shape(ell(10, 10, 18, -64), RED, sw=0, name="Ruby"),
        shape(ell(20, 18, 17, 54), SKIN, sw=2, name="Hand"),
    ], name="SceptreArm", x=38, y=-22, id=ID["Sceptre"])
    head = node([
        shape(rect(18, 14, 0, -2), SKIN, sw=0, name="Neck"),
        shape(ell(60, 44, 0, -34), BROWN, name="Hair"),
        shape(ell(46, 54, 0, -30), SKIN, name="Face"),
        shape(ell(7, 11, 0, -30), "FFE7B48C", sw=0, name="Nose"),
        shape(ell(52, 40, 0, -10), BROWN, name="Beard"),
        shape([ell(16, 8, -8, -22, 0.15), ell(16, 8, 8, -22, -0.15)], DKBROWN, sw=0, name="Moustache"),
        node([shape([ell(6, 8, -10, 0), ell(6, 8, 10, 0)], INK, sw=0, name="Pupils")], name="Eyes", y=-38, id=ID["KingEyes"]),
        node([
            shape([tri(16, 24, -16, -13), tri(16, 28, 0, -16), tri(16, 24, 16, -13)], GOLD, sw=2, name="Points"),
            shape(rect(54, 14, 0, 0, 3), GOLD, sw=2, name="Band"),
            shape([ell(7, 7, -15, 0), ell(7, 7, 15, 0)], RED, sw=0, name="Rubies"),
            shape(ell(8, 8, 0, 0), BLUE, sw=0, name="Sapphire"),
        ], name="Crown", y=-60, id=ID["KingCrown"]),
    ], name="Head", y=-40, id=ID["KingHead"])
    return node([
        shape(rect(150, 196, 0, -24, 14), RED, name="Throne"),
        shape(rect(130, 176, 0, -24, 10), None, stroke=GOLD, sw=2, name="ThroneTrim"),
        shape([ell(22, 22, -70, -120), ell(22, 22, 70, -120)], GOLD, name="Finials"),
        shape(rect(172, 26, 0, 60, 8), BROWN, name="Seat"),
        shape(rect(118, 88, 0, 98, 14), BLUE, name="Robe"),
        shape([ell(30, 14, -28, 140), ell(30, 14, 28, 140)], INK, sw=0, name="Feet"),
        shape(rect(94, 98, 0, 14, 22), RED, name="Torso"),
        shape(rect(16, 96, 0, 14), IVORY, sw=2, name="Ermine"),
        shape(rect(94, 10, 0, 42), GOLD, sw=2, name="Belt"),
        shape(rect(22, 58, -50, 2, 11, 0.4), RED, name="CupArm"),
        cup,
        shape(ell(20, 18, -58, 26), SKIN, sw=2, name="CupHand"),
        shape(rect(98, 18, 0, -32, 9), IVORY, name="Collar"),
        shape(collar_dots, INK, sw=0, name="Spots"),
        sceptre,
        head,
    ], name="Re")


def knight():
    for k in ("Horse", "HorseHead", "Tail", "Plume", "LegB1", "LegB2", "LegF1", "LegF2", "Rider", "KnightEye"):
        ID[k] = nid()

    def leg(k, x, colour):
        return node([
            shape(rect(13, 58, 0, 27, 6), colour, name="Leg"),
            shape(ell(16, 9, 0, 57), INK, sw=0, name="Hoof"),
        ], name=k, x=x, y=16, id=ID[k])

    rider = node([
        shape(rect(18, 52, 8, 30, 8, -0.15), BLUE, name="Leg"),
        shape(ell(24, 12, 13, 56), INK, sw=0, name="Boot"),
        shape(rect(42, 58, 0, -6, 12), BLUE, name="Torso"),
        shape(rect(28, 22, 0, -12, 6), GOLD, sw=2, name="Breastplate"),
        shape(rect(12, 10, 0, -38), SKIN, sw=0, name="Neck"),
        shape(ell(28, 32, 2, -52), SKIN, name="Face"),
        node([shape(ell(4, 6), INK, sw=0, name="Pupil")], name="Eye", x=9, y=-54, id=ID["KnightEye"]),
        node([
            shape(ell(14, 46, -10, -16, -0.6), RED, name="PlumeA"),
            shape(ell(10, 34, -2, -20, -0.3), GOLD, sw=2, name="PlumeB"),
        ], name="Plume", x=-2, y=-74, id=ID["Plume"]),
        shape(ell(36, 24, 1, -64), GOLD, name="Helmet"),
        shape(rect(30, 5, 4, -58, 2), INK, sw=0, name="Visor"),
        shape(rect(36, 12, 16, 4, 6), BLUE, name="SwordArm"),
        shape(rect(7, 100, 36, -46), STEEL, sw=2, name="Blade"),
        shape(rect(28, 6, 36, 2, 2), GOLD, sw=1.8, name="Guard"),
        shape(ell(15, 15, 36, 8), SKIN, sw=2, name="Fist"),
        shape(ell(8, 8, 36, 18), GOLD, sw=1.6, name="Pommel"),
    ], name="Rider", x=-10, y=-34, id=ID["Rider"])

    head = node([
        shape(tri(11, 20, 4, -14, 0.3), HORSE, sw=2, name="Ear"),
        shape(rect(62, 28, 20, 12, 13, 0.95), HORSE, name="Muzzle"),
        shape(ell(6, 6, 10, 0), INK, sw=0, name="Eye"),
        shape(ell(4, 4, 38, 34), INK, sw=0, name="Nostril"),
        shape(rect(4, 34, 22, 14, 2, 0.95), RED, sw=0, name="Bridle"),
    ], name="Head", x=70, y=-62, id=ID["HorseHead"])

    horse = node([
        leg("LegB2", -30, HORSE2), leg("LegF2", 58, HORSE2),
        leg("LegB1", -48, HORSE), leg("LegF1", 42, HORSE),
        node([shape(ell(18, 58, -8, 24, 0.45), DKBROWN, name="Hair")], name="Tail", x=-74, y=-12, id=ID["Tail"]),
        shape(ell(156, 66), HORSE, name="Body"),
        shape(rect(36, 72, 60, -34, 16, 0.55), HORSE, name="Neck"),
        shape(ell(14, 62, 50, -46, 0.55), RED, name="Mane"),
        head,
        shape(rect(68, 46, -8, -4, 8), RED, name="Caparison"),
        shape(rect(56, 34, -8, -4, 5), None, stroke=GOLD, sw=2, name="Trim"),
        rider,
    ], name="Horse", x=-12, y=52, id=ID["Horse"])
    return node([horse], name="Cavallo")


def knave():
    for k in ("KnaveHead", "KnaveEyes", "Hat", "Feather", "WaveArm", "Coin"):
        ID[k] = nid()
    coin = node([
        shape(ell(50, 50), GOLD, name="Coin"),
        shape(star(8, 30, 0.55), None, stroke=INK, sw=1.4, name="Sun"),
        shape(ell(9, 9), RED, sw=0, name="Core"),
    ], name="Coin", x=-50, y=58, id=ID["Coin"])
    head = node([
        shape(rect(14, 12, 0, 0), SKIN, sw=0, name="Neck"),
        shape(ell(50, 48, 0, -20), BROWN, name="Hair"),
        shape(ell(38, 44, 0, -24), SKIN, name="Face"),
        node([shape([ell(5, 7, -8, 0), ell(5, 7, 8, 0)], INK, sw=0, name="Pupils")], name="Eyes", y=-28, id=ID["KnaveEyes"]),
        shape(rect(10, 3, 0, -12, 1.5), DKRED, sw=0, name="Mouth"),
        node([
            node([shape(ell(12, 54, 10, -22, 0.6), GOLD, sw=2, name="Plume")], name="Feather", x=14, y=-16, id=ID["Feather"]),
            shape(rect(40, 26, 2, -11, 10), RED, name="Crown"),
            shape(ell(80, 16, 0, 2), RED, name="Brim"),
            shape(rect(40, 5, 2, -4), GOLD, sw=0, name="Band"),
        ], name="Hat", y=-46, id=ID["Hat"]),
    ], name="Head", y=-44, id=ID["KnaveHead"])
    wave = node([
        shape(rect(18, 60, 0, 28, 9), GREEN, name="Arm"),
        shape(ell(18, 18, 0, 60), SKIN, sw=2, name="Hand"),
    ], name="WaveArm", x=34, y=-28, rot=0.15, id=ID["WaveArm"])
    return node([
        shape(rect(106, 152, 0, 20, 20), RED, name="Cape"),
        shape(rect(20, 86, -14, 96, 8), GOLD, name="LegL"),
        shape(rect(20, 86, 14, 96, 8), RED, name="LegR"),
        shape([ell(28, 12, -18, 140), ell(28, 12, 18, 140)], INK, sw=0, name="Shoes"),
        shape(tri(114, 66, 0, 64), GREEN, name="Skirt"),
        shape(rect(72, 94, 0, 8, 18), GREEN, name="Tunic"),
        shape(rect(72, 9, 0, 40), GOLD, sw=2, name="Belt"),
        shape([ell(6, 6, 0, -14), ell(6, 6, 0, 2), ell(6, 6, 0, 18)], GOLD, sw=1.2, name="Buttons"),
        shape(rect(18, 60, -40, 0, 9, 0.25), GREEN, name="CoinArm"),
        coin,
        shape(ell(18, 18, -48, 30), SKIN, sw=2, name="CoinHand"),
        wave,
        shape(rect(52, 12, 0, -38, 6), IVORY, sw=2, name="Collar"),
        head,
    ], name="Fante")


def court_card(name, figure, x, y, rot):
    """A face-up court card on the felt: shadow, ivory face, red double frame, figure."""
    return node([
        shape(rect(200, 300, 8, 9, 16), "55000000", stroke=None, name="Shadow"),
        shape(rect(200, 300, 0, 0, 16), IVORY, stroke=RED, sw=3, name="Face"),
        shape(rect(184, 284, 0, 0, 11), None, stroke="88D92A2F", sw=1.2, name="Frame"),
        node([figure], name="Figure", y=4, sx=0.8, sy=0.8),
    ], name=name, x=x, y=y, rot=rot)


# ---- card back ------------------------------------------------------------------
def card_back(w=180, h=270):
    pw, ph = w - 30, h - 30
    s = 25.0
    diamonds = []
    nx, ny = int(pw // s), int(ph // s)
    x0 = -(nx - 1) * s / 2
    y0 = -(ny - 1) * s / 2
    d = s / math.sqrt(2) - 1.5
    for i in range(nx):
        for j in range(ny):
            diamonds.append(rect(round(d, 2), round(d, 2), round(x0 + i * s, 2), round(y0 + j * s, 2), 0, 0.7853982))
    return node([
        shape(rect(w, h, 0, 0, 14), IVORY, stroke=RED, sw=3, name="Card"),
        shape(rect(pw, ph, 0, 0, 8), BLUE, stroke=None, name="Panel"),
        shape(diamonds, None, stroke="CCFDFBF4", sw=1.4, name="Lattice"),
        shape(rect(pw, ph, 0, 0, 8), None, stroke=GOLD, sw=2, name="PanelTrim"),
        shape(ell(66, 88), IVORY, stroke=RED, sw=3, name="Medallion"),
        shape(star(8, 44, 0.5), GOLD, sw=1.6, name="Rose"),
        shape(ell(12, 12), RED, sw=0, name="Heart"),
    ], name="Back")


def ace_of_coins(w=180, h=270):
    return node([
        shape(rect(w, h, 0, 0, 14), IVORY, stroke=RED, sw=3, name="Card"),
        shape(rect(w - 16, h - 16, 0, 0, 9), None, stroke="88D92A2F", sw=1.2, name="Frame"),
        shape(ell(132, 132), None, stroke=RED, sw=3, name="Ring"),
        shape(star(16, 124, 0.82), "FFF7D774", stroke=INK, sw=1.5, name="Rays"),
        shape(ell(104, 104), GOLD, sw=2.5, name="Coin"),
        shape(star(8, 62, 0.5), None, stroke=INK, sw=1.6, name="Sun"),
        shape(ell(20, 20), RED, sw=2, name="Core"),
        shape([ell(14, 14, -62, -104), ell(14, 14, 62, 104)], GOLD, sw=1.5, name="Corners"),
    ], name="Ace")


def deck():
    for k in ("TopCard", "TopBack", "TopFace"):
        ID[k] = nid()
    under = [node([shape(rect(180, 270, 0, 0, 14), "55000000", stroke=None, name="Shadow"), card_back()],
                  name=f"Under{i}", x=dx, y=dy, rot=r)
             for i, (dx, dy, r) in enumerate([(14, 12, 0.06), (7, 6, 0.03)])]
    top = node([
        node([ace_of_coins()], name="FaceSide", id=ID["TopFace"], opacity=0),
        node([card_back()], name="BackSide", id=ID["TopBack"]),
    ], name="TopCard", id=ID["TopCard"])
    return node(under + [top], name="Deck", x=222, y=968, rot=-0.12, sx=0.88, sy=0.88)


# ---- felt lattice -----------------------------------------------------------------
def felt_lattice():
    paths = []
    step = 96
    for c in range(-1200, 3200, step):
        paths.append(rect(1.5, 2800, c, 540, 0, 0.7853982))
        paths.append(rect(1.5, 2800, c, 540, 0, -0.7853982))
    dots = []
    # little rosettes on the crossings near the middle band, like a printed back
    for i in range(-12, 34):
        for j in range(-2, 14):
            x = i * step / 2
            y = 540 + (j - 6) * step / 2
            if (i + j) % 2 == 0 and 0 <= x <= 1920 and 0 <= y <= 1080:
                dots.append(ell(5, 5, x, y))
    return node([
        shape(paths, "12F2C318", stroke=None, name="Lines"),
        shape(dots, "1EF2C318", stroke=None, name="Studs"),
    ], name="FeltLattice")


# ---- divider band -----------------------------------------------------------------
def divider_band(width=1776, h=14):
    cy = h / 2
    buckets = {}
    n = 46
    for k in range(n):
        x = width * (k + 0.5) / n
        t = abs(x / width - 0.5) * 2  # 0 at centre, 1 at ends
        a = max(0.0, 1 - t ** 2)
        b = min(5, int(a * 6))
        buckets.setdefault(b, []).append(x)
    shapes = [shape(rect(width * 0.9, 1.5, width / 2, cy), None, stroke=None, name="Line")]
    shapes[0] = shape(rect(width * 0.9, 1.5, width / 2, cy), "66F2C318", stroke=None, name="Line")
    for b, xs in sorted(buckets.items()):
        if b == 0:
            continue
        alpha = f"{int(255 * b / 5):02X}"
        shapes.append(shape([rect(7, 7, round(x, 1), cy, 1, 0.7853982) for x in xs], alpha + "F2C318",
                            stroke=None, name=f"Diamonds{b}"))
        shapes.append(shape([ell(3.5, 3.5, round(x + width / n / 2, 1), cy) for x in xs[:-1]], alpha + "D92A2F",
                            stroke=None, name=f"Beads{b}"))
    return node(shapes, name="Band")


# ================================================================================
# assemble
# ================================================================================
TABLE = node([
    felt_lattice(),
    deck(),
    court_card("FanteCard", knave(), 1336, 902, -0.07),
    court_card("CavalloCard", knight(), 1556, 896, 0.02),
    court_card("ReCard", king(), 1776, 904, 0.08),
], name="Table")

FPS = 60
I = ID


def anims():
    a = []
    # idle: blinks, nods, sways (one track per property; nothing else keys these)
    D = 480
    a.append(anim("Court Idle", "8:900", D, {
        I["KingEyes"]: {"scaleY": blink(D, 140)},
        I["KnaveEyes"]: {"scaleY": blink(D, 300)},
        I["KnightEye"]: {"scaleY": blink(D, 410)},
        I["KingHead"]: {"rotation": swing(D, -0.035, 0.035)},
        I["KingCrown"]: {"y": swing(D // 2, -60, -63) + [(D, -60, "hold")]},
        I["HorseHead"]: {"rotation": swing(D // 4, 0, 0.09) + [(D, 0, "hold")]},
        I["Tail"]: {"rotation": swing(D // 3, -0.12, 0.18) + [(D, -0.12, "hold")]},
        I["Plume"]: {"rotation": swing(D // 2, -0.1, 0.12) + [(D, -0.1, "hold")]},
        I["Feather"]: {"rotation": swing(D // 2, 0.08, -0.14, 60) + [(D, 0.08, "hold")]},
        I["KnaveHead"]: {"rotation": swing(D, 0.03, -0.03)},
    }))
    # the knave greets: lifts his hat and waves, every 10 s
    D = 600
    up, wav = 380, 400
    a.append(anim("Fante Greet", "8:901", D, {
        I["WaveArm"]: {"rotation": [(0, 0.15, "hold"), (up, 0.15, "ease"), (wav, -2.55, "ease"),
                                    (wav + 14, -2.25, "ease"), (wav + 28, -2.6, "ease"), (wav + 42, -2.25, "ease"),
                                    (wav + 56, -2.55, "ease"), (wav + 80, 0.15, "hold"), (D, 0.15, "hold")]},
        I["Hat"]: {"y": [(0, -46, "hold"), (up - 10, -46, "ease"), (up + 12, -60, "ease"),
                         (wav + 60, -60, "ease"), (wav + 84, -46, "hold"), (D, -46, "hold")],
                   "rotation": [(0, 0, "hold"), (up - 10, 0, "ease"), (up + 12, -0.28, "ease"),
                                (wav + 60, -0.28, "ease"), (wav + 84, 0, "hold"), (D, 0, "hold")]},
    }))
    # the coin he holds turns over now and then
    D = 300
    a.append(anim("Coin Turn", "8:902", D, {
        I["Coin"]: {"scaleX": [(0, 1, "hold"), (200, 1, "ease"), (225, -1, "ease"), (250, 1, "hold"), (D, 1, "hold")]},
    }))
    # the deck's top card flips to the Ace of Coins and back
    D = 840
    f1, f2 = 480, 640
    a.append(anim("Deck Flip", "8:903", D, {
        I["TopCard"]: {
            "scaleX": [(0, 1, "hold"), (f1, 1, "linear"), (f1 + 12, 0.02, "linear"), (f1 + 24, 1, "hold"),
                       (f2, 1, "linear"), (f2 + 12, 0.02, "linear"), (f2 + 24, 1, "hold"), (D, 1, "hold")],
            "y": [(0, 0, "hold"), (f1 - 8, 0, "ease"), (f1 + 6, -14, "ease"), (f1 + 30, 0, "hold"),
                  (f2 - 8, 0, "ease"), (f2 + 6, -14, "ease"), (f2 + 30, 0, "hold"), (D, 0, "hold")],
        },
        I["TopBack"]: {"opacity": [(0, 1, "hold"), (f1 + 12, 0, "hold"), (f2 + 12, 1, "hold"), (D, 1, "hold")]},
        I["TopFace"]: {"opacity": [(0, 0, "hold"), (f1 + 12, 1, "hold"), (f2 + 12, 0, "hold"), (D, 0, "hold")]},
    }))
    # music: at rest, still; while something plays the king taps his sceptre and the horse trots
    rest = {I["Sceptre"]: {"rotation": [(0, 0, "hold")]}, I["Horse"]: {"y": [(0, 52, "hold")]},
            I["Rider"]: {"y": [(0, -34, "hold")]}}
    for k in ("LegB1", "LegB2", "LegF1", "LegF2"):
        rest[I[k]] = {"rotation": [(0, 0, "hold")]}
    a.append(anim("Music Rest", "8:904", 1, rest, loop=False))
    P = 32  # one beat, ~112 bpm
    play = {
        I["Sceptre"]: {"rotation": [(0, 0, "ease"), (8, -0.2, "ease"), (16, 0.02, "ease"), (P, 0, "hold")]},
        I["Horse"]: {"y": [(0, 52, "ease"), (P // 4, 46, "ease"), (P // 2, 52, "ease"),
                           (3 * P // 4, 46, "ease"), (P, 52, "hold")]},
        I["Rider"]: {"y": [(0, -34, "ease"), (P // 4, -36, "ease"), (P // 2, -34, "ease"),
                           (3 * P // 4, -36, "ease"), (P, -34, "hold")]},
    }
    for k, ph in (("LegB1", 0), ("LegF2", 0), ("LegB2", 1), ("LegF1", 1)):
        a_, b_ = (0.32, -0.32) if ph == 0 else (-0.32, 0.32)
        play[I[k]] = {"rotation": [(0, a_, "ease"), (P // 2, b_, "ease"), (P, a_, "hold")]}
    a.append(anim("Music Play", "8:905", P, play))
    return "\n".join(a)


def layers():
    def simple(name, lid, sid, aid):
        return f'''<StateMachineLayer name="{name}" id="{lid}">
    <AnyState x="200" y="-120"/>
    <ExitState x="400" y="-120"/>
    <EntryState><StateTransition stateToId="{sid}"/></EntryState>
    <AnimationState x="200" animationId="{aid}" id="{sid}"/>
</StateMachineLayer>'''

    def cond(v):
        return f'''        <TransitionViewModelCondition opValue="equal">
            <TransitionPropertyViewModelComparator>
                <BindablePropertyBoolean>
                    <DataBindContext sourcePathIds="4:1-4:7" propertyKey="634"/>
                </BindablePropertyBoolean>
            </TransitionPropertyViewModelComparator>
            <TransitionValueBooleanComparator value="{v}"/>
        </TransitionViewModelCondition>'''
    out = [simple("Court Idle", "8:910", "8:911", "8:900"),
           simple("Fante Greet", "8:912", "8:913", "8:901"),
           simple("Coin Turn", "8:914", "8:915", "8:902"),
           simple("Deck Flip", "8:916", "8:917", "8:903"),
           f'''<StateMachineLayer name="Court Music" id="8:920">
    <AnyState x="200" y="-120"/>
    <ExitState x="400" y="-120"/>
    <EntryState><StateTransition stateToId="8:921"/></EntryState>
    <AnimationState x="100" y="100" animationId="8:904" stateName="Rest" id="8:921">
        <StateTransition stateToId="8:922" duration="250" interpolationType="cubic">
            <CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>
{cond("true")}
        </StateTransition>
    </AnimationState>
    <AnimationState x="300" y="100" animationId="8:905" stateName="Play" id="8:922">
        <StateTransition stateToId="8:921" duration="300" interpolationType="cubic">
            <CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>
{cond("false")}
        </StateTransition>
    </AnimationState>
</StateMachineLayer>''']
    return "\n".join(out)


def indent(text, n):
    return "\n".join((" " * n + ln) if ln else ln for ln in text.split("\n"))


def put(s, tag, body, n):
    pat = re.compile(rf"([ \t]*<!-- {tag}:begin[^>]*-->\n).*?([ \t]*<!-- {tag}:end -->)", re.S)
    assert pat.search(s), tag
    return pat.sub(lambda m: m.group(1) + indent(body, n) + "\n" + m.group(2), s)


if __name__ == "__main__":
    p = Path(__file__).with_name("scene.rml")
    s = p.read_text()
    s = put(s, "table", TABLE, 8)
    s = put(s, "band", divider_band(), 16)
    s = put(s, "court-anims", anims(), 8)
    s = put(s, "court-layers", layers(), 12)
    p.write_text(s)
    print("table dressing written:", _next[0] - 1, "ids")
