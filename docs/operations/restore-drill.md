# Hub restore drill — fresh VM scenario (M1.11)

Operational companion to [`scripts/operations/restore_hub.sh`](../../scripts/operations/restore_hub.sh).

## Scenario

A newly provisioned Hub VM needs an authoritative SQLite restored from the Litestream replica in R2 (or MinIO in lab environments), then migrated with Alembic, then the Hub Compose stack brought online.

Expected operator time:

- **Under ~5 minutes** when Age/SOPS keys are already on the machine and network egress to R2 works.
- **Under ~15 minutes** when operators must install tooling (`litestream`, `docker`, `uv`) from scratch.

## Preconditions

1. Linux host with Docker Engine + Compose v2 plugin.
2. Litestream CLI **v0.3.13** (match [`deploy/workers/r2-pull/Dockerfile`](../../deploy/workers/r2-pull/Dockerfile)).
3. Repository cloned at `/srv/terra-incognita-v2` (adjust paths below).
4. Decrypted object-store credentials exported into the shell **or** sourced from SOPS per [`secrets/README.md`](../../secrets/README.md).
5. [`deploy/litestream/config.yml`](../../deploy/litestream/config.yml) (Hub writer layout) available with `${ACCESS_KEY_ID}` etc. resolved via Compose `.env` or templating — restore uses the **same replica URL** Hub uses.

## Steps

1. Export Litestream env vars (`ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REPLICA_ENDPOINT`, `REPLICA_URL`, optional `SKIP_VERIFY`).
2. Choose host bind mount path aligned with Hub persistence (`RESTORE_DB_PATH`).
3. Run dry-run once:

```bash
cd /srv/terra-incognita-v2
RESTORE_HUB_DRY_RUN=1 ./scripts/operations/restore_hub.sh
```

4. Execute live restore:

```bash
export LITESTREAM_CONFIG=/srv/terra-incognita-v2/deploy/litestream/config.yml
export RESTORE_DB_PATH=/srv/hub-data/terra.sqlite
export RESTORE_HUB_HEALTH_URL=https://hub.example/v1/health
./scripts/operations/restore_hub.sh
```

Ensure Compose mounts `${RESTORE_DB_PATH}` into `api` service (`hub_db_data` bind migration documented per deployment overlay).

5. Record outcome + timestamps in `catchup.md` (especially failures).

## Full lifecycle drill (pre v1.0)

Execute at least one realistic rehearsal before tagging **`v1.0.0`** (tracked under Phase **M8**); archive findings with Grafana snapshots + Litestream validation logs.
