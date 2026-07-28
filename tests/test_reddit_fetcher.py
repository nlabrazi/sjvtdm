import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sources import reddit_fetcher


def build_submission(
    *,
    submission_id,
    title,
    url,
    permalink,
    is_self,
    selftext="",
    comments=None,
):
    comment_forest = Mock()
    comment_forest.list.return_value = comments or []
    return SimpleNamespace(
        id=submission_id,
        title=title,
        url=url,
        permalink=permalink,
        is_self=is_self,
        selftext=selftext,
        comments=comment_forest,
        preview={
            "images": [
                {
                    "source": {
                        "url": "https://images.example/photo.jpg?width=1200&amp;format=pjpg"
                    }
                }
            ]
        },
    )


class RedditFetcherTests(unittest.TestCase):
    @patch(
        "sources.reddit_fetcher.REDDIT_SOURCE_CONFIGS",
        (
            {
                "subreddit": "technology",
                "source_key": "reddit_technology",
                "source_label": "/r/technology",
                "language": "english",
                "emoji": "🔧",
            },
        ),
    )
    @patch("sources.reddit_fetcher.get_reddit_client")
    def test_external_post_uses_destination_article_url(self, get_client):
        submission = build_submission(
            submission_id="external",
            title="External article",
            url="https://publisher.example/article",
            permalink="/r/technology/comments/external/article/",
            is_self=False,
        )
        subreddit = Mock()
        subreddit.new.return_value = [submission]
        get_client.return_value.subreddit.return_value = subreddit

        posts = reddit_fetcher.fetch_reddit_posts(limit=1)

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["link"], "https://publisher.example/article")
        self.assertEqual(
            posts[0]["discussion_url"],
            "https://www.reddit.com/r/technology/comments/external/article/",
        )
        self.assertFalse(posts[0]["is_self_post"])
        self.assertEqual(posts[0]["comments"], [])
        self.assertEqual(
            posts[0]["image"],
            "https://images.example/photo.jpg?width=1200&format=pjpg",
        )
        submission.comments.replace_more.assert_not_called()

    @patch(
        "sources.reddit_fetcher.REDDIT_SOURCE_CONFIGS",
        (
            {
                "subreddit": "gaming",
                "source_key": "reddit_gaming",
                "source_label": "/r/gaming",
                "language": "english",
                "emoji": "🎮",
            },
        ),
    )
    @patch("sources.reddit_fetcher.get_reddit_client")
    def test_self_post_uses_discussion_and_collects_substantive_comments(
        self,
        get_client,
    ):
        submission = build_submission(
            submission_id="self-post",
            title="A personal gaming story",
            url="https://www.reddit.com/r/gaming/comments/self-post/story/",
            permalink="/r/gaming/comments/self-post/story/",
            is_self=True,
            selftext="The complete post body.",
            comments=[
                SimpleNamespace(body="[deleted]"),
                SimpleNamespace(body="Too short"),
                SimpleNamespace(
                    body="  This is a thoughtful response with enough useful context.  "
                ),
                SimpleNamespace(
                    body="This is a thoughtful response with enough useful context."
                ),
                SimpleNamespace(
                    body="Another substantial reaction that adds a different perspective."
                ),
            ],
        )
        subreddit = Mock()
        subreddit.new.return_value = [submission]
        get_client.return_value.subreddit.return_value = subreddit

        posts = reddit_fetcher.fetch_reddit_posts(limit=1, comment_limit=2)

        self.assertEqual(
            posts[0]["link"],
            "https://www.reddit.com/r/gaming/comments/self-post/story/",
        )
        self.assertTrue(posts[0]["is_self_post"])
        self.assertEqual(
            posts[0]["comments"],
            [
                "This is a thoughtful response with enough useful context.",
                "Another substantial reaction that adds a different perspective.",
            ],
        )
        submission.comments.replace_more.assert_called_once_with(limit=0)
        submission.comments.list.assert_called_once_with()

    def test_get_top_comments_returns_empty_list_when_reddit_fails(self):
        submission = SimpleNamespace(id="broken", comments=Mock())
        submission.comments.replace_more.side_effect = RuntimeError("Reddit unavailable")

        with patch("sources.reddit_fetcher.log.warning") as warning:
            comments = reddit_fetcher.get_top_comments(submission)

        self.assertEqual(comments, [])
        warning.assert_called_once()

    def test_get_submission_image_falls_back_to_gallery_metadata(self):
        submission = SimpleNamespace(
            preview=None,
            gallery_data={"items": [{"media_id": "image-1"}]},
            media_metadata={
                "image-1": {
                    "s": {
                        "u": "https://preview.redd.it/gallery.jpg?width=1080&amp;format=pjpg"
                    }
                }
            },
        )

        self.assertEqual(
            reddit_fetcher.get_submission_image(submission),
            "https://preview.redd.it/gallery.jpg?width=1080&format=pjpg",
        )

    def test_get_submission_image_falls_back_to_thumbnail(self):
        submission = SimpleNamespace(
            preview=None,
            gallery_data=None,
            media_metadata=None,
            url="https://publisher.example/article",
            thumbnail="https://external-preview.redd.it/article.jpg",
        )

        self.assertEqual(
            reddit_fetcher.get_submission_image(submission),
            "https://external-preview.redd.it/article.jpg",
        )


if __name__ == "__main__":
    unittest.main()
