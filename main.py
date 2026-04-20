import time
from collections import defaultdict

from config import MAX_MESSAGES_PER_MINUTE, MAX_MESSAGES_PER_SOURCE
from database.db import find_sent_urls, mark_article_as_sent, setup_table
from sources.catalog import SOURCE_EMOJI_MAP, TARGET_SOURCE_KEYS
from sources.reddit_fetcher import fetch_reddit_posts
from sources.rss_fetcher import fetch_rss_articles
from telegram.notifier import build_message, escape_html, send_to_telegram
from utils.logger import setup_logger
from utils.summarizer import generate_summary


log = setup_logger("cron_push_logger", "cron_push.log")


def collect_articles():
    return fetch_rss_articles() + fetch_reddit_posts()


def group_articles_by_source(articles):
    grouped_articles = defaultdict(list)
    for article in articles:
        source_key = article.get("source_key")
        if source_key in TARGET_SOURCE_KEYS:
            grouped_articles[source_key].append(article)
    return grouped_articles


def build_article_message(article):
    title = article.get("title", "")
    description = article.get("description") or title
    summary_raw = generate_summary(
        title,
        description,
        max_sentences=2,
        language=article.get("language", "english"),
    )
    summary = escape_html(summary_raw)
    emoji = SOURCE_EMOJI_MAP.get(article.get("source_key", ""), "")
    return build_message(emoji, summary, article.get("link", ""))


def send_pending_articles():
    articles = collect_articles()
    if not articles:
        log.info("No articles fetched.")
        return 0

    sent_urls = find_sent_urls(article.get("link", "") for article in articles)
    source_map = group_articles_by_source(articles)
    sent_count = 0
    global_count = 0

    for source_key in TARGET_SOURCE_KEYS:
        group = source_map.get(source_key, [])
        if not group:
            continue

        source_label = group[0].get("source_label", source_key)
        source_count = 0

        for article in group:
            url = (article.get("link") or "").strip()
            if not url or url in sent_urls:
                continue

            if source_count >= MAX_MESSAGES_PER_SOURCE:
                log.info("Per-source limit reached for %s.", source_label)
                break

            message = build_article_message(article)
            if not message:
                log.info("Skipped article with empty message: %s", url)
                continue

            if send_to_telegram(message, preview=True):
                mark_article_as_sent(url)
                sent_urls.add(url)
                sent_count += 1
                source_count += 1
                global_count += 1

            time.sleep(1)

            if global_count >= MAX_MESSAGES_PER_MINUTE:
                log.info("Global rate limit reached, sleeping for 60 seconds.")
                time.sleep(60)
                global_count = 0

        log.info("Processed source %s: %s new article(s) sent.", source_label, source_count)
        time.sleep(10)

    log.info("Sent %s new articles to Telegram.", sent_count)
    return sent_count


def main():
    try:
        setup_table()
        send_pending_articles()
    except Exception:
        log.exception("Push job failed.")
        raise


if __name__ == "__main__":
    main()
