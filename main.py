import base64
import csv
import datetime as dt
import html
import os
import urllib.parse
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

import poster

# ------------------------------------------------------------------
# Page config must be the first Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ",
    page_icon="🪔",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_FILE = "panchanga_2026_2027_verified.csv"
IST = ZoneInfo("Asia/Kolkata")

HEADER_LINES = [
    "ಶ್ರೀ ಶೇಚಜಯತು :",
    "ಶ್ರೀ ಶ್ರೀಪಾದರಾಜ , ಶ್ರೀ ರಾಘವೇಂದ್ರ ತೀರ್ಥರು , ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಕೇಶವನಿಧಿ ತೀರ್ಥರು ಪರಮಾನುಗ್ರಹದಿಂದ,",
]
TITLE = "ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ"
FOOTER_LINES = ["ಪಂಚಾಂಗ ಕರ್ತೃ :", "ಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."]

TEMPLATES = {"ಪೂರ್ಣ": "full", "ಸಂಕ್ಷಿಪ್ತ": "short", "ಶ್ರಾದ್ಧ": "shraddha"}
STYLES = {"ಮೇಲೆ ಚಿತ್ರ": "banner", "ವಾಟರ್‌ಮಾರ್ಕ್": "watermark"}


# ------------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------------
@st.cache_data
def load_rows():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def empty(val):
    return val is None or str(val).strip() == "" or str(val).lower() == "nan"


def end_text(e):
    if empty(e):
        return ""
    if e == "AR":
        return "ಅಹೋರಾತ್ರ (ಇಡೀ ದಿನ-ರಾತ್ರಿ)"
    try:
        h, m = (int(x) for x in e.split(":"))
        if h >= 24:
            return f"ಮರುದಿನ {h - 24:02d}:{m:02d} ರವರೆಗೆ"
        return f"{h:02d}:{m:02d} ರವರೆಗೆ"
    except ValueError:
        return e


def limb(r, key):
    """Name + end time, with optional second item (e.g. tithi2)."""
    name, end = r.get(key, ""), r.get(f"{key}_end", "")
    name2, end2 = r.get(f"{key}2", ""), r.get(f"{key}2_end", "")
    if empty(name):
        return ""
    s = f"{name} – {end_text(end)}" if not empty(end) else name
    if not empty(name2):
        s += f", ನಂತರ {name2} – {end_text(end2)}"
    return s


def t12(hhmm):
    if empty(hhmm):
        return ""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
        return f"{(h % 12) or 12:02d}:{m:02d} {'am' if h < 12 else 'pm'}"
    except ValueError:
        return hhmm


def get_fields(r, template, show_year=True):
    """Returns (date_line, [(label, value), ...], event_text)."""
    d = dt.date.fromisoformat(r["date"])
    year = f" {d.year}" if show_year else ""
    date_line = f"{d.strftime('%d-%m-%Y')}, {r['vara']}{year}"

    full = [
        ("ಸಂವತ್ಸರ", r["samvatsara"]),
        ("ಆಯಣ", r["ayana"]),
        ("ಋತು", r["ruthu"]),
        ("ಮಾಸ", r["masa"]),
        ("ಪಕ್ಷ", r["paksha"]),
        ("ತಿಥಿ", limb(r, "tithi")),
        ("ವಾರ", r["vara"]),
        ("ನಕ್ಷತ್ರ", limb(r, "nakshatra")),
        ("ಯೋಗ", limb(r, "yoga")),
        ("ಕರಣ", limb(r, "karana")),
        ("🌅 ಸೂರ್ಯೋದಯ", t12(r["sunrise"])),
        ("🌇 ಸೂರ್ಯಾಸ್ತ", t12(r["sunset"])),
        ("ಶ್ರಾದ್ಧತಿಥಿ", r["shraddha_tithi"]),
    ]
    short = [
        ("ಮಾಸ", r["masa"]),
        ("ಪಕ್ಷ", r["paksha"]),
        ("ತಿಥಿ", limb(r, "tithi")),
        ("ನಕ್ಷತ್ರ", limb(r, "nakshatra")),
        ("🌅 ಸೂರ್ಯೋದಯ", t12(r["sunrise"])),
        ("🌇 ಸೂರ್ಯಾಸ್ತ", t12(r["sunset"])),
    ]
    shraddha = [
        ("ಮಾಸ", r["masa"]),
        ("ಪಕ್ಷ", r["paksha"]),
        ("ತಿಥಿ", limb(r, "tithi")),
        ("ನಕ್ಷತ್ರ", limb(r, "nakshatra")),
        ("ಶ್ರಾದ್ಧತಿಥಿ", r["shraddha_tithi"]),
    ]
    chosen = {"full": full, "short": short, "shraddha": shraddha}[template]
    fields = [(k, v) for k, v in chosen if not empty(v)]

    event = "" if empty(r.get("event", "")) else r["event"].strip()
    if template == "short":
        event = ""
    return date_line, fields, event


# ------------------------------------------------------------------
# WhatsApp / plain-text message
# ------------------------------------------------------------------
DIVIDER = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈"


def render_message(r, template, show_year=True):
    date_line, fields, event = get_fields(r, template, show_year)
    bold = lambda x: f"*{x}*"
    lines = list(HEADER_LINES)
    lines += [bold("🪔 " + TITLE), DIVIDER]
    lines += ["📅 " + bold(date_line), ""]
    for label, value in fields:
        lines.append(f"{bold(label + ':')} {value}")
    if event:
        lines += ["", DIVIDER, bold("ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ:"), event]
    lines += ["", DIVIDER] + list(FOOTER_LINES)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Poster
# ------------------------------------------------------------------
def build_poster(r, template, show_year=True, style="banner", bg=None):
    date_line, fields, event = get_fields(r, template, show_year)
    return poster.make_poster(
        date_line, fields, event, HEADER_LINES, TITLE, FOOTER_LINES, bg=bg, style=style
    )


@st.cache_data(show_spinner="ಚಿತ್ರ ತಯಾರಾಗುತ್ತಿದೆ...")
def cached_poster(date_key, template, show_year, style, bg):
    return build_poster(load_rows()[date_key], template, show_year, style, bg)


# ------------------------------------------------------------------
# Direct share button (Web Share API -> WhatsApp / any app on the phone)
# ------------------------------------------------------------------
SHARE_HTML = """
<style>
  html, body { margin:0; padding:0; background:transparent; }
  #share {
    width:100%; box-sizing:border-box; border:0; cursor:pointer;
    padding:16px 12px; border-radius:16px;
    font-size:18px; font-weight:800; color:#fff; letter-spacing:.2px;
    font-family:-apple-system,"Segoe UI",Roboto,"Noto Sans Kannada",sans-serif;
    background:linear-gradient(135deg,#16a34a,#22c55e 50%,#f59e0b);
    box-shadow:0 6px 16px rgba(22,163,74,.35);
    -webkit-tap-highlight-color:transparent;
  }
  #share:active { transform:scale(.98); }
  #msg { font:13px sans-serif; color:#9a3412; text-align:center; margin-top:6px; min-height:16px; }
</style>
<button id="share">📤 ಹಂಚಿಕೊಳ್ಳಿ · Share</button>
<div id="msg"></div>
<script>
  const B64 = "__B64__";
  const NAME = "__NAME__";
  const msg = document.getElementById("msg");

  function makeFile() {
    const bin = atob(B64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new File([arr], NAME, { type: "image/png" });
  }
  function fallbackSave(file) {
    const url = URL.createObjectURL(file);
    const a = document.createElement("a");
    a.href = url; a.download = NAME;
    document.body.appendChild(a); a.click(); a.remove();
    msg.textContent = "ಈ ಸಾಧನದಲ್ಲಿ ನೇರ ಹಂಚಿಕೆ ಲಭ್ಯವಿಲ್ಲ — ಚಿತ್ರ ಸೇವ್ ಆಗಿದೆ.";
  }
  document.getElementById("share").addEventListener("click", async () => {
    const file = makeFile();
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "ನಿತ್ಯ ಪಂಚಾಂಗ" });
      } else {
        fallbackSave(file);
      }
    } catch (e) {
      if (e && e.name !== "AbortError") fallbackSave(file);
    }
  });
</script>
"""


def share_button(png_bytes, filename):
    b64 = base64.b64encode(png_bytes).decode()
    code = SHARE_HTML.replace("__B64__", b64).replace("__NAME__", filename)
    components.html(code, height=90)


# ------------------------------------------------------------------
# Styling: colourful + mobile first
# ------------------------------------------------------------------
CSS = """
<style>
/* ===== page background ===== */
.stApp {
  background:
    radial-gradient(circle at 12% 8%, rgba(251,146,60,.28), transparent 38%),
    radial-gradient(circle at 92% 18%, rgba(236,72,153,.18), transparent 36%),
    radial-gradient(circle at 50% 100%, rgba(250,204,21,.28), transparent 45%),
    linear-gradient(180deg, #fff7ed 0%, #ffedd5 45%, #fef3c7 100%);
  background-attachment: fixed;
}
.stApp, .stApp label, .stApp p, .stApp span { color: #3b1d0a; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container {
  padding: .6rem .8rem 3rem .8rem !important;
  max-width: 720px;
}

/* ===== hero ===== */
.hero {
  position: relative; overflow: hidden; text-align: center;
  margin: .2rem 0 .9rem 0; padding: 18px 12px 16px 12px;
  border-radius: 22px; color: #fff;
  background: linear-gradient(135deg, #7f1d1d 0%, #c2410c 45%, #f59e0b 100%);
  box-shadow: 0 10px 26px rgba(127,29,29,.30);
  border: 2px solid #fcd34d;
}
.hero::before, .hero::after {
  content: ""; position: absolute; border-radius: 50%; background: rgba(255,255,255,.12);
}
.hero::before { width: 120px; height: 120px; top: -45px; left: -35px; }
.hero::after  { width: 160px; height: 160px; bottom: -70px; right: -50px; }
.hero .diya { font-size: clamp(2rem, 10vw, 2.8rem); line-height: 1; }
.hero .h1 { font-size: clamp(1.25rem, 6.2vw, 1.8rem); font-weight: 800; margin-top: 4px; color:#fff !important; }
.hero .h2 { font-size: clamp(.78rem, 3.4vw, .95rem); color: #fef3c7 !important; margin-top: 2px; }

/* ===== keep button rows on one line, even on phones ===== */
div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem !important; }
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
  min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}

/* ===== buttons ===== */
.stButton > button, .stLinkButton > a {
  min-height: 2.9rem; border-radius: 14px; border: 0;
  font-weight: 700; padding: .35rem .2rem; white-space: nowrap;
  color: #fff !important;
  background: linear-gradient(135deg, #b45309, #f59e0b);
  box-shadow: 0 4px 10px rgba(180,83,9,.28);
  transition: transform .08s ease;
}
.stButton > button:active, .stLinkButton > a:active { transform: scale(.96); }
.stButton > button p, .stLinkButton > a p { color: #fff !important; font-size: clamp(.78rem, 3.6vw, 1rem); font-weight: 700; }
div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button { background: linear-gradient(135deg,#7f1d1d,#dc2626); box-shadow: 0 4px 10px rgba(185,28,28,.30); }
div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton > button { background: linear-gradient(135deg,#047857,#10b981); box-shadow: 0 4px 10px rgba(4,120,87,.30); }
div[data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton > button { background: linear-gradient(135deg,#1d4ed8,#6366f1); box-shadow: 0 4px 10px rgba(29,78,216,.30); }
div[data-testid="stHorizontalBlock"] > div:nth-child(4) .stButton > button { background: linear-gradient(135deg,#86198f,#ec4899); box-shadow: 0 4px 10px rgba(134,25,143,.30); }
.stLinkButton > a { background: linear-gradient(135deg,#15803d,#22c55e); box-shadow: 0 4px 12px rgba(21,128,61,.35); text-decoration: none; display:flex; align-items:center; justify-content:center; }

/* ===== date input ===== */
div[data-testid="stDateInput"] > div > div { border-radius: 14px; border: 2px solid #fb923c; background: #fff; }
div[data-testid="stDateInput"] input { font-size: 1.05rem; font-weight: 700; min-height: 2.8rem; color: #7c2d12 !important; }
div[data-testid="stDateInput"] label p { font-weight: 700; color: #9a3412 !important; }

/* ===== template picker (segmented / radio) ===== */
div[data-testid="stSegmentedControl"] { width: 100%; }
div[data-testid="stSegmentedControl"] button { flex: 1 1 0; min-height: 2.6rem; font-weight: 700; }
div[data-testid="stRadio"] > div { gap: .4rem; flex-wrap: wrap; }
div[data-testid="stRadio"] label {
  background: #fff; border: 2px solid #fdba74; border-radius: 999px; padding: .25rem .9rem;
}

/* ===== tabs ===== */
.stTabs [data-baseweb="tab-list"] {
  gap: .3rem; padding: .3rem; border-radius: 16px;
  background: rgba(255,255,255,.7); border: 1px solid #fdba74; overflow-x: auto;
}
.stTabs [data-baseweb="tab"] {
  flex: 1 1 0; justify-content: center; border-radius: 12px; padding: .5rem .4rem;
  font-weight: 800; background: transparent; height: auto;
}
.stTabs [aria-selected="true"] { background: linear-gradient(135deg,#c2410c,#f59e0b); }
.stTabs [aria-selected="true"] p { color: #fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ===== expander ===== */
div[data-testid="stExpander"] { border-radius: 16px; border: 2px dashed #fdba74; background: rgba(255,255,255,.7); }

/* ===== images ===== */
div[data-testid="stImage"] img { border-radius: 18px; box-shadow: 0 8px 22px rgba(0,0,0,.22); border: 2px solid #fcd34d; }

/* ===== panchanga card ===== */
.pc-card {
  border-radius: 22px; overflow: hidden; background: #fffdf8;
  border: 2px solid #f59e0b; box-shadow: 0 10px 26px rgba(180,83,9,.22);
  margin: .6rem 0 1rem 0;
}
.pc-head {
  background: linear-gradient(135deg, #7f1d1d, #c2410c 55%, #f59e0b);
  padding: 14px 12px; text-align: center;
}
.pc-head .blessing { font-size: clamp(.66rem, 2.7vw, .8rem); color: #fef3c7; line-height: 1.55; }
.pc-head .title { font-size: clamp(1.1rem, 5.2vw, 1.45rem); font-weight: 800; margin-top: 6px; color: #fff; }
.pc-date {
  background: linear-gradient(90deg, #fde68a, #fcd34d, #fde68a);
  text-align: center; padding: 10px 8px; font-weight: 800;
  font-size: clamp(.95rem, 4.4vw, 1.2rem); color: #7c2d12;
}
.pc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px; }
.pc-item {
  --c: #c2410c;
  min-width: 0; padding: 9px 11px; border-radius: 14px;
  background: #fff; border: 1px solid rgba(0,0,0,.06); border-left: 5px solid var(--c);
  background: color-mix(in srgb, var(--c) 9%, #ffffff);
  box-shadow: 0 2px 6px rgba(0,0,0,.05);
}
.pc-item.wide { grid-column: 1 / -1; }
.pc-label { font-size: .74rem; font-weight: 800; color: var(--c); letter-spacing: .2px; }
.pc-value { font-size: clamp(.92rem, 3.9vw, 1.05rem); font-weight: 700; color: #2b1407; overflow-wrap: anywhere; margin-top: 2px; }
.pc-event {
  margin: 2px 10px 12px 10px; padding: 12px 14px; border-radius: 16px;
  background: linear-gradient(135deg, #fff1f2, #ffe4e6); border: 2px solid #fb7185;
  white-space: pre-wrap; font-size: clamp(.9rem, 3.8vw, 1rem); line-height: 1.6; color: #4c0519;
}
.pc-event .pc-label { font-size: .85rem; color: #be123c; margin-bottom: 4px; }
.pc-foot {
  text-align: center; padding: 10px; font-size: .88rem; font-weight: 700; color: #fef3c7;
  background: linear-gradient(135deg, #7f1d1d, #c2410c);
}
@media (max-width: 340px) { .pc-grid { grid-template-columns: 1fr; } }
</style>
"""

LABEL_STYLE = {
    "ಸಂವತ್ಸರ": ("🗓️", "#c2410c"),
    "ಆಯಣ": ("🧭", "#0f766e"),
    "ಋತು": ("🌿", "#15803d"),
    "ಮಾಸ": ("🌙", "#7c3aed"),
    "ಪಕ್ಷ": ("🌓", "#be185d"),
    "ತಿಥಿ": ("🔆", "#b45309"),
    "ವಾರ": ("📆", "#1d4ed8"),
    "ನಕ್ಷತ್ರ": ("⭐", "#a21caf"),
    "ಯೋಗ": ("🕉️", "#0e7490"),
    "ಕರಣ": ("🔱", "#b91c1c"),
    "ಸೂರ್ಯೋದಯ": ("🌅", "#ea580c"),
    "ಸೂರ್ಯಾಸ್ತ": ("🌇", "#4338ca"),
    "ಶ್ರಾದ್ಧತಿಥಿ": ("🙏", "#9f1239"),
}
WIDE_LABELS = ("ತಿಥಿ", "ನಕ್ಷತ್ರ", "ಯೋಗ", "ಕರಣ", "ಶ್ರಾದ್ಧತಿಥಿ")


def render_card(r, template, show_year):
    date_line, fields, event = get_fields(r, template, show_year)
    esc = html.escape
    items = ""
    for label, value in fields:
        name = poster.clean_label(label)
        icon, color = LABEL_STYLE.get(name, ("✨", "#c2410c"))
        wide = " wide" if name in WIDE_LABELS else ""
        items += (
            f'<div class="pc-item{wide}" style="--c:{color}">'
            f'<div class="pc-label">{icon} {esc(name)}</div>'
            f'<div class="pc-value">{esc(value)}</div></div>'
        )
    ev = ""
    if event:
        ev = (
            '<div class="pc-event"><div class="pc-label">🕉️ ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ</div>'
            f"{esc(event)}</div>"
        )
    return (
        '<div class="pc-card">'
        '<div class="pc-head">'
        f'<div class="blessing">{esc(HEADER_LINES[0])}<br>{esc(HEADER_LINES[1])}</div>'
        f'<div class="title">🪔 {esc(TITLE)}</div></div>'
        f'<div class="pc-date">📅 {esc(date_line)}</div>'
        f'<div class="pc-grid">{items}</div>'
        f"{ev}"
        f'<div class="pc-foot">{esc(FOOTER_LINES[0])} {esc(FOOTER_LINES[1])}</div>'
        "</div>"
    )


def pick(label, options, key):
    """Segmented control when available, otherwise a horizontal radio."""
    names = list(options.keys())
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(
            label, names, default=names[0], key=key, label_visibility="collapsed"
        )
        return v or names[0]
    return st.radio(label, names, horizontal=True, key=key, label_visibility="collapsed")


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
def main():
    st.markdown(CSS, unsafe_allow_html=True)

    rows = load_rows()
    if not rows:
        st.error(f"⚠️ `{DATA_FILE}` ಫೈಲ್ ಸಿಕ್ಕಿಲ್ಲ! ಮೇನ್ ಫೋಲ್ಡರ್‌ನಲ್ಲಿ ಅಪ್ಲೋಡ್ ಮಾಡಿ.")
        return

    dates = sorted(rows.keys())
    min_d = dt.date.fromisoformat(dates[0])
    max_d = dt.date.fromisoformat(dates[-1])
    today = dt.datetime.now(IST).date()

    def clamp(d):
        return min(max(d, min_d), max_d)

    if "sel_date" not in st.session_state:
        st.session_state["sel_date"] = clamp(today)

    # ---- Hero ----
    st.markdown(
        '<div class="hero"><div class="diya">🪔</div>'
        '<div class="h1">ನಿತ್ಯ ಪಂಚಾಂಗ</div>'
        '<div class="h2">ಸೂರ್ಯಸಿದ್ಧಾಂತ · ಪ್ರತಿದಿನದ ಪಂಚಾಂಗ</div></div>',
        unsafe_allow_html=True,
    )

    # ---- Date navigation ----
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("◀ ಹಿಂದೆ", use_container_width=True):
        st.session_state["sel_date"] = clamp(st.session_state["sel_date"] - dt.timedelta(days=1))
        st.rerun()
    if c2.button("ಇಂದು", use_container_width=True):
        st.session_state["sel_date"] = clamp(today)
        st.rerun()
    if c3.button("ನಾಳೆ", use_container_width=True):
        st.session_state["sel_date"] = clamp(today + dt.timedelta(days=1))
        st.rerun()
    if c4.button("ಮುಂದೆ ▶", use_container_width=True):
        st.session_state["sel_date"] = clamp(st.session_state["sel_date"] + dt.timedelta(days=1))
        st.rerun()

    selected = st.date_input(
        "📅 ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ",
        key="sel_date",
        min_value=min_d,
        max_value=max_d,
        format="DD/MM/YYYY",
    )

    # ---- Template ----
    template = TEMPLATES[pick("ಟೆಂಪ್ಲೇಟ್", TEMPLATES, "tpl")]

    # ---- Settings ----
    with st.expander("⚙️ ಇನ್ನಷ್ಟು ಸೆಟ್ಟಿಂಗ್ಸ್"):
        show_year = st.toggle("ವರ್ಷ ತೋರಿಸಿ", value=True)
        st.caption("ಚಿತ್ರದ ಶೈಲಿ")
        style = STYLES[pick("ಚಿತ್ರದ ಶೈಲಿ", STYLES, "sty")]
        bg_file = st.file_uploader(
            "ಹಿನ್ನೆಲೆ ಚಿತ್ರ ಬದಲಿಸಿ (ಐಚ್ಛಿಕ)", type=["jpg", "jpeg", "png", "webp"]
        )
        bg_bytes = bg_file.getvalue() if bg_file else None
        if not bg_bytes and poster.find_bg() is None:
            st.warning(
                "ಹಿನ್ನೆಲೆ ಚಿತ್ರ ಸಿಕ್ಕಿಲ್ಲ. `assets/background.jpg` ಎಂದು ಸೇರಿಸಿ ಅಥವಾ ಇಲ್ಲಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ."
            )

    row = rows.get(selected.isoformat())
    if not row:
        st.warning(f"⚠️ {selected.strftime('%d-%m-%Y')} ರ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ.")
        return

    tab_view, tab_img, tab_share = st.tabs(["📖 ಪಂಚಾಂಗ", "🖼️ ಚಿತ್ರ", "💬 ಸಂದೇಶ"])

    with tab_view:
        st.markdown(render_card(row, template, show_year), unsafe_allow_html=True)

    with tab_img:
        png = cached_poster(row["date"], template, show_year, style, bg_bytes)
        st.image(png, use_container_width=True)
        share_button(png, f"panchanga_{row['date']}.png")

    with tab_share:
        wa_text = render_message(row, template, show_year)
        st.link_button(
            "🟢 WhatsApp ನಲ್ಲಿ ಹಂಚಿಕೊಳ್ಳಿ",
            "https://wa.me/?text=" + urllib.parse.quote(wa_text),
            use_container_width=True,
        )
        st.caption("ಸಂದೇಶವನ್ನು ಬಲ ಮೂಲೆಯ 📋 ಬಟನ್‌ನಿಂದ ಕಾಪಿ ಮಾಡಬಹುದು.")
        st.code(wa_text, language=None, wrap_lines=True)


main()
