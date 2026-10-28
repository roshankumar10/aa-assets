"""Contact sheet of every way to show the skill / topic lists, so you can pick one before rendering.
    python preview_styles.py --level 1                        -> styles_level1.png
    python preview_styles.py --level 5 list columns inline    -> only those rows
Rows are styles; columns are the intro title card, outro "What they learned" and outro "Skills learned:".
Put the pick in levels.json ("intro_skills_style", "outro_skills_style", "learned_style") - per level,
or once at the top level for every level that doesn't set its own.
"""
import os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
from render import STYLES, BG, GOLD, WHITE, spartan, dmsans

SHOTS = [("Intro - this level", "intro_level.py", 13.6, "--skills-style"),
         ("Outro - what we learned", "outro_level.py", 7.5, "--learned-style"),
         ("Outro - skills unlocked", "outro_level.py", 9.95, "--skills-style")]
TW, TH, LABEL_W, HEAD_H, GAP = 640, 360, 230, 60, 6

def shot(level, style, script, t, flag, path):
    subprocess.run([sys.executable, script, "--level", str(level), flag, style,
                    "--still", str(t), "--still-out", path], check=True, stdout=subprocess.DEVNULL)

def main():
    level = int(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else 1
    styles = [a for a in sys.argv[1:] if a in STYLES + ("cards",)] or ["cards", *STYLES]
    tmp = tempfile.mkdtemp()
    try:
        with ThreadPoolExecutor(4) as ex:
            jobs = {(r, k): (ex.submit(shot, level, style, script, t, flag, os.path.join(tmp, f"{r}_{k}.png")),
                             os.path.join(tmp, f"{r}_{k}.png"))
                    for r, style in enumerate(styles) for k, (_, script, t, flag) in enumerate(SHOTS)
                    if style != "cards" or flag == "--learned-style"}     # cards only exist for 'learned'
        sheet = Image.new("RGB", (LABEL_W + (TW + GAP) * 3, HEAD_H + (TH + GAP) * len(styles)), (12, 15, 34))
        d = ImageDraw.Draw(sheet)
        for k, (title, *_) in enumerate(SHOTS):
            d.text((LABEL_W + k * (TW + GAP) + 16, 16), title, font=dmsans(28, 500), fill=WHITE)
        for r, style in enumerate(styles):
            y = HEAD_H + r * (TH + GAP)
            d.text((24, y + TH / 2 - 22), style, font=spartan(40), fill=GOLD)
            for k in range(3):
                x = LABEL_W + k * (TW + GAP)
                if (r, k) in jobs:
                    fut, path = jobs[(r, k)]
                    fut.result()
                    sheet.paste(Image.open(path).resize((TW, TH), Image.LANCZOS), (x, y))
                else:
                    d.rectangle((x, y, x + TW, y + TH), fill=BG)
                    d.text((x + 24, y + 24), "n/a for this section", font=dmsans(24), fill=(120, 128, 160))
        out = f"styles_level{level}.png"
        sheet.save(out)
        print("wrote", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
