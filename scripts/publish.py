"""Publish a complete build as a new release; existing downloads stay available."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rulesets.exports import asset_names


def publication_files(output: Path) -> list[Path]:
    if "\nMode: full\n" not in (output / "build-info.txt").read_text(encoding="utf-8"):
        raise ValueError("Publication requires a full build")
    files = [output / name for name in asset_names()]
    for path in files:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing release file: {path.name}; run Mihomo validation first")
    return files


def release_notes(output: Path, commit: str) -> str:
    report = (output / "build-info.txt").read_text(encoding="utf-8")
    fields = dict(line.split(": ", 1) for line in report.splitlines() if ": " in line)
    source_hashes = report.partition("\nSource SHA-256:\n")[2].strip()
    notices = "\n\n".join(
        (output / name).read_text(encoding="utf-8").strip()
        for name in ("maxmind-COPYRIGHT.txt", "maxmind-LICENSE.txt")
    )
    notices += (
        "\n\n"
        + (Path(__file__).resolve().parents[1] / "third-party-notices.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    text = (
        f"Сборка: {fields['Generated']}. GeoLite2 Country: {fields['GeoLite build']}.\n\n"
        f"[Исходники и условия](https://github.com/wwwegwerg/split-tunneling/blob/{commit}/SOURCES.md).\n\n"
        "IP address data powered by [IPinfo](https://ipinfo.io).\n"
        "This product includes GeoLite Data created by [MaxMind](https://www.maxmind.com).\n\n"
        "Изменения в IP-данных: отбор, объединение, агрегация и преобразование форматов. "
        "Собственные изменения — [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).\n\n"
    )
    if source_hashes:
        text += (
            "<details>\n<summary>Снимки источников (SHA-256 скачанных файлов)</summary>\n\n"
            f"```text\n{source_hashes}\n```\n\n</details>\n\n"
        )
    return text + (
        "<details>\n<summary>Copyright и лицензионные уведомления</summary>\n\n"
        f"{notices}\n\n</details>\n"
    )


def publish() -> None:
    files = publication_files(Path("dist"))
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, stdout=subprocess.PIPE, text=True
    ).stdout.strip()
    now = datetime.now(UTC)
    tag = now.strftime("rules-%Y%m%dT%H%M%SZ")
    with TemporaryDirectory() as temporary:
        notes = Path(temporary) / "notes.md"
        notes.write_text(
            release_notes(Path("dist"), commit),
            encoding="utf-8",
        )
        # gh creates a draft, uploads all assets, then publishes it as latest.
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag,
                *map(str, files),
                "--repo",
                "wwwegwerg/split-tunneling",
                "--target",
                commit,
                "--latest",
                "--title",
                f"Rules {now:%Y-%m-%d}",
                "--notes-file",
                str(notes),
            ],
            check=True,
        )


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python scripts/publish.py")
    publish()
