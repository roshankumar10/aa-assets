"""Atlas Academy - level intro (pairs with outro_level.py, reads the same CONFIG).

Slot-machine "Atlas ____" reel lands on "Academy" (from intro_v1), the
"Users -> builders" tagline gag, then a level title card listing the level's skills
(look set by "intro_skills_style" in levels.json - see outro_level.py for the choices).
    python intro_level.py --level 3            -> intro_level3.mov (ProRes 422 HQ, no audio)
    python intro_level.py --level 3 --skills-style list   -> intro_level3_list.mov
    python intro_level.py --level 3 --still 6  -> still_6.png preview

The slot-machine reel is set by "reel" in levels.json (top level = every level, levels/level_N.json
overrides single keys): prefix, words, land, loops, start, first_hold, last_hold, ease, snap,
overshoot, direction - see REEL_DEFAULTS below for what each does. One-off test without editing json:
    python intro_level.py --level 1 --reel words="Python,Robotics" --reel loops=2 --out test_intro.mov
"""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from render import (W, H, FPS, BG, GOLD, WHITE, FONT_DIR, spartan, dmsans, text_sprite,
                    item_block, paste, word_layout, exit_ofs, prog, clamp,
                    out_expo, out_cubic, in_cubic, out_back)
from render import caveat, Aside, hand_underline
from render import Timeline, set_real_t, logo_icon
from outro_level import CONFIG, LEVEL, logo_layer, TOP_CENTER, TOP_SCALE, _arg, durations, _data

# ---------------------------------------------------------------- reel settings
# levels.json "reel": {...} at the top level sets the default for every level; a "reel" block in
# levels/level_N.json overrides single keys for that level. Try one-offs without editing the json
# (repeatable; words are comma-separated):
#     python intro_level.py --level 1 --reel words="Python,Robotics,Games" --reel loops=2 --reel land=Academy
REEL_DEFAULTS = {
    "prefix": "Atlas",          # fixed word left of the reel
    "words": ["3D Modelling", "Animation", "Robotics", "Coding", "Circuitry", "Debugging"],
    "land": "Academy",          # word the reel stops on (shown in gold)
    "loops": 1,                 # times to cycle through "words" before landing
    "start": 1.15,              # seconds in when the first word snaps away
    "first_hold": 0.62,         # how long the first word sits before the next snap
    "last_hold": 0.32,          # gap before the final snap onto "land" (smaller = faster finish)
    "ease": 1.6,                # how the gaps shrink from first_hold to last_hold: 1 = evenly,
                                # higher = speeds up early then levels off
    "snap": 0.26,               # length of each snap animation
    "overshoot": 2.2,           # bounce when it lands on the final word (0 = no bounce)
    "direction": "up",          # words travel "up" or "down"
}
REEL_LAND_LATEST = 4.26         # landing any later and the tagline can't finish before the reel exits (7.2s)
REEL_LAND_DESIGN = 3.63         # where the original reel landed; the tagline keeps the same gap after it

def _reel_settings():
    r = dict(REEL_DEFAULTS)
    r.update(_data.get("reel") or {})
    r.update(_data["levels"][LEVEL - 1].get("reel") or {})
    for i, a in enumerate(sys.argv[:-1]):
        if a == "--reel" and "=" in sys.argv[i + 1]:
            k, v = (s.strip() for s in sys.argv[i + 1].split("=", 1))
            if k not in REEL_DEFAULTS:
                sys.exit(f"--reel: unknown setting '{k}'. Settings: {', '.join(REEL_DEFAULTS)}")
            r[k] = [w.strip() for w in v.split(",") if w.strip()] if k == "words" else v
    try:
        r["loops"] = int(r["loops"])
        for k in ("start", "first_hold", "last_hold", "ease", "snap", "overshoot"):
            r[k] = float(r[k])
    except ValueError as e:
        sys.exit(f"reel settings: {e}")
    if isinstance(r["words"], str):
        r["words"] = [w.strip() for w in r["words"].split(",") if w.strip()]
    problems = [msg for bad, msg in (
        (not r["words"], "'words' needs at least one word"),
        (not str(r["land"]).strip(), "'land' can't be empty"),
        (r["loops"] < 1, "'loops' must be 1 or more"),
        (min(r["first_hold"], r["last_hold"], r["snap"]) <= 0, "'first_hold', 'last_hold' and 'snap' must be above 0"),
        (r["ease"] <= 0, "'ease' must be above 0"),
        (r["overshoot"] < 0, "'overshoot' can't be negative"),
        (r["direction"] not in ("up", "down"), "'direction' must be \"up\" or \"down\""),
    ) if bad]
    if problems:
        sys.exit("reel settings: " + "; ".join(problems))
    return r

REEL = _reel_settings()
REEL_SEQ = list(REEL["words"]) * REEL["loops"] + [str(REEL["land"])]
N = len(REEL_SEQ) - 1                                   # number of snaps

def _gap(k):
    """Time between snap k and snap k+1: first_hold easing down to last_hold."""
    f = 1 - k / max(1, N - 2)
    return REEL["last_hold"] + (REEL["first_hold"] - REEL["last_hold"]) * f ** REEL["ease"]

_gaps = [_gap(k) for k in range(N - 1)]
_land = REEL["start"] + sum(_gaps) + REEL["snap"]
if _land > REEL_LAND_LATEST:
    _room = REEL_LAND_LATEST - REEL["start"] - REEL["snap"]
    if _room <= 0.05 * len(_gaps):
        sys.exit(f"reel settings: {len(REEL_SEQ)} words starting at {REEL['start']}s can't land by "
                 f"{REEL_LAND_LATEST}s - use fewer words/loops or an earlier 'start'")
    _scale = _room / sum(_gaps)
    _gaps = [g * _scale for g in _gaps]
    print(f"reel: would land at {_land:.2f}s, sped up x{1 / _scale:.2f} to land by {REEL_LAND_LATEST}s "
          f"(fewer words/loops, a lower 'first_hold' or an earlier 'start' avoids this)", flush=True)
R_TICKS = [REEL["start"] + sum(_gaps[:k]) for k in range(N)]
R_LAND = R_TICKS[-1] + REEL["snap"]
TAG_SHIFT = R_LAND - REEL_LAND_DESIGN                   # tagline, strike-through and "builders" follow the landing

DUR = 15.0
# section lengths from levels.json "intro_durations" (see outro_level.py); hold = where extra time pauses
# (the reel's pause point moves with a later landing so a longer section never freezes "builders" mid-scrawl)
SECTIONS = [("reel", 0.0, 7.4, min(7.0, 6.5 + max(0.0, TAG_SHIFT)), 0.6), ("title", 7.4, DUR, 13.0, 1.4)]
TIMELINE = Timeline(SECTIONS, durations("intro_durations", [s[0] for s in SECTIONS]), "intro")
OUT = _arg("--out", f"intro_level{LEVEL}{CONFIG['style_suffix']}.mov")
TAGLINE = ["An", "Academy", "for", "Technical", "&", "Creative", "Education", "Users"]

# ---------------------------------------------------------------- 1: Atlas + reel  0 - 7.4
R_FONT = spartan(170)
R_ATLAS = text_sprite(REEL["prefix"], R_FONT, GOLD)
R_ATLAS_W = R_FONT.getlength(REEL["prefix"])
R_SPR = [text_sprite(w, R_FONT, GOLD if k == N else WHITE) for k, w in enumerate(REEL_SEQ)]
R_W = [R_FONT.getlength(w) for w in REEL_SEQ]
R_GAP, R_STEP, R_Y = 44, 260, 470
R_DIR = 1 if REEL["direction"] == "up" else -1          # up: next word rises from below
_too_wide = [w for w, rw in zip(REEL_SEQ, R_W) if rw > 1380 or R_ATLAS_W + R_GAP + rw > W - 80]
if _too_wide:
    print(f"reel: these will be cut off at this size, use shorter words: {', '.join(sorted(set(_too_wide)))}", flush=True)

# snaps land at R_TICKS (set from the reel settings above); the last one bounces onto the "land" word
def reel_pos(t):
    pos = 0.0
    for k, tk in enumerate(R_TICKS):
        q = prog(t, tk, REEL["snap"])
        pos += out_back(q, REEL["overshoot"]) if k == N - 1 and REEL["overshoot"] > 0 else out_expo(q)
    return pos

# "reel_logo": true (intro_split.json) - once the reel lands, "Atlas" and "Academy" slide into the logo lockup
# (ref_logo.PNG / the Outro_v2 end card: cap+globe icon on the left, the two words stacked and left-aligned
# beside it) while the icon pops in
REEL_LOGO = bool(CONFIG.get("reel_logo", False))
R_POP = 0.6                                # pop size: grows from 1 - R_POP, overshoots by R_POP x out_back's bounce
R_TAG_GAP = 110 if REEL_LOGO else 0      # tagline / "builders" sit lower, under the taller lockup
if REEL_LOGO:
    def _ink(img):
        """Bounding box of the solid part of a sprite (ignores soft edges and padding)."""
        return img.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    R_ICON = logo_icon()
    _ib, _ai, _bi = _ink(R_ICON), _ink(R_ATLAS), _ink(R_SPR[N])
    # measured from ref_logo.PNG, in its pixels relative to its icon's top-left (icon 190 x 150):
    # "Atlas" ink left 204 / top 71; "Academy" ink left 192, 183 wide, bottom (the y's tail) level with the
    # globe's bottom at 150; whole lockup 375 wide
    _u = (_ib[3] - _ib[1]) / 150
    R_LOCK_SCALE = 183 * _u / (_bi[2] - _bi[0])
    _ox, _oy = W / 2 - 375 * _u / 2, 440 - 150 * _u / 2          # icon's top-left, lockup centred on (W/2, 440)
    R_ICON_XY = (_ox + R_ICON.width / 2 - _ib[0], _oy + R_ICON.height / 2 - _ib[1])
    def _centre(spr, ink, left, top):
        """Paste centre for spr at R_LOCK_SCALE so its ink box's top-left lands on (left, top)."""
        return (left + (spr.width / 2 - ink[0]) * R_LOCK_SCALE, top + (spr.height / 2 - ink[1]) * R_LOCK_SCALE)
    R_LOCK = [_centre(R_ATLAS, _ai, _ox + 204 * _u, _oy + 71 * _u),
              _centre(R_SPR[N], _bi, _ox + 192 * _u, _oy + 150 * _u - (_bi[3] - _bi[1]) * R_LOCK_SCALE)]

def scene_reel(c, t):
    if t > 7.7: return
    ey, ea = exit_ofs(t, 7.2, 0.4, -80)
    k = 0.0                                          # 0 = one line (reel), 1 = logo lockup
    if REEL_LOGO:
        q = out_cubic(prog(t, R_LAND + 0.25, 0.55))
        paste(c, R_ICON, R_ICON_XY[0], R_ICON_XY[1] + ey,
              1 - R_POP + R_POP * out_back(prog(t, R_LAND + 0.25, 0.6)) if q > 0 else 0,
              clamp(q * 2.5) * ea, rot=(1 - q) * -18)
        k = out_expo(prog(t, R_LAND + 0.1, 0.7))
    pos = reel_pos(t)
    i0 = int(clamp(pos, 0, N))
    frac = clamp(pos - i0)
    rw = R_W[i0] + (R_W[min(i0 + 1, N)] - R_W[i0]) * frac
    left = W / 2 - (R_ATLAS_W + R_GAP + rw) / 2      # whole line re-centres as the word width changes
    q = out_expo(prog(t, 0.15, 0.6))
    if REEL_LOGO and t >= R_LAND:                    # landed: both words drawn directly, sliding into the lockup
        spr = R_SPR[N]
        for word, (x0, y0), (x1, y1) in ((R_ATLAS, (left + R_ATLAS_W / 2, R_Y), R_LOCK[0]),
                                         (spr, (left + R_ATLAS_W + R_GAP - 8 + spr.width / 2, R_Y), R_LOCK[1])):
            paste(c, word, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k + ey, 1 + (R_LOCK_SCALE - 1) * k, ea)
    else:
        paste(c, R_ATLAS, left + R_ATLAS_W / 2, R_Y + (1 - q) * 80 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)

    # reel window: only the slot band is visible
    band_h = 340
    layer = Image.new("RGBA", (1400, band_h), (0, 0, 0, 0))
    vel = abs(reel_pos(t + 0.5 / FPS) - reel_pos(t - 0.5 / FPS)) * FPS   # words per second
    taps = 1 + min(6, int(vel * 1.2))                                     # fake motion blur
    appear = out_expo(prog(t, 0.45, 0.5))
    for k, spr in enumerate(R_SPR):
        dy = (k - pos) * R_STEP * R_DIR
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
    if not (REEL_LOGO and t >= R_LAND):              # once landed the word is drawn above, without the slot
        paste(c, layer, left + R_ATLAS_W + R_GAP + 700 - 8, R_Y + ey, 1, ea)

    # tagline: "... Education Users" -> Users struck out -> "builders" scrawled in
    f = dmsans(56, 450)
    xs = word_layout(TAGLINE, f, 15)
    for i, (w, x) in enumerate(zip(TAGLINE, xs)):
        q = out_expo(prog(t, 4.3 + TAG_SHIFT + i * 0.07, 0.5))
        paste(c, text_sprite(w, f, WHITE), x, 650 + R_TAG_GAP + (1 - q) * 40 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)
    uw = f.getlength("Users")
    q = out_cubic(prog(t, 5.5 + TAG_SHIFT, 0.35))
    if q > 0 and ea > 0.05:
        x0 = xs[-1] - uw / 2
        ImageDraw.Draw(c).rectangle((x0, 660 + R_TAG_GAP + ey - 3, x0 + uw * q, 660 + R_TAG_GAP + ey + 3),
                                    fill=GOLD + (int(255 * ea),))
    q = prog(t, 5.85 + TAG_SHIFT, 0.5)
    if q > 0:
        spr = text_sprite("builders", caveat(96), GOLD)
        paste(c, spr, xs[-1] + 10, 575 + R_TAG_GAP + ey, out_back(q, 2.4), clamp(q * 3) * ea, rot=8 + (1 - out_cubic(q)) * 20)

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
