#!/usr/bin/env bash
# restore_hub.sh — Hub disaster-recovery glue (M1.11).
# Prerequisites on PATH: bash, docker, docker compose plugin, litestream (same release used in deploy/images),
# Python / uv for Alembic (optional uv — falls back to python -m alembic).
#
# Required env for live restore:
#   LITESTREAM_CONFIG — litestream.yml path (Hub replicate layout).
#   RESTORE_DB_PATH — writable sqlite destination path on host (mount target for Hub api volume).
#   RESTORE_HUB_HEALTH_URL — reachable `/v1/health` URL after compose up.
# Plus Litestream credential env from deploy/litestream/config.yml (`ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`,
# `REPLICA_URL`, `REPLICA_ENDPOINT`, optional `SKIP_VERIFY`).
#
# Optional:
#   ORIGINAL_DB_PATH — logical DB path encoded in Litestream replica metadata (default `/var/lib/terra/db/terra.sqlite`).
#   HUB_COMPOSE_CMD — compose invocation prefix (default minimal hub + dev ports overlay).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

RESTORE_HUB_DRY_RUN="${RESTORE_HUB_DRY_RUN:-0}"
ORIGINAL_DB_PATH="${ORIGINAL_DB_PATH:-/var/lib/terra/db/terra.sqlite}"

have() { command -v "$1" >/dev/null 2>&1; }

if [[ "${RESTORE_HUB_DRY_RUN}" == "1" ]]; then
  # Live restore still requires litestream below; dry-run only asserts tooling CI has for glue checks.
  for binary in bash docker curl python; do
    have "${binary}" || {
      echo "error: missing prerequisite command: ${binary}" >&2
      exit 1
    }
  done
  docker compose version >/dev/null
  echo "RESTORE_HUB_DRY_RUN=1 prerequisite checks passed."
  exit 0
fi

have docker || {
  echo "error: docker not found" >&2
  exit 1
}
have litestream || {
  echo "error: litestream CLI not found — install https://litestream.io/install/" >&2
  exit 1
}
docker compose version >/dev/null

: "${LITESTREAM_CONFIG:?set LITESTREAM_CONFIG}"
: "${RESTORE_DB_PATH:?set RESTORE_DB_PATH}"
: "${RESTORE_HUB_HEALTH_URL:?set RESTORE_HUB_HEALTH_URL}"

mkdir -p "$(dirname "${RESTORE_DB_PATH}")"

litestream restore \
  -config "${LITESTREAM_CONFIG}" \
  -o "${RESTORE_DB_PATH}" \
  "${ORIGINAL_DB_PATH}"

export TI_HUB_ALEMBIC_URL="${TI_HUB_ALEMBIC_URL:-sqlite+aiosqlite:////${RESTORE_DB_PATH}}"

if have uv; then
  uv run alembic -c app/backend/ti_hub/db/alembic.ini upgrade head
else
  python -m alembic -c app/backend/ti_hub/db/alembic.ini upgrade head
fi

HUB_COMPOSE_CMD=${HUB_COMPOSE_CMD:-"docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml --profile minimal"}

eval "${HUB_COMPOSE_CMD} up -d --wait --wait-timeout 300"

python - <<'PYCODE'
import json
import os
import urllib.request

url = os.environ["RESTORE_HUB_HEALTH_URL"]
with urllib.request.urlopen(url, timeout=60) as resp:
    body = json.loads(resp.read().decode("utf-8"))
assert body.get("ok") is True, body
PYCODE

echo "restore_hub.sh completed successfully."
