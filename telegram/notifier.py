import json
import requests
from html import escape
from urllib.parse import urlparse

from config import HTTP_TIMEOUT_SECONDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import setup_logger

BOT_TOKEN = TELEGRAM_BOT_TOKEN
CHAT_ID = TELEGRAM_CHAT_ID

log = setup_logger("bot_logger", "bot.log")


def escape_html(text: str) -> str:
    return escape(text)


def sanitize_url(url: str) -> str:
    candidate = (url or "").strip()
    if not is_valid_url(candidate):
        log.warning("Skipping invalid article URL: %s", candidate)
        return ""

    return escape(candidate, quote=True)


def is_valid_url(url: str) -> bool:
    candidate = (url or "").strip()
    if not candidate:
        return False
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_link_preview_options(preview: bool, url: str = "") -> dict:
    if not preview:
        return {"is_disabled": True}

    options = {"is_disabled": False}
    candidate = (url or "").strip()
    if is_valid_url(candidate):
        options.update(
            {
                "url": candidate,
                "prefer_large_media": True,
                "show_above_text": False,
            }
        )
    return options


def send_to_telegram(message: str, preview: bool = False, preview_url: str = "") -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
        return False

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "link_preview_options": json.dumps(
            build_link_preview_options(preview=preview, url=preview_url)
        ),
    }

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        try:
            result = response.json()
        except ValueError:
            result = {"ok": False, "description": response.text[:200]}
        if response.status_code == 200 and result.get("ok"):
            preview_msg = message.replace("\n", " ")[:100] + "..." if len(message) > 100 else message
            log.info(f"✅ Message sent to Telegram: {preview_msg}")
            return True
        else:
            log.error(f"❌ Failed to send message: {result}")
            return False
    except Exception as e:
        log.exception(f"❌ Exception while sending message: {e}")
        return False


def send_error_alert(error_msg: str) -> bool:
    alert = f"<b>SJVTDM Error Alert</b>\n<pre>{escape_html(error_msg)}</pre>"
    return send_to_telegram(alert, preview=False)


def build_message(emoji: str, summary: str, url: str) -> str:
    summary_clean = summary.strip()
    if not summary_clean:
        return ""

    if emoji:
        summary_line = f"{emoji} {summary_clean}"
    else:
        summary_line = summary_clean

    safe_url = sanitize_url(url)
    if not safe_url:
        return summary_line

    return f"{summary_line}\n\n<a href=\"{safe_url}\">🔗 Lire l'article complet</a>"
