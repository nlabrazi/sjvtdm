import unittest
from unittest.mock import call, patch

import main
from telegram.notifier import TelegramSendResult


class MainTests(unittest.TestCase):
    class FakeConnection:
        def __init__(self):
            self.commit_count = 0

        def commit(self):
            self.commit_count += 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def test_group_articles_by_source_filters_unknown_sources(self):
        known_article = {"source_key": "polygon", "title": "Known"}
        unknown_article = {"source_key": "unknown", "title": "Unknown"}
        reddit_article = {"source_key": "reddit_gaming", "title": "Gaming"}

        grouped = main.group_articles_by_source(
            [known_article, unknown_article, reddit_article]
        )

        self.assertEqual(grouped["polygon"], [known_article])
        self.assertEqual(grouped["reddit_gaming"], [reddit_article])
        self.assertNotIn("unknown", grouped)

    def test_build_article_message_uses_gemini_service_and_catalog_emoji(self):
        article = {
            "source_key": "polygon",
            "source_label": "Polygon",
            "title": "Some title",
            "description": "Some description",
            "language": "english",
            "link": 'https://example.com/post?q="quoted"',
        }
        gemini_client = object()

        with patch(
            "main.generate_article_summary",
            return_value='5 < 6 & "quoted"',
        ) as generate:
            message = main.build_article_message(
                article,
                gemini_client=gemini_client,
            )

        self.assertIn("<b>📢 Polygon</b>", message)
        self.assertIn("5 &lt; 6 &amp; &quot;quoted&quot;", message)
        self.assertIn(
            'href="https://example.com/post?q=&quot;quoted&quot;"',
            message,
        )
        generate.assert_called_once_with(
            title="Some title",
            description="Some description",
            url='https://example.com/post?q="quoted"',
            language="english",
            min_characters=main.SUMMARY_MIN_CHARACTERS,
            max_characters=main.SUMMARY_MAX_CHARACTERS,
            gemini_client=gemini_client,
            is_discussion=False,
            comments=[],
        )

    @patch("main.time.sleep", return_value=None)
    def test_send_pending_articles_batches_sent_urls_by_source(self, _mock_sleep):
        fake_conn = self.FakeConnection()
        articles = [
            {
                "source_key": "polygon",
                "source_label": "Polygon",
                "title": "One",
                "description": "Desc one",
                "language": "english",
                "link": "https://example.com/one",
                "image": "https://images.example/one.jpg",
            },
            {
                "source_key": "polygon",
                "source_label": "Polygon",
                "title": "Two",
                "description": "Desc two",
                "language": "english",
                "link": "https://example.com/two",
                "image": "",
            },
            {
                "source_key": "reddit_gaming",
                "source_label": "/r/gaming",
                "title": "Three",
                "description": "Desc three",
                "language": "english",
                "link": "https://example.com/three",
                "image": "https://images.example/three.jpg",
            },
        ]

        with (
            patch("main.collect_articles", return_value=articles),
            patch("main.get_db_connection", return_value=fake_conn),
            patch("main.find_sent_urls", return_value=set()),
            patch("main.GeminiSummaryClient"),
            patch("main.build_article_message", return_value="message") as build,
            patch("main.send_article_message", return_value=(True, None)) as send,
            patch("main.mark_articles_as_sent") as mark,
        ):
            sent_count = main.send_pending_articles()

        self.assertEqual(sent_count, 3)
        self.assertEqual(build.call_count, 3)
        send.assert_has_calls(
            [
                call("message", image_url="https://images.example/one.jpg"),
                call("message", image_url=""),
                call("message", image_url="https://images.example/three.jpg"),
            ]
        )
        mark.assert_has_calls(
            [
                call(
                    ["https://example.com/one", "https://example.com/two"],
                    conn=fake_conn,
                ),
                call(["https://example.com/three"], conn=fake_conn),
            ]
        )
        self.assertEqual(fake_conn.commit_count, 2)

    @patch("main.time.sleep", return_value=None)
    def test_send_pending_articles_retries_current_message_after_rate_limit(
        self,
        mock_sleep,
    ):
        fake_conn = self.FakeConnection()
        article = {
            "source_key": "polygon",
            "source_label": "Polygon",
            "title": "One",
            "description": "Desc one",
            "language": "english",
            "link": "https://example.com/one",
            "image": "https://images.example/one.jpg",
        }

        with (
            patch("main.collect_articles", return_value=[article]),
            patch("main.get_db_connection", return_value=fake_conn),
            patch("main.find_sent_urls", return_value=set()),
            patch("main.GeminiSummaryClient"),
            patch("main.build_article_message", return_value="message"),
            patch(
                "main.send_to_telegram_result",
                side_effect=[
                    TelegramSendResult(success=False, retry_after=17),
                    TelegramSendResult(success=True),
                ],
            ) as send,
            patch("main.mark_articles_as_sent") as mark,
        ):
            sent_count = main.send_pending_articles()

        self.assertEqual(sent_count, 1)
        send.assert_has_calls(
            [
                call(
                    "message",
                    image_url="https://images.example/one.jpg",
                ),
                call(
                    "message",
                    image_url="https://images.example/one.jpg",
                ),
            ]
        )
        mark.assert_called_once_with(["https://example.com/one"], conn=fake_conn)
        self.assertEqual(fake_conn.commit_count, 1)
        mock_sleep.assert_has_calls([call(17), call(1), call(10)])


if __name__ == "__main__":
    unittest.main()
