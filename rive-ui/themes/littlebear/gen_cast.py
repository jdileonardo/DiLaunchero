#!/usr/bin/env python3
"""Writes the Little Bear theme's forest and cast into scene.rml, between <!-- cast:... --> markers.

A sunny day in the woods, after the Little Bear books and TV show: our own
storybook caricatures, drawn here as simple ink-and-wash shapes. Re-run after
editing; only the marked regions are replaced:

    python3 themes/littlebear/gen_cast.py

Who is where (the app tiles sit on top of all of it):
  top bar      Owl, reading beside the clock (bops along when music plays);
               the sun, drifting clouds, two butterflies
  bottom left  the Bear house with chimney smoke; Mother Bear waving at the door;
               Grandfather Bear dozing and Grandmother Bear knitting on a bench;
               Hen pecking, with two chicks
  bottom mid   Cat asleep in the grass (and, now and then, "Boo!")
  bottom right Mitzi swinging from the big tree; Father Bear fishing
               at the pond; Frog hopping between lily pads
  walking by   Little Bear and Emily (carrying Lucy), Duck, Tutu, and No Feet
"""
import math
import re
from pathlib import Path

SCENE = Path(__file__).with_name("scene.rml")

INK, PAPER = "FF3B2A1E", "FFFFFAEE"
BERRY, HONEY, LEAF, LEAF_DK, SKY = "FFC0503A", "FFF4C14F", "FF6E9B4B", "FF557F38", "FF6FB6EA"
PINK, CREAM, WATER = "FFF2A08A", "FFF6E7C8", "FF74B6DC"
FLOOR = 1050

_n = [0]


def nid():
    _n[0] += 1
    return f"12:{_n[0]}"

# ---------------------------------------------------------------- drawing helpers

def fill(c, cid=None):
    i = f' id="{cid}"' if cid else ""
    return f'<Fill name="F"><SolidColor colorValue="{c}" name="C"{i}/></Fill>'


def stroke(c=INK, t=3):
    return f'<Stroke thickness="{t}" name="S"><SolidColor colorValue="{c}" name="C"/></Stroke>'


def fs(c, t=3):
    """fill + ink outline, the storybook look"""
    return fill(c) + stroke(INK, t)


def _rot(r):
    return f' rotation="{r}"' if r else ""


def rect(w, h, x=0, y=0, r=0, rot=0):
    rr = f' cornerRadiusTL="{r}"' if r else ""
    return f'<Rectangle x="{x}" y="{y}" width="{w}" height="{h}"{rr}{_rot(rot)} name="P"/>'


def ell(w, h, x=0, y=0, rot=0):
    return f'<Ellipse x="{x}" y="{y}" width="{w}" height="{h}"{_rot(rot)} name="P"/>'


def tri(w, h, x=0, y=0, rot=0):
    return f'<Triangle x="{x}" y="{y}" width="{w}" height="{h}"{_rot(rot)} name="P"/>'


def shape(name, paths, paint, x=0, y=0, rot=0, sid=None, extra=""):
    i = f' id="{sid}"' if sid else ""
    return f'<Shape x="{x}" y="{y}"{_rot(rot)}{extra} name="{name}"{i}>' + "".join(paths) + paint + "</Shape>"


def node(name, kids, x=0, y=0, oid=None, extra=""):
    i = f' id="{oid}"' if oid else ""
    return f'<Node x="{x}" y="{y}"{extra} name="{name}"{i}>' + "".join(kids) + "</Node>"


def eyes(oid, gap, y, w=5, h=7, x=0, c=INK):
    """Two eyes in a node of their own, so a blink can squash them (scaleY)."""
    return node("Eyes", [shape("Pupils", [ell(w, h, x - gap), ell(w, h, x + gap)], fill(c))], 0, y, oid)

def idof(xml):
    """The id of an element built by node()/shape() (its first id attribute)."""
    return re.search(r'id="([^"]+)"', xml[:xml.index(">")]).group(1)


# ---------------------------------------------------------------- animation helpers

def keys(prop, frames, interp="linear"):
    """frames: [(frame, value[, interp]), ...]; 'hold' keys jump, 'linear' keys glide to the next."""
    ks = "".join(
        f'<KeyFrameDouble frame="{f}" value="{round(v, 4)}" interpolationType="{rest[0] if rest else interp}"/>'
        for f, v, *rest in frames)
    return f'<KeyedProperty property="{prop}">{ks}</KeyedProperty>'


def keyed(oid, *props):
    return f'<KeyedObject objectId="{oid}">' + "".join(props) + "</KeyedObject>"


_a, _l = [0], [99]


def anim(name, dur, *objs):
    _a[0] += 1
    aid = f"13:{_a[0]}"
    anims.append(f'<LinearAnimation duration="{dur}" loopValue="loop" name="{name}" id="{aid}">' + "".join(objs)
                 + "</LinearAnimation>")
    _l[0] += 1
    lid = f"14:{_l[0]}"
    layers.append(f'<StateMachineLayer name="{name}" id="{lid}"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
                  f'<EntryState><StateTransition stateToId="{lid}1"/></EntryState>'
                  f'<AnimationState x="200" animationId="{aid}" id="{lid}1"/></StateMachineLayer>')


def blink(oid, period, *at):
    k = [(0, 1, "hold")]
    for t in at:
        k += [(t, 1), (t + 5, 0.1), (t + 10, 1, "hold")]
    return keyed(oid, keys("scaleY", k + [(period, 1, "hold")]))


def swing(oid, prop, a, b, period, ease=True):
    """a -> b -> a, smoothly (cubic) over one period."""
    it = "cubic" if ease else "linear"
    c = '<CubicEaseInterpolator x1="0.42" y1="0" x2="0.58" y2="1"/>'
    ks = "".join(f'<KeyFrameDouble frame="{f}" value="{v}" interpolationType="{it}">{c if ease else ""}</KeyFrameDouble>'
                 for f, v in ((0, a), (period // 2, b), (period, a)))
    return keyed(oid, f'<KeyedProperty property="{prop}">{ks}</KeyedProperty>')


shapes, backdrop, anims, layers = [], [], [], []

# ---------------------------------------------------------------- bears (front view)

def bear_head(fur, muzzle, eyes_id, w=56, h=50, y=-74, extra=()):
    """Ears, round head, pale muzzle, button nose. Extra parts (hats, glasses) go on top."""
    return list(extra) + [
        eyes(eyes_id, w * 0.18, y - h * 0.16),
        shape("Nose", [ell(w * 0.19, w * 0.13, 0, y + h * 0.06)], fill(INK)),
        shape("Mouth", [rect(w * 0.05, w * 0.12, 0, y + h * 0.18, 1)], fill(INK)),
        shape("Muzzle", [ell(w * 0.48, h * 0.38, 0, y + h * 0.14)], fs(muzzle, 2.5)),
        shape("Head", [ell(w, h, 0, y)], fs(fur)),
        shape("EarIn", [ell(w * 0.16, w * 0.16, -w * 0.38, y - h * 0.42), ell(w * 0.16, w * 0.16, w * 0.38, y - h * 0.42)],
              fill(muzzle)),
        shape("Ears", [ell(w * 0.32, w * 0.32, -w * 0.38, y - h * 0.42), ell(w * 0.32, w * 0.32, w * 0.38, y - h * 0.42)],
              fs(fur)),
    ]


def limb(name, oid, x, y, w, ln, c, end=None, end_c=None, rot=0, t=2.5):
    """An arm or leg hanging from a pivot at (x, y); optional paw/shoe at the end."""
    kids = []
    if end:
        kids.append(shape("End", [ell(end[0], end[1], end[2] if len(end) > 2 else 0, ln)], fs(end_c or c, t)))
    kids.append(shape("Limb", [rect(w, ln, 0, ln / 2, w / 2)], fs(c, t)))
    return node(name, kids, x, y, oid, _rot(rot) and f' rotation="{rot}"')

# ---------------------------------------------------------------- walkers

LEFT, RIGHT = -160, 2080


def walker(name, body, legs, rightward, start, dur, period, step=14, bob=4, scale=1.0, extra=(), body_id=None):
    """Crosses the bottom of the screen one way, then waits off-screen. legs: [(id, a, b), ...] swing a<->b."""
    root, flip = nid(), nid()
    x0, x1 = (LEFT, RIGHT) if rightward else (RIGHT, LEFT)
    d = 1 if rightward else -1
    shapes.append(node(name, [node("Flip", [body] + [l for l in legs if isinstance(l, str)], 0, 0, flip,
                                   f' scaleX="{d * scale}" scaleY="{scale}"')], x0, FLOOR, root))

    def alt(a, b, rest=0):
        out, f, fl = [(0, rest, "hold")], start, False
        while f < start + dur:
            out.append((f, a if fl else b)); f += step; fl = not fl
        return out + [(start + dur, rest, "hold"), (period, rest, "hold")]
    objs = [keyed(root, keys("x", [(0, x0, "hold"), (start, x0), (start + dur, x1, "hold"), (period, x1, "hold")]))]
    if body_id and bob:
        objs.append(keyed(body_id, keys("y", alt(0, -bob))))
    return objs, alt


# Little Bear and Emily (with Lucy), walking together left to right
LB_FUR, LB_MUZ = "FFA8733F", "FFEBCB98"
lb_legs = [limb("LegL", nid(), -11, -18, 15, 14, LB_FUR, (20, 11), LB_FUR),
           limb("LegR", nid(), 11, -18, 15, 14, LB_FUR, (20, 11), LB_FUR)]
lb_arms = [limb("ArmL", nid(), -22, -50, 12, 26, LB_FUR, rot=0.25),
           limb("ArmR", nid(), 22, -50, 12, 26, LB_FUR, rot=-0.25)]
lb_eyes = nid()
little_bear = node("LittleBear", [lb_arms[1]] + bear_head(LB_FUR, LB_MUZ, lb_eyes) + [
    shape("Belly", [ell(28, 30, 0, -34)], fill(LB_MUZ)),
    shape("Body", [ell(50, 52, 0, -36)], fs(LB_FUR)),
    lb_arms[0]] + lb_legs, 46, 0)

SKIN, HAIR, DRESS = "FFF7D6BC", "FFF0C75E", "FF7FA7D8"
em_legs = [limb("LegL", nid(), -8, -24, 7, 20, SKIN, (14, 8, 3), INK, t=2),
           limb("LegR", nid(), 8, -24, 7, 20, SKIN, (14, 8, 3), INK, t=2)]
em_arm = limb("ArmL", nid(), -18, -66, 9, 30, SKIN, rot=0.3, t=2)
em_eyes = nid()
lucy = node("Lucy", [
    shape("Face", [ell(5, 5, -3, -2), ell(5, 5, 3, -2)], fill(INK)),
    shape("Head", [ell(17, 17, 0, 0)], fs("FFF9E2CF", 2)),
    shape("Hair", [ell(22, 14, 0, -6)], fs("FFA0522D", 2)),
    shape("Dress", [tri(24, 26, 0, 20)], fs(BERRY, 2)),
    shape("Legs", [rect(4, 10, -5, 36, 2), rect(4, 10, 5, 36, 2)], fill(INK)),
], 22, -64)
emily = node("Emily", [
    lucy,
    shape("HugArm", [rect(9, 28, 0, 0, 4.5, rot=-1.0)], fs(SKIN, 2), 22, -60),
    shape("Knot", [ell(7, 7)], fs(BERRY, 2), 14, -124),
    shape("Bow", [tri(14, 16, -8, 0, rot=1.57), tri(14, 16, 8, 0, rot=-1.57)], fs(BERRY, 2), 14, -124),
    eyes(em_eyes, 8, -100, 5, 6),
    shape("Smile", [rect(10, 3, 0, -86, 1.5)], fill(INK)),
    shape("Cheeks", [ell(8, 5, -14, -90), ell(8, 5, 14, -90)], fill(PINK)),
    shape("Bangs", [ell(40, 16, 0, -112)], fs(HAIR, 2.5)),
    shape("Face", [ell(38, 40, 0, -96)], fs(SKIN, 2.5)),
    shape("Hair", [ell(50, 50, 0, -100)], fs(HAIR)),
    shape("Collar", [ell(22, 8, 0, -74)], fs(PAPER, 2)),
    shape("Pinafore", [rect(26, 34, 0, -48, 5)], fs(PAPER, 2)),
    shape("Dress", [tri(62, 56, 0, -50)], fs(DRESS)),
    em_arm,
] + em_legs, -36, 0)
pair_body = nid()
pair = node("Body", [little_bear, emily], 0, 0, pair_body)
objs, alt = walker("Little Bear & Emily", pair, [], True, 600, 1500, 3600, step=16, body_id=pair_body)
anim("Little Bear & Emily Walk", 3600, *objs,
     *(keyed(idof(l), keys("rotation", alt(a, -a))) for l, a in
       zip(lb_legs + em_legs + lb_arms, (0.4, -0.4, -0.35, 0.35, -0.3, 0.3))),
     blink(lb_eyes, 3600, 900, 1500, 2000), blink(em_eyes, 3600, 1100, 1800))


# Duck: yellow, long neck, waddles right to left
DUCK, DUCK_DK, BILL = "FFF6D85A", "FFE2BC3C", "FFF09A3A"
duck_feet = [limb("FootB", nid(), -6, -14, 5, 12, BILL, (16, 7, 5), BILL, t=2),
             limb("FootF", nid(), 8, -14, 5, 12, BILL, (16, 7, 5), BILL, t=2)]
duck_eyes = nid()
duck_body = nid()
duck = node("Body", [
    eyes(duck_eyes, 0, -66, 5, 6, 26),
    shape("Bill", [ell(24, 9, 44, -60)], fs(BILL, 2)),
    shape("Head", [ell(32, 28, 26, -64)], fs(DUCK)),
    shape("Neck", [rect(16, 34, 18, -44, 8)], fs(DUCK)),
    shape("Wing", [ell(32, 18, -4, -28, rot=0.15)], fs(DUCK_DK, 2.5)),
    shape("Tail", [tri(20, 16, -34, -36, rot=-1.1)], fs(DUCK)),
    shape("Body", [ell(62, 38, 0, -30)], fs(DUCK)),
] + duck_feet, 0, 0, duck_body)
objs, alt = walker("Duck", duck, [], False, 2000, 1500, 4200, step=12, body_id=None, scale=1.05)
anim("Duck Waddle", 4200, *objs,
     keyed(duck_body, keys("rotation", alt(0.1, -0.1))),
     keyed(idof(duck_feet[0]), keys("rotation", alt(0.45, -0.45))),
     keyed(idof(duck_feet[1]), keys("rotation", alt(-0.45, 0.45))),
     blink(duck_eyes, 4200, 2600, 3200))

# Tutu, Emily's Chihuahua: dashes across, yapping
TAN = "FFDDB27C"
tutu_legs = [limb(n, nid(), x, -14, 6, 12, TAN, t=2) for n, x in (("BackL", -14), ("FrontL", 14))]
tutu_legs_far = [limb(n, nid(), x, -14, 6, 12, "FFC89A64", t=2) for n, x in (("BackR", -10), ("FrontR", 18))]
yap, tutu_body = nid(), nid()
tutu = node("Body", [
    shape("Yap", [rect(10, 2.5, 0, -6, 1, rot=-0.5), rect(12, 2.5, 2, 0, 1), rect(10, 2.5, 0, 6, 1, rot=0.5)],
          fill(INK), 52, -40, sid=yap, extra=' opacity="0"'),
    tutu_legs[1], tutu_legs[0],
    shape("Eye", [ell(6, 7, 26, -40)], fill(INK)),
    shape("Nose", [ell(5, 4, 41, -36)], fill(INK)),
    shape("Snout", [ell(14, 10, 36, -34)], fs(TAN, 2)),
    shape("Ears", [tri(14, 22, 16, -58, rot=-0.3), tri(14, 22, 30, -58, rot=0.3)], fs(TAN, 2)),
    shape("Head", [ell(28, 26, 26, -40)], fs(TAN, 2.5)),
    shape("Tail", [rect(4, 18, -24, -36, 2, rot=-0.6)], fs(TAN, 2)),
    shape("Body", [ell(46, 22, 0, -26)], fs(TAN, 2.5)),
] + tutu_legs_far, 0, 0, tutu_body)
objs, alt = walker("Tutu", tutu, [], True, 3000, 330, 3900, step=6, body_id=tutu_body, bob=6, scale=1.1)
YAPS = [3060, 3140, 3220]
anim("Tutu Dash", 3900, *objs,
     *(keyed(idof(l), keys("rotation", alt(a, -a))) for l, a in
       zip(tutu_legs + tutu_legs_far, (0.6, -0.6, -0.6, 0.6))),
     keyed(yap, keys("opacity", [(0, 0, "hold")] + [k for t in YAPS for k in ((t, 1, "hold"), (t + 14, 0, "hold"))]
                     + [(3900, 0, "hold")])))

# No Feet, the green garter snake: slithers slowly right to left through the grass
SNAKE, SNAKE_LT = "FF7DB04A", "FFB9D97A"
N_SEG = 16
segs = [nid() for _ in range(N_SEG)]  # the green body, one id per segment
inks = [nid() for _ in range(N_SEG)]  # matching ink discs underneath, so only the outer edge shows a line
tongue = nid()
snake_kids = [
    shape("Tongue", [rect(10, 2, 0, 0), rect(5, 2, 5, -2, rot=-0.5), rect(5, 2, 5, 2, rot=0.5)], fill(BERRY),
          26, -8, sid=tongue),
    shape("Eye", [ell(5, 6, 8, -12)], fill(INK)),
    shape("Smile", [rect(8, 2, 10, -4, 1)], fill(INK)),
    shape("Head", [ell(28, 20, 4, -9)], fs(SNAKE, 2.5)),
]
widths = [17 - i * 0.75 for i in range(N_SEG)]
# garter stripe: a pale dot on every other segment, riding with it
snake_kids += [shape(f"Seg{i}", [ell(w, w * 0.8)] + ([ell(w * 0.45, w * 0.22, 0, -w * 0.12)] if i % 2 == 0 else []),
                     fill(SNAKE), -10 - i * 6, -8, sid=s) for i, (s, w) in enumerate(zip(segs, widths))]
snake_kids += [shape(f"Ink{i}", [ell(w + 4, w * 0.8 + 4)], fill(INK), -10 - i * 6, -8, sid=k)
               for i, (k, w) in enumerate(zip(inks, widths))]
objs, _ = walker("No Feet", node("Body", snake_kids), [], False, 300, 2700, 4800, step=30, scale=1.0)
WAVE = 60
anim("No Feet Slither", 4800, *objs)
anim("No Feet Wiggle", WAVE, *(keyed(s, keys("y", [(f, -8 - 5 * math.sin(2 * math.pi * (f / WAVE) + i * 0.6))
                                                   for f in range(0, WAVE + 1, 10)]))
                               for i, s in list(enumerate(segs)) + list(enumerate(inks))),
     keyed(tongue, keys("scaleX", [(0, 0, "hold"), (30, 0), (34, 1), (44, 1), (48, 0, "hold"), (WAVE, 0, "hold")])))

# ---------------------------------------------------------------- the house and the bench folk

def house():
    x, top = 150, FLOOR - 120
    smoke = []
    for i in range(3):
        s = nid()
        smoke.append((s, i))
        backdrop.append(shape(f"Smoke{i}", [ell(22, 18), ell(16, 14, 10, -6)], fill("E6FFFFFF") + stroke("66A0A8B0", 2),
                              x + 50, top - 70, sid=s, extra=' opacity="0"'))
    backdrop.append(node("BearHouse", [
        shape("Knob", [ell(5, 5, 12, 0)], fill(HONEY), 0, FLOOR - 32),
        shape("Door", [rect(38, 64, 0, FLOOR - 32, 14)], fs("FF7A5133"), 0, 0),
        shape("Mullions", [rect(3, 30, -58, 0), rect(34, 3, -58, 0), rect(3, 30, 58, 0), rect(34, 3, 58, 0)], fill(INK),
              0, FLOOR - 72),
        shape("Windows", [rect(34, 30, -58, 0, 4), rect(34, 30, 58, 0, 4)], fs("FFFFE7A6", 2.5), 0, FLOOR - 72),
        shape("Shutters", [rect(10, 32, -82, 0, 2), rect(10, 32, -34, 0, 2), rect(10, 32, 34, 0, 2), rect(10, 32, 82, 0, 2)],
              fs(LEAF, 2), 0, FLOOR - 72),
        shape("Beams", [rect(176, 6, 0, FLOOR - 104), rect(6, 116, -86, FLOOR - 58), rect(6, 116, 86, FLOOR - 58)],
              fill("FF8A5A36")),
        shape("Walls", [rect(176, 116, 0, FLOOR - 58, 4)], fs("FFF4E3C2")),
        shape("RoofEdge", [rect(216, 10, 0, top - 4, 5)], fs("FF8E3F2C", 2.5)),
        shape("Roof", [tri(228, 92, 0, top - 46)], fs("FFB4573D")),
        shape("Chimney", [rect(26, 54, 50, top - 64, 3)], fs("FFB8694C")),
        shape("Step", [rect(56, 8, 0, FLOOR - 2, 3)], fs("FFB9A68C", 2)),
    ], x, 0))
    T = 240
    anim("Chimney Smoke", T, *(keyed(s, keys("opacity", [(0, 0, "hold"), (i * 80, 0), (i * 80 + 10, 0.9), (min(T, i * 80 + 200), 0),
                                              (T, 0, "hold")]),
                                    keys("y", [(0, top - 70, "hold"), (i * 80, top - 70), (min(T, i * 80 + 200), top - 160),
                                               (T, top - 160, "hold")]),
                                    keys("x", [(0, x + 50, "hold"), (i * 80, x + 50), (min(T, i * 80 + 200), x + 80),
                                               (T, x + 80, "hold")]),
                                    keys("scaleX", [(0, 0.6, "hold"), (i * 80, 0.6), (min(T, i * 80 + 200), 1.6),
                                                    (T, 1.6, "hold")]),
                                    keys("scaleY", [(0, 0.6, "hold"), (i * 80, 0.6), (min(T, i * 80 + 200), 1.6),
                                                    (T, 1.6, "hold")]))
                               for s, i in smoke))


house()

# Mother Bear: blue dress, white apron; waves now and then
MB_FUR, MB_MUZ = "FF9A673A", "FFE6C391"
mb_eyes, mb_wave = nid(), nid()
mb_wave_arm = limb("ArmR", mb_wave, 26, -84, 14, 34, MB_FUR, rot=-0.3)
mother = node("MotherBear", [mb_wave_arm] + bear_head(MB_FUR, MB_MUZ, mb_eyes, 62, 56, -116) + [
    shape("Apron", [rect(34, 44, 0, -40, 6)], fs(PAPER, 2.5)),
    shape("Straps", [rect(5, 28, -12, -76, 2), rect(5, 28, 12, -76, 2)], fs(PAPER, 1.5)),
    shape("Dress", [tri(80, 92, 0, -48), rect(44, 30, 0, -78, 12)], fs("FF7C9ECB")),
    limb("ArmL", None, -26, -84, 14, 34, MB_FUR, rot=0.25),
    shape("Feet", [ell(22, 12, -14, -4), ell(22, 12, 14, -4)], fs(MB_FUR, 2.5)),
], 290, FLOOR)
shapes.append(mother)
W = 900
wave = [(0, -0.3, "hold"), (600, -0.3), (618, -2.5)]
for i in range(4):
    wave += [(626 + 14 * i, -2.1), (633 + 14 * i, -2.6)]
wave += [(700, -2.5), (730, -0.3, "hold"), (W, -0.3, "hold")]
anim("Mother Bear Wave", W, keyed(mb_wave, keys("rotation", wave)), blink(mb_eyes, W, 200, 520, 800))

# The bench, with Grandfather Bear (dozing) and Grandmother Bear (knitting)
BX = 455
backdrop.append(shape("Bench", [rect(170, 10, BX, FLOOR - 40, 3), rect(170, 8, BX, FLOOR - 82, 3), rect(170, 8, BX, FLOOR - 66, 3),
                                rect(8, 40, BX - 74, FLOOR - 20), rect(8, 40, BX + 74, FLOOR - 20),
                                rect(8, 50, BX - 74, FLOOR - 70), rect(8, 50, BX + 74, FLOOR - 70)], fs("FF9A6A42", 2.5)))


def seated(name, fur, muz, x, head_id, eyes_id, outfit, extra_head=(), hands=()):
    """A bear on the bench: head (in its own node), outfit, round body, short legs dangling."""
    head = node("Head", bear_head(fur, muz, eyes_id, 50, 44, -36, extra_head), 0, -54, head_id)
    return node(name, list(hands) + [head] + outfit + [
        shape("Body", [ell(54, 52, 0, -66)], fs(fur)),
        shape("Legs", [rect(14, 26, -12, -32, 7), rect(14, 26, 12, -32, 7)], fs(fur, 2.5)),
        shape("Feet", [ell(20, 11, -13, -18), ell(20, 11, 13, -18)], fs(fur, 2.5)),
    ], x, FLOOR)


def specs(y):
    return shape("Specs", [ell(15, 13, -10, y), ell(15, 13, 10, y), rect(6, 2, 0, y)], stroke(INK, 2.2))


GF_FUR, GF_MUZ, GM_FUR, GM_MUZ = "FF8E7967", "FFE2D3C2", "FFA27A55", "FFEBD2B0"
gf_head, gf_eyes, gm_eyes, needles = nid(), nid(), nid(), nid()
grandpa = seated("GrandfatherBear", GF_FUR, GF_MUZ, BX - 40, gf_head, gf_eyes,
                 [shape("Buttons", [ell(4, 4, 0, -76), ell(4, 4, 0, -64)], fill(HONEY)),
                  shape("Vest", [rect(36, 40, 0, -68, 10)], fs("FF5E8A57", 2.5))],
                 extra_head=[specs(-44), shape("Hat", [rect(46, 6, 0, -58, 3), rect(32, 18, 0, -68, 4)], fs("FF6B5A4A", 2.5))])
grandma = seated("GrandmotherBear", GM_FUR, GM_MUZ, BX + 40, None, gm_eyes,
                 [shape("ShawlTie", [tri(16, 14, 0, -70, rot=3.14)], fs("FFA48BC6", 2)),
                  shape("Shawl", [ell(60, 30, 0, -82)], fs("FFB89FD6", 2.5))],
                 extra_head=[specs(-44)],
                 hands=[node("Needles", [shape("Knitting", [rect(20, 12, 0, 6, 3)], fs(BERRY, 2)),
                                         shape("N", [rect(3, 30, -6, 0, 1.5, rot=0.6), rect(3, 30, 6, 0, 1.5, rot=-0.6)],
                                               fs("FFD6C6A8", 1.5))], 0, -48, needles)])
shapes += [grandpa, grandma]
backdrop.insert(0, shape("YarnBall", [ell(18, 18, 0, 0), rect(14, 2, 0, -2, rot=0.5), rect(14, 2, 0, 3, rot=0.4)],
                         fill(BERRY) + stroke(INK, 2), BX + 108, FLOOR - 8))
D = 600
anim("Grandfather Doze", D, keyed(gf_head, keys("rotation", [(0, 0), (300, 0.22), (420, 0.28), (436, 0, "hold"), (D, 0, "hold")]),
                                 keys("y", [(0, -54), (300, -48), (420, -46), (436, -54, "hold"), (D, -54, "hold")])),
     keyed(gf_eyes, keys("scaleY", [(0, 1, "hold"), (200, 1), (260, 0.1, "hold"), (436, 1, "hold"), (D, 1, "hold")])))
anim("Grandmother Knit", 40, keyed(needles, keys("rotation", [(0, -0.12), (10, 0.12), (20, -0.12), (30, 0.12), (40, -0.12)]),
                                  keys("y", [(0, -48), (10, -46), (20, -48), (30, -46), (40, -48)])),
     )
anim("Grandmother Blink", 420, blink(gm_eyes, 420, 150, 380))

# Hen, fussing about with two chicks
HEN, COMB = "FFFFF7EA", "FFD9483A"
hen_head = nid()
hen = node("Hen", [
    node("Head", [
        shape("Eye", [ell(5, 6, 6, -2)], fill(INK)),
        shape("Beak", [tri(10, 12, 18, 2, rot=1.57)], fs(HONEY, 2)),
        shape("Wattle", [ell(7, 10, 11, 12)], fill(COMB)),
        shape("Head", [ell(26, 26, 4, 0)], fs(HEN, 2.5)),
        shape("Comb", [ell(9, 10, -2, -14), ell(9, 11, 5, -16), ell(8, 9, 11, -13)], fs(COMB, 2)),
    ], 16, -50, hen_head),
    shape("Wing", [ell(30, 20, -6, -30, rot=0.2)], fs("FFEEE2CC", 2.5)),
    shape("Tail", [tri(20, 30, -30, -42, rot=-0.5), tri(16, 24, -24, -48, rot=-0.2)], fs(HEN, 2.5)),
    shape("Body", [ell(56, 42, -2, -30)], fs(HEN)),
    shape("Legs", [rect(3, 14, -8, -6), rect(3, 14, 6, -6), rect(10, 3, -5, 0), rect(10, 3, 9, 0)], fill(HONEY)),
], 640, FLOOR - 2)
chicks = []
for i, cx in enumerate((700, 730)):
    c = nid()
    chicks.append(c)
    shapes.append(node(f"Chick{i}", [
        shape("Eye", [ell(3.5, 4, 3, -14)], fill(INK)),
        shape("Beak", [tri(6, 7, 11, -12, rot=1.57)], fill(BILL)),
        shape("Body", [ell(18, 16, 0, -10), ell(13, 12, 3, -16)], fs("FFFCE27A", 2)),
        shape("Legs", [rect(2, 5, -3, -1), rect(2, 5, 3, -1)], fill(BILL)),
    ], cx, FLOOR, c, ' scaleX="-1"' if i else ""))
shapes.append(hen)
P = 360
anim("Hen Peck", P, keyed(hen_head, keys("rotation", [(0, 0, "hold"), (100, 0), (110, 1.0), (118, 0.9), (124, 1.0), (134, 0),
                                                     (240, 0), (250, 1.0), (262, 0, "hold"), (P, 0, "hold")]),
                          keys("y", [(0, -50, "hold"), (100, -50), (110, -30), (124, -30), (134, -50),
                                     (240, -50), (250, -30), (262, -50, "hold"), (P, -50, "hold")])),
     *(keyed(c, keys("y", [(0, FLOOR, "hold"), (40 + 60 * i, FLOOR), (48 + 60 * i, FLOOR - 12), (56 + 60 * i, FLOOR),
                           (64 + 60 * i, FLOOR - 12), (72 + 60 * i, FLOOR, "hold"), (P, FLOOR, "hold")]))
       for i, c in enumerate(chicks)))

# ---------------------------------------------------------------- Cat, asleep (and "Boo!")
CAT, CAT_W = "FF2F2B2C", "FFF5F0E8"
cat_body, cat_tail, cat_shut, cat_open, cat_bubble = nid(), nid(), nid(), nid(), nid()
zs = [nid() for _ in range(2)]


def zee(s):
    return [rect(10 * s, 2.5 * s, 0, -6 * s), rect(13 * s, 2.5 * s, 0, 0, rot=-0.85), rect(10 * s, 2.5 * s, 0, 6 * s)]


cat = node("Cat", [
    *(shape(f"Z{i}", zee(1 + 0.3 * i), fill("FF4A5C78"), 40, -60, sid=z, extra=' opacity="0"') for i, z in enumerate(zs)),
    node("Bubble", [
        shape("Bang", [rect(5, 16, 0, -6, 2.5), ell(6, 6, 0, 8)], fill(BERRY)),
        shape("Balloon", [ell(40, 34, 0, 0), tri(10, 12, -12, 18, rot=2.6)], fs(PAPER, 2.5)),
    ], 44, -86, cat_bubble, ' opacity="0"'),
    node("Body", [
        shape("EyesOpen", [ell(9, 11, 18, -32), ell(9, 11, 34, -32), ell(4, 6, 19, -32), ell(4, 6, 35, -32)],
              fill("FFE8D25A"), sid=cat_open, extra=' opacity="0"'),
        shape("EyesShut", [rect(9, 2.5, 18, -30, 1, rot=0.2), rect(9, 2.5, 34, -30, 1, rot=-0.2)], fill(CAT_W), sid=cat_shut),
        shape("Nose", [tri(6, 4, 26, -24, rot=3.14)], fill(PINK)),
        shape("Muzzle", [ell(22, 14, 26, -22)], fill(CAT_W)),
        shape("Ears", [tri(14, 16, 14, -44, rot=-0.3), tri(14, 16, 38, -44, rot=0.3)], fs(CAT, 2)),
        shape("Head", [ell(40, 34, 26, -30)], fs(CAT, 2.5)),
        shape("Chest", [ell(26, 22, 8, -16)], fill(CAT_W)),
        shape("Paws", [ell(14, 8, 16, -4), ell(14, 8, 30, -4)], fs(CAT_W, 2)),
        shape("Body", [ell(76, 36, -6, -18)], fs(CAT)),
    ], 0, 0, cat_body),
    node("Tail", [shape("Tip", [ell(12, 10, 40, 0)], fs(CAT_W, 2)),
                  shape("Tail", [rect(44, 10, 20, 0, 5)], fs(CAT, 2.5))], -38, -10, cat_tail, ' rotation="3.0"'),
], 1010, FLOOR)
shapes.append(cat)
C = 1500
BOO = 1200
anim("Cat Tail", 150, swing(cat_tail, "rotation", 2.8, 3.3, 150))
anim("Cat Nap", C,
     keyed(cat_body, keys("scaleY", [(f, 1.0 + (0.05 if (f // 60) % 2 else 0)) for f in range(0, BOO, 60)]
                          + [(BOO, 1), (BOO + 6, 1.25), (BOO + 12, 1.15, "hold"), (BOO + 120, 1.15), (BOO + 140, 1, "hold"), (C, 1, "hold")]),
           keys("y", [(0, 0, "hold"), (BOO, 0), (BOO + 6, -14), (BOO + 12, -6, "hold"), (BOO + 120, -6), (BOO + 140, 0, "hold"),
                      (C, 0, "hold")])),
     keyed(cat_open, keys("opacity", [(0, 0, "hold"), (BOO, 1, "hold"), (BOO + 130, 0, "hold"), (C, 0, "hold")])),
     keyed(cat_shut, keys("opacity", [(0, 1, "hold"), (BOO, 0, "hold"), (BOO + 130, 1, "hold"), (C, 1, "hold")])),
     keyed(cat_bubble, keys("opacity", [(0, 0, "hold"), (BOO + 4, 1, "hold"), (BOO + 110, 1), (BOO + 124, 0, "hold"), (C, 0, "hold")]),
           keys("scaleX", [(0, 0.3, "hold"), (BOO + 4, 0.3), (BOO + 12, 1.15), (BOO + 18, 1, "hold"), (C, 1, "hold")]),
           keys("scaleY", [(0, 0.3, "hold"), (BOO + 4, 0.3), (BOO + 12, 1.15), (BOO + 18, 1, "hold"), (C, 1, "hold")])),
     *(keyed(z, keys("opacity", [(0, 0, "hold")] + [k for t in range(i * 90, BOO - 180, 180)
                                                     for k in ((t, 0), (t + 30, 1), (t + 150, 0, "hold"))] + [(C, 0, "hold")]),
             keys("y", [(0, -50, "hold")] + [k for t in range(i * 90, BOO - 180, 180)
                                              for k in ((t, -50), (t + 150, -110, "hold"))] + [(C, -50, "hold")]),
             keys("x", [(0, 40, "hold")] + [k for t in range(i * 90, BOO - 180, 180)
                                             for k in ((t, 40), (t + 150, 62, "hold"))] + [(C, 40, "hold")]))
       for i, z in enumerate(zs)))

# ---------------------------------------------------------------- the big tree, Mitzi, the pond, Father Bear, Frog
TX = 1330
CANOPY = [(150, 110, -40, -190), (170, 120, 50, -200), (130, 100, 10, -250), (120, 90, 100, -150), (110, 80, -90, -170)]
CANOPY_BACK = [(160, 120, -70, -150), (150, 110, 130, -210)]
backdrop.append(node("BigTree", [
    shape("Canopy", [ell(w, h, x, y) for w, h, x, y in CANOPY], fill(LEAF)),
    shape("CanopyBack", [ell(w, h, x, y) for w, h, x, y in CANOPY_BACK], fill(LEAF_DK)),
    shape("CanopyInk", [ell(w + 6, h + 6, x, y) for w, h, x, y in CANOPY + CANOPY_BACK], fill(INK)),
    shape("Branch", [rect(120, 14, -60, -118, 7, rot=0.12)], fs("FF7E5636")),
    shape("Trunk", [rect(38, 170, 0, -85, 8), ell(70, 16, 0, -4)], fs("FF8A5E3A")),
], TX, FLOOR))
MZ, MZ_FACE = "FF8A5632", "FFEBC79C"
mitzi_eyes, mitzi = nid(), nid()
shapes.append(node("Mitzi", [
    shape("Hand", [ell(12, 10, 0, 0)], fs(MZ_FACE, 2)),
    shape("Arm", [rect(8, 34, 0, 17, 4)], fs(MZ, 2)),
    eyes(mitzi_eyes, 6, 46, 4, 6),
    shape("Grin", [rect(10, 3, 0, 58, 1.5)], fill(INK)),
    shape("Face", [ell(16, 16, -6, 48), ell(16, 16, 6, 48), ell(24, 14, 0, 56)], fill(MZ_FACE)),
    shape("Head", [ell(34, 32, 0, 50)], fs(MZ, 2.5)),
    shape("Ears", [ell(12, 12, -18, 48), ell(12, 12, 18, 48)], fs(MZ_FACE, 2)),
    shape("ArmL", [rect(8, 26, -14, 78, 4, rot=0.5)], fs(MZ, 2)),
    shape("Body", [ell(28, 34, 0, 80)], fs(MZ, 2.5)),
    shape("Belly", [ell(16, 20, 0, 82)], fill(MZ_FACE)),
    shape("Legs", [rect(8, 22, -8, 104, 4, rot=0.2), rect(8, 22, 8, 104, 4, rot=-0.2)], fs(MZ, 2)),
    shape("Tail", [rect(6, 40, 14, 100, 3, rot=-0.9)], fs(MZ, 2)),
], TX - 108, FLOOR - 130, mitzi))
anim("Mitzi Swing", 150, swing(mitzi, "rotation", -0.35, 0.35, 150), blink(mitzi_eyes, 150, 90))

PX, PW = 1720, 380
backdrop.insert(0, node("Pond", [
    shape("Pads", [ell(46, 14, 50, 4), ell(40, 12, 120, -2)], fs(LEAF, 2)),
    shape("Shine", [ell(120, 8, -60, 4), ell(60, 6, 80, 12)], fill("88FFFFFF")),
    shape("Water", [ell(PW, 64, 0, 0)], fs(WATER)),
    shape("Reeds", [rect(4, 50, -PW / 2 + 6, -28, 2, rot=-0.15), rect(4, 60, -PW / 2 + 18, -32, 2, rot=0.05),
                    rect(4, 46, PW / 2 - 14, -26, 2, rot=0.15)], fs(LEAF_DK, 1.5)),
    shape("Cattails", [rect(8, 18, -PW / 2 + 2, -52, 4, rot=-0.15), rect(8, 18, -PW / 2 + 19, -62, 4, rot=0.05)],
          fs("FF7E5636", 1.5)),
], PX, FLOOR - 2))

FB_FUR, FB_MUZ, NAVY = "FF6E4A2E", "FFD9B78C", "FF34507A"
fb_eyes, rod, bobber, fish = nid(), nid(), nid(), nid()
father = node("FatherBear", [
    node("Rod", [
        shape("Line", [rect(1.5, 173, 154, -30)], fill("AA3B2A1E")),
        shape("Pole", [rect(4, 190, 75, -66, 2, rot=1.0)], fs("FF8A5E3A", 1.5)),
    ], 20, -60, rod),
    shape("Paws", [ell(16, 14, 22, -60)], fs(FB_FUR, 2.5)),
] + bear_head(FB_FUR, FB_MUZ, fb_eyes, 60, 54, -120, extra=[
    shape("CapBand", [rect(46, 6, 0, -144)], fill(PAPER)),
    shape("Brim", [rect(52, 8, 4, -138, 4)], fs(INK, 1)),
    shape("Cap", [rect(46, 22, 0, -152, 8)], fs(NAVY, 2.5)),
]) + [
    shape("Ribs", [rect(52, 3, 0, -50), rect(52, 3, 0, -42)], fill("FF27405F")),
    shape("Sweater", [rect(66, 70, 0, -62, 22)], fs(NAVY)),
    shape("Legs", [ell(26, 16, -14, -26), ell(26, 16, 18, -26)], fs(FB_FUR, 2.5)),
    shape("Stump", [rect(56, 26, 0, -13, 4), ell(56, 10, 0, -26)], fs("FF9A6A42", 2.5)),
], 1500, FLOOR)
shapes.append(father)
shapes.insert(0, shape("Bobber", [ell(12, 12, 0, -4), rect(12, 6, 0, 1)], fill(BERRY) + stroke(INK, 2), 1670, FLOOR - 4,
                       sid=bobber))
shapes.insert(0, node("Fish", [shape("Eye", [ell(4, 4, 12, -2)], fill(INK)),
                               shape("Fish", [ell(34, 16), tri(14, 16, -20, 0, rot=-1.57)], fs("FFE88A4A", 2))],
                      1790, FLOOR + 40, fish))
F = 1200
TUG = 900
anim("Father Bear Fishing", F,
     keyed(rod, keys("rotation", [(0, 0), (120, 0.04), (240, 0), (TUG, 0), (TUG + 8, -0.12), (TUG + 60, -0.08), (TUG + 90, 0, "hold"),
                                  (F, 0, "hold")])),
     keyed(bobber, keys("y", [(f, FLOOR - 4 + (2 if (f // 40) % 2 else -1)) for f in range(0, TUG, 40)]
                        + [(TUG, FLOOR - 4), (TUG + 6, FLOOR + 6), (TUG + 50, FLOOR + 4), (TUG + 70, FLOOR - 4, "hold"), (F, FLOOR - 4, "hold")])),
     keyed(fish, keys("y", [(0, FLOOR + 40, "hold"), (TUG + 10, FLOOR + 40), (TUG + 40, FLOOR - 90), (TUG + 70, FLOOR + 40, "hold"),
                            (F, FLOOR + 40, "hold")]),
           keys("x", [(0, 1790, "hold"), (TUG + 10, 1790), (TUG + 70, 1730, "hold"), (F, 1790, "hold")]),
           keys("rotation", [(0, -0.8, "hold"), (TUG + 10, -0.8), (TUG + 70, 1.0, "hold"), (F, -0.8, "hold")])),
     blink(fb_eyes, F, 300, 700, TUG + 20))

frog_root, frog_sac, frog_eyes = nid(), nid(), nid()
FROG = "FF6FAE44"
shapes.insert(0, node("Frog", [
    eyes(frog_eyes, 8, -24, 4, 5),
    shape("EyeBumps", [ell(13, 13, -8, -24), ell(13, 13, 8, -24)], fs(FROG, 2)),
    shape("Smile", [rect(14, 2, 0, -12, 1)], fill(INK)),
    shape("Sac", [ell(16, 10, 0, -6)], fs("FFDDEB9C", 1.5), sid=frog_sac),
    shape("Body", [ell(34, 22, 0, -12)], fs(FROG, 2.5)),
    shape("Legs", [ell(14, 8, -14, -4), ell(14, 8, 14, -4)], fs(FROG, 2)),
], PX + 120, FLOOR - 2, frog_root))
G = 720
anim("Frog", G,
     keyed(frog_root, keys("x", [(0, PX + 120, "hold"), (300, PX + 120), (324, PX + 50, "hold"),
                                 (660, PX + 50), (684, PX + 120, "hold"), (G, PX + 120, "hold")]),
           keys("y", [(0, FLOOR - 2, "hold"), (300, FLOOR - 2), (312, FLOOR - 40), (324, FLOOR + 4, "hold"),
                      (660, FLOOR + 4), (672, FLOOR - 40), (684, FLOOR - 2, "hold"), (G, FLOOR - 2, "hold")])),
     keyed(frog_sac, keys("scaleX", [(0, 1, "hold")] + [k for t in (100, 140, 480, 520) for k in ((t, 1), (t + 10, 1.8), (t + 20, 1, "hold"))]
                          + [(G, 1, "hold")]),
           keys("scaleY", [(0, 1, "hold")] + [k for t in (100, 140, 480, 520) for k in ((t, 1), (t + 10, 1.8), (t + 20, 1, "hold"))]
                + [(G, 1, "hold")])),
     blink(frog_eyes, G, 220, 600))

# Moose, peeking over the hill now and then
moose = nid()
moose_node = (node("Moose", [
    shape("Eyes", [ell(5, 6, -9, -4), ell(5, 6, 9, -4)], fill(INK)),
    shape("Nostrils", [ell(4, 3, -5, 28), ell(4, 3, 5, 28)], fill(INK)),
    shape("Snout", [ell(30, 26, 0, 24)], fs("FF8A6448")),
    shape("Head", [ell(40, 52, 0, 4)], fs("FF6E4C33")),
    shape("Ears", [ell(12, 22, -24, -18, rot=-0.9), ell(12, 22, 24, -18, rot=0.9)], fs("FF6E4C33", 2.5)),
    shape("Antlers", [ell(54, 22, -42, -32, rot=-0.3), ell(54, 22, 42, -32, rot=0.3), ell(10, 18, -62, -46), ell(10, 18, -46, -50),
                      ell(10, 18, 62, -46), ell(10, 18, 46, -50)], fs("FFD8B886", 2.5)),
], 830, 1110, moose))
M = 2700
anim("Moose Peek", M, keyed(moose, keys("y", [(0, 1110, "hold"), (1500, 1110), (1600, 975), (1900, 975), (2000, 1110, "hold"), (M, 1110, "hold")]),
                            keys("rotation", [(0, 0, "hold"), (1650, 0), (1700, 0.15), (1800, -0.1), (1880, 0, "hold"), (M, 0, "hold")])))

# an otter from the river, popping up in the pond
otter = nid()
OTTER = "FF7A5434"
backdrop.insert(1, node("Otter", [
    shape("Whiskers", [rect(10, 1.5, -10, 6, rot=0.2), rect(10, 1.5, 10, 6, rot=-0.2)], fill(INK)),
    shape("Face", [ell(5, 6, -6, -4), ell(5, 6, 6, -4), ell(7, 5, 0, 3)], fill(INK)),
    shape("Muzzle", [ell(18, 12, 0, 5)], fill("FFD9B88A")),
    shape("Head", [ell(32, 30, 0, 0)], fs(OTTER, 2.5)),
    shape("Ears", [ell(8, 8, -13, -11), ell(8, 8, 13, -11)], fs(OTTER, 2)),
    shape("Body", [ell(30, 34, 0, 22)], fs(OTTER, 2.5)),
], 1610, FLOOR + 50, otter))
O = 1500
anim("Otter Pop", O, keyed(otter, keys("y", [(0, FLOOR + 50, "hold"), (400, FLOOR + 50), (416, FLOOR - 30), (560, FLOOR - 30), (576, FLOOR + 50, "hold"),
                                             (O, FLOOR + 50, "hold")])))

# ---------------------------------------------------------------- butterflies in the top bar's gap and over the meadow

def butterfly(color, path, period):
    root, wings = nid(), nid()
    shapes.insert(0, node("Butterfly", [
        shape("Body", [rect(3, 14, 0, 0, 1.5)], fill(INK)),
        node("Wings", [shape("W", [ell(12, 14, -6, -3), ell(12, 14, 6, -3), ell(8, 9, -5, 7), ell(8, 9, 5, 7)], fs(color, 1.5))],
             0, 0, wings),
    ], path[0][1], path[0][2], root))
    anim("Butterfly", period, keyed(root, keys("x", [(f, x) for f, x, y in path]), keys("y", [(f, y) for f, x, y in path])))
    anim("Flutter", 12, keyed(wings, keys("scaleX", [(0, 1), (6, 0.25), (12, 1)])))


butterfly("FFF39BC0", [(0, 560, 120), (180, 700, 70), (360, 880, 140), (540, 1040, 80), (720, 900, 160), (900, 700, 110),
                       (1080, 560, 120)], 1080)
butterfly("FFFFD24F", [(0, 900, 960), (200, 1000, 900), (400, 1100, 980), (600, 980, 930), (800, 860, 990), (1000, 900, 960)], 1000)

# ---------------------------------------------------------------- the sky and the meadow (backdrop, drawn underneath everything)
sky = []
for i, (y, s, period, offset) in enumerate(((150, 1.0, 7200, 0.25), (430, 0.8, 9000, 0.7), (690, 1.2, 10800, 0.05))):
    c = nid()
    sky.append(node(f"Cloud{i}", [shape("Puff", [ell(110, 54, 0, 0), ell(80, 60, -40, -16), ell(90, 74, 26, -24), ell(150, 36, 0, 14)],
                                        fill("FFFFFFFF")),
                                  shape("Shade", [ell(150, 36, 0, 18)], fill("FFDCEBF5"))],
                    -200, y, c, f' scaleX="{s}" scaleY="{s}"'))
    span = 2320
    x0 = -200 + span * offset
    t0 = int(period * (1 - offset))
    anim(f"Cloud {i}", period, keyed(c, keys("x", [(0, x0), (t0, 2120, "hold"), (t0 + 1, -200), (period, x0)])))

flowers = []
for i, x in enumerate(range(30, 1920, 74)):
    y = FLOOR + 6 + (i * 37 % 22)
    flowers += [ell(9, 9, x + (i * 13 % 30), y)]
meadow = [
    shape("FlowerHearts", [ell(4, 4, float(f.split('x="')[1].split('"')[0]), float(f.split('y="')[1].split('"')[0])) for f in flowers],
          fill(HONEY)),
    shape("Flowers", flowers[::2], fill(PAPER)),
    shape("FlowersPink", flowers[1::2], fill("FFF6B1C3")),
    shape("Meadow", [rect(1960, 80, 960, FLOOR + 40), ell(700, 60, 300, FLOOR), ell(900, 70, 1100, FLOOR + 6),
                     ell(700, 60, 1750, FLOOR)], fill("FF8DBE5B")),
    shape("Hills", [ell(1100, 240, 250, FLOOR + 40), ell(1200, 220, 1200, FLOOR + 50), ell(900, 260, 1900, FLOOR + 40)],
          fill("FFA9D27A")),
    moose_node,
    shape("FarTrees", [ell(110, 150, x, 905 + (x * 7 % 40)) for x in range(-20, 1980, 85)] + [rect(1960, 160, 960, 1000)],
          fill("FF8DBBA0")),
]
sun = node("Sun", [
    shape("Disc", [ell(96, 96)], fill("FFFFD75A") + stroke("FFF2B23A", 3)),
    shape("Rays", ['<Star points="12" width="190" height="190" innerRadius="0.62" name="P"/>'], fill("FFFFEBA6"), sid="1:3"),
], 1020, 92)
backdrop += meadow + sky + [sun]

# ---------------------------------------------------------------- Owl, the mascot by the clock (ids kept from the template:
# 1:202 bobs to music, 1:203 blinks, 1:204 the book tilts as he bops)
OWL, OWL_DK, FACE = "FF8A6440", "FF6E4E31", "FFEBD3A8"
page = nid()
owl = node("Bob", [
    node("Book", [
        node("Page", [shape("P", [rect(22, 26, 11, 0, 2)], fs(PAPER, 2))], 0, 0, page),
        shape("Pages", [rect(22, 26, -11, 0, 2), rect(22, 26, 11, 0, 2)], fs(PAPER, 2)),
        shape("Lines", [rect(14, 2, -11, -6), rect(14, 2, -11, 0), rect(14, 2, -11, 6), rect(14, 2, 11, -6), rect(14, 2, 11, 0)],
              fill("FFB8A688")),
        shape("Cover", [rect(52, 30, 0, 2, 3)], fs(BERRY, 2.5)),
    ], 0, -26, "1:204"),
    node("Eyes", [shape("Glints", [ell(4, 4, -10, -3), ell(4, 4, 14, -3)], fill(PAPER)),
                  shape("Pupils", [ell(11, 12, -12, 0), ell(11, 12, 12, 0)], fill(INK))], 0, -64, "1:203"),
    shape("Whites", [ell(26, 26, -12, -64), ell(26, 26, 12, -64)], fs(PAPER, 2.5)),
    shape("Beak", [tri(11, 13, 0, -50, rot=3.14)], fs(HONEY, 2)),
    shape("WingL", [ell(22, 48, -34, -34, rot=0.25)], fs(OWL_DK, 2.5)),
    shape("WingR", [ell(22, 48, 34, -34, rot=-0.25)], fs(OWL_DK, 2.5)),
    shape("FaceDisc", [ell(64, 44, 0, -62)], fs(FACE, 2.5)),
    shape("Belly", [ell(42, 50, 0, -28)], fill(FACE)),
    shape("Body", [ell(74, 92, 0, -44)], fs(OWL)),
    shape("Tufts", [tri(16, 24, -26, -92, rot=-0.4), tri(16, 24, 26, -92, rot=0.4)], fs(OWL)),
    shape("Feet", [ell(12, 8, -12, 0), ell(12, 8, 12, 0)], fs(HONEY, 2)),
], 62, 100, "1:202")
mascot = f'''<!-- Owl, reading beside the clock. Blinks on a loop; bobs while something plays -->
                <LayoutComponent width="124" height="112" clip="false" styleId="1:201" name="Mascot" id="1:200">
                    <LayoutComponentStyle layoutWidthScaleType="fixed" layoutHeightScaleType="fixed"
                                          marginLeft="18" name="Mascot Style" id="1:201"/>
                    {owl}
                </LayoutComponent>'''
anim("Owl Turns The Page", 480, keyed(page, keys("scaleX", [(0, 1, "hold"), (400, 1), (420, -1, "hold"), (480, -1, "hold")])))

# ================================================================ write into scene.rml
def put(s, tag, body):
    begin, end = f"<!-- cast:{tag} begin -->", f"<!-- cast:{tag} end -->"
    assert begin in s, begin
    return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: f"{begin}\n{body}\n{end}", s, flags=re.S)


s = SCENE.read_text()
s = put(s, "mascot", mascot)
s = put(s, "shapes", "\n".join(shapes))
s = put(s, "backdrop", "\n".join(backdrop))
s = put(s, "anims", "\n".join(anims))
s = put(s, "layers", "\n".join(layers))
SCENE.write_text(s)
print(f"cast written: {len(shapes)} shapes, {len(backdrop)} backdrop pieces, {len(anims)} animations")
