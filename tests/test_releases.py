import unittest
from datetime import UTC, datetime

from scripts.prune_releases import expired_releases


class ReleaseTests(unittest.TestCase):
    def test_retention_uses_build_time_and_only_our_release_tags(self) -> None:
        releases = [
            {"tag_name": "rules-20261010T000000Z", "draft": False},
            {"tag_name": "rules-20261011T000000Z", "draft": False},
            {"tag_name": "rules-20261016T000000Z", "draft": False, "created_at": "2020-01-01"},
            {"tag_name": "rules-20261015T000000Z", "draft": True},
            {"tag_name": "rules-20261017T000000Z", "draft": True},
            {"tag_name": "v1.0", "draft": False},
        ]
        self.assertEqual(
            expired_releases(releases, datetime(2026, 10, 17, tzinfo=UTC)),
            [("rules-20261010T000000Z", False), ("rules-20261015T000000Z", True)],
        )
