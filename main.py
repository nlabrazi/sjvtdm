import os
import time
import logging
from collections import defaultdict

from sources.rss_fetcher import fetch_rss_articles
from telegram.notifier import send_to_telegram, send_error_alert
from utils.sent_tracker import load_sent_links, save_sent_links, is_new_article

# 📁 Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "logs", "bot.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 🔎 Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("sjvtdm")

# 🎨 Source display formats
SOURCE_FORMATS = {
    "Polygon": "🎮 *🧠 Insights from Polygon Gaming News*",
    "gHacks Technology News": "🛠️ *gHacks: Tech Tips & Software Alerts*",
    "/r/Technology": "💻 *Reddit Tech Highlights*",
    "r/gaming": "🎮 *Reddit Gamers Speak!*",
    "HackerNoon": "📗 *HackerNoon: Dev, Crypto & Startups*",
    "Les Numériques": "📸 *Le top de l'actu high-tech*"
}

def main():
    log.info("SJVTDM bot started")

    sent_links = load_sent_links()
    articles = fetch_rss_articles()

    new_articles = [a for a in articles if is_new_article(a["link"], sent_links)]
    log.info(f"Fetched {len(articles)} article(s), {len(new_articles)} new")

    if not new_articles:
        log.info("No new articles to send")
    else:
        total_count = len(new_articles)
        send_to_telegram(
            f"👋 *Hey there! Your SJVTDM digest is ready!*\n"
            f"📰 *{total_count} new article{'s' if total_count > 1 else ''} just landed — enjoy the read!*"
        )
        time.sleep(1.5)

        grouped = defaultdict(list)
        for article in new_articles:
            grouped[article["source"]].append(article)

        for source, items in grouped.items():
            title = SOURCE_FORMATS.get(source, f"📌 *{source}*")
            header = f"{title} — `{len(items)} article{'s' if len(items) > 1 else ''}`"

            body = "\n".join(
                f"→ [{article['title']}]({article['link']})"
                for article in items
            )

            full_message = f"{header}\n{body}"
            try:
                success = send_to_telegram(full_message)
                time.sleep(1.5)
                if success:
                    for article in items:
                        sent_links.add(article["link"])
                        log.info(f"Sent: {article['title']}")
                else:
                    raise Exception("send_to_telegram returned False")
            except Exception as e:
                error_text = f"Failed to send group: {source}"
                log.error(f"{error_text} | Reason: {e}")
                send_error_alert(error_text)

        send_to_telegram("✅ *That's all for now — see you in the next update!* 👋")

    save_sent_links(sent_links)
    log.info("SJVTDM bot finished\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"Unhandled exception: {e}"
        log.exception("CRITICAL ERROR in bot")
        send_error_alert(error_msg)
