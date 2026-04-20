import unittest
import requests
from unittest.mock import Mock, patch

from telegram.notifier import build_message, sanitize_url


def build_mock_response(status_code=200, json_data=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.text = text
    if json_data is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = json_data
    return response


class NotifierTests(unittest.TestCase):
    def test_sanitize_url_rejects_non_http_schemes(self):
        self.assertEqual(sanitize_url("javascript:alert(1)"), "")

    def test_sanitize_url_escapes_quotes(self):
        sanitized = sanitize_url('https://example.com/article?q="quoted"')

        self.assertEqual(sanitized, "https://example.com/article?q=&quot;quoted&quot;")

    def test_build_message_returns_summary_only_when_url_is_invalid(self):
        message = build_message("🧠", "A useful summary", "javascript:alert(1)")

        self.assertEqual(message, "🧠 A useful summary")

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_returns_true_on_successful_api_response(self):
        response = build_mock_response(status_code=200, json_data={"ok": True, "result": {"message_id": 1}})

        with patch("telegram.notifier.SESSION.post", return_value=response):
            from telegram.notifier import send_to_telegram

            self.assertTrue(send_to_telegram("hello"))

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_result_exposes_retry_after_when_rate_limited(self):
        response = build_mock_response(
            status_code=429,
            json_data={
                "ok": False,
                "description": "Too Many Requests: retry later",
                "parameters": {"retry_after": 17},
            },
        )

        with patch("telegram.notifier.SESSION.post", return_value=response):
            from telegram.notifier import send_to_telegram_result

            send_result = send_to_telegram_result("hello")

        self.assertFalse(send_result.success)
        self.assertEqual(send_result.retry_after, 17)

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_handles_rate_limit_response(self):
        response = build_mock_response(
            status_code=429,
            json_data={
                "ok": False,
                "description": "Too Many Requests: retry later",
                "parameters": {"retry_after": 17},
            },
        )

        with patch("telegram.notifier.SESSION.post", return_value=response):
            with patch("telegram.notifier.log.warning") as mock_warning:
                from telegram.notifier import send_to_telegram

                self.assertFalse(send_to_telegram("hello"))

        mock_warning.assert_called_once()

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_handles_timeout(self):
        with patch("telegram.notifier.SESSION.post", side_effect=requests.Timeout):
            with patch("telegram.notifier.log.error") as mock_error:
                from telegram.notifier import send_to_telegram

                self.assertFalse(send_to_telegram("hello"))

        mock_error.assert_called_once()
