# Litestream operations — Hub SQLite → R2 / MinIO

This repository configures **[Litestream](https://litestream.io)** so the Hub authoritative SQLite file at **`/var/lib/terra/db/terra.sqlite`** is replicated to an S3-compatible bucket (Cloudflare **R2** in production, **MinIO** in CI).

Canonical config files:

| File                                                                                       | Purpose                                                                                                   |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| [`deploy/litestream/config.yml`](../../deploy/litestream/config.yml)                       | Production-style replication (`min-checkpoint-page-count: 1024`, retention **720h**, validation **12h**). |
| [`deploy/litestream/config.ci.yml`](../../deploy/litestream/config.ci.yml)                 | Faster checkpoints for CI smoke only (`min-checkpoint-page-count: 1`).                                    |
| [`deploy/litestream/config.vault-pull.yml`](../../deploy/litestream/config.vault-pull.yml) | Vault `r2-pull` worker restore target path (`/var/lib/vault/db/terra.sqlite`), same replica URL as Hub.   |

The Vault **`r2-pull`** worker polls with **`litestream restore`**. Because restore **does not overwrite** an existing output file, the worker deletes `terra.sqlite` and typical sidecars (`-wal`, `-shm`, `-journal`) before each restore so every cycle can reflect the latest replica state (brief read unavailability on Vault during restore).

Compose integrates Litestream behind profile **`litestream`** in [`deploy/compose/hub.yml`](../../deploy/compose/hub.yml). Minimal stacks omit this profile until credentials exist.

For steady replication the Hub stack caps the Litestream service at **48 MiB** (`mem_limit` in `hub.yml`). CI stacks layer [`deploy/compose/hub.override.litestream-ci.yml`](../../deploy/compose/hub.override.litestream-ci.yml), which raises that limit because **`docker compose exec litestream litestream restore …`** runs in the same cgroup as `replicate` and briefly needs more RAM while replaying WAL segments.

## Environment variables (profile `litestream`)

| Variable                              | Purpose                                                                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------- |
| `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY` | Object-store credentials (R2 API token or MinIO root user in CI).                           |
| `REPLICA_ENDPOINT`                    | S3 endpoint URL (R2 `https://<accountid>.r2.cloudflarestorage.com` or `http://minio:9000`). |
| `REPLICA_URL`                         | Replica prefix, e.g. `s3://terra-incognita-prod/litestream/prod/terra.sqlite`.              |
| `SKIP_VERIFY`                         | Set `"true"` only for plain-HTTP MinIO in CI (never in production).                         |

See [`docs/operations/r2-buckets.md`](r2-buckets.md) for frozen bucket names and key layout (M1.9).

## First-time Hub replication (cold bucket)

After the Hub database file exists and credentials are injected (Compose env or systemd):

1. Ensure the bucket exists and IAM allows **PutObject** on `litestream/<env>/…`.
2. Bring up Compose with `--profile minimal --profile litestream`.
3. Optionally force an initial snapshot (Litestream CLI):

```bash
docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml \
  --profile minimal --profile litestream exec litestream \
  litestream replicate -config /etc/litestream.yml
```

(Long-running **`replicate`** is already the default container command; this exec is only needed for one-shot debugging.)

## Restore a copy locally or on a fresh disk

Use the **same replica URL** credentials as replication:

```bash
litestream restore -o /tmp/restored.db -config /etc/litestream.yml /var/lib/terra/db/terra.sqlite
```

For disaster recovery on a blank host, point `-config` at a checked-out `deploy/litestream/config.yml` with env vars set, or use [`scripts/operations/restore_hub.sh`](../../scripts/operations/restore_hub.sh) (M1.11).

## Validation / drift alerts

`validation-interval: 12h` asks Litestream to verify replica integrity. If logs report validation failures:

1. Check R2/MinIO credentials and bucket policies.
2. Confirm clock skew is minimal on the Hub VM.
3. Restore to a scratch path (above) and compare checksums / run Hub migrations against the scratch DB in a maintenance window.

## CI smoke

[`deploy/compose/hub.override.litestream-ci.yml`](../../deploy/compose/hub.override.litestream-ci.yml) adds MinIO plus bucket bootstrap. Pytest marker **`compose_litestream`** (`tests/integration/test_litestream_smoke.py`) runs replicate → restore round-trip.

Manual verification on the Hub VM with **real R2** credentials should still be recorded in the merge PR when first enabling Litestream in production.
