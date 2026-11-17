#!/usr/bin/env python3
"""
Sends TOMORROW's Surya-Siddhanta panchanga to Telegram (plain text, so the *bold*
marks survive when you copy the message into WhatsApp).

Usage
  python send_panchanga.py                    # send tomorrow's panchanga (IST) to Telegram
  python send_panchanga.py --dry-run          # just print it
  python send_panchanga.py --dry-run --date 2026-11-18

Needs two environment variables (never put them in the code):
  TELEGRAM_BOT_TOKEN   token from @BotFather
  TELEGRAM_CHAT_ID     your chat id
"""
import argparse, csv, datetime as dt, json, os, sys, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "panchanga_2026_2027_verified.csv")

# ---- text you can edit (copied exactly as you wrote it) ---------------------------------
HEADER = (
    "ಶ್ರೀ ಶೇಚಜಯತು : \n"
    "ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ ರ ಪರಮಾನುಗ್ರಹದಿಂದ, \n"
    "*ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ*"
)
FOOTER = "ಪಂಚಾಂಗ ಕರ್ತೃ :\nಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."
SHOW_YEAR_AFTER_WEEKDAY = True      # your sample line: *04-04-2026*, ಶನಿವಾರ 2026
# ------------------------------------------------------------------------------------------


def load_rows():
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def end_text(e):
    """'08:26' -> '08:26 ರವರೆಗೆ';  '26:07' (past midnight) -> 'ಮರುದಿನ 02:07 ರವರೆಗೆ';  'AR' -> whole day+night"""
    if e == "AR":
        return "ಅಹೋರಾತ್ರ (ಇಡೀ ದಿನ-ರಾತ್ರಿ)"
    h, m = (int(x) for x in e.split(":"))
    if h >= 24:
        return f"ಮರುದಿನ {h - 24:02d}:{m:02d} ರವರೆಗೆ"
    return f"{h:02d}:{m:02d} ರವರೆಗೆ"


def limb(name, end, name2="", end2=""):
    s = f"{name} – {end_text(end)}"
    if name2:                       # the book lists two tithis / nakshatras / yogas ending on the same day
        s += f", ನಂತರ {name2} – {end_text(end2)}"
    return s


def t12(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return f"{(h % 12) or 12:02d}:{m:02d} {'am' if h < 12 else 'pm'}"


def build_message(r):
    d = dt.date.fromisoformat(r["date"])
    year = f" {d.year}" if SHOW_YEAR_AFTER_WEEKDAY else ""
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
        f"*ಸೂರ್ಯಾಸ್ತ:* {t12(r['sunset'])}",
        f"*ಶ್ರಾದ್ಧತಿಥಿ:* {r['shraddha_tithi']}",
    ]
    if r["event"].strip():
        lines += ["", "*ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ:*", r["event"].strip()]
    lines += ["", FOOTER]
    return "\n".join(lines)


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        sys.exit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first.")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()   # no parse_mode: keeps the * marks
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=30) as resp:
            ok = json.load(resp).get("ok")
    except urllib.error.HTTPError as e:
        sys.exit(f"Telegram refused the message (HTTP {e.code}). Check the bot token and chat id.")
    except Exception as e:                      # network problems etc. (the token is never printed)
        sys.exit(f"Could not reach Telegram: {type(e).__name__}")
    if not ok:
        sys.exit("Telegram did not accept the message.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="send/print this date (YYYY-MM-DD) instead of tomorrow")
    ap.add_argument("--dry-run", action="store_true", help="print the message, do not send")
    a = ap.parse_args()

    target = dt.date.fromisoformat(a.date) if a.date else (dt.datetime.now(ZoneInfo("Asia/Kolkata")).date() + dt.timedelta(days=1))
    rows = load_rows()
    row = rows.get(target.isoformat())
    if row is None:
        last = max(rows)
        msg = (f"⚠️ {target.strftime('%d-%m-%Y')} ರ ಪಂಚಾಂಗ ದತ್ತಾಂಶ ಲಭ್ಯವಿಲ್ಲ (ಕೊನೆಯ ದಿನಾಂಕ: {last}). "
               f"Panchanga data file needs the next year's pages.")
        if a.dry_run:
            print(msg)
        else:
            send_telegram(msg)
        sys.exit(1)
    msg = build_message(row)
    if a.dry_run:
        print(msg)
    else:
        send_telegram(msg)
        print("Sent panchanga for", target.isoformat())


if __name__ == "__main__":
    main()
