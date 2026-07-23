import json
import unittest
from unittest.mock import Mock, patch

import requests

from telegram import notifier


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
        self.assertEqual(notifier.sanitize_url("javascript:alert(1)"), "")

    def test_sanitize_url_escapes_quotes(self):
        sanitized = notifier.sanitize_url('https://example.com/article?q="quoted"')

        self.assertEqual(
            sanitized,
            "https://example.com/article?q=&quot;quoted&quot;",
        )

    def test_build_message_returns_summary_only_when_url_is_invalid(self):
        message = notifier.build_message(
            "🧠",
            "A useful summary",
            "javascript:alert(1)",
        )

        self.assertEqual(message, "🧠 A useful summary")

    def test_build_link_preview_options_prefers_large_media(self):
        options = notifier.build_link_preview_options(
            preview=True,
            url="https://example.com/article",
        )

        self.assertEqual(
            options,
            {
                "is_disabled": False,
                "url": "https://example.com/article",
                "prefer_large_media": True,
                "show_above_text": False,
            },
        )

    def test_build_link_preview_options_disables_preview(self):
        self.assertEqual(
            notifier.build_link_preview_options(
                preview=False,
                url="https://example.com/article",
            ),
            {"is_disabled": True},
        )

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_serializes_modern_preview_options(self):
        response = build_mock_response(
            status_code=200,
            json_data={"ok": True, "result": {"message_id": 1}},
        )

        with patch("telegram.notifier.SESSION.post", return_value=response) as post:
            sent = notifier.send_to_telegram(
                "Résumé",
                preview=True,
                preview_url="https://example.com/article?a=1&b=2",
            )

        self.assertTrue(sent)
        payload = post.call_args.kwargs["data"]
        self.assertNotIn("disable_web_page_preview", payload)
        self.assertEqual(
            json.loads(payload["link_preview_options"]),
            {
                "is_disabled": False,
                "url": "https://example.com/article?a=1&b=2",
                "prefer_large_media": True,
                "show_above_text": False,
            },
        )

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
            send_result = notifier.send_to_telegram_result("hello")

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

        with (
            patch("telegram.notifier.SESSION.post", return_value=response),
            patch("telegram.notifier.log.warning") as warning,
        ):
            self.assertFalse(notifier.send_to_telegram("hello"))

        warning.assert_called_once()

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_handles_timeout(self):
        with (
            patch("telegram.notifier.SESSION.post", side_effect=requests.Timeout),
            patch("telegram.notifier.log.error") as error,
        ):
            self.assertFalse(notifier.send_to_telegram("hello"))

        error.assert_called_once()

    def test_send_to_telegram_does_not_call_api_without_credentials(self):
        with (
            patch.object(notifier, "BOT_TOKEN", ""),
            patch.object(notifier, "CHAT_ID", ""),
            patch.object(notifier.SESSION, "post") as post,
        ):
            sent = notifier.send_to_telegram("Résumé")

        self.assertFalse(sent)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
