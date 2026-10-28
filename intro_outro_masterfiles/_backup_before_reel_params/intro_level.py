"""Atlas Academy - level intro (pairs with outro_level.py, reads the same CONFIG).

Slot-machine "Atlas ____" reel lands on "Academy" (from intro_v1), the
"Users -> builders" tagline gag, then a level title card listing the level's skills
(look set by "intro_skills_style" in levels.json - see outro_level.py for the choices).
    python intro_level.py --level 3            -> intro_level3.mov (ProRes 422 HQ, no audio)
    python intro_level.py --level 3 --skills-style list   -> intro_level3_list.mov
    python intro_level.py --level 3 --still 6  -> still_6.png preview
"""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from render import (W, H, FPS, BG, GOLD, WHITE, FONT_DIR, spartan, dmsans, text_sprite,
                    item_block, paste, word_layout, exit_ofs, prog, clamp,
                    out_expo, out_cubic, in_cubic, out_back)
from render import caveat, Aside, hand_underline
from render import Timeline, set_real_t
from outro_level import CONFIG, LEVEL, logo_layer, TOP_CENTER, TOP_SCALE, _arg, durations

DUR = 15.0
# section lengths from levels.json "intro_durations" (see outro_level.py); hold = where extra time pauses
SECTIONS = [("reel", 0.0, 7.4, 6.5, 0.6), ("title", 7.4, DUR, 13.0, 1.4)]
TIMELINE = Timeline(SECTIONS, durations("intro_durations", [s[0] for s in SECTIONS]), "intro")
OUT = _arg("--out", f"intro_level{LEVEL}{CONFIG['style_suffix']}.mov")
REEL_WORDS = ["3D Modelling", "Animation", "Robotics", "Coding", "Circuitry", "Debugging", "Academy"]
TAGLINE = ["An", "Academy", "for", "Technical", "&", "Creative", "Education", "Users"]

# ---------------------------------------------------------------- 1: Atlas + reel  0 - 7.4
R_FONT = spartan(170)
R_ATLAS = text_sprite("Atlas", R_FONT, GOLD)
R_ATLAS_W = R_FONT.getlength("Atlas")
R_SPR = [text_sprite(w, R_FONT, GOLD if w == "Academy" else WHITE) for w in REEL_WORDS]
R_W = [R_FONT.getlength(w) for w in REEL_WORDS]
R_GAP, R_STEP, R_Y = 44, 260, 470
N = len(REEL_WORDS) - 1
# tick times: each word holds a little less than the last, final tick overshoots onto "Academy"
_holds = [0.62, 0.5, 0.42, 0.36, 0.32, 0.3]
R_TICKS, _t = [], 1.15
for h in _holds:
    R_TICKS.append(_t); _t += h

def reel_pos(t):
    pos = 0.0
    for k, tk in enumerate(R_TICKS):
        q = prog(t, tk, 0.26)
        pos += out_back(q, 2.2) if k == N - 1 else out_expo(q)
    return pos

def scene_reel(c, t):
    if t > 7.7: return
    ey, ea = exit_ofs(t, 7.2, 0.4, -80)
    pos = reel_pos(t)
    i0 = int(clamp(pos, 0, N))
    frac = clamp(pos - i0)
    rw = R_W[i0] + (R_W[min(i0 + 1, N)] - R_W[i0]) * frac
    left = W / 2 - (R_ATLAS_W + R_GAP + rw) / 2      # whole line re-centres as the word width changes
    q = out_expo(prog(t, 0.15, 0.6))
    paste(c, R_ATLAS, left + R_ATLAS_W / 2, R_Y + (1 - q) * 80 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)

    # reel window: only the slot band is visible
    band_h = 340
    layer = Image.new("RGBA", (1400, band_h), (0, 0, 0, 0))
    vel = abs(reel_pos(t + 0.5 / FPS) - reel_pos(t - 0.5 / FPS)) * FPS   # words per second
    taps = 1 + min(6, int(vel * 1.2))                                     # fake motion blur
    appear = out_expo(prog(t, 0.45, 0.5))
    for k, spr in enumerate(R_SPR):
        dy = (k - pos) * R_STEP
        if abs(dy) > band_h: continue
        for j in range(taps):
            off = (j - (taps - 1) / 2) * vel * R_STEP / FPS / max(1, taps - 1) * 0.9
            paste(layer, spr, spr.width / 2, band_h / 2 + dy + off, 1, appear / taps ** 0.8 if taps > 1 else appear)
    # soft fade at top/bottom of the slot
    a = layer.getchannel("A")
    fh = band_h // 4
    fade = Image.linear_gradient("L").resize((1400, fh))
    mask = Image.new("L", (1400, band_h), 255)
    mask.paste(fade, (0, 0)); mask.paste(fade.rotate(180), (0, band_h - fh))
    layer.putalpha(Image.composite(a, Image.new("L", a.size, 0), mask))
    paste(c, layer, left + R_ATLAS_W + R_GAP + 700 - 8, R_Y + ey, 1, ea)

    # tagline: "... Education Users" -> Users struck out -> "builders" scrawled in
    f = dmsans(56, 450)
    xs = word_layout(TAGLINE, f, 15)
    for i, (w, x) in enumerate(zip(TAGLINE, xs)):
        q = out_expo(prog(t, 4.3 + i * 0.07, 0.5))
        paste(c, text_sprite(w, f, WHITE), x, 650 + (1 - q) * 40 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)
    uw = f.getlength("Users")
    q = out_cubic(prog(t, 5.5, 0.35))
    if q > 0 and ea > 0.05:
        x0 = xs[-1] - uw / 2
        ImageDraw.Draw(c).rectangle((x0, 660 + ey - 3, x0 + uw * q, 660 + ey + 3),
                                    fill=GOLD + (int(255 * ea),))
    q = prog(t, 5.85, 0.5)
    if q > 0:
        spr = text_sprite("builders", caveat(96), GOLD)
        paste(c, spr, xs[-1] + 10, 575 + ey, out_back(q, 2.4), clamp(q * 3) * ea, rot=8 + (1 - out_cubic(q)) * 20)

# ---------------------------------------------------------------- 2: level title card  7.4 - 15
T_LVL = text_sprite(CONFIG["level"], spartan(230), WHITE)
T_CW = CONFIG["course"].split()
T_C = [text_sprite(w, dmsans(80, 450), GOLD) for w in T_CW]
T_CX = word_layout(T_CW, dmsans(80, 450), 22)
T_LABEL = text_sprite("This level", spartan(52), WHITE)
T_SKILLS = item_block(CONFIG["intro_skills_style"], CONFIG["skills"], top=815, bottom=1020,
                      t0=10.15, span=1.6, y=865, notes=CONFIG["chip_notes"], note_dur=0.9)

# optional margin note (levels.json "intro_note"): written top-right of the level title, pen arrow to it
T_NOTE = (Aside(CONFIG["intro_note"], W / 2 + T_LVL.width / 2 - 8, 450, t0=10.0, seed=LEVEL + 9)
          if CONFIG["intro_note"] else None)

def scene_title(c, t):
    if t < 7.4: return
    # everything fades to navy over the last 0.5s so the lesson can cut in cleanly
    fade = 1 - in_cubic(prog(t, 14.5, 0.5))
    # logo builds straight into its parked spot at the top (same as the outro's parked logo)
    paste(c, logo_layer(t - 7.45), TOP_CENTER[0], TOP_CENTER[1], TOP_SCALE, fade)
    q = prog(t, 8.2, 0.55)
    paste(c, T_LVL, W / 2, 450, 1 + 1.4 * (1 - out_expo(q)) if q > 0 else 0, clamp(q * 3) * fade)
    for i, (spr, x) in enumerate(zip(T_C, T_CX)):
        q = out_expo(prog(t, 8.7 + i * 0.1, 0.55))
        paste(c, spr, x, 610 + (1 - q) * 60, 1, q * fade, reveal=0.1 + 0.9 * q)
    if CONFIG["hand_title_line"]:
        hand_underline(c, W / 2 - 280, W / 2 + 280, 681, out_cubic(prog(t, 9.3, 0.45)), seed=LEVEL, alpha=fade)
    else:
        q = out_expo(prog(t, 9.3, 0.7))
        if q > 0:
            w = 560 * q
            ImageDraw.Draw(c).rounded_rectangle((W / 2 - w / 2, 678, W / 2 + w / 2, 684), radius=3,
                                                fill=GOLD + (int(255 * fade),))
    q = out_expo(prog(t, 9.9, 0.5))
    paste(c, T_LABEL, W / 2, 770 + (1 - q) * 30, 1, q * fade, reveal=q)
    T_SKILLS.draw(c, t, alpha=fade)
    if T_NOTE:
        T_NOTE.draw(c, t, alpha=fade)

SCENES = [scene_reel, scene_title]

def frame(t):
    c = Image.new("RGBA", (W, H), BG + (255,))
    for s in SCENES:
        s(c, t)
    return c.convert("RGB")

def main():
    if "--still" in sys.argv:
        t = float(sys.argv[sys.argv.index("--still") + 1])
        frame(TIMELINE.warp(set_real_t(t))).save(_arg("--still-out", f"still_{t:g}.png")); return
    print("intro sections:", TIMELINE.describe(), flush=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3",
           "-pix_fmt", "yuv422p10le", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(TIMELINE.total * FPS))
    for i in range(n):
        p.stdin.write(frame(TIMELINE.warp(set_real_t(i / FPS))).tobytes())
        if i % 60 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", OUT)

if __name__ == "__main__":
    main()
