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
            self.assertIn("203.0.113.0/24", (output / "ru-ips.txt").read_text().splitlines())
