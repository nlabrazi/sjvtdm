import os
import time
from collections import defaultdict

from sources.rss_fetcher import fetch_rss_articles
from sources.reddit_fetcher import fetch_reddit_posts
from sources.twitter_fetcher import fetch_twitter_posts
from telegram.notifier import send_to_telegram, send_error_alert
from utils.sent_tracker import load_sent_links, save_sent_links, is_new_article
from utils.logger import setup_logger

# ⏺️ Loggers
bot_log = setup_logger("bot_logger", "bot.log")
cron_log = setup_logger("cron_logger", "cron.log")

# 🎨 Source display formats
SOURCE_FORMATS = {
    "Polygon": "🎮 *🧠 Insights from Polygon Gaming News*",
    "gHacks Technology News": "🛠️ *gHacks: Tech Tips & Software Alerts*",
    "/r/Technology": "💻 *Reddit Tech Highlights*",
    "r/gaming": "🎮 *Reddit Gamers Speak!*",
    "HackerNoon": "📗 *HackerNoon: Dev, Crypto & Startups*",
    "Les Numériques": "📸 *Le top de l'actu high-tech*",
    "SaudiNewsFR": "🇸🇦 *Dernières nouvelles de SaudiNewsFR*",
    "Le360fr": "🌍 *Actu Maroc : Le360fr*",
}

def format_articles(grouped_articles):
    messages = []
    for source, items in grouped_articles.items():
        title = SOURCE_FORMATS.get(source, f"📌 *{source}*")
        header = f"{title} — `{len(items)} article{'s' if len(items) > 1 else ''}`"
        body = "\n".join(f"→ [{a['title']}]({a['link']})" for a in items)
        messages.append(f"{header}\n\n{body}\n───────────────")
    return messages

def main():
    bot_log.info("SJVTDM bot started")
    cron_log.info("🔁 Cron started")

    sent_links = load_sent_links()
    all_articles = []

    rss_articles = fetch_rss_articles()
    bot_log.info(f"Fetched {len(rss_articles)} article(s) from RSS")
    all_articles.extend(rss_articles)

    twitter_articles = fetch_twitter_posts()
    bot_log.info(f"Fetched {len(twitter_articles)} tweet(s)")
    all_articles.extend(twitter_articles)

    reddit_articles = fetch_reddit_posts()
    bot_log.info(f"Fetched {len(reddit_articles)} reddit post(s)")
    all_articles.extend(reddit_articles)

    new_articles = [a for a in all_articles if is_new_article(a["link"], sent_links)]
    bot_log.info(f"Total fetched: {len(all_articles)} | New: {len(new_articles)}")
    cron_log.info(f"📰 {len(new_articles)} new article(s)")

    if not new_articles:
        bot_log.info("No new articles to send")
        cron_log.info("✅ No new articles to post")
    else:
        total_count = len(new_articles)
        send_to_telegram(
            f"👋 *Hey there! Your SJVTDM digest is ready!*\n\n"
            f"📰 *{total_count} new article{'s' if total_count > 1 else ''} just landed — enjoy the read!*\n"
        )
        time.sleep(1.5)

        grouped = defaultdict(list)
        for article in new_articles:
            grouped[article["source"]].append(article)

        for message in format_articles(grouped):
            try:
                success = send_to_telegram(message)
                time.sleep(1.5)
                if success:
                    for article in new_articles:
                        if article["link"] in message:
                            sent_links.add(article["link"])
                            bot_log.info(f"Sent: {article['title']}")
                else:
                    raise Exception("send_to_telegram returned False")
            except Exception as e:
                error_text = f"Failed to send message block."
                bot_log.error(f"{error_text} | Reason: {e}")
                send_error_alert(error_text)

        send_to_telegram("\n✅ *That's all for now — see you in the next update!* 👋")
        cron_log.info("✅ Digest sent to Telegram")

    save_sent_links(sent_links)
    bot_log.info("SJVTDM bot finished")
    cron_log.info("✅ Cron finished\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        bot_log.exception("CRITICAL ERROR in bot")
        send_error_alert(f"Unhandled exception: {e}")
