#!/usr/bin/env bash
set -euo pipefail

resource_group="$1"
container_app_name="$2"

for attempt in $(seq 1 60); do
  fqdn="$(
    az containerapp show \
      --resource-group "${resource_group}" \
      --name "${container_app_name}" \
      --query properties.configuration.ingress.fqdn \
      --output tsv
  )"

  if [[ -n "${fqdn}" ]] && curl --fail --silent --show-error "https://${fqdn}/healthz/" >/tmp/healthz.json; then
    cat /tmp/healthz.json
    exit 0
  fi

  sleep 10
done

echo "Container App health endpoint did not become ready in time." >&2
exit 1
