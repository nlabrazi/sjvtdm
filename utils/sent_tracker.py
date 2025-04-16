import json
import os

SENT_FILE = "sent_articles.json"

def load_sent_links() -> set:
    """Load previously sent article links."""
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return set(data)
        except json.JSONDecodeError:
            return set()

def save_sent_links(sent_links: set):
    """Save updated set of sent article links."""
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_links), f, indent=2)

def is_new_article(link: str, sent_links: set) -> bool:
    """Check if the link is new (not sent yet)."""
    return link not in sent_links
