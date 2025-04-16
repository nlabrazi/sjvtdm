import logging
from datetime import datetime
from sources.rss_fetcher import fetch_rss_articles
from telegram.notifier import send_to_telegram
from utils.sent_tracker import load_sent_links, save_sent_links, is_new_article

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()  # Keep console output for cron
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
        for article in new_articles:
            message = f"📰 *{article['title']}*\n[{article['source']}]({article['link']})"
            success = send_to_telegram(message)

            if success:
                sent_links.add(article["link"])
                log.info(f"Sent: {article['title']}")
            else:
                log.error(f"Failed to send: {article['title']}")

    save_sent_links(sent_links)
    log.info("SJVTDM bot finished\n")

if __name__ == "__main__":
    main()
