# Vault R2-pull worker

Python asyncio worker (`pull.py`) pulls the Hub Litestream replica into `/var/lib/vault/db/terra.sqlite` on a fixed cadence (default **30 s**, exponential backoff to **5 min** on failures).

## Endpoints (container)

| Port     | Purpose                                                             |
| -------- | ------------------------------------------------------------------- |
| **8081** | Prometheus `/metrics`                                               |
| **8082** | JSON `GET /vault/status` (proxied by edge Caddy as `/vault/status`) |

## Required configuration

- Litestream CLI **v0.3.13** (installed in the image).
- Replica credentials + URL aligned with Hub (`deploy/litestream/config.vault-pull.yml` mounted at `/etc/litestream.yml`).

Environment variables mirror Hub Litestream (`ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REPLICA_ENDPOINT`, `REPLICA_URL`, `SKIP_VERIFY`).

See [`docs/operations/litestream.md`](../../docs/operations/litestream.md) and [`docs/operations/r2-buckets.md`](../../docs/operations/r2-buckets.md).
