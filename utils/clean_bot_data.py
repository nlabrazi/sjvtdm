import os
import time
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
SENT_FILE = os.path.join(LOG_DIR, "sent_articles.json")
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
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
        print(f"🧼 Cleared: sent_articles.json")
    else:
        print("❗ sent_articles.json does not exist.")

if __name__ == "__main__":
    print(f"🔧 Cleaning logs older than {RETENTION_DAYS} days — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    clean_old_logs()
    clean_sent_articles()
