import unittest

from rulesets.domains import DomainRule, parse_domains, reduce_domains


class DomainTests(unittest.TestCase):
    def test_upstream_formats_preserve_exact_suffix_and_keyword(self) -> None:
        self.assertEqual(
            parse_domains("API.Example.com\n+.example.org\n", "mihomo"),
            {DomainRule("full", "api.example.com"), DomainRule("domain", "example.org")},
        )
        self.assertEqual(
            parse_domains("full:api.example.com\nexample.org\nkeyword:.bank.\n", "geosite"),
            {
                DomainRule("full", "api.example.com"),
                DomainRule("domain", "example.org"),
                DomainRule("keyword", ".bank."),
            },
        )

    def test_yaml_keywords_survive_export_without_wildcard_conversion(self) -> None:
        rules = parse_domains('payload:\n  - "DOMAIN-KEYWORD,sber."\n', "yaml")
        self.assertEqual(next(iter(rules)).classical(), "DOMAIN-KEYWORD,sber.")

    def test_only_suffix_rules_cover_child_domains(self) -> None:
        rules = parse_domains(
            "full:example.com\nfull:a.example.com\ndomain:example.org\n"
            "full:a.example.org\ndomain:b.example.org\nfull:otherexample.org\nkeyword:example\n",
            "geosite",
        )
        self.assertEqual(
            set(reduce_domains(rules)),
            {
                DomainRule("full", "example.com"),
                DomainRule("full", "a.example.com"),
                DomainRule("domain", "example.org"),
                DomainRule("full", "otherexample.org"),
                DomainRule("keyword", "example"),
            },
        )

    def test_comments_attributes_idna_and_top_level_domains(self) -> None:
        self.assertEqual(
            parse_domains(
                "# comment\n// comment\ndomain:ПРИМЕР.РФ. @ru # note\ndomain:by\n", "geosite"
            ),
            {DomainRule("domain", "xn--e1afmkfd.xn--p1ai"), DomainRule("domain", "by")},
        )

    def test_unsupported_or_malformed_rules_fail_instead_of_disappearing(self) -> None:
        with self.assertRaisesRegex(ValueError, "Subdomain-only"):
            parse_domains(".example.com", "mihomo")
        for text in (
            "include:other",
            "regexp:.*example",
            "keyword:",
            "domain:bad..com",
            "full:https://example.com",
            "DOMAIN,example.com,DIRECT",
            "192.0.2.1",
            "<html>",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_domains(text, "geosite")
