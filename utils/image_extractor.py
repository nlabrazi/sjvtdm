import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def extract_image(article: dict) -> str | None:
    link = article.get("link", "")
    domain = urlparse(link).netloc

    if "ghacks.net" in domain:
        return extract_ghacks_image(link)
    elif "polygon.com" in domain:
        return extract_polygon_image(link)
    elif "lesnumeriques.com" in domain:
        return extract_lesnums_image(link)
    elif "reddit.com" in domain:
        return extract_reddit_image(article)
    elif "hackernoon.com" in domain:
        return extract_hackernoon_image(link)

    return None


def extract_ghacks_image(link: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(link, headers=headers, timeout=8)
        if response.status_code != 200:
            print(f"❌ [ghacks] HTTP {response.status_code} for {link}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        img = soup.select_one(".featured-image img")
        if img:
            return img.get("src")

        print(f"⚠️ [ghacks] No .featured-image img at {link}")
        return None
    except Exception as e:
        print(f"❌ [ghacks] Error fetching {link}: {e}")
        return None


def extract_polygon_image(link: str) -> str | None:
    try:
        response = requests.get(link, timeout=8)
        soup = BeautifulSoup(response.content, "html.parser")
        meta = soup.find("meta", property="og:image")
        return meta["content"] if meta else None
    except Exception:
        return None


def extract_lesnums_image(link: str) -> str | None:
    try:
        response = requests.get(link, timeout=8)
        soup = BeautifulSoup(response.content, "html.parser")
        meta = soup.find("meta", property="og:image")
        return meta["content"] if meta else None
    except Exception:
        return None


def extract_reddit_image(link: str) -> str | None:
    try:
        if "reddit.com/r/" not in link:
            return None
        headers = {"User-Agent": "Mozilla/5.0"}
        print(f"🔍 [reddit] Opening: {link}")
        response = requests.get(link, headers=headers, timeout=8)
        if response.status_code != 200:
            print(f"❌ [reddit] HTTP {response.status_code} for {link}")
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        img = soup.select_one("#post-image")
        if img:
            print(f"✅ [reddit] Found image: {img.get('src')}")
            return img.get("src")
        print(f"⚠️ [reddit] No #post-image found at {link}")
        return None
    except Exception as e:
        print(f"❌ [reddit] Exception for {link}: {e}")
        return None


def extract_hackernoon_image(link: str) -> str | None:
    try:
        response = requests.get(link, timeout=8)
        soup = BeautifulSoup(response.content, "html.parser")
        meta = soup.find("meta", property="og:image")
        return meta["content"] if meta else None
    except Exception:
        return None
