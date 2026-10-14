import json
from pathlib import Path

from rulesets.domains import DomainRule
from rulesets.ips import Network

DOMAIN_SETS = ("ru-domains", "telegram-domains")
IP_SETS = ("ru-ips", "telegram-ips")


def asset_names() -> list[str]:
    names = [
        f"{name}.{suffix}"
        for name in DOMAIN_SETS
        for suffix in ("txt", "mihomo.yaml", "shadowrocket.list")
    ]
    names.extend(
        f"{name}.{suffix}"
        for name in IP_SETS
        for suffix in ("txt", "mihomo.mrs", "shadowrocket.list", "amnezia.json")
    )
    return sorted(names)


def build_file_names() -> list[str]:
    """Includes intermediate IP YAML and metadata used to prepare the release description."""
    return sorted(
        [
            *asset_names(),
            *[f"{name}.mihomo.yaml" for name in IP_SETS],
            "build-info.txt",
            "maxmind-COPYRIGHT.txt",
            "maxmind-LICENSE.txt",
        ]
    )


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def export_domains(output: Path, name: str, rules: list[DomainRule]) -> None:
    write_lines(output / f"{name}.txt", [rule.neutral() for rule in rules])
    classical = [rule.classical() for rule in rules]
    write_lines(output / f"{name}.shadowrocket.list", classical)
    write_lines(
        output / f"{name}.mihomo.yaml",
        ["payload:"] + [f"  - {json.dumps(line, ensure_ascii=False)}" for line in classical],
    )


def export_ips(output: Path, name: str, networks: list[Network]) -> None:
    write_lines(output / f"{name}.txt", [str(net) for net in networks])
    write_lines(
        output / f"{name}.shadowrocket.list",
        [f"{'IP-CIDR' if net.version == 4 else 'IP-CIDR6'},{net}" for net in networks],
    )
    write_lines(
        output / f"{name}.mihomo.yaml",
        ["payload:"] + [f'  - "{net}"' for net in networks],
    )
    # AmneziaVPN's site importer preserves IPv4 CIDRs in hostname (since 5.0.1.5).
    # It cannot represent our IPv6 or domain-matching rules.
    sites = [{"hostname": str(net), "ip": ""} for net in networks if net.version == 4]
    (output / f"{name}.amnezia.json").write_text(
        json.dumps(sites, separators=(",", ":")) + "\n", encoding="utf-8"
    )
