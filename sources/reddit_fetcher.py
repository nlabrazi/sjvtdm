import os
import praw

# 🔧 Chargement des identifiants depuis .env
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

SUBREDDITS = ["technology", "gaming"]

def fetch_reddit_posts(limit=10):
    posts = []
    for sub in SUBREDDITS:
        for submission in reddit.subreddit(sub).new(limit=limit):
            posts.append({
                "source": f"/r/{sub}",
                "title": submission.title,
                "link": submission.url
            })
    return posts
