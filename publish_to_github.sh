#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
repo="riotcore/static-mudforge-support"
[[ -f plugins.json && -f dist/stillwake-map-companion.json ]] || {
  echo 'STOP: not inside the standalone MudForge pack.' >&2; exit 2;
}
command -v git >/dev/null || { echo 'STOP: install git'; exit 2; }
command -v gh >/dev/null || { echo 'STOP: install/authenticate GitHub CLI (gh)'; exit 2; }
gh auth status >/dev/null || { echo 'STOP: run gh auth login'; exit 2; }
[[ ! -e .git ]] || { echo 'STOP: this folder is already a Git repository.' >&2; exit 2; }
git init -b main
# Allowlist only the public package; never accidentally stage other files.
git add -- README.md LICENSE plugins.json github.com/plugins.json \
  dist/stillwake-map-companion.json static_map_companion.lua \
  stillwake_terrain_pack.json stillwake-terrain-v1.json \
  tools/repair_mudforge_export.py tools/test_terrain_repair.py \
  publish_to_github.sh
git -c user.name='STATIC' -c user.email='static@users.noreply.github.com' \
  commit -m 'Initial public MudForge-only support package'
echo "Creating PUBLIC GitHub repo $repo (not Static2.0)."
gh repo create "$repo" --public --source . --remote origin --push
printf 'Published: https://github.com/%s\n' "$repo"
