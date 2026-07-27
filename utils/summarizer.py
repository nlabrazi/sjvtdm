import logging
import re
import warnings
from difflib import SequenceMatcher
from html import unescape

warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer

from utils.gemini_client import GeminiSummaryError


log = logging.getLogger("cron_push_logger")
SUPPORTED_LANGUAGES = {"english", "french"}


def clean_html(text: str | None) -> str:
    text = unescape(re.sub(r"<[^>]+>", "", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def summarize_sumy(text: str, max_sentences: int = 3, language: str = "english") -> str:
    parser = PlaintextParser.from_string(
        text,
        Tokenizer(language if language in SUPPORTED_LANGUAGES else "english"),
    )
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, max_sentences)
    return " ".join(str(sentence) for sentence in summary)


def deduplicate_sentences(sentences: list[str]) -> list[str]:
    seen = set()
    result = []
    for sentence in sentences:
        normalized = sentence.lower().strip()
        if normalized not in seen and len(normalized) > 30:
            seen.add(normalized)
            result.append(sentence)
    return result


def build_fallback_summary(title: str, description: str, max_sentences: int) -> str:
    fallback = deduplicate_sentences(split_sentences(description))
    if fallback:
        return " ".join(fallback[:max_sentences])
    return clean_html(title)


def generate_summary(
    title: str,
    description: str,
    max_sentences: int = 2,
    language: str = "english",
) -> str:
    title_clean = clean_html(title)
    description_clean = clean_html(description)

    if not description_clean:
        return title_clean

    try:
        summary = summarize_sumy(description_clean, max_sentences + 1, language=language)
        summary_sentences = split_sentences(summary)
        filtered = [
            sentence
            for sentence in summary_sentences
            if title_clean.lower() not in sentence.lower() and len(sentence.strip()) > 30
        ]
        deduped = deduplicate_sentences(filtered)
        if deduped:
            return " ".join(deduped[:max_sentences])
    except Exception as exc:
        log.warning("Sumy summarization failed, using fallback summary: %s", exc)

    fallback = build_fallback_summary(title_clean, description_clean, max_sentences)
    return fallback or title_clean


def normalize_for_comparison(text: str) -> str:
    normalized = clean_html(text).lower()
    return re.sub(r"[^\w]+", " ", normalized).strip()


def summaries_are_too_similar(summary: str, reference: str) -> bool:
    summary_normalized = normalize_for_comparison(summary)
    reference_normalized = normalize_for_comparison(reference)
    if not summary_normalized or not reference_normalized:
        return False
    if summary_normalized == reference_normalized:
        return True
    if len(summary_normalized) >= 60 and summary_normalized in reference_normalized:
        return True
    return SequenceMatcher(None, summary_normalized, reference_normalized).ratio() >= 0.88


def generate_article_summary(
    title: str,
    description: str,
    url: str,
    language: str = "english",
    max_characters: int = 480,
    gemini_client=None,
    is_discussion: bool = False,
    comments: list[str] | None = None,
) -> str:
    title_clean = clean_html(title)
    description_clean = clean_html(description)
    comments_clean = []
    for comment in comments or []:
        comment_clean = clean_html(comment)
        if comment_clean:
            comments_clean.append(comment_clean)

    if gemini_client is not None and gemini_client.is_configured:
        rejected_summary = ""
        for attempt in range(2):
            try:
                if is_discussion:
                    generated = gemini_client.summarize_discussion(
                        title=title_clean,
                        body=description_clean,
                        comments=comments_clean,
                        max_characters=max_characters,
                        rejected_summary=rejected_summary,
                    )
                else:
                    generated = gemini_client.summarize_url(
                        url=url,
                        title=title_clean,
                        excerpt=description_clean,
                        max_characters=max_characters,
                        rejected_summary=rejected_summary,
                    )
            except GeminiSummaryError as exc:
                log.warning("Gemini summary unavailable for %s: %s", url, exc)
                break

            duplicates_preview = summaries_are_too_similar(generated, description_clean)
            duplicates_title = summaries_are_too_similar(generated, title_clean)
            if not duplicates_preview and not duplicates_title:
                return generated

            if attempt == 0:
                rejected_summary = generated
                log.info("Retrying a summary too close to source metadata: %s", url)

    fallback_source = description_clean
    if is_discussion and comments_clean:
        fallback_source = " ".join([description_clean, *comments_clean])

    return generate_summary(
        title_clean,
        fallback_source,
        max_sentences=3,
        language=language,
    )
