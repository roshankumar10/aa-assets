"""Render videos for every level in levels/ (level_1.json, level_2.json, ...).
    python make_all.py                 -> intro + outro for all levels
    python make_all.py --intros 2 4    -> intros only, levels 2 and 4
    python make_all.py --outros        -> outros only
    python make_all.py --skills-style list --learned-style checklist   -> override levels.json styles
    python make_all.py 1 --duration learned=5 --duration end=6          -> override section lengths
    python make_all.py --first Jane --last Doe                          -> one student's set (names in file names)
"""
import os, subprocess, sys

n = 0                                          # levels/level_1.json, levels/level_2.json, ...
while os.path.exists(f"levels/level_{n + 1}.json"):
    n += 1
levels = [int(a) for a in sys.argv[1:] if a.isdigit()] or range(1, n + 1)
scripts = (["intro_level.py"] if "--outros" not in sys.argv else []) + \
          (["outro_level.py"] if "--intros" not in sys.argv else [])
extra = []
for flag in ("--skills-style", "--learned-style", "--first", "--last"):
    if flag in sys.argv:
        extra += [flag, sys.argv[sys.argv.index(flag) + 1]]
for i, a in enumerate(sys.argv[:-1]):          # repeatable: --duration learned=5
    if a == "--duration":
        extra += [a, sys.argv[i + 1]]
for lv in levels:
    for script in scripts:
        print(f"--- level {lv}: {script}", flush=True)
        subprocess.run([sys.executable, script, "--level", str(lv)] + extra, check=True)
