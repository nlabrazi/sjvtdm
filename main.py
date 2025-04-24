import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

import os
import json
import nltk
import time
import re
from html import unescape, escape

from sources.rss_fetcher import fetch_rss_articles
from sources.reddit_fetcher import fetch_reddit_posts
from utils.image_extractor import extract_image
from utils.summarizer import summarize_text
from telegram.notifier import send_to_telegram
from utils.logger import setup_logger

nltk.download("punkt", quiet=True)

log = setup_logger("cron_push_logger", "cron_push.log")

MAX_MESSAGES_PER_MINUTE = 20
MAX_MESSAGES_PER_SOURCE = 10
GLOBAL_COUNT = 0

TARGET_SOURCES = [
    "Polygon",
    "gHacks Technology News",
    "HackerNoon",
    "/r/technology",
    "/r/gaming",
    "Les Numériques - Toute l'actualité, les tests et dossiers, les bons plans"
]

def clean_html(text):
    return unescape(re.sub(r"<[^>]+>", "", text))

sent_path = "logs/sent_articles.json"
if os.path.exists(sent_path):
    with open(sent_path, "r", encoding="utf-8") as f:
        try:
            sent_links = set(json.load(f).get("links", []))
        except Exception:
            sent_links = set()
else:
    sent_links = set()

rss_articles = fetch_rss_articles()
reddit_posts = fetch_reddit_posts()
articles = rss_articles + reddit_posts

source_map = {}
for article in articles:
    source = article.get("source", "❓ Unknown")
    source_map.setdefault(source, []).append(article)

new_links = set()
sent_count = 0

for source, group in source_map.items():
    if source not in TARGET_SOURCES:
        continue

    source_count = 0

    for article in group:
        if article["link"] in sent_links:
            continue
        if source_count >= MAX_MESSAGES_PER_SOURCE:
            log.info(f"⏭️ Limite atteinte pour: {source}")
            break

        title = escape(article["title"])
        description = clean_html(article.get("description", ""))
        summary_raw = summarize_text(f"{title}. {description}", max_sentences=2)
        summary = escape(summary_raw)

        message = f"🚨 <b>{title}</b>\n\n{summary}"
        success = send_to_telegram(message, article["link"])

        if success:
            sent_count += 1
            new_links.add(article["link"])
            source_count += 1
            GLOBAL_COUNT += 1

        time.sleep(1)

        if GLOBAL_COUNT >= MAX_MESSAGES_PER_MINUTE:
            log.info("⏳ Limite globale atteinte, pause 60s.")
            time.sleep(60)
            GLOBAL_COUNT = 0

    log.info(f"⏳ Sleep après: {source}")
    time.sleep(10)

with open(sent_path, "w", encoding="utf-8") as f:
    json.dump({"links": list(sent_links.union(new_links))}, f, indent=2, ensure_ascii=False)

log.info(f"✅ Sent {sent_count} new articles to Telegram")
