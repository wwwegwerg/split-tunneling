import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

type DomainKind = Literal["full", "domain", "keyword"]
type DomainFormat = Literal["geosite", "mihomo", "yaml"]


@dataclass(frozen=True, order=True)
class DomainRule:
    kind: DomainKind
    value: str

    def neutral(self) -> str:
        return f"{self.kind}:{self.value}"

    def classical(self) -> str:
        names = {"full": "DOMAIN", "domain": "DOMAIN-SUFFIX", "keyword": "DOMAIN-KEYWORD"}
        return f"{names[self.kind]},{self.value}"


def clean_line(line: str) -> str:
    """Remove comments and geosite attributes, without changing keyword punctuation."""
    return re.split(r"\s*(?:#|\s@|\s//)", line.strip(), maxsplit=1)[0].strip()


def normalize_domain(value: str) -> str:
    value = value.strip().rstrip(".").lower()
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("Invalid internationalized domain") from error
    if len(value) > 253 or not all(
        re.fullmatch(r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?", part) for part in value.split(".")
    ):
        raise ValueError("Invalid domain name")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise ValueError("An IP address is not a domain rule")


def make_rule(kind: DomainKind, value: str) -> DomainRule:
    if kind == "keyword":
        value = value.strip().lower()
        if not value or any(c.isspace() or c in ",#@" for c in value):
            raise ValueError("Invalid domain keyword")
        return DomainRule(kind, value)
    return DomainRule(kind, normalize_domain(value))


def parse_domains(text: str, format: DomainFormat) -> set[DomainRule]:
    """Bare geosite names match subdomains; bare Mihomo domain entries match exactly."""
    rules: set[DomainRule] = set()
    for number, raw in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = clean_line(raw)
        if not line or line.startswith("//"):
            continue
        if format == "yaml":
            if line == "payload:":
                continue
            if not line.startswith("- "):
                raise ValueError(f"Line {number}: expected a YAML payload entry")
            line = line[2:].strip().strip("\"'")
        try:
            if line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,")):
                prefix, value = line.split(",", 1)
                kinds: dict[str, DomainKind] = {
                    "DOMAIN": "full",
                    "DOMAIN-SUFFIX": "domain",
                    "DOMAIN-KEYWORD": "keyword",
                }
                rule = make_rule(kinds[prefix], value)
            elif line.startswith(("full:", "domain:", "keyword:", "host:")):
                prefix, value = line.split(":", 1)
                match prefix:
                    case "keyword":
                        rule = make_rule("keyword", value)
                    case "full" | "host":
                        rule = make_rule("full", value)
                    case _:
                        rule = make_rule("domain", value)
            elif line.startswith("+."):
                rule = make_rule("domain", line[2:])
            elif line.startswith(".") and format == "mihomo":
                # Mihomo's leading dot matches subdomains only. It cannot be silently widened.
                raise ValueError("Subdomain-only rules are not supported by the neutral format")
            elif line.startswith(".") and format == "geosite":
                # itdog's raw list uses ".ua" for a domain suffix.
                rule = make_rule("domain", line[1:])
            else:
                rule = make_rule("full" if format == "mihomo" else "domain", line)
        except ValueError as error:
            raise ValueError(f"Line {number}: {error}") from error
        rules.add(rule)
    if not rules:
        raise ValueError("Source contains no domain rules")
    return rules


def reduce_domains(rules: Iterable[DomainRule]) -> list[DomainRule]:
    """Remove only rules covered by a suffix rule; exact parents never cover subdomains."""
    unique = set(rules)
    suffixes: set[str] = set()

    def covered(value: str) -> bool:
        labels = value.split(".")
        return any(".".join(labels[index:]) in suffixes for index in range(len(labels)))

    for rule in sorted(unique, key=lambda r: (r.value.count("."), r.value)):
        if rule.kind == "domain" and not covered(rule.value):
            suffixes.add(rule.value)
    return sorted(
        [DomainRule("domain", value) for value in suffixes]
        + [r for r in unique if r.kind == "keyword" or (r.kind == "full" and not covered(r.value))]
    )
