import logging
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

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


class ArticleImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in {"og:image", "twitter:image"}:
            self.images.setdefault(key, attrs.get("content") or "")


GHACKS_PROXY_URL_TEMPLATE = "https://r.jina.ai/{url}"
PROXY_REQUEST_HEADERS = {
    "User-Agent": HTTP_USER_AGENT,
    "X-Return-Format": "html",
}


def fetch_ghacks_page_html(url):
    try:
        response = SESSION.get(url, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        log.warning(
            "Direct fetch failed for gHacks article %s: %s; trying proxy fallback.",
            url,
            exc,
        )

    try:
        proxy_url = GHACKS_PROXY_URL_TEMPLATE.format(url=url)
        response = SESSION.get(
            proxy_url,
            headers=PROXY_REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        log.warning("Proxy fetch failed for gHacks article %s: %s", url, exc)
        return None


def get_article_image(article):
    """Resolve gHacks page metadata only when an unsent article has no RSS image."""
    if article.get("image"):
        return article["image"]
    url = article.get("link") or ""
    if (
        article.get("source_key") != "ghacks"
        or not is_public_http_url(url)
        or urlparse(url).hostname not in {"ghacks.net", "www.ghacks.net"}
    ):
        return None

    html = fetch_ghacks_page_html(url)
    if not html:
        return None

    parser = ArticleImageParser()
    parser.feed(html)
    for key in ("og:image", "twitter:image"):
        candidate = parser.images.get(key, "").strip()
        if candidate:
            image_url = urljoin(url, candidate)
            if is_public_http_url(image_url):
                return image_url
    log.info("No image metadata found for gHacks article %s.", url)
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

        log.info(
            "Fetched %s RSS entries from %s (%s available in feed).",
            len(entries), source_config["source_label"], len(feed.entries),
        )

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
