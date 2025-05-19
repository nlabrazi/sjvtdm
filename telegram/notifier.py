import os
import requests
from dotenv import load_dotenv
from html import escape
from utils.logger import setup_logger

if not os.getenv("TELEGRAM_BOT_TOKEN"):
    load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

log = setup_logger("bot_logger", "bot.log")


def escape_html(text: str) -> str:
    return escape(text)


def send_image_with_caption(image_url: str, caption: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
        return False

    payload = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=payload)
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            log.info(f"✅ Image message sent to Telegram.")
            return True
        else:
            log.error(f"❌ Failed to send image: {result}")
            return False
    except Exception as e:
        log.exception(f"❌ Exception while sending image: {e}")
        return False


def send_to_telegram(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
        return False

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            preview = message.replace("\n", " ")[:100] + "..." if len(message) > 100 else message
            log.info(f"✅ Message sent to Telegram: {preview}")
            return True
        else:
            log.error(f"❌ Failed to send message: {result}")
            return False
    except Exception as e:
        log.exception(f"❌ Exception while sending message: {e}")
        return False


def send_error_alert(error_msg: str) -> bool:
    alert = f"<b>SJVTDM Error Alert</b>\n<pre>{escape_html(error_msg)}</pre>"
    return send_to_telegram(alert)


def build_caption(emoji: str, summary: str, url: str) -> str:
    summary_clean = summary.strip()
    if not summary_clean:
        return ""

    if emoji:
        summary_line = f"{emoji} {summary_clean}"
    else:
        summary_line = summary_clean

    return f"{summary_line}\n\n<a href=\"{url}\">🔗 Lire l'article complet</a>"
