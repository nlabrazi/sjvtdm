import unittest

from telegram.notifier import build_message, sanitize_url


class NotifierTests(unittest.TestCase):
    def test_sanitize_url_rejects_non_http_schemes(self):
        self.assertEqual(sanitize_url("javascript:alert(1)"), "")

    def test_sanitize_url_escapes_quotes(self):
        sanitized = sanitize_url('https://example.com/article?q="quoted"')

        self.assertEqual(sanitized, "https://example.com/article?q=&quot;quoted&quot;")

    def test_build_message_returns_summary_only_when_url_is_invalid(self):
        message = build_message("🧠", "A useful summary", "javascript:alert(1)")

        self.assertEqual(message, "🧠 A useful summary")

