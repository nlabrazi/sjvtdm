from sources.rss_fetcher import fetch_rss_articles

articles = fetch_rss_articles()

for article in articles:
    print(f"📰 [{article['source']}] {article['title']}\n🔗 {article['link']}\n")
