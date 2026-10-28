"""Atlas Academy - end-of-level outro (kinetic version of Outro_v2's layout).

Level content lives in levels.json. Render one level with:
    python outro_level.py --level 3            -> outro_level3.mov (ProRes 422 HQ, no audio)
    python outro_level.py --level 3 --still 6  -> still_6.png preview
Student name defaults to first_name/last_name in levels.json; override per render with
    python outro_level.py --level 3 --first Jane --last Doe   -> outro_level3_Jane_Doe.mov
Or render every level's intro + outro with make_all.py.
"""
import json, subprocess, sys
from PIL import Image, ImageDraw
from render import (W, H, FPS, BG, GOLD, WHITE, GREEN, CHIP_LINE, spartan, dmsans, text_sprite,
                    chip_sprite, chip_row, TubeLine, logo_icon, paste, word_layout, exit_ofs, prog, clamp,
                    out_expo, out_cubic, out_back)

# ---------------------------------------------------------------- CONFIG
LEVEL = int(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else 1
with open("levels.json", encoding="utf-8") as _f:
    _data = json.load(_f)
def _arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

CONFIG = dict(_data["levels"][LEVEL - 1], url=_data["url"],
              first_name=_arg("--first", _data.get("first_name", "First Name")),
              last_name=_arg("--last", _data.get("last_name", "Last Name")))
_suffix = "".join(f"_{CONFIG[k]}".replace(" ", "_") for k, flag in
                  (("first_name", "--first"), ("last_name", "--last")) if flag in sys.argv)
CONFIG["out"] = f"outro_level{LEVEL}{_suffix}.mov"
DUR = 15.0

# ---------------------------------------------------------------- logo group
# Layout copied from the Outro_v2 end card: icon left, two-line wordmark right.
ICON = logo_icon()                      # 455x390, top-left at (535, 300) in the reference
LOGO_FONT = spartan(118)
GW, GH = 1060, 420                       # group canvas; reference origin (520, 290)
G_ORIGIN = (520, 290)
ICON_C = (535 + ICON.width / 2 - G_ORIGIN[0], 300 + ICON.height / 2 - G_ORIGIN[1])
WORDS = []
for word, y in (("Atlas", 400), ("Academy", 520)):
    x = 1015
    for ch in word:
        w = LOGO_FONT.getlength(ch)
        WORDS.append((text_sprite(ch, LOGO_FONT, GOLD), x + w / 2 - G_ORIGIN[0], y - G_ORIGIN[1]))
        x += w
END_CENTER = (G_ORIGIN[0] + GW / 2, G_ORIGIN[1] + GH / 2)   # where it sits on the end card
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
B_HEAD = text_sprite("What we learned", spartan(104), GOLD)
CARD_W, CARD_H = 500, 210
COLS, GAP_X, GAP_Y = 3, 40, 30

def wrap(text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= maxw or not cur: cur = trial
        else: lines.append(cur); cur = w
    return lines + [cur]

def card_sprite(num, name):
    s = 3
    img = Image.new("RGBA", (CARD_W * s, CARD_H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2 * s, 2 * s, (CARD_W - 2) * s, (CARD_H - 2) * s), radius=28 * s,
                        fill=(33, 43, 92, 255), outline=CHIP_LINE, width=2 * s)
    d.text((34 * s, 22 * s), f"{num:02d}", font=spartan(64 * s), fill=GOLD)
    cx, cy, r = (CARD_W - 46) * s, 50 * s, 11 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN)
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

def scene_b(c, t):
    if t < 4.3 or t > 8.3: return
    ey, ea = exit_ofs(t, 7.8)
    q = out_expo(prog(t, 4.45, 0.6))
    paste(c, B_HEAD, W / 2 - (1 - q) * 220, 405 + ey, 1, q * ea)
    for i, (spr, (x, y)) in enumerate(zip(B_CARDS, B_POS)):
        q = prog(t, 4.8 + i * 0.16, 0.55)
        paste(c, spr, x, y + (1 - out_expo(q)) * 100 + ey, 0.85 + 0.15 * out_back(q) if q > 0 else 0,
              clamp(q * 3) * ea)

# ---------------------------------------------------------------- C: skills unlocked  8.0 - 10.4
C_HEAD = text_sprite("Skills unlocked", spartan(104), GOLD)
C_CHIPS = chip_row(CONFIG["skills"], y=650)

# skills style per level (levels.json: "outro_skills_style": "chips" | "tube")
C_TUBE = (TubeLine(CONFIG["skills"], y=620, t0=8.4, dur=1.25)
          if CONFIG.get("outro_skills_style") == "tube" else None)

def scene_c(c, t):
    if t < 7.9 or t > 10.7: return
    ey, ea = exit_ofs(t, 10.2)
    q = out_expo(prog(t, 8.05, 0.6))
    paste(c, C_HEAD, W / 2 + (1 - q) * 220, 470 + ey, 1, q * ea)
    if C_TUBE:
        C_TUBE.draw(c, t, alpha=ea, dy=ey)
        return
    for i, (spr, x, y) in enumerate(C_CHIPS):
        q = prog(t, 8.45 + i * 0.22, 0.5)
        paste(c, spr, x, y + ey, out_back(q) if q > 0 else 0, clamp(q * 3) * ea)

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

def scene_e(c, t):
    url = CONFIG["url"]
    n = int(len(url) * clamp(prog(t, 13.1, 0.75)))
    if n:
        spr = text_sprite(url[:n], URL_FONT, WHITE)
        paste(c, spr, W / 2 - URL_FONT.getlength(url) / 2 + spr.width / 2 - 8, 770)
    q = out_expo(prog(t, 13.8, 0.6))
    if q > 0:
        w = 520 * q
        ImageDraw.Draw(c).rounded_rectangle((W / 2 - w / 2, 830, W / 2 + w / 2, 836), radius=3, fill=GOLD)

SCENES = [logo, scene_a, scene_b, scene_c, scene_d, scene_e]

def frame(t):
    c = Image.new("RGBA", (W, H), BG + (255,))
    for s in SCENES:
        s(c, t)
    return c.convert("RGB")

def main():
    if "--still" in sys.argv:
        t = float(sys.argv[sys.argv.index("--still") + 1])
        frame(t).save(f"still_{t:g}.png"); return
    out = CONFIG["out"]
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3",
           "-pix_fmt", "yuv422p10le", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 60 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", out)

if __name__ == "__main__":
    main()
