#!/usr/bin/env bash
set -euo pipefail

PRUNE_UNTIL="${PRUNE_UNTIL:-168h}"

echo "Pruning Docker builder cache older than ${PRUNE_UNTIL}..."
docker builder prune -af --filter "until=${PRUNE_UNTIL}"

echo "Pruning unused Docker images older than ${PRUNE_UNTIL}..."
docker image prune -af --filter "until=${PRUNE_UNTIL}"
