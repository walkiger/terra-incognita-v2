# Hub compose stack (M0.3)

Minimal hub skeleton: **Caddy** → **API** stub (`/v1/health`), **NATS**, **cloudflared**, optional **node-exporter**.

## Profiles

| Profile | Command |
|---------|---------|
| **`minimal`** | From repo root: `docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml --profile minimal up -d --build` — core services only (mem limits Σ ≤ 720 MB). |
| **`default`** (full monitoring) | Same files plus `--profile default` — adds **prom-node-exporter** (Linux host mounts). |

Core services are listed under **both** `minimal` and `default`; exporters only under `default`.

## Ports

- **Caddy:** host `127.0.0.1:8080` → container `:80` (see `hub.override.dev.yml`). Health check: `GET /v1/health` → API.

## CI / headless

Use **`hub.override.ci.yml`** so **cloudflared** is replaced with a no-op stub (no outbound tunnel). Example:

```bash
docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.ci.yml \
  -f deploy/compose/hub.override.dev.yml \
  --profile minimal up -d --build --wait --wait-timeout 240
curl -fsS http://127.0.0.1:8080/v1/health
```

Copy **`env.example`** to `.env` only when you need tunable vars (tokens land in M0.5).
