"""
Shared logic for the Surya-Siddhanta Nitya Panchanga app and the daily Telegram sender:
loading the data, building the message from a template, and sending it to Telegram.
"""
import csv
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "panchanga_2026_2027_verified.csv")
IST = ZoneInfo("Asia/Kolkata")

# ---- text you can edit (copied exactly as you wrote it) --------------------------------
DEFAULT_HEADER = (
    "ಶ್ರೀ ಶೇಚಜಯತು : \n"
    "ಶ್ರೀ ಸುಧರ್ಮೇoದ್ರ ತೀರ್ಥರ , ಶ್ರೀ ಸುಶೀಲೆಂದ್ರ ತೀರ್ಥರ ರ ಪರಮಾನುಗ್ರಹದಿಂದ, \n"
    "*ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ*"
)
DEFAULT_FOOTER = "ಪಂಚಾಂಗ ಕರ್ತೃ :\nಅಲ್ಲಿಪುರ ವಾದಿರಾಜ ಆಚಾರ್."
# -----------------------------------------------------------------------------------------

KN_MONTHS = ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್",
             "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"]


@dataclass
class Options:
    style: str = "full"            # "full" (your format) or "short"
    show_header: bool = True
    show_footer: bool = True
    show_year: bool = True         # your sample line: *04-04-2026*, ಶನಿವಾರ 2026
    show_sun: bool = True
    show_shraddha: bool = True
    show_event: bool = True
    header: str = DEFAULT_HEADER
    footer: str = DEFAULT_FOOTER


class TelegramError(Exception):
    pass


def now_ist():
    return dt.datetime.now(IST)


def load_rows():
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def blank(v):
    return v is None or str(v).strip() == "" or str(v).lower() == "nan"


def end_text(e):
    """'08:26' -> '08:26 ರವರೆಗೆ' ; '26:07' (after midnight) -> 'ಮರುದಿನ 02:07 ರವರೆಗೆ' ; 'AR' -> whole day and night"""
    if blank(e):
        return ""
    if e == "AR":
        return "ಅಹೋರಾತ್ರ (ಇಡೀ ದಿನ-ರಾತ್ರಿ)"
    h, m = (int(x) for x in e.split(":"))
    if h >= 24:
        return f"ಮರುದಿನ {h - 24:02d}:{m:02d} ರವರೆಗೆ"
    return f"{h:02d}:{m:02d} ರವರೆಗೆ"


def limb(name, end, name2="", end2=""):
    s = f"{name} – {end_text(end)}" if not blank(end) else name
    if not blank(name2):          # the book lists two tithis / nakshatras / yogas ending on the same day
        s += f", ನಂತರ {name2} – {end_text(end2)}"
    return s


def t12(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return f"{(h % 12) or 12:02d}:{m:02d} {'am' if h < 12 else 'pm'}"


def build_message(r, opt=None):
    opt = opt or Options()
    d = dt.date.fromisoformat(r["date"])
    date_s = d.strftime("%d-%m-%Y")
    tithi = limb(r["tithi"], r["tithi_end"], r["tithi2"], r["tithi2_end"])
    nak = limb(r["nakshatra"], r["nakshatra_end"], r["nakshatra2"], r["nakshatra2_end"])
    yoga = limb(r["yoga"], r["yoga_end"], r["yoga2"], r["yoga2_end"])
    karana = limb(r["karana"], r["karana_end"])
    event = (r.get("event") or "").strip()

    if opt.style == "short":
        lines = []
        if opt.show_header:
            lines.append("*ಸೂರ್ಯಸಿದ್ಧಾಂತ ನಿತ್ಯ ಪಂಚಾಂಗ*")
        lines += [
            f"*{date_s}*, {r['vara']}",
            f"{r['samvatsara']} ಸಂವತ್ಸರ · {r['ayana']} · {r['ruthu']} ಋತು",
            f"{r['masa']} ಮಾಸ · {r['paksha']} ಪಕ್ಷ",
            "",
            f"*ತಿಥಿ:* {tithi}",
            f"*ನಕ್ಷತ್ರ:* {nak}",
            f"*ಯೋಗ:* {yoga}",
            f"*ಕರಣ:* {karana}",
        ]
        if opt.show_sun:
            lines.append(f"*ಸೂರ್ಯೋದಯ:* {t12(r['sunrise'])} · *ಸೂರ್ಯಾಸ್ತ:* {t12(r['sunset'])}")
        if opt.show_shraddha:
            lines.append(f"*ಶ್ರಾದ್ಧತಿಥಿ:* {r['shraddha_tithi']}")
        if opt.show_event and event:
            lines += ["", f"*ವಿಶೇಷ:* {event}"]
        return "\n".join(lines)

    # ---- full template (your format) ----
    year = f" {d.year}" if opt.show_year else ""
    lines = []
    if opt.show_header:
        lines += [opt.header, ""]
    lines += [
        f"*{date_s}*, {r['vara']}{year}",
        "",
        f"*ಸಂವತ್ಸರ:* {r['samvatsara']}",
        f"*ಆಯಣ:* {r['ayana']}",
        f"*ಋತು:* {r['ruthu']}",
        f"*ಮಾಸ:* {r['masa']}",
        f"*ಪಕ್ಷ:* {r['paksha']}",
        f"*ತಿಥಿ:* {tithi}",
        f"*ವಾರ:* – {r['vara']}",
        f"*ನಕ್ಷತ್ರ:* {nak}",
        f"*ಯೋಗ:* {yoga}",
        f"*ಕರಣ:* {karana}",
    ]
    if opt.show_sun:
        lines += [f"*ಸೂರ್ಯೋದಯ:* {t12(r['sunrise'])}",
                  f"*ಸೂರ್ಯಾಸ್ತ:* {t12(r['sunset'])}"]      # no space before the closing * (WhatsApp needs that for bold)
    if opt.show_shraddha:
        lines.append(f"*ಶ್ರಾದ್ಧತಿಥಿ:* {r['shraddha_tithi']}")
    if opt.show_event and event:
        lines += ["", "*ಧರ್ಮಶಾಸ್ತ್ರ ವಿಚಾರ:*", event]
    if opt.show_footer:
        lines += ["", opt.footer]
    return "\n".join(lines)


def send_telegram(text, token, chat_id):
    """Plain text on purpose (no parse_mode) so the *bold* marks survive when copied into WhatsApp."""
    if not token or not chat_id:
        raise TelegramError("Bot token / Chat ID ಇಲ್ಲ (missing).")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks, cur = [], ""
    for line in text.split("\n"):                 # Telegram limit is 4096 characters per message
        if len(cur) + len(line) + 1 > 3800 and cur:
            chunks.append(cur); cur = ""
        cur += line + "\n"
    chunks.append(cur.rstrip("\n"))
    for part in chunks:
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": part}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=30) as resp:
                if not json.load(resp).get("ok"):
                    raise TelegramError("Telegram did not accept the message.")
        except urllib.error.HTTPError as e:
            try:
                why = json.loads(e.read().decode()).get("description", "")
            except Exception:
                why = ""
            raise TelegramError(f"Telegram error {e.code}: {why}") from None
        except TelegramError:
            raise
        except Exception as e:                    # network problems etc. (the token is never included)
            raise TelegramError(f"Could not reach Telegram ({type(e).__name__}).") from None
