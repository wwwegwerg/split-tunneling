import csv
import gzip
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import maxminddb

from rulesets.ips import (
    IPFilters,
    collapse_networks,
    parse_cidrs,
    read_geofeed,
    read_ipinfo,
    read_maxmind,
    subtract_networks,
)


class IPTests(unittest.TestCase):
    def test_subtraction_preserves_every_address_outside_exclusions(self) -> None:
        cases = [
            ("192.0.2.0/28", "192.0.2.2/31\n192.0.2.8/30\n192.0.2.15/32"),
            ("2001:db8::/124", "2001:db8::2/127\n2001:db8::8/126\n2001:db8::f/128"),
            ("192.0.2.0/30\n2001:db8::/126", "192.0.2.0/24\n2001:db8::/64"),
            ("192.0.2.0/30\n2001:db8::/126", "192.0.2.0/30\n2001:db8::/126"),
            ("192.0.2.0/30\n2001:db8::/126", "198.51.100.0/30\n2001:db8:1::/126"),
            ("192.0.2.0/30\n192.0.2.8/30", "192.0.2.0/28"),
            ("192.0.2.0/30\n2001:db8::/126", ""),
            ("", "192.0.2.0/30"),
        ]
        for included, excluded in cases:
            with self.subTest(included=included, excluded=excluded):
                original = parse_cidrs(included) if included else []
                blocked = parse_cidrs(excluded) if excluded else []
                result = subtract_networks(original, blocked)
                expected = {
                    ip
                    for net in original
                    for ip in net
                    if not any(ip in exclusion for exclusion in blocked)
                }
                self.assertEqual({ip for net in result for ip in net}, expected)
                self.assertEqual(result, collapse_networks(result))

    def test_narrower_ru_prefix_does_not_override_telegram(self) -> None:
        result = subtract_networks(
            parse_cidrs("91.108.0.0/22\n91.109.0.0/24"), parse_cidrs("91.108.0.0/16")
        )
        self.assertEqual([str(net) for net in result], ["91.109.0.0/24"])

    def test_aggregation_cannot_create_a_default_route(self) -> None:
        for entries in ("0.0.0.0/1\n128.0.0.0/1", "::/1\n8000::/1"):
            with self.subTest(entries=entries), self.assertRaisesRegex(ValueError, "default route"):
                collapse_networks(parse_cidrs(entries))

    def test_collapse_preserves_exact_union_in_both_families(self) -> None:
        original = parse_cidrs(
            "192.0.2.0/31\n192.0.2.2/31\n192.0.2.2/32\n2001:db8::/127\n2001:db8::2/127\n"
        )
        result = collapse_networks(original)
        self.assertEqual([str(net) for net in result], ["192.0.2.0/30", "2001:db8::/126"])
        self.assertEqual(
            {ip for network in original for ip in network},
            {ip for network in result for ip in network},
        )

    def test_default_routes_and_invalid_sources_are_rejected(self) -> None:
        for value in ("0.0.0.0/0", "::/0", "<html>"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_cidrs(value)

    def test_ipinfo_combines_country_and_all_as_selectors(self) -> None:
        filters = IPFilters(
            frozenset({"RU", "BY"}),
            frozenset({"as123"}),
            ("yandex",),
            ("edgecenter",),
            frozenset({"exact.example"}),
        )
        rows = [
            ["192.0.2.0/32", "RU", "", "", ""],
            ["192.0.2.1/32", "BY", "", "", ""],
            ["192.0.2.2/32", "US", "AS123", "", ""],
            ["192.0.2.3/32", "US", "", "YANDEX LLC", ""],
            ["192.0.2.4/32", "US", "", "", "cdn.EdgeCenter.net"],
            ["192.0.2.5/32", "US", "", "", "EXACT.EXAMPLE"],
            ["192.0.2.6/32", "US", "", "", "other.exact.example"],
        ]
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "ipinfo.csv.gz"
            with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["network", "country_code", "asn", "as_name", "as_domain"])
                writer.writerows(rows)
            self.assertEqual(
                {str(net) for net in read_ipinfo(path, filters)},
                {f"192.0.2.{index}/32" for index in range(6)},
            )

    def test_geofeed_uses_country_column_and_does_not_infer_from_region(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "feed.csv"
            path.write_text(
                "# comment\n192.0.2.0/24,RU,,,\n198.51.100.0/24,US,RU,,\n"
                "2001:db8::/48,BY,,,\n203.0.113.0/24,,,,\n",
                encoding="utf-8",
            )
            self.assertEqual(
                [str(net) for net in read_geofeed(path, frozenset({"RU", "BY"}))],
                ["192.0.2.0/24", "2001:db8::/48"],
            )

    def test_real_maxmind_reader_selects_ru_by_networks(self) -> None:
        path = Path(__file__).parent / "fixtures" / "GeoIP2-Country-Test.mmdb"
        networks = read_maxmind(path, frozenset({"RU", "BY"}))
        self.assertEqual(len(networks), 32)
        with maxminddb.open_database(path) as reader:
            for network in networks:
                self.assertIn(
                    reader.get(str(network.network_address))["country"]["iso_code"], {"RU", "BY"}
                )
