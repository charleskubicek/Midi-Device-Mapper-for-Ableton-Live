#!/usr/bin/env bash
# Launch the mapping editor.
#
#   ./run-ui.sh                          # normal launch
#   ./run-ui.sh <controller.nt>          # auto-load a controller file
#   ./run-ui.sh <controller.nt> --demo   # …and seed example mappings
#   ./run-ui.sh --dev                    # electron-vite dev mode (hot reload)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d node_modules ]; then
  echo "Installing dependencies…"
  npm install
fi

if [ "${1:-}" = "--dev" ]; then
  exec npm run dev
fi

if [ -n "${1:-}" ]; then
  export MAPPING_EDITOR_CONTROLLER="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
fi
if [ "${2:-}" = "--demo" ]; then
  export MAPPING_EDITOR_DEMO=1
fi

npm run build
exec npx electron out/main/index.js
