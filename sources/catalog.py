RSS_SOURCE_CONFIGS: tuple[dict[str, str], ...] = (
    {
        "url": "https://www.polygon.com/rss/index.xml",
        "source_key": "polygon",
        "source_label": "Polygon",
        "language": "english",
        "emoji": "📢",
    },
    {
        "url": "https://www.ghacks.net/feed/",
        "source_key": "ghacks",
        "source_label": "gHacks Technology News",
        "language": "english",
        "emoji": "💻",
    },
    {
        "url": "https://hackernoon.com/feed",
        "source_key": "hackernoon",
        "source_label": "HackerNoon",
        "language": "english",
        "emoji": "🧠",
    },
    {
        "url": "https://www.lesnumeriques.com/rss.xml",
        "source_key": "les_numeriques",
        "source_label": "Les Numeriques",
        "language": "french",
        "emoji": "🧪",
    },
)

REDDIT_SOURCE_CONFIGS: tuple[dict[str, str], ...] = (
    {
        "subreddit": "technology",
        "source_key": "reddit_technology",
        "source_label": "/r/technology",
        "language": "english",
        "emoji": "🔧",
    },
    {
        "subreddit": "gaming",
        "source_key": "reddit_gaming",
        "source_label": "/r/gaming",
        "language": "english",
        "emoji": "🎮",
    },
)

ALL_SOURCE_CONFIGS = RSS_SOURCE_CONFIGS + REDDIT_SOURCE_CONFIGS
TARGET_SOURCE_KEYS = tuple(source["source_key"] for source in ALL_SOURCE_CONFIGS)
SOURCE_EMOJI_MAP = {source["source_key"]: source["emoji"] for source in ALL_SOURCE_CONFIGS}
