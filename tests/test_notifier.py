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

    def test_build_message_displays_escaped_source_in_header(self):
        message = notifier.build_message(
            "📢",
            "Un résumé utile.",
            "https://example.com/article",
            source_label="Polygon & partners",
        )

        self.assertEqual(
            message,
            "<b>📢 Polygon &amp; partners</b>\n\n"
            "Un résumé utile.\n\n"
            '<a href="https://example.com/article">🔗 Lire l\'article complet</a>',
        )

    def test_build_photo_payload_uses_image_and_caption(self):
        self.assertEqual(
            notifier.build_photo_payload(
                "Résumé avec lien",
                "https://images.example/article.jpg",
            ),
            {
                "chat_id": notifier.CHAT_ID,
                "photo": "https://images.example/article.jpg",
                "caption": f"Résumé avec lien\n\n{notifier.PHOTO_SEPARATOR}",
                "parse_mode": "HTML",
                "show_caption_above_media": True,
            },
        )

    def test_build_photo_payload_rejects_invalid_image_url(self):
        with patch("telegram.notifier.log.warning") as warning:
            payload = notifier.build_photo_payload("Résumé", "file:///tmp/image.jpg")

        self.assertIsNone(payload)
        warning.assert_called_once()

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_sends_remote_photo_with_caption(self):
        response = build_mock_response(
            status_code=200,
            json_data={"ok": True, "result": {"message_id": 1}},
        )

        with patch("telegram.notifier.SESSION.post", return_value=response) as post:
            sent = notifier.send_to_telegram(
                "Résumé",
                image_url="https://images.example/article.jpg",
            )

        self.assertTrue(sent)
        self.assertTrue(post.call_args.args[0].endswith("/sendPhoto"))
        payload = post.call_args.kwargs["data"]
        self.assertEqual(payload["photo"], "https://images.example/article.jpg")
        self.assertEqual(
            payload["caption"],
            f"Résumé\n\n{notifier.PHOTO_SEPARATOR}",
        )
        self.assertTrue(payload["show_caption_above_media"])
        self.assertNotIn("link_preview_options", payload)

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_send_to_telegram_without_image_disables_link_preview(self):
        response = build_mock_response(
            status_code=200,
            json_data={"ok": True, "result": {"message_id": 1}},
        )

        with patch("telegram.notifier.SESSION.post", return_value=response) as post:
            sent = notifier.send_to_telegram("Résumé")

        self.assertTrue(sent)
        self.assertTrue(post.call_args.args[0].endswith("/sendMessage"))
        payload = post.call_args.kwargs["data"]
        self.assertEqual(
            json.loads(payload["link_preview_options"]),
            {"is_disabled": True},
        )

    @patch("telegram.notifier.BOT_TOKEN", "token")
    @patch("telegram.notifier.CHAT_ID", "chat")
    def test_invalid_remote_photo_falls_back_to_text_message(self):
        photo_error = build_mock_response(
            status_code=400,
            json_data={"ok": False, "description": "Bad Request: failed to get HTTP URL content"},
        )
        text_success = build_mock_response(
            status_code=200,
            json_data={"ok": True, "result": {"message_id": 1}},
        )

        with (
            patch(
                "telegram.notifier.SESSION.post",
                side_effect=[photo_error, text_success],
            ) as post,
            patch("telegram.notifier.log.warning") as warning,
        ):
            result = notifier.send_to_telegram_result(
                "Résumé",
                image_url="https://images.example/unavailable.jpg",
            )

        self.assertTrue(result.success)
        self.assertEqual(post.call_count, 2)
        self.assertTrue(post.call_args_list[0].args[0].endswith("/sendPhoto"))
        self.assertTrue(post.call_args_list[1].args[0].endswith("/sendMessage"))
        warning.assert_called_once()

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
    def test_photo_rate_limit_does_not_fall_back_to_text(self):
        response = build_mock_response(
            status_code=429,
            json_data={
                "ok": False,
                "description": "Too Many Requests: retry later",
                "parameters": {"retry_after": 17},
            },
        )

        with patch("telegram.notifier.SESSION.post", return_value=response) as post:
            result = notifier.send_to_telegram_result(
                "Résumé",
                image_url="https://images.example/article.jpg",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.retry_after, 17)
        self.assertEqual(post.call_count, 1)

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
