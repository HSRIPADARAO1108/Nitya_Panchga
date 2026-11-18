import datetime as dt
import os
import csv
import urllib.parse
import urllib.request
import json
from zoneinfo import ZoneInfo

DATA_FILE = "panchanga_2026_2027_verified.csv"

HEADER = (
    "ಶ್ರೀ ಶೇಚಜಯತು : \n"
    "ಶ್ರೀ ಶ್ರೀಪಾದರಾಜ , ಶ್ರೀ ರಾಘವೇಂದ್ರ ತೀರ್ಥರು , ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಕೇಶವನಿಧಿ ತೀರ್ಥರು ಪರಮಾನುಗ್ರಹದಿಂದ, \n"
    "*ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ*"
)
FOOTER = "ಪಂಚಾಂಗ ಕರ್ತೃ :\nಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."
SHOW_YEAR_AFTER_WEEKDAY = True

def load_rows():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}

def pd_isna(val):
    return val is None or val == "" or str(val).lower() == "nan"

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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(url, data=body)
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.load(resp)
            return res.get("ok", False)
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Missing Telegram Token or Chat ID")
        return

    rows = load_rows()
    # Fixed date extraction to match CSV format (YYYY-MM-DD)
    now = dt.datetime.now(ZoneInfo("Asia/Kolkata"))
    tomorrow = (now + dt.timedelta(days=1)).date().isoformat()
    
    if tomorrow in rows:
        msg = build_message(rows[tomorrow])
        success = send_telegram(msg, token, chat_id)
        if success:
            print("Successfully sent tomorrow's panchanga!")
        else:
            print("Failed to send message.")
    else:
        print(f"No panchanga data found for tomorrow: {tomorrow}")

if __name__ == "__main__":
    main()
