import csv
import datetime as dt
import html
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import streamlit as st

import poster

# ------------------------------------------------------------------
# Page config must be the first Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ",
    page_icon="🪔",
    layout="centered",
)

DATA_FILE = "panchanga_2026_2027_verified.csv"
IST = ZoneInfo("Asia/Kolkata")
SEND_HOUR = 22  # 10 PM IST: sends tomorrow's panchanga

HEADER_LINES = [
    "ಶ್ರೀ ಶೇಚಜಯತು :",
    "ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ ಪರಮಾನುಗ್ರಹದಿಂದ,",
]
TITLE = "ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ"
FOOTER_LINES = ["ಪಂಚಾಂಗ ಕರ್ತೃ :", "ಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."]

TEMPLATES = {
    "ಪೂರ್ಣ ಪಂಚಾಂಗ (Full)": "full",
    "ಸಂಕ್ಷಿಪ್ತ (Short)": "short",
    "ಶ್ರಾದ್ಧ ಕೇಂದ್ರಿತ (Shraddha)": "shraddha",
}


# ------------------------------------------------------------------
# Secrets: never hard-code the bot token in source code
# ------------------------------------------------------------------
def get_secret(name, default=""):
    val = os.environ.get(name)
    if val:
        return val
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


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
# Message rendering (WhatsApp / plain  vs  Telegram HTML)
# ------------------------------------------------------------------
DIVIDER = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈"


def render_message(r, template, fmt="wa", show_year=True):
    """fmt = 'wa' (WhatsApp/Markdown-style *bold*) or 'tg' (Telegram HTML)."""
    date_line, fields, event = get_fields(r, template, show_year)

    if fmt == "tg":
        esc = html.escape
        bold = lambda x: f"<b>{esc(x)}</b>"
        txt = esc
    else:
        bold = lambda x: f"*{x}*"
        txt = lambda x: x

    lines = [txt(x) for x in HEADER_LINES]
    lines += [bold("🪔 " + TITLE), DIVIDER]
    lines += ["📅 " + bold(date_line), ""]
    for label, value in fields:
        lines.append(f"{bold(label + ':')} {txt(value)}")
    if event:
        lines += ["", DIVIDER, bold("ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ:"), txt(event)]
    lines += ["", DIVIDER] + [txt(x) for x in FOOTER_LINES]
    return "\n".join(lines)


# ------------------------------------------------------------------
# Telegram
# ------------------------------------------------------------------
def send_telegram(text, token, chat_id):
    if not token or not chat_id:
        return False, "Bot Token ಅಥವಾ Chat ID ನೀಡಲಾಗಿಲ್ಲ."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    ).encode()
    try:
        req = urllib.request.Request(url, data=body)
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.load(resp)
            return res.get("ok", False), "ಯಶಸ್ವಿಯಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ"
    except Exception as e:
        return False, f"ದೋಷ ({chat_id}): {e}"


def send_to_all(text, token, chat_ids):
    results = []
    for cid in chat_ids:
        ok, msg = send_telegram(text, token, cid)
        results.append((cid, ok, msg))
    return results


def send_telegram_photo(png_bytes, token, chat_id, caption=""):
    """Send a PNG as a document-quality photo (multipart/form-data)."""
    if not token or not chat_id:
        return False, "Bot Token ಅಥವಾ Chat ID ನೀಡಲಾಗಿಲ್ಲ."
    boundary = "----PanchangaBoundary7MA4YWxkTrZu0gW"
    parts = []

    def field(name, value):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    field("chat_id", chat_id)
    if caption:
        field("caption", caption)
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
            'filename="panchanga.png"\r\nContent-Type: image/png\r\n\r\n'
        ).encode()
    )
    parts.append(png_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.load(resp)
            return res.get("ok", False), "ಚಿತ್ರ ಯಶಸ್ವಿಯಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ"
    except Exception as e:
        return False, f"ದೋಷ ({chat_id}): {e}"


def build_poster(r, template, show_year=True):
    date_line, fields, event = get_fields(r, template, show_year)
    return poster.make_poster(
        date_line, fields, event, HEADER_LINES, TITLE, FOOTER_LINES
    )


@st.cache_data(show_spinner="ಚಿತ್ರ ತಯಾರಾಗುತ್ತಿದೆ...")
def cached_poster(date_key, template, show_year):
    return build_poster(load_rows()[date_key], template, show_year)


def parse_ids(raw):
    return [x.strip() for x in raw.replace("\n", ",").split(",") if x.strip()]


# ------------------------------------------------------------------
# Background scheduler: ONE thread per server (not per browser session)
# ------------------------------------------------------------------
@st.cache_resource
def start_scheduler(token, chat_ids_tuple, template, send_image):
    state = {"last_sent": None}

    def loop():
        while True:
            try:
                now = dt.datetime.now(IST)
                tomorrow = (now + dt.timedelta(days=1)).date().isoformat()
                if (
                    now.hour == SEND_HOUR
                    and now.minute < 10
                    and state["last_sent"] != tomorrow
                ):
                    rows = load_rows()
                    if tomorrow in rows and token and chat_ids_tuple:
                        msg = render_message(rows[tomorrow], template, "tg")
                        if send_image:
                            png = build_poster(rows[tomorrow], template)
                            for cid in chat_ids_tuple:
                                send_telegram_photo(png, token, cid)
                        send_to_all(msg, token, chat_ids_tuple)
                        state["last_sent"] = tomorrow
            except Exception:
                pass
            time.sleep(30)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return state


# ------------------------------------------------------------------
# Styling
# ------------------------------------------------------------------
CSS = """
<style>
.block-container { padding-top: 1.5rem; max-width: 760px; }
.pc-card {
  border: 1px solid rgba(214,125,20,.45);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(0,0,0,.12);
  margin: .5rem 0 1rem 0;
}
.pc-head {
  background: linear-gradient(135deg, #b45309, #f59e0b);
  color: #fff; padding: 16px 18px; text-align: center;
}
.pc-head .blessing { font-size: .8rem; opacity: .95; line-height: 1.5; }
.pc-head .title { font-size: 1.35rem; font-weight: 700; margin-top: 6px; }
.pc-date {
  background: rgba(245,158,11,.14);
  text-align: center; padding: 10px; font-weight: 700; font-size: 1.1rem;
}
.pc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.pc-item { padding: 10px 16px; border-top: 1px solid rgba(128,128,128,.2); }
.pc-item.wide { grid-column: 1 / -1; }
.pc-label { font-size: .75rem; opacity: .7; }
.pc-value { font-size: 1rem; font-weight: 600; }
.pc-event {
  padding: 12px 16px; border-top: 1px solid rgba(128,128,128,.2);
  background: rgba(245,158,11,.08); white-space: pre-wrap;
}
.pc-event .pc-label { font-weight: 700; opacity: .9; }
.pc-foot {
  text-align: center; padding: 10px; font-size: .85rem; opacity: .8;
  border-top: 1px solid rgba(128,128,128,.2);
}
@media (max-width: 520px) { .pc-grid { grid-template-columns: 1fr; } }
</style>
"""

WIDE_LABELS = ("ತಿಥಿ", "ನಕ್ಷತ್ರ", "ಯೋಗ", "ಕರಣ", "ಶ್ರಾದ್ಧತಿಥಿ")


def render_card(r, template, show_year):
    date_line, fields, event = get_fields(r, template, show_year)
    esc = html.escape
    items = ""
    for label, value in fields:
        wide = " wide" if label in WIDE_LABELS else ""
        items += (
            f'<div class="pc-item{wide}"><div class="pc-label">{esc(label)}</div>'
            f'<div class="pc-value">{esc(value)}</div></div>'
        )
    ev = ""
    if event:
        ev = (
            '<div class="pc-event"><div class="pc-label">ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ</div>'
            f"{esc(event)}</div>"
        )
    return f"""
<div class="pc-card">
  <div class="pc-head">
    <div class="blessing">{esc(HEADER_LINES[0])}<br>{esc(HEADER_LINES[1])}</div>
    <div class="title">🪔 {esc(TITLE)}</div>
  </div>
  <div class="pc-date">📅 {esc(date_line)}</div>
  <div class="pc-grid">{items}</div>
  {ev}
  <div class="pc-foot">{esc(FOOTER_LINES[0])} {esc(FOOTER_LINES[1])}</div>
</div>
"""


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

    # ---- Sidebar settings ----
    token = get_secret("TELEGRAM_BOT_TOKEN")
    with st.sidebar:
        st.header("⚙️ ಸೆಟ್ಟಿಂಗ್ಸ್")
        tpl_name = st.selectbox("ಸಂದೇಶ ಟೆಂಪ್ಲೇಟ್", list(TEMPLATES.keys()))
        template = TEMPLATES[tpl_name]
        show_year = st.toggle("ವರ್ಷ ತೋರಿಸಿ", value=True)
        send_image = st.toggle("ಸ್ವಯಂ ಸಂದೇಶದೊಂದಿಗೆ ಚಿತ್ರವನ್ನೂ ಕಳುಹಿಸಿ", value=True)

        st.markdown("---")
        st.subheader("📨 Telegram")
        chat_raw = st.text_area(
            "Chat ID(ಗಳು)",
            value=get_secret("TELEGRAM_CHAT_ID"),
            help="ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಇದ್ದರೆ ಕಾಮಾ (,) ಬಳಸಿ ಬೇರ್ಪಡಿಸಿ.",
            height=80,
        )
        chat_ids = parse_ids(chat_raw)
        if token:
            st.caption("✅ Bot token ಸೆಟ್ ಆಗಿದೆ (secrets)")
        else:
            st.warning("TELEGRAM_BOT_TOKEN ಸೆಟ್ ಮಾಡಿಲ್ಲ. Secrets ನಲ್ಲಿ ಸೇರಿಸಿ.")
        st.markdown("---")
        st.caption(
            f"🕙 ಪ್ರತಿದಿನ ರಾತ್ರಿ {SEND_HOUR}:00 IST ಗೆ ನಾಳೆಯ ಪಂಚಾಂಗ ಸ್ವಯಂಚಾಲಿತವಾಗಿ "
            "ಕಳುಹಿಸಲಾಗುತ್ತದೆ. ಮೊದಲು ಬೋಟ್ "
            "(`t.me/surya_panchanga_bot`) ನಲ್ಲಿ **Start** ಒತ್ತಿ."
        )

    if token and chat_ids:
        start_scheduler(token, tuple(chat_ids), template, send_image)

    # ---- Header ----
    st.title("🪔 ನಿತ್ಯ ಪಂಚಾಂಗ")

    # ---- Date navigation ----
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    if c1.button("◀ ಹಿಂದಿನ", use_container_width=True):
        st.session_state["sel_date"] = clamp(st.session_state["sel_date"] - dt.timedelta(days=1))
        st.rerun()
    if c2.button("ಇಂದು", use_container_width=True):
        st.session_state["sel_date"] = clamp(today)
        st.rerun()
    if c3.button("ನಾಳೆ", use_container_width=True):
        st.session_state["sel_date"] = clamp(today + dt.timedelta(days=1))
        st.rerun()
    if c4.button("ಮುಂದಿನ ▶", use_container_width=True):
        st.session_state["sel_date"] = clamp(st.session_state["sel_date"] + dt.timedelta(days=1))
        st.rerun()

    selected = st.date_input(
        "ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ",
        key="sel_date",
        min_value=min_d,
        max_value=max_d,
        format="DD/MM/YYYY",
    )

    row = rows.get(selected.isoformat())
    if not row:
        st.warning(f"⚠️ {selected.strftime('%d-%m-%Y')} ರ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ.")
        return

    tab_view, tab_img, tab_share = st.tabs(
        ["📖 ಪಂಚಾಂಗ", "🖼️ ಚಿತ್ರ (Image)", "📤 ಹಂಚಿಕೊಳ್ಳಿ (Text)"]
    )

    with tab_view:
        st.markdown(render_card(row, template, show_year), unsafe_allow_html=True)

    with tab_img:
        png = cached_poster(row["date"], template, show_year)
        st.image(png, use_container_width=True)
        i1, i2 = st.columns(2)
        i1.download_button(
            "⬇️ PNG ಡೌನ್‌ಲೋಡ್ (WhatsApp ಗೆ ಹಂಚಿ)",
            data=png,
            file_name=f"panchanga_{row['date']}.png",
            mime="image/png",
            use_container_width=True,
            type="primary",
        )
        if token and chat_ids:
            if i2.button("🚀 ಚಿತ್ರವನ್ನು Telegram ಗೆ ಕಳುಹಿಸಿ", use_container_width=True):
                for cid in chat_ids:
                    ok, msg = send_telegram_photo(png, token, cid, caption=row["date"])
                    (st.success if ok else st.error)(f"{cid}: {msg}")
        else:
            i2.caption("Telegram ಗೆ ಕಳುಹಿಸಲು ಸೈಡ್‌ಬಾರ್‌ನಲ್ಲಿ Chat ID ನೀಡಿ.")

    with tab_share:
        wa_text = render_message(row, template, "wa", show_year)
        tg_text = render_message(row, template, "tg", show_year)

        st.caption("ಕೆಳಗಿನ ಸಂದೇಶವನ್ನು ಬಲ ಮೂಲೆಯ 📋 ಬಟನ್‌ನಿಂದ ಕಾಪಿ ಮಾಡಬಹುದು.")
        st.code(wa_text, language=None, wrap_lines=True)

        s1, s2, s3 = st.columns(3)
        s1.link_button(
            "🟢 WhatsApp",
            "https://wa.me/?text=" + urllib.parse.quote(wa_text),
            use_container_width=True,
        )
        s2.link_button(
            "🔵 Telegram",
            "https://t.me/share/url?url=%20&text=" + urllib.parse.quote(wa_text),
            use_container_width=True,
        )
        s3.download_button(
            "💾 .txt",
            data=wa_text,
            file_name=f"panchanga_{row['date']}.txt",
            mime="text/plain",
            use_container_width=True,
        )

        st.markdown("---")
        st.subheader("🚀 Bot ಮೂಲಕ ಕಳುಹಿಸಿ")
        if not token or not chat_ids:
            st.info("ಸೈಡ್‌ಬಾರ್‌ನಲ್ಲಿ Chat ID ನಮೂದಿಸಿ ಮತ್ತು Bot Token secrets ನಲ್ಲಿ ಸೇರಿಸಿ.")
        else:
            if st.button("ಈ ದಿನದ ಪಂಚಾಂಗ ಕಳುಹಿಸಿ", type="primary", use_container_width=True):
                with st.spinner("ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ..."):
                    for cid, ok, msg in send_to_all(tg_text, token, chat_ids):
                        (st.success if ok else st.error)(f"{cid}: {msg}")


main()
