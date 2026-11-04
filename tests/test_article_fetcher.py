import io
import unittest
from unittest.mock import Mock, patch

import requests

from utils import article_fetcher
from utils.article_fetcher import fetch_article_text

PARAGRAPH = (
    "The company unveiled a new graphics card on Tuesday, promising significantly "
    "better performance per watt than the previous generation. Analysts say the "
    "launch could reshape the mid-range market over the coming months. "
)
HTML = (
    "<html><head><title>t</title></head><body><nav>menu menu</nav><article><h1>Title</h1>"
    + "".join(f"<p>{PARAGRAPH} Detail number {n} about benchmark {n * 7}.</p>" for n in range(4))
    + "</article><footer>footer</footer></body></html>"
)


def make_response(html=HTML, content_type="text/html; charset=utf-8", status_error=None):
    response = Mock()
    response.headers = {"Content-Type": content_type}
    response.encoding = "utf-8"
    response.raw.read.return_value = html.encode("utf-8")
    if status_error:
        response.raise_for_status.side_effect = status_error
    return response


class FetchArticleTextTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(article_fetcher, "_is_public_host", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_extracts_main_text_without_boilerplate(self):
        http = Mock()
        http.get.return_value = make_response()
        text = fetch_article_text("https://example.com/a", http_client=http)
        self.assertIn("new graphics card", text)
        self.assertNotIn("menu menu", text)
        self.assertNotIn("footer", text)

    def test_returns_empty_on_http_error_or_network_failure(self):
        http = Mock()
        http.get.return_value = make_response(
            status_error=requests.HTTPError("403")
        )
        self.assertEqual(fetch_article_text("https://example.com/a", http_client=http), "")
        http.get.side_effect = requests.ConnectionError("boom")
        self.assertEqual(fetch_article_text("https://example.com/a", http_client=http), "")

    def test_returns_empty_for_non_html_and_short_pages(self):
        http = Mock()
        http.get.return_value = make_response(content_type="application/pdf")
        self.assertEqual(fetch_article_text("https://example.com/a", http_client=http), "")
        http.get.return_value = make_response(html="<html><body><p>Too short.</p></body></html>")
        self.assertEqual(fetch_article_text("https://example.com/a", http_client=http), "")

    def test_rejects_invalid_scheme_and_non_public_hosts(self):
        http = Mock()
        self.assertEqual(fetch_article_text("file:///etc/passwd", http_client=http), "")
        self.assertEqual(fetch_article_text("", http_client=http), "")
        with patch.object(article_fetcher, "_is_public_host", return_value=False):
            self.assertEqual(fetch_article_text("http://127.0.0.1/a", http_client=http), "")
        http.get.assert_not_called()



class PublicHostTests(unittest.TestCase):
    def test_loopback_and_private_hosts_are_rejected(self):
        for host in ("localhost", "127.0.0.1", "10.0.0.5", "192.168.1.1"):
            self.assertFalse(article_fetcher._is_public_host(host), host)


if __name__ == "__main__":
    unittest.main()
