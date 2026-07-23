import unittest
from unittest.mock import patch

import main


class BuildArticleMessageTests(unittest.TestCase):
    def test_builds_message_from_article_summary_service(self):
        article = {
            "title": "A title",
            "description": "Feed preview",
            "link": "https://example.com/article",
            "source_key": "hackernoon",
            "language": "english",
        }
        gemini_client = object()

        with patch(
            "main.generate_article_summary",
            return_value="Un résumé réellement synthétique.",
        ) as generate:
            message = main.build_article_message(article, gemini_client=gemini_client)

        self.assertIn("🧠 Un résumé réellement synthétique.", message)
        self.assertIn("https://example.com/article", message)
        generate.assert_called_once_with(
            title="A title",
            description="Feed preview",
            url="https://example.com/article",
            language="english",
            max_characters=main.SUMMARY_MAX_CHARACTERS,
            gemini_client=gemini_client,
        )


class SendPendingArticlesTests(unittest.TestCase):
    def test_sends_explicit_article_url_to_telegram_preview(self):
        article = {
            "title": "A title",
            "description": "Feed preview",
            "link": "https://example.com/article",
            "source_key": "hackernoon",
            "source_label": "HackerNoon",
            "language": "english",
        }

        with (
            patch("main.collect_articles", return_value=[article]),
            patch("main.find_sent_urls", return_value=set()),
            patch("main.GeminiSummaryClient"),
            patch("main.build_article_message", return_value="Message") as build,
            patch("main.send_to_telegram", return_value=True) as send,
            patch("main.mark_article_as_sent") as mark,
            patch("main.time.sleep"),
        ):
            sent_count = main.send_pending_articles()

        self.assertEqual(sent_count, 1)
        build.assert_called_once()
        send.assert_called_once_with(
            "Message",
            preview=True,
            preview_url="https://example.com/article",
        )
        mark.assert_called_once_with("https://example.com/article")


if __name__ == "__main__":
    unittest.main()
