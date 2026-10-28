"""Atlas Academy - intro split into a general video (rendered once) and a personalized one (per student).

    python intro_split.py                  -> intro_level2_general.mov + intro_level2_personal_<First_Last>.mov
    python intro_split.py --part general   -> no names in it: slot-machine "Atlas ____" reel, then the
        "Level 2 / <course>" title card (same as intro_level.py, but using intro_split.json)
    python intro_split.py --part personal  -> the outro's level-complete card: student name + "Level 2 complete",
        then (with "personal_lists": true) the outro's "What they learned" list, "Curriculum Highlights"
        (the level's "highlights", if it has any) and "Skills learned"
        (no logo unless "show_logo": true); ends on plain navy once everything has slid out
    python intro_split.py --config other.json   -> use a different settings file

Settings live in intro_split.json (its own file - editing it doesn't change intro_level / outro_level):
render_level, student first/last name, reel, intro_durations, outro_durations "complete", name_tail, general_tail,
title_card, personal_lists, show_logo, fade_logo, intro_skills_style, intro_note, chip_notes, hand_title_line. Course name, level title and skills
still come from levels/level_N.json; any of their keys added to intro_split.json override that file too.
Command-line options still win over the json (--level, --first/--last, --duration, --reel, --skills-style ...).
"""
import json, subprocess, sys
CONFIG_FILE = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else "intro_split.json"
with open(CONFIG_FILE, encoding="utf-8") as _f:
    _split = json.load(_f)
if "--config" not in sys.argv:
    sys.argv += ["--config", CONFIG_FILE]
if "--level" not in sys.argv:
    sys.argv += ["--level", str(_split.get("render_level", 1))]

from PIL import Image
from render import W, H, FPS, BG, set_real_t, exit_ofs
import outro_level as outro
import intro_level as intro
from outro_level import CONFIG, LEVEL, _arg, _suffix

PART = _arg("--part", "both")
NAME_TAIL = float(_split.get("name_tail", 0.2))   # name card's exit runs this far past its section - let it finish
GENERAL_TAIL = float(_split.get("general_tail", 0.1))  # title card fades to navy right at its end - hold a few frames past it
SHOW_LOGO = bool(_split.get("show_logo", False))   # Atlas Academy logo on the personalized card
FADE_LOGO = bool(_split.get("fade_logo", True))    # parked logo slides out with the name, so it ends on navy
TITLE_CARD = bool(_split.get("title_card", True))
PERSONAL_LISTS = bool(_split.get("personal_lists", False))  # name card, then the outro's learned + skills lists  # false: general video is just the reel (no "Level N" title card)

def render(out, n, frame):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3",
           "-pix_fmt", "yuv422p10le", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).convert("RGB").tobytes())
        if i % 60 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", out, flush=True)

L_DONE = outro.TIMELINE.lengths["complete"]
# with the lists: name card -> "What they learned" -> each list in C_LISTS, one after another in the outro's
# section-C slot (design 7.9 - 10.6s, played again for each list); else just the name card
HIGHLIGHTS = outro.CONFIG.get("highlights") or []
C_LISTS = ([outro.skills_scene(_split.get("highlights_heading", "Curriculum Highlights"), HIGHLIGHTS)]
           if HIGHLIGHTS else []) + [outro.skills_scene("Skills learned:", outro.CONFIG["skills"],
                                                        outro.CONFIG["skills_note"])]
C_START, C_END = outro.real_time(7.9), outro.real_time(10.6)
PERSONAL_LEN = C_START + len(C_LISTS) * (C_END - C_START) if PERSONAL_LISTS else L_DONE + NAME_TAIL

if not TITLE_CARD:
    intro.SCENES = [intro.scene_reel]
# the reel has slid out by 0.2s past its section; without the title card the video ends there
GENERAL_LEN = intro.TIMELINE.total if TITLE_CARD else intro.TIMELINE.lengths["reel"] + 0.2

def frame_general(t):
    return intro.frame(intro.TIMELINE.warp(set_real_t(t)))

def frame_personal(t):
    c = Image.new("RGBA", (W, H), BG + (255,))
    k = 0                                                  # which list in C_LISTS is playing
    if PERSONAL_LISTS and t >= C_START:
        k = min(len(C_LISTS) - 1, int((t - C_START) // (C_END - C_START)))
        t -= k * (C_END - C_START)
    d = outro.TIMELINE.warp(set_real_t(t))
    ey, ea = exit_ofs(d, 4.2) if FADE_LOGO else (0, 1)     # same exit timing as the name card
    if SHOW_LOGO and ea > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        outro.logo(layer, d)
        if ea < 1:
            layer.putalpha(layer.getchannel("A").point(lambda a: int(a * ea)))
        c.alpha_composite(layer, (0, int(ey)))
    outro.scene_a(c, d)
    if PERSONAL_LISTS:
        if k == 0:                                         # "What they learned" only plays once
            outro.scene_b(c, d)
        C_LISTS[k](c, d)
    return c

if PART in ("both", "general"):
    render(_arg("--out-general", f"intro_level{LEVEL}_general{CONFIG['style_suffix']}.mov"),
           int(round((GENERAL_LEN + GENERAL_TAIL) * FPS)), frame_general)
if PART in ("both", "personal"):
    render(_arg("--out-personal", f"intro_level{LEVEL}_personal{_suffix}.mov"),
           int(round(PERSONAL_LEN * FPS)), frame_personal)
