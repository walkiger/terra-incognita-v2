# Cloudflare Tunnel (`cloudflared`) — Hub & Vault

Configs live beside Compose:

| File               | Role                                                       |
| ------------------ | ---------------------------------------------------------- |
| `config.hub.yml`   | Ingress for Hub VM (`terra…` → API, `app.terra…` → Caddy). |
| `config.vault.yml` | Ingress for Vault VM (`mirror.app.terra…` → Caddy).        |

## Operating modes (pick one connector per tunnel)

| Mode                           | When                                                                                                                 | Origin / routing                                                                                                                                                                                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Container + `config.*.yml`** | Credential JSON under `credentials/`; Compose **`cloudflared`** runs **`tunnel … run`** with mounted config.         | Ingress hostnames and **`http://api:8000`** / **`http://caddy:80`** are defined in YAML — no host port required for the tunnel path (optional **`hub.override.dev.yml`** still helps local curls).                                                   |
| **Host + Zero Trust token**    | **`sudo cloudflared service install <TOKEN>`** (or **`tunnel run --token`**). Public routes edited in the dashboard. | Set **Public Hostname** service to **`http://127.0.0.1:8080`** when Caddy is published via **`hub.override.dev.yml`**. Use **`hub.override.host-tunnel.yml`** so the Compose **`cloudflared`** container does **not** connect the same tunnel twice. |

**DNS:** If the domain is **not** a Cloudflare zone, skip **`tunnel route dns`** and create a **CNAME** at your registrar to **`<TUNNEL_UUID>.cfargotunnel.com`**.

**Dashboard tunnels:** Under **Tunnel → Public Hostnames**, add **every** FQDN you serve (e.g. hub hostname → **`http://127.0.0.1:8080`** when using host `cloudflared` + **`hub.override.dev.yml`**). Without a matching hostname route, **`curl https://<fqdn>/…`** returns **HTTP 530** even if **`127.0.0.1:8080`** works locally. No Cloudflare zone is required if DNS is a manual CNAME. See [`docs/operations/hub-oracle-vm1-deployment-status.md`](../../docs/operations/hub-oracle-vm1-deployment-status.md) §5.2.

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

- **In Compose:** both `hub.yml` and `vault.yml` mount `../cloudflared/credentials` read-only at `/etc/cloudflared/credentials`.
- **Never commit** JSON credentials — only `.gitkeep` is tracked in `credentials/`.

## Changing tunnel ID

1. Create or import the new tunnel; update DNS CNAMEs in Cloudflare to the new tunnel.
2. Replace `TUNNEL_ID` in the matching `config.*.yml` and swap the JSON file under `credentials/`.
3. Redeploy Compose (`docker compose … up -d`).

## Local / CI without credentials

Use **`hub.override.quicktunnel.yml`** / **`vault.override.quicktunnel.yml`** with **`hub.override.dev.yml`** so `cloudflared` runs **`tunnel --url http://caddy:80`** instead of config-file mode. CI keeps replacing `cloudflared` with an Alpine sleep stub via `*.override.ci.yml`.

Production **host** tunnel + Compose: use **`hub.override.host-tunnel.yml`** (same stub pattern — avoids two connectors for one tunnel).

## Manual acceptance (production)

With DNS plus either dashboard routes (**host tunnel**) or **`config.*.yml`** + credentials (**container tunnel**):

```text
https://terra.<your-domain>/v1/health   → 200, Hub API JSON
```
