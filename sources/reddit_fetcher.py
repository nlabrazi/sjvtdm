import os
import praw
from dotenv import load_dotenv

# 📥 Charge les variables d'environnement depuis .env
load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

SUBREDDITS = ["technology", "gaming"]

def fetch_reddit_posts(limit=5):
    posts = []
    for sub in SUBREDDITS:
        for submission in reddit.subreddit(sub).new(limit=limit):
            posts.append({
                "source": f"/r/{sub}",
                "title": submission.title,
                "link": submission.url
            })
    return posts
