#!/usr/bin/env bash
# Regenerate and deploy every surface in this composition directory.
#
# lc_parks is a *composition*: the single source `lc_parks.nt` generates BOTH
# namespaced surfaces (ck_lc_parks__launch_control + ck_lc_parks__parks) in one
# gen.py run. This script regenerates them, then runs each generated surface's
# own deploy.sh to copy it into Ableton's MIDI Remote Scripts dir.
#
# Restart Ableton Live afterwards to pick up the changes (and rebuild/restart
# the HUD app if its protocol changed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Regenerating composition: live_surfaces/lc_parks/lc_parks.nt"
( cd "$REPO_ROOT" && poetry run python ableton_control_surface_as_code/gen.py \
    live_surfaces/lc_parks/lc_parks.nt )

# Deploy every generated surface (each emits its own deploy.sh).
shopt -s nullglob
deployed=0
while IFS= read -r -d '' deploy_sh; do
    deploy_dir="$(dirname "$deploy_sh")"
    echo "Deploying: ${deploy_dir#"$REPO_ROOT/"}"
    ( cd "$deploy_dir" && bash deploy.sh )
    deployed=$((deployed + 1))
done < <(find "$SCRIPT_DIR" -mindepth 2 -maxdepth 2 -name deploy.sh -print0 | sort -z)

if [[ "$deployed" -eq 0 ]]; then
    echo "No surfaces found to deploy (expected generated ck_lc_parks__* dirs)." >&2
    exit 1
fi

echo "Done — deployed $deployed surface(s). Restart Ableton Live to load them."
