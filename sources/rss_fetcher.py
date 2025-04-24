import feedparser

RSS_FEEDS = [
    "https://www.polygon.com/rss/index.xml",
    "https://www.ghacks.net/feed/",
    "https://www.reddit.com/r/technology/.rss",
    "https://www.reddit.com/r/gaming/.rss",
    "https://hackernoon.com/feed",
    "https://www.lesnumeriques.com/rss.xml",
]

def fetch_rss_articles():
    articles = []

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        source_name = feed.feed.get("title", "Unknown Source")
        entries = feed.entries[:10]

        print(f"📡 Feed: {source_name} ({len(entries)} articles)")

        for entry in entries:
            image = None
            if "media_content" in entry:
                image = entry.media_content[0].get("url")
            elif "media_thumbnail" in entry:
                image = entry.media_thumbnail[0].get("url")
            elif "image" in entry and isinstance(entry.image, dict):
                image = entry.image.get("href")

            articles.append({
                "title": entry.title,
                "link": entry.link,
                "description": entry.get("summary", ""),
                "source": source_name,
                "image": image,
            })

    return articles

if __name__ == "__main__":
    fetched = fetch_rss_articles()
    for article in fetched:
        print(f"[{article['source']}] {article['title']}")
        print(f"🔗 {article['link']}")
        if article.get("image"):
            print(f"🖼️ {article['image']}")
        print()
