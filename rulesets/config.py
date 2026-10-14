import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from rulesets.domains import DomainFormat
from rulesets.ips import IPFilters


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    group: str
    format: DomainFormat = "geosite"


@dataclass(frozen=True)
class Config:
    sources: tuple[Source, ...]
    filters: IPFilters
    local_domains: Path
    local_telegram_ips: Path


def load_config() -> Config:
    path = Path("config/sources.toml")
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    sources = []
    names: set[str] = set()
    for entry in data["sources"]:
        source = Source(**entry)
        if not re.fullmatch(r"[a-z0-9-]+", source.name) or source.name in names:
            raise ValueError("Source names must be unique filename-safe identifiers")
        if urlsplit(source.url).scheme != "https":
            raise ValueError(f"{source.name}: expected an HTTPS source URL")
        if source.group not in {
            "ru-domains",
            "telegram-domains",
            "blocked-domains",
            "telegram-ips",
            "geofeed",
        }:
            raise ValueError(f"{source.name}: unknown source group")
        if source.format not in {"geosite", "mihomo", "yaml"}:
            raise ValueError(f"{source.name}: unknown domain format")
        names.add(source.name)
        sources.append(source)
    filters = data["ip_filters"]
    strings = cast(dict[str, list[str]], filters)
    return Config(
        tuple(sources),
        IPFilters(
            frozenset(s.upper() for s in strings["countries"]),
            frozenset(s.casefold() for s in strings["asns"]),
            tuple(s.casefold() for s in strings["as_name_keywords"]),
            tuple(s.casefold() for s in strings["as_domain_keywords"]),
            frozenset(s.casefold() for s in strings["as_domains"]),
        ),
        path.parent / data["local"]["ru_domains"],
        path.parent / data["local"]["telegram_ips"],
    )
