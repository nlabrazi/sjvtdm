# database/db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        port=int(os.getenv("PGPORT", 5432))
    )

def setup_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_articles (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def article_already_sent(url):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id FROM sent_articles WHERE url = %s", (url,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def mark_article_as_sent(url):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO sent_articles (url) VALUES (%s)", (url,))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
    finally:
        cur.close()
        conn.close()
