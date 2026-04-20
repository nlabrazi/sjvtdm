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

        grouped = main.group_articles_by_source([known_article, unknown_article, reddit_article])

        self.assertEqual(grouped["polygon"], [known_article])
        self.assertEqual(grouped["reddit_gaming"], [reddit_article])
        self.assertNotIn("unknown", grouped)

    @patch("main.generate_summary", return_value='5 < 6 & "quoted"')
    def test_build_article_message_uses_catalog_emoji_and_escapes_summary(self, _mock_generate_summary):
        article = {
            "source_key": "polygon",
            "title": "Some title",
            "description": "Some description",
            "language": "english",
            "link": 'https://example.com/post?q="quoted"',
        }

        message = main.build_article_message(article)

        self.assertIn("📢 5 &lt; 6 &amp; &quot;quoted&quot;", message)
        self.assertIn('href="https://example.com/post?q=&quot;quoted&quot;"', message)

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
            },
            {
                "source_key": "polygon",
                "source_label": "Polygon",
                "title": "Two",
                "description": "Desc two",
                "language": "english",
                "link": "https://example.com/two",
            },
            {
                "source_key": "reddit_gaming",
                "source_label": "/r/gaming",
                "title": "Three",
                "description": "Desc three",
                "language": "english",
                "link": "https://example.com/three",
            },
        ]

        with patch("main.collect_articles", return_value=articles):
            with patch("main.get_db_connection", return_value=fake_conn):
                with patch("main.find_sent_urls", return_value=set()):
                    with patch("main.build_article_message", return_value="message"):
                        with patch("main.send_article_message", return_value=(True, None)):
                            with patch("main.mark_articles_as_sent") as mock_mark_articles_as_sent:
                                sent_count = main.send_pending_articles()

        self.assertEqual(sent_count, 3)
        mock_mark_articles_as_sent.assert_has_calls(
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
    def test_send_pending_articles_retries_current_message_after_telegram_retry_after(self, mock_sleep):
        fake_conn = self.FakeConnection()
        articles = [
            {
                "source_key": "polygon",
                "source_label": "Polygon",
                "title": "One",
                "description": "Desc one",
                "language": "english",
                "link": "https://example.com/one",
            },
        ]

        with patch("main.collect_articles", return_value=articles):
            with patch("main.get_db_connection", return_value=fake_conn):
                with patch("main.find_sent_urls", return_value=set()):
                    with patch("main.build_article_message", return_value="message"):
                        with patch(
                            "main.send_to_telegram_result",
                            side_effect=[
                                TelegramSendResult(success=False, retry_after=17),
                                TelegramSendResult(success=True),
                            ],
                        ) as mock_send_to_telegram_result:
                            with patch("main.mark_articles_as_sent") as mock_mark_articles_as_sent:
                                sent_count = main.send_pending_articles()

        self.assertEqual(sent_count, 1)
        self.assertEqual(mock_send_to_telegram_result.call_count, 2)
        mock_mark_articles_as_sent.assert_called_once_with(["https://example.com/one"], conn=fake_conn)
        self.assertEqual(fake_conn.commit_count, 1)
        mock_sleep.assert_has_calls([call(17), call(1), call(10)])
