# Deploy — Compose stacks (M0)

Two sibling stacks live under **`deploy/compose/`**: **hub** (M0.3) and **vault** (M0.4). Both support **`minimal`** vs **`default`** profiles (`default` adds **prom-node-exporter** with Linux host mounts).

---

## Hub compose stack (M0.3)

Minimal hub skeleton: **Caddy** → **API** stub (`/v1/health`), **NATS**, **cloudflared**, optional **node-exporter**.

### Profiles

| Profile                         | Command                                                                                                                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`minimal`**                   | From repo root: `docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml --profile minimal up -d --build` — core services only (mem limits Σ ≤ 720 MB). |
| **`default`** (full monitoring) | Same files plus `--profile default` — adds **prom-node-exporter**.                                                                                                              |

Core services are listed under **both** `minimal` and **`default`**; exporters only under **`default`**.

### Ports

- **Hub Caddy:** host `127.0.0.1:8080` → container `:80` (see `hub.override.dev.yml`). Health check: `GET /v1/health` → API.

### CI / headless (hub)

Use **`hub.override.ci.yml`** so **cloudflared** is replaced with a no-op stub (no outbound tunnel). Example:

```bash
docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.ci.yml \
  -f deploy/compose/hub.override.dev.yml \
  --profile minimal up -d --build --wait --wait-timeout 240
curl -fsS http://127.0.0.1:8080/v1/health
```

Copy **`compose/env.example`** to `.env` only when you need tunable vars (tokens land in M0.5).

---

## Vault compose stack (M0.4)

Vault / mirror VM skeleton: **Caddy** serves a JSON heartbeat on **`GET /`**, **cloudflared**, **r2-pull** stub (Alpine sleep loop + disk layout until M1.10), optional **node-exporter**.

### Profiles

| Profile       | Command                                                                                                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`minimal`** | From repo root: `docker compose -f deploy/compose/vault.yml -f deploy/compose/vault.override.dev.yml --profile minimal up -d --build` — Σ **`mem_limit`** ≤ **480 MB**. |
| **`default`** | Same plus **`prom-node-exporter`**.                                                                                                                                     |

### Ports

- **Vault Caddy:** host `127.0.0.1:8081` → container `:80` (see `vault.override.dev.yml`). Stub payload: `{"ok":true,"role":"vault","version":"0.0.1-bootstrap"}`.

### CI / headless (vault)

Use **`vault.override.ci.yml`** for the cloudflared stub, same pattern as hub:

```bash
docker compose -f deploy/compose/vault.yml -f deploy/compose/vault.override.ci.yml \
  -f deploy/compose/vault.override.dev.yml \
  --profile minimal up -d --build --wait --wait-timeout 240
curl -fsS http://127.0.0.1:8081/
```
