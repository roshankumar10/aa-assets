"""Atlas Academy - 15s kinetic typography promo (style matched to Outro_v2).

Renders 1920x1080 @ 30fps frames with Pillow and pipes them into ffmpeg.
Usage:  python render.py            -> kinetic_v1.mp4
        python render.py --mov      -> kinetic_v1.mov (ProRes 422 HQ, no audio)
        python render.py --still 7  -> preview frame at t=7s (still_7.png)
"""
import math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1920, 1080, 30, 15.0
BG = (25, 33, 72)          # navy from Outro_v2
GOLD = (215, 167, 72)      # logo gold
WHITE = (255, 255, 255)
GREEN = (176, 248, 122)    # chip dot
CHIP_LINE = (200, 206, 230)

FONT_DIR = r"C:/Users/Jonathan/AppData/Local/Microsoft/Windows/Fonts/"
REF_FRAME = "ref13.png"

_font_cache = {}
def spartan(size):
    k = ("sp", size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(FONT_DIR + "LeagueSpartan-Bold.ttf", size)
    return _font_cache[k]

def dmsans(size, weight=400):
    k = ("dm", size, weight)
    if k not in _font_cache:
        f = ImageFont.truetype(FONT_DIR + "DMSans-VariableFont_opsz,wght.ttf", size)
        f.set_variation_by_axes([min(40, size), weight])
        _font_cache[k] = f
    return _font_cache[k]

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, start, dur): return clamp((t - start) / dur)
def out_expo(x): return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def out_cubic(x): return 1 - (1 - x) ** 3
def in_cubic(x): return x ** 3
def out_back(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

# ---------------------------------------------------------------- sprites
def text_sprite(text, font, color):
    l, t, r, b = font.getbbox(text)
    pad = 8
    asc, desc = font.getmetrics()
    img = Image.new("RGBA", (int(r - l) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad), text, font=font, fill=color)
    return img

def chip_sprite(label, w=440, h=86):
    s = 3  # supersample for smooth outline
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2 * s, 2 * s, (w - 2) * s, (h - 2) * s), radius=(h // 2 - 2) * s,
                        outline=CHIP_LINE, width=2 * s)
    cy, cx, r = h * s // 2, 46 * s, 11 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN)
    f = dmsans(34 * s, 450)
    tw = f.getlength(label)
    asc, desc = f.getmetrics()
    d.text(((w * s - tw) / 2 + 22 * s, cy - (asc + desc) / 2 + 2 * s), label, font=f, fill=WHITE)
    return img.resize((w, h), Image.LANCZOS)

def chip_row(labels, y, h=90, gap=40, max_w=1800, row_gap=24):
    """Chips for any number of skills: the classic equal 500 px pills when they fit, otherwise
    pills sized to their text, wrapping to two centred rows. Returns [(sprite, x, y)]."""
    f = dmsans(34, 450)
    need = [f.getlength(s) + 140 for s in labels]          # dot + padding either side
    if max(need) <= 500 and len(labels) * 500 + (len(labels) - 1) * gap <= max_w:
        widths = [500] * len(labels)
    else:
        widths = [int(max(300, n)) for n in need]
    rows = [list(range(len(labels)))]
    if sum(widths) + gap * (len(labels) - 1) > max_w:
        k = (len(labels) + 1) // 2
        rows = [rows[0][:k], rows[0][k:]]
    out = [None] * len(labels)
    for r, idx in enumerate(rows):
        ry = y + (r - (len(rows) - 1) / 2) * (h + row_gap)
        tot = sum(widths[i] for i in idx) + gap * (len(idx) - 1)
        x = W / 2 - tot / 2
        for i in idx:
            out[i] = (chip_sprite(labels[i], w=widths[i], h=h), x + widths[i] / 2, ry)
            x += widths[i] + gap
    return out

def logo_icon():
    """Key the gold cap+globe icon out of the reference outro frame."""
    a = np.array(Image.open(REF_FRAME).convert("RGB")).astype(float)
    crop = a[300:690, 535:990]
    dist = np.abs(crop - np.array(BG)).sum(2)
    full = np.abs(np.array(GOLD) - np.array(BG)).sum()
    alpha = np.clip(dist / full, 0, 1) * 255
    out = np.zeros(crop.shape[:2] + (4,), np.uint8)
    out[..., :3] = GOLD
    out[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(out, "RGBA")

# ---------------------------------------------------------------- compositing
def paste(canvas, spr, cx, cy, scale=1.0, alpha=1.0, reveal=1.0, rot=0.0):
    """Paste sprite centred at (cx, cy). reveal<1 masks from the bottom up (text rising out of a line)."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if alpha < 1:
        a = spr.getchannel("A").point(lambda v: int(v * alpha))
        spr = spr.copy(); spr.putalpha(a)
    x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
    if reveal < 1:
        hh = int(spr.height * clamp(reveal))
        if hh <= 0:
            return
        spr = spr.crop((0, 0, spr.width, hh))
    if x >= canvas.width or y >= canvas.height or x + spr.width <= 0 or y + spr.height <= 0:
        return
    canvas.alpha_composite(spr, (max(0, x), max(0, y)),
                           (max(0, -x), max(0, -y)))

class TubeLine:
    """Skills as stations on a tube-map line: the line draws left->right behind a little train,
    stations pop as it passes and their labels rise in underneath."""
    def __init__(self, skills, y, t0, dur, spacing=470, overhang=190):
        self.y, self.t0, self.dur = y, t0, dur
        n = len(skills)
        self.st = [W / 2 + (i - (n - 1) / 2) * spacing for i in range(n)]
        self.x0, self.x1 = self.st[0] - overhang, self.st[-1] + overhang
        self.labels = [text_sprite(sk, dmsans(46, 500), WHITE) for sk in skills]

    def _hit(self, x):
        """Time the head reaches x (inverse of the out_cubic draw)."""
        p = (x - self.x0) / (self.x1 - self.x0)
        return self.t0 + self.dur * (1 - (1 - p) ** (1 / 3))

    def draw(self, c, t, alpha=1.0, dy=0.0):
        if t < self.t0: return
        s, band = 2, 120                     # supersampled strip centred on the line
        strip = Image.new("RGBA", (W * s, band * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(strip)
        cy = band * s // 2
        head = self.x0 + (self.x1 - self.x0) * out_cubic(prog(t, self.t0, self.dur))
        if head > self.x0 + 1:
            d.rounded_rectangle((self.x0 * s, cy - 9 * s, head * s, cy + 9 * s), radius=9 * s, fill=GOLD)
        for x in self.st:
            if head < x: continue
            k = out_back(clamp((head - x) / 60), 2.6)
            r_out, r_in = 30 * k, 20 * k
            d.ellipse(((x - r_out) * s, cy - r_out * s, (x + r_out) * s, cy + r_out * s), fill=BG)
            d.ellipse(((x - r_in) * s, cy - r_in * s, (x + r_in) * s, cy + r_in * s), fill=WHITE)
        # train capsule rides the head, then pulls into the terminus and fades
        if t < self.t0 + self.dur + 0.4:
            ta = 1 - prog(t, self.t0 + self.dur, 0.4)
            tw, th = 54, 26
            d.rounded_rectangle(((head - tw) * s, cy - th / 2 * s, head * s, cy + th / 2 * s),
                                radius=th / 2 * s, fill=WHITE + (int(255 * ta),))
        paste(c, strip.resize((W, band), Image.LANCZOS), W / 2, self.y + dy, 1, alpha)
        for spr, x in zip(self.labels, self.st):
            q = out_expo(prog(t, self._hit(x) + 0.05, 0.5))
            paste(c, spr, x, self.y + dy + 72 + (1 - q) * 30, 1, q * alpha, reveal=0.1 + 0.9 * q)

def word_layout(words, font, gap):
    widths = [font.getlength(w) for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    xs, x = [], W / 2 - total / 2
    for w in widths:
        xs.append(x + w / 2); x += w + gap
    return xs

def exit_ofs(t, t_out, d=0.35, dist=-60):
    """Shared exit: slide up + fade."""
    p = in_cubic(prog(t, t_out, d))
    return dist * p, 1 - p

# ---------------------------------------------------------------- scenes
ICON = logo_icon()

# Scene 1: "Builders," / "not users."   0.0 - 3.3
S1_A = text_sprite("Builders,", spartan(230), GOLD)
S1_B = [text_sprite(w, spartan(150), WHITE) for w in ("not", "users.")]
S1_BX = word_layout(["not", "users."], spartan(150), 40)

def scene1(c, t):
    if t > 3.4: return
    ey, ea = exit_ofs(t, 3.0)
    p = prog(t, 0.15, 0.55)
    # slam in: big -> 1 with slight overshoot
    sc = 1 + 1.6 * (1 - out_expo(p))
    paste(c, S1_A, W / 2, 430 + ey, sc, clamp(p * 3) * ea)
    for i, (spr, x) in enumerate(zip(S1_B, S1_BX)):
        q = out_expo(prog(t, 0.9 + i * 0.22, 0.6))
        paste(c, spr, x, 640 + (1 - q) * 90 + ey, 1, q * ea, reveal=0.15 + 0.85 * q)
    # strike through "users."
    q = out_cubic(prog(t, 1.85, 0.45))
    if q > 0:
        sw = S1_B[1].width - 20
        x0 = S1_BX[1] - sw / 2
        d = ImageDraw.Draw(c)
        y = 640 + ey + 6
        if ea > 0.05:
            d.rectangle((x0, y - 7, x0 + sw * q, y + 7), fill=GOLD + (int(255 * ea),))

# Scene 2: "Learn to build" / "REAL THINGS" / "with real tools."   3.3 - 6.6
S2_A_WORDS = ["Learn", "to", "build"]
S2_A = [text_sprite(w, dmsans(96, 500), WHITE) for w in S2_A_WORDS]
S2_AX = word_layout(S2_A_WORDS, dmsans(96, 500), 26)
S2_B = [text_sprite(ch, spartan(250), GOLD) for ch in "real things"]
S2_BX = []
_x = W / 2 - spartan(250).getlength("real things") / 2
for ch in "real things":
    w = spartan(250).getlength(ch); S2_BX.append(_x + w / 2); _x += w
S2_C_WORDS = ["with", "real", "tools."]
S2_C = [text_sprite(w, dmsans(96, 500), GOLD if w == "real" else WHITE) for w in S2_C_WORDS]
S2_CX = word_layout(S2_C_WORDS, dmsans(96, 500), 26)

def scene2(c, t):
    if t < 3.25 or t > 6.8: return
    ey, ea = exit_ofs(t, 6.3)
    for i, (spr, x) in enumerate(zip(S2_A, S2_AX)):
        q = out_expo(prog(t, 3.35 + i * 0.12, 0.55))
        paste(c, spr, x, 330 + (1 - q) * 70 + ey, 1, q * ea, reveal=0.1 + 0.9 * q)
    for i, (spr, x) in enumerate(zip(S2_B, S2_BX)):
        if spr.width < 30: continue  # space
        q = prog(t, 3.9 + i * 0.045, 0.5)
        sc = out_back(q) if q > 0 else 0
        paste(c, spr, x, 540 + ey, sc, clamp(q * 4) * ea, rot=(1 - out_cubic(q)) * 25)
    for i, (spr, x) in enumerate(zip(S2_C, S2_CX)):
        q = out_expo(prog(t, 4.9 + i * 0.14, 0.55))
        paste(c, spr, x, 760 - (1 - q) * 70 + ey, 1, q * ea)

# Scene 3: "Skills you'll unlock" + chips   6.6 - 10.0
S3_H = text_sprite("Skills you'll unlock", spartan(110), GOLD)
S3_CHIPS = [chip_sprite(s) for s in ("Coding", "Robotics", "3D Modelling", "Animation")]
S3_POS = [(W / 2 - 245, 540), (W / 2 + 245, 540), (W / 2 - 245, 660), (W / 2 + 245, 660)]
S3_SUB = text_sprite("Real projects. Real tools.", dmsans(64, 400), WHITE)

def scene3(c, t):
    if t < 6.5 or t > 10.2: return
    ey, ea = exit_ofs(t, 9.7)
    q = out_expo(prog(t, 6.6, 0.6))
    paste(c, S3_H, W / 2 + (1 - q) * -220, 360 + ey, 1, q * ea)
    for i, (spr, (x, y)) in enumerate(zip(S3_CHIPS, S3_POS)):
        q = prog(t, 7.05 + i * 0.2, 0.5)
        paste(c, spr, x, y + ey, out_back(q) if q > 0 else 0, clamp(q * 3) * ea)
    q = out_expo(prog(t, 8.2, 0.6))
    paste(c, S3_SUB, W / 2, 820 + (1 - q) * 50 + ey, 1, q * ea, reveal=q)

# Scene 4: rapid-fire stack   10.0 - 12.4
S4_LINES = [("Small", "classes."), ("Industry", "instructors."), ("Showcase-ready", "projects.")]
S4_SPR = []
for a, b in S4_LINES:
    f = spartan(120)
    S4_SPR.append(((text_sprite(a, f, WHITE), text_sprite(b, f, GOLD)), word_layout([a, b], f, 34)))

def scene4(c, t):
    if t < 9.9 or t > 12.6: return
    ey, ea = exit_ofs(t, 12.1)
    for i, ((sa, sb), (xa, xb)) in enumerate(S4_SPR):
        st = 10.0 + i * 0.45
        y = 380 + i * 160
        q1 = out_expo(prog(t, st, 0.5))
        q2 = out_expo(prog(t, st + 0.12, 0.5))
        paste(c, sa, xa - (1 - q1) * 160, y + ey, 1, q1 * ea)
        paste(c, sb, xb + (1 - q2) * 160, y + ey, 1, q2 * ea)

# Scene 5: logo end card   12.4 - 15.0  (matches Outro_v2 layout)
LOGO_FONT = spartan(118)
S5_ATLAS = [text_sprite(ch, LOGO_FONT, GOLD) for ch in "Atlas"]
S5_ACAD = [text_sprite(ch, LOGO_FONT, GOLD) for ch in "Academy"]
S5_URL = "www.atlas-academy.ca"
URL_FONT = spartan(64)

def letters_x(word, x0):
    xs, x = [], x0
    for ch in word:
        w = LOGO_FONT.getlength(ch); xs.append(x + w / 2); x += w
    return xs

def scene5(c, t):
    if t < 12.3: return
    icx, icy = 765, 440
    q = prog(t, 12.4, 0.7)
    paste(c, ICON, icx, icy, 0.6 + 0.4 * out_back(q) if q > 0 else 0, clamp(q * 2.5),
          rot=(1 - out_cubic(q)) * -12)
    tx = 1015
    for row, (word, sprs, y) in enumerate((("Atlas", S5_ATLAS, 400), ("Academy", S5_ACAD, 520))):
        for i, (spr, x) in enumerate(zip(sprs, letters_x(word, tx))):
            q = out_expo(prog(t, 12.75 + row * 0.18 + i * 0.04, 0.5))
            paste(c, spr, x, y + (1 - q) * 60, 1, q, reveal=0.1 + 0.9 * q)
    # url types on
    n = int(len(S5_URL) * clamp(prog(t, 13.5, 0.75)))
    if n:
        spr = text_sprite(S5_URL[:n], URL_FONT, WHITE)
        full_w = URL_FONT.getlength(S5_URL)
        paste(c, spr, W / 2 - full_w / 2 + spr.width / 2 - 8, 770)
    # accent underline grows under url
    q = out_expo(prog(t, 14.2, 0.6))
    if q > 0:
        w = 520 * q
        ImageDraw.Draw(c).rounded_rectangle((W / 2 - w / 2, 830, W / 2 + w / 2, 836), radius=3, fill=GOLD)

SCENES = [scene1, scene2, scene3, scene4, scene5]

def frame(t):
    c = Image.new("RGBA", (W, H), BG + (255,))
    for s in SCENES:
        s(c, t)
    return c.convert("RGB")

def main():
    if "--still" in sys.argv:
        t = float(sys.argv[sys.argv.index("--still") + 1])
        frame(t).save(f"still_{t:g}.png"); return
    src = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if "--mov" in sys.argv:  # ProRes 422 HQ, same family as the AME outro exports
        out = "kinetic_v1.mov"
        cmd = src + ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", out]
    else:
        out = "kinetic_v1.mp4"
        cmd = src + ["-c:v", "libx264", "-preset", "slow", "-crf", "16",
                     "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 60 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", out)

if __name__ == "__main__":
    main()
