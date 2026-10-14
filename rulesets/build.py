import shutil
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import maxminddb

from rulesets.config import Config
from rulesets.domains import DomainRule, parse_domains, reduce_domains
from rulesets.exports import DOMAIN_SETS, build_file_names, export_domains, export_ips, write_lines
from rulesets.ips import (
    Network,
    collapse_networks,
    parse_cidrs,
    read_geofeed,
    read_ipinfo,
    read_maxmind,
    subtract_networks,
)


def generate(
    config: Config,
    inputs: Path,
    output: Path,
    *,
    hashes: dict[str, str] | None = None,
) -> dict[str, int]:
    """A broken source must not replace the last successful build."""
    domains: dict[str, set[DomainRule]] = {
        "ru-domains": parse_domains(config.local_domains.read_text(encoding="utf-8"), "geosite"),
        "telegram-domains": set(),
        "blocked-domains": set(),
    }
    telegram = parse_cidrs(config.local_telegram_ips.read_text(encoding="utf-8"))
    ru: list[Network] = []
    for source in config.sources:
        path = inputs / source.name
        try:
            if source.group in DOMAIN_SETS:
                rules = parse_domains(path.read_text(encoding="utf-8"), source.format)
                domains[source.group].update(rules)
            elif source.group == "telegram-ips":
                networks = parse_cidrs(path.read_text(encoding="utf-8"))
                telegram.extend(networks)
            else:
                networks = read_geofeed(path, config.filters.countries)
                ru.extend(networks)
        except (OSError, ValueError) as error:
            raise ValueError(f"{source.name}: {error}") from error
    ipinfo = read_ipinfo(inputs / "ipinfo.csv.gz", config.filters)
    maxmind = read_maxmind(inputs / "maxmind.mmdb", config.filters.countries)
    with maxminddb.open_database(inputs / "maxmind.mmdb") as reader:
        geo_build = datetime.fromtimestamp(reader.metadata().build_epoch, UTC)
    ru.extend(ipinfo)
    ru.extend(maxmind)
    reduced = {name: reduce_domains(rules) for name, rules in domains.items()}
    telegram_networks = collapse_networks(telegram)
    networks_by_name = {
        # Shadowrocket may prefer a narrower RU prefix despite Telegram's rule order.
        "ru-ips": subtract_networks(ru, telegram_networks),
        "telegram-ips": telegram_networks,
    }
    if any(not rules for rules in reduced.values()) or any(
        not networks for networks in networks_by_name.values()
    ):
        raise ValueError("Refusing to generate an empty rule set")
    counts = {name: len(rules) for name, rules in reduced.items()}
    counts.update({name: len(networks) for name, networks in networks_by_name.items()})
    report = [
        "Generated: " + datetime.now(UTC).isoformat(timespec="seconds"),
        "Mode: full",
        "GeoLite build: " + geo_build.isoformat(timespec="seconds"),
        *[f"{name}: {counts[name]}" for name in (*DOMAIN_SETS, *networks_by_name)],
        f"telegram-ips input prefixes: {len(telegram)}",
        f"ru-ips input prefixes: {len(ru)}",
    ]
    if hashes:
        report.extend(["", "Source SHA-256:"])
        report.extend(f"{name}: {digest}" for name, digest in sorted(hashes.items()))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage exports before touching an existing build; leave unrelated local files alone.
    with TemporaryDirectory(prefix=".rules-", dir=output.parent) as temporary:
        stage = Path(temporary)
        for name, domain_rules in reduced.items():
            export_domains(stage, name, domain_rules)
        for name, networks in networks_by_name.items():
            export_ips(stage, name, networks)
        write_lines(stage / "build-info.txt", report)
        for name in ("maxmind-COPYRIGHT.txt", "maxmind-LICENSE.txt"):
            shutil.copyfile(inputs / name, stage / name)
        output.mkdir(parents=True, exist_ok=True)
        written = {path.name for path in stage.iterdir()}
        for path in stage.iterdir():
            path.replace(output / path.name)
        # Compiled MRS files belong to the old build until conversion runs again.
        for name in set(build_file_names()) - written:
            (output / name).unlink(missing_ok=True)
    return counts
