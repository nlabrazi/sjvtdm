import unittest
import requests
from unittest.mock import patch

from sources import rss_fetcher


class RssFetcherTests(unittest.TestCase):
    def test_fetch_rss_articles_continues_when_a_feed_times_out(self):
        with patch("sources.rss_fetcher.SESSION.get", side_effect=requests.Timeout):
            with patch("sources.rss_fetcher.log.warning") as mock_warning:
                articles = rss_fetcher.fetch_rss_articles(limit=2)

        self.assertEqual(articles, [])
        self.assertEqual(mock_warning.call_count, len(rss_fetcher.RSS_SOURCE_CONFIGS))
