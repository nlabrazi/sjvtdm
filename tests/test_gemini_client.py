import unittest

import requests

from utils.gemini_client import (
    GEMINI_INTERACTIONS_URL,
    GeminiSummaryClient,
    GeminiSummaryError,
    clean_generated_summary,
    is_valid_article_url,
)


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class GeminiSummaryClientTests(unittest.TestCase):
    def test_summarize_url_uses_url_context_without_storing_interaction(self):
        http_client = FakeHttpClient(
            FakeResponse(
                {
                    "status": "completed",
                    "steps": [
                        {"type": "url_context_result", "status": "success"},
                        {
                            "type": "model_output",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Résumé : Une nouvelle architecture réduit les délais de notification.",
                                }
                            ],
                        },
                    ],
                }
            )
        )
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        summary = client.summarize_url(
            "https://example.com/article",
            "Un titre",
            "Un extrait",
            max_characters=180,
        )

        self.assertEqual(summary, "Une nouvelle architecture réduit les délais de notification.")
        self.assertEqual(len(http_client.calls), 1)
        url, request = http_client.calls[0]
        self.assertEqual(url, GEMINI_INTERACTIONS_URL)
        self.assertEqual(request["headers"]["x-goog-api-key"], "secret-key")
        self.assertEqual(request["headers"]["Api-Revision"], "2026-05-20")
        self.assertEqual(request["json"]["tools"], [{"type": "url_context"}])
        self.assertFalse(request["json"]["store"])
        self.assertIn("https://example.com/article", request["json"]["input"])
        self.assertNotIn("secret-key", str(request["json"]))

    def test_summarize_url_rejects_missing_key(self):
        client = GeminiSummaryClient("")

        with self.assertRaisesRegex(GeminiSummaryError, "not configured"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_url_wraps_http_errors(self):
        http_client = FakeHttpClient(
            FakeResponse(error=requests.HTTPError("429 Too Many Requests"))
        )
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "request failed"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_url_rejects_empty_model_output(self):
        http_client = FakeHttpClient(FakeResponse({"status": "completed", "steps": []}))
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "empty summary"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_url_rejects_failed_interaction(self):
        http_client = FakeHttpClient(FakeResponse({"status": "failed", "steps": []}))
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "did not complete"):
            client.summarize_url("https://example.com/article", "Title")


class SummaryCleaningTests(unittest.TestCase):
    def test_clean_generated_summary_truncates_on_word_boundary(self):
        summary = clean_generated_summary(
            "Une phrase volontairement beaucoup trop longue pour la limite.",
            max_characters=35,
        )

        self.assertLessEqual(len(summary), 36)
        self.assertTrue(summary.endswith("…"))

    def test_article_url_requires_http_scheme_and_host(self):
        self.assertTrue(is_valid_article_url("https://example.com/news"))
        self.assertFalse(is_valid_article_url("javascript:alert(1)"))
        self.assertFalse(is_valid_article_url("https:///missing-host"))


if __name__ == "__main__":
    unittest.main()
