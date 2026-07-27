import unittest
from unittest.mock import patch

from utils import summarizer
from utils.gemini_client import GeminiSummaryError


class FakeGeminiClient:
    def __init__(self, responses, configured=True):
        self.responses = list(responses)
        self.is_configured = configured
        self.calls = []

    def summarize_url(self, **kwargs):
        self.calls.append(("url", kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def summarize_discussion(self, **kwargs):
        self.calls.append(("discussion", kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FallbackSummarizerTests(unittest.TestCase):
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

        with (
            patch(
                "utils.summarizer.summarize_sumy",
                side_effect=RuntimeError("boom"),
            ),
            patch("utils.summarizer.log.warning") as warning,
        ):
            summary = summarizer.generate_summary(
                "Title",
                description,
                max_sentences=2,
            )

        self.assertIn(
            "First fallback sentence is definitely longer than thirty characters.",
            summary,
        )
        self.assertIn(
            "Second fallback sentence is also comfortably above the length threshold.",
            summary,
        )
        warning.assert_called_once()


class ArticleSummaryTests(unittest.TestCase):
    def test_uses_gemini_summary_when_it_differs_from_preview(self):
        client = FakeGeminiClient(
            [
                "Patreon sépare désormais le calcul et l'envoi des notifications "
                "pour absorber les pics."
            ]
        )

        summary = summarizer.generate_article_summary(
            title="Patreon's legacy notification task times out",
            description="Patreon addressed a critical scalability issue.",
            url="https://example.com/patreon",
            gemini_client=client,
        )

        self.assertEqual(
            summary,
            "Patreon sépare désormais le calcul et l'envoi des notifications "
            "pour absorber les pics.",
        )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0][0], "url")

    def test_retries_once_when_first_summary_duplicates_preview(self):
        duplicate = "Patreon addressed a critical scalability issue."
        rewritten = (
            "La plateforme remplace une tâche monolithique par un traitement en deux étapes."
        )
        client = FakeGeminiClient([duplicate, rewritten])

        summary = summarizer.generate_article_summary(
            title="Notification task",
            description=duplicate,
            url="https://example.com/patreon",
            gemini_client=client,
        )

        self.assertEqual(summary, rewritten)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[1][1]["rejected_summary"], duplicate)

    def test_summarizes_reddit_discussion_from_post_and_comments(self):
        client = FakeGeminiClient(
            [
                (
                    "Un joueur raconte une période difficile durant laquelle Final Fantasy "
                    "l'aide à retrouver du réconfort. Les réponses lui témoignent leur soutien."
                )
            ]
        )

        summary = summarizer.generate_article_summary(
            title="Final Fantasy is making me happy again",
            description="The author explains how the game helps after a breakup.",
            url="https://www.reddit.com/r/gaming/comments/example",
            gemini_client=client,
            is_discussion=True,
            comments=["A supportive comment with a personal recommendation."],
        )

        self.assertIn("témoignent leur soutien", summary)
        call_type, call_args = client.calls[0]
        self.assertEqual(call_type, "discussion")
        self.assertEqual(
            call_args["comments"],
            ["A supportive comment with a personal recommendation."],
        )

    def test_discussion_fallback_includes_comments(self):
        client = FakeGeminiClient([GeminiSummaryError("quota exceeded")])

        with patch(
            "utils.summarizer.generate_summary",
            return_value="Résumé local de la discussion",
        ) as fallback:
            summary = summarizer.generate_article_summary(
                title="Discussion title",
                description="Original post body.",
                url="https://www.reddit.com/r/gaming/comments/example",
                gemini_client=client,
                is_discussion=True,
                comments=["A substantive public comment with useful context."],
            )

        self.assertEqual(summary, "Résumé local de la discussion")
        fallback.assert_called_once_with(
            "Discussion title",
            "Original post body. A substantive public comment with useful context.",
            max_sentences=3,
            language="english",
        )

    def test_falls_back_to_existing_summarizer_on_api_error(self):
        client = FakeGeminiClient([GeminiSummaryError("quota exceeded")])

        with patch(
            "utils.summarizer.generate_summary",
            return_value="Résumé de secours",
        ) as fallback:
            summary = summarizer.generate_article_summary(
                title="Title",
                description="Description suffisamment longue pour être résumée.",
                url="https://example.com/article",
                gemini_client=client,
            )

        self.assertEqual(summary, "Résumé de secours")
        fallback.assert_called_once()

    def test_falls_back_without_calling_unconfigured_client(self):
        client = FakeGeminiClient([], configured=False)

        with patch(
            "utils.summarizer.generate_summary",
            return_value="Résumé de secours",
        ):
            summary = summarizer.generate_article_summary(
                title="Title",
                description="Description",
                url="https://example.com/article",
                gemini_client=client,
            )

        self.assertEqual(summary, "Résumé de secours")
        self.assertEqual(client.calls, [])


class SimilarityTests(unittest.TestCase):
    def test_detects_exact_and_near_duplicates(self):
        self.assertTrue(
            summarizer.summaries_are_too_similar(
                "Patreon corrige un problème critique de scalabilité.",
                "Patreon corrige un problème critique de scalabilité.",
            )
        )
        self.assertTrue(
            summarizer.summaries_are_too_similar(
                "Une description assez longue pour être retrouvée telle quelle dans le texte source.",
                "Préfixe. Une description assez longue pour être retrouvée telle quelle dans le texte source.",
            )
        )

    def test_accepts_a_genuine_rewrite(self):
        self.assertFalse(
            summarizer.summaries_are_too_similar(
                "La plateforme répartit désormais les envois en deux traitements successifs.",
                "Patreon addressed a critical scalability issue with its legacy notification task.",
            )
        )


if __name__ == "__main__":
    unittest.main()
