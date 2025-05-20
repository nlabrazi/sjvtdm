import os
import time
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Chargement .env si nécessaire
if not os.getenv("DATABASE_URL"):
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
RETENTION_DAYS = 3

def clean_old_logs(retention_days=RETENTION_DAYS):
    now = time.time()
    if not os.path.exists(LOG_DIR):
        print("❗ Log directory does not exist.")
        return

    deleted = 0
    for file in os.listdir(LOG_DIR):
        file_path = os.path.join(LOG_DIR, file)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > retention_days * 86400:  # seconds in a day
                os.remove(file_path)
                print(f"🧹 Deleted old log: {file}")
                deleted += 1
    if deleted == 0:
        print("✅ No old logs to delete.")

def clean_sent_articles():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
        cur.execute("DELETE FROM sent_articles WHERE sent_at < %s", (cutoff,))
        deleted = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        print(f"🧼 Deleted {deleted} old entries from sent_articles (before {cutoff}).")
    except Exception as e:
        print(f"❌ Error while cleaning sent_articles: {e}")

if __name__ == "__main__":
    print(f"🔧 Cleaning logs and DB entries older than {RETENTION_DAYS} days — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    clean_old_logs()
    clean_sent_articles()
