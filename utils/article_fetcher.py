import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests
import trafilatura

from config import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT


log = logging.getLogger("cron_push_logger")

MAX_DOWNLOAD_BYTES = 2_000_000
MAX_TEXT_CHARACTERS = 12_000
MIN_TEXT_CHARACTERS = 400
REQUEST_HEADERS = {
    "User-Agent": HTTP_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml",
}


def _is_public_host(hostname: str) -> bool:
    """Reject hosts resolving to private/loopback ranges (feed links are untrusted)."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        return False
    return bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses)


def fetch_article_text(
    url: str,
    http_client=requests,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> str:
    """Download an article page ourselves and return its main text, or "" on failure.

    Never raises: callers fall back to other strategies when nothing is returned.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    if not _is_public_host(parsed.hostname):
        log.warning("Article fetch skipped for non-public host %s.", parsed.hostname)
        return ""

    try:
        response = http_client.get(
            url.strip(), headers=REQUEST_HEADERS, timeout=timeout, stream=True
        )
        try:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" not in content_type:
                log.warning(
                    "Article fetch skipped for %s: content_type=%s",
                    parsed.hostname, content_type.split(";")[0] or "unknown",
                )
                return ""
            body = response.raw.read(MAX_DOWNLOAD_BYTES, decode_content=True)
            encoding = response.encoding or response.apparent_encoding or "utf-8"
            html = body.decode(encoding, errors="replace")
        finally:
            response.close()
    except requests.RequestException as exc:
        log.warning(
            "Article fetch failed for %s: %s", parsed.hostname, type(exc).__name__
        )
        return ""

    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    text = " ".join(text.split())
    if len(text) < MIN_TEXT_CHARACTERS:
        log.warning(
            "Article text too short for %s (%s characters).", parsed.hostname, len(text)
        )
        return ""
    return text[:MAX_TEXT_CHARACTERS]

