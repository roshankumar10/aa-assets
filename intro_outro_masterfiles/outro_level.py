"""Atlas Academy - end-of-level outro (kinetic version of Outro_v2's layout).

Each level's content lives in its own file, levels/level_N.json (level_1.json, level_2.json, ...).
levels.json holds shared defaults; a key in a level file overrides the levels.json value for that level.
Below, "per level" means levels/level_N.json and "top level" means levels.json. Render one level with:
    python outro_level.py --level 3            -> outro_level3.mov (ProRes 422 HQ, no audio)
    python outro_level.py --level 3 --still 6  -> still_6.png preview
Student name comes from "first_name"/"last_name" in levels/level_N.json, else levels.json; override per render with
    python outro_level.py --level 3 --first Jane --last Doe   -> outro_level3_Jane_Doe.mov
Or render every level's intro + outro with make_all.py.

How the lists look is set in levels.json, per level or once at the top level as the default:
    "intro_skills_style"  intro title card skills      chips | tube | list | checklist | numbered | inline |
                                                       columns | handwritten
    "outro_skills_style"  outro "Skills learned:"      (same choices)
    "learned_style"       outro "What they learned"      cards | (any of the above)
Try one without editing the json (adds _<style> to the file name so nothing is overwritten):
    python outro_level.py --level 3 --skills-style columns --learned-style checklist
Compare them all side by side with preview_styles.py.

Personal handwritten note on the end card (writes itself on under the URL; logo shifts up to fit).
Set "note" / "note_from" in levels.json (per level or top level), or per student on the command line.
{first} and {last} are swapped for the student's name, so one note can serve a whole class:
    python outro_level.py --level 1 --first Jane --last Doe --note "So proud of your buzzer song, {first}!" --from "Ms. K"

More handwriting (levels.json, per level or top level):
    "intro_note": "this one's a fun one!"   margin note + pen arrow at the level title on the intro card
    "learned_note": "..."                    same, at the outro "What they learned" heading
    "skills_note": "..."                     same, at the outro "Skills learned:" heading
    "chip_notes": {"For Loops": "my fave!"}  small note + pen arrow under matching chips (any chip row;
                                             keep notes short, ~25 characters)
    "hand_title_line": true                  intro course-title underline becomes a wobbly pen stroke
    "hand_url_line": true                    same for the end-card URL underline
    "hand_lines": true                       shorthand default for both of the above
    command-line equivalents: --intro-note / --learned-note / --skills-note "..."
                              --hand-title-line / --hand-url-line / --hand-lines  (turn on)
                              --straight-title-line / --straight-url-line          (turn off)

Section lengths in seconds (levels.json top level, and/or per level to override single sections):
    "outro_durations": {"complete": 4.4, "learned": 3.6, "skills": 2.4, "next": 1.9, "end": 4.2}
    "intro_durations": {"reel": 7.4, "title": 7.6}
Longer = the section pauses once everything is on screen; shorter = less pause (each section has a
minimum so its animations can finish - you get a warning if you go under it). Try without editing:
    python outro_level.py --level 1 --duration learned=5 --duration end=6

Output file name for a one-off test, so nothing real gets overwritten:
    python outro_level.py --level 1 --out test_outro.mov
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw
from render import (set_real_t, W, H, FPS, BG, GOLD, WHITE, GREEN, CHIP_LINE, spartan, dmsans, text_sprite,
                    logo_icon, paste, word_layout, exit_ofs, prog, clamp, wrap, item_block, HandNote,
                    hand_underline, Aside, Timeline,
                    out_expo, out_cubic, out_back)

# ---------------------------------------------------------------- CONFIG
LEVEL = int(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else 1
if "--config" in sys.argv and "--level" not in sys.argv:      # a --config file can pick the level
    with open(sys.argv[sys.argv.index("--config") + 1], encoding="utf-8") as _f:
        LEVEL = int(json.load(_f).get("render_level", LEVEL))
with open("levels.json", encoding="utf-8") as _f:
    _data = json.load(_f)
# each level lives in its own file: levels/level_1.json, levels/level_2.json, ...
_data["levels"] = []
while os.path.exists(f"levels/level_{len(_data['levels']) + 1}.json"):
    with open(f"levels/level_{len(_data['levels']) + 1}.json", encoding="utf-8") as _f:
        _data["levels"].append(json.load(_f))
def _arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
# --config file.json: its keys sit on top of this level's file (dicts like "reel" merge key by key),
# so a separate render (e.g. intro_split.json) can change settings without touching the shared json
if "--config" in sys.argv:
    with open(_arg("--config", ""), encoding="utf-8") as _f:
        for _k, _v in json.load(_f).items():
            _lvd = _data["levels"][LEVEL - 1]
            _lvd[_k] = dict(_lvd.get(_k) or {}, **_v) if isinstance(_v, dict) else _v

# student name: command line, else this level's file, else levels.json, else placeholder
_lv = _data["levels"][LEVEL - 1]
_NAME_PLACEHOLDERS = {"first_name": "First Name", "last_name": "Last Name"}
CONFIG = dict(_lv, url=_data["url"], **{k: _arg(flag, _lv.get(k) or _data.get(k) or _NAME_PLACEHOLDERS[k])
                                        for k, flag in (("first_name", "--first"), ("last_name", "--last"))})
# a real name goes in the file name so it never overwrites the placeholder render
_suffix = "".join(f"_{CONFIG[k]}".replace(" ", "_") for k in _NAME_PLACEHOLDERS
                  if CONFIG[k] != _NAME_PLACEHOLDERS[k])
DEFAULT_STYLES = {"intro_skills_style": "tube", "outro_skills_style": "chips", "learned_style": "cards"}
for _k, _flag in (("intro_skills_style", "--skills-style"), ("outro_skills_style", "--skills-style"),
                  ("learned_style", "--learned-style")):
    CONFIG[_k] = _arg(_flag, CONFIG.get(_k) or _data.get(_k) or DEFAULT_STYLES[_k])
CONFIG["style_suffix"] = "".join(f"_{_arg(f, '')}" for f in ("--skills-style", "--learned-style") if f in sys.argv)
for _k, _flag in (("note", "--note"), ("note_from", "--from")):
    CONFIG[_k] = (_arg(_flag, CONFIG.get(_k) or _data.get(_k) or "")
                  .replace("{first}", CONFIG["first_name"]).replace("{last}", CONFIG["last_name"]).strip())
def _setting(key, default):
    """This level's value, else the top-level value, else default (so a level can switch a default off)."""
    lv = _data["levels"][LEVEL - 1]
    return lv[key] if key in lv else _data.get(key, default)
_hand = _setting("hand_lines", False)
for _k in ("hand_title_line", "hand_url_line"):
    _flag = "--" + _k.replace("_", "-")
    _off = _flag.replace("hand", "straight")
    CONFIG[_k] = (_off not in sys.argv and
                  (_flag in sys.argv or "--hand-lines" in sys.argv or bool(_setting(_k, _hand))))
for _k in ("intro_note", "learned_note", "skills_note"):
    CONFIG[_k] = _arg("--" + _k.replace("_", "-"), _setting(_k, "")).strip()
# notes under individual chips: {"For Loops": "my favourite!"}; CLI: --chip-note "For Loops=my favourite!" (repeatable)
CONFIG["chip_notes"] = dict(_setting("chip_notes", {}) or {})
for _i, _a in enumerate(sys.argv[:-1]):
    if _a == "--chip-note" and "=" in sys.argv[_i + 1]:
        _label, _text = sys.argv[_i + 1].split("=", 1)
        CONFIG["chip_notes"][_label.strip()] = _text.strip()
if "--note" in sys.argv and not _suffix:
    _suffix = "_note"                    # don't overwrite the plain outro with a personalised one
CONFIG["out"] = _arg("--out", _setting("out", "").format(level=LEVEL) or
                     f"outro_level{LEVEL}{_suffix}{CONFIG['style_suffix']}.mov")
DUR = 15.0 + (1.5 if CONFIG["note"] else 0)   # longer hold on the end card so the note can be read

def durations(key, names):
    """Section lengths: top-level dict, then this level's dict, then --duration name=seconds."""
    d = dict(_data.get(key) or {})
    d.update(_data["levels"][LEVEL - 1].get(key) or {})
    for i, a in enumerate(sys.argv[:-1]):
        if a == "--duration" and "=" in sys.argv[i + 1]:
            k, v = sys.argv[i + 1].split("=", 1)
            if k.strip() in names:                 # the flag is shared with the intro's sections
                d[k.strip()] = float(v)
    return d

# (name, design start, design end, hold point, max shortening) - hold points sit after each
# section's animations have landed and before its exit, so a pause there looks intentional
_end_hold = 15.0 if CONFIG["note"] else 14.6
SECTIONS = [("complete", 0.0, 4.4, 3.9, 0.25), ("learned", 4.4, 8.0, 7.25, 0.5),
            ("skills", 8.0, 10.4, 10.17, 0.0), ("next", 10.4, 12.3, 11.9, 0.1),
            ("end", 12.3, DUR, _end_hold, DUR - _end_hold)]
_durs = durations("outro_durations", [s[0] for s in SECTIONS])
# some styles hold their finished list on screen a little longer (seconds on top of the section)
STYLE_HOLD = {"circuit": 3.0, "code": 3.0}
for _sec, _style_key, _base in (("learned", "learned_style", 3.6), ("skills", "outro_skills_style", 2.4)):
    if CONFIG[_style_key] in STYLE_HOLD:
        _durs[_sec] = float(_durs.get(_sec, _base)) + STYLE_HOLD[CONFIG[_style_key]]
TIMELINE = Timeline(SECTIONS, _durs, "outro")
# "name_plate": false drops the name / "Level N complete" card: the logo still builds and parks at the
# top, then "What they learned" comes straight in (the rest of the "complete" section is skipped)
NAME_PLATE = bool(_setting("name_plate", True))
# "learned_section": false / "skills_section": false drop "What they learned" (B) / "Skills learned" (C)
# (e.g. when the personalized intro shows those lists instead); the logo stays parked across the gap
LEARNED = bool(_setting("learned_section", True))
SKILLS = bool(_setting("skills_section", True))
# "logo": false / "end_card": false drop the Atlas Academy logo / the closing logo + URL card; with
# "name_plate", "learned_section" and "skills_section" also off, only "What's next?" is left
LOGO = bool(_setting("logo", True))
END_CARD = bool(_setting("end_card", True))
_SKIP_AT = 2.0                                          # logo has parked by here
def real_time(d):
    """Design time -> timeline (real) time, for a point outside a pause."""
    for rs, re_, ds, rate in TIMELINE.pieces:
        if rate and ds - 1e-9 <= d <= ds + (re_ - rs) + 1e-9:
            return rs + (d - ds)
    return TIMELINE.total
_cuts = []                                              # design-time ranges to jump over, in order
if not NAME_PLATE:
    _cuts.append((_SKIP_AT if LOGO else 0.0, 4.3))      # straight to just before B / C comes in
if not (LEARNED and SKILLS):
    _from = 8.15 if LEARNED else (4.55 if NAME_PLATE else 4.3)   # after B's exit / A's exit
    _cuts.append((_from, 7.9 if SKILLS else 10.3))               # to just before C / D comes in
_SKIPS = [(real_time(a), max(real_time(a), real_time(b))) for a, b in _cuts]
# without the end card it stops once "What's next?" has slid out (design 12.4s)
TOTAL = (TIMELINE.total if END_CARD else real_time(12.4)) - sum(b - a for a, b in _SKIPS)
def warp(t):
    """Output time -> design time, jumping over the skipped sections."""
    for a, b in _SKIPS:
        if t >= a:
            t += b - a
    return TIMELINE.warp(set_real_t(t))

# ---------------------------------------------------------------- logo group
# Icon left, two-line wordmark right, laid out to match ref_logo.PNG (measured in its pixels, relative to its
# icon's top-left, icon 150 tall): "Atlas" ink left 204 / top 71; "Academy" ink left 192, 183 wide, its y's tail
# level with the globe's bottom (150); whole lockup 375 wide. Same numbers as the intro's reel lockup.
def _ink(img):
    """Bounding box of the solid part of an image (ignores soft edges and padding)."""
    return img.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
ICON = logo_icon()                      # 455x390
GW, GH = 1060, 420                       # group canvas
G_ORIGIN = (520, 290)                    # its top-left on the end card (Outro_v2 position)
_ib = _ink(ICON)
_u = (_ib[3] - _ib[1]) / 150             # ref_logo.PNG px -> ours
_ix, _iy = GW / 2 - 375 * _u / 2, GH / 2 - 150 * _u / 2   # icon ink top-left, lockup centred in the group
ICON_C = (_ix + ICON.width / 2 - _ib[0], _iy + ICON.height / 2 - _ib[1])
_b118 = _ink(text_sprite("Academy", spartan(118), GOLD))
LOGO_FONT = spartan(round(118 * 183 * _u / (_b118[2] - _b118[0])))   # size that makes "Academy" 183 ref px wide

def _word_chars(word, left, top=None, bottom=None):
    """Letter sprites + centres for one word, placed so its ink box's left edge and top (or bottom) land there."""
    chars, x = [], 0.0
    for ch in word:
        w = LOGO_FONT.getlength(ch)
        chars.append((text_sprite(ch, LOGO_FONT, GOLD), x + w / 2)); x += w
    probe = Image.new("RGBA", (int(x) + 400, 600), (0, 0, 0, 0))
    for spr, cx in chars:
        paste(probe, spr, cx + 200, 300, 1, 1)
    ink = _ink(probe)
    dx = left - (ink[0] - 200)
    dy = (top - (ink[1] - 300)) if top is not None else (bottom - (ink[3] - 300))
    return [(spr, cx + dx, dy) for spr, cx in chars]

WORDS = (_word_chars("Atlas", _ix + 204 * _u, top=_iy + 71 * _u)
         + _word_chars("Academy", _ix + 192 * _u, bottom=_iy + 150 * _u))
NOTE_LIFT = 95 if CONFIG["note"] else 0   # end card moves up to make room for the handwritten note
END_CENTER = (G_ORIGIN[0] + GW / 2, G_ORIGIN[1] + GH / 2 - NOTE_LIFT)   # where it sits on the end card
TOP_CENTER, TOP_SCALE = (W / 2, 165), 0.52

def logo_layer(t):
    layer = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    q = prog(t, 0.1, 0.7)
    if q > 0:
        paste(layer, ICON, *ICON_C, 0.6 + 0.4 * out_back(q), clamp(q * 2.5), rot=(1 - out_cubic(q)) * -12)
    for i, (spr, x, y) in enumerate(WORDS):
        q = out_expo(prog(t, 0.4 + i * 0.035, 0.5))
        paste(layer, spr, x, y + (1 - q) * 60, 1, q, reveal=0.1 + 0.9 * q)
    return layer

def logo(c, t):
    # centred intro -> parks at top (1.2-1.9s) -> returns to centre for the end card (12.2-13.0s)
    up = out_expo(prog(t, 1.2, 0.7))
    down = out_expo(prog(t, 12.2, 0.8))
    k = up * (1 - down)
    cx = END_CENTER[0] + (TOP_CENTER[0] - END_CENTER[0]) * k
    cy = END_CENTER[1] + (TOP_CENTER[1] - END_CENTER[1]) * k
    paste(c, logo_layer(t), cx, cy, 1 + (TOP_SCALE - 1) * k)

# ---------------------------------------------------------------- A: level complete  1.6 - 4.4
A_HEAD = f"{CONFIG['level']} complete"
A_FONT = spartan(150)
A_LET = []
_x = W / 2 - A_FONT.getlength(A_HEAD) / 2
for ch in A_HEAD:
    w = A_FONT.getlength(ch)
    A_LET.append((text_sprite(ch, A_FONT, GOLD), _x + w / 2, ch == " ")); _x += w
A_SUB_W = CONFIG["course"].split()
A_SUB = [text_sprite(w, dmsans(72, 450), WHITE) for w in A_SUB_W]
A_SUBX = word_layout(A_SUB_W, dmsans(72, 450), 20)
N_FONT = spartan(88)
_names = [CONFIG["first_name"], CONFIG["last_name"]]
A_NAME = [text_sprite(n, N_FONT, c) for n, c in zip(_names, (WHITE, GOLD))]
A_NAMEX = word_layout(_names, N_FONT, 28)

def check_badge(c, t, cx, cy, ea):
    """Gold ring draws on, then the tick strokes in."""
    s = 2
    r = 62
    img = Image.new("RGBA", ((r * 2 + 20) * s,) * 2, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    q = out_cubic(prog(t, 1.7, 0.55))
    if q > 0:
        d.arc((10 * s, 10 * s, (10 + r * 2) * s, (10 + r * 2) * s), -90, -90 + 360 * q,
              fill=GOLD, width=9 * s)
    q = out_cubic(prog(t, 2.1, 0.35))
    if q > 0:
        o = 10 + r
        p0, p1, p2 = (o - 28, o + 2), (o - 8, o + 22), (o + 30, o - 20)
        seg1 = clamp(q / 0.4); seg2 = clamp((q - 0.4) / 0.6)
        pts = [p0, (p0[0] + (p1[0] - p0[0]) * seg1, p0[1] + (p1[1] - p0[1]) * seg1)]
        if seg2 > 0:
            pts.append((p1[0] + (p2[0] - p1[0]) * seg2, p1[1] + (p2[1] - p1[1]) * seg2))
        d.line([(x * s, y * s) for x, y in pts], fill=GREEN, width=11 * s, joint="curve")
    paste(c, img.resize((img.width // s, img.height // s), Image.LANCZOS), cx, cy, 1, ea)

def scene_a(c, t):
    if t < 1.5 or t > 4.7: return
    ey, ea = exit_ofs(t, 4.2)
    check_badge(c, t, W / 2, 395 + ey, ea)
    for i, (spr, x) in enumerate(zip(A_NAME, A_NAMEX)):
        q = out_expo(prog(t, 1.95 + i * 0.15, 0.55))
        paste(c, spr, x, 540 + (1 - q) * 60 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)
    for i, (spr, x, space) in enumerate(A_LET):
        if space: continue
        q = prog(t, 2.3 + i * 0.03, 0.5)
        paste(c, spr, x, 690 + ey, out_back(q) if q > 0 else 0, clamp(q * 4) * ea,
              rot=(1 - out_cubic(q)) * 20)
    for i, (spr, x) in enumerate(zip(A_SUB, A_SUBX)):
        q = out_expo(prog(t, 3.0 + i * 0.1, 0.55))
        paste(c, spr, x, 820 + (1 - q) * 60 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)

# ---------------------------------------------------------------- B: what we learned  4.4 - 8.0
B_HEAD = text_sprite(_setting("learned_heading", "What they learned"), spartan(104), GOLD)
CARD_W, CARD_H = 500, 210
COLS, GAP_X, GAP_Y = 3, 40, 30

def card_sprite(num, name):
    s = 3
    img = Image.new("RGBA", (CARD_W * s, CARD_H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2 * s, 2 * s, (CARD_W - 2) * s, (CARD_H - 2) * s), radius=28 * s,
                        fill=(33, 43, 92, 255), outline=CHIP_LINE, width=2 * s)
    d.text((34 * s, 22 * s), f"{num:02d}", font=spartan(64 * s), fill=GOLD)
    f = dmsans(38 * s, 500)
    y = 98 * s
    for line in wrap(name, f, (CARD_W - 68) * s)[:2]:
        d.text((34 * s, y), line, font=f, fill=WHITE); y += 46 * s
    return img.resize((CARD_W, CARD_H), Image.LANCZOS)

B_CARDS = [card_sprite(i + 1, p) for i, p in enumerate(CONFIG["learned"])]
_row_w = COLS * CARD_W + (COLS - 1) * GAP_X
def _grid_pos(i, n):
    """3-wide grid; a partial last row is centred instead of left-aligned."""
    row, col = divmod(i, COLS)
    in_row = min(COLS, n - row * COLS)
    w = in_row * CARD_W + (in_row - 1) * GAP_X
    return (W / 2 - w / 2 + CARD_W / 2 + col * (CARD_W + GAP_X), 600 + row * (CARD_H + GAP_Y))

B_POS = [_grid_pos(i, len(B_CARDS)) for i in range(len(B_CARDS))]
B_BLOCK = (None if CONFIG["learned_style"] == "cards" else
           item_block(CONFIG["learned_style"], CONFIG["learned"], top=490, bottom=980, t0=4.8, span=1.0,
                      notes=CONFIG["chip_notes"], note_dur=0.7, hold=7.2, var="learned"))
B_ASIDE = (Aside(CONFIG["learned_note"], W / 2 + B_HEAD.width / 2 - 8, 405, t0=5.5, lift=135,
                 max_dur=1.0, seed=LEVEL + 21, arrow=bool(_setting("learned_note_arrow", True)))
           if CONFIG["learned_note"] else None)

def scene_b(c, t):
    if t < 4.3 or t > 8.3: return
    ey, ea = exit_ofs(t, 7.8)
    q = out_expo(prog(t, 4.45, 0.6))
    paste(c, B_HEAD, W / 2 - (1 - q) * 220, 405 + ey, 1, q * ea)
    if B_ASIDE:
        B_ASIDE.draw(c, t, alpha=ea, dy=ey)
    if B_BLOCK:
        B_BLOCK.draw(c, t, alpha=ea, dy=ey)
        return
    for i, (spr, (x, y)) in enumerate(zip(B_CARDS, B_POS)):
        q = prog(t, 4.8 + i * 0.16, 0.55)
        paste(c, spr, x, y + (1 - out_expo(q)) * 100 + ey, 0.85 + 0.15 * out_back(q) if q > 0 else 0,
              clamp(q * 3) * ea)

# ---------------------------------------------------------------- C: skills unlocked  8.0 - 10.4
_c_style = CONFIG["outro_skills_style"]

def skills_scene(heading, items, note=""):
    """Section C: a heading + list (+ optional margin note). Built by a function so another list, e.g.
    "Curriculum Highlights", can reuse the same layout and timing (intro_split.py plays it a second time)."""
    head = text_sprite(heading, spartan(104), GOLD)
    block = item_block(_c_style, items, top=560, bottom=880, t0=8.4, span=1.25,
                       y={"chips": 650, "tube": 620, "circuit": 680}.get(_c_style), notes=CONFIG["chip_notes"],
                       note_dur=0.5, t_out=10.17, hold=10.12, var="skills")
    # the note's arrow points down at the list (list styles), else at the heading as before
    target = (block.right + 28, block.first_y) if hasattr(block, "right") else None
    aside = (Aside(note, W / 2 + head.width / 2 - 8, 470, t0=8.6, lift=135,
                   max_dur=0.8, seed=LEVEL + 33, target=target,
                   arrow=bool(_setting("skills_note_arrow", True))) if note else None)

    def scene(c, t):
        if t < 7.9 or t > 10.7: return
        ey, ea = exit_ofs(t, 10.2)
        q = out_expo(prog(t, 8.05, 0.6))
        paste(c, head, W / 2 + (1 - q) * 220, 470 + ey, 1, q * ea)
        if aside:
            aside.draw(c, t, alpha=ea, dy=ey)
        if getattr(block, "t_out", None):          # styles with their own exit animation
            block.draw(c, t)
        else:
            block.draw(c, t, alpha=ea, dy=ey)
    return scene

# "skills_key": list to show here instead of "skills" (outro_split.json uses "highlights")
scene_c = skills_scene(_setting("skills_heading", "Skills learned:"), CONFIG[_setting("skills_key", "skills")],
                       CONFIG["skills_note"])

# ---------------------------------------------------------------- D: what's next  10.4 - 12.3
# final level has no next_level: close on "Keep building." instead
_final = not CONFIG["next_level"]
D_HEAD = text_sprite("All levels complete" if _final else "What's next?", spartan(96), GOLD)
D_LVL = text_sprite("Keep building." if _final else CONFIG["next_level"], spartan(190), WHITE)
D_TW = CONFIG["next_title"].split()
D_T = [text_sprite(w, dmsans(76, 450), WHITE) for w in D_TW]
D_TX = word_layout(D_TW, dmsans(76, 450), 22)

def scene_d(c, t):
    if t < 10.3 or t > 12.6: return
    ey, ea = exit_ofs(t, 12.0)
    q = out_expo(prog(t, 10.45, 0.5))
    paste(c, D_HEAD, W / 2, 440 + (1 - q) * 50 + ey, 1, q * ea, reveal=q)
    q = prog(t, 10.75, 0.55)
    paste(c, D_LVL, W / 2, 610 + ey, 1 + 1.4 * (1 - out_expo(q)) if q > 0 else 0, clamp(q * 3) * ea)
    for i, (spr, x) in enumerate(zip(D_T, D_TX)):
        q = out_expo(prog(t, 11.15 + i * 0.1, 0.5))
        paste(c, spr, x, 780 + (1 - q) * 60 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)

# ---------------------------------------------------------------- E: end card  12.2 - 15.0
URL_FONT = spartan(64)

E_NOTE = (HandNote(CONFIG["note"], W / 2, 925, t0=13.3, signature=CONFIG["note_from"])
          if CONFIG["note"] else None)

def scene_e(c, t):
    url, y = CONFIG["url"], 770 - NOTE_LIFT
    n = int(len(url) * clamp(prog(t, 13.1, 0.75)))
    if n:
        spr = text_sprite(url[:n], URL_FONT, WHITE)
        paste(c, spr, W / 2 - URL_FONT.getlength(url) / 2 + spr.width / 2 - 8, y)
    if CONFIG["hand_url_line"]:
        hand_underline(c, W / 2 - 260, W / 2 + 260, y + 63, out_cubic(prog(t, 13.8, 0.4)), seed=LEVEL + 50)
    else:
        q = out_expo(prog(t, 13.8, 0.6))
        if q > 0:
            w = 520 * q
            ImageDraw.Draw(c).rounded_rectangle((W / 2 - w / 2, y + 60, W / 2 + w / 2, y + 66), radius=3, fill=GOLD)
    if E_NOTE:
        E_NOTE.draw(c, t)

SCENES = ([logo] * LOGO + [scene_a] * NAME_PLATE + [scene_b] * LEARNED + [scene_c] * SKILLS + [scene_d] +
          [scene_e] * END_CARD)

def frame(t):
    c = Image.new("RGBA", (W, H), BG + (255,))
    for s in SCENES:
        s(c, t)
    return c.convert("RGB")

def main():
    if "--still" in sys.argv:
        t = float(sys.argv[sys.argv.index("--still") + 1])
        frame(warp(t)).save(_arg("--still-out", f"still_{t:g}.png")); return
    out = CONFIG["out"]
    print("outro sections:", TIMELINE.describe(), flush=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3",
           "-pix_fmt", "yuv422p10le", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for i in range(n):
        p.stdin.write(frame(warp(i / FPS)).tobytes())
        if i % 60 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", out)

if __name__ == "__main__":
    main()
