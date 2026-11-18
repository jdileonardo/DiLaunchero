#!/usr/bin/env python3
"""Gives a theme day, dusk and night, following the Home view model's skyPhase (4:41).

    python3 tools/sky.py littlebear retro

The app sets skyPhase from sunrise and sunset where the TV is: 0 night, 1 dusk (or dawn),
2 day. Each theme lists, in SPECS below, what changes: (object id, property, day, dusk,
night). This writes three still animations (one per phase) and a "Sky" state machine layer
that eases between them, plus a field of twinkling stars at the very back. It also gives
ids to the parts every theme shares (background gradient, clock text, the "more below"
fade) and a pale halo to the tile labels, so they read on a dark sky.

Everything goes between <!-- sky:... --> markers, so re-running replaces it.
"""
import random
import re
import sys
from pathlib import Path

INK = "FF3B2A1E"
SPECS = {
    "littlebear": [
        # sky gradient, top to bottom
        ("15:1", "colorValue", "FF6FB6EA", "FF6F7EC2", "FF0E1838"),
        ("15:2", "colorValue", "FFA6D6F4", "FFEFA48C", "FF1B2B58"),
        ("15:3", "colorValue", "FFDDF0F2", "FFFFD49C", "FF2F4272"),
        # clock and date
        ("15:4", "colorValue", INK, INK, "FFFFF4DC"),
        ("15:5", "colorValue", "FF3E5A78", "FF5A3550", "FFC9D6F0"),
        # the "more below" fade melts into the (tinted) meadow
        ("15:9", "colorValue", "0090BF62", "0090A060", "00304A48"),
        ("15:10", "colorValue", "F590BF62", "F590A060", "F5304A48"),
        # sun sets, moon rises, stars come out
        ("15:40", "y", 92, 170, 300),
        ("15:40", "opacity", 1, 1, 0),
        ("15:41", "opacity", 0, 0.35, 1),
        ("15:22", "opacity", 0, 0.25, 1),
        # clouds: white, then peach, then moonlit blue
        *((c, "colorValue", "FFFFFFFF", "FFFFE0D0", "FF4A5784") for c in ("15:42", "15:43", "15:44")),
        *((c, "colorValue", "FFDCEBF5", "FFF4BFB0", "FF38446E") for c in ("15:45", "15:46", "15:47")),
        # the evening light over the forest and the folk in it
        ("15:50", "opacity", 0, 1, 1),
        ("15:51", "colorValue", "00F08850", "00F08850", "00101C40"),
        ("15:52", "colorValue", "00F08850", "40F08850", "9E101C40"),
        # lamplight in the Bear house windows, fireflies over the meadow
        ("15:54", "opacity", 0, 0.7, 1),
        ("15:53", "opacity", 0, 0, 1),
    ],
    "retro": [
        ("15:1", "colorValue", "FFF6E9CC", "FFF8C9A4", "FF20254A"),
        ("15:2", "colorValue", "FFF3E2BF", "FFF2B39A", "FF262B50"),
        ("15:3", "colorValue", "FFEEDAB3", "FFE7A1A0", "FF2E3358"),
        ("15:4", "colorValue", "FF2B1E16", "FF2B1E16", "FFFFF4DC"),
        ("15:5", "colorValue", "FF9A5B3A", "FF8A3F3A", "FFC9C3E6"),
        ("15:9", "colorValue", "00EEDAB3", "00E7A1A0", "002E3358"),
        ("15:10", "colorValue", "F5EEDAB3", "F5E7A1A0", "F52E3358"),
        # the sunburst fades to faint moonbeams; the sun cools to a moon
        ("15:6", "colorValue", "55FFFBF0", "55FFE2C4", "12FFFFFF"),
        ("15:7", "colorValue", "40F2B134", "70F2843A", "D0F4EBC8"),
        ("15:22", "opacity", 0, 0.25, 1),
    ],
}
FOCUS = "4:1-4:41"


def prepare(s):
    """Ids on the shared parts (idempotent), and halos on the tile labels."""
    bg = re.search(r'<Fill name="Background">.*?</Fill>', s, re.S)
    stops = bg.group(0)
    for i, sid in enumerate(("15:1", "15:2", "15:3")):
        stops = re.sub(r'(<GradientStop colorValue="\w+" position="[\d.]+")(/>)', rf'\1 id="{sid}"\2', stops, count=1) \
            if f'id="{sid}"' not in stops else stops
    s = s[:bg.start()] + stops + s[bg.end():]
    for style, sid in (("1:25", "15:4"), ("1:27", "15:5")):
        s = re.sub(rf'(id="{style}">\s*<Fill name="F"><SolidColor colorValue="\w+" name="C")(/>)', rf'\1 id="{sid}"\2', s)
    fade = re.search(r'name="MoreFade".*?</LinearGradient>', s, re.S)
    f = fade.group(0)
    if 'id="15:9"' not in f:
        f = re.sub(r'(<GradientStop colorValue="\w+" position="0")(/>)', r'\1 id="15:9"\2', f, count=1)
        f = re.sub(r'(<GradientStop colorValue="\w+" position="1")(/>)', r'\1 id="15:10"\2', f, count=1)
    s = s[:fade.start()] + f + s[fade.end():]
    for style in ("3:21", "2:21"):
        if not re.search(rf'id="{style}">\s*<Stroke', s):
            s = re.sub(rf'(name="Label Style" id="{style}">\s*)(<Fill)',
                       r'\1<Stroke thickness="6" name="Halo"><SolidColor colorValue="E6FFFAEE" name="C"/></Stroke>\2', s)
    return s


def stars():
    rnd = random.Random(7)
    big, small = [], []
    for _ in range(70):
        x, y = rnd.uniform(20, 1900), rnd.uniform(10, 780)
        (big if rnd.random() < 0.3 else small).append((x, y))
    dots = lambda pts, r: "".join(f'<Ellipse x="{x:.0f}" y="{y:.0f}" width="{r}" height="{r}" name="P"/>' for x, y in pts)
    return ('<!-- sky:stars begin -->\n'
            '<Node name="Stars" opacity="0" id="15:22">'
            f'<Shape name="Twinkle" id="15:23">{dots(big, 5)}<Fill name="F"><SolidColor colorValue="FFFFF6D8" name="C"/></Fill></Shape>'
            f'<Shape name="Faint">{dots(small, 3)}<Fill name="F"><SolidColor colorValue="CCFFF6D8" name="C"/></Fill></Shape>'
            '</Node>\n<!-- sky:stars end -->\n')


def keyframe(prop, v):
    if prop == "colorValue":
        return f'<KeyFrameColor value="{v}" interpolationType="hold"/>'
    return f'<KeyFrameDouble value="{v}" interpolationType="hold"/>'


def anims(spec):
    out = []
    for phase, (aid, name) in enumerate((("16:1", "Sky Night"), ("16:2", "Sky Dusk"), ("16:3", "Sky Day"))):
        by_obj = {}
        for oid, prop, *vals in spec:
            by_obj.setdefault(oid, []).append(
                f'<KeyedProperty property="{prop}">{keyframe(prop, vals[2 - phase])}</KeyedProperty>')
        out.append(f'<LinearAnimation duration="1" name="{name}" id="{aid}">'
                   + "".join(f'<KeyedObject objectId="{o}">{"".join(p)}</KeyedObject>' for o, p in by_obj.items())
                   + '</LinearAnimation>')
    out.append('<LinearAnimation duration="180" loopValue="loop" name="Twinkle" id="16:5"><KeyedObject objectId="15:23">'
               '<KeyedProperty property="opacity"><KeyFrameDouble frame="0" value="1" interpolationType="linear"/>'
               '<KeyFrameDouble frame="60" value="0.35" interpolationType="linear"/><KeyFrameDouble frame="110" value="1" interpolationType="linear"/>'
               '<KeyFrameDouble frame="140" value="0.6" interpolationType="linear"/><KeyFrameDouble frame="180" value="1" interpolationType="linear"/>'
               '</KeyedProperty></KeyedObject></LinearAnimation>')
    return "<!-- sky:anims begin -->\n" + "\n".join(out) + "\n<!-- sky:anims end -->\n"


def layers():
    def cond(v):
        return (f'<TransitionViewModelCondition opValue="equal"><TransitionPropertyViewModelComparator><BindablePropertyNumber>'
                f'<DataBindContext sourcePathIds="{FOCUS}" propertyKey="636"/></BindablePropertyNumber>'
                f'</TransitionPropertyViewModelComparator><TransitionValueNumberComparator value="{v}"/></TransitionViewModelCondition>')
    states = []
    for phase in range(3):
        trans = "".join(f'<StateTransition stateToId="16:1{other + 1}" duration="2500">{cond(other)}</StateTransition>'
                        for other in range(3) if other != phase)
        states.append(f'<AnimationState x="{100 + 200 * phase}" y="100" animationId="16:{phase + 1}" '
                      f'stateName="{("Night", "Dusk", "Day")[phase]}" id="16:1{phase + 1}">{trans}</AnimationState>')
    sky = ('<StateMachineLayer name="Sky" id="16:10"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
           '<EntryState><StateTransition stateToId="16:13"/></EntryState>' + "".join(states) + '</StateMachineLayer>')
    twinkle = ('<StateMachineLayer name="Twinkle" id="16:20"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
               '<EntryState><StateTransition stateToId="16:21"/></EntryState>'
               '<AnimationState x="200" animationId="16:5" id="16:21"/></StateMachineLayer>')
    return "<!-- sky:layers begin -->\n" + sky + "\n" + twinkle + "\n<!-- sky:layers end -->\n"


def put(s, tag, block, anchor):
    begin, end = f"<!-- sky:{tag} begin -->", f"<!-- sky:{tag} end -->\n"
    if begin in s:
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: block, s, flags=re.S)
    assert s.count(anchor) == 1, anchor
    return s.replace(anchor, block + anchor)


for name in sys.argv[1:]:
    scene = Path(__file__).resolve().parent.parent / "themes" / name / "scene.rml"
    s = prepare(scene.read_text())
    s = put(s, "stars", stars(), '        <StateMachine name="Home Machine"')
    s = put(s, "anims", anims(SPECS[name]), "<!-- theme-button:anims begin -->")
    s = put(s, "layers", layers(), "<!-- theme-button:layer begin -->")
    scene.write_text(s)
    print(f"sky -> {scene}")
