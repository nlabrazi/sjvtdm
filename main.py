import time
from collections import defaultdict

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_THINKING_LEVEL,
    GEMINI_TIMEOUT_SECONDS,
    MAX_MESSAGES_PER_MINUTE,
    MAX_MESSAGES_PER_SOURCE,
    SUMMARY_MIN_CHARACTERS,
    SUMMARY_MAX_CHARACTERS,
)
from database.db import find_sent_urls, get_db_connection, mark_articles_as_sent, setup_table
from sources.catalog import SOURCE_EMOJI_MAP, TARGET_SOURCE_KEYS
from sources.reddit_fetcher import fetch_reddit_posts
from sources.rss_fetcher import fetch_rss_articles, get_article_image
from telegram.notifier import build_message, escape_html, send_to_telegram_result
from utils.gemini_client import GeminiSummaryClient
from utils.logger import setup_logger
from utils.summarizer import generate_article_summary


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


def build_article_message(article, gemini_client=None):
    title = article.get("title", "")
    description = article.get("description") or title
    summary_raw = generate_article_summary(
        title=title,
        description=description,
        url=article.get("link", ""),
        language=article.get("language", "english"),
        min_characters=SUMMARY_MIN_CHARACTERS,
        max_characters=SUMMARY_MAX_CHARACTERS,
        gemini_client=gemini_client,
        is_discussion=article.get("is_self_post", False),
        comments=article.get("comments", []),
    )
    summary = escape_html(summary_raw)
    emoji = SOURCE_EMOJI_MAP.get(article.get("source_key", ""), "")
    return build_message(
        emoji,
        summary,
        article.get("link", ""),
        source_label=article.get("source_label", ""),
    )


def send_article_message(
    message: str,
    image_url: str = "",
) -> tuple[bool, int | None]:
    send_result = send_to_telegram_result(
        message,
        image_url=image_url,
    )
    if send_result.success:
        return True, None

    if send_result.retry_after:
        wait_seconds = max(1, send_result.retry_after)
        log.info("Retrying current Telegram message after %s second(s).", wait_seconds)
        time.sleep(wait_seconds)
        retry_result = send_to_telegram_result(
            message,
            image_url=image_url,
        )
        return retry_result.success, wait_seconds

    return False, None


def send_pending_articles():
    articles = collect_articles()
    if not articles:
        log.info("No articles fetched.")
        return 0

    source_map = group_articles_by_source(articles)
    gemini_client = GeminiSummaryClient(
        api_key=GEMINI_API_KEY,
        model=GEMINI_MODEL,
        thinking_level=GEMINI_THINKING_LEVEL,
        timeout_seconds=GEMINI_TIMEOUT_SECONDS,
    )
    sent_count = 0
    global_count = 0

    with get_db_connection() as conn:
        sent_urls = find_sent_urls(
            (article.get("link", "") for article in articles),
            conn=conn,
        )

        for source_key in TARGET_SOURCE_KEYS:
            group = source_map.get(source_key, [])
            if not group:
                continue

            source_label = group[0].get("source_label", source_key)
            source_count = 0
            source_sent_urls = []

            for article in group:
                url = (article.get("link") or "").strip()
                if not url or url in sent_urls:
                    continue

                if source_count >= MAX_MESSAGES_PER_SOURCE:
                    log.info("Per-source limit reached for %s.", source_label)
                    break

                message = build_article_message(article, gemini_client=gemini_client)
                if not message:
                    log.info("Skipped article with empty message: %s", url)
                    continue

                send_succeeded, retry_wait = send_article_message(
                    message,
                    image_url=get_article_image(article) or "",
                )
                if retry_wait:
                    global_count = 0

                if send_succeeded:
                    source_sent_urls.append(url)
                    sent_urls.add(url)
                    sent_count += 1
                    source_count += 1
                    global_count += 1

                time.sleep(1)

                if global_count >= MAX_MESSAGES_PER_MINUTE:
                    log.info("Global rate limit reached, sleeping for 60 seconds.")
                    time.sleep(60)
                    global_count = 0

            if source_sent_urls:
                mark_articles_as_sent(source_sent_urls, conn=conn)
                conn.commit()

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
