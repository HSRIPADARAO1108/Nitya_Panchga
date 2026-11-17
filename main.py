import datetime as dt
import os
import csv
import io
import urllib.parse
import urllib.request
import json
import time
import threading
from zoneinfo import ZoneInfo
import streamlit as st

DATA_FILE = "panchanga_2026_2027_verified.csv"

# ---- ಹೆಡರ್ ಮತ್ತು ಫೂಟರ್ ಟೆಕ್ಸ್ಟ್ ----
HEADER = (
    "ಶ್ರೀ ಶೇಚಜಯತು : \n"
    "ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ ರ ಪರಮಾನುಗ್ರಹದಿಂದ, \n"
    "*ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ*"
)
FOOTER = "ಪಂಚಾಂಗ ಕರ್ತೃ :\nಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."
SHOW_YEAR_AFTER_WEEKDAY = True  # ದಿನಾಂಕದ ನಂತರ ವರ್ಷ ತೋರಿಸಲು


@st.cache_data
def load_rows():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def end_text(e):
    if not e or pd_isna(e):
        return ""
    if e == "AR":
        return "ಅಹೋರಾತ್ರ (ಇಡೀ ದಿನ-ರಾತ್ರಿ)"
    try:
        h, m = (int(x) for x in e.split(":"))
        if h >= 24:
            return f"ಮರುದಿನ {h - 24:02d}:{m:02d} ರವರೆಗೆ"
        return f"{h:02d}:{m:02d} ರವರೆಗೆ"
    except:
        return e


def pd_isna(val):
    return val is None or val == "" or str(val).lower() == "nan"


def limb(name, end, name2="", end2=""):
    if pd_isna(name):
        return ""
    s = f"{name} – {end_text(end)}" if not pd_isna(end) else name
    if not pd_isna(name2):
        s += f", ನಂತರ {name2} – {end_text(end2)}"
    return s


def t12(hhmm):
    if pd_isna(hhmm):
        return ""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
        return f"{(h % 12) or 12:02d}:{m:02d} {'am' if h < 12 else 'pm'}"
    except:
        return hhmm


def build_message(r):
    d = dt.date.fromisoformat(r["date"])
    year = f" {d.year}" if SHOW_YEAR_AFTER_WEEKDAY else ""
    
    # ಸೂರ್ಯಾಸ್ತದ ಫಾರ್ಮ್ಯಾಟ್ ಸರಿಪಡಿಸಲು (ಉದಾ: 6.45 pm ಅಥವಾ 18:45)
    sunset_val = t12(r['sunset'])
    
    lines = [
        HEADER,
        "",
        f"*{d.strftime('%d-%m-%Y')}*, {r['vara']}{year}",
        "",
        f"*ಸಂವತ್ಸರ:* {r['samvatsara']}",
        f"*ಆಯಣ:* {r['ayana']}",
        f"*ಋತು:* {r['ruthu']}",
        f"*ಮಾಸ:* {r['masa']}",
        f"*ಪಕ್ಷ:* {r['paksha']}",
        f"*ತಿಥಿ:* {limb(r['tithi'], r['tithi_end'], r['tithi2'], r['tithi2_end'])}",
        f"*ವಾರ:* – {r['vara']}",
        f"*ನಕ್ಷತ್ರ:* {limb(r['nakshatra'], r['nakshatra_end'], r['nakshatra2'], r['nakshatra2_end'])}",
        f"*ಯೋಗ:* {limb(r['yoga'], r['yoga_end'], r['yoga2'], r['yoga2_end'])}",
        f"*ಕರಣ:* {limb(r['karana'], r['karana_end'])}",
        f"*ಸೂರ್ಯೋದಯ:* {t12(r['sunrise'])}",
        f"*ಸೂರ್ಯಾಸ್ತ * : {sunset_val}",
        f"*ಶ್ರಾದ್ಧತಿಥಿ:* {r['shraddha_tithi']}",
    ]
    if not pd_isna(r.get("event", "")):
        lines += ["", "*ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ:*", r["event"].strip()]
    lines += ["", FOOTER]
    return "\n".join(lines)


def send_telegram(text, token, chat_id):
    if not token or not chat_id:
        return False, "Token ಅಥವಾ Chat ID നൽകಲಾಗಿಲ್ಲ."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(url, data=body)
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.load(resp)
            return res.get("ok", False), " ಯಶಸ್ವಿಯಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ!"
    except Exception as e:
        return False, f"ದೋಷ: {str(e)}"


# ---- ರಾತ್ರಿ 10 ಗಂಟೆಗೆ ಆಟೋಮ್ಯಾಟಿಕ್ ನೋಟಿಫಿಕೇಶನ್ ಕಳುಹಿಸಲು ಬ್ಯಾಕ್‌ಗ್ರೌಂಡ್ ಜಾಬ್ ----
def background_scheduler():
    while True:
        now = dt.datetime.now(ZoneInfo("Asia/Kolkata"))
        # ರಾತ್ರಿ 10:00 ಗಂಟೆಗೆ (22:00) ರನ್ ಆಗಲು
        if now.hour == 22 and now.minute == 0:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            rows = load_rows()
            
            # ನಾಳೆಯ ದಿನಾಂಕ
            tomorrow = (now + dt.timedelta(days=1)).isoformat()
            if tomorrow in rows:
                msg = build_message(rows[tomorrow])
                if token and chat_id:
                    send_telegram(msg, token, chat_id)
            time.sleep(60) # ಒಂದು ನಿಮಿಷ ಮರುಕಳಿಸದಂತೆ ತಡೆಯಲು
        time.sleep(30)


# ಆ್ಯಪ್ ಲೋಡ್ ಆದಾಗ ಬ್ಯಾಕ್‌ಗ್ರೌಂಡ್ ಥ್ರೆಡ್ ರನ್ ಮಾಡುವುದು (ಒಂದೇ ಬಾರಿ ಸ್ಟಾರ್ಟ್ ಆಗಲು)
if "scheduler_started" not in st.session_state:
    st.session_state["scheduler_started"] = True
    threading.Thread(target=background_scheduler, daemon=True).start()


# ---- Streamlit UI ವಿನ್ಯಾಸ ----
def main():
    st.set_page_config(page_title="ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ", page_icon="📅", layout="centered")
    
    st.title("☀️ ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ")
    st.write("ದಿನಾಂಕವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ ಪಂಚಾಂಗ ವೀಕ್ಷಿಸಿ ಮತ್ತು Telegram ಗೆ ಕಳುಹಿಸಿ.")

    rows = load_rows()
    if not rows:
        st.error(f"⚠️ `{DATA_FILE}` ಫೈಲ್ ಸಿಕ್ಕಿಲ್ಲ! ದಯವಿಟ್ಟು ಅದನ್ನು ಮೇನ್ ಫೋಲ್ಡರ್‌ನಲ್ಲಿ ಅಪ್ಲೋಡ್ ಮಾಡಿ.")
        return

    # ದಿನಾಂಕ ಆಯ್ಕೆ ಮಾಡುವ ವೀಜೆಟ್ (Date Selector)
    available_dates = sorted(rows.keys())
    min_date = dt.date.fromisoformat(available_dates[0])
    max_date = dt.date.fromisoformat(available_dates[-1])
    default_date = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    
    if default_date < min_date:
        default_date = min_date
    elif default_date > max_date:
        default_date = max_date

    selected_date = st.date_input(
        "ಪಂಚಾಂಗ ದಿನಾಂಕವನ್ನು ಆಯ್ಕೆಮಾಡಿ:",
        value=default_date,
        min_value=min_date,
        max_value=max_date
    )

    date_str = selected_date.isoformat()

    if date_str in rows:
        row = rows[date_str]
        message_content = build_message(row)
        
        st.subheader("📋 ಪಂಚಾಂಗ ಸಂದೇಶದ ಪೂರ್ವವೀಕ್ಷಣೆ (Preview):")
        st.code(message_content, language="markdown")
        
        st.markdown("---")
        st.subheader("🚀 Telegram ಗೆ ಕಳುಹಿಸಿ")
        
        # ಸೈಡ್‌ಬಾರ್ ಅಥವಾ ಫಾರ್ಮ್‌ನಲ್ಲಿ ಟೋಕನ್ ಹಾಗೂ ಚಾಟ್ ಐಡಿ ಪಡೆಯುವುದು
        with st.form("telegram_form"):
            st.info("ನೀವು ಕೇವಲ ಒಮ್ಮೆ ಟೋಕನ್ ಮತ್ತು ಚಾಟ್ ಐಡಿ ನಮೂದಿಸಿ ಕಳುಹಿಸಬಹುದು ಅಥವಾ Environment Variables ಬಳಸಿ.")
            bot_token_input = st.text_input("Telegram Bot Token", type="password", value=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
            chat_id_input = st.text_input("Telegram Chat ID", value=os.environ.get("TELEGRAM_CHAT_ID", ""))
            
            submit_btn = st.form_submit_button("ಈ ಪಂಚಾಂಗವನ್ನು Telegram ಗೆ ಕಳುಹಿಸಿ")
            
            if submit_btn:
                success, resp_msg = send_telegram(message_content, bot_token_input, chat_id_input)
                if success:
                    st.success(f"ಸಂದೇಶ ಯಶಸ್ವಿಯಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ!{resp_msg}")
                else:
                    st.error(f"ಕಳುಹಿಸಲು ವಿಫಲವಾಯಿತು. {resp_msg}")
    else:
        st.warning(f"⚠️ {selected_date.strftime('%d-%m-%Y')} ರ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ.")

    # ಸೈಡ್‌ಬಾರ್‌ನಲ್ಲಿ ಆಟೋಮ್ಯಾಟಿಕ್ ನೋಟಿಫಿಕೇಶನ್ ಮಾಹಿತಿ
    with st.sidebar:
        st.header("⚙️ ಆಟೋಮ್ಯಾಟಿಕ್ ನೋಟಿಫಿಕೇಶನ್")
        st.write("ಪ್ರತಿದಿನ **ರಾತ್ರಿ 10:00 ಗಂಟೆಗೆ** (IST) ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನಾಳೆಯ ದಿನದ ಪಂಚಾಂಗವು ನಿಮ್ಮ Telegram ಚಾಟ್‌ಗೆ ರವಾನೆಯಾಗುತ್ತದೆ.")
        st.markdown("---")
        st.markdown("**ಸೂಚನೆ:** ಸ್ಟ್ರೀಮ್‌ಕ್ಲೌಡ್ (Streamlit Cloud) ನಲ್ಲಿ ಆ್ಯಪ್ ನಿರಂತರವಾಗಿ ರನ್ ಆಗಲು Cloud Hosting ನ ಸೌಲಭ್ಯವಿರಬೇಕು ಅಥವಾ GitHub Actions ಬಳಸಿ ರಾತ್ರಿ 10 ಗಂಟೆಗೆ ಸ್ಕ್ರಿಪ್ಟ್ ಟ్రిಗ್ಗರ್ ಮಾಡಬಹುದು.")

if __name__ == "__main__":
    main()
