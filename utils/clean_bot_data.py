import time
from datetime import datetime, timedelta

from config import LOGS_DIR, RETENTION_DAYS
from database.db import delete_articles_older_than
from utils.logger import setup_logger

log = setup_logger("cron_clean_logger", "cron_clean.log")


def clean_old_logs(retention_days=RETENTION_DAYS):
    now = time.time()
    if not LOGS_DIR.exists():
        log.info("Log directory does not exist.")
        return 0

    deleted = 0
    for file_path in LOGS_DIR.iterdir():
        if file_path.is_file():
            file_age = now - file_path.stat().st_mtime
            if file_age > retention_days * 86400:  # seconds in a day
                file_path.unlink()
                log.info("Deleted old log: %s", file_path.name)
                deleted += 1
    if deleted == 0:
        log.info("No old logs to delete.")
    return deleted

def clean_sent_articles(retention_days=RETENTION_DAYS):
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    try:
        deleted = delete_articles_older_than(cutoff)
        log.info("Deleted %s old entries from sent_articles (before %s).", deleted, cutoff)
        return deleted
    except Exception as e:
        log.exception("Error while cleaning sent_articles: %s", e)
        return 0


def main():
    log.info(
        "Cleaning logs and DB entries older than %s days - %s",
        RETENTION_DAYS,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    clean_old_logs()
    clean_sent_articles()

if __name__ == "__main__":
    main()
