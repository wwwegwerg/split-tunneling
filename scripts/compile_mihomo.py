"""Convert the IP rule sets from YAML to MRS."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rulesets.exports import IP_SETS

if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python scripts/compile_mihomo.py")
    for name in IP_SETS:
        subprocess.run(
            [
                ".tools/mihomo",
                "convert-ruleset",
                "ipcidr",
                "yaml",
                f"dist/{name}.mihomo.yaml",
                f"dist/{name}.mihomo.mrs",
            ],
            check=True,
        )
