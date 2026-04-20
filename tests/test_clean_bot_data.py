import os
import time
import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from utils import clean_bot_data


class CleanBotDataTests(unittest.TestCase):
    def test_clean_old_logs_only_deletes_files_older_than_retention(self):
        with TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            old_log = logs_dir / "old.log"
            fresh_log = logs_dir / "fresh.log"
            old_log.write_text("old", encoding="utf-8")
            fresh_log.write_text("fresh", encoding="utf-8")

            now = time.time()
            os.utime(old_log, (now - (5 * 86400), now - (5 * 86400)))
            os.utime(fresh_log, (now, now))

            with patch("utils.clean_bot_data.LOGS_DIR", logs_dir):
                deleted_count = clean_bot_data.clean_old_logs(retention_days=3)

            self.assertEqual(deleted_count, 1)
            self.assertFalse(old_log.exists())
            self.assertTrue(fresh_log.exists())

    def test_clean_sent_articles_initializes_table_and_uses_utc_cutoff(self):
        calls: list[object] = []

        def fake_setup_table():
            calls.append("setup")

        def fake_delete(cutoff):
            calls.append(cutoff)
            return 4

        with patch("utils.clean_bot_data.setup_table", side_effect=fake_setup_table):
            with patch("utils.clean_bot_data.delete_articles_older_than", side_effect=fake_delete):
                deleted_count = clean_bot_data.clean_sent_articles(retention_days=2)

        self.assertEqual(deleted_count, 4)
        self.assertEqual(calls[0], "setup")
        self.assertEqual(calls[1].utcoffset(), timedelta(0))
