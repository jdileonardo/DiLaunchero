#!/usr/bin/env python3
"""Adds (or refreshes) the small theme button under the gear in a theme's scene.rml.

    python3 tools/theme_button.py vanilla      # or retro, scopa ...

The button is pinned to the top bar's right edge just below Settings, bound to
the Home view model's themeFocused (4:40). Each theme picks its colours in
STYLES below. Everything goes between <!-- theme-button:... --> markers, so
re-running replaces it.
"""
import re
import sys
from pathlib import Path

STYLES = {
    # fill, focused fill, ring, focused ring, ring width, icon, icon outline, hard shadow
    "vanilla": dict(fill="FF1A2336", fill_on="FF2C3B5C", ring="00FFFFFF", ring_on="FFE8EEFF", ring_w=3,
                    icon="FFDCE3F0", outline=None, shadow=None, dots=("FFFF7A6B", "FFFFD66B", "FF6FD3C2", "FF6F9BFF")),
    "retro": dict(fill="FFFFF8EA", fill_on="FFF2B134", ring="FF2B1E16", ring_on="FF2B1E16", ring_w=4,
                  icon="FFFFF8EA", outline="FF2B1E16", shadow="FF2B1E16", dots=("FFE4572E", "FFF2B134", "FF2A9D8F", "FF2B1E16")),
    "scopa": dict(fill="FFFFFBEF", fill_on="FFF2C318", ring="FF2A1C14", ring_on="FF2A1C14", ring_w=3,
                  icon="FFFFFBEF", outline="FF2A1C14", shadow="66000000", dots=("FFD42A2A", "FFF2C318", "FF1F6E3A", "FF22408C")),
    "littlebear": dict(fill="FFFFFAEE", fill_on="FFF4C14F", ring="FF3B2A1E", ring_on="FF3B2A1E", ring_w=3,
                       icon="FFFFFAEE", outline="FF3B2A1E", shadow="4D2C4A1E", dots=("FFC0503A", "FFF4C14F", "FF6E9B4B", "FF6FB6EA")),
}
SIZE, BAR_H, GAP = 52, 112, 12
FOCUS_PROP = "4:1-4:40"


def button(st):
    def layer(name, sid, paint, off):
        return (f'<LayoutComponent clip="false" styleId="{sid}" name="{name}">'
                f'<LayoutComponentStyle widthUnitsValue="auto" heightUnitsValue="auto" positionTypeValue="absolute" '
                f'positionLeft="{off}" positionLeftUnitsValue="points" positionTop="{off}" positionTopUnitsValue="points" '
                f'positionRight="{-off}" positionRightUnitsValue="points" positionBottom="{-off}" positionBottomUnitsValue="points" '
                f'cornerRadiusTL="{SIZE // 2}" name="{name} Style" id="{sid}"/>{paint}</LayoutComponent>')
    outline = f'<Stroke thickness="2.5" name="S"><SolidColor colorValue="{st["outline"]}" name="C"/></Stroke>' if st["outline"] else ""
    dots = "".join(f'<Shape x="{x}" y="{y}" name="Dot{i}"><Ellipse width="6" height="6" name="P"/>'
                   f'<Fill name="F"><SolidColor colorValue="{c}" name="C"/></Fill></Shape>'
                   for i, (c, (x, y)) in enumerate(zip(st["dots"], ((-7, -5), (1, -8), (8, -3), (7, 5)))))
    face = layer("Face", "11:5",
                 f'<Fill name="F"><SolidColor colorValue="{st["fill"]}" name="C" id="11:3"/></Fill>'
                 f'<Stroke thickness="{st["ring_w"]}" name="Ring"><SolidColor colorValue="{st["ring"]}" name="C" id="11:4"/></Stroke>', 0)
    shadow = layer("Shadow", "11:6", f'<Fill name="F"><SolidColor colorValue="{st["shadow"]}" name="C"/></Fill>', 4) if st["shadow"] else ""
    return f'''<!-- theme-button:shape begin -->
                <!-- theme button: pinned under the gear; opens the theme picker -->
                <LayoutComponent width="{SIZE}" height="{SIZE}" clip="false" styleId="11:2" name="Theme" id="11:1">
                    <LayoutComponentStyle layoutWidthScaleType="fixed" layoutHeightScaleType="fixed"
                                          positionTypeValue="absolute"
                                          positionRight="{(84 - SIZE) // 2}" positionRightUnitsValue="points"
                                          positionTop="{BAR_H - 14 + GAP}" positionTopUnitsValue="points"
                                          cornerRadiusTL="{SIZE // 2}" name="Theme Style" id="11:2"/>
                    <ComponentOrigin originX="0.5" originY="0.5" name="Origin"/>
                    <Node x="{SIZE // 2}" y="{SIZE // 2}" name="Icon">{dots}<Shape x="-4" y="5" name="Thumb"><Ellipse width="7" height="6" name="P"/><Fill name="F"><SolidColor colorValue="{st["fill"]}" name="C" id="11:7"/></Fill></Shape><Shape name="Palette"><Ellipse width="30" height="24" name="P"/><Fill name="F"><SolidColor colorValue="{st["icon"]}" name="C"/></Fill>{outline}</Shape></Node>
                    {face}
                    {shadow}
                </LayoutComponent>
<!-- theme-button:shape end -->
'''


def anims(st):
    def one(aid, name, scale, fill_c, ring_c):
        return (f'<LinearAnimation duration="1" name="{name}" id="{aid}">'
                f'<KeyedObject objectId="11:1"><KeyedProperty property="scaleX"><KeyFrameDouble value="{scale}" interpolationType="hold"/></KeyedProperty>'
                f'<KeyedProperty property="scaleY"><KeyFrameDouble value="{scale}" interpolationType="hold"/></KeyedProperty></KeyedObject>'
                f'<KeyedObject objectId="11:3"><KeyedProperty property="colorValue"><KeyFrameColor value="{fill_c}" interpolationType="hold"/></KeyedProperty></KeyedObject>'
                f'<KeyedObject objectId="11:7"><KeyedProperty property="colorValue"><KeyFrameColor value="{fill_c}" interpolationType="hold"/></KeyedProperty></KeyedObject>'
                f'<KeyedObject objectId="11:4"><KeyedProperty property="colorValue"><KeyFrameColor value="{ring_c}" interpolationType="hold"/></KeyedProperty></KeyedObject>'
                '</LinearAnimation>')
    return ("<!-- theme-button:anims begin -->\n"
            + one("11:10", "Theme Focus Off", 1, st["fill"], st["ring"])
            + one("11:11", "Theme Focus On", 1.12, st["fill_on"], st["ring_on"])
            + "\n<!-- theme-button:anims end -->\n")


def layer():
    def cond(v):
        return (f'<TransitionViewModelCondition opValue="equal"><TransitionPropertyViewModelComparator><BindablePropertyBoolean>'
                f'<DataBindContext sourcePathIds="{FOCUS_PROP}" propertyKey="634"/></BindablePropertyBoolean>'
                f'</TransitionPropertyViewModelComparator><TransitionValueBooleanComparator value="{v}"/></TransitionViewModelCondition>')
    return ('<!-- theme-button:layer begin -->\n'
            '<StateMachineLayer name="Theme Focus" id="11:20"><AnyState x="200" y="-120"/><ExitState x="400" y="-120"/>'
            '<EntryState><StateTransition stateToId="11:21"/></EntryState>'
            '<AnimationState x="100" y="100" animationId="11:10" stateName="Off" id="11:21">'
            '<StateTransition stateToId="11:22" duration="160" interpolationType="cubic"><CubicEaseInterpolator x1="0.2" y1="0.9" x2="0.3" y2="1"/>'
            + cond("true") + '</StateTransition></AnimationState>'
            '<AnimationState x="300" y="100" animationId="11:11" stateName="On" id="11:22">'
            '<StateTransition stateToId="11:21" duration="140" interpolationType="cubic"><CubicEaseInterpolator x1="0.4" y1="0" x2="0.2" y2="1"/>'
            + cond("false") + '</StateTransition></AnimationState></StateMachineLayer>\n'
            '<!-- theme-button:layer end -->\n')


def put(s, tag, block, anchor, after=False):
    begin, end = f"<!-- theme-button:{tag} begin -->", f"<!-- theme-button:{tag} end -->\n"
    if begin in s:
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: block, s, flags=re.S)
    m = re.search(anchor, s)
    assert m, anchor
    i = m.end() if after else m.start()
    return s[:i] + block + s[i:]


for name in sys.argv[1:]:
    scene = Path(__file__).resolve().parent.parent / "themes" / name / "scene.rml"
    st = STYLES[name]
    s = scene.read_text()
    # the top bar must not clip the button hanging below it
    s = s.replace('<LayoutComponent height="112" styleId="1:21" name="TopBar" id="1:20">',
                  '<LayoutComponent height="112" clip="false" styleId="1:21" name="TopBar" id="1:20">')
    s = put(s, "shape", button(st), r'name="TopBar Style" id="1:21"/>\n', after=True)
    s = put(s, "anims", anims(st), r'[ \t]*<LinearAnimation duration="1" name="Settings Focus Off"')
    s = put(s, "layer", layer(), r'[ \t]*<StateMachineLayer name="Settings Focus"')
    scene.write_text(s)
    print(f"theme button -> {scene}")
