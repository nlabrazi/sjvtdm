import feedparser
from typing import List, Dict

# List of RSS feed URLs
RSS_FEEDS = [
    "https://www.polygon.com/rss/index.xml",
    "https://www.ghacks.net/feed/",
    "https://www.reddit.com/r/technology/.rss",
    "https://www.reddit.com/r/gaming/.rss",
    "https://hackernoon.com/feed",
    "https://www.lesnumeriques.com/rss.xml"
]

def fetch_rss_articles(limit_per_feed: int = 5) -> List[Dict]:
    """
    Fetch latest articles from configured RSS feeds.

    Returns:
        List of dictionaries with 'title', 'link', and 'source'.
    """
    all_articles = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        source_name = feed.feed.get("title", "Unknown Source")

        print(f"📡 Feed: {source_name} ({len(feed.entries)} articles)")

        for entry in feed.entries[:limit_per_feed]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue  # Skip incomplete articles

            article = {
                "title": title,
                "link": link,
                "source": source_name
            }
            all_articles.append(article)

    return all_articles
