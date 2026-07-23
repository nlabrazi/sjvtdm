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


if __name__ == "__main__":
    unittest.main()
