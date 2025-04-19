import os
import requests
from dotenv import load_dotenv
from utils.logger import setup_logger

# 📥 Load .env only if local
if not os.getenv("TELEGRAM_BOT_TOKEN"):
    load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

log = setup_logger("bot_logger", "bot.log")

def send_to_telegram(message: str) -> bool:
    """
    Send a message to the configured Telegram channel.
    Returns True if successful, False otherwise.
    """
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
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
    """
    Send an alert message to Telegram in case of error.
    """
    alert_message = f"⚠️ *SJVTDM Error Alert*\n```{error_msg}```"
    return send_to_telegram(alert_message)
