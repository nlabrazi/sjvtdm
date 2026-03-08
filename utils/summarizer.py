import warnings
import re
from html import unescape

warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

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
    except Exception:
        pass

    fallback = build_fallback_summary(title_clean, description_clean, max_sentences)
    return fallback or title_clean
