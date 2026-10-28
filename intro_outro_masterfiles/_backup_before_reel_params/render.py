"""Atlas Academy - 15s kinetic typography promo (style matched to Outro_v2).

Renders 1920x1080 @ 30fps frames with Pillow and pipes them into ffmpeg.
Usage:  python render.py            -> kinetic_v1.mp4
        python render.py --mov      -> kinetic_v1.mov (ProRes 422 HQ, no audio)
        python render.py --still 7  -> preview frame at t=7s (still_7.png)
"""
import math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
        spacing = min(spacing, 1500 / max(n - 1, 1))       # 5+ stations still fit on screen
        self.st = [W / 2 + (i - (n - 1) / 2) * spacing for i in range(n)]
        self.x0, self.x1 = self.st[0] - overhang, self.st[-1] + overhang
        f = dmsans(46 if n <= 4 else 38, 500)
        self.labels = [lines_sprite(wrap(sk, f, spacing - 40), f, WHITE) for sk in skills]
        one_line = text_sprite("A", f, WHITE).height
        self.label_dy = [72 + (l.height - one_line) / 2 for l in self.labels]   # wrapped labels hang down

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
        for spr, x, ly in zip(self.labels, self.st, self.label_dy):
            q = out_expo(prog(t, self._hit(x) + 0.05, 0.5))
            paste(c, spr, x, self.y + dy + ly + (1 - q) * 30, 1, q * alpha, reveal=0.1 + 0.9 * q)

class Timeline:
    """Lets each section run longer or shorter than designed without re-timing its animations.
    Real time maps to the time the scenes were designed for: extra seconds become a pause at the
    section's hold point (everything on screen, nothing moving); fewer seconds cut into that pause,
    up to max_cut. sections: [(name, start, end, hold, max_cut)] in design seconds."""
    def __init__(self, sections, durations=None, label=""):
        durations = durations or {}
        names = [s[0] for s in sections]
        unknown = sorted(set(durations) - set(names))
        if unknown:
            print(f"warning: unknown {label} section(s) {unknown} - use: {', '.join(names)}")
        self.pieces, self.lengths, real = [], {}, 0.0    # pieces: (real_start, real_end, design_start, rate)

        def add(length, design_start, rate):
            nonlocal real
            if length > 1e-9:
                self.pieces.append((real, real + length, design_start, rate))
                real += length

        for name, s, e, hold, max_cut in sections:
            extra = float(durations.get(name, e - s)) - (e - s)
            if extra < -max_cut - 1e-9:
                print(f"warning: {label} '{name}' can't be shorter than {e - s - max_cut:.2f}s "
                      f"(animations need the time) - using that")
                extra = -max_cut
            add(hold - s, s, 1)
            if extra >= 0:
                add(extra, hold, 0)                        # pause, then the rest as designed
                add(e - hold, hold, 1)
            else:
                add(e - hold + extra, hold - extra, 1)     # skip part of the pause
            self.lengths[name] = round(e - s + extra, 2)
        self.total = real

    def warp(self, t):
        for rs, re_, ds, rate in self.pieces:
            if t < re_:
                return ds + max(0.0, t - rs) * rate
        rs, re_, ds, rate = self.pieces[-1]
        return ds + (re_ - rs) * rate

    def describe(self):
        return ", ".join(f"{k} {v:g}s" for k, v in self.lengths.items()) + f"  (total {self.total:.2f}s)"

_REAL_T = [None]
def set_real_t(t):
    """Record the real (output) time of the frame being drawn - scene time stands still during a
    Timeline hold, this doesn't. Returns t so it can wrap the warp call."""
    _REAL_T[0] = t
    return t

def real_t(default):
    return default if _REAL_T[0] is None else _REAL_T[0]

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

# ---------------------------------------------------------------- list styles (skills / topics)
# Every style is built by item_block() and drawn with .draw(canvas, t, alpha, dy), so the intro
# and outro scenes can swap between them from levels.json without knowing how each one looks.
STYLES = ("chips", "tube", "list", "checklist", "numbered", "inline", "columns", "handwritten",
          "circuit", "painted", "code")

def wrap(text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= maxw or not cur: cur = trial
        else: lines.append(cur); cur = w
    return lines + [cur]

def lines_sprite(lines, font, color, line_h=None):
    """Centred multi-line text as one sprite."""
    sprs = [text_sprite(l, font, color) for l in lines]
    lh = line_h or int(font.size * 1.15)
    img = Image.new("RGBA", (max(s.width for s in sprs), sprs[0].height + lh * (len(sprs) - 1)), (0, 0, 0, 0))
    for i, s in enumerate(sprs):
        img.alpha_composite(s, ((img.width - s.width) // 2, i * lh))
    return img

def glyph_mid(font, sample="x"):
    """Offset from a text_sprite's centre to the middle of `sample` - for lining markers up with text."""
    _, top, _, bot = font.getbbox(sample)
    asc, desc = font.getmetrics()
    return 8 + (top + bot) / 2 - (asc + desc + 16) / 2

def dot_sprite(d=14, color=GOLD):
    s = 4
    img = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, d * s - 1, d * s - 1), fill=color)
    return img.resize((d, d), Image.LANCZOS)

def tick_sprite(q, size=40, color=GOLD, width=7):
    """Check mark stroked on as q goes 0 -> 1 (short leg first, like the outro badge)."""
    s = 3
    img = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    p0, p1, p2 = [(x * size * s, y * size * s) for x, y in ((0.12, 0.52), (0.4, 0.8), (0.9, 0.2))]
    a, b = clamp(q / 0.4), clamp((q - 0.4) / 0.6)
    path = [p0, (p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a)]
    if b > 0:
        path.append((p1[0] + (p2[0] - p1[0]) * b, p1[1] + (p2[1] - p1[1]) * b))
    if q > 0:
        ImageDraw.Draw(img).line(path, fill=color, width=width * s, joint="curve")
    return img.resize((size, size), Image.LANCZOS)

class ChipRow:
    """Outlined pills with a green dot that pop in one by one (the original look).
    notes = {chip label: text}: a small handwritten note under that chip with a pen arrow up to it,
    written just after the chip pops in. Keep them short (~25 characters) - they sit below the row."""
    def __init__(self, labels, y, t0, stagger=0.22, notes=None, note_dur=0.6):
        self.items, self.t0, self.stagger = chip_row(labels, y=y), t0, stagger
        self.asides = chip_asides(labels, [(x, yy, spr.width, spr.height) for spr, x, yy in self.items],
                                  [t0 + i * stagger for i in range(len(labels))], notes, note_dur)

    def draw(self, c, t, alpha=1.0, dy=0.0):
        for i, (spr, x, y) in enumerate(self.items):
            q = prog(t, self.t0 + i * self.stagger, 0.5)
            paste(c, spr, x, y + dy, out_back(q) if q > 0 else 0, clamp(q * 3) * alpha)
        draw_asides(c, t, self.asides, alpha, dy)

def chip_noted(notes):
    return {k.strip().lower(): v.strip() for k, v in (notes or {}).items() if v and v.strip()}

def chip_asides(labels, boxes, starts, notes, note_dur):
    """Handwritten notes under the chips they name. boxes = [(cx, cy, w, h)] per chip, starts = the
    time each chip appears; the note is written just after."""
    notes = chip_noted(notes)
    bottom = max(y + h / 2 for _, y, _, h in boxes)
    out = []
    for i, (label, (x, y, w, h)) in enumerate(zip(labels, boxes)):
        text = notes.get(label.strip().lower())
        if not text: continue
        note = HandNote(text, 0, 0, starts[i] + 0.35, size=46, max_w=max(w + 40, 300),
                        max_lines=1, tilt=4 if len(out) % 2 == 0 else -3, max_dur=note_dur)
        note.cx, note.cy = x + 25, bottom + 42 + note.h / 2
        out.append((note, ((x - 20, bottom + 46), (x + 2, y + h / 2 + 8)), 40 + i))
    return out

def draw_asides(c, t, asides, alpha, dy):
    for note, ((ax, ay), (bx, by)), seed in asides:
        note.draw(c, t, alpha, dy)
        hand_arrow(c, (ax, ay + dy), (bx, by + dy), out_cubic(prog(t, note.end, 0.35)),
                   seed=seed, bow=18, alpha=alpha, width=4)

class ListBlock:
    """No boxes - a clean typographic list. marker: 'bar' (gold dash grows), 'check' (tick strokes on)
    or 'number' (gold 01, 02 ...). Splits into side-by-side columns when the items don't fit max_h."""
    LINE, MARK_W, COL_GAP = 76, 70, 110

    def __init__(self, labels, y, max_h, t0, stagger, marker="bar", font=None):
        n = len(labels)
        self.font = font or dmsans(48 if n <= 4 else 44, 500)
        self.write = [min(0.55, 0.035 * len(s)) for s in labels]        # 'hand': pen time per item
        self.num_font = spartan(42)
        rows = max(1, min(n, int(max_h // self.LINE)))
        cols = math.ceil(n / rows)
        rows = math.ceil(n / cols)                       # balance the columns
        self.sprs = [text_sprite(s, self.font, WHITE) for s in labels]
        self.nums = [text_sprite(f"{i + 1:02d}", self.num_font, GOLD) for i in range(n)]
        self.mid = glyph_mid(self.font)
        self.num_mid = glyph_mid(self.num_font, "0")
        col_w = [max(s.width for s in self.sprs[k * rows:(k + 1) * rows]) + self.MARK_W for k in range(cols)]
        x = W / 2 - (sum(col_w) + self.COL_GAP * (cols - 1)) / 2
        self.pos = []
        for k in range(cols):
            for r in range(min(rows, n - k * rows)):
                self.pos.append((x, y + (r - (rows - 1) / 2) * self.LINE))
            x += col_w[k] + self.COL_GAP
        self.t0, self.stagger, self.marker = t0, stagger, marker

    def draw(self, c, t, alpha=1.0, dy=0.0):
        for i, (spr, (x, y)) in enumerate(zip(self.sprs, self.pos)):
            ti = self.t0 + i * self.stagger
            ym = y + dy + self.mid                       # middle of the lowercase letters
            if self.marker == "hand":                    # pen dash, then the words write on
                dash = wobble_pts((x + 6, ym + 2), (x + 40, ym - 1), seed=i * 13 + 3, amp=1.5, n=8)
                draw_stroke(c, dash, prog(t, ti, 0.2), GOLD, 5, alpha)
                p = prog(t, ti + 0.15, self.write[i])
                if p > 0:
                    vis = spr if p >= 1 else spr.crop((0, 0, int(8 + (spr.width - 16) * p), spr.height))
                    paste(c, vis, x + self.MARK_W - 8 + vis.width / 2, y + dy, 1, alpha)
                continue
            q = prog(t, ti, 0.4)
            if q > 0 and self.marker == "bar":
                w = max(1, int(30 * out_cubic(q)))
                paste(c, Image.new("RGBA", (w, 6), GOLD + (255,)), x + 8 + w / 2, ym, 1, alpha)
            elif q > 0 and self.marker == "check":
                paste(c, tick_sprite(q), x + 22, ym, 1, alpha)
            elif q > 0:
                qq = out_expo(q)
                num = self.nums[i]
                paste(c, num, x + num.width / 2 - 8, ym - self.num_mid + (1 - qq) * 20, 1, qq * alpha,
                      reveal=0.1 + 0.9 * qq)
            q = out_expo(prog(t, ti + 0.08, 0.5))
            paste(c, spr, x + self.MARK_W + spr.width / 2 - 8, y + dy + (1 - q) * 30, 1, q * alpha,
                  reveal=0.1 + 0.9 * q)

class InlineRow:
    """Items flow like a sentence separated by gold dots; wraps to extra lines when too wide."""
    def __init__(self, labels, y, t0, stagger, max_w=1640, sep=64):
        n = len(labels)
        f = dmsans(56 if n <= 4 else 50, 500)
        widths = [f.getlength(s) for s in labels]
        lines, cur = [[]], 0.0
        for i, w in enumerate(widths):
            if lines[-1] and cur + sep + w > max_w:
                lines.append([]); cur = 0.0
            cur += (sep if lines[-1] else 0) + w
            lines[-1].append(i)
        lh, mid = f.size * 1.7, glyph_mid(f)
        self.items, self.dots, self.dot = [], {}, dot_sprite()
        for li, idx in enumerate(lines):
            x = W / 2 - (sum(widths[i] for i in idx) + sep * (len(idx) - 1)) / 2
            cy = y + (li - (len(lines) - 1) / 2) * lh
            for k, i in enumerate(idx):
                if k:
                    self.dots[i] = (x + sep / 2, cy + mid); x += sep
                self.items.append((text_sprite(labels[i], f, WHITE), x + widths[i] / 2, cy))
                x += widths[i]
        self.t0, self.stagger = t0, stagger

    def draw(self, c, t, alpha=1.0, dy=0.0):
        for i, (spr, x, y) in enumerate(self.items):
            ti = self.t0 + i * self.stagger
            if i in self.dots:
                q = prog(t, ti, 0.35)
                dx, dy0 = self.dots[i]
                paste(c, self.dot, dx, dy0 + dy, out_back(q, 3) if q > 0 else 0, alpha)
            q = out_expo(prog(t, ti + 0.05, 0.5))
            paste(c, spr, x, y + dy + (1 - q) * 30, 1, q * alpha, reveal=0.1 + 0.9 * q)

class Columns:
    """Editorial columns: a big gold number over each item, thin gold rules drawing down between them."""
    def __init__(self, labels, y, t0, stagger, max_w=1720):
        n = len(labels)
        self.cw = min(440, max_w / n)
        f = dmsans(42 if n <= 4 else 36, 500)
        self.nums = [text_sprite(f"{i + 1:02d}", spartan(60), GOLD) for i in range(n)]
        self.labs = [lines_sprite(wrap(s, f, self.cw - 50), f, WHITE) for s in labels]
        self.num_h = self.nums[0].height
        self.h = self.num_h + max(l.height for l in self.labs)
        self.top = y - self.h / 2
        self.xs = [W / 2 + (i - (n - 1) / 2) * self.cw for i in range(n)]
        self.rule = Image.new("RGBA", (2, int(self.h)), GOLD + (140,))
        self.t0, self.stagger = t0, stagger

    def draw(self, c, t, alpha=1.0, dy=0.0):
        for i, x in enumerate(self.xs):
            ti = self.t0 + i * self.stagger
            if i:
                q = out_cubic(prog(t, ti - 0.05, 0.5))
                paste(c, self.rule, x - self.cw / 2, self.top + self.h / 2 + dy, 1, alpha, reveal=q)
            q = prog(t, ti, 0.5)
            paste(c, self.nums[i], x, self.top + self.num_h / 2 + dy, out_back(q) if q > 0 else 0,
                  clamp(q * 3) * alpha)
            q = out_expo(prog(t, ti + 0.1, 0.5))
            lab = self.labs[i]
            paste(c, lab, x, self.top + self.num_h + lab.height / 2 + dy + (1 - q) * 30, 1, q * alpha,
                  reveal=0.1 + 0.9 * q)

def glow_sprite(r, halo, core=GREEN, glow=GREEN, strength=120):
    """Solid dot with a soft blurred halo (lit LED, signal pulse)."""
    size = halo * 2 + 24
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    m = size / 2
    ImageDraw.Draw(img).ellipse((m - halo * 0.6, m - halo * 0.6, m + halo * 0.6, m + halo * 0.6),
                                fill=glow + (strength,))
    img = img.filter(ImageFilter.GaussianBlur(halo * 0.35))
    dot = dot_sprite(r * 2, core)
    img.alpha_composite(dot, (int(m - r), int(m - r)))
    return img

def _cum_len(pts):
    cum = [0.0]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(bx - ax, by - ay))
    return cum

def _cut(pts, cum, L):
    """The first L px of a polyline (and the point the cut ends on)."""
    if L >= cum[-1]: return list(pts), pts[-1]
    for i in range(1, len(pts)):
        if cum[i] >= L:
            (ax, ay), (bx, by) = pts[i - 1], pts[i]
            f = (L - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-9)
            head = (ax + (bx - ax) * f, ay + (by - ay) * f)
            return list(pts[:i]) + [head], head
    return list(pts), pts[-1]

class CircuitRow:
    """Chips as components on a circuit board: a gold trace draws left -> right behind a glowing
    signal pulse (45-degree jogs between parts, vias at both ends). Each chip is a little IC with
    pins that pops in as the pulse reaches it; its LED lights and a pair of leads fan out to vias.
    Wraps to two traces when one doesn't fit. notes work like chips (written under the bottom row).
    region = (top, bottom) the block may use: if two traces won't fit in it, it stays one trace and
    the whole block is scaled down to fit there instead (the intro title card)."""
    H, PIN, GAP, LEAD, LED_X = 86, 11, 120, 150, 44
    FILL = (33, 43, 92)

    def __init__(self, labels, y, t0, span, notes=None, note_dur=0.6, max_w=W - 80, region=None, t_out=None):
        self.t_out = t_out                                       # own exit: chips pop out, trace retracts
        f = dmsans(34, 450)
        n = len(labels)
        widths = [int(max(280, f.getlength(s) + 124)) for s in labels]
        row_w = lambda idx: sum(widths[i] for i in idx) + self.GAP * (len(idx) - 1)
        rows = [list(range(n))]
        if n > 1 and row_w(rows[0]) + 2 * 90 > max_w:          # each trace needs ~90 px of lead
            k = (n + 1) // 2
            rows = [rows[0][:k], rows[0][k:]]
        noted = chip_noted(notes)
        pitch = self.H + 2 * self.PIN + 58
        self.cw, self.compact = W, False                         # cw = width the layout is centred in
        if region and len(rows) > 1 and pitch + self.H + 2 * self.PIN + 170 > region[1] - region[0]:
            rows, self.compact = [list(range(n))], True
            self.cw = int(max(W, row_w(rows[0]) + 2 * self.LEAD + 80))
        last_noted = any(labels[i].strip().lower() in noted for i in rows[-1])
        rdur = span if len(rows) == 1 else span * 0.72
        self.rows, self.chips = [], [None] * n
        for r, idx in enumerate(rows):
            ry = y + (r - (len(rows) - 1) / 2) * pitch
            tot = row_w(idx)
            lead = min(self.LEAD, (self.cw - tot) / 2 - 40)
            x = self.cw / 2 - tot / 2
            pts = [(x - lead, ry + 38), (x - 60, ry + 38), (x - 22, ry)]
            at = []                                              # index of each chip's left edge in pts
            for j, i in enumerate(idx):
                left, right = x, x + widths[i]
                at.append(len(pts))
                pts += [(left, ry), (right, ry)]
                if j < len(idx) - 1:                             # jog up or down between parts
                    d = 26 if (j + r) % 2 == 0 else -26
                    pts += [(right + 20, ry), (right + 46, ry + d), (right + 74, ry + d), (right + 100, ry)]
                x = right + self.GAP
            right = x - self.GAP
            pts += [(right + 22, ry), (right + 60, ry - 38), (right + lead, ry - 38)]
            cum = _cum_len(pts)
            rt0 = t0 + r * span * 0.28
            hit = lambda L, rt0=rt0, tot=cum[-1]: rt0 + rdur * (1 - (1 - L / tot) ** (1 / 3))
            self.rows.append(dict(pts=pts, cum=cum, t0=rt0, dur=rdur, end=hit(cum[-1])))
            for j, i in enumerate(idx):
                # leads point away from the heading / the other trace / the notes
                if len(rows) == 1:
                    side = -1 if last_noted or j % 2 == 0 else 1
                elif r < len(rows) - 1:
                    side = 1
                else:
                    side = 0 if last_noted else 1
                w, cx = widths[i], pts[at[j]][0] + widths[i] / 2
                y0 = ry + side * (self.H / 2 + self.PIN)
                leads = [] if not side else [
                    [(lx, y0), (lx, y0 + side * 14), (lx + dx * 20, y0 + side * 34)]
                    for lx, dx in ((cx - w * 0.28, -1), (cx + w * 0.28, 1))]
                self.chips[i] = dict(spr=self.chip_sprite(labels[i], w), x=cx, y=ry, w=w,
                                     t=hit(cum[at[j]]), led=hit(cum[at[j]] + self.LED_X), leads=leads)
        for i, ch in enumerate(self.chips):                      # exit ripples left -> right
            ch["out"] = t_out + i * 0.03 if t_out is not None else math.inf
        ys = [c["y"] for c in self.chips]
        self.band_top = min(ys) - self.H / 2 - self.PIN - 60
        self.band_h = int(max(ys) - min(ys) + self.H + 2 * self.PIN + 120)
        self.led = glow_sprite(11, 30)
        self.pulse = glow_sprite(7, 28, core=(255, 248, 225), glow=GOLD, strength=200)
        self.asides = chip_asides(labels, [(c["x"], c["y"], c["w"], self.H + 2 * self.PIN) for c in self.chips],
                                  [c["t"] for c in self.chips], notes, note_dur)
        if self.compact:                                         # scale the drawn block into the region
            edge = [y for c in self.chips for y in (c["y"] - self.H / 2 - self.PIN, c["y"] + self.H / 2 + self.PIN)]
            edge += [p[1] for c in self.chips for lead in c["leads"] for p in lead]
            edge += [note.cy + note.h / 2 for note, _, _ in self.asides]
            self.box = (min(edge) - 14, max(edge) + 14)
            xs = [p[0] for row in self.rows for p in (row["pts"][0], row["pts"][-1])]
            self.k = min(1.0, (W - 60) / (max(xs) - min(xs) + 30),
                         (region[1] - region[0]) / (self.box[1] - self.box[0]))
            self.target = (region[0] + region[1]) / 2

    def chip_sprite(self, label, w):
        s, P, H = 3, self.PIN, self.H
        img = Image.new("RGBA", (w * s, (H + 2 * P) * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        npins = max(2, int((w - 60) / 34))
        for k in range(npins):                                   # IC legs along top and bottom
            px = 30 + (w - 60) * k / (npins - 1)
            for y0, y1 in ((1, P + 2), (P + H - 2, H + 2 * P - 1)):
                d.rectangle(((px - 4) * s, y0 * s, (px + 4) * s, y1 * s), fill=CHIP_LINE + (170,))
        d.rounded_rectangle((2 * s, P * s, (w - 2) * s, (P + H) * s), radius=10 * s,
                            fill=self.FILL + (255,), outline=CHIP_LINE, width=2 * s)
        cy, lx = (P + H / 2) * s, self.LED_X * s
        d.ellipse((lx - 14 * s, cy - 14 * s, lx + 14 * s, cy + 14 * s), outline=CHIP_LINE + (90,), width=2 * s)
        d.ellipse((lx - 9 * s, cy - 9 * s, lx + 9 * s, cy + 9 * s), fill=(58, 84, 74))      # LED, off
        ft = dmsans(34 * s, 450)
        asc, desc = ft.getmetrics()
        d.text(((w * s - ft.getlength(label)) / 2 + 22 * s, cy - (asc + desc) / 2 + 2 * s), label,
               font=ft, fill=WHITE)
        return img.resize((w, H + 2 * P), Image.LANCZOS)

    def draw(self, c, t, alpha=1.0, dy=0.0):
        if t < self.rows[0]["t0"]: return
        if not self.compact:
            return self._draw(c, t, alpha, dy)
        top, bot = self.box
        layer = Image.new("RGBA", (self.cw, int(bot - top)), (0, 0, 0, 0))
        self._draw(layer, t, 1.0, -top)
        paste(c, layer, W / 2, self.target + dy, self.k, alpha)

    def _draw(self, c, t, alpha, dy):
        s, top = 2, self.band_top
        strip = Image.new("RGBA", (self.cw * s, self.band_h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(strip)
        sp = lambda pts: [(x * s, (y - top) * s) for x, y in pts]

        def via(p, r, q=1.0):
            r *= out_back(q, 2.6)
            if r <= 0.5: return
            x, y = p[0] * s, (p[1] - top) * s
            d.ellipse((x - r * s, y - r * s, x + r * s, y + r * s), fill=BG, outline=GOLD, width=3 * s)

        out = self.t_out is not None and t >= self.t_out
        heads = []
        for row in self.rows:
            if t < row["t0"]: continue
            total = row["cum"][-1]
            L = total * out_cubic(prog(t, row["t0"], row["dur"]))
            # exit: the tail chases the head off the end of the trace, the pulse riding the tail
            Ls = total * in_cubic(prog(t, self.t_out, 0.3)) if out else 0.0
            part, head = _cut(row["pts"], row["cum"], L)
            if Ls > 0:
                pre, tail = _cut(row["pts"], row["cum"], Ls)
                part = [tail] + list(row["pts"][len(pre) - 1:]) if Ls < total else []
                heads.append((tail, 1 - prog(t, self.t_out + 0.25, 0.06)))
            if len(part) > 1:
                d.line(sp(part), fill=GOLD, width=5 * s, joint="curve")
            vq = 1 - prog(t, self.t_out, 0.12) if out else 1.0
            via(row["pts"][0], 10, min(prog(t, row["t0"], 0.25), vq))
            if t >= row["end"]:
                eq = 1 - prog(t, self.t_out + 0.24, 0.08) if out else 1.0
                via(row["pts"][-1], 10, min(prog(t, row["end"], 0.25), eq))
            if not out:
                heads.append((head, 1 - prog(t, row["end"], 0.3)))
        for ch in self.chips:
            q = out_cubic(prog(t, ch["t"] + 0.2, 0.3))
            qo = prog(t, ch["out"], 0.15) if out else 0.0       # leads pull back into the chip
            for lead in ch["leads"]:
                if q * (1 - qo) <= 0: break
                cum = _cum_len(lead)
                part, _ = _cut(lead, cum, cum[-1] * q * (1 - qo))
                d.line(sp(part), fill=GOLD, width=4 * s, joint="curve")
                if q >= 1 and qo == 0:
                    via(lead[-1], 6, prog(t, ch["t"] + 0.5, 0.2))
        paste(c, strip.resize((self.cw, self.band_h), Image.LANCZOS), self.cw / 2, top + self.band_h / 2 + dy,
              1, alpha)
        for i, ch in enumerate(self.chips):
            sign = 1 if i % 2 else -1
            q = prog(t, ch["t"], 0.55)
            if q <= 0: continue
            # in: springs up from below with a twist and a big overshoot
            k = out_back(q, 3.2)
            rot = sign * 14 * (1 - out_cubic(q))
            rise = 46 * (1 - out_expo(q))
            a = clamp(q * 4)
            qo = prog(t, ch["out"], 0.24) if out else 0.0
            if qo > 0:                                           # out: swells, then twists and shrinks away
                k = 1 + 0.2 * out_cubic(clamp(qo / 0.3)) if qo < 0.3 else 1.2 * (1 - in_cubic((qo - 0.3) / 0.7))
                rot = -sign * 18 * in_cubic(qo)
                rise = -24 * in_cubic(qo)
                a = clamp((1 - qo) * 2.5)
            cy = ch["y"] + rise + dy
            paste(c, ch["spr"], ch["x"], cy, k, a * alpha, rot=rot)
            if 0 < t - ch["t"] - 0.2 < 0.4:                      # ripple as it lands
                self._ring(c, ch["x"], ch["y"] + dy, ch["w"], prog(t, ch["t"] + 0.2, 0.4), alpha, 34)
            if out and 0 < t - ch["out"] - 0.04 < 0.22:          # quick burst as it pops
                self._ring(c, ch["x"], ch["y"] + dy, ch["w"], prog(t, ch["out"] + 0.04, 0.22), alpha, 20)
            lq = prog(t, ch["led"] + 0.05, 0.18) * (1 - prog(t, ch["out"], 0.08) if out else 1)
            if lq > 0:                                           # LED switches on with a little flash
                ox, r = (self.LED_X - ch["w"] / 2) * k, math.radians(rot)
                paste(c, self.led, ch["x"] + ox * math.cos(r), cy - ox * math.sin(r),
                      (1 + 0.35 * (1 - lq)) * min(k, 1.2), lq * alpha)
        for (hx, hy), a in heads:
            paste(c, self.pulse, hx, hy + dy, 1, a * alpha)
        draw_asides(c, t, self.asides, alpha * (1 - prog(t, self.t_out, 0.15) if out else 1), dy)

    def _ring(self, c, x, y, w, q, alpha, grow):
        """Outline that ripples out from a chip and fades."""
        s, pad = 2, 6 + grow * out_cubic(q)
        bw, bh = w + 2 * pad, self.H + 2 * pad
        img = Image.new("RGBA", (int(bw + 8) * s, int(bh + 8) * s), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle((4 * s, 4 * s, (bw + 4) * s, (bh + 4) * s), radius=(10 + pad) * s,
                                              outline=GOLD + (int(220 * (1 - q) ** 2),), width=3 * s)
        paste(c, img.resize((img.width // s, img.height // s), Image.LANCZOS), x, y, 1, alpha)

def _smooth_noise(rng, n, k):
    """1-D noise with features about k px wide, unit std."""
    k = max(1, int(k))
    kern = np.hanning(2 * k + 1)
    out = np.convolve(rng.standard_normal(n + 2 * k), kern / kern.sum(), "valid")[:n]
    return out / (out.std() + 1e-9)

def brush_alpha(w, h, seed, text_end):
    """Alpha (0-255) of a dry-brush paint swipe: round loaded start, ragged edges, faint bristle
    lines, breaking into streaks only past text_end so nothing on top of it loses its backing."""
    rng = np.random.default_rng(seed)
    x = np.arange(w)
    u = x / (w - 1)
    half = (h - 12) / 2 * 0.88
    cy = h / 2 + rng.choice([-1, 1]) * 3 * np.sin(np.pi * u + rng.uniform(-0.5, 0.5)) + _smooth_noise(rng, w, 40)
    th = half * (1 + 0.05 * _smooth_noise(rng, w, 60))
    th *= np.sqrt(np.clip(1 - (1 - np.clip(x / (half * 1.1), 0, 1)) ** 2, 0, 1))      # round start
    dry = np.clip((x - text_end) / max(w - text_end, 1), 0, 1)
    th *= 1 - 0.5 * dry ** 1.5                                                        # thins as it runs out
    top = cy - th + 1.8 * _smooth_noise(rng, w, 16) + 0.6 * _smooth_noise(rng, w, 3)
    bot = cy + th + 1.8 * _smooth_noise(rng, w, 16) + 0.6 * _smooth_noise(rng, w, 3)
    Y = np.arange(h)[:, None]
    a = np.clip(Y - top + 0.5, 0, 1) * np.clip(bot - Y + 0.5, 0, 1)
    st = _smooth_noise(rng, h, 1) + 0.8 * _smooth_noise(rng, h, 4)                  # fine + broad bristles
    st = (st - st.min()) / (st.max() - st.min() + 1e-9)                              # bristle density per row
    a *= np.clip(1 - dry ** 1.2 * (1.7 * (1 - st[:, None]) - 0.15), 0, 1)
    a *= 0.86 + 0.14 * st[:, None]
    tail = w - text_end                                                               # bristles run out
    a *= np.clip((w - 6 - x - (1 - st[:, None]) * tail * 0.55 - rng.uniform(0, tail * 0.15, (h, 1))) / 14, 0, 1)
    return (a * 255).astype(np.float32)

class PaintRow:
    """Each item gets a gold paint stroke swiped on behind it, then the words (navy, bold) rise in
    on top. Flows into centred rows; each stroke sits at its own slight tilt."""
    GAP, PAD, TAIL, FEATHER = 56, 46, 84, 40

    def __init__(self, labels, y, max_h, t0, stagger, max_w=1680):
        n = len(labels)
        size = 52 if n <= 4 else 48
        while True:
            f = dmsans(size, 700)
            sh = int(size * 1.95)
            lh = sh + 26
            widths = [int(f.getlength(s)) + self.PAD + self.TAIL for s in labels]
            lines, cur = [[]], 0
            for i, w in enumerate(widths):
                if lines[-1] and cur + self.GAP + w > max_w:
                    lines.append([]); cur = 0
                cur += (self.GAP if lines[-1] else 0) + w
                lines[-1].append(i)
            if len(lines) * lh <= max_h or size <= 36: break
            size -= 4
        mid = glyph_mid(f, "H")
        self.items = [None] * n
        for li, idx in enumerate(lines):
            x = W / 2 - (sum(widths[i] for i in idx) + self.GAP * (len(idx) - 1)) / 2
            cy = y + (li - (len(lines) - 1) / 2) * lh
            for i in idx:
                w = widths[i]
                txt = text_sprite(labels[i], f, BG)
                rgb = np.zeros((sh, w, 4), np.uint8)
                rgb[..., :3] = GOLD
                tilt = (1 if i % 2 else -1) * random.Random(i * 7 + 3).uniform(0.8, 2.2)
                # text sits in the loaded part of the stroke; the dry tail trails off to the right
                tx = x + self.PAD + (txt.width - 16) / 2
                self.items[i] = dict(a=brush_alpha(w, sh, 100 + i * 17, self.PAD + txt.width - 16), rgb=rgb,
                                     txt=txt, x=x + w / 2, tx=tx, y=cy, ty=cy - mid, tilt=tilt)
                x += w + self.GAP
        self.t0, self.stagger = t0, stagger

    def draw(self, c, t, alpha=1.0, dy=0.0):
        for i, it in enumerate(self.items):
            ti = self.t0 + i * self.stagger
            q = out_cubic(prog(t, ti, 0.4))
            if q <= 0: continue
            w = it["a"].shape[1]
            if q < 1:                                            # swipe on left -> right, soft leading edge
                mask = np.clip((q * (w + self.FEATHER) - np.arange(w)) / self.FEATHER, 0, 1)
                it["rgb"][..., 3] = (it["a"] * mask).astype(np.uint8)
            else:
                it["rgb"][..., 3] = it["a"].astype(np.uint8)
            rot = it["tilt"]
            paste(c, Image.fromarray(it["rgb"], "RGBA"), it["x"], it["y"] + dy, 1, alpha, rot=rot)
            # keep the text on the stroke's tilt: rotate its offset from the stroke centre too
            ox = it["tx"] - it["x"]
            a = math.radians(rot)
            tq = out_expo(prog(t, ti + 0.18, 0.45))
            paste(c, it["txt"], it["x"] + ox * math.cos(a), it["ty"] - ox * math.sin(a) + (1 - tq) * 24 + dy,
                  1, tq * alpha, rot=rot)

def mono(size):
    k = ("mono", size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype("C:/Windows/Fonts/CascadiaMono.ttf", size)
    return _font_cache[k]

class CodeBlock:
    """The list gets typed out live as code in an editor window (line numbers, syntax colours,
    blinking cursor, a slightly uneven human typing rhythm), and a live-preview panel beside it
    renders each item as a chip the moment its line is finished. Typing is paced to be done by
    `hold`. Scales down as one piece when the band is too short for it."""
    LH, TB, PAD, GUTTER, GAP = 46, 46, 22, 70, 50
    PANEL, TITLE, EDGE = (16, 22, 52), (24, 31, 68), (62, 72, 124)
    VAR, PUNCT, NUM = (156, 220, 254), (200, 206, 230), (92, 102, 150)

    def __init__(self, labels, cy, max_h, t0, hold, var="items"):
        f = mono(30)
        self.cw = f.getlength("M")
        lines = [[(var, self.VAR), (" = ", self.PUNCT), ("[", GOLD)]]
        lines += [[("    ", WHITE), (f'"{s}"', GREEN), (",", self.PUNCT)] for s in labels]
        lines += [[("]", GOLD)]]
        self.text = ["".join(tok for tok, _ in ln) for ln in lines]
        self.line_sprs = []
        for ln in lines:
            img = Image.new("RGBA", (int(self.cw * len("".join(t for t, _ in ln))) + 16, self.LH), (0, 0, 0, 0))
            d, x = ImageDraw.Draw(img), 0
            for tok, col in ln:
                d.text((x, self.LH / 2), tok, font=f, fill=col, anchor="lm"); x += self.cw * len(tok)
            self.line_sprs.append(img)
        self.nums = [text_sprite(str(i + 1), mono(24), self.NUM) for i in range(len(lines))]
        # editor + preview panels, side by side
        n = len(labels)
        self.ew = int(max(640, self.GUTTER + max(map(len, self.text)) * self.cw + 70))
        chip_w = int(max(320, max(dmsans(34, 450).getlength(s) for s in labels) + 140))
        self.pw = max(440, chip_w + 60)
        self.chip_h, chip_gap = 60, 14
        self.h = int(max(self.TB + 2 * self.PAD + len(lines) * self.LH,
                         self.TB + 2 * self.PAD + n * (self.chip_h + chip_gap) - chip_gap))
        self.w = self.ew + self.GAP + self.pw
        self.editor = self.panel(self.ew, self.h, f"{var}.py")
        self.preview = self.panel(self.pw, self.h, "Preview")
        self.chips = [chip_sprite(s, w=chip_w, h=self.chip_h) for s in labels]
        stack = n * (self.chip_h + chip_gap) - chip_gap
        body_mid = self.TB + (self.h - self.TB) / 2
        self.chip_y = [body_mid - stack / 2 + self.chip_h / 2 + i * (self.chip_h + chip_gap) for i in range(n)]
        self.code_top = self.TB + (self.h - self.TB - len(lines) * self.LH) / 2
        self.status = {k: text_sprite(txt, dmsans(24, 500), col) for k, txt, col in
                       (("busy", "rendering", self.PUNCT), ("done", "rendered", GREEN))}
        # typing schedule: uneven keystrokes, a beat on each newline, auto-indent is instant
        rnd = random.Random(len(labels) * 31 + len(var))
        weights, self.where = [], []                       # where[k] = (line, col) after keystroke k
        for li, line in enumerate(self.text):
            for ci, ch in enumerate(line):
                indent = li and ci < 4 and line[:4] == "    "
                weights.append(0 if indent else rnd.uniform(0.6, 1.4) * (1.6 if ch == "," else 1))
                self.where.append((li, ci + 1))
            weights[-1] += 2.5                             # pause / Enter at the end of the line
        start, end = t0 + 0.15, hold - 0.3
        dur = min(end - start, sum(1 for w in weights if w) / 14)      # never slower than ~14 chars/s
        acc, tot, self.key_t = 0.0, sum(weights), []
        for w in weights:
            acc += w
            self.key_t.append(start + dur * acc / tot)
        self.line_start = [start] + [self.key_t[sum(len(l) for l in self.text[:i]) - 1] for i in range(1, len(lines))]
        self.item_t = [self.key_t[sum(len(l) for l in self.text[:i + 2]) - 1] for i in range(n)]   # on its ","
        self.t0, self.done = t0, self.key_t[-1]
        self.k = min(1.0, max_h / (self.h + 20), (W - 120) / self.w)
        self.cy = cy

    def panel(self, w, h, title):
        s, r = 2, 18
        img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=r * s, fill=self.TITLE)
        d.rectangle((0, self.TB * s, w * s - 1, (self.TB + r) * s), fill=self.PANEL)
        d.rounded_rectangle((0, self.TB * s, w * s - 1, h * s - 1), radius=r * s, fill=self.PANEL)
        d.rectangle((0, self.TB * s, w * s - 1, self.TB * s + 1), fill=self.EDGE)
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=r * s, outline=self.EDGE, width=2 * s)
        for i, col in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            x, y = (26 + i * 24) * s, self.TB / 2 * s
            d.ellipse((x - 7 * s, y - 7 * s, x + 7 * s, y + 7 * s), fill=col)
        d.text((104 * s, self.TB / 2 * s), title, font=dmsans(24 * s, 500), fill=self.PUNCT, anchor="lm")
        return img.resize((w, h), Image.LANCZOS)

    def draw(self, c, t, alpha=1.0, dy=0.0):
        if t < self.t0 - 0.35: return
        layer = Image.new("RGBA", (self.w + 40, self.h + 40), (0, 0, 0, 0))
        ox, oy = 20, 20
        for i, (spr, x) in enumerate(((self.editor, ox + self.ew / 2), (self.preview, ox + self.ew + self.GAP + self.pw / 2))):
            q = prog(t, self.t0 - 0.35 + i * 0.1, 0.4)                # windows pop open
            paste(layer, spr, x, oy + self.h / 2 + (1 - out_expo(q)) * 30, 0.9 + 0.1 * out_back(q),
                  clamp(q * 3))
        if t >= self.t0:
            typed = sum(1 for kt in self.key_t if kt <= t)
            line, col = self.where[typed - 1] if typed else (0, 0)
            x0 = ox + self.GUTTER
            ys = [oy + self.code_top + (i + 0.5) * self.LH for i in range(len(self.text))]
            hl = Image.new("RGBA", (self.ew - 4, self.LH), (255, 255, 255, 14))    # current-line highlight
            paste(layer, hl, ox + self.ew / 2, ys[line])
            for i, (spr, num) in enumerate(zip(self.line_sprs, self.nums)):
                if t < self.line_start[i]: break
                paste(layer, num, ox + 50 - num.width / 2, ys[i], 1, 1.0 if i == line else 0.6)
                n = len(self.text[i]) if i < line else (col if i == line else 0)
                if n:
                    vis = spr.crop((0, 0, int(n * self.cw), self.LH))
                    paste(layer, vis, x0 + vis.width / 2, ys[i])
            # cursor: solid while typing, then blinks - on the real clock, so it keeps blinking in a hold
            if t < self.done or (real_t(t) - self.done) % 1.0 < 0.5:
                cx = x0 + col * self.cw + 2
                paste(layer, Image.new("RGBA", (3, 34), WHITE + (255,)), cx, ys[line])
            px = ox + self.ew + self.GAP + self.pw / 2
            for spr, y, ti in zip(self.chips, self.chip_y, self.item_t):            # rendered output
                q = prog(t, ti, 0.4)
                if q > 0:
                    paste(layer, spr, px, oy + y, out_back(q, 2.4), clamp(q * 3))
            busy = t < self.item_t[-1] + 0.05
            st = self.status["busy" if busy else "done"]
            if busy:
                dots = text_sprite("." * (1 + int(t * 4) % 3), dmsans(24, 500), self.PUNCT)
                paste(layer, dots, ox + self.ew + self.GAP + self.pw - 24 - dots.width / 2, oy + self.TB / 2)
                paste(layer, st, ox + self.ew + self.GAP + self.pw - 52 - st.width / 2, oy + self.TB / 2)
            else:
                q = prog(t, self.item_t[-1] + 0.05, 0.3)
                sx = ox + self.ew + self.GAP + self.pw - 24 - st.width / 2
                paste(layer, st, sx, oy + self.TB / 2, out_back(q))
                paste(layer, tick_sprite(q, size=24, color=GREEN, width=4), sx - st.width / 2 - 8, oy + self.TB / 2)
        paste(c, layer, W / 2, self.cy + dy, self.k, alpha)

def item_block(style, labels, top, bottom, t0, span, y=None, notes=None, note_dur=0.6, t_out=None,
               hold=None, var="items"):
    """One way of showing a list of skills/topics inside the band top..bottom, all items in by
    ~t0 + span. y pins chips/tube to their original anchor. notes = {label: handwritten note}
    (chips only). Returns an object with .draw()."""
    cy = (top + bottom) / 2
    stagger = min(0.2, span / max(len(labels), 1))
    if style == "chips":
        return ChipRow(labels, y or cy, t0, notes=notes, note_dur=note_dur)
    if style == "tube":
        return TubeLine(labels, y or cy, t0, dur=span)
    if style == "circuit":
        return CircuitRow(labels, y or cy, t0, span, notes=notes, note_dur=note_dur, region=(top - 10, H - 15),
                          t_out=t_out)
    if style == "painted":
        return PaintRow(labels, cy, bottom - top, t0, stagger)
    if style == "code":
        return CodeBlock(labels, cy, bottom - top, t0, hold or t0 + span * 1.8, var=var)
    if style in ("list", "checklist", "numbered"):
        marker = {"list": "bar", "checklist": "check", "numbered": "number"}[style]
        return ListBlock(labels, cy, bottom - top, t0, stagger, marker)
    if style == "inline":
        return InlineRow(labels, cy, t0, stagger)
    if style == "columns":
        return Columns(labels, cy, t0, stagger)
    if style == "handwritten":                     # one pen: items follow each other more slowly
        f = caveat(64 if len(labels) <= 4 else 58, 600)
        return ListBlock(labels, cy, bottom - top, t0, span / max(len(labels), 1), "hand", font=f)
    sys.exit(f"Unknown style {style!r} - pick one of: {', '.join(STYLES)}")

# ---------------------------------------------------------------- handwritten note
def caveat(size, weight=700):
    k = ("cv", size, weight)
    if k not in _font_cache:
        f = ImageFont.truetype(FONT_DIR + "Caveat-VariableFont_wght.ttf", size)
        f.set_variation_by_axes([weight])
        _font_cache[k] = f
    return _font_cache[k]

class HandNote:
    """A personal note in handwriting that writes itself on left to right, line by line, slightly
    tilted - deliberately a bit imperfect next to the clean type. Shrinks to fit max_lines."""
    def __init__(self, text, cx, cy, t0, signature="", size=72, max_w=1250, max_lines=2,
                 tilt=-2.5, cps=48, max_dur=1.4):
        while True:
            f = caveat(size, 600)
            body = wrap(text, f, max_w)
            if len(body) <= max_lines or size <= 44: break
            size -= 6
        lines = [(l, f, WHITE) for l in body]
        if signature:
            lines.append(("- " + signature, caveat(int(size * 0.85), 700), GOLD))
        self.sprs = [text_sprite(l, lf, col) for l, lf, col in lines]
        self.sig = bool(signature)
        self.lh = int(size * 1.08)
        self.w = max(s.width for s in self.sprs) + 40
        self.h = self.sprs[0].height + self.lh * (len(self.sprs) - 1) + 20
        # pen time per line proportional to its length, whole note capped at max_dur
        chars = [len(l) for l, _, _ in lines]
        per = min(1 / cps, max_dur / sum(chars))
        self.spans, t = [], t0
        for i, n in enumerate(chars):
            if self.sig and i == len(chars) - 1: t += 0.15          # small pause before signing
            self.spans.append((t, n * per)); t += n * per + 0.05
        self.end = t
        self.cx, self.cy, self.t0, self.tilt = cx, cy, t0, tilt

    def draw(self, c, t, alpha=1.0, dy=0.0):
        if t < self.t0: return
        layer = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for i, (spr, (start, dur)) in enumerate(zip(self.sprs, self.spans)):
            p = prog(t, start, dur)
            if p <= 0: continue
            vis = spr if p >= 1 else spr.crop((0, 0, int(8 + (spr.width - 16) * p), spr.height))
            last_sig = self.sig and i == len(self.sprs) - 1
            x = self.w - 20 - spr.width if last_sig else 20       # signature sits bottom-right
            layer.alpha_composite(vis, (x, i * self.lh))
        paste(c, layer, self.cx, self.cy + dy, 1, alpha, rot=self.tilt)

# ---------------------------------------------------------------- pen strokes
def wobble_pts(p0, p1, seed, amp=3.0, n=28, bow=0.0):
    """Points along p0 -> p1 with a gentle hand wobble; bow bends it into an arc (px)."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    pts = []
    for i in range(n + 1):
        u = i / n
        off = bow * 4 * u * (1 - u) + amp * (0.6 * math.sin(u * 3.1 + ph[0]) + 0.3 * math.sin(u * 7.7 + ph[1])
                                             + 0.1 * math.sin(u * 15 + ph[2]))
        pts.append((x0 + dx * u + nx * off, y0 + dy * u + ny * off))
    return pts

def draw_stroke(c, pts, q, color=GOLD, width=6, alpha=1.0, dy=0.0):
    """Pen stroke: the first q (0-1) of a polyline, round ends, supersampled."""
    if q <= 0 or alpha <= 0.003: return
    f = clamp(q) * (len(pts) - 1)
    i = int(f)
    part = list(pts[:i + 1])
    if i < len(pts) - 1 and f > i:
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        part.append((ax + (bx - ax) * (f - i), ay + (by - ay) * (f - i)))
    if len(part) < 2: return
    s, m = 2, width + 4
    x0, y0 = min(p[0] for p in part) - m, min(p[1] for p in part) - m
    x1, y1 = max(p[0] for p in part) + m, max(p[1] for p in part) + m
    img = Image.new("RGBA", (int((x1 - x0) * s) + 2, int((y1 - y0) * s) + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sp = [((x - x0) * s, (y - y0) * s) for x, y in part]
    d.line(sp, fill=color, width=width * s, joint="curve")
    r = width * s / 2
    for x, y in (sp[0], sp[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    img = img.resize((max(1, img.width // s), max(1, img.height // s)), Image.LANCZOS)
    paste(c, img, x0 + img.width / 2, y0 + dy + img.height / 2, 1, alpha)

def hand_underline(c, x0, x1, y, q, seed=1, alpha=1.0, width=6, dy=0.0):
    """Wobbly pen underline that overshoots a little and rises slightly, like a quick marker swipe."""
    draw_stroke(c, wobble_pts((x0 - 8, y + 3), (x1 + 12, y - 5), seed, amp=2.5), q, GOLD, width, alpha, dy)

def hand_arrow(c, p0, p1, q, seed=7, bow=40, alpha=1.0, width=5):
    """Curved pen arrow from p0 to p1: shaft draws first, then the two head strokes."""
    body = wobble_pts(p0, p1, seed, amp=2, bow=bow)
    draw_stroke(c, body, clamp(q / 0.75), GOLD, width, alpha)
    hq = clamp((q - 0.75) / 0.25)
    if hq > 0:
        (ax, ay), (bx, by) = body[-4], body[-1]
        ang = math.atan2(by - ay, bx - ax)
        for side in (-1, 1):
            a = ang + math.pi + side * 0.5
            tip = (bx + 26 * math.cos(a), by + 26 * math.sin(a))
            draw_stroke(c, wobble_pts((bx, by), tip, seed + side, amp=1, n=6), hq, GOLD, width, alpha)

class Aside:
    """Handwritten margin note up and to the right of a heading, with a pen arrow back to it.
    right/y = right edge and centre line of the thing being pointed at."""
    def __init__(self, text, right, y, t0, size=58, lift=150, max_w=500, tilt=6, max_dur=1.3, seed=9):
        # one line reads best as an aside: shrink to fit first, only wrap if it's still too long
        n = self.note = HandNote(text, 0, 0, t0, size=size, max_w=max_w, max_lines=1, tilt=tilt, max_dur=max_dur)
        n.cx = min(W - 60 - n.w / 2, right + 150 + n.w / 2)
        n.cy = y - lift
        self.arrow = ((n.cx - n.w / 6, n.cy + n.h / 2 + 10), (right + 25, y - 30))
        self.seed = seed

    def draw(self, c, t, alpha=1.0, dy=0.0):
        self.note.draw(c, t, alpha, dy)
        (ax, ay), (bx, by) = self.arrow
        hand_arrow(c, (ax, ay + dy), (bx, by + dy), out_cubic(prog(t, self.note.end, 0.45)),
                   seed=self.seed, bow=-35, alpha=alpha)

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
