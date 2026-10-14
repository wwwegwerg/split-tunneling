"""Compile IP MRS files and load every provider in a real Mihomo process before publishing."""

import json
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rulesets.exports import DOMAIN_SETS, IP_SETS


def verify(binary: Path, output: Path) -> None:
    binary = binary.resolve()
    output = output.resolve()
    providers: list[tuple[str, str, str, Path, int]] = []
    for name in (*DOMAIN_SETS, *IP_SETS):
        path = output / f"{name}.mihomo.yaml"
        count = len((output / f"{name}.txt").read_text(encoding="utf-8").splitlines())
        behavior = "ipcidr" if name.endswith("-ips") else "classical"
        providers.append((name, behavior, "yaml", path, count))
        if behavior == "ipcidr":
            mrs = path.with_suffix(".mrs")
            subprocess.run(
                [str(binary), "convert-ruleset", "ipcidr", "yaml", str(path), str(mrs)],
                check=True,
            )
            providers.append((name + "-mrs", behavior, "mrs", mrs, count))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    secret = secrets.token_hex(16)
    config = [
        f"external-controller: 127.0.0.1:{port}",
        f"secret: {secret}",
        "log-level: warning",
        "mode: rule",
        "rule-providers:",
    ]
    for name, behavior, format, path, _ in providers:
        config.extend(
            [
                f"  {name}:",
                "    type: file",
                f"    behavior: {behavior}",
                f"    format: {format}",
                f"    path: {json.dumps(str(path))}",
            ]
        )
    config.extend(
        ["rules:", *[f"  - RULE-SET,{p[0]},DIRECT" for p in providers], "  - MATCH,DIRECT"]
    )
    with TemporaryDirectory(prefix="mihomo-check-") as temporary:
        home = Path(temporary)
        # Provider paths live under output, so use it as Mihomo's HomeDir.
        config_path = home / "config.yaml"
        config_path.write_text("\n".join(config) + "\n", encoding="utf-8")
        with (home / "mihomo.log").open("w+") as log:
            process = subprocess.Popen(
                [str(binary), "-d", str(output), "-f", str(config_path)],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                request = Request(
                    f"http://127.0.0.1:{port}/providers/rules",
                    headers={"Authorization": f"Bearer {secret}"},
                )
                for _ in range(100):
                    if process.poll() is not None:
                        break
                    try:
                        with urlopen(request, timeout=1) as response:
                            actual = json.load(response)["providers"]
                        if all(actual.get(p[0], {}).get("ruleCount") == p[4] for p in providers):
                            print(f"Mihomo loaded {len(providers)} providers; rule counts match")
                            break
                    except (URLError, OSError):
                        pass
                    time.sleep(0.1)
                else:
                    raise ValueError(
                        "Mihomo did not load every provider with the expected rule count"
                    )
                if process.poll() is not None:
                    log.seek(0)
                    raise ValueError("Mihomo exited during validation: " + log.read())
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python scripts/verify_mihomo.py")
    verify(Path(".tools/mihomo"), Path("dist"))
