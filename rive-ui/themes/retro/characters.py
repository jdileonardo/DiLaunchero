#!/usr/bin/env python3
"""Writes the retro theme's cast into scene.rml, between <!-- cast:... --> markers.

The characters are repetitive keyframe work (walk cycles, rolls, pops), so they
are generated here rather than hand-written. Re-run after editing; it replaces
only the marked regions:

    python3 themes/retro/characters.py      (from rive-ui/, or anywhere)

Cast:
  Cass     a cassette who paces the gap between the clock and Now Playing
  Spinny   a vinyl record that rolls across the floor now and then
  Pops     a popcorn bucket in the bottom-right that pops kernels
  Ray      a radio in the bottom-left; bounces and sends notes while music plays
  TV guy   (in scene.rml) gets arms here, and waves now and then
"""
import math
import re
from pathlib import Path

SCENE = Path(__file__).with_name("scene.rml")
INK, PAPER, TOMATO, MUSTARD, TEAL, PINK = "FF2B1E16", "FFFFF8EA", "FFE4572E", "FFF2B134", "FF2A9D8F", "FFF08A6C"
FPS = 60

# ---------------------------------------------------------------- drawing helpers

def fill(c, cid=None):
    i = f' id="{cid}"' if cid else ""
    return f'<Fill name="F"><SolidColor colorValue="{c}" name="C"{i}/></Fill>'


def stroke(c=INK, t=4):
    return f'<Stroke thickness="{t}" name="S"><SolidColor colorValue="{c}" name="C"/></Stroke>'


def rect(w, h, x=0, y=0, r=0, name="P"):
    rr = f' cornerRadiusTL="{r}"' if r else ""
    return f'<Rectangle x="{x}" y="{y}" width="{w}" height="{h}"{rr} name="{name}"/>'


def ell(w, h, x=0, y=0, name="P"):
    return f'<Ellipse x="{x}" y="{y}" width="{w}" height="{h}" name="{name}"/>'


def shape(name, paths, paint, x=0, y=0, rot=0, sid=None, extra=""):
    i = f' id="{sid}"' if sid else ""
    r = f' rotation="{rot}"' if rot else ""
    return f'<Shape x="{x}" y="{y}"{r}{extra} name="{name}"{i}>' + "".join(paths) + paint + "</Shape>"


def node(name, kids, x=0, y=0, nid=None, extra=""):
    i = f' id="{nid}"' if nid else ""
    return f'<Node x="{x}" y="{y}"{extra} name="{name}"{i}>' + "".join(kids) + "</Node>"


def eyes(nid, gap, y, w=6, h=9, x=0):
    """Two pupils in a node of their own, so a blink can squash them (scaleY)."""
    return node("Eyes", [shape("Pupils", [ell(w, h, -gap), ell(w, h, gap)], fill(INK))], x, y, nid)

# ---------------------------------------------------------------- animation helpers

def keys(prop, frames, interp="linear"):
    """frames: [(frame, value), ...]; 'hold' keys jump, 'linear' keys glide to the next."""
    ks = "".join(
        f'<KeyFrameDouble frame="{f}" value="{round(v, 4)}" interpolationType="{it if isinstance(it, str) else interp}"/>'
        for f, v, *rest in frames for it in [rest[0] if rest else interp])
    return f'<KeyedProperty property="{prop}">{ks}</KeyedProperty>'


def keyed(oid, *props):
    return f'<KeyedObject objectId="{oid}">' + "".join(props) + "</KeyedObject>"


def anim(aid, name, dur, *objs):
    return f'<LinearAnimation duration="{dur}" loopValue="loop" name="{name}" id="{aid}">' + "".join(objs) + "</LinearAnimation>"


def blink(oid, period, at):
    return keyed(oid, keys("scaleY", [(0, 1, "hold"), (at, 1), (at + 6, 0.1), (at + 12, 1, "hold"), (period, 1, "hold")]))


def layer(lid, name, aid):
    return (f'<StateMachineLayer name="{name}" id="{lid}"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
            f'<EntryState><StateTransition stateToId="{lid}1"/></EntryState>'
            f'<AnimationState x="200" animationId="{aid}" id="{lid}1"/></StateMachineLayer>')


def playing_layer(lid, name, rest_aid, play_aid):
    """Rest until npPlaying (4:7) turns true, then the play loop; back when it stops."""
    def cond(v):
        return ('<TransitionViewModelCondition opValue="equal"><TransitionPropertyViewModelComparator><BindablePropertyBoolean>'
                '<DataBindContext sourcePathIds="4:1-4:7" propertyKey="634"/></BindablePropertyBoolean>'
                f'</TransitionPropertyViewModelComparator><TransitionValueBooleanComparator value="{v}"/></TransitionViewModelCondition>')
    ease = '<CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>'
    return (f'<StateMachineLayer name="{name}" id="{lid}"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
            f'<EntryState><StateTransition stateToId="{lid}1"/></EntryState>'
            f'<AnimationState x="100" y="100" animationId="{rest_aid}" stateName="Rest" id="{lid}1">'
            f'<StateTransition stateToId="{lid}2" duration="250" interpolationType="cubic">{ease}{cond("true")}</StateTransition></AnimationState>'
            f'<AnimationState x="300" y="100" animationId="{play_aid}" stateName="Play" id="{lid}2">'
            f'<StateTransition stateToId="{lid}1" duration="300" interpolationType="cubic">{ease}{cond("false")}</StateTransition></AnimationState>'
            '</StateMachineLayer>')


def still(aid, name, *objs):
    return f'<LinearAnimation duration="1" name="{name}" id="{aid}">' + "".join(objs) + "</LinearAnimation>"

# ================================================================ the cast
shapes, anims, layers = [], [], []

# ---------------------------------------------------------------- Cass the cassette
# Walker (x) > Flip (scaleX, faces the way it walks) > Body (bob). Feet at y=0.
CASS_Y, X0, X1 = 166, 560, 1060
cass_legs = [
    node(f"Leg{s}", [shape("Shin", [rect(7, 16, 0, 8, 3)], fill(INK)),
                     shape("Shoe", [ell(15, 8, 3, 17)], fill(TOMATO) + stroke(INK, 2.5))],
         x, -19, nid)
    for s, x, nid in (("L", -11, "9:16"), ("R", 11, "9:17"))]
cass_body = node("Body", [
    eyes("9:13", 8, -55, 6, 8),
    shape("Mouth", [rect(9, 3.5, 0, -46, 1.75)], fill(INK)),
    shape("Label", [rect(52, 22, 0, -51, 5)], fill(PAPER) + stroke(INK, 2.5)),
    shape("ReelL", [ell(13, 13), '<Star points="6" width="7" height="7" innerRadius="0.5" name="Hub"/>'],
          fill(PAPER) + stroke(INK, 2.5), -13, -31, sid="9:14"),
    shape("ReelR", [ell(13, 13), '<Star points="6" width="7" height="7" innerRadius="0.5" name="Hub"/>'],
          fill(PAPER) + stroke(INK, 2.5), 13, -31, sid="9:15"),
    shape("Window", [rect(44, 17, 0, -31, 6)], fill("FF6B4A36") + stroke(INK, 2.5)),
    shape("ArmL", [rect(5, 20, 0, 0, 2.5), ell(9, 9, 0, 11)], fill(INK), -42, -36, rot=0.3),
    shape("ArmR", [rect(5, 20, 0, 0, 2.5), ell(9, 9, 0, 11)], fill(INK), 42, -36, rot=-0.3),
    shape("Shell", [rect(74, 52, 0, -42, 8)], fill(TEAL) + stroke(INK, 4)),
    shape("Shadow", [rect(74, 52, 5, -37, 8)], fill(INK)),
], 0, 0, "9:12")
shapes.append(node("Cass", [node("Flip", [cass_body] + cass_legs, 0, 0, "9:11")], X0, CASS_Y, "9:10",
                   ' scaleX="1.3" scaleY="1.3"'))

# 20 s: walk right 8 s, stop and look 2 s, turn, walk left 8 s, stop 2 s.
WALK = 480
T = [0, WALK, WALK + 120, 2 * WALK + 120, 2 * WALK + 240]
step = 14  # frames per half-step
def walk_keys(prop, a, b, rest=0.0):
    """Alternate a/b every half-step while walking; settle to rest while stopped."""
    out = []
    for start, end in ((T[0], T[1]), (T[2], T[3])):
        f, flip = start, False
        while f < end:
            out.append((f, a if flip else b)); f += step; flip = not flip
        out.append((end, rest))
        out.append((end + 1, rest, "hold"))
    return sorted(out, key=lambda k: k[0])
anims.append(anim("9:100", "Cass Walk", T[4],
    keyed("9:10", keys("x", [(T[0], X0), (T[1], X1, "hold"), (T[2], X1), (T[3], X0, "hold"), (T[4], X0, "hold")])),
    keyed("9:11", keys("scaleX", [(0, 1, "hold"), (T[1] + 70, -1, "hold"), (T[3] + 70, 1, "hold")])),
    keyed("9:12", keys("y", walk_keys("y", 0, -4))),
    keyed("9:16", keys("rotation", walk_keys("r", 0.45, -0.45))),
    keyed("9:17", keys("rotation", walk_keys("r", -0.45, 0.45))),
    # during each stop, a look at the viewer: blink twice
    keyed("9:13", keys("scaleY", [(0, 1, "hold"), (T[1] + 20, 1), (T[1] + 26, 0.1), (T[1] + 32, 1), (T[1] + 44, 1),
                                  (T[1] + 50, 0.1), (T[1] + 56, 1, "hold"), (T[3] + 30, 1), (T[3] + 36, 0.1),
                                  (T[3] + 42, 1, "hold")]))))
anims.append(anim("9:101", "Cass Reels", 90,
    keyed("9:14", keys("rotation", [(0, 0), (90, 2 * math.pi)])),
    keyed("9:15", keys("rotation", [(0, 0), (90, 2 * math.pi)]))))
layers += [layer("9:200", "Cass Walk", "9:100"), layer("9:201", "Cass Reels", "9:101")]

# ---------------------------------------------------------------- Spinny the record
# Rolls left to right along the floor every 30 s (15 s across, 15 s off-screen).
R = 44
FLOOR = 1040
spin = node("Spin", [
    shape("Shine", [rect(4, 30, 0, -26, 2)], fill("55FFF8EA"), rot=0.6),
    shape("Label", [ell(34, 34)], fill(TOMATO) + stroke(INK, 3)),
    shape("Grooves", [ell(70, 70), ell(54, 54)], stroke("FF5A4636", 2)),
    shape("Disc", [ell(2 * R, 2 * R)], fill(INK)),
], 0, 0, "9:31")
face = node("Face", [eyes("9:32", 6, -3, 5, 7), shape("Mouth", [rect(8, 3, 0, 6, 1.5)], fill(INK))], 0, 0)
shapes.append(node("Spinny", [face, spin], -120, FLOOR - R, "9:30"))
ROLL = 900
dist = 1920 + 240
hops = [(0, FLOOR - R)]
for k in range(1, 9):
    f = int(ROLL * k / 9)
    hops += [(f - 25, FLOOR - R - 10), (f, FLOOR - R)]
hops += [(ROLL, FLOOR - R, "hold"), (2 * ROLL, FLOOR - R, "hold")]
anims.append(anim("9:102", "Spinny Roll", 2 * ROLL,
    keyed("9:30", keys("x", [(0, -120), (ROLL, -120 + dist, "hold"), (2 * ROLL, -120 + dist, "hold")]),
          keys("y", hops)),
    keyed("9:31", keys("rotation", [(0, 0), (ROLL, dist / R, "hold"), (2 * ROLL, dist / R, "hold")])),
    blink("9:32", 2 * ROLL, 400)))
layers.append(layer("9:202", "Spinny Roll", "9:102"))

# ---------------------------------------------------------------- Pops the popcorn bucket
PX, PY = 1800, 1046  # bottom of the bucket
kernels = [shape(f"Kernel{i}", [ell(13, 11), ell(9, 8, 4, -4)], fill(PAPER) + stroke(INK, 2), x, -92, sid=f"9:4{i + 1}",
                 extra=' opacity="0"')
           for i, x in enumerate((-12, 8, -2))]
bucket = node("Bucket", [
    eyes("9:45", 9, -34, 6, 9),
    shape("Cheeks", [ell(9, 5, -19, -26), ell(9, 5, 19, -26)], fill(PINK)),
    shape("Mouth", [rect(10, 4, 0, -24, 2)], fill(INK)),
    shape("Stripes", [rect(9, 64, -18, -32), rect(9, 64, 0, -32), rect(9, 64, 18, -32)], fill(TOMATO)),
    shape("Tub", [rect(64, 64, 0, -32, 6)], fill(PAPER) + stroke(INK, 4)),
    shape("Corn", [ell(26, 22, -18, -66), ell(28, 24, 2, -72), ell(24, 22, 20, -66), ell(22, 18, -6, -80),
                   ell(20, 18, 12, -82)], fill("FFFFF1C9") + stroke(INK, 3)),
    shape("Shadow", [rect(64, 64, 5, -27, 6)], fill(INK)),
], 0, 0, "9:44")
shapes.append(node("Pops", kernels + [bucket], PX, PY, "9:40"))
POP = 300
def pop(k, at, dx):
    return keyed(f"9:4{k + 1}",
                 keys("opacity", [(0, 0, "hold"), (at, 1, "hold"), (at + 50, 1), (at + 56, 0, "hold"), (POP, 0, "hold")]),
                 keys("y", [(0, -80, "hold"), (at, -80), (at + 22, -170), (at + 50, -60, "hold"), (POP, -80, "hold")]),
                 keys("x", [(0, 0, "hold"), (at, 0), (at + 50, dx, "hold"), (POP, 0, "hold")]),
                 keys("rotation", [(0, 0, "hold"), (at, 0), (at + 50, 3 * (1 if dx > 0 else -1), "hold"), (POP, 0, "hold")]))
squash = [(0, 1, "hold")]
for at in (20, 120, 200):
    squash += [(at - 10, 1), (at - 2, 0.86), (at + 6, 1.08), (at + 16, 1, "hold")]
squash.append((POP, 1, "hold"))
anims.append(anim("9:103", "Pops Pop", POP,
    keyed("9:44", keys("scaleY", squash)),
    pop(0, 20, -40), pop(1, 120, 45), pop(2, 200, -20),
    blink("9:45", POP, 260)))
layers.append(layer("9:203", "Pops Pop", "9:103"))

# ---------------------------------------------------------------- Ray the radio
RX, RY = 130, 1046
notes = [node(f"Note{i}", [shape("Head", [ell(14, 11)], fill(c) + stroke(INK, 2.5), rot=-0.4),
                           shape("Stem", [rect(3.5, 24, 6, -11)], fill(INK))],
              x, -110, f"9:5{i + 1}", ' opacity="0"')
         for i, (x, c) in enumerate(((-20, TEAL), (24, TOMATO)))]
radio = node("Radio", [
    eyes("9:56", 10, -50, 6, 9, 22),
    shape("Mouth", [rect(10, 4, 22, -38, 2)], fill(INK)),
    shape("Dial", [rect(30, 22, 22, -45, 5)], fill(PAPER) + stroke(INK, 2.5)),
    shape("GrilleDots", [ell(6, 6, -30, -48), ell(6, 6, -14, -48), ell(6, 6, -30, -32), ell(6, 6, -14, -32),
                         ell(6, 6, -22, -40)], fill(MUSTARD)),
    shape("Grille", [ell(38, 38, -22, -40)], fill("FF6B4A36") + stroke(INK, 3)),
    shape("Case", [rect(100, 62, 0, -41, 12)], fill(MUSTARD) + stroke(INK, 4)),
    shape("Handle", [rect(52, 20, 0, -76, 8)], stroke(INK, 4)),
    shape("Tip", [ell(10, 10, 53, -112)], fill(TEAL) + stroke(INK, 2.5)),
    shape("Antenna", [rect(3.5, 46)], fill(INK), 42, -92, rot=0.5),
    shape("FeetL", [rect(14, 8, -32, 0, 3)], fill(INK)),
    shape("FeetR", [rect(14, 8, 32, 0, 3)], fill(INK)),
    shape("Shadow", [rect(100, 62, 5, -36, 12)], fill(INK)),
], 0, 0, "9:55")
shapes.append(node("Ray", notes + [radio], RX, RY, "9:50"))
anims.append(anim("9:104", "Ray Sway", 240,
    keyed("9:55", keys("rotation", [(0, 0), (60, 0.035), (120, 0), (180, -0.035), (240, 0)])),
    blink("9:56", 240, 150)))
anims.append(still("9:105", "Ray Rest",
    keyed("9:50", keys("y", [(0, RY, "hold")])),
    keyed("9:51", keys("opacity", [(0, 0, "hold")])), keyed("9:52", keys("opacity", [(0, 0, "hold")]))))
anims.append(anim("9:106", "Ray Groove", 120,
    keyed("9:50", keys("y", [(0, RY), (15, RY - 10), (30, RY), (45, RY - 10), (60, RY), (75, RY - 10), (90, RY),
                             (105, RY - 10), (120, RY)])),
    keyed("9:51", keys("opacity", [(0, 0), (10, 1), (75, 1), (90, 0, "hold"), (120, 0, "hold")]),
          keys("y", [(0, -100), (90, -175, "hold"), (120, -100, "hold")]),
          keys("x", [(0, -20), (45, -34), (90, -22, "hold")])),
    keyed("9:52", keys("opacity", [(0, 0, "hold"), (55, 0), (65, 1), (110, 1), (120, 0)]),
          keys("y", [(0, -100, "hold"), (55, -100), (120, -160)]),
          keys("x", [(0, 24, "hold"), (55, 24), (120, 40)]))))
layers += [layer("9:204", "Ray Sway", "9:104"), playing_layer("9:205", "Ray Groove", "9:105", "9:106")]

# ---------------------------------------------------------------- TV guy's arms (inside the Mascot's Bob node)
arms = [node("ArmL", [shape("Arm", [rect(6, 24, 0, 12, 3)], fill(INK)),
                      shape("Hand", [ell(11, 11, 0, 25)], fill(PAPER) + stroke(INK, 2.5))], -45, -52, "9:60",
             ' rotation="0.35"'),
        node("ArmR", [shape("Arm", [rect(6, 24, 0, 12, 3)], fill(INK)),
                      shape("Hand", [ell(11, 11, 0, 25)], fill(PAPER) + stroke(INK, 2.5))], 45, -52, "9:61",
             ' rotation="-0.35"')]
WAVE = 600
wave = [(0, 0.35, "hold"), (420, 0.35), (440, 2.5)]
for i in range(4):
    wave += [(450 + 16 * i, 2.1), (458 + 16 * i, 2.6)]
wave += [(530, 2.5), (560, 0.35, "hold"), (WAVE, 0.35, "hold")]
anims.append(anim("9:107", "TV Wave", WAVE, keyed("9:60", keys("rotation", wave)),
                  keyed("9:61", keys("rotation", [(0, -0.35), (300, -0.45), (WAVE, -0.35)]))))
layers.append(layer("9:206", "TV Wave", "9:107"))

# ================================================================ write into scene.rml
def put(s, tag, body, before):
    begin, end = f"<!-- cast:{tag} begin -->", f"<!-- cast:{tag} end -->"
    block = f"{begin}\n{body}\n{end}\n"
    if begin in s:
        return re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n", lambda _: block, s, flags=re.S)
    assert s.count(before) == 1, before
    return s.replace(before, block + before)

s = SCENE.read_text()
s = put(s, "shapes", "\n".join(shapes), "        <!-- sunburst from the top-right")
s = put(s, "arms", "\n".join(arms), '                        <Shape x="6" y="-44" name="BodyShadow">')
s = put(s, "anims", "\n".join(anims), '        <LinearAnimation duration="240" loopValue="loop" name="Blink"')
s = put(s, "layers", "\n".join(layers), '            <StateMachineLayer name="Mascot Blink"')
SCENE.write_text(s)
print(f"cast written: {len(shapes)} characters, {len(anims)} animations, {len(layers)} layers")
