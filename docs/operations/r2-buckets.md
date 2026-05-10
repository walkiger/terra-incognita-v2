# R2 buckets, object layout, and IAM (M1.9)

Cloudflare **R2** is the canonical object store for Litestream replicas, snapshot payloads (later engine flows), and operational bundles. This document freezes **bucket names**, **key prefixes**, **API token roles**, and **rotation** expectations. Values are mirrored operationally via **SOPS** under `secrets/` (see [`secrets/README.md`](../../secrets/README.md)).

## Bucket names (frozen)

| Environment            | Bucket name            |
| ---------------------- | ---------------------- |
| Production             | `terra-incognita-prod` |
| Development / CI smoke | `terra-incognita-dev`  |

CI Litestream compose stacks may use an ephemeral **`terra-litestream-ci`** bucket inside embedded MinIO (not R2) — see [`litestream.md`](litestream.md).

## Object key layout

```
litestream/<env>/<logical-db-path>/…           # Litestream replication trees
snapshots/<user_id>/<ts>-<sha256>.tar.zst      # Engine snapshot payloads (future upload flow)
replay-bundles/<user_id>/<bundle_id>.tar.zst   # Optional replay bundles (M7)
audit-logs/<yyyy>/<mm>/<dd>.jsonl.zst          # Audit logs (later phase)
snapshots/manifest/…                           # Manifest pointers readable by Vault mirror (read-mostly)
```

`<env>` examples: `prod`, `dev`, `ci` — align with `LITESTREAM_ENV` / deployment overlay naming.

## API tokens (logical roles)

| Token name      | Scope                                                            | Intended use                                   |
| --------------- | ---------------------------------------------------------------- | ---------------------------------------------- |
| `terra-hub-rw`  | Read/write on **all** prefixes in the Hub bucket                 | Hub VM / Litestream writer + snapshot pipeline |
| `terra-vault-r` | Read-only on `litestream/` **and** read on `snapshots/manifest/` | Vault `r2-pull` restore worker                 |
| `terra-ci-rw`   | Read/write **only** on `terra-incognita-dev`                     | GitHub Actions / developer CI buckets          |

Create tokens in the Cloudflare dashboard (R2 → Manage R2 API Tokens). Store **only** encrypted material in SOPS (`hub.sops.yaml`); never commit plaintext secrets.

### Rotation policy

- Rotate tokens at least every **180 days** (calendar reminder).
- Document rotation date in `catchup.md` when performed (who/when/buckets touched).

### Cost notes

- R2 bills on storage + Class A/B operations. Litestream steady churn stays small at MVP scale but spikes during bulk restores / snapshot uploads — watch **operations/day** on early tenants.
- Prefer lifecycle rules on snapshot prefixes (below) to avoid unbounded growth.

## Lifecycle (snapshots prefix)

For `snapshots/` enable an R2 lifecycle rule via dashboard or API:

- Delete non-current versions **older than 30 days**, retaining at least the latest full snapshot pointer policy described in phase docs.

Implementation is **operator-applied** (dashboard/API), not implied to be automated by this repo’s Compose stack.

## Manual smoke (developer laptop)

With `terra-ci-rw` against **dev** bucket:

```bash
aws s3 ls "s3://terra-incognita-dev/" \
  --endpoint-url "https://${CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
```

Use credentials exported from decrypted SOPS locally — never paste secrets into shell history on shared machines.

## Vault secrets schema (reference)

`vault.sops.yaml` is optional until the Vault VM encrypts its own secrets file; expected logical keys mirror Hub (`R2_*` style placeholders). Until that file exists in-repo, operators store Vault RO credentials alongside Hub secrets policy documented here.
