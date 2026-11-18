#!/usr/bin/env python3
"""Draws the Scopa theme's table dressing into scene.rml.

Drawn after the real Neapolitan pattern (carte napoletane); see RESEARCH.md.
The cards have no frame and no indices: a white card, a full-length,
single-ended figure standing on a coloured hatched platform, and the suit
sign floating in a top corner.

  - Three court cards face up on the felt: Fante di Coppe (raises his cup in a
    toast), Cavallo di Denari (grey horse walking, rider holding up a coin) and
    Re di Denari (crowned, bearded, sword in hand, coin floating at his side).
  - A table hand in the middle: four cards laid out (the Settebello shimmers).
    Now and then a card is played, a broom (scopa!) sweeps the table clean, and
    the cards are dealt again.
  - The red tuck case, open with cards peeking out, and the deck beside it
    whose top card flips to the Asso di Denari (the double-headed eagle).
  - Tiles: the icon is the "figure": it stands on a hatched platform with the
    suit sign floating in a corner (Denari for favourites, Coppe for apps).
  - A faint card-back lattice in the felt and a band for the divider.

Generated into marked regions of scene.rml:  python3 gen_figures.py

Draw order: Rive draws the FIRST-declared child on top, so the helpers below
take children back-to-front (painter's order) and reverse them when writing.
"""
import math
import re
from pathlib import Path

INK, IVORY, EDGE = "FF1C1A17", "FFFDFBF4", "FF9C968A"
RED, DKRED, GOLD, DKGOLD = "FFD8262C", "FFA31E22", "FFF5C51A", "FFD9A514"
BLUE, LTBLUE, DKBLUE = "FF2348A8", "FF5B8BD6", "FF1A2A6C"
GREEN, DKGREEN = "FF1F7A3A", "FF155A2A"
SKIN, HAIRGREY, WHITE = "FFF6D5B5", "FF9EA9BA", "FFFFFFFF"
HORSE, HORSEDK, MANE = "FFBDB2A4", "FF9C9183", "FF7E7468"
WOOD, WOODDK, STRAW = "FFB0743F", "FF7A4A24", "FFE9C46A"

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


def star(n, w, inner=0.5, x=0, y=0, rot=0):
    return f'<Star {_attrs(x=x, y=y, rotation=rot, points=n, width=w, height=w, innerRadius=inner)} name="S"/>'


def poly(pts, radius=0, closed=True):
    """A custom outline through `pts`; `radius` rounds every corner (clamped by Rive)."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    cw = "true" if area > 0 else "false"  # y points down: positive area runs clockwise on screen
    vs = "".join(f'<StraightVertex x="{round(x, 2)}" y="{round(y, 2)}"{f" radius=\"{radius}\"" if radius else ""}/>'
                 for x, y in pts)
    return f'<PointsPath isClosed="{"true" if closed else "false"}" isClockwise="{cw}" name="P">{vs}</PointsPath>'


def mirror(pts):
    """Close a left-half outline (top to bottom along x<=0) into a symmetric one."""
    return pts + [(-x, y) for x, y in reversed(pts) if x != 0]


def shape(paths, fill=None, stroke=INK, sw=2, name="Shape", x=0, y=0, rot=0, id=None, opacity=None, sx=None, sy=None):
    """A Shape: its paths share one fill and one stroke."""
    if isinstance(paths, str):
        paths = [paths]
    a = _attrs(x=x, y=y, rotation=rot, opacity=opacity, scaleX=sx, scaleY=sy)
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
        v = round(v, 4)
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


def swing(period, a, b, total=None):
    """A smooth a→b→a over `period` frames, repeated to fill `total` frames."""
    total = total or period
    out, f = [], 0
    while f < total:
        out += [(f, a, "ease"), (f + period // 2, b, "ease")]
        f += period
    out.append((total, a, "hold"))
    return out


def blink(duration, at, rest=1):
    return [(0, rest, "hold"), (at, rest, "linear"), (at + 5, 0.1, "linear"),
            (at + 10, rest, "hold"), (duration, rest, "hold")]


ID = {}


def ids(*names):
    for n in names:
        ID[n] = nid()


# ================================================================================
# suit signs (pips), drawn about 0,0 at roughly 40 px across
# ================================================================================
def coin(d=40, name="Coin", id=None, x=0, y=0, rot=0, sx=None):
    """Denaro: an ink-ringed white band round a gold sun-burst disc with a small core."""
    return node([
        shape(ell(d), WHITE, sw=1.6, name="Band"),
        shape(ell(d * 0.78), GOLD, sw=1.4, name="Disc"),
        shape(star(12, d * 0.66, 0.55), "FFFFE27A", sw=1.1, name="Rays"),
        shape(ell(d * 0.22), RED, sw=1.1, name="Core"),
    ], name=name, id=id, x=x, y=y, rot=rot, sx=sx)


def cup(h=44, name="Cup", id=None, x=0, y=0, rot=0, foot=RED):
    """Coppa: a gold chalice, rim band, knop on the stem, red foot."""
    k = h / 44
    bowl = poly([(-15 * k, -20 * k), (15 * k, -20 * k), (13 * k, -8 * k), (6 * k, 0), (-6 * k, 0), (-13 * k, -8 * k)], 3 * k)
    return node([
        shape(poly([(-11 * k, 22 * k), (11 * k, 22 * k), (6 * k, 14 * k), (-6 * k, 14 * k)], 2 * k), foot, sw=1.4, name="Foot"),
        shape(rect(4 * k, 14 * k, 0, 7 * k), GOLD, sw=1.4, name="Stem"),
        shape(ell(10 * k, 6 * k, 0, 6 * k), GOLD, sw=1.4, name="Knop"),
        shape(bowl, GOLD, sw=1.6, name="Bowl"),
        shape(rect(32 * k, 5 * k, 0, -20 * k, 2 * k), DKGOLD, sw=1.4, name="Rim"),
        shape([rect(1.2 * k, 9 * k, x_ * k, -11 * k) for x_ in (-7, -3, 1, 5)], "66000000", stroke=None, name="Hatch"),
    ], name=name, id=id, x=x, y=y, rot=rot)


def sword(h=110, name="Sword", id=None, x=0, y=0, rot=0):
    """Spada (Neapolitan: short and straight): a pale blade, gold guard and pommel, red grip. Hilt at 0,0."""
    return node([
        shape(poly([(-2.5, 6), (2.5, 6), (2, h - 8), (0, h), (-2, h - 8)]), "FFE6ECF2", sw=1.4, name="Blade"),
        shape(rect(24, 5, 0, 4, 2), GOLD, sw=1.4, name="Guard"),
        shape(rect(5, 14, 0, -6, 2), RED, sw=1.2, name="Grip"),
        shape(ell(8, 8, 0, -15), GOLD, sw=1.2, name="Pommel"),
    ], name=name, id=id, x=x, y=y, rot=rot)


def platform(w, color, y, h=12, boxes=False):
    """The coloured ground each figure stands on, shaded with fine hatching."""
    hatch = [rect(1.2, h - 3, round(-w / 2 + 6 + i * 6, 1), y) for i in range(int((w - 10) / 6))]
    parts = [shape(rect(w, h, 0, y), color, sw=1.6, name="Ground"),
             shape(hatch, "55000000", stroke=None, name="Hatch")]
    if boxes:
        parts.append(shape([rect(w / 4 - 8, h - 5, -w / 2 + (i + 0.5) * w / 4, y, 1) for i in range(4)], None,
                           sw=1.2, name="Boxes"))
    return node(parts, name="Platform")


def face(eyes_id, beard=None, hair=None, hair_len=0, w=24, h=30, look=0):
    """A head about 0,0: hair behind, face, eyes (own node for blinking), nose, mouth, optional beard."""
    parts = []
    if hair:
        parts.append(shape(rect(w + 10, h * 0.6 + hair_len, 0, -h * 0.12 + hair_len / 2, 10), hair, sw=1.6, name="Hair"))
    parts += [shape(ell(w, h), SKIN, sw=1.6, name="Face")]
    if beard:
        parts.append(shape(poly([(-w / 2 + 1, 0), (w / 2 - 1, 0), (w / 3, h * 0.42), (0, h * 0.62), (-w / 3, h * 0.42)], 4),
                           beard, sw=1.4, name="Beard"))
        parts.append(shape(rect(w * 0.5, 3.5, 0, h * 0.12, 1.5), beard, sw=1, name="Moustache"))
    parts += [node([shape([ell(3.2, 4.2, -w * 0.2 + look, -h * 0.06), ell(3.2, 4.2, w * 0.2 + look, -h * 0.06)], INK,
                          stroke=None, name="Pupils")], name="Eyes", id=eyes_id),
              shape(rect(1.6, 6, look * 0.6, h * 0.08), "88B07A5A", stroke=None, name="Nose")]
    if not beard:
        parts.append(shape(rect(6, 1.8, look * 0.5, h * 0.27, 0.9), "FFB04A44", stroke=None, name="Mouth"))
    return parts


def leg(x, top, length, hose, shoe=WHITE, w=11, name="Leg", id=None, rot=0):
    """A hose-clad leg hanging from its hip at (x, top), with a shoe at the foot."""
    return node([
        shape(rect(w, length, 0, length / 2, 4), hose, sw=1.6, name="Hose"),
        shape(ell(w + 9, 8, 3, length + 1), shoe, sw=1.4, name="Shoe"),
    ], name=name, x=x, y=top, rot=rot, id=id)


# ================================================================================
# court cards, in card space: 200 x 300 centred on 0,0, y down; ground at y≈122
# ================================================================================
def fante_di_coppe():
    """A young page: green beret with a red feather, grey-blue bobbed hair, green and
    blue doublet, red sleeves, gold puffed breeches with red garter bows, green hose.
    His right arm holds the cup up; a gold sword-stick hangs from his other hand."""
    ids("FanteHead", "FanteEyes", "Feather", "CupArm", "FanteCup")
    head = node(face(ID["FanteEyes"], hair=HAIRGREY, hair_len=8, look=-1.5) + [
        shape(ell(38, 12, 2, -17), GREEN, sw=1.6, name="Brim"),
        shape(ell(26, 14, 0, -22), GREEN, sw=1.6, name="Crown"),
        node([shape(poly([(0, 0), (8, -10), (16, -30), (10, -32), (2, -14)], 4), RED, sw=1.4, name="Plume")],
             name="Feather", x=10, y=-24, id=ID["Feather"]),
    ], name="Head", x=0, y=-74, id=ID["FanteHead"])
    cup_arm = node([
        shape(rect(13, 46, 0, -21, 5), RED, sw=1.6, name="Sleeve"),
        shape(rect(15, 5, 0, -44, 2), GOLD, sw=1.2, name="Cuff"),
        shape(ell(11, 10, 0, -50), SKIN, sw=1.4, name="Hand"),
        cup(30, name="Cup", id=ID["FanteCup"], x=0, y=-68),
    ], name="CupArm", x=-24, y=-44, rot=-0.42, id=ID["CupArm"])
    return node([
        platform(150, RED, 124),
        leg(-12, 50, 64, GREEN, name="LegR"),
        leg(12, 50, 64, GREEN, name="LegL"),
        shape([ell(16, 8, -12, 84), ell(16, 8, 12, 84)], RED, sw=1.2, name="Garters"),
        shape(poly([(-27, 8), (27, 8), (30, 46), (16, 62), (0, 54), (-16, 62), (-30, 46)], 8), GOLD, sw=1.6, name="Breeches"),
        shape([rect(1.2, 30, x_, 36) for x_ in (-20, -12, -4, 4, 12, 20)], "55000000", stroke=None, name="Pleats"),
        shape(rect(44, 58, 0, -20, 7), GREEN, sw=1.6, name="Doublet"),
        shape(rect(9, 58, 0, -20), BLUE, sw=1.2, name="Placket"),
        shape([ell(3, 3, 0, y_) for y_ in (-36, -26, -16, -6)], GOLD, sw=0.8, name="Buttons"),
        shape(rect(48, 6, 0, 8, 2), GOLD, sw=1.4, name="Belt"),
        node([shape(rect(12, 44, 0, 20, 5), RED, sw=1.6, name="Sleeve"),
              shape(ell(10, 10, 1, 45), SKIN, sw=1.4, name="Hand"),
              node([shape(rect(4, 56, 0, 26, 2), GOLD, sw=1.2, name="Stick")], name="Stick", x=2, y=44, rot=-0.55)],
             name="Arm", x=26, y=-42, rot=-0.12),
        shape(poly([(-20, -50), (20, -50), (14, -42), (-14, -42)], 3), GOLD, sw=1.4, name="Ruff"),
        head,
        cup_arm,
    ], name="Fante")


def cavallo_di_denari():
    """A grey horse walking to the left on a gold ground; the rider in a gold turban,
    red sleeves and a green jerkin holds a coin high."""
    ids("HorseHead", "HorseEye", "Tail", "LegF1", "LegF2", "LegB1", "LegB2", "Horse", "Rider",
        "RiderEyes", "RiderArm", "RiderCoin")
    hoof = lambda: shape(rect(10, 7, 0, 46, 2), "FF4A443C", sw=1.2, name="Hoof")
    def hleg(name, x, y, color):
        return node([shape(rect(10, 46, 0, 22, 4), color, sw=1.4, name="Shank"), hoof()],
                    name=name, x=x, y=y, id=ID[name])
    body = poly([(-44, -12), (-20, -22), (30, -22), (52, -12), (56, 6), (46, 18), (-30, 20), (-46, 8)], 10)
    horse = node([
        node([shape(poly([(0, 0), (10, 8), (14, 40), (8, 50), (2, 30), (-4, 6)], 4), MANE, sw=1.4, name="Hair")],
             name="Tail", x=52, y=-8, id=ID["Tail"]),
        hleg("LegB2", 38, 8, HORSEDK), hleg("LegF2", -30, 8, HORSEDK),
        shape(body, HORSE, sw=1.8, name="Body"),
        hleg("LegB1", 30, 10, HORSE), hleg("LegF1", -38, 10, HORSE),
        node([
            shape(poly([(0, 0), (-14, -34), (-22, -44), (-40, -30), (-46, -18), (-40, -12), (-24, -18), (-10, 10)], 6),
                  HORSE, sw=1.8, name="NeckHead"),
            shape(poly([(-2, -4), (-14, -32), (-20, -40), (-12, -40), (4, -12)], 3), MANE, sw=1.2, name="Mane"),
            shape(poly([(-22, -42), (-20, -54), (-15, -42)], 1), HORSE, sw=1.2, name="Ear"),
            node([shape(ell(4, 4, -30, -32), INK, stroke=None, name="Pupil")], name="Eye", id=ID["HorseEye"]),
            shape(ell(4, 3, -43, -18), "88000000", stroke=None, name="Nostril"),
            shape([rect(26, 2.5, -30, -22, 1, 0.5)], RED, sw=0.8, name="Bridle"),
        ], name="Head", x=-34, y=-6, id=ID["HorseHead"]),
        shape(poly([(-8, -24), (24, -24), (28, -12), (-12, -12)], 5), GOLD, sw=1.4, name="Saddle"),
        shape(rect(30, 6, 8, -12, 2), RED, sw=1, name="Girth"),
    ], name="Horse", x=0, y=52, id=ID["Horse"])
    rider = node([
        shape(rect(14, 30, 6, 4, 5), RED, sw=1.6, name="Thigh"),
        shape(poly([(0, 16), (12, 16), (14, 40), (2, 42)], 3), GOLD, sw=1.4, name="Boot"),
        shape(rect(30, 40, 0, -24, 7), GREEN, sw=1.6, name="Jerkin"),
        shape(rect(30, 5, 0, -6, 2), GOLD, sw=1.2, name="Belt"),
        node([shape(rect(11, 34, 0, 15, 4), RED, sw=1.4, name="Sleeve"),
              shape(ell(9, 9, -2, 34), SKIN, sw=1.2, name="Hand"),
              shape(rect(1.6, 30, -10, 46, 0, 1.1), DKRED, stroke=None, name="Rein")],
             name="ReinArm", x=10, y=-38, rot=0.5),
        shape(poly([(-16, -46), (16, -46), (10, -40), (-10, -40)], 2), GOLD, sw=1.2, name="Collar"),
        node(face(ID["RiderEyes"], beard="FFDCD6CC", look=-2, w=20, h=24) + [
            shape(ell(28, 14, 0, -12), GOLD, sw=1.4, name="Turban"),
            shape(ell(20, 12, 0, -18), GOLD, sw=1.4, name="TurbanTop"),
            shape([rect(22, 1.5, 0, -13, 0, 0.15), rect(16, 1.5, 0, -18, 0, -0.15)], DKGOLD, stroke=None, name="Wraps"),
        ], name="Head", x=0, y=-58),
        node([
            shape(rect(11, 38, 0, -17, 4), RED, sw=1.4, name="Sleeve"),
            shape(ell(10, 10, 0, -38), SKIN, sw=1.2, name="Hand"),
            coin(30, name="Coin", id=ID["RiderCoin"], y=-56),
        ], name="CoinArm", x=-12, y=-40, rot=-0.35, id=ID["RiderArm"]),
    ], name="Rider", x=8, y=24, id=ID["Rider"])
    return node([platform(170, GOLD, 124, 14, boxes=True), node([horse, rider], name="Mount", y=4)], name="Cavallo")


def re_di_denari():
    """The king: gold crown, white hair and beard, blue doublet with gold sleeves, green
    breeches, gold hose; a blue cape lined red falls behind; sword in his left hand;
    his coin floats at the top right."""
    ids("KingHead", "KingEyes", "KingCrown", "KingSword", "Cape", "KingCoin")
    crown = poly([(-14, 0), (-15, -16), (-9, -8), (-4, -20), (0, -10), (4, -20), (9, -8), (15, -16), (14, 0)], 1.5)
    head = node(face(ID["KingEyes"], beard="FFE7E2D8", hair="FFE7E2D8", hair_len=4, look=-1) + [
        node([shape(crown, GOLD, sw=1.4, name="Crown"),
              shape([ell(4, 4, -9, -4), ell(4, 4, 0, -4), ell(4, 4, 9, -4)], RED, sw=0.8, name="Jewels")],
             name="Crown", y=-14, id=ID["KingCrown"]),
    ], name="Head", x=-2, y=-80, id=ID["KingHead"])
    cape = node([
        shape(poly([(-28, 0), (26, 0), (64, 150), (40, 162), (-32, 150)], 8), BLUE, sw=1.8, name="Outer"),
        shape(poly([(20, 8), (44, 120), (56, 148), (40, 156), (24, 120), (10, 40)], 6), RED, sw=1.4, name="Lining"),
    ], name="Cape", y=-56, id=ID["Cape"])
    return node([
        platform(150, GOLD, 124),
        cape,
        leg(-12, 52, 62, GOLD, name="LegR"),
        leg(12, 52, 62, GOLD, name="LegL"),
        shape(poly([(-26, 14), (26, 14), (28, 50), (12, 62), (0, 56), (-12, 62), (-28, 50)], 8), GREEN, sw=1.6, name="Breeches"),
        shape(rect(46, 70, 0, -16, 7), BLUE, sw=1.6, name="Doublet"),
        shape([rect(1.2, 64, x_, -16) for x_ in (-12, -6, 6, 12)], "44FFFFFF", stroke=None, name="Stripes"),
        shape(rect(48, 6, 0, 14, 2), WHITE, sw=1.2, name="Belt"),
        shape(poly([(0, 10), (5, 15), (0, 20), (-5, 15)]), RED, sw=1, name="Jewel"),
        node([shape(rect(12, 46, 0, 21, 5), GOLD, sw=1.6, name="Sleeve"),
              shape(rect(14, 5, 0, 44, 2), WHITE, sw=1, name="Cuff"),
              shape(ell(10, 10, 0, 50), SKIN, sw=1.2, name="Hand")],
             name="ArmR", x=-26, y=-46, rot=0.1),
        node([shape(rect(12, 46, 0, 21, 5), GOLD, sw=1.6, name="Sleeve"),
              shape(rect(14, 5, 0, 44, 2), WHITE, sw=1, name="Cuff"),
              shape(ell(10, 10, 0, 50), SKIN, sw=1.2, name="Hand"),
              sword(96, id=ID["KingSword"], x=0, y=50, rot=-0.93)],
             name="ArmL", x=26, y=-46, rot=-0.18),
        shape(poly([(-22, -52), (22, -52), (16, -44), (-16, -44)], 3), WHITE, sw=1.4, name="Collar"),
        head,
        coin(34, name="Coin", id=ID["KingCoin"], x=62, y=-114),
    ], name="Re")


# ---- the cards themselves ---------------------------------------------------------
def card(name, content, x, y, rot, w=200, h=300, id=None, s=None):
    """A Neapolitan card: plain white, rounded, no frame (with a soft table shadow)."""
    return node([
        shape(rect(w, h, 7, 8, 14), "4D000000", stroke=None, name="Shadow"),
        shape(rect(w, h, 0, 0, 14), IVORY, stroke=EDGE, sw=1.5, name="Face"),
        content,
    ], name=name, x=x, y=y, rot=rot, id=id, sx=s, sy=s)


SETTE = [(-46, -100), (46, -100), (0, -42), (-46, 16), (46, 16), (-46, 96), (46, 96)]


def settebello():
    """The 7 of Coins, laid 2-1-2-2 as in the pattern; each coin has a glint that can flash."""
    for i in range(7):
        ID[f"Glint{i}"] = nid()
    parts = []
    for i, (x, y) in enumerate(SETTE):
        parts.append(coin(46, name=f"Coin{i}", x=x, y=y))
        parts.append(shape(star(4, 30, 0.18), WHITE, stroke=None, name=f"Glint{i}", x=x + 9, y=y - 9,
                           id=ID[f"Glint{i}"], opacity=0))
    return node(parts, name="Sette")


PIPS = {1: [(0, 0)], 2: [(0, -80), (0, 80)], 3: [(0, -90), (0, 0), (0, 90)],
        4: [(-44, -80), (44, -80), (-44, 80), (44, 80)], 5: [(-44, -90), (44, -90), (0, 0), (-44, 90), (44, 90)],
        6: [(-44, -90), (44, -90), (-44, 0), (44, 0), (-44, 90), (44, 90)]}


def numeral(n, suit):
    draw = (lambda x, y, i: coin(48, name=f"Pip{i}", x=x, y=y)) if suit == "denari" else \
           (lambda x, y, i: cup(58, name=f"Pip{i}", x=x, y=y))
    return node([draw(x, y, i) for i, (x, y) in enumerate(PIPS[n])], name=f"{n} {suit}")


def asso_di_coppe():
    """The ace of cups: the great urn: lidded, red shoulder, blue gadroons, gold belly, green foot."""
    return node([
        shape(poly([(-30, 92), (30, 92), (22, 76), (-22, 76)], 4), RED, sw=1.6, name="Foot"),
        shape(rect(14, 30, 0, 62), GOLD, sw=1.4, name="Stem"),
        shape(poly([(-46, 0), (46, 0), (40, 34), (16, 52), (-16, 52), (-40, 34)], 14), GREEN, sw=1.6, name="Base"),
        shape(rect(92, 34, 0, -8, 10), GOLD, sw=1.6, name="Belly"),
        shape(ell(18, 20, 0, -8), SKIN, sw=1.2, name="Mask"),
        shape([ell(12, 18, x_, -38) for x_ in (-34, -20, -6, 8, 22, 36)], BLUE, sw=1.2, name="Gadroons"),
        shape(rect(96, 26, 0, -38, 10), BLUE, sw=1.6, name="Band"),
        shape(rect(84, 26, 0, -62, 8), RED, sw=1.6, name="Shoulder"),
        shape(rect(72, 10, 0, -78, 4), GOLD, sw=1.4, name="Lip"),
        shape(ell(20, 24, 0, -96), RED, sw=1.4, name="Finial"),
        shape([ell(30, 46, -58, -44), ell(30, 46, 58, -44)], None, stroke=INK, sw=6, name="HandlesInk"),
        shape([ell(30, 46, -58, -44), ell(30, 46, 58, -44)], None, stroke=WHITE, sw=3, name="Handles"),
    ], name="AssoCoppe")


def asso_di_denari():
    """The ace of coins: an uncrowned double-headed eagle holding the great ring, a gold
    horseshoe ring below (the tax-stamp circle)."""
    wing = lambda sx: poly([(0, 0), (sx * 40, -30), (sx * 64, -10), (sx * 60, 40), (sx * 40, 70), (sx * 14, 50)], 8)
    head = lambda sx: [shape(poly([(sx * 8, 0), (sx * 22, -26), (sx * 40, -34), (sx * 52, -28), (sx * 38, -20),
                                   (sx * 26, -6), (sx * 18, 12)], 5), GOLD, sw=1.6, name="Neck"),
                       shape(ell(4, 4, sx * 38, -28), INK, stroke=None, name="Eye")]
    return node([
        shape(ell(108, 92, 0, 66), None, stroke=INK, sw=16, name="RingInk"),
        shape(ell(108, 92, 0, 66), None, stroke=GOLD, sw=12, name="Ring"),
        node([shape(wing(-1), RED, sw=1.6, name="WingL"), shape(wing(1), RED, sw=1.6, name="WingR"),
              shape([rect(8, 34, -50, 30, 3, 0.5), rect(8, 34, 50, 30, 3, -0.5)], GREEN, sw=1.2, name="Feathers"),
              *head(-1), *head(1),
              shape([poly([(-36, 50), (-30, 66), (-22, 58)]), poly([(36, 50), (30, 66), (22, 58)])], GOLD, sw=1.2,
                    name="Talons")], name="Eagle", y=-60),
        shape(ell(80, 80, 0, -40), WHITE, sw=2.2, name="Disc"),
    ], name="AssoDenari")


# ---- the back: Modiano-style "3D" checks (tumbling blocks) in blues -------------------
def card_back(w=180, h=270, light=LTBLUE, mid=BLUE, dark=DKBLUE):
    pw, ph, s = w - 26, h - 26, 13.0
    hgt = s * math.sqrt(3)
    tops, lefts, rights = [], [], []
    row, y = 0, -ph / 2 + s
    while y + s <= ph / 2:
        x = -pw / 2 + hgt / 2 + (hgt / 2 if row % 2 else 0)
        while x + hgt / 2 <= pw / 2:
            cx, cy = x, y
            tops.append(poly([(cx, cy - s), (cx + hgt / 2, cy - s / 2), (cx, cy), (cx - hgt / 2, cy - s / 2)]))
            lefts.append(poly([(cx - hgt / 2, cy - s / 2), (cx, cy), (cx, cy + s), (cx - hgt / 2, cy + s / 2)]))
            rights.append(poly([(cx, cy), (cx + hgt / 2, cy - s / 2), (cx + hgt / 2, cy + s / 2), (cx, cy + s)]))
            x += hgt
        y += 1.5 * s
        row += 1
    return node([
        shape(rect(w, h, 0, 0, 14), IVORY, stroke=EDGE, sw=1.5, name="Card"),
        shape(rect(pw, ph, 0, 0, 6), dark, stroke=None, name="Panel"),
        shape(tops, light, stroke=None, name="Tops"),
        shape(lefts, mid, stroke=None, name="Lefts"),
        shape(rights, dark, stroke=None, name="Rights"),
        shape(rect(pw, ph, 0, 0, 6), None, stroke=IVORY, sw=3, name="Trim"),
    ], name="Back")


def deck():
    ids("TopCard", "TopBack", "TopFace")
    under = [node([shape(rect(180, 270, 0, 0, 14), "4D000000", stroke=None, name="Shadow"), card_back()],
                  name=f"Under{i}", x=dx, y=dy, rot=r)
             for i, (dx, dy, r) in enumerate([(10, 9, 0.05), (5, 4, 0.025)])]
    top = node([
        node([shape(rect(180, 270, 0, 0, 14), IVORY, stroke=EDGE, sw=1.5, name="Card"),
              node([asso_di_denari()], name="Ace", sx=0.82, sy=0.82)],
             name="FaceSide", id=ID["TopFace"], opacity=0),
        node([card_back()], name="BackSide", id=ID["TopBack"]),
    ], name="TopCard", id=ID["TopCard"])
    return node(under + [top], name="Deck", x=372, y=968, rot=0.1, sx=0.8, sy=0.8)


def case():
    """The tuck case (astuccio), red with a gold double frame and a coin medallion, open
    at the top with the backs of a few cards showing. Shapes only, no maker's marks."""
    return node([
        shape(rect(150, 220, 8, 9, 10), "4D000000", stroke=None, name="Shadow"),
        shape(poly([(-70, -110), (70, -110), (60, -150), (-60, -150)], 6), DKRED, sw=1.8, name="Flap"),
        node([card_back(132, 196)], name="Cards", y=-26, sx=0.98, sy=0.98),
        shape(rect(150, 170, 0, 25, 8), RED, sw=2, name="Box"),
        shape(rect(150, 18, 0, -52, 3), DKRED, sw=1.6, name="Lip"),
        shape(rect(128, 140, 0, 32, 6), None, stroke=GOLD, sw=3, name="Frame"),
        shape(rect(118, 130, 0, 32, 4), None, stroke=GOLD, sw=1.2, name="Frame2"),
        shape(ell(70, 86, 0, 32), IVORY, stroke=GOLD, sw=3, name="Cartouche"),
        coin(44, name="Medallion", y=32),
        shape([star(4, 12, 0.3, x_, y_) for x_, y_ in ((-52, -28), (52, -28), (-52, 92), (52, 92))], GOLD,
              stroke=None, name="Corners"),
    ], name="Case", x=168, y=962, rot=-0.08, sx=0.82, sy=0.82)


# ---- the table hand and the sweep ----------------------------------------------------
TABLE_X = [590, 712, 834, 956]
TABLE_Y = 966
PLAYED_X = 1086


def table_hand():
    ids("Broom", *[f"T{i}" for i in range(4)], "Played")
    hand = [
        card("Sette", settebello(), TABLE_X[0], TABLE_Y, -0.04, id=ID["T0"], s=0.5),
        card("AssoCoppe", node([asso_di_coppe()], sx=0.95, sy=0.95), TABLE_X[1], TABLE_Y, 0.03, id=ID["T1"], s=0.5),
        card("TreCoppe", numeral(3, "coppe"), TABLE_X[2], TABLE_Y, -0.02, id=ID["T2"], s=0.5),
        card("QuattroDenari", numeral(4, "denari"), TABLE_X[3], TABLE_Y, 0.05, id=ID["T3"], s=0.5),
    ]
    played = card("Played", numeral(6, "coppe"), PLAYED_X, 1260, 0.06, id=ID["Played"], s=0.5)
    broom = node([
        shape(rect(10, 120, 0, -70, 4), WOOD, sw=1.6, name="Handle"),
        shape([rect(1.4, 110, x_, -70) for x_ in (-2, 2)], WOODDK, stroke=None, name="Grain"),
        shape(poly([(-16, -12), (16, -12), (44, 70), (-44, 70)], 6), STRAW, sw=1.8, name="Bristles"),
        shape([rect(1.6, 66, x_ * 7, 30, 0, x_ * 0.06) for x_ in range(-5, 6)], "77A0782A", stroke=None, name="Straws"),
        shape(rect(36, 9, 0, -10, 3), RED, sw=1.4, name="Band"),
        shape(rect(30, 6, 0, 12, 2), RED, sw=1.2, name="Band2"),
    ], name="Scopa", x=420, y=900, rot=-0.9, id=ID["Broom"], opacity=0)
    return node(hand + [played, broom], name="TableHand")


# ---- tiles: platform + suit sign -----------------------------------------------------
def tile_deco(kind):
    if kind == "fav":   # card 256 x 168, icon 112 centred: favourites are Denari
        return node([
            node([platform(112, GOLD, 0, 7)], name="Ground", x=128, y=146),
            coin(26, name="Suit", x=224, y=28),
        ], name="Deco")
    return node([         # card 172 x 116, icon 76 centred: apps are Coppe
        node([platform(76, RED, 0, 6)], name="Ground", x=86, y=101),
        cup(24, name="Suit", x=150, y=24),
    ], name="Deco")


# ---- felt lattice -----------------------------------------------------------------
def felt_lattice():
    paths = []
    step = 96
    for c in range(-1200, 3200, step):
        paths.append(rect(1.5, 2800, c, 540, 0, 0.7853982))
        paths.append(rect(1.5, 2800, c, 540, 0, -0.7853982))
    dots = []
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
        t = abs(x / width - 0.5) * 2
        a = max(0.0, 1 - t ** 2)
        b = min(5, int(a * 6))
        buckets.setdefault(b, []).append(x)
    shapes = [shape(rect(width * 0.9, 1.5, width / 2, cy), "66F2C318", stroke=None, name="Line")]
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
    case(),
    deck(),
    table_hand(),
    card("FanteCard", fante_di_coppe(), 1336, 902, -0.07),
    card("CavalloCard", cavallo_di_denari(), 1556, 896, 0.02),
    card("ReCard", re_di_denari(), 1776, 904, 0.07),
], name="Table")

I = ID


def anims():
    a = []
    # idle: blinks, nods, sways, the king's coin turning slowly
    D = 480
    a.append(anim("Court Idle", "8:900", D, {
        I["KingEyes"]: {"scaleY": blink(D, 140)},
        I["FanteEyes"]: {"scaleY": blink(D, 300)},
        I["RiderEyes"]: {"scaleY": blink(D, 220)},
        I["HorseEye"]: {"scaleY": blink(D, 410)},
        I["KingHead"]: {"rotation": swing(D, -0.03, 0.03)},
        I["KingCrown"]: {"y": swing(D // 2, -14, -16, D)},
        I["Cape"]: {"rotation": swing(D // 2, 0, 0.025, D)},
        I["Feather"]: {"rotation": swing(D // 3, 0.05, -0.18, D)},
        I["FanteHead"]: {"rotation": swing(D, 0.03, -0.04)},
        I["Tail"]: {"rotation": swing(D // 4, -0.05, 0.2, D)},
        I["KingCoin"]: {"scaleX": [(0, 1, "hold"), (300, 1, "ease"), (330, -1, "ease"), (360, 1, "hold"), (D, 1, "hold")]},
    }))
    # the page raises his cup in a toast every 9 s
    D = 540
    t = 360
    a.append(anim("Fante Toast", "8:901", D, {
        I["CupArm"]: {"rotation": [(0, -0.42, "hold"), (t, -0.42, "ease"), (t + 30, -0.05, "ease"),
                                   (t + 70, -0.05, "ease"), (t + 100, -0.42, "hold"), (D, -0.42, "hold")]},
        I["FanteCup"]: {"rotation": [(0, 0, "hold"), (t + 30, 0, "ease"), (t + 45, -0.35, "ease"),
                                     (t + 62, 0, "ease"), (t + 70, 0, "hold"), (D, 0, "hold")]},
    }))
    # the horse walks in place: a slow four-beat walk; trots (faster) while music plays
    def gait(P, amp, bob):
        trk = {}
        for k, ph in (("LegF1", 0), ("LegB2", 0.25), ("LegF2", 0.5), ("LegB1", 0.75)):
            o = int(P * ph)
            pts = [(0, 0, "ease")]
            for f, v in ((o, -amp), ((o + P // 2) % P, amp)):
                pts.append((f, v, "ease"))
            pts = sorted({f: (f, v, h) for f, v, h in pts}.values())
            pts.append((P, pts[0][1] if pts[0][0] == 0 else 0, "hold"))
            trk[I[k]] = {"rotation": pts}
        trk[I["HorseHead"]] = {"rotation": [(0, 0, "ease"), (P // 4, 0.07, "ease"), (P // 2, 0, "ease"),
                                            (3 * P // 4, 0.07, "ease"), (P, 0, "hold")]}
        trk[I["Horse"]] = {"y": [(0, 52, "ease"), (P // 4, 52 - bob, "ease"), (P // 2, 52, "ease"),
                                 (3 * P // 4, 52 - bob, "ease"), (P, 52, "hold")]}
        trk[I["Rider"]] = {"y": [(0, 24, "ease"), (P // 4, 24 - bob * 1.4, "ease"), (P // 2, 24, "ease"),
                                 (3 * P // 4, 24 - bob * 1.4, "ease"), (P, 24, "hold")]}
        return trk
    walk = gait(120, 0.16, 1.5)
    walk[I["KingSword"]] = {"rotation": [(0, -0.93, "hold"), (120, -0.93, "hold")]}
    walk[I["RiderArm"]] = {"rotation": [(0, -0.35, "hold"), (120, -0.35, "hold")]}
    a.append(anim("Horse Walk", "8:904", 120, walk))
    play = gait(32, 0.34, 4)  # ~112 bpm
    play[I["KingSword"]] = {"rotation": [(0, -0.93, "ease"), (8, -0.74, "ease"), (16, -0.93, "hold"), (32, -0.93, "hold")]}
    play[I["RiderArm"]] = {"rotation": [(0, -0.35, "ease"), (16, -0.2, "ease"), (32, -0.35, "hold")]}
    a.append(anim("Music Play", "8:905", 32, play))
    # the rider's coin turns over now and then
    D = 300
    a.append(anim("Coin Turn", "8:902", D, {
        I["RiderCoin"]: {"scaleX": [(0, 1, "hold"), (200, 1, "ease"), (225, -1, "ease"), (250, 1, "hold"), (D, 1, "hold")]},
    }))
    # the deck's top card flips to the Asso di Denari and back
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
    # the settebello shimmers: its seven coins glint one after another
    D = 360
    sh = {}
    for i in range(7):
        at = 20 + i * 14
        sh[I[f"Glint{i}"]] = {"opacity": [(0, 0, "hold"), (at, 0, "linear"), (at + 8, 1, "linear"), (at + 22, 0, "hold"),
                                          (D, 0, "hold")],
                              "rotation": [(0, 0, "hold"), (at, 0, "linear"), (at + 22, 0.8, "hold"), (D, 0, "hold")]}
    a.append(anim("Settebello", "8:907", D, sh))
    # a card is played, the broom sweeps the table (scopa!), the cards are dealt again; 25 s
    D = 1500
    play_at, sweep0, sweep1, deal = 840, 930, 1020, 1200
    bx0, bx1 = 470, 1190
    tr = {}
    for i, x in enumerate(TABLE_X + [PLAYED_X]):
        key = I[f"T{i}"] if i < 4 else I["Played"]
        hit = sweep0 + int((x - 60 - bx0) / (bx1 - bx0) * (sweep1 - sweep0))
        hit = max(sweep0, hit)
        y_rest = TABLE_Y if i < 4 else 1260
        xs = [(0, x, "hold"), (hit, x, "ease"), (hit + 40, x + 170, "hold"), (deal - 1, x, "hold"), (D, x, "hold")]
        ops = [(0, 1 if i < 4 else 1, "hold"), (hit + 8, 1, "linear"), (hit + 40, 0, "hold")]
        if i < 4:
            d = deal + i * 18
            ops += [(d, 0, "linear"), (d + 16, 1, "hold"), (D, 1, "hold")]
            ys = [(0, TABLE_Y, "hold"), (deal - 1, TABLE_Y - 24, "hold"), (d, TABLE_Y - 24, "ease"), (d + 18, TABLE_Y, "hold"),
                  (D, TABLE_Y, "hold")]
        else:
            ops += [(D, 1, "hold")]
            ys = [(0, 1260, "hold"), (play_at, 1260, "ease"), (play_at + 36, TABLE_Y + 6, "hold"),
                  (deal - 1, 1260, "hold"), (D, 1260, "hold")]
        tr[key] = {"x": xs, "opacity": ops, "y": ys,
                   "rotation": [(0, [-0.04, 0.03, -0.02, 0.05, 0.06][i], "hold"), (hit, [-0.04, 0.03, -0.02, 0.05, 0.06][i], "ease"),
                                (hit + 40, 0.35, "hold"), (deal - 1, [-0.04, 0.03, -0.02, 0.05, 0.06][i], "hold"),
                                (D, [-0.04, 0.03, -0.02, 0.05, 0.06][i], "hold")]}
    sweep = [(0, bx0, "hold"), (sweep0, bx0, "linear")]
    n = 6
    for k in range(1, n + 1):
        sweep.append((sweep0 + (sweep1 - sweep0) * k // n, bx0 + (bx1 - bx0) * k / n, "linear"))
    sweep[-1] = (sweep1, bx1, "hold")
    sweep.append((D, bx0, "hold"))
    tr[I["Broom"]] = {
        "x": sweep,
        "y": [(0, 900, "hold"), (sweep0 - 30, 860, "ease"), (sweep0, 912, "ease"), (sweep1, 912, "ease"),
              (sweep1 + 40, 860, "hold"), (D, 900, "hold")],
        "rotation": [(0, -0.9, "hold"), (sweep0 - 30, -0.9, "ease"), (sweep0, -0.6, "linear")] +
                    [(sweep0 + (sweep1 - sweep0) * k // 6, -0.6 + (0.12 if k % 2 else 0), "linear") for k in range(1, 6)] +
                    [(sweep1, -0.55, "ease"), (sweep1 + 40, -0.3, "hold"), (D, -0.9, "hold")],
        "opacity": [(0, 0, "hold"), (sweep0 - 30, 0, "linear"), (sweep0 - 10, 1, "hold"), (sweep1 + 20, 1, "linear"),
                    (sweep1 + 45, 0, "hold"), (D, 0, "hold")],
    }
    a.append(anim("Scopa Sweep", "8:908", D, tr))
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

    def music(name, lid, rest_aid, play_aid):
        return f'''<StateMachineLayer name="{name}" id="{lid}">
    <AnyState x="200" y="-120"/>
    <ExitState x="400" y="-120"/>
    <EntryState><StateTransition stateToId="{lid}1"/></EntryState>
    <AnimationState x="100" y="100" animationId="{rest_aid}" stateName="Rest" id="{lid}1">
        <StateTransition stateToId="{lid}2" duration="250" interpolationType="cubic">
            <CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>
{cond("true")}
        </StateTransition>
    </AnimationState>
    <AnimationState x="300" y="100" animationId="{play_aid}" stateName="Play" id="{lid}2">
        <StateTransition stateToId="{lid}1" duration="300" interpolationType="cubic">
            <CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>
{cond("false")}
        </StateTransition>
    </AnimationState>
</StateMachineLayer>'''
    return "\n".join([
        simple("Court Idle", "8:910", "8:911", "8:900"),
        simple("Fante Toast", "8:912", "8:913", "8:901"),
        simple("Coin Turn", "8:914", "8:915", "8:902"),
        simple("Deck Flip", "8:916", "8:917", "8:903"),
        music("Horse Gait", "8:920", "8:904", "8:905"),
        simple("Settebello", "8:940", "8:941", "8:907"),
        simple("Scopa Sweep", "8:942", "8:943", "8:908"),
    ])


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
    s = put(s, "fav-deco", tile_deco("fav"), 12)
    s = put(s, "app-deco", tile_deco("app"), 12)
    p.write_text(s)
    assert _next[0] < 900, _next[0]
    print("table dressing written:", _next[0] - 1, "ids")
