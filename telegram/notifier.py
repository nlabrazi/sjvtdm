import json
from dataclasses import dataclass
from html import escape
from urllib.parse import urlparse

import requests

from config import HTTP_TIMEOUT_SECONDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import setup_logger


BOT_TOKEN = TELEGRAM_BOT_TOKEN
CHAT_ID = TELEGRAM_CHAT_ID
SESSION = requests.Session()

log = setup_logger("bot_logger", "bot.log")


@dataclass(frozen=True)
class TelegramSendResult:
    success: bool
    retry_after: int | None = None


def escape_html(text: str) -> str:
    return escape(text)


def is_valid_url(url: str) -> bool:
    candidate = (url or "").strip()
    if not candidate:
        return False
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def sanitize_url(url: str) -> str:
    candidate = (url or "").strip()
    if not is_valid_url(candidate):
        if candidate:
            log.warning("Skipping invalid article URL: %s", candidate)
        return ""
    return escape(candidate, quote=True)


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


def parse_json_response(response: requests.Response) -> dict:
    try:
        parsed = response.json()
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_response_details(response: requests.Response, result: dict) -> str:
    description = result.get("description")
    if description:
        return str(description)

    body = (response.text or "").strip()
    if body:
        return body[:200]
    return f"HTTP {response.status_code}"


def send_to_telegram_result(
    message: str,
    preview: bool = False,
    preview_url: str = "",
) -> TelegramSendResult:
    if not BOT_TOKEN or not CHAT_ID:
        log.error("❌ Missing BOT_TOKEN or CHAT_ID in .env file.")
        return TelegramSendResult(success=False)

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "link_preview_options": json.dumps(
            build_link_preview_options(preview=preview, url=preview_url)
        ),
    }

    try:
        response = SESSION.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        result = parse_json_response(response)
        if response.status_code == 200 and result.get("ok"):
            preview_msg = message.replace("\n", " ")[:100] + "..." if len(message) > 100 else message
            log.info("✅ Message sent to Telegram: %s", preview_msg)
            return TelegramSendResult(success=True)

        details = build_response_details(response, result)
        retry_after = result.get("parameters", {}).get("retry_after")
        if response.status_code == 429 and retry_after:
            log.warning(
                "❌ Telegram rate limit hit. Retry after %s second(s): %s",
                retry_after,
                details,
            )
            return TelegramSendResult(success=False, retry_after=int(retry_after))

        log.error(
            "❌ Failed to send Telegram message (status=%s): %s",
            response.status_code,
            details,
        )
        return TelegramSendResult(success=False)
    except requests.Timeout:
        log.error("❌ Telegram request timed out after %s second(s).", HTTP_TIMEOUT_SECONDS)
        return TelegramSendResult(success=False)
    except requests.RequestException as exc:
        log.error("❌ Telegram request failed: %s", exc)
        return TelegramSendResult(success=False)


def send_to_telegram(message: str, preview: bool = False, preview_url: str = "") -> bool:
    return send_to_telegram_result(
        message,
        preview=preview,
        preview_url=preview_url,
    ).success


def send_error_alert(error_msg: str) -> bool:
    alert = f"<b>SJVTDM Error Alert</b>\n<pre>{escape_html(error_msg)}</pre>"
    return send_to_telegram(alert, preview=False)


def build_message(emoji: str, summary: str, url: str) -> str:
    summary_clean = summary.strip()
    if not summary_clean:
        return ""

    summary_line = f"{emoji} {summary_clean}" if emoji else summary_clean
    safe_url = sanitize_url(url)
    if not safe_url:
        return summary_line

    return f"{summary_line}\n\n<a href=\"{safe_url}\">🔗 Lire l'article complet</a>"
