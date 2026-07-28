import logging
from html import unescape
from urllib.parse import urlparse

import feedparser
import requests

from config import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT
from sources.catalog import RSS_SOURCE_CONFIGS


log = logging.getLogger("cron_push_logger")

REQUEST_HEADERS = {"User-Agent": HTTP_USER_AGENT}
SESSION = requests.Session()


def is_public_http_url(url):
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def get_entry_image(entry):
    candidates = []

    candidates.extend(entry.get("media_content") or [])
    candidates.extend(entry.get("media_thumbnail") or [])

    entry_image = entry.get("image")
    if isinstance(entry_image, dict):
        candidates.append(entry_image)
    elif isinstance(entry_image, str):
        candidates.append({"url": entry_image})

    for enclosure in entry.get("enclosures") or []:
        media_type = (enclosure.get("type") or "").lower()
        if media_type.startswith("image/"):
            candidates.append(enclosure)

    for candidate in candidates:
        image_url = candidate.get("url") or candidate.get("href")
        image_url = unescape(image_url).strip() if image_url else ""
        if is_public_http_url(image_url):
            return image_url

    return None


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
            articles.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("summary", "") or entry.get("description", ""),
                    "source_key": source_config["source_key"],
                    "source_label": source_config["source_label"],
                    "language": source_config["language"],
                    "image": get_entry_image(entry),
                }
            )

    return articles
