import re
from html import unescape

def clean_html(text):
    return unescape(re.sub(r"<[^>]+>", "", text))

def summarize_text(text: str, max_sentences: int = 2) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary_sentences = sentences[:max_sentences]
    return " ".join(summary_sentences)
