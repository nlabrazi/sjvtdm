import os
import unittest
from unittest.mock import patch

import config


class ConfigTests(unittest.TestCase):
    def test_get_database_connection_kwargs_prefers_database_url(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://user:pass@db:5432/app",
                "PGHOST": "ignored-host",
            },
            clear=True,
        ):
            kwargs = config.get_database_connection_kwargs()

        self.assertEqual(kwargs, {"dsn": "postgresql://user:pass@db:5432/app"})

    def test_get_database_connection_kwargs_builds_pg_mapping_and_casts_port(self):
        with patch.dict(
            os.environ,
            {
                "PGHOST": "localhost",
                "PGDATABASE": "sjvtdm",
                "PGUSER": "postgres",
                "PGPASSWORD": "secret",
                "PGPORT": "5433",
            },
            clear=True,
        ):
            kwargs = config.get_database_connection_kwargs()

        self.assertEqual(
            kwargs,
            {
                "host": "localhost",
                "database": "sjvtdm",
                "user": "postgres",
                "password": "secret",
                "port": 5433,
            },
        )

    def test_get_database_connection_kwargs_raises_when_required_pg_values_are_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                config.get_database_connection_kwargs()

