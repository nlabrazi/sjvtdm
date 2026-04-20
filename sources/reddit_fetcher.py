import logging
import os

import praw

from sources.catalog import REDDIT_SOURCE_CONFIGS


log = logging.getLogger("cron_push_logger")


def get_reddit_client():
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not all([client_id, client_secret, user_agent]):
        return None

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def fetch_reddit_posts(limit=5):
    reddit = get_reddit_client()
    if reddit is None:
        log.warning("Reddit credentials are missing, skipping Reddit fetch.")
        return []

    posts = []
    for source_config in REDDIT_SOURCE_CONFIGS:
        try:
            submissions = reddit.subreddit(source_config["subreddit"]).new(limit=limit)
            for submission in submissions:
                image_url = None
                if hasattr(submission, "preview") and "images" in submission.preview:
                    image_url = submission.preview["images"][0]["source"]["url"]

                posts.append(
                    {
                        "source_key": source_config["source_key"],
                        "source_label": source_config["source_label"],
                        "language": source_config["language"],
                        "title": submission.title,
                        "description": submission.selftext or submission.title,
                        "link": f"https://www.reddit.com{submission.permalink}",
                        "image": image_url,
                    }
                )
        except Exception as exc:
            log.warning("Failed to fetch subreddit %s: %s", source_config["subreddit"], exc)

    return posts
