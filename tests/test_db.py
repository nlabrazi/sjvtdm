from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from database import db


def _make_fake_connection(fetchone_result=None, fetchall_result=None, rowcount=0):
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.fetchone.return_value = fetchone_result
    cursor.fetchall.return_value = fetchall_result or []
    cursor.rowcount = rowcount

    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    conn.cursor.return_value = cursor
    return conn, cursor


class DatabaseModuleTests(unittest.TestCase):
    def test_get_db_connection_forwards_config_kwargs(self) -> None:
        kwargs = {"host": "localhost", "dbname": "sjvtdm", "user": "bot"}
        with patch("database.db.get_database_connection_kwargs", return_value=kwargs), patch(
            "database.db.psycopg2.connect", return_value="fake-conn"
        ) as connect_mock:
            conn = db.get_db_connection()

        self.assertEqual(conn, "fake-conn")
        connect_mock.assert_called_once_with(**kwargs)

    def test_normalize_urls_strips_blanks_and_deduplicates_preserving_order(self) -> None:
        result = db.normalize_urls(["  https://a.test  ", "", None, "https://b.test", "https://a.test", "   "])
        self.assertEqual(result, ["https://a.test", "https://b.test"])

    def test_setup_table_creates_table_without_migration_when_already_timestamptz(self) -> None:
        conn, cursor = _make_fake_connection(fetchone_result=("timestamp with time zone",))
        with patch("database.db.get_db_connection", return_value=conn):
            db.setup_table()

        self.assertEqual(cursor.execute.call_count, 2)
        self.assertIn("CREATE TABLE IF NOT EXISTS sent_articles", cursor.execute.call_args_list[0].args[0])
        self.assertIn("information_schema.columns", cursor.execute.call_args_list[1].args[0])

    def test_setup_table_migrates_legacy_timestamp_without_time_zone(self) -> None:
        conn, cursor = _make_fake_connection(fetchone_result=("timestamp without time zone",))
        with patch("database.db.get_db_connection", return_value=conn):
            db.setup_table()

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn("ALTER COLUMN sent_at TYPE TIMESTAMPTZ", cursor.execute.call_args_list[2].args[0])

    def test_find_sent_urls_handles_empty_explicit_connection_and_auto_connection(self) -> None:
        with patch("database.db.get_db_connection") as get_conn:
            self.assertEqual(db.find_sent_urls(["", "   ", None]), set())
        get_conn.assert_not_called()

        conn, cursor = _make_fake_connection(fetchall_result=[("https://a.test",)])
        found = db.find_sent_urls([" https://a.test ", "https://b.test", "https://a.test"], conn=conn)
        self.assertEqual(found, {"https://a.test"})
        cursor.execute.assert_called_once_with(
            "SELECT url FROM sent_articles WHERE url = ANY(%s)",
            (["https://a.test", "https://b.test"],),
        )

        auto_conn, auto_cursor = _make_fake_connection(fetchall_result=[("https://b.test",)])
        with patch("database.db.get_db_connection", return_value=auto_conn):
            auto_found = db.find_sent_urls(["https://b.test"])
        self.assertEqual(auto_found, {"https://b.test"})
        auto_cursor.execute.assert_called_once()

    def test_mark_articles_as_sent_and_single_helper(self) -> None:
        with patch("database.db.get_db_connection") as get_conn:
            self.assertEqual(db.mark_articles_as_sent(["", None]), 0)
            self.assertEqual(db.mark_article_as_sent(""), 0)
            self.assertEqual(db.mark_article_as_sent(None), 0)
        get_conn.assert_not_called()

        conn, cursor = _make_fake_connection()
        with patch("database.db.execute_values") as exec_values:
            count = db.mark_articles_as_sent([" https://a.test ", "https://b.test", "https://a.test"], conn=conn)
        self.assertEqual(count, 2)
        exec_values.assert_called_once_with(
            cursor,
            "INSERT INTO sent_articles (url) VALUES %s ON CONFLICT (url) DO NOTHING",
            [("https://a.test",), ("https://b.test",)],
        )

        auto_conn, auto_cursor = _make_fake_connection()
        with patch("database.db.get_db_connection", return_value=auto_conn), patch(
            "database.db.execute_values"
        ) as exec_values:
            single_count = db.mark_article_as_sent("https://single.test")
        self.assertEqual(single_count, 1)
        exec_values.assert_called_once_with(
            auto_cursor,
            "INSERT INTO sent_articles (url) VALUES %s ON CONFLICT (url) DO NOTHING",
            [("https://single.test",)],
        )

    def test_delete_articles_older_than_returns_deleted_rowcount(self) -> None:
        cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
        conn, cursor = _make_fake_connection(rowcount=7)
        with patch("database.db.get_db_connection", return_value=conn):
            deleted = db.delete_articles_older_than(cutoff)

        self.assertEqual(deleted, 7)
        cursor.execute.assert_called_once_with("DELETE FROM sent_articles WHERE sent_at < %s", (cutoff,))


if __name__ == "__main__":
    unittest.main()
