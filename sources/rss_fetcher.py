import logging

import feedparser
import requests

from config import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT


log = logging.getLogger("cron_push_logger")

RSS_FEEDS = [
    {
        "url": "https://www.polygon.com/rss/index.xml",
        "source_key": "polygon",
        "source_label": "Polygon",
        "language": "english",
    },
    {
        "url": "https://www.ghacks.net/feed/",
        "source_key": "ghacks",
        "source_label": "gHacks Technology News",
        "language": "english",
    },
    {
        "url": "https://hackernoon.com/feed",
        "source_key": "hackernoon",
        "source_label": "HackerNoon",
        "language": "english",
    },
    {
        "url": "https://www.lesnumeriques.com/rss.xml",
        "source_key": "les_numeriques",
        "source_label": "Les Numeriques",
        "language": "french",
    },
]

REQUEST_HEADERS = {"User-Agent": HTTP_USER_AGENT}


def fetch_rss_articles(limit=10):
    articles = []

    for feed_config in RSS_FEEDS:
        try:
            response = requests.get(
                feed_config["url"],
                headers=REQUEST_HEADERS,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            log.warning("Failed to fetch RSS feed %s: %s", feed_config["source_label"], exc)
            continue

        feed = feedparser.parse(response.content)
        entries = feed.entries[:limit]

        if getattr(feed, "bozo", False):
            log.warning(
                "Feed parsing issue for %s: %s",
                feed_config["source_label"],
                getattr(feed, "bozo_exception", "unknown error"),
            )

        log.info("Fetched %s RSS entries from %s", len(entries), feed_config["source_label"])

        for entry in entries:
            image = None
            media_content = entry.get("media_content") or []
            media_thumbnail = entry.get("media_thumbnail") or []
            entry_image = entry.get("image")

            if media_content:
                image = media_content[0].get("url")
            elif media_thumbnail:
                image = media_thumbnail[0].get("url")
            elif isinstance(entry_image, dict):
                image = entry_image.get("href")

            articles.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("summary", "") or entry.get("description", ""),
                    "source_key": feed_config["source_key"],
                    "source_label": feed_config["source_label"],
                    "language": feed_config["language"],
                    "image": image,
                }
            )

    return articles
