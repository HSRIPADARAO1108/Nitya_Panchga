"""Panchanga poster generator (PNG) - background photo + Kannada text.

Needs: Pillow with RAQM (for correct Kannada conjunct shaping) and a Kannada font.
Font lookup order (inside ./fonts):
  1. NotoSansKannada-Regular.ttf + NotoSansKannada-Bold.ttf   (static, best)
  2. NotoSansKannada-VF.ttf                                   (variable font)
If none is found, the variable font is downloaded once from Google Fonts on GitHub.
"""
import io
import os
import urllib.request

from PIL import Image, ImageDraw, ImageFont, features

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")
BG_PATH = os.path.join(BASE, "assets", "background.jpg")

VF_URL = (
    "https://github.com/google/fonts/raw/main/ofl/notosanskannada/"
    "NotoSansKannada%5Bwdth%2Cwght%5D.ttf"
)

GOLD = (255, 205, 96)
GOLD_DARK = (176, 96, 10)
WHITE = (255, 255, 255)
SOFT = (235, 225, 210)
DARK = (28, 14, 6)

W = 1080
PAD = 56
IMG_VISIBLE = 720  # height of the area where the photo stays clearly visible


# ------------------------------------------------------------------ fonts
def _find_font_files():
    reg = os.path.join(FONT_DIR, "NotoSansKannada-Regular.ttf")
    bold = os.path.join(FONT_DIR, "NotoSansKannada-Bold.ttf")
    vf = os.path.join(FONT_DIR, "NotoSansKannada-VF.ttf")
    if os.path.exists(reg) and os.path.exists(bold):
        return reg, bold, False
    if not os.path.exists(vf):
        os.makedirs(FONT_DIR, exist_ok=True)
        urllib.request.urlretrieve(VF_URL, vf)
    return vf, vf, True


_CACHE = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key in _CACHE:
        return _CACHE[key]
    reg, bld, variable = _find_font_files()
    engine = (
        ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    )
    font = ImageFont.truetype(bld if bold else reg, size, layout_engine=engine)
    if variable:
        try:
            axes = font.get_variation_axes()
            vals = []
            for a in axes:
                name = a["name"]
                name = name.decode() if isinstance(name, bytes) else str(name)
                if "eight" in name:  # Weight
                    vals.append(700 if bold else 400)
                else:  # Width etc.
                    vals.append(a.get("default", 100))
            font.set_variation_by_axes(vals)
        except Exception:
            pass
    _CACHE[key] = font
    return font


# ------------------------------------------------------------------ helpers
def clean_label(label):
    """Remove emoji (not supported by the Kannada font) from labels."""
    return "".join(ch for ch in label if ord(ch) < 0x1F000).strip()


def text_w(draw, text, font):
    return draw.textlength(text, font=font)


def wrap(draw, text, font, max_w):
    lines = []
    for para in str(text).split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            test = cur + " " + w
            if text_w(draw, test, font) <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def line_h(font, extra=1.45):
    return int(font.size * extra)


def centered(draw, y, text, font, fill, width=W, shadow=True):
    x = (width - text_w(draw, text, font)) / 2
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0), )
    draw.text((x, y), text, font=font, fill=fill)


def diamond_divider(draw, y, width=W, color=GOLD):
    cx = width // 2
    draw.line((PAD + 40, y, cx - 24, y), fill=color, width=2)
    draw.line((cx + 24, y, width - PAD - 40, y), fill=color, width=2)
    r = 9
    draw.polygon([(cx, y - r), (cx + r, y), (cx, y + r), (cx - r, y)], fill=color)


def cover_top(img, width):
    """Scale image to the given width, keep top aligned."""
    scale = width / img.width
    return img.resize((width, int(img.height * scale)), Image.LANCZOS)


def vertical_gradient(width, height, c_top, c_bottom, a_top, a_bottom):
    grad = Image.new("RGBA", (width, height))
    px = grad.load()
    for y in range(height):
        t = y / max(1, height - 1)
        a = int(a_top + (a_bottom - a_top) * t)
        c = tuple(int(c_top[i] + (c_bottom[i] - c_top[i]) * t) for i in range(3))
        for x in range(width):
            px[x, y] = (*c, a)
    return grad


# ------------------------------------------------------------------ main
def make_poster(
    date_line,
    fields,
    event,
    header_lines,
    title,
    footer_lines,
    bg_path=BG_PATH,
):
    """Returns PNG bytes. fields = [(label, value), ...]."""
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    f_bless = get_font(30)
    f_title = get_font(60, bold=True)
    f_date = get_font(46, bold=True)
    f_label = get_font(32, bold=True)
    f_value = get_font(36)
    f_ev_t = get_font(34, bold=True)
    f_ev = get_font(33)
    f_foot = get_font(32, bold=True)

    # ---- measure the lower panel first so total height is exact
    label_col = 300
    value_w = W - 2 * PAD - 2 * 28 - label_col
    rows = []
    rows_h = 0
    for label, value in fields:
        vl = wrap(scratch, value, f_value, value_w)
        h = max(len(vl) * line_h(f_value), line_h(f_label)) + 26
        rows.append((clean_label(label), vl, h))
        rows_h += h

    ev_lines = []
    ev_h = 0
    if event:
        ev_lines = wrap(scratch, event, f_ev, W - 2 * PAD - 2 * 28)
        ev_h = line_h(f_ev_t) + len(ev_lines) * line_h(f_ev) + 56

    date_y = IMG_VISIBLE
    date_h = 92
    panel_y = date_y + date_h + 36
    panel_h = rows_h + 24
    after_panel = panel_y + panel_h
    ev_y = after_panel + 28
    foot_y = ev_y + ev_h + (28 if ev_h else 0)
    total_h = foot_y + 40 + 2 * line_h(f_foot) + 48

    # ---- background
    canvas = Image.new("RGBA", (W, total_h), (*DARK, 255))
    if os.path.exists(bg_path):
        bg = cover_top(Image.open(bg_path).convert("RGB"), W)
        # slight softening so upscaled photo looks cleaner
        bg = bg.convert("RGBA")
        canvas.paste(bg, (0, 0))
    else:
        canvas.paste(vertical_gradient(W, total_h, (120, 60, 10), DARK, 255, 255))

    # fade photo into dark brown below the visible area
    fade_start = IMG_VISIBLE - 120
    fade_h = 260
    canvas.alpha_composite(
        vertical_gradient(W, fade_h, DARK, DARK, 0, 245), (0, fade_start)
    )
    solid_y = fade_start + fade_h
    if solid_y < total_h:
        canvas.alpha_composite(
            Image.new("RGBA", (W, total_h - solid_y), (*DARK, 245)), (0, solid_y)
        )
    # top shade behind header text
    canvas.alpha_composite(vertical_gradient(W, 300, (0, 0, 0), (0, 0, 0), 190, 0), (0, 0))

    d = ImageDraw.Draw(canvas)

    # ---- outer gold frame
    d.rounded_rectangle((14, 14, W - 14, total_h - 14), radius=26, outline=GOLD, width=4)
    d.rounded_rectangle((24, 24, W - 24, total_h - 24), radius=20, outline=(*GOLD_DARK, 255), width=2)

    # ---- header
    y = 52
    for ln in header_lines:
        for sub in wrap(d, ln, f_bless, W - 2 * PAD - 20):
            centered(d, y, sub, f_bless, SOFT)
            y += line_h(f_bless, 1.4)
    y += 10
    centered(d, y, title, f_title, GOLD)
    y += line_h(f_title, 1.3)
    diamond_divider(d, y + 6)

    # ---- date pill
    pill = (PAD + 40, date_y, W - PAD - 40, date_y + date_h)
    d.rounded_rectangle(pill, radius=46, fill=GOLD, outline=WHITE, width=3)
    dw = text_w(d, date_line, f_date)
    d.text(((W - dw) / 2, date_y + (date_h - f_date.size * 1.25) / 2 - 2), date_line, font=f_date, fill=DARK)

    # ---- details panel
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(
        (PAD, panel_y, W - PAD, panel_y + panel_h),
        radius=24,
        fill=(0, 0, 0, 120),
        outline=(*GOLD, 160),
        width=2,
    )
    canvas.alpha_composite(overlay)
    d = ImageDraw.Draw(canvas)

    ry = panel_y + 12
    for i, (label, vl, h) in enumerate(rows):
        d.text((PAD + 28, ry + 10), label, font=f_label, fill=GOLD)
        d.text((PAD + 28 + label_col - 22, ry + 10), ":", font=f_label, fill=GOLD)
        vy = ry + 10
        for ln in vl:
            d.text((PAD + 28 + label_col, vy), ln, font=f_value, fill=WHITE)
            vy += line_h(f_value)
        ry += h
        if i < len(rows) - 1:
            d.line((PAD + 28, ry - 2, W - PAD - 28, ry - 2), fill=(255, 205, 96, 60), width=1)

    # ---- event box
    if event:
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle(
            (PAD, ev_y, W - PAD, ev_y + ev_h),
            radius=24,
            fill=(120, 60, 10, 150),
            outline=(*GOLD, 200),
            width=2,
        )
        canvas.alpha_composite(overlay)
        d = ImageDraw.Draw(canvas)
        d.text((PAD + 28, ev_y + 18), "ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ", font=f_ev_t, fill=GOLD)
        ty = ev_y + 18 + line_h(f_ev_t)
        for ln in ev_lines:
            d.text((PAD + 28, ty), ln, font=f_ev, fill=WHITE)
            ty += line_h(f_ev)

    # ---- footer
    diamond_divider(d, foot_y + 10)
    fy = foot_y + 30
    for ln in footer_lines:
        centered(d, fy, ln, f_foot, GOLD)
        fy += line_h(f_foot)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
