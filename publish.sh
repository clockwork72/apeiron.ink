#!/usr/bin/env bash
# Build the site and push it live. GitHub Pages serves docs/ from branch agent/site.
# Usage: ./publish.sh ["commit message"]
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
git add -A
git diff --cached --quiet && { echo "Nothing new to publish."; exit 0; }
git commit -q -m "${1:-Publish}"
git push -q origin HEAD:agent/site
echo "Pushed. Live at https://apeiron.ink in about a minute."
