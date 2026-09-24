import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import psycopg2
from psycopg2 import sql

from database import db


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "TEST_DATABASE_URL is not configured")
class DatabaseIntegrationTests(unittest.TestCase):
    """Run real SQL in a fresh schema; never use the application's DATABASE_URL."""

    def setUp(self):
        self.dsn = os.environ["TEST_DATABASE_URL"]
        self.schema = "sjvtdm_test_" + uuid4().hex
        self.admin = psycopg2.connect(self.dsn)
        self.admin.autocommit = True
        self.addCleanup(self.admin.close)
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)

        # Only redirect connection creation. Queries and transactions remain real.
        connection_patch = patch("database.db.get_db_connection", side_effect=self.connect)
        connection_patch.start()
        self.addCleanup(connection_patch.stop)

    def connect(self):
        conn = psycopg2.connect(
            self.dsn,
            options=f"-c search_path={self.schema} -c timezone=Europe/Paris",
        )
        # psycopg2's connection context commits/rollbacks, but does not close.
        self.addCleanup(conn.close)
        return conn

    def drop_schema(self):
        with self.admin.cursor() as cur:
            cur.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
            )

    def test_sent_urls_persist_and_duplicate_inserts_are_idempotent(self):
        db.setup_table()
        first = "https://example.com/first"
        second = "https://example.com/article?title=l'article"
        db.mark_articles_as_sent([None, "", "  ", f" {first} ", first, second])
        db.mark_articles_as_sent([first, second])

        self.assertEqual(
            db.find_sent_urls([first, second, "https://example.com/unknown"]),
            {first, second},
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT url FROM sent_articles")
            self.assertEqual(sorted(row[0] for row in cur.fetchall()), sorted([first, second]))

    def test_empty_batches_do_not_need_a_database_connection(self):
        with patch("database.db.get_db_connection") as connect:
            self.assertEqual(db.find_sent_urls([None, "", "  "]), set())
            self.assertEqual(db.mark_articles_as_sent([None, "", "  "]), 0)
        connect.assert_not_called()

    def test_caller_transaction_rolls_back_unsuccessful_batch(self):
        db.setup_table()
        url = "https://example.com/rolled-back"
        with self.assertRaisesRegex(RuntimeError, "abort batch"):
            with self.connect() as conn:
                db.mark_articles_as_sent([url], conn=conn)
                self.assertEqual(db.find_sent_urls([url], conn=conn), {url})
                raise RuntimeError("abort batch")
        self.assertEqual(db.find_sent_urls([url]), set())

    def test_cleanup_keeps_articles_at_and_after_cutoff(self):
        db.setup_table()
        cutoff = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO sent_articles (url, sent_at) VALUES (%s, %s)",
                [
                    ("https://example.com/old", cutoff - timedelta(seconds=1)),
                    ("https://example.com/boundary", cutoff),
                    ("https://example.com/recent", cutoff + timedelta(seconds=1)),
                ],
            )
        self.assertEqual(db.delete_articles_older_than(cutoff), 1)
        self.assertEqual(
            db.find_sent_urls([
                "https://example.com/old",
                "https://example.com/boundary",
                "https://example.com/recent",
            ]),
            {"https://example.com/boundary", "https://example.com/recent"},
        )

    def test_legacy_timestamp_migration_preserves_utc_instant_and_is_repeatable(self):
        legacy_timestamp = datetime(2025, 7, 10, 12, 30)
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE sent_articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute(
                "INSERT INTO sent_articles (url, sent_at) VALUES (%s, %s)",
                ("https://example.com/legacy", legacy_timestamp),
            )

        db.setup_table()
        db.setup_table()

        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT sent_at FROM sent_articles")
            self.assertEqual(
                cur.fetchone()[0],
                legacy_timestamp.replace(tzinfo=timezone.utc),
            )
            cur.execute("""
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'sent_articles' AND column_name = 'sent_at'
            """)
            self.assertEqual(cur.fetchone()[0], "timestamp with time zone")
