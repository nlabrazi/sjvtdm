import unittest
from unittest.mock import patch

from utils import summarizer


class SummarizerTests(unittest.TestCase):
    def test_clean_html_strips_tags_and_normalizes_whitespace(self):
        cleaned = summarizer.clean_html(" <p>Hello</p>\n\n  <b>world</b> ")

        self.assertEqual(cleaned, "Hello world")

    def test_generate_summary_returns_title_when_description_is_empty(self):
        summary = summarizer.generate_summary("A short title", "")

        self.assertEqual(summary, "A short title")

    def test_generate_summary_logs_and_uses_fallback_when_sumy_fails(self):
        description = (
            "<p>First fallback sentence is definitely longer than thirty characters. "
            "Second fallback sentence is also comfortably above the length threshold.</p>"
        )

        with patch("utils.summarizer.summarize_sumy", side_effect=RuntimeError("boom")):
            with patch("utils.summarizer.log.warning") as mock_warning:
                summary = summarizer.generate_summary("Title", description, max_sentences=2)

        self.assertIn("First fallback sentence is definitely longer than thirty characters.", summary)
        self.assertIn("Second fallback sentence is also comfortably above the length threshold.", summary)
        mock_warning.assert_called_once()
