import unittest
import requests
from unittest.mock import Mock, patch

from sources import rss_fetcher


class RssFetcherTests(unittest.TestCase):
    @patch(
        "sources.rss_fetcher.RSS_SOURCE_CONFIGS",
        (
            {
                "url": "https://www.polygon.com/rss/index.xml",
                "source_key": "polygon",
                "source_label": "Polygon",
                "language": "english",
            },
        ),
    )
    def test_fetches_polygon_image_from_rss_enclosure(self):
        rss = b"""\
            <rss version="2.0">
              <channel>
                <item>
                  <title>Article</title>
                  <link>https://www.polygon.com/article</link>
                  <enclosure
                    url="https://static0.polygonimages.com/article.jpg"
                    type="image/jpeg"
                    length="123"
                  />
                </item>
              </channel>
            </rss>
        """
        response = Mock(content=rss)
        response.raise_for_status.return_value = None

        with patch("sources.rss_fetcher.SESSION.get", return_value=response):
            articles = rss_fetcher.fetch_rss_articles(limit=1)

        self.assertEqual(
            articles[0]["image"],
            "https://static0.polygonimages.com/article.jpg",
        )

    def test_fetch_rss_articles_continues_when_a_feed_times_out(self):
        with patch("sources.rss_fetcher.SESSION.get", side_effect=requests.Timeout):
            with patch("sources.rss_fetcher.log.warning") as mock_warning:
                articles = rss_fetcher.fetch_rss_articles(limit=2)

        self.assertEqual(articles, [])
        self.assertEqual(mock_warning.call_count, len(rss_fetcher.RSS_SOURCE_CONFIGS))


class GhacksArticleImageTests(unittest.TestCase):
    def setUp(self):
        self.article = {"source_key": "ghacks", "link": "https://www.ghacks.net/article/"}

    def response(self, html):
        return Mock(text=html, url=self.article["link"])

    @patch("sources.rss_fetcher.SESSION.get")
    def test_extracts_open_graph_image_and_decodes_entities(self, get):
        get.return_value = self.response(
            '<meta name="twitter:image" content="https://example.com/twitter.jpg">'
            '<meta content="/photo.png?a=1&amp;b=2" property="og:image">'
        )
        self.assertEqual(rss_fetcher.get_article_image(self.article),
                         "https://www.ghacks.net/photo.png?a=1&b=2")
        get.assert_called_once_with(self.article["link"],
                                    headers=rss_fetcher.REQUEST_HEADERS,
                                    timeout=rss_fetcher.HTTP_TIMEOUT_SECONDS)

    @patch("sources.rss_fetcher.SESSION.get")
    def test_preserves_rss_images_and_skips_other_sources(self, get):
        self.assertEqual(rss_fetcher.get_article_image(
            dict(self.article, image="https://example.com/rss.jpg")),
            "https://example.com/rss.jpg")
        self.assertIsNone(rss_fetcher.get_article_image(
            dict(self.article, source_key="polygon")))
        self.assertIsNone(rss_fetcher.get_article_image(
            dict(self.article, link="https://example.com/article")))
        get.assert_not_called()

    @patch("sources.rss_fetcher.SESSION.get")
    def test_falls_back_to_twitter_image_when_open_graph_is_invalid(self, get):
        get.return_value = self.response(
            '<meta property="og:image" content="data:image/png;base64,abc">'
            '<meta name="twitter:image" content="https://example.com/photo.jpg">'
        )
        self.assertEqual(rss_fetcher.get_article_image(self.article),
                         "https://example.com/photo.jpg")

    @patch("sources.rss_fetcher.SESSION.get")
    def test_missing_image_or_http_failure_keeps_text_fallback(self, get):
        get.return_value = self.response('<html></html>')
        self.assertIsNone(rss_fetcher.get_article_image(self.article))
        get.side_effect = requests.Timeout
        self.assertIsNone(rss_fetcher.get_article_image(self.article))
        get.side_effect = None
        get.return_value.raise_for_status.side_effect = requests.HTTPError
        self.assertIsNone(rss_fetcher.get_article_image(self.article))
