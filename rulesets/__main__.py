import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from rulesets.build import generate
from rulesets.config import load_config
from rulesets.download import fetch_inputs


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python -m rulesets")
    try:
        config = load_config()
        with TemporaryDirectory(prefix="split-tunneling-") as temporary:
            inputs = Path(temporary)
            hashes = fetch_inputs(config, inputs)
            counts = generate(config, inputs, Path("dist"), hashes=hashes)
        for name in ("ru-domains", "ru-ips", "telegram-domains", "telegram-ips"):
            print(f"{name}: {counts[name]}")
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
