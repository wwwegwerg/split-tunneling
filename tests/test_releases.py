import unittest

from scripts.prune_releases import previous_releases


class ReleaseTests(unittest.TestCase):
    def test_cleanup_keeps_latest_and_only_selects_our_releases(self) -> None:
        releases = [
            {"tag_name": "rules-20261010T000000Z", "draft": False},
            {"tag_name": "rules-20261011T000000Z", "draft": False},
            {"tag_name": "rules-20261016T000000Z", "draft": False},
            {"tag_name": "rules-20261017T000000Z", "draft": True},
            {"tag_name": "v1.0", "draft": False},
        ]
        self.assertEqual(
            previous_releases(releases, "rules-20261016T000000Z"),
            [
                ("rules-20261010T000000Z", False),
                ("rules-20261011T000000Z", False),
                ("rules-20261017T000000Z", True),
            ],
        )
