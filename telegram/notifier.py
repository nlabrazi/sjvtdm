import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_to_telegram(message: str) -> bool:
    """
    Send a message to the configured Telegram channel.
    Returns True if successful, False otherwise.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
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
            print("✅ Message sent to Telegram.")
            return True
        else:
            print("❌ Failed to send message:", result)
            return False
    except Exception as e:
        print("❌ Exception while sending message:", e)
        return False

def send_error_alert(error_msg: str) -> bool:
    """
    Send an alert message to Telegram in case of error.
    """
    alert_message = f"⚠️ *SJVTDM Error Alert*\n```{error_msg}```"
    return send_to_telegram(alert_message)
