import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

import os
import json
import nltk
import time
import re
from html import unescape

from sources.rss_fetcher import fetch_rss_articles
from sources.reddit_fetcher import fetch_reddit_posts
from utils.image_extractor import extract_image
from utils.summarizer import generate_summary
from telegram.notifier import send_to_telegram
from utils.logger import setup_logger
from database.db import setup_table, article_already_sent, mark_article_as_sent

# Setup
setup_table()
nltk.download("punkt", quiet=True)
log = setup_logger("cron_push_logger", "cron_push.log")

# Constantes
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

# Fetch articles
rss_articles = fetch_rss_articles()
reddit_posts = fetch_reddit_posts()
articles = rss_articles + reddit_posts

source_map = {}
for article in articles:
    source = article.get("source", "❓ Unknown")
    source_map.setdefault(source, []).append(article)

sent_count = 0

# Traitement par source
for source, group in source_map.items():
    if source not in TARGET_SOURCES:
        continue

    source_count = 0

    for article in group:
        url = article["link"]

        if article_already_sent(url):
            continue

        if source_count >= MAX_MESSAGES_PER_SOURCE:
            log.info(f"⏭️ Limite atteinte pour: {source}")
            break

        raw_title = article["title"]
        raw_description = article.get("description", "")

        title = clean_html(raw_title)
        description = clean_html(raw_description)

        summary_raw = generate_summary(title, description, max_sentences=2)

        def safe_escape(text):
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        summary = safe_escape(summary_raw)
        title = safe_escape(title)

        message = f"🚨 <b>{title}</b>\n\n{summary}"
        success = send_to_telegram(message, url)

        if success:
            mark_article_as_sent(url)
            sent_count += 1
            source_count += 1
            GLOBAL_COUNT += 1

        time.sleep(1)

        if GLOBAL_COUNT >= MAX_MESSAGES_PER_MINUTE:
            log.info("⏳ Limite globale atteinte, pause 60s.")
            time.sleep(60)
            GLOBAL_COUNT = 0

    log.info(f"⏳ Sleep après: {source}")
    time.sleep(10)

log.info(f"✅ Sent {sent_count} new articles to Telegram")
