import re
from html import unescape
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

# Nettoyage HTML
def clean_html(text: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\s+", " ", text).strip()

# Résumé basé sur sumy (LSA)
def summarize_sumy(text: str, max_sentences: int = 3) -> str:
    parser = PlaintextParser.from_string(text, Tokenizer("french"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, max_sentences)
    return " ".join(str(sentence) for sentence in summary)

# Dédupliquer les phrases répétées (souvent entre titre/description)
def deduplicate_sentences(sentences: list) -> list:
    seen = set()
    result = []
    for s in sentences:
        normalized = s.lower().strip()
        if normalized not in seen and len(normalized) > 30:
            seen.add(normalized)
            result.append(s)
    return result

# Génération intelligente du résumé
def generate_summary(title: str, description: str, max_sentences: int = 2) -> str:
    title_clean = clean_html(title).lower()
    description_clean = clean_html(description)

    # Tentative de résumé intelligent
    try:
        summary = summarize_sumy(description_clean, max_sentences + 1)
        # Enlever phrases trop proches du titre
        summary_sentences = re.split(r'(?<=[.!?])\s+', summary)
        filtered = [
            s for s in summary_sentences
            if title_clean not in s.lower() and len(s.strip()) > 30
        ]
        deduped = deduplicate_sentences(filtered)
        return " ".join(deduped[:max_sentences])
    except Exception:
        # Fallback en cas d'erreur
        fallback = re.split(r'(?<=[.!?])\s+', description_clean)
        return " ".join(deduplicate_sentences(fallback)[:max_sentences])
