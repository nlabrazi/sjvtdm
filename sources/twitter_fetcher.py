import os
import requests
from dotenv import load_dotenv

load_dotenv()

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Twitter API endpoints
BASE_URL = "https://api.twitter.com/2"
USERNAMES = ["SaudiNewsFR"]

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

def get_user_id(username):
    url = f"{BASE_URL}/users/by/username/{username}"
    response = requests.get(url, headers=HEADERS)
    if response.ok:
        return response.json().get("data", {}).get("id")
    return None

def fetch_latest_tweets(user_id, max_results=5):
    url = f"{BASE_URL}/users/{user_id}/tweets"
    params = {
        "max_results": max_results,
        "tweet.fields": "created_at",
        "exclude": "replies,retweets"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.ok:
        return response.json().get("data", [])
    return []

def fetch_twitter_articles():
    all_tweets = []

    for username in USERNAMES:
        user_id = get_user_id(username)
        if not user_id:
            continue

        tweets = fetch_latest_tweets(user_id, max_results=6)

        for tweet in tweets:
            tweet_id = tweet["id"]
            text = tweet["text"]
            link = f"https://twitter.com/{username}/status/{tweet_id}"

            all_tweets.append({
                "title": text if len(text) <= 120 else text[:117] + "...",
                "link": link,
                "source": f"@{username}"
            })

    return all_tweets

if __name__ == "__main__":
    tweets = fetch_twitter_articles()
    for tweet in tweets:
        print(f"🕊️ [{tweet['source']}] {tweet['title']}")
        print(f"🔗 {tweet['link']}\n")
