import json
import unittest
from unittest.mock import patch

from telegram import notifier


class FakeResponse:
    status_code = 200

    def json(self):
        return {"ok": True}


class NotifierTests(unittest.TestCase):
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

    def test_send_to_telegram_serializes_modern_preview_options(self):
        with (
            patch.object(notifier, "BOT_TOKEN", "bot-token"),
            patch.object(notifier, "CHAT_ID", "chat-id"),
            patch.object(notifier.requests, "post", return_value=FakeResponse()) as post,
        ):
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

    def test_send_to_telegram_does_not_call_api_without_credentials(self):
        with (
            patch.object(notifier, "BOT_TOKEN", ""),
            patch.object(notifier, "CHAT_ID", ""),
            patch.object(notifier.requests, "post") as post,
        ):
            sent = notifier.send_to_telegram("Résumé")

        self.assertFalse(sent)
        post.assert_not_called()

    def test_build_message_escapes_url_query_for_html(self):
        message = notifier.build_message(
            "🧠",
            "Un résumé",
            "https://example.com/article?a=1&b=2",
        )

        self.assertIn("🧠 Un résumé", message)
        self.assertIn("a=1&amp;b=2", message)

    def test_invalid_url_is_not_injected_in_message(self):
        message = notifier.build_message("🧠", "Un résumé", "javascript:alert(1)")

        self.assertEqual(message, "🧠 Un résumé")


if __name__ == "__main__":
    unittest.main()
