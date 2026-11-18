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
# suit signs (pips), in the style of the Modiano Napoletane reference (RESEARCH.md)
# ================================================================================
COINBLK, HAIRBRN, CROWNDK, HORSEBRN, HORSEBR2 = "FF23261C", "FF6E4426", "FF2E2A26", "FFD29A78", "FFB97E5E"


def coin(d=40, name="Coin", id=None, x=0, y=0, rot=0, sx=None):
    """Denaro: a black disc in a gold rim, a gold sun-burst with a round sun face at its heart."""
    return node([
        shape(ell(d), COINBLK, stroke=GOLD, sw=max(1.5, d * 0.07), name="Disc"),
        shape(star(16, d * 0.78, 0.55), GOLD, stroke=None, name="Rays"),
        shape(ell(d * 0.36), GOLD, stroke=COINBLK, sw=max(0.8, d * 0.025), name="Sun"),
        shape([ell(d * 0.05, d * 0.05, -d * 0.06, -d * 0.03), ell(d * 0.05, d * 0.05, d * 0.06, -d * 0.03),
               rect(d * 0.12, d * 0.025, 0, d * 0.07)], COINBLK, stroke=None, name="Face"),
    ], name=name, id=id, x=x, y=y, rot=rot, sx=sx)


def cup(h=44, name="Cup", id=None, x=0, y=0, rot=0):
    """Coppa (as on the 6 di Coppe): an urn: red rim, white loop handles, gold shoulder,
    dark green bowl, short stem, red foot."""
    k = h / 44
    return node([
        shape([ell(9 * k, 16 * k, -15 * k, -10 * k), ell(9 * k, 16 * k, 15 * k, -10 * k)], None, stroke=INK,
              sw=4 * k, name="HandlesInk"),
        shape([ell(9 * k, 16 * k, -15 * k, -10 * k), ell(9 * k, 16 * k, 15 * k, -10 * k)], None, stroke=WHITE,
              sw=2 * k, name="Handles"),
        shape(poly([(-11 * k, 21 * k), (11 * k, 21 * k), (8 * k, 15 * k), (-8 * k, 15 * k)], 2 * k), RED, sw=1.2,
              name="Foot"),
        shape(rect(5 * k, 8 * k, 0, 12 * k), GOLD, sw=1.1, name="Stem"),
        shape(poly([(-14 * k, -4 * k), (14 * k, -4 * k), (10 * k, 6 * k), (4 * k, 10 * k), (-4 * k, 10 * k),
                    (-10 * k, 6 * k)], 3 * k), DKGREEN, sw=1.3, name="Bowl"),
        shape(rect(26 * k, 11 * k, 0, -9 * k, 3 * k), GOLD, sw=1.3, name="Shoulder"),
        shape(rect(22 * k, 6 * k, 0, -17 * k, 2 * k), RED, sw=1.3, name="Rim"),
    ], name=name, id=id, x=x, y=y, rot=rot)


def blade(length, w=7, color=BLUE):
    """A straight blue sword blade from 0,0 to 0,length with a point."""
    return shape(poly([(-w / 2, 0), (w / 2, 0), (w / 2, length - w), (0, length), (-w / 2, length - w)], 1), color,
                 sw=1.2, name="Blade")


def hilt():
    """The ornate gold cross-hilt of the Neapolitan swords: knobbed quillons, a round pommel."""
    return node([
        shape(rect(30, 6, 0, 0, 3), GOLD, sw=1.2, name="Quillons"),
        shape([ell(8, 8, -16, 0), ell(8, 8, 16, 0), ell(8, 8, 0, 9), ell(9, 9, 0, -12)], GOLD, sw=1.1, name="Knobs"),
        shape(rect(5, 10, 0, -6, 2), DKGOLD, sw=1, name="Grip"),
    ], name="Hilt")


def platform(w, color, y, h=12, boxes=False, x=0):
    """The coloured ground each figure stands on, shaded with fine hatching."""
    hatch = [rect(1.2, h - 3, round(x - w / 2 + 6 + i * 6, 1), y) for i in range(int((w - 10) / 6))]
    parts = [shape(rect(w, h, x, y), color, sw=1.6, name="Ground"),
             shape(hatch, "55000000", stroke=None, name="Hatch")]
    return node(parts, name="Platform")


def face(eyes_id, hair=None, w=22, h=28, look=0, moustache=False):
    """A head about 0,0: hair behind, face, eyes (own node for blinking), nose, mouth or moustache."""
    parts = []
    if hair:
        parts.append(shape(rect(w + 8, h * 0.75, 0, -h * 0.05, 9), hair, sw=1.4, name="Hair"))
    parts += [shape(ell(w, h), SKIN, sw=1.5, name="Face"),
              node([shape([ell(3, 4, -w * 0.2 + look, -h * 0.06), ell(3, 4, w * 0.2 + look, -h * 0.06)], INK,
                          stroke=None, name="Pupils")], name="Eyes", id=eyes_id),
              shape(rect(1.6, 6, look * 0.6, h * 0.08), "88B07A5A", stroke=None, name="Nose")]
    if moustache:
        parts.append(shape(poly([(-8, h * 0.2), (0, h * 0.16), (8, h * 0.2), (5, h * 0.25), (0, h * 0.21),
                                 (-5, h * 0.25)], 1), HAIRBRN, sw=0.8, name="Moustache"))
    else:
        parts.append(shape(rect(6, 1.8, look * 0.5, h * 0.27, 0.9), "FFB04A44", stroke=None, name="Mouth"))
    return parts


def leg(x, top, length, hose, shoe=WHITE, w=11, name="Leg", id=None, rot=0):
    return node([
        shape(rect(w, length, 0, length / 2, 4), hose, sw=1.5, name="Hose"),
        shape(ell(w + 8, 7, 3, length + 1), shoe, sw=1.3, name="Shoe"),
    ], name=name, x=x, y=top, rot=rot, id=id)


def club(length=120, name="Club", id=None, x=0, y=0, rot=0, handle=RED):
    """A Neapolitan baton: a long green paddle with a gold wheat-ear down its middle, on a
    short handle. Grip at 0,0; the paddle runs up (negative y)."""
    L = length
    ears = [poly([(0, -L * t), (5, -L * t - 8), (0, -L * t - 4), (-5, -L * t - 8)]) for t in (0.4, 0.5, 0.6, 0.7, 0.8)]
    return node([
        shape(rect(7, 30, 0, 6, 3), handle, sw=1.2, name="Handle"),
        shape(poly([(-5, -8), (5, -8), (13, -L * 0.6), (12, -L + 8), (0, -L), (-12, -L + 8), (-13, -L * 0.6)], 10),
              GREEN, sw=1.5, name="Paddle"),
        shape(rect(2, L * 0.5, 0, -L * 0.6), GOLD, stroke=None, name="Stalk"),
        shape(ears, GOLD, sw=0.7, name="Ears"),
    ], name=name, id=id, x=x, y=y, rot=rot)


# ================================================================================
# court cards, in card space: 200 x 300 centred on 0,0, y down; ground at y≈126.
# Everything stays inside about ±88 x ±140 so nothing pokes past the card edge.
# ================================================================================
def fante_di_coppe():
    """A young page, three-quarter left: green beret with a red feather, brown bob, gold
    ruff, green doublet trimmed gold, red sleeves, gold puffed breeches, green hose with red
    tops, white shoes; his right hand holds the cup up at the shoulder; a dagger at his hip."""
    ids("FanteHead", "FanteEyes", "Feather", "CupArm", "FanteCup")
    head = node(face(ID["FanteEyes"], hair=HAIRBRN, look=-2) + [
        shape(ell(36, 11, 4, -13, -0.12), GREEN, sw=1.5, name="Beret"),
        shape(ell(22, 10, 2, -17), GREEN, sw=1.4, name="Crown"),
        node([shape(poly([(0, 0), (10, -6), (24, -6), (18, 2), (6, 4)], 4), RED, sw=1.2, name="Plume")],
             name="Feather", x=14, y=-16, id=ID["Feather"]),
    ], name="Head", x=-2, y=-94, id=ID["FanteHead"])
    cup_arm = node([
        shape(poly([(-6, -4), (6, 2), (-8, 30), (-20, 24)], 5), RED, sw=1.5, name="Upper"),
        shape(poly([(-20, 24), (-8, 30), (-14, 4), (-24, 0)], 5), RED, sw=1.5, name="Fore"),
        shape(rect(13, 5, -19, 1, 2), GOLD, sw=1, name="Cuff"),
        shape(ell(10, 9, -19, -4), SKIN, sw=1.2, name="Hand"),
        cup(30, name="Cup", id=ID["FanteCup"], x=-19, y=-24),
    ], name="CupArm", x=-20, y=-66, id=ID["CupArm"])
    return node([
        platform(120, RED, 126, x=4),
        leg(-12, 36, 80, GREEN, name="LegR"),
        leg(12, 36, 80, GREEN, name="LegL"),
        shape([rect(14, 14, -12, 58, 3), rect(14, 14, 12, 58, 3)], RED, sw=1.2, name="BootTops"),
        shape(poly([(-26, -14), (26, -14), (30, 24), (16, 46), (0, 38), (-16, 46), (-30, 24)], 9), GOLD, sw=1.5,
              name="Breeches"),
        shape([rect(1.2, 30, x_, 16) for x_ in (-18, -9, 0, 9, 18)], "4D7A5A00", stroke=None, name="Pleats"),
        shape(rect(46, 56, 0, -40, 6), GREEN, sw=1.5, name="Doublet"),
        shape(rect(5, 54, 0, -40), GOLD, sw=0.8, name="Trim"),
        shape(rect(48, 7, 0, -12, 2), RED, sw=1.2, name="Belt"),
        node([shape(rect(4, 34, 0, 16, 1), "FFD5DCE6", sw=1, name="Dagger"),
              shape(rect(14, 4, 0, 0, 2), GOLD, sw=0.8, name="Guard")], name="Dagger", x=22, y=-6, rot=-0.6),
        node([shape(rect(12, 42, 0, 19, 5), RED, sw=1.5, name="Sleeve"),
              shape(ell(10, 9, 1, 42), SKIN, sw=1.2, name="Hand")],
             name="Arm", x=26, y=-62, rot=-0.18),
        shape(ell(38, 12, 0, -68), GOLD, sw=1.3, name="Ruff"),
        head,
        cup_arm,
    ], name="Fante")


def cavallo_di_spade():
    """A Moor in a blue turban on a brown horse prancing to the right (near foreleg raised);
    red sleeves, green jerkin, gold skirt, red hose; his raised hand swings a blue scimitar."""
    ids("HorseHead", "HorseEye", "Tail", "LegF1", "LegF2", "LegB1", "LegB2", "Horse", "Rider",
        "RiderEyes", "SwordArm", "Prance")
    hoof = lambda: shape(rect(9, 6, 0, 60, 2), "FF4A3A30", sw=1.1, name="Hoof")

    def hleg(name, x, y, color, rot=0):
        return node([shape(rect(9, 60, 0, 29, 4), color, sw=1.3, name="Shank"), hoof()],
                    name=name, x=x, y=y, rot=rot, id=ID[name])
    raised = node([shape(rect(9, 32, 0, 15, 4), HORSEBRN, sw=1.3, name="Forearm"),
                   node([shape(rect(9, 28, 0, 13, 4), HORSEBRN, sw=1.3, name="Cannon"),
                         shape(rect(9, 6, 0, 28, 2), "FF4A3A30", sw=1.1, name="Hoof")],
                        name="Knee", y=30, rot=-1.3, id=ID["LegF1"])],
                  name="Raised", x=44, y=8, rot=-0.5, id=ID["Prance"])
    body = poly([(-50, -12), (-30, -22), (28, -24), (50, -14), (54, 4), (44, 16), (-34, 18), (-52, 6)], 10)
    horse = node([
        node([shape(poly([(0, 0), (-8, 8), (-12, 40), (-6, 48), (-2, 28), (4, 6)], 4), "FF6A4A34", sw=1.3,
                    name="Hair")], name="Tail", x=-50, y=-8, id=ID["Tail"]),
        hleg("LegB2", -36, 10, HORSEBR2, 0.1), hleg("LegF2", 30, 10, HORSEBR2, -0.05),
        shape(body, HORSEBRN, sw=1.7, name="Body"),
        hleg("LegB1", -26, 10, HORSEBRN, 0.15),
        raised,
        node([
            shape(poly([(0, 0), (12, -34), (22, -46), (40, -36), (48, -20), (42, -12), (26, -18), (14, 10)], 6),
                  HORSEBRN, sw=1.7, name="NeckHead"),
            shape(poly([(2, -6), (12, -32), (18, -40), (8, -38), (-4, -10)], 3), "FF6A4A34", sw=1.1, name="Mane"),
            shape(poly([(20, -44), (20, -56), (26, -46)], 1), HORSEBRN, sw=1.1, name="Ear"),
            node([shape(ell(4, 4, 30, -34), INK, stroke=None, name="Pupil")], name="Eye", id=ID["HorseEye"]),
            shape(ell(4, 3, 44, -18), "88000000", stroke=None, name="Nostril"),
            shape(rect(22, 2.2, 32, -26, 1, -0.5), GOLD, sw=0.6, name="Bridle"),
        ], name="Head", x=36, y=-10, id=ID["HorseHead"]),
        shape(rect(44, 36, -6, -8, 4), GREEN, stroke=GOLD, sw=2.5, name="Cloth"),
        shape(rect(10, 30, 16, 4, 3), GOLD, sw=1, name="Girth"),
    ], name="Horse", x=-10, y=35, sx=1.22, sy=1.22, id=ID["Horse"])
    scimitar = node([
        shape(poly([(-3, 0), (3, 0), (8, -30), (6, -58), (-2, -74), (-1, -52), (-2, -28)], 3), BLUE, sw=1.3,
              name="Blade"),
        shape(rect(18, 4, 0, 1, 2), GOLD, sw=0.9, name="Guard"),
        shape(rect(4, 9, 0, 7, 1.5), RED, sw=0.8, name="Grip"),
    ], name="Scimitar", y=-8, rot=-0.35)
    rider = node([
        shape(poly([(-4, 2), (8, 2), (10, 34), (2, 38)], 3), RED, sw=1.4, name="Leg"),
        shape(ell(14, 7, 6, 38), WHITE, sw=1.1, name="Shoe"),
        shape(poly([(-18, -10), (18, -10), (22, 12), (-20, 12)], 5), GOLD, sw=1.4, name="Skirt"),
        shape(rect(30, 34, 0, -26, 6), GREEN, sw=1.5, name="Jerkin"),
        node([shape(rect(11, 30, 0, 13, 4), RED, sw=1.3, name="Sleeve"),
              shape(ell(9, 9, 0, 30), SKIN, sw=1.1, name="Hand")],
             name="ReinArm", x=12, y=-38, rot=-0.7),
        shape(ell(26, 8, 0, -42), GOLD, sw=1.1, name="Collar"),
        node(face(ID["RiderEyes"], look=1.5, w=20, h=24, moustache=True) + [
            shape(ell(34, 24, 0, -13), BLUE, sw=1.4, name="Turban"),
            shape([rect(26, 1.6, 0, -10, 0, 0.18), rect(22, 1.6, 0, -16, 0, -0.15)], DKBLUE, stroke=None, name="Wraps"),
        ], name="Head", x=0, y=-58),
        node([
            shape(rect(11, 30, 0, -12, 4), RED, sw=1.3, name="Sleeve"),
            shape(ell(9, 9, 0, -28), SKIN, sw=1.1, name="Hand"),
            node([scimitar], name="InHand", y=-28),
        ], name="SwordArm", x=-14, y=-36, rot=-0.55, id=ID["SwordArm"]),
    ], name="Rider", x=-12, y=-12, id=ID["Rider"])
    return node([platform(160, BLUE, 128), node([horse, rider], name="Mount", sx=0.92, sy=0.92)], name="Cavallo")


def re_di_bastoni():
    """The king: dark crown, brown hair and moustache, white ruff, blue mantle over a dark
    green tunic, gold sleeves, gold hose, red cape; his left hand holds a great green club."""
    ids("KingHead", "KingEyes", "KingCrown", "ClubArm", "Cape")
    crown = poly([(-13, 0), (-15, -16), (-8, -8), (-4, -18), (0, -9), (4, -18), (8, -8), (15, -16), (13, 0)], 1.2)
    head = node(face(ID["KingEyes"], hair=HAIRBRN, look=1, moustache=True) + [
        node([shape(crown, CROWNDK, stroke=INK, sw=1.2, name="Crown"),
              shape([ell(3.5, 3.5, -8, -4), ell(3.5, 3.5, 0, -4), ell(3.5, 3.5, 8, -4)], GOLD, stroke=None,
                    name="Studs")],
             name="Crown", y=-13, id=ID["KingCrown"]),
    ], name="Head", x=0, y=-98, id=ID["KingHead"])
    cape = node([
        shape(poly([(-28, 0), (28, 0), (50, 172), (34, 180), (-40, 176)], 8), RED, stroke=DKRED, sw=1.6, name="Outer"),
        shape(poly([(-28, 4), (-40, 172), (-30, 176), (-20, 30)], 4), GREEN, sw=1.2, name="Edge"),
    ], name="Cape", y=-70, id=ID["Cape"])
    club_arm = node([
        shape(poly([(-6, -4), (6, 4), (14, 34), (2, 38)], 5), GOLD, sw=1.5, name="Upper"),
        shape(poly([(2, 38), (14, 34), (30, 44), (24, 54)], 5), GOLD, sw=1.5, name="Fore"),
        club(108, name="Club", x=30, y=48, rot=0.05),
        shape(ell(10, 10, 30, 48), SKIN, sw=1.2, name="Hand"),
    ], name="ClubArm", x=22, y=-74, id=ID["ClubArm"])
    return node([
        platform(118, DKGREEN, 128),
        cape,
        leg(-10, 30, 88, GOLD, name="LegR"),
        leg(12, 30, 88, GOLD, name="LegL"),
        shape(poly([(-22, -70), (22, -70), (26, 14), (-26, 14)], 6), DKGREEN, sw=1.5, name="Tunic"),
        shape(rect(46, 5, 0, -18, 2), DKGREEN, stroke=INK, sw=1, name="Belt"),
        shape(poly([(-27, -76), (27, -76), (31, -56), (-31, -56)], 6), BLUE, sw=1.4, name="Mantle"),
        node([shape(rect(12, 46, 0, 21, 5), GOLD, sw=1.5, name="Sleeve"),
              shape(ell(10, 10, 0, 47), SKIN, sw=1.2, name="Hand")],
             name="ArmR", x=-28, y=-70, rot=0.12),
        shape(ell(34, 10, 0, -78), WHITE, sw=1.2, name="Ruff"),
        head,
        club_arm,
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
    """The 7 of Coins, laid 2-1-2-2; each coin has a glint that can flash."""
    for i in range(7):
        ID[f"Glint{i}"] = nid()
    parts = []
    for i, (x, y) in enumerate(SETTE):
        parts.append(coin(54, name=f"Coin{i}", x=x, y=y))
        parts.append(shape(star(4, 30, 0.18), WHITE, stroke=None, name=f"Glint{i}", x=x + 12, y=y - 12,
                           id=ID[f"Glint{i}"], opacity=0))
    return node(parts, name="Sette")


def sei_di_coppe():
    """The 6 of Cups: two columns of three urns."""
    return node([cup(58, name=f"Cup{i}", x=x, y=y) for i, (x, y) in
                 enumerate([(-44, -92), (44, -92), (-44, 0), (44, 0), (-44, 92), (44, 92)])], name="SeiCoppe")


def quattro_di_spade():
    """The 4 of Swords: a long blue sword down each side, hilts meeting in the middle, and a
    crossing one between."""
    parts = []
    for x in (-50, 50):
        parts += [node([blade(110)], name="Up", x=x, y=-12, rot=math.pi), node([hilt()], name="HiltUp", x=x, y=-14),
                  node([blade(110)], name="Down", x=x, y=26), node([hilt()], name="HiltDown", x=x, y=24, rot=math.pi)]
    parts += [node([blade(84, 6)], name="Cross", x=-38, y=6, rot=-math.pi / 2),
              node([hilt()], name="HiltX", x=-40, y=6, rot=math.pi / 2)]
    return node(parts, name="QuattroSpade")


def asso_di_bastoni():
    """The ace of clubs: three great green batons fanned behind a gold grotesque mask, their
    red-and-gold shafts crossing below and ending in green tips."""
    batons = []
    for r in (-0.36, 0.36, 0):
        batons.append(node([
            shape(poly([(-5, 0), (5, 0), (6, 110), (0, 118), (-6, 110)], 3), RED if r else GOLD, sw=1.3, name="Shaft"),
            shape(poly([(-7, 100), (7, 100), (10, 128), (0, 136), (-10, 128)], 4), GREEN, sw=1.3, name="Tip"),
            node([club(118, handle=GOLD)], name="Top", y=-6),
        ], name="Baton", y=-6, rot=r))
    mask = node([
        shape(poly([(-30, -24), (30, -24), (34, 4), (22, 30), (0, 38), (-22, 30), (-34, 4)], 10), GOLD, sw=1.6,
              name="Mask"),
        shape([poly([(-24, -10), (-6, -14), (-8, -6), (-22, -4)]), poly([(24, -10), (6, -14), (8, -6), (22, -4)])],
              DKGREEN, sw=0.8, name="Brows"),
        shape([ell(6, 5, -14, -2), ell(6, 5, 14, -2)], INK, stroke=None, name="Eyes"),
        shape(poly([(-3, -4), (3, -4), (6, 10), (-6, 10)], 2), "FFE0B020", sw=1, name="Nose"),
        shape(poly([(-22, 18), (-6, 12), (0, 15), (6, 12), (22, 18), (8, 20), (0, 18), (-8, 20)], 2), DKGREEN, sw=0.8,
              name="Moustache"),
        shape(rect(10, 3, 0, 24, 1.5), RED, stroke=None, name="Mouth"),
        shape([poly([(-34, -20), (-46, -30), (-38, -8)]), poly([(34, -20), (46, -30), (38, -8)])], GOLD, sw=1.2,
              name="Leaves"),
    ], name="MaskGroup", y=-4)
    return node(batons + [mask], name="AssoBastoni", sx=0.95, sy=0.95)


def asso_di_denari():
    """The ace of coins as on the reference: two gold eagle heads facing apart at the top, red
    wings banded green wrapping a great white ring, red legs with gold tassels down the sides,
    and the gold ring that closes the bottom of the '8'."""
    head = lambda s: [
        shape(poly([(s * 4, 0), (s * 14, -24), (s * 30, -32), (s * 46, -30), (s * 36, -22), (s * 24, -18), (s * 16, 4)],
                   5), GOLD, sw=1.5, name="Neck"),
        shape(poly([(s * 46, -30), (s * 54, -26), (s * 44, -22)], 1), "FFE09A10", sw=1, name="Beak"),
        shape(ell(4, 4, s * 32, -27), INK, stroke=None, name="Eye")]
    wing = lambda s: poly([(s * 10, -6), (s * 44, -2), (s * 58, 26), (s * 54, 70), (s * 36, 92), (s * 30, 64),
                           (s * 40, 30)], 8)
    band = lambda s: poly([(s * 46, 30), (s * 58, 34), (s * 56, 50), (s * 42, 46)], 3)
    legs = lambda s: poly([(s * 30, 80), (s * 44, 86), (s * 40, 120), (s * 50, 160), (s * 40, 162), (s * 28, 122)], 4)
    tassel = lambda s: poly([(s * 44, 150), (s * 52, 150), (s * 58, 186), (s * 40, 186)], 2)
    return node([
        shape(ell(124, 108, 0, 64), None, stroke=INK, sw=15, name="RingInk"),
        shape(ell(124, 108, 0, 64), None, stroke=GOLD, sw=11, name="Ring"),
        shape([legs(-1), legs(1)], RED, sw=1.4, name="Legs"),
        shape([tassel(-1), tassel(1)], GOLD, sw=1.2, name="Tassels"),
        shape([wing(-1), wing(1)], RED, sw=1.6, name="Wings"),
        shape([band(-1), band(1)], DKGREEN, sw=1, name="Bands"),
        *head(-1), *head(1),
        shape(ell(98, 98, 0, -36), WHITE, sw=2, name="Disc"),
    ], name="AssoDenari", y=-20, sx=0.9, sy=0.9)


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
    return node(under + [top], name="Deck", x=190, y=962, rot=0.1, sx=0.88, sy=0.88)


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
    ], name="Case", x=CASE_X, y=CASE_Y, rot=-0.06, sx=CASE_S, sy=CASE_S)


# ---- the table hand and the sweep ----------------------------------------------------
COURT_X, COURT_Y, COURT_S = [570, 710, 850], 104, 0.55
CASE_X, CASE_Y, CASE_S = 1004, 102, 0.58
TABLE_S = 0.62
TABLE_X = [480, 720, 960, 1200]
TABLE_Y = 960
PLAYED_X = 1440


def tre_di_denari():
    return node([coin(54, name=f"Coin{i}", y=y) for i, y in enumerate((-92, 0, 92))], name="TreDenari")


def table_hand():
    ids("Broom", *[f"T{i}" for i in range(4)], "Played")
    hand = [
        card("Sette", settebello(), TABLE_X[0], TABLE_Y, -0.04, id=ID["T0"], s=TABLE_S),
        card("AssoBastoni", asso_di_bastoni(), TABLE_X[1], TABLE_Y, 0.03, id=ID["T1"], s=TABLE_S),
        card("QuattroSpade", quattro_di_spade(), TABLE_X[2], TABLE_Y, -0.02, id=ID["T2"], s=TABLE_S),
        card("SeiCoppe", sei_di_coppe(), TABLE_X[3], TABLE_Y, 0.05, id=ID["T3"], s=TABLE_S),
    ]
    played = card("Played", tre_di_denari(), PLAYED_X, 1260, 0.06, id=ID["Played"], s=TABLE_S)
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
    # the court cards stand in the top bar, between the clock and Now Playing
    card("FanteCard", fante_di_coppe(), COURT_X[0], COURT_Y, -0.06, s=COURT_S),
    card("CavalloCard", cavallo_di_spade(), COURT_X[1], COURT_Y - 4, 0.02, s=COURT_S),
    card("ReCard", re_di_bastoni(), COURT_X[2], COURT_Y, 0.06, s=COURT_S),
], name="Table")

I = ID


def anims():
    a = []
    # idle: blinks, nods, sways
    D = 480
    a.append(anim("Court Idle", "8:900", D, {
        I["KingEyes"]: {"scaleY": blink(D, 140)},
        I["FanteEyes"]: {"scaleY": blink(D, 300)},
        I["RiderEyes"]: {"scaleY": blink(D, 220)},
        I["HorseEye"]: {"scaleY": blink(D, 410)},
        I["KingHead"]: {"rotation": swing(D, -0.03, 0.03)},
        I["KingCrown"]: {"y": swing(D // 2, -13, -15, D)},
        I["Cape"]: {"rotation": swing(D // 2, 0, 0.02, D)},
        I["Feather"]: {"rotation": swing(D // 3, 0.05, -0.2, D)},
        I["FanteHead"]: {"rotation": swing(D, 0.03, -0.04)},
        I["Tail"]: {"rotation": swing(D // 4, -0.05, 0.18, D)},
    }))
    # the page raises his cup in a toast every 9 s
    D = 540
    t = 360
    a.append(anim("Fante Toast", "8:901", D, {
        I["CupArm"]: {"rotation": [(0, 0, "hold"), (t, 0, "ease"), (t + 30, 0.28, "ease"),
                                   (t + 70, 0.28, "ease"), (t + 100, 0, "hold"), (D, 0, "hold")]},
        I["FanteCup"]: {"rotation": [(0, 0, "hold"), (t + 30, 0, "ease"), (t + 45, -0.4, "ease"),
                                     (t + 62, 0, "ease"), (t + 70, 0, "hold"), (D, 0, "hold")]},
    }))
    # the Moor flourishes his scimitar now and then
    D = 480
    f = 330
    a.append(anim("Scimitar", "8:902", D, {
        I["SwordArm"]: {"rotation": [(0, -0.55, "hold"), (f, -0.55, "ease"), (f + 18, -1.15, "ease"),
                                     (f + 40, 0.2, "ease"), (f + 60, -0.85, "ease"), (f + 84, -0.55, "hold"),
                                     (D, -0.55, "hold")]},
    }))
    # the horse: an easy prance at rest, a trot while music plays (~112 bpm)
    def gait(P, amp, bob, lift):
        b = 35
        return {
            I["Prance"]: {"rotation": [(0, -0.5, "ease"), (P // 2, -0.5 + lift, "ease"), (P, -0.5, "hold")]},
            I["LegF1"]: {"rotation": [(0, -1.3, "ease"), (P // 2, -1.3 + lift * 1.6, "ease"), (P, -1.3, "hold")]},
            I["LegF2"]: {"rotation": [(0, -0.05 - amp, "ease"), (P // 2, -0.05 + amp, "ease"), (P, -0.05 - amp, "hold")]},
            I["LegB1"]: {"rotation": [(0, 0.15 + amp, "ease"), (P // 2, 0.15 - amp, "ease"), (P, 0.15 + amp, "hold")]},
            I["LegB2"]: {"rotation": [(0, 0.1 - amp, "ease"), (P // 2, 0.1 + amp, "ease"), (P, 0.1 - amp, "hold")]},
            I["HorseHead"]: {"rotation": [(0, 0, "ease"), (P // 2, 0.08, "ease"), (P, 0, "hold")]},
            I["Horse"]: {"y": [(0, b, "ease"), (P // 4, b - bob, "ease"), (P // 2, b, "ease"),
                               (3 * P // 4, b - bob, "ease"), (P, b, "hold")]},
            I["Rider"]: {"y": [(0, -12, "ease"), (P // 4, -12 - bob * 1.3, "ease"), (P // 2, -12, "ease"),
                               (3 * P // 4, -12 - bob * 1.3, "ease"), (P, -12, "hold")]},
        }
    a.append(anim("Horse Prance", "8:904", 150, gait(150, 0.04, 1, 0.25)))
    a.append(anim("Horse Trot", "8:905", 32, gait(32, 0.22, 4, 0.45)))
    # the king lifts his club every 10 s; with music he beats time with it
    D = 600
    u = 420
    a.append(anim("King Lift", "8:906", D, {
        I["ClubArm"]: {"rotation": [(0, 0, "hold"), (u, 0, "ease"), (u + 30, -0.3, "ease"), (u + 80, -0.3, "ease"),
                                    (u + 110, 0, "hold"), (D, 0, "hold")]},
    }))
    a.append(anim("King Beat", "8:909", 32, {
        I["ClubArm"]: {"rotation": [(0, 0, "ease"), (8, -0.16, "ease"), (16, 0.02, "ease"), (32, 0, "hold")]},
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
    bx0, bx1 = 320, 1640
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
        simple("Scimitar", "8:914", "8:915", "8:902"),
        simple("Deck Flip", "8:916", "8:917", "8:903"),
        music("Horse Gait", "8:920", "8:904", "8:905"),
        music("King Club", "8:930", "8:906", "8:909"),
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
