#!/usr/bin/env bash
set -euo pipefail

if (( $# )); then
  printf '%s\n' 'Usage: bash scripts/install-mihomo.sh' >&2
  exit 1
fi

# Pin both the version and the compressed binary digest from its GitHub release.
version=1.19.32
digest=8451100836c9eda194331c2babfad490b2faf30cebc1a04b0e76fd8ac2d35d10
destination=.tools/mihomo
archive="$(mktemp)"
trap 'rm -f "$archive"' EXIT
curl -fsSL --retry 3 --connect-timeout 15 --max-time 180 \
  "https://github.com/MetaCubeX/mihomo/releases/download/v${version}/mihomo-linux-amd64-v${version}.gz" \
  -o "$archive"
printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status
mkdir -p "$(dirname "$destination")"
gzip -dc "$archive" > "$destination"
chmod +x "$destination"
"$destination" -v
