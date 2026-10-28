#!/usr/bin/env bash
# Installs the clinic-funnel skill for Claude Code. Nothing else is installed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills/clinic-funnel"

if ! command -v python3 >/dev/null 2>&1; then
  echo "This skill needs Python 3, which isn't on this computer yet."
  echo "  Mac: run 'xcode-select --install' (or get it from python.org), then run ./install.sh again."
  echo "  Windows/Linux: install Python 3 from python.org, then run ./install.sh again."
  exit 1
fi

mkdir -p "$HOME/.claude/skills"
if [ -L "$DEST" ] || [ ! -e "$DEST" ]; then
  ln -sfn "$HERE" "$DEST"
elif [ "$(cd "$DEST" && pwd)" != "$HERE" ]; then
  echo "A different clinic-funnel skill is already at $DEST."
  echo "Rename or delete that folder, then run ./install.sh again."
  exit 1
fi

NAME_NOW="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("name",""))' "$HERE/studio.json")"
if [ "$NAME_NOW" = "Your Studio" ] && [ -t 0 ]; then
  read -r -p "Your business name (shown as 'Prototype by ...' on every funnel; Enter to skip): " NAME || NAME=""
  if [ -n "${NAME:-}" ]; then
    python3 -c 'import json,sys;p,n=sys.argv[1:];s=json.load(open(p));s["name"]=n;open(p,"w").write(json.dumps(s,indent=2)+"\n")' "$HERE/studio.json" "$NAME"
  fi
fi

echo ""
echo "Installed. Open Claude Code in any folder and say:"
echo "    build a funnel for @clinichandle"
echo "Claude will ask whether to use photos the clinic sends you or pull them from its Instagram."
