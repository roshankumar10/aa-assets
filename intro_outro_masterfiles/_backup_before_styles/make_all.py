"""Render videos for every level in levels.json.
    python make_all.py                 -> intro + outro for all levels
    python make_all.py --intros 2 4    -> intros only, levels 2 and 4
    python make_all.py --outros        -> outros only
"""
import json, subprocess, sys

with open("levels.json", encoding="utf-8") as f:
    n = len(json.load(f)["levels"])
levels = [int(a) for a in sys.argv[1:] if a.isdigit()] or range(1, n + 1)
scripts = (["intro_level.py"] if "--outros" not in sys.argv else []) + \
          (["outro_level.py"] if "--intros" not in sys.argv else [])
for lv in levels:
    for script in scripts:
        print(f"--- level {lv}: {script}", flush=True)
        subprocess.run([sys.executable, script, "--level", str(lv)], check=True)
