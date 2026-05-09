# Cloudflare Tunnel (`cloudflared`) — Hub & Vault

Configs live beside Compose:

| File | Role |
|------|------|
| `config.hub.yml` | Ingress for Hub VM (`terra…` → API, `app.terra…` → Caddy). |
| `config.vault.yml` | Ingress for Vault VM (`mirror.app.terra…` → Caddy). |

## One-time tunnel creation (per VM)

Run on the VM (after installing `cloudflared` from Cloudflare packages):

```bash
cloudflared tunnel create hub-prod
# Note the printed Tunnel UUID and credentials file path.
cloudflared tunnel route dns hub-prod terra.example.tld
cloudflared tunnel route dns hub-prod app.terra.example.tld
```

Copy the generated credential JSON to:

```text
deploy/cloudflared/credentials/<TUNNEL_UUID>.json   # not committed; see .gitignore
```

Edit `config.hub.yml`: replace both occurrences of `TUNNEL_ID` with that UUID (tunnel id and credentials filename).

Vault VM: repeat with a **second** tunnel (`vault-prod`) and `config.vault.yml`, routing `mirror.app.terra.example.tld`.

## Where credentials live

* **In Compose:** both `hub.yml` and `vault.yml` mount `../cloudflared/credentials` read-only at `/etc/cloudflared/credentials`.
* **Never commit** JSON credentials — only `.gitkeep` is tracked in `credentials/`.

## Changing tunnel ID

1. Create or import the new tunnel; update DNS CNAMEs in Cloudflare to the new tunnel.
2. Replace `TUNNEL_ID` in the matching `config.*.yml` and swap the JSON file under `credentials/`.
3. Redeploy Compose (`docker compose … up -d`).

## Local / CI without credentials

Use **`hub.override.quicktunnel.yml`** / **`vault.override.quicktunnel.yml`** with **`hub.override.dev.yml`** so `cloudflared` runs **`tunnel --url http://caddy:80`** instead of config-file mode. CI keeps replacing `cloudflared` with an Alpine sleep stub via `*.override.ci.yml`.

## Manual acceptance (production)

With DNS + credentials in place:

```text
https://terra.<your-domain>/v1/health   → 200, Hub API JSON
```
