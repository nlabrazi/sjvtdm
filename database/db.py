import psycopg2

from config import get_database_connection_kwargs


def get_db_connection():
    return psycopg2.connect(**get_database_connection_kwargs())


def setup_table():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )


def find_sent_urls(urls):
    candidate_urls = [url for url in urls if url]
    if not candidate_urls:
        return set()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM sent_articles WHERE url = ANY(%s)", (candidate_urls,))
            return {row[0] for row in cur.fetchall()}


def mark_article_as_sent(url):
    if not url:
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sent_articles (url) VALUES (%s) ON CONFLICT (url) DO NOTHING",
                (url,),
            )


def delete_articles_older_than(cutoff):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sent_articles WHERE sent_at < %s", (cutoff,))
            return cur.rowcount
