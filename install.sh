#!/usr/bin/env bash
# Installs the clinic-funnel skill for Claude Code: ~/.claude/skills/clinic-funnel -> this folder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills/clinic-funnel"
mkdir -p "$HOME/.claude/skills"
if [ -e "$DEST" ] && [ "$(readlink "$DEST" || true)" != "$HERE" ]; then
  echo "Something already exists at $DEST. Move it, then run this again." >&2; exit 1
fi
ln -sfn "$HERE" "$DEST"
python3 -m pip install --quiet --user pillow playwright || echo "Install Pillow + Playwright yourself: python3 -m pip install pillow playwright"
if [ "$(python3 -c 'import json;print(json.load(open("'"$HERE"'/studio.json"))["name"])')" = "Your Studio" ]; then
  read -r -p "Your studio or agency name (shown as 'Prototype by ...' on every funnel): " NAME || NAME=""
  if [ -n "${NAME:-}" ]; then
    python3 - "$HERE/studio.json" "$NAME" <<'PY'
import json, sys
p, name = sys.argv[1], sys.argv[2]
s = json.load(open(p)); s["name"] = name; json.dump(s, open(p, "w"), indent=2); open(p, "a").write("\n")
PY
  fi
fi
echo "Installed. In Claude Code say: build a funnel for @clinichandle   (or /clinic-funnel)"
echo "Needs: the Apify connector in Claude (for Instagram), and Google Chrome (for the screen check)."
