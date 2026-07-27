import logging
import os
import re
from html import unescape
from urllib.parse import urlparse

import praw

from sources.catalog import REDDIT_SOURCE_CONFIGS


log = logging.getLogger("cron_push_logger")
REDDIT_BASE_URL = "https://www.reddit.com"
IGNORED_COMMENT_BODIES = {"[deleted]", "[removed]"}


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


def is_public_http_url(url):
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def get_submission_image(submission):
    preview = getattr(submission, "preview", None)
    if not isinstance(preview, dict):
        return None

    images = preview.get("images") or []
    if not images:
        return None

    source = images[0].get("source") or {}
    image_url = source.get("url")
    return unescape(image_url) if image_url else None


def get_top_comments(submission, limit=5):
    if limit <= 0:
        return []

    try:
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)
        comments = submission.comments.list()
    except Exception as exc:
        log.warning("Failed to fetch comments for Reddit post %s: %s", submission.id, exc)
        return []

    selected = []
    seen = set()
    for comment in comments:
        body = re.sub(r"\s+", " ", getattr(comment, "body", "") or "").strip()
        normalized = body.lower()
        if (
            not body
            or normalized in IGNORED_COMMENT_BODIES
            or normalized in seen
            or len(body) < 30
        ):
            continue

        selected.append(body)
        seen.add(normalized)
        if len(selected) >= limit:
            break

    return selected


def fetch_reddit_posts(limit=5, comment_limit=5):
    reddit = get_reddit_client()
    if reddit is None:
        log.warning("Reddit credentials are missing, skipping Reddit fetch.")
        return []

    posts = []
    for source_config in REDDIT_SOURCE_CONFIGS:
        try:
            submissions = reddit.subreddit(source_config["subreddit"]).new(limit=limit)
            for submission in submissions:
                discussion_url = f"{REDDIT_BASE_URL}{submission.permalink}"
                destination_url = (getattr(submission, "url", "") or "").strip()
                is_self_post = bool(getattr(submission, "is_self", False))
                content_url = discussion_url
                if not is_self_post and is_public_http_url(destination_url):
                    content_url = destination_url

                posts.append(
                    {
                        "source_key": source_config["source_key"],
                        "source_label": source_config["source_label"],
                        "language": source_config["language"],
                        "title": submission.title,
                        "description": submission.selftext or submission.title,
                        "link": content_url,
                        "discussion_url": discussion_url,
                        "is_self_post": is_self_post,
                        "comments": (
                            get_top_comments(submission, limit=comment_limit)
                            if is_self_post
                            else []
                        ),
                        "image": get_submission_image(submission),
                    }
                )
        except Exception as exc:
            log.warning("Failed to fetch subreddit %s: %s", source_config["subreddit"], exc)

    return posts
