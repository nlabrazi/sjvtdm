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
