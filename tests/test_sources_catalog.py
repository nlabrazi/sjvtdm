import unittest

from sources.catalog import ALL_SOURCE_CONFIGS, REDDIT_SOURCE_CONFIGS, RSS_SOURCE_CONFIGS, SOURCE_EMOJI_MAP, TARGET_SOURCE_KEYS


class SourceCatalogTests(unittest.TestCase):
    def test_target_source_keys_follow_catalog_order(self):
        expected_keys = tuple(source["source_key"] for source in ALL_SOURCE_CONFIGS)

        self.assertEqual(TARGET_SOURCE_KEYS, expected_keys)

    def test_source_keys_are_unique_across_all_sources(self):
        source_keys = [source["source_key"] for source in ALL_SOURCE_CONFIGS]

        self.assertEqual(len(source_keys), len(set(source_keys)))

    def test_every_source_exposes_required_lookup_fields(self):
        for source in RSS_SOURCE_CONFIGS:
            self.assertIn("url", source)
            self.assertEqual(SOURCE_EMOJI_MAP[source["source_key"]], source["emoji"])

        for source in REDDIT_SOURCE_CONFIGS:
            self.assertIn("subreddit", source)
            self.assertEqual(SOURCE_EMOJI_MAP[source["source_key"]], source["emoji"])

