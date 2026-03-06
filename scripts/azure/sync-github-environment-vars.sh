#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/azure/sync-github-environment-vars.sh <environment> [options]

Options:
  --repo <owner/name>          GitHub repository. Defaults to the current gh repo.
  --backend-config <path>      Backend HCL file. Defaults to infra/env/<environment>/backend.hcl
  --dry-run                    Print values without writing to GitHub.
  -h, --help                   Show this help text.
EOF
}

require_cmd() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    echo "Missing required command: ${name}" >&2
    exit 1
  fi
}

read_backend_value() {
  local backend_path="$1"
  local key="$2"
  python3 - "${backend_path}" "${key}" <<'PY'
import re
import sys

path = sys.argv[1]
key = sys.argv[2]
pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*\"([^\"]*)\"\s*$")

with open(path, "r", encoding="utf-8") as handle:
    for raw_line in handle:
        line = raw_line.split("#", 1)[0].split("//", 1)[0].strip()
        match = pattern.match(line)
        if match:
            print(match.group(1))
            sys.exit(0)

print(f"Unable to read `{key}` from {path}.", file=sys.stderr)
sys.exit(1)
PY
}

ENVIRONMENT=""
REPO=""
BACKEND_CONFIG=""
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --backend-config)
      BACKEND_CONFIG="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -z "${ENVIRONMENT}" ]]; then
        ENVIRONMENT="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "${ENVIRONMENT}" ]]; then
  usage
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
BACKEND_CONFIG="${BACKEND_CONFIG:-${INFRA_DIR}/env/${ENVIRONMENT}/backend.hcl}"

require_cmd gh
require_cmd terraform
require_cmd python3

if [[ -z "${REPO}" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

if [[ -z "${REPO}" ]]; then
  echo "Unable to determine GitHub repository. Pass --repo <owner/name>." >&2
  exit 1
fi

if [[ ! -f "${BACKEND_CONFIG}" ]]; then
  echo "Backend config not found: ${BACKEND_CONFIG}" >&2
  exit 1
fi

gh api "repos/${REPO}/environments/${ENVIRONMENT}" >/dev/null

TFSTATE_RESOURCE_GROUP="$(read_backend_value "${BACKEND_CONFIG}" "resource_group_name")"
TFSTATE_STORAGE_ACCOUNT="$(read_backend_value "${BACKEND_CONFIG}" "storage_account_name")"
TFSTATE_CONTAINER="$(read_backend_value "${BACKEND_CONFIG}" "container_name")"

terraform -chdir="${INFRA_DIR}" init -input=false -reconfigure -backend-config="${BACKEND_CONFIG}" >/dev/null

OUTPUT_JSON="$(terraform -chdir="${INFRA_DIR}" output -json github_environment_variables)"

set_var() {
  local key="$1"
  local value="$2"

  if [[ -z "${value}" && ( "${key}" == "AZURE_CONTAINER_APP_NAME" || "${key}" == "AZURE_MIGRATION_JOB_NAME" ) ]]; then
    echo "Skipping ${key}: value is empty (application resources not deployed yet)."
    return
  fi

  if [[ "${DRY_RUN}" == "true" ]]; then
    printf 'Would set [%s] %s=%q\n' "${ENVIRONMENT}" "${key}" "${value}"
    return
  fi

  gh variable set "${key}" \
    --repo "${REPO}" \
    --env "${ENVIRONMENT}" \
    --body "${value}"
  echo "Set ${key}"
}

while IFS=$'\t' read -r key value; do
  set_var "${key}" "${value}"
done < <(
  python3 - <<'PY' "${OUTPUT_JSON}"
import json
import sys

payload = json.loads(sys.argv[1])
value = payload.get("value", {})
if not isinstance(value, dict):
    print("Terraform output `github_environment_variables` is not a map.", file=sys.stderr)
    sys.exit(1)

for key in sorted(value.keys()):
    raw = value[key]
    if raw is None:
        rendered = ""
    elif isinstance(raw, (list, dict)):
        rendered = json.dumps(raw, separators=(",", ":"))
    else:
        rendered = str(raw)
    print(f"{key}\t{rendered}")
PY
)

set_var "TFSTATE_RESOURCE_GROUP" "${TFSTATE_RESOURCE_GROUP}"
set_var "TFSTATE_STORAGE_ACCOUNT" "${TFSTATE_STORAGE_ACCOUNT}"
set_var "TFSTATE_CONTAINER" "${TFSTATE_CONTAINER}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "Dry run complete for ${REPO} environment ${ENVIRONMENT}."
else
  echo "GitHub environment variable sync complete for ${REPO} environment ${ENVIRONMENT}."
fi
