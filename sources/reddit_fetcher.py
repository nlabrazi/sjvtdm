import os
import praw
from dotenv import load_dotenv

# 📥 Load .env only if local
if not os.getenv("REDDIT_CLIENT_ID"):
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
            image_url = None
            if hasattr(submission, "preview") and "images" in submission.preview:
                image_url = submission.preview["images"][0]["source"]["url"]

            posts.append({
                "source": f"/r/{sub}",
                "title": submission.title,
                "link": f"https://www.reddit.com{submission.permalink}",
                "image": image_url
            })
    return posts
