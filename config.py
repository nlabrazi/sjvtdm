import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
MAX_MESSAGES_PER_MINUTE = int(os.getenv("MAX_MESSAGES_PER_MINUTE", "20"))
MAX_MESSAGES_PER_SOURCE = int(os.getenv("MAX_MESSAGES_PER_SOURCE", "10"))
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "3"))
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "sjvtdm/1.0")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def get_database_connection_kwargs() -> dict[str, object]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}

    mapping = {
        "host": "PGHOST",
        "database": "PGDATABASE",
        "user": "PGUSER",
        "password": "PGPASSWORD",
        "port": "PGPORT",
    }

    kwargs: dict[str, object] = {}
    missing: list[str] = []

    for key, env_var in mapping.items():
        value = os.getenv(env_var)
        if value:
            kwargs[key] = int(value) if key == "port" else value
        elif key != "port":
            missing.append(env_var)

    if missing:
        raise RuntimeError(
            "Missing database configuration. Set DATABASE_URL or PGHOST/PGDATABASE/PGUSER/PGPASSWORD."
        )

    kwargs.setdefault("port", 5432)
    return kwargs
