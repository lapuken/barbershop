#!/usr/bin/env bash
set -euo pipefail

resource_group="$1"
job_name="$2"
image="$3"

echo "Updating migration job image to ${image}"
az containerapp job update \
  --resource-group "${resource_group}" \
  --name "${job_name}" \
  --image "${image}" \
  --output none

echo "Starting migration job execution"
execution_name="$(
  az containerapp job start \
    --resource-group "${resource_group}" \
    --name "${job_name}" \
    --query name \
    --output tsv
)"

echo "Waiting for execution ${execution_name}"
attempt=0
while [[ "${attempt}" -lt 60 ]]; do
  status="$(
    az containerapp job execution show \
      --resource-group "${resource_group}" \
      --name "${job_name}" \
      --job-execution-name "${execution_name}" \
      --query properties.status \
      --output tsv
  )"
  case "${status}" in
    Succeeded)
      echo "Migration job completed successfully."
      exit 0
      ;;
    Failed|Stopped)
      echo "Migration job failed with status ${status}." >&2
      exit 1
      ;;
  esac
  attempt=$((attempt + 1))
  sleep 10
done

echo "Timed out waiting for migration job execution ${execution_name}." >&2
exit 1
