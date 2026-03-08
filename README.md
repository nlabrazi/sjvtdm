# SJVTDM

Bot Python qui agrège des articles RSS et des posts Reddit, génère un résumé court, puis publie le tout dans un canal Telegram privé. La déduplication repose sur PostgreSQL pour éviter les renvois d’articles déjà envoyés.

## Fonctionnement

- Sources actives: Polygon, gHacks, HackerNoon, Les Numeriques, `/r/technology`, `/r/gaming`
- Envoi Telegram au format HTML avec validation minimale des URLs
- Déduplication persistante via la table `sent_articles`
- Job de nettoyage séparé pour purger les logs anciens et les URLs expirées

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Variables d’environnement

Renseigner dans `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- soit `DATABASE_URL`
- soit `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGPORT`

Variables optionnelles:

- `HTTP_TIMEOUT_SECONDS`
- `MAX_MESSAGES_PER_MINUTE`
- `MAX_MESSAGES_PER_SOURCE`
- `RETENTION_DAYS`

## Lancement

Envoi du digest:

```bash
RUN_MODE=bot ./start.sh
```

Nettoyage:

```bash
RUN_MODE=clean ./start.sh
```

## Structure

- `main.py`: orchestration du digest
- `sources/`: récupération des contenus
- `telegram/notifier.py`: envoi vers Telegram
- `database/db.py`: accès PostgreSQL
- `utils/clean_bot_data.py`: purge des logs et des articles anciens

## Logs

Les fichiers de logs sont écrits dans `logs/`:

- `cron_push.log`
- `cron_clean.log`
- `bot.log`
