import ipaddress
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.build_fixture import build_fixture


class PipelineTests(unittest.TestCase):
    def test_amnezia_uses_native_ipv4_cidrs_without_exporting_domains(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            build_fixture(output)
            self.assertEqual(
                json.loads((output / "telegram-ips.amnezia.json").read_text()),
                [{"hostname": "192.0.2.0/24", "ip": ""}],
            )
            self.assertFalse((output / "ru-domains.amnezia.json").exists())

    def test_rebuild_preserves_local_files_and_removes_stale_compiled_outputs(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            build_fixture(output)
            (output / "notes.txt").write_text("keep", encoding="utf-8")
            (output / "ru-ips.mihomo.mrs").write_bytes(b"old compiled rules")
            build_fixture(output)
            self.assertEqual((output / "notes.txt").read_text(), "keep")
            self.assertFalse((output / "ru-ips.mihomo.mrs").exists())

    def test_fixture_exercises_full_pipeline_and_preserves_client_semantics(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            counts = build_fixture(output)
            self.assertGreater(counts["ru-ips"], 0)
            self.assertEqual(
                (output / "ru-domains.shadowrocket.list").read_text().splitlines(),
                [
                    "DOMAIN-SUFFIX,example.org",
                    "DOMAIN-SUFFIX,xn--e1afmkfd.xn--p1ai",
                    "DOMAIN,api.example.net",
                    "DOMAIN-KEYWORD,bank.",
                ],
            )
            self.assertEqual(
                (output / "telegram-ips.shadowrocket.list").read_text().splitlines(),
                ["IP-CIDR,192.0.2.0/24", "IP-CIDR6,2001:db8::/126"],
            )
            self.assertEqual(
                (output / "telegram-domains.shadowrocket.list").read_text().splitlines(),
                ["DOMAIN-SUFFIX,telegram.example", "DOMAIN-KEYWORD,nicegram"],
            )
            self.assertIn("203.0.113.0/24", (output / "ru-ips.txt").read_text().splitlines())

    def test_telegram_space_is_excluded_from_every_ru_export(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            build_fixture(output)
            ru = (output / "ru-ips.txt").read_text().splitlines()
            networks = [ipaddress.ip_network(line) for line in ru]
            telegram = [
                ipaddress.ip_network(line)
                for line in (output / "telegram-ips.txt").read_text().splitlines()
            ]
            self.assertFalse(
                any(a.overlaps(b) for a in networks for b in telegram if a.version == b.version)
            )
            self.assertIn("192.0.3.0/24", ru)
            self.assertIn("2001:db8::4/126", ru)
            self.assertEqual(
                (output / "ru-ips.shadowrocket.list").read_text().splitlines(),
                [f"{'IP-CIDR6' if net.version == 6 else 'IP-CIDR'},{net}" for net in networks],
            )
            yaml = (output / "ru-ips.mihomo.yaml").read_text().splitlines()
            self.assertEqual([json.loads(line.strip()[2:]) for line in yaml[1:]], ru)
            self.assertEqual(
                json.loads((output / "ru-ips.amnezia.json").read_text()),
                [{"hostname": str(net), "ip": ""} for net in networks if net.version == 4],
            )
