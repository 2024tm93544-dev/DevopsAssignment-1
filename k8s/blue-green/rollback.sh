#!/bin/bash
set -e

PREVIOUS_COLOR=$(kubectl get configmap blue-green-state -n default -o jsonpath='{.data.previous-color}')

if [ "$PREVIOUS_COLOR" = "none" ] || [ -z "$PREVIOUS_COLOR" ]; then
    echo "No previous deployment to roll back to — skipping."
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/switch-traffic.sh" "$PREVIOUS_COLOR"

echo "================================================"
echo "  ROLLBACK COMPLETE: now serving $PREVIOUS_COLOR"
echo "================================================"
