import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
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

