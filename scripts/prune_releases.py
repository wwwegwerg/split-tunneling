"""Keep the latest published release after a successful update."""

import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping


def previous_releases(
    releases: Iterable[Mapping[str, object]], latest: str
) -> list[tuple[str, bool]]:
    previous = []
    for release in releases:
        tag = release.get("tag_name")
        if (
            not isinstance(tag, str)
            or tag == latest
            or not re.fullmatch(r"rules-\d{8}T\d{6}Z", tag)
        ):
            continue
        previous.append((tag, bool(release.get("draft"))))
    return previous


def prune() -> None:
    repository = "wwwegwerg/split-tunneling"
    latest = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases/latest", "--jq", ".tag_name"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases?per_page=100", "--paginate", "--slurp"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    pages: list[list[dict[str, object]]] = json.loads(result.stdout)
    releases = (release for page in pages for release in page)
    for tag, draft in previous_releases(releases, latest):
        command = ["gh", "release", "delete", tag, "--repo", repository, "--yes"]
        # An interrupted upload can leave a draft whose Git tag was never created.
        if not draft:
            command.append("--cleanup-tag")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python scripts/prune_releases.py")
    prune()
