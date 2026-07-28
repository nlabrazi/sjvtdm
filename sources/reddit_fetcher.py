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
IMAGE_FILE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


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


def normalize_image_url(url):
    candidate = unescape(url).strip() if isinstance(url, str) else ""
    return candidate if is_public_http_url(candidate) else None


def get_gallery_image(submission):
    gallery_data = getattr(submission, "gallery_data", None)
    media_metadata = getattr(submission, "media_metadata", None)
    if not isinstance(gallery_data, dict) or not isinstance(media_metadata, dict):
        return None

    for item in gallery_data.get("items") or []:
        media = media_metadata.get(item.get("media_id")) or {}
        source = media.get("s") or {}
        image_url = normalize_image_url(source.get("u") or source.get("gif"))
        if image_url:
            return image_url

    return None


def get_embedded_thumbnail(submission):
    for media_attribute in ("secure_media", "media"):
        media = getattr(submission, media_attribute, None)
        if not isinstance(media, dict):
            continue
        oembed = media.get("oembed") or {}
        image_url = normalize_image_url(oembed.get("thumbnail_url"))
        if image_url:
            return image_url

    return None


def is_direct_image_submission(submission, url):
    if getattr(submission, "post_hint", None) == "image":
        return True

    path = urlparse(url).path.lower()
    return any(path.endswith(extension) for extension in IMAGE_FILE_EXTENSIONS)


def get_submission_image(submission):
    preview = getattr(submission, "preview", None)
    if isinstance(preview, dict):
        images = preview.get("images") or []
        if images:
            source = images[0].get("source") or {}
            image_url = normalize_image_url(source.get("url"))
            if image_url:
                return image_url

            for resolution in reversed(images[0].get("resolutions") or []):
                image_url = normalize_image_url(resolution.get("url"))
                if image_url:
                    return image_url

    gallery_image = get_gallery_image(submission)
    if gallery_image:
        return gallery_image

    destination_url = normalize_image_url(getattr(submission, "url", None))
    if destination_url and is_direct_image_submission(submission, destination_url):
        return destination_url

    thumbnail = normalize_image_url(getattr(submission, "thumbnail", None))
    if thumbnail:
        return thumbnail

    return get_embedded_thumbnail(submission)


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
