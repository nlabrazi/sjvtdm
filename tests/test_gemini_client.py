import unittest
from unittest.mock import Mock

import requests

from utils.gemini_client import (
    GEMINI_INTERACTIONS_URL,
    GeminiSummaryClient,
    GeminiSummaryError,
    clean_generated_summary,
    is_valid_article_url,
)
from utils.summarizer import generate_article_summary


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
    @staticmethod
    def http_error(status, headers=None):
        response = requests.Response()
        response.status_code = status
        response.url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        response.headers.update(headers or {})
        return response

    def test_two_timeouts_open_circuit_and_articles_use_fallback(self):
        http = Mock()
        http.post.side_effect = requests.ReadTimeout("secret-key in raw exception")
        client = GeminiSummaryClient("secret-key", http_client=http)

        with self.assertLogs("cron_push_logger", level="WARNING") as captured:
            for index in range(3):
                summary = generate_article_summary(
                    title="Titre",
                    description="Une description française suffisamment longue pour servir de résumé.",
                    url=f"https://example.com/{index}?token=private-token",
                    language="french",
                    min_characters=10,
                    gemini_client=client,
                )
                self.assertTrue(summary)

        self.assertEqual(http.post.call_count, 2)
        logs = "\n".join(captured.output)
        self.assertIn("category=read_timeout", logs)
        self.assertIn("duration=", logs)
        self.assertIn("circuit opened", logs)
        self.assertNotIn("secret-key", logs)
        self.assertNotIn("private-token", logs)

        new_run = GeminiSummaryClient("secret-key", http_client=http)
        with self.assertRaisesRegex(GeminiSummaryError, "read_timeout"):
            new_run.summarize_discussion("title", "body", [])
        self.assertEqual(http.post.call_count, 3)

    def test_http_auth_and_quota_open_circuit_without_exposing_response(self):
        for status in (401, 403, 404, 429):
            with self.subTest(status=status):
                response = self.http_error(status, {"Retry-After": "17"})
                response._content = b"secret-key and sensitive response"
                http = Mock()
                http.post.return_value = response
                client = GeminiSummaryClient("secret-key", http_client=http)
                with self.assertLogs("cron_push_logger", level="WARNING") as captured:
                    with self.assertRaisesRegex(GeminiSummaryError, f"HTTP {status}"):
                        client.summarize_discussion("title", "body", [])
                    with self.assertRaisesRegex(GeminiSummaryError, "circuit is open"):
                        client.summarize_discussion("title", "body", [])
                self.assertEqual(http.post.call_count, 1)
                logs = "\n".join(captured.output)
                self.assertIn(f"status={status}", logs)
                self.assertIn("retry_after=17", logs)
                self.assertNotIn("secret-key", logs)

    def test_server_errors_open_circuit_but_bad_request_does_not(self):
        http = Mock()
        http.post.side_effect = [self.http_error(400), self.http_error(503), self.http_error(503)]
        client = GeminiSummaryClient("key", http_client=http)
        for status in (400, 503, 503):
            with self.assertRaisesRegex(GeminiSummaryError, f"HTTP {status}"):
                client.summarize_discussion("title", "body", [])
        with self.assertRaisesRegex(GeminiSummaryError, "circuit is open"):
            client.summarize_discussion("title", "body", [])
        self.assertEqual(http.post.call_count, 3)

    def test_success_resets_consecutive_failures(self):
        http = Mock()
        http.post.side_effect = [
            requests.ConnectTimeout(),
            FakeResponse({"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": "Résumé valide."}]}]}),
            requests.ConnectionError(),
            FakeResponse({"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": "Autre résumé."}]}]}),
        ]
        client = GeminiSummaryClient("key", http_client=http)
        with self.assertRaisesRegex(GeminiSummaryError, "connect_timeout"):
            client.summarize_discussion("title", "body", [])
        self.assertEqual(client.summarize_discussion("title", "body", []), "Résumé valide.")
        with self.assertRaisesRegex(GeminiSummaryError, "connection"):
            client.summarize_discussion("title", "body", [])
        self.assertEqual(client.summarize_discussion("title", "body", []), "Autre résumé.")

    def test_invalid_json_is_distinguished_and_does_not_open_circuit(self):
        response = self.http_error(200)
        response._content = b"not JSON"
        http = Mock()
        http.post.return_value = response
        client = GeminiSummaryClient("key", http_client=http)
        for _ in range(3):
            with self.assertRaisesRegex(GeminiSummaryError, "invalid JSON"):
                client.summarize_discussion("title", "body", [])
        self.assertEqual(http.post.call_count, 3)

    def test_unavailable_article_does_not_open_circuit(self):
        response = FakeResponse({
            "status": "completed",
            "steps": [{"type": "url_context_result", "result": [{"status": "paywall"}]}],
        })
        http = FakeHttpClient(response)
        client = GeminiSummaryClient("key", http_client=http)
        for _ in range(3):
            with self.assertRaisesRegex(GeminiSummaryError, "could not retrieve"):
                client.summarize_url("https://example.com/article", "title")
        self.assertEqual(len(http.calls), 3)

    def test_summarize_url_uses_url_context_without_storing_interaction(self):
        http_client = FakeHttpClient(
            FakeResponse(
                {
                    "status": "completed",
                    "steps": [
                        {
                            "type": "url_context_result",
                            "result": {
                                "url": "https://example.com/article",
                                "status": "success",
                            },
                        },
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
        client = GeminiSummaryClient(
            "secret-key",
            thinking_level="medium",
            http_client=http_client,
        )

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
        self.assertEqual(
            request["json"]["generation_config"],
            {"thinking_level": "medium"},
        )
        self.assertFalse(request["json"]["store"])
        self.assertIn("https://example.com/article", request["json"]["input"])
        self.assertIn("fait principal", request["json"]["input"])
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
        http_client = FakeHttpClient(
            FakeResponse(
                {
                    "status": "completed",
                    "steps": [
                        {"type": "url_context_result", "status": "success"},
                    ],
                }
            )
        )
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "empty summary"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_url_rejects_unretrieved_article(self):
        http_client = FakeHttpClient(
            FakeResponse(
                {
                    "status": "completed",
                    "steps": [
                        {
                            "type": "url_context_result",
                            "result": {
                                "url": "https://example.com/article",
                                "status": "paywall",
                            },
                        },
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "Résumé inventé"}],
                        },
                    ],
                }
            )
        )
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "could not retrieve"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_url_rejects_failed_interaction(self):
        http_client = FakeHttpClient(FakeResponse({"status": "failed", "steps": []}))
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        with self.assertRaisesRegex(GeminiSummaryError, "did not complete"):
            client.summarize_url("https://example.com/article", "Title")

    def test_summarize_discussion_uses_post_and_comments_without_url_context(self):
        http_client = FakeHttpClient(
            FakeResponse(
                {
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Un joueur partage son expérience et reçoit "
                                        "plusieurs conseils bienveillants."
                                    ),
                                }
                            ],
                        }
                    ],
                }
            )
        )
        client = GeminiSummaryClient("secret-key", http_client=http_client)

        summary = client.summarize_discussion(
            title="A personal story",
            body="The author explains their situation.",
            comments=["A detailed and supportive public reaction."],
        )

        self.assertIn("plusieurs conseils", summary)
        request_payload = http_client.calls[0][1]["json"]
        self.assertNotIn("tools", request_payload)
        self.assertIn("The author explains their situation.", request_payload["input"])
        self.assertIn(
            "A detailed and supportive public reaction.",
            request_payload["input"],
        )


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
