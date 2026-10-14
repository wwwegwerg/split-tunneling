"""Exercise the full offline pipeline using synthetic sources and MaxMind's public test database."""

import gzip
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rulesets.build import generate
from rulesets.config import Config, Source
from rulesets.ips import IPFilters
from scripts.verify_mihomo import verify


def build_fixture(output: Path) -> dict[str, int]:
    with TemporaryDirectory() as temporary:
        inputs = Path(temporary)
        (inputs / "local-domains").write_text("domain:example.org\n", encoding="utf-8")
        (inputs / "local-telegram").write_text("192.0.2.0/25\n", encoding="utf-8")
        (inputs / "ru-domains").write_text(
            "full:api.example.net\nkeyword:bank.\ndomain:пример.рф\n", encoding="utf-8"
        )
        (inputs / "telegram-domains").write_text(
            "payload:\n  - DOMAIN-SUFFIX,telegram.example\n  - DOMAIN-KEYWORD,nicegram\n",
            encoding="utf-8",
        )
        (inputs / "telegram-ips").write_text("192.0.2.128/25\n2001:db8::/126\n", encoding="utf-8")
        (inputs / "geofeed").write_text("198.51.100.0/24,RU,,,\n", encoding="utf-8")
        with gzip.open(inputs / "ipinfo.csv.gz", "wt", encoding="utf-8") as stream:
            stream.write(
                "network,country_code,asn,as_name,as_domain\n"
                "203.0.113.0/25,RU,AS100,Example,example.org\n"
                "203.0.113.128/25,BY,AS101,Example,example.org\n"
                "2001:db8:1::/48,US,AS13238,Yandex LLC,yandex.net\n"
            )
        shutil.copyfile(
            Path(__file__).parent / "fixtures" / "GeoIP2-Country-Test.mmdb",
            inputs / "maxmind.mmdb",
        )
        (inputs / "maxmind-COPYRIGHT.txt").write_text("Synthetic MaxMind test database\n")
        shutil.copyfile(
            Path(__file__).parent / "fixtures" / "LICENSE-MIT",
            inputs / "maxmind-LICENSE.txt",
        )
        config = Config(
            (
                Source("ru-domains", "https://example.test/ru", "ru-domains"),
                Source("telegram-domains", "https://example.test/tg", "telegram-domains", "yaml"),
                Source("telegram-ips", "https://example.test/ips", "telegram-ips"),
                Source("geofeed", "https://example.test/feed", "geofeed"),
            ),
            IPFilters(frozenset({"RU", "BY"}), frozenset({"as13238"}), (), (), frozenset()),
            inputs / "local-domains",
            inputs / "local-telegram",
        )
        counts = generate(config, inputs, output)
        report = output / "build-info.txt"
        report.write_text(
            report.read_text(encoding="utf-8").replace("\nMode: full\n", "\nMode: fixture\n"),
            encoding="utf-8",
        )
        return counts


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python tests/build_fixture.py")
    with TemporaryDirectory() as temporary:
        output = Path(temporary)
        build_fixture(output)
        verify(Path(".tools/mihomo"), output)
