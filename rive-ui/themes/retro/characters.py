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
  Parade   along the floor: Vic the VHS tape, Gabby the handheld, Snap the
           camera (flash!), and Scoot the robot pup, who drags its bum across
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

# ---------------------------------------------------------------- the floor parade
# Walkers cross the bottom of the screen one way, then wait off-screen; each has
# its own period, so who meets whom keeps changing. Drawn facing right, feet at y=0.
FLOOR_Y = 1050
LEFT, RIGHT = -140, 2060


def legs(base, spread, shoe, top=-18, length=16):
    return [node(f"Leg{s}", [shape("Shin", [rect(7, length, 0, length / 2, 3)], fill(INK)),
                              shape("Shoe", [ell(15, 8, 3, length + 1)], fill(shoe) + stroke(INK, 2.5))],
                 x, top, f"{base}{i + 6}")
            for i, (s, x) in enumerate((("L", -spread), ("R", spread)))]


def stroll(base, name, body, leg_nodes, rightward, start, dur, period, step=14, amp=0.45, bob=4, scale=1.2, extra=()):
    """A walker: root (x) > Flip (faces the way it goes) > Body (bob) + legs (ids base+6, base+7)."""
    x0, x1 = (LEFT, RIGHT) if rightward else (RIGHT, LEFT)
    flip = 1 if rightward else -1
    shapes.append(node(name, [node("Flip", [body] + leg_nodes, 0, 0, f"{base}1",
                                   f' scaleX="{flip * scale}" scaleY="{scale}"')], x0, FLOOR_Y, f"{base}0"))
    def alt(a, b, rest=0):
        out, f, fl = [(0, rest, "hold")], start, False
        while f < start + dur:
            out.append((f, a if fl else b)); f += step; fl = not fl
        out += [(start + dur, rest, "hold"), (period, rest, "hold")]
        return out
    anims.append(anim(f"{base}9", f"{name} Stroll", period,
        keyed(f"{base}0", keys("x", [(0, x0, "hold"), (start, x0), (start + dur, x1, "hold"), (period, x1, "hold")])),
        keyed(f"{base}2", keys("y", alt(0, -bob))),
        keyed(f"{base}6", keys("rotation", alt(amp, -amp))),
        keyed(f"{base}7", keys("rotation", alt(-amp, amp))),
        *extra))
    layers.append(layer(f"{base}8", f"{name} Stroll", f"{base}9"))


# Vic the VHS tape: marches right to left
vic = node("Body", [
    eyes("10:13", 9, -50, 6, 9),
    shape("Mouth", [rect(12, 4, 0, -40, 2)], fill(INK)),
    shape("Label", [rect(56, 26, 0, -45, 4)], fill(PAPER) + stroke(INK, 2.5)),
    shape("Windows", [rect(18, 10, -22, -22, 3), rect(18, 10, 22, -22, 3)], fill("FF6B4A36") + stroke(INK, 2)),
    shape("Shell", [rect(96, 56, 0, -38, 6)], fill("FF3A2B22") + stroke(INK, 4)),
    shape("Shadow", [rect(96, 56, 5, -33, 6)], fill(INK)),
], 0, 0, "10:12")
stroll("10:1", "Vic", vic, legs("10:1", 22, MUSTARD), False, 300, 1500, 3000,
       extra=[blink("10:13", 3000, 1100)])

# Gabby the handheld: hops left to right
gabby = node("Body", [
    eyes("10:23", 8, -62, 5, 8),
    shape("Smile", [rect(10, 4, 0, -54, 2)], fill(INK)),
    shape("Screen", [rect(38, 30, 0, -60, 4)], fill("FF9FC08A") + stroke(INK, 2.5)),
    shape("Bezel", [rect(46, 38, 0, -60, 6)], fill("FF7A7F86")),
    shape("Pad", [rect(14, 5, -12, -26), rect(5, 14, -12, -26)], fill(INK)),
    shape("Buttons", [ell(9, 9, 10, -30), ell(9, 9, 20, -22)], fill(TOMATO) + stroke(INK, 2)),
    shape("Case", [rect(58, 86, 0, -50, 8)], fill("FFE3DCCB") + stroke(INK, 4)),
    shape("Shadow", [rect(58, 86, 5, -45, 8)], fill(INK)),
], 0, -6, "10:22")
stroll("10:2", "Gabby", gabby, legs("10:2", 14, TEAL, top=-12, length=12), True, 1700, 1000, 3600,
       step=10, amp=0.6, bob=12, extra=[blink("10:23", 3600, 2100)])

# Snap the camera: strolls right to left and fires the flash half way
snap = node("Body", [
    shape("Burst", ['<Star points="8" width="70" height="70" innerRadius="0.4" name="P"/>'], fill("EEFFF8EA"),
          30, -82, sid="10:34", extra=' opacity="0"'),
    eyes("10:33", 8, -52, 5, 8, -26),
    shape("Glint", [ell(8, 8, 8, -46)], fill(PAPER)),
    shape("Lens", [ell(24, 24, 14, -40)], fill(TEAL) + stroke(INK, 3)),
    shape("Ring", [ell(40, 40, 14, -40)], fill(INK)),
    shape("Flash", [rect(18, 10, 24, -74, 2)], fill(PAPER) + stroke(INK, 2.5)),
    shape("Top", [rect(28, 14, -14, -70, 4)], fill(TOMATO) + stroke(INK, 3)),
    shape("Box", [rect(84, 54, 0, -40, 9)], fill(TOMATO) + stroke(INK, 4)),
    shape("Shadow", [rect(84, 54, 5, -35, 9)], fill(INK)),
], 0, 0, "10:32")
SNAP_AT = 2600 + 700
stroll("10:3", "Snap", snap, legs("10:3", 20, TEAL), False, 2600, 1400, 4200,
       extra=[blink("10:33", 4200, 2900),
              keyed("10:34", keys("opacity", [(0, 0, "hold"), (SNAP_AT, 0), (SNAP_AT + 4, 1), (SNAP_AT + 24, 0, "hold"),
                                              (SNAP_AT + 40, 0), (SNAP_AT + 44, 1), (SNAP_AT + 64, 0, "hold"), (4200, 0, "hold")]),
                     keys("scaleX", [(0, 0.6, "hold"), (SNAP_AT, 0.6), (SNAP_AT + 20, 1.3, "hold"),
                                     (SNAP_AT + 40, 0.6), (SNAP_AT + 60, 1.3, "hold"), (4200, 0.6, "hold")]),
                     keys("scaleY", [(0, 0.6, "hold"), (SNAP_AT, 0.6), (SNAP_AT + 20, 1.3, "hold"),
                                     (SNAP_AT + 40, 0.6), (SNAP_AT + 60, 1.3, "hold"), (4200, 0.6, "hold")]))])

# Scoot the robot pup: a turn-of-the-millennium toy robot dog, white plastic with
# LED eyes. Sits on its bum and drags itself across, front paws paddling.
SHELL, JOINT, LED, GLOW = "FFF6F4EE", "FFAEB4BE", "FF6FE3E8", "556FE3E8"
def paw(n, nid, x):
    return node(n, [shape("Foot", [rect(14, 9, 2, 30, 3)], fill(SHELL) + stroke(INK, 2.5)),
                    shape("Knee", [ell(8, 8, 0, 14)], fill(TOMATO) + stroke(INK, 2)),
                    shape("Leg", [rect(9, 30, 0, 15, 3)], fill(JOINT) + stroke(INK, 3))], x, -30, nid)
def ear(nid, x, rot):
    return node("Ear", [shape("Panel", [rect(12, 26, 0, -12, 4)], fill(JOINT) + stroke(INK, 3)),
                        shape("Hinge", [ell(8, 8)], fill(TOMATO) + stroke(INK, 2))], x, -16, nid, f' rotation="{rot}"')
def heart(x, y):
    return [ell(6, 6, x - 2.5, y - 1.5), ell(6, 6, x + 2.5, y - 1.5),
            '<Triangle x="%s" y="%s" rotation="3.14159" width="11" height="7" name="V"/>' % (x, y + 3)]
puffs = [shape(f"Puff{i}", [ell(14, 10), ell(10, 8, 9, -3)], fill("CCFFF8EA") + stroke("88A88A6A", 2), -54 - 14 * i, -6,
               sid=f"10:4{5 + i}", extra=' opacity="0"') for i in range(2)]
dog = node("Body", [
    paw("PawNear", "10:43", 20),
    node("Head", [
        ear("10:470", -14, -0.8),
        shape("Hearts", heart(0, -4) + heart(16, -4), fill(TOMATO), sid="10:49", extra=' opacity="0"'),
        node("Leds", [shape("Dots", [ell(8, 8, 0, -4), ell(8, 8, 16, -4)], fill(LED)),
                      shape("Glow", [ell(14, 14, 0, -4), ell(14, 14, 16, -4)], fill(GLOW))], 0, 0, "10:48"),
        shape("Grille", [rect(10, 2, 26, 9), rect(10, 2, 26, 13)], fill(JOINT)),
        shape("Visor", [rect(36, 20, 8, -4, 9)], fill(INK)),
        shape("Muzzle", [rect(24, 18, 24, 8, 7)], fill(SHELL) + stroke(INK, 3)),
        shape("Dome", [rect(50, 42, 2, 0, 18)], fill(SHELL) + stroke(INK, 4)),
        ear("10:471", 14, 0.8),
    ], 30, -62, "10:44"),
    shape("Led", [ell(6, 6, -2, -32)], fill(LED) + stroke(INK, 1.5)),
    shape("Panel", [rect(30, 12, -10, -24, 5)], fill(TOMATO) + stroke(INK, 2.5), rot=-0.35),
    shape("Haunch", [rect(32, 18, -16, -10, 8)], fill(JOINT) + stroke(INK, 3)),
    shape("Belly", [rect(76, 44, -8, -26, 20)], fill(SHELL) + stroke(INK, 4), rot=-0.35),
    paw("PawFar", "10:42", 30),
    node("Tail", [shape("Tip", [ell(10, 10, 0, -26)], fill(TOMATO) + stroke(INK, 2.5)),
                  shape("Spring", [rect(4, 24, 0, -12, 2)], fill(JOINT) + stroke(INK, 2))], -44, -18, "10:41",
         ' rotation="-0.9"'),
] + puffs, 0, 0, "10:40")
SCOOT_START, SCOOT_PERIOD, HOP, LURCH = 900, 5400, 30, 20
xs, rock, near, far, head, tail_k = [(0, LEFT, "hold")], [(0, 0, "hold")], [(0, 0.3, "hold")], [(0, -0.3, "hold")], [(0, 0, "hold")], []
puff_k = {0: [(0, 0, "hold")], 1: [(0, 0, "hold")]}
x, f = LEFT, SCOOT_START
while x < RIGHT:
    xs += [(f, x), (f + 12, x + LURCH, "hold")]
    rock += [(f, 0), (f + 6, -0.12), (f + 14, 0.06), (f + 22, 0)]
    near += [(f, 0.35), (f + 12, -0.35), (f + HOP - 1, 0.35)]
    far += [(f, -0.35), (f + 12, 0.35), (f + HOP - 1, -0.35)]
    head += [(f, 0), (f + 8, 0.08), (f + 20, 0)]
    k = (f // HOP) % 2
    puff_k[k] += [(f + 6, 0), (f + 10, 1), (f + 26, 0, "hold")]
    x += LURCH; f += HOP
end = f
for lst, v in ((xs, RIGHT), (rock, 0), (near, 0.3), (far, -0.3), (head, 0)):
    lst += [(end, v, "hold"), (SCOOT_PERIOD, v, "hold")]
for k in puff_k:
    puff_k[k] += [(SCOOT_PERIOD, 0, "hold")]
assert end < SCOOT_PERIOD, end
shapes.append(node("Scoot", [node("Flip", [dog], 0, 0, "10:401", ' scaleX="1.25" scaleY="1.25"')], LEFT, FLOOR_Y, "10:400"))
anims.append(anim("10:409", "Scoot Drag", SCOOT_PERIOD,
    keyed("10:400", keys("x", xs)), keyed("10:40", keys("rotation", rock)),
    keyed("10:43", keys("rotation", near)), keyed("10:42", keys("rotation", far)),
    keyed("10:44", keys("rotation", head)),
    keyed("10:45", keys("opacity", puff_k[0])), keyed("10:46", keys("opacity", puff_k[1]))))
anims.append(anim("10:419", "Scoot Wag", 24,
    keyed("10:41", keys("rotation", [(0, -0.9), (12, -0.3), (24, -0.9)]))))
# robot quirks: LED eyes blink, switch to hearts now and then; ears twitch with a mechanical snap
anims.append(anim("10:429", "Scoot Robot", 360,
    keyed("10:48", keys("opacity", [(0, 1, "hold"), (220, 0, "hold"), (290, 1, "hold"), (360, 1, "hold")]),
          keys("scaleY", [(0, 1, "hold"), (120, 1), (124, 0.15), (130, 1, "hold"), (360, 1, "hold")])),
    keyed("10:49", keys("opacity", [(0, 0, "hold"), (220, 1, "hold"), (290, 0, "hold"), (360, 0, "hold")]),
          keys("scaleX", [(0, 1, "hold"), (220, 0.6), (230, 1.15), (240, 1), (250, 1.15), (260, 1, "hold"), (360, 1, "hold")]),
          keys("scaleY", [(0, 1, "hold"), (220, 0.6), (230, 1.15), (240, 1), (250, 1.15), (260, 1, "hold"), (360, 1, "hold")])),
    keyed("10:470", keys("rotation", [(0, -0.8, "hold"), (60, -1.25, "hold"), (68, -0.8, "hold"), (180, -1.25, "hold"),
                                      (186, -0.8, "hold"), (192, -1.25, "hold"), (198, -0.8, "hold"), (360, -0.8, "hold")])),
    keyed("10:471", keys("rotation", [(0, 0.8, "hold"), (64, 1.25, "hold"), (72, 0.8, "hold"), (220, 1.2, "hold"),
                                      (290, 0.8, "hold"), (360, 0.8, "hold")]))))
layers += [layer("10:408", "Scoot Drag", "10:409"), layer("10:418", "Scoot Wag", "10:419"), layer("10:428", "Scoot Robot", "10:429")]

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
