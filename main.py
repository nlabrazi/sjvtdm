import os
import logging
from collections import defaultdict

from sources.rss_fetcher import fetch_rss_articles
from telegram.notifier import send_to_telegram, send_error_alert
from utils.sent_tracker import load_sent_links, save_sent_links, is_new_article

# 🔧 Assure-toi que le dossier logs/ existe
os.makedirs("logs", exist_ok=True)

# 🔎 Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("sjvtdm")

def main():
    log.info("SJVTDM bot started")

    sent_links = load_sent_links()
    articles = fetch_rss_articles()

    new_articles = [a for a in articles if is_new_article(a["link"], sent_links)]
    log.info(f"Fetched {len(articles)} article(s), {len(new_articles)} new")

    if not new_articles:
        log.info("No new articles to send")
    else:
        send_to_telegram("📰 *New articles detected!*\nCompiled by SJVTDM Bot.\n")

        grouped = defaultdict(list)
        for article in new_articles:
            grouped[article["source"]].append(article)

        for source, items in grouped.items():
            send_to_telegram(f"📌 *{source}*")

            for article in items:
                message = f"→ [{article['title']}]({article['link']})"
                try:
                    success = send_to_telegram(message)
                    if success:
                        sent_links.add(article["link"])
                        log.info(f"Sent: {article['title']}")
                    else:
                        raise Exception("send_to_telegram returned False")
                except Exception as e:
                    error_text = f"Failed to send: {article['title']} ({article['link']})"
                    log.error(f"{error_text} | Reason: {e}")
                    send_error_alert(error_text)

    save_sent_links(sent_links)
    log.info("SJVTDM bot finished\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"Unhandled exception: {e}"
        log.exception("CRITICAL ERROR in bot")
        send_error_alert(error_msg)
