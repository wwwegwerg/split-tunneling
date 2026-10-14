"""Delete this generator's expired releases even when source downloads fail."""

import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta


def expired_releases(
    releases: Iterable[Mapping[str, object]], now: datetime
) -> list[tuple[str, bool]]:
    expired = []
    for release in releases:
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not re.fullmatch(r"rules-\d{8}T\d{6}Z", tag):
            continue
        # GitHub created_at may reflect the target commit's date; our tag records build time.
        created = datetime.strptime(tag, "rules-%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        draft = bool(release.get("draft"))
        lifetime = timedelta(days=1 if draft else 7)
        if created <= now - lifetime:
            expired.append((tag, draft))
    return expired


def prune() -> None:
    repository = "wwwegwerg/split-tunneling"
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases?per_page=100", "--paginate", "--slurp"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    pages: list[list[dict[str, object]]] = json.loads(result.stdout)
    releases = (release for page in pages for release in page)
    for tag, draft in expired_releases(releases, datetime.now(UTC)):
        command = ["gh", "release", "delete", tag, "--repo", repository, "--yes"]
        # An interrupted upload can leave a draft whose Git tag was never created.
        if not draft:
            command.append("--cleanup-tag")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python scripts/prune_releases.py")
    prune()
