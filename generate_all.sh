#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies..."
poetry -C "$SCRIPT_DIR" install --sync

for controller_dir in "$SCRIPT_DIR"/live_surfaces/*/; do
    gen_sh="${controller_dir%/}/generate.sh"
    [[ -f "$gen_sh" ]] || continue

    rel="${gen_sh#"$SCRIPT_DIR/"}"
    echo "Generating: $rel"
    (cd "$controller_dir" && bash generate.sh)

    while IFS= read -r -d '' deploy_sh; do
        deploy_dir="$(dirname "$deploy_sh")"
        deploy_rel="${deploy_sh#"$SCRIPT_DIR/"}"
        echo "Deploying: $deploy_rel"
        (cd "$deploy_dir" && bash deploy.sh)
    done < <(find "$controller_dir" -maxdepth 2 -name "deploy.sh" -print0 | sort -z)
done

echo "Done."
