import logging

import feedparser
import requests

from config import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT
from sources.catalog import RSS_SOURCE_CONFIGS


log = logging.getLogger("cron_push_logger")

REQUEST_HEADERS = {"User-Agent": HTTP_USER_AGENT}
SESSION = requests.Session()


def fetch_rss_articles(limit=10):
    articles = []

    for source_config in RSS_SOURCE_CONFIGS:
        try:
            response = SESSION.get(
                source_config["url"],
                headers=REQUEST_HEADERS,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.Timeout:
            log.warning(
                "Timed out while fetching RSS feed %s after %s second(s).",
                source_config["source_label"],
                HTTP_TIMEOUT_SECONDS,
            )
            continue
        except requests.RequestException as exc:
            log.warning("Failed to fetch RSS feed %s: %s", source_config["source_label"], exc)
            continue

        feed = feedparser.parse(response.content)
        entries = feed.entries[:limit]

        if getattr(feed, "bozo", False):
            log.warning(
                "Feed parsing issue for %s: %s",
                source_config["source_label"],
                getattr(feed, "bozo_exception", "unknown error"),
            )

        log.info("Fetched %s RSS entries from %s", len(entries), source_config["source_label"])

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
                    "source_key": source_config["source_key"],
                    "source_label": source_config["source_label"],
                    "language": source_config["language"],
                    "image": image,
                }
            )

    return articles
