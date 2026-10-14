import csv
import gzip
import ipaddress
from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import maxminddb

type Network = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(frozen=True)
class IPFilters:
    countries: frozenset[str]
    asns: frozenset[str]
    as_name_keywords: tuple[str, ...]
    as_domain_keywords: tuple[str, ...]
    as_domains: frozenset[str]

    def matches_as(self, asn: str, name: str, domain: str) -> bool:
        return (
            asn.strip().casefold() in self.asns
            or any(keyword in name.casefold() for keyword in self.as_name_keywords)
            or any(keyword in domain.casefold() for keyword in self.as_domain_keywords)
            or domain.strip().casefold() in self.as_domains
        )


def parse_network(value: str) -> Network:
    network = ipaddress.ip_network(value.strip(), strict=False)
    if network.prefixlen == 0:
        raise ValueError("Default routes are not allowed in country/service lists")
    return network


def collapse_networks(networks: Iterable[Network]) -> list[Network]:
    unique = set(networks)
    v4 = [net for net in unique if isinstance(net, ipaddress.IPv4Network)]
    v6 = [net for net in unique if isinstance(net, ipaddress.IPv6Network)]
    collapsed: list[Network] = [
        *ipaddress.collapse_addresses(v4),
        *ipaddress.collapse_addresses(v6),
    ]
    if any(net.prefixlen == 0 for net in collapsed):
        raise ValueError("Aggregation produced a default route")
    return collapsed


def subtract_networks(networks: Iterable[Network], excluded: Iterable[Network]) -> list[Network]:
    """Subtract exact address space, preserving the rest of any containing subnet."""
    original = collapse_networks(networks)
    blocked = collapse_networks(excluded)
    result: list[Network] = []
    for version in (4, 6):
        exclusions = [net for net in blocked if net.version == version]
        ends = [int(net.broadcast_address) for net in exclusions]
        address = ipaddress.IPv4Address if version == 4 else ipaddress.IPv6Address
        for network in original:
            if network.version != version:
                continue
            start = int(network.network_address)
            end = int(network.broadcast_address)
            index = bisect_left(ends, start)
            while index < len(exclusions):
                exclusion = exclusions[index]
                left = int(exclusion.network_address)
                if left > end:
                    break
                if start < left:
                    result.extend(
                        ipaddress.summarize_address_range(address(start), address(left - 1))
                    )
                start = max(start, int(exclusion.broadcast_address) + 1)
                if start > end:
                    break
                index += 1
            if start <= end:
                result.extend(ipaddress.summarize_address_range(address(start), address(end)))
    return result


def parse_cidrs(text: str) -> list[Network]:
    networks = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            networks.append(parse_network(line))
        except ValueError as error:
            raise ValueError(f"Line {number}: invalid CIDR") from error
    if not networks:
        raise ValueError("Source contains no IP networks")
    return networks


def read_ipinfo(path: Path, filters: IPFilters) -> list[Network]:
    networks = []
    matches_as = lru_cache(maxsize=65536)(filters.matches_as)
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        required = {"network", "country_code", "asn", "as_name", "as_domain"}
        if not required.issubset(rows.fieldnames or []):
            raise ValueError("IPinfo CSV is missing required columns")
        for number, row in enumerate(rows, 2):
            if any(row.get(key) is None for key in required) or None in row:
                raise ValueError(f"IPinfo CSV row {number} has the wrong number of columns")
            if row["country_code"].strip().upper() in filters.countries or matches_as(
                row["asn"], row["as_name"], row["as_domain"]
            ):
                try:
                    networks.append(parse_network(row["network"]))
                except ValueError as error:
                    raise ValueError(f"IPinfo CSV row {number}: invalid network") from error
    if not networks:
        raise ValueError("IPinfo selected no networks")
    return networks


def read_maxmind(path: Path, countries: frozenset[str]) -> list[Network]:
    networks: list[Network] = []
    with maxminddb.open_database(path) as reader:
        if "Country" not in reader.metadata().database_type:
            raise ValueError("Expected a MaxMind Country database")
        for network, record in reader:
            if not isinstance(record, dict):
                continue
            country = record.get("country")
            if isinstance(country, dict) and country.get("iso_code") in countries:
                networks.append(parse_network(str(network)))
    if not networks:
        raise ValueError("MaxMind selected no networks")
    return networks


def read_geofeed(path: Path, countries: frozenset[str]) -> list[Network]:
    networks = []
    rows_seen = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for number, row in enumerate(csv.reader(stream), 1):
            if not row or row[0].lstrip().startswith("#"):
                continue
            rows_seen += 1
            if len(row) < 2:
                raise ValueError(f"Geofeed row {number}: expected prefix,country")
            # Empty country fields are allowed by RFC 8805; validate the prefix anyway.
            try:
                network = parse_network(row[0])
            except ValueError as error:
                raise ValueError(f"Geofeed row {number}: invalid network") from error
            if row[1].strip().upper() in countries:
                networks.append(network)
    if not rows_seen:
        raise ValueError("Geofeed contains no records")
    return networks
