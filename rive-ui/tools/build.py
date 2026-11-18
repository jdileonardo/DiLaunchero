#!/usr/bin/env python3
"""Builds every theme (or the ones named) and copies each into the app.

    python3 tools/build.py            # all themes
    python3 tools/build.py retro      # just one

For each themes/<name>/: regenerates data.rml, checks it, publishes
build/<name>.riv and copies it to app/src/main/res/raw/home_<name>.riv.
Adding a theme folder here is half the job; the app's Theme enum is the other half.
"""
import shutil, subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rive = Path.home() / ".rive/bin/rive"
raw = root.parent / "app/src/main/res/raw"
names = sys.argv[1:] or sorted(d.name for d in (root / "themes").iterdir() if (d / "scene.rml").exists())

for name in names:
    theme = root / "themes" / name
    subprocess.run([sys.executable, root / "tools/gen_data.py", theme], check=True)
    subprocess.run([rive, ".", "--verify"], cwd=theme, check=True)
    subprocess.run([rive, ".", "--publish"], cwd=theme, check=True)
    shutil.copy(theme / "build" / f"{name}.riv", raw / f"home_{name}.riv")
    print(f"-> {raw / f'home_{name}.riv'}")
