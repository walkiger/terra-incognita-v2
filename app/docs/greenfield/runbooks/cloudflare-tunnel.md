# `runbooks/cloudflare-tunnel.md` — Cloudflare-Tunnel-Operationen

> **Zweck.** Konkrete Konfiguration und Betrieb des Cloudflare-Free-
> Tunnels für die v1.0-Topologie. Ergänzt
> `runbooks/operations.md` §6 und `architecture/security.md` §4.
>
> **Wichtig.** Der Tunnel ist die **einzige** öffentliche Eingangs­
> stelle für den Hub. Sicherheit und Verfügbarkeit hängen direkt an
> seiner korrekten Konfiguration.

---

## Inhalt

1. [Zonenbild & DNS](#1-zonenbild--dns)
2. [Tunnel-Erstellung](#2-tunnel-erstellung)
3. [`config.yml` (Hub VM-A)](#3-configyml-hub-vm-a)
4. [SystemD-Unit](#4-systemd-unit)
5. [Routing & Hostnames](#5-routing--hostnames)
6. [WAF-Regeln (Cloudflare-Dashboard)](#6-waf-regeln-cloudflare-dashboard)
7. [Engine-mTLS-Header-Validation](#7-engine-mtls-header-validation)
8. [Token-Rotation](#8-token-rotation)
9. [Monitoring & Alerts](#9-monitoring--alerts)
10. [Inzident-Pfad](#10-inzident-pfad)

---

## 1. Zonenbild & DNS

* **Cloudflare-Zone:** `terra.example` (oder eigene Domain).
* **DNS-Records (alle proxied / orange-cloud aktiv):**

| Hostname                    | Typ  | Ziel             | Zweck                      |
|-----------------------------|------|------------------|-----------------------------|
| `terra.example`             | A    | 192.0.2.1        | Cloudflare Pages (Frontend) |
| `api.terra.example`         | CNAME| `<tunnel-id>.cfargotunnel.com` | Hub HTTP/WS public |
| `engine.terra.example`      | CNAME| `<tunnel-id>.cfargotunnel.com` | Engine WS-only      |
| `admin.terra.example`       | CNAME| `<tunnel-id>.cfargotunnel.com` | Admin (IP-allow)    |

* **Cloudflare Page-Rule:** `admin.terra.example/*` →
  *Access*-geschützt (siehe §6).

---

## 2. Tunnel-Erstellung

```bash
# Auf Workstation des Admins (einmalig)
cloudflared login                       # Browser-Flow, Auth gegen CF-Account
cloudflared tunnel create terra-mvp     # erzeugt tunnel-id + Credentials-File
# Credentials-File (~/.cloudflared/<id>.json) → SOPS verschlüsseln
sops -e ~/.cloudflared/<id>.json > secrets/cloudflared.json.enc.json
```

* `cloudflared.json.enc.json` wird im Repo committed.
* Auf Hub-VM:

```bash
sops -d secrets/cloudflared.json.enc.json > /etc/cloudflared/<id>.json
chmod 0600 /etc/cloudflared/<id>.json
```

---

## 3. `config.yml` (Hub VM-A)

```yaml
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/<tunnel-id>.json
metrics: 127.0.0.1:9090
loglevel: info
no-autoupdate: true

ingress:
  # Public API + WS
  - hostname: api.terra.example
    service: http://localhost:8080

  # Engine WS (mTLS)
  - hostname: engine.terra.example
    service: https://localhost:8443
    originRequest:
      noTLSVerify: false
      caPool: /etc/cloudflared/origin-ca.pem
      originServerName: localhost
      # mTLS-Client-Cert wird über CF-Header durchgereicht;
      # der Hub-Caddy validiert. Siehe §7.

  # Admin (IP-allow + CF Access)
  - hostname: admin.terra.example
    service: http://localhost:8081

  # Catch-all (rejection)
  - service: http_status:404
```

---

## 4. SystemD-Unit

```ini
# /etc/systemd/system/cloudflared.service
[Unit]
Description=Cloudflared
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/cloudflared tunnel --config /etc/cloudflared/config.yml run
Restart=always
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60
WatchdogSec=30s

# Memory budget per runbooks/oom-and-capacity.md §3
MemoryHigh=45M
MemoryMax=60M
TasksMax=64
LimitNOFILE=4096
OOMScoreAdjust=100

[Install]
WantedBy=multi-user.target
```

Aktivieren:

```bash
systemctl daemon-reload
systemctl enable --now cloudflared
systemctl status cloudflared
```

---

## 5. Routing & Hostnames

* **`api.terra.example`**:
  * öffentlich, alle `/api/v1/*` und `/ws/v1/viewer`.
  * WAF-Regel: blockt `User-Agent`-Bots, Geo-Block (optional).
* **`engine.terra.example`**:
  * **NUR** `/ws/v1/engine` erlaubt; alles andere → 404.
  * Cloudflare Access optional (Service Token), zusätzlich zur
    mTLS am Origin.
* **`admin.terra.example`**:
  * Cloudflare Access (Email-OTP + Service-Token).
  * IP-allow-list als zweite Linie (Caddy).

---

## 6. WAF-Regeln (Cloudflare-Dashboard)

```
# Standard-Regeln (Free-Plan deckt OWASP-Set ab)
Block: SQL-Injection
Block: XSS
Challenge: Bots (cf.client.bot)

# Custom Rule 1 — Engine-Hostname nur WS
(http.host eq "engine.terra.example" and not starts_with(http.request.uri.path, "/ws/v1/engine"))
→ Block

# Custom Rule 2 — Admin-Hostname Access-only
(http.host eq "admin.terra.example" and not http.request.headers["cf-access-jwt-assertion"][0])
→ Challenge

# Custom Rule 3 — Rate-Limit Login per IP
(http.host eq "api.terra.example" and http.request.uri.path eq "/api/v1/auth/login")
→ Rate Limit: 10 / 60s, Action: Block 15min
```

---

## 7. Engine-mTLS-Header-Validation

Cloudflare Tunnel kann mTLS so konfigurieren, dass das Client-Cert
am Edge geprüft und als Header zum Hub durchgereicht wird:

* **Cloudflare-Dashboard → SSL/TLS → Client Certificates** —
  Engine-CA als `Authenticated Origin Pull` hinterlegen.
* CF gibt am Origin folgende Header zurück:
  * `Cf-Client-Cert: <PEM url-encoded>`
  * `Cf-Client-Cert-Verify: SUCCESS|FAILED`
  * `Cf-Connecting-IP: <real-ip>`

**Hub-Caddy validiert:**

```caddy
@engine_ws path /ws/v1/engine
handle @engine_ws {
  @cert_ok header_regexp Cf-Client-Cert-Verify "^SUCCESS$"
  handle @cert_ok {
    reverse_proxy localhost:8443
  }
  handle {
    respond 401 "engine cert not validated"
  }
}
```

Der Hub-FastAPI prüft zusätzlich Cert-Thumbprint gegen
`engine_registrations` (siehe `architecture/security.md` §3.4).

---

## 8. Token-Rotation

* **Frequenz:** alle 180 d (siehe `architecture/security.md` §8).
* **Schritte:**
  1. `cloudflared tunnel token <tunnel-id>` (gibt aktiven Token).
  2. Cloudflare-Dashboard → Tunnel → „Generate new token".
  3. SOPS-Update: alten Token in `secrets/cloudflared.old.enc.json`
     archivieren (für 14 Tage Roll-Back), neuen schreiben.
  4. `systemctl reload cloudflared` (graceful, neuer Token).
  5. Alten Token im Dashboard revoken nach 14 Tagen.

---

## 9. Monitoring & Alerts

* `cloudflared metrics` (Port 9090, lokal):
  * `cloudflared_tunnel_active_streams`
  * `cloudflared_tunnel_request_errors`
  * `cloudflared_tunnel_response_by_code{code="5xx"}`
* Prometheus scraped diese; Alerts:
  * `A.TUNNEL.DOWN` — `up{job="cloudflared"} == 0` für 1 min.
  * `A.TUNNEL.5XX` — rate(`cloudflared_tunnel_response_by_code{code=~"5.."}`)[5m] > 0.5.
  * `A.TUNNEL.STREAMS.HIGH` — `cloudflared_tunnel_active_streams > 200`.

---

## 10. Inzident-Pfad

* **Tunnel-Down**:
  1. `journalctl -u cloudflared -n 100`.
  2. Cloudflare-Status-Page prüfen.
  3. `systemctl restart cloudflared`.
  4. Falls Persistenz: neuen Token (siehe §8) und re-enrollen.
* **Tunnel-falsch-routet**:
  * `cloudflared tunnel route ingress validate /etc/cloudflared/config.yml`
    prüft Routing-Regeln offline.
* **Tunnel-Token kompromittiert**:
  * Sofort revoken (Dashboard); neuen erzeugen; Secret-Rotation
    laut `architecture/security.md` §8.
* **Cloudflare-Account kompromittiert**:
  * Eskalation: alle Tunnel-Konfigs via Console löschen, neuen
    Account aufsetzen, DNS umkonfigurieren. RTO: ≤ 4 h.

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`architecture/mvp.md`, `runbooks/operations.md` §6.*
