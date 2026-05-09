# catchup.md — Session- und Release-Log (terra-incognita-v2)

> Living document. Kurze, datierte Einträge; keine Romane.

---

## 2026-05-09 — Domain `terra-incognita.cloud` und Tunnel-Fix

Eigene Domain **`terra-incognita.cloud`** bei checkdomain.de registriert (~1 EUR/Jahr), als **Cloudflare Free zone** angelegt (NS `melissa`/`santino`). CNAME **`hub`** proxied auf Tunnel-UUID (`8d4bb120-…`). Published Application Route im Tunnel auf `hub.terra-incognita.cloud` → `http://127.0.0.1:8080`. NS-Propagierung von checkdomain.de zu Cloudflare ausstehend.

**Erkenntnis:** Free-Subdomain-Dienste (`is-into.tech` via is-pro.dev) sind mit eigenem Cloudflare Tunnel inkompatibel — der Dienst schaltet seinen eigenen Cloudflare-Proxy davor, Traffic landet beim falschen Account (530). Ohne Proxy fehlen A-Records (Timeout). Eigene Domain ist der einzige saubere Weg.

Repo-Doku aktualisiert: `config.hub.yml` (konkrete Tunnel-UUID + Hostname), `deploy/cloudflared/README.md`, `hub-oracle-vm1-deployment-status.md` (Ist-Zustand, §5.4 Free-Subdomain), `CLAUDE.md`.

---

## 2026-05-09 — Greenfield M0 abgeschlossen (`greenfield-M0`)

Thin-Shell-MVP **Phase M0** (Bootstrap & Tooling) ist im Repo **`walkiger/terra-incognita-v2`** umgesetzt (Lieferung **PR #10**, Branch **`feature/m0-bootstrap-m05-m010`**): Compose Hub/Vault inkl. Cloudflared-Konfig-Vorlagen, SOPS/AGE-Secrets-Stub, Pre-commit + erweiterte GitHub Actions (Lint, Mypy, Tests/Coverage, Schema-Lint, Protected-Deletions, Secrets-Layout, Pre-commit-CI, Compose-Smokes inkl. Prometheus/Grafana-Profil), Observability-Baseline, konsolidierte Branch-/PR-Doku (`docs/operations/branch-and-pr-rules.md`). VM-Gates laut **`M0-bootstrap.md`** §5 und Annotated Tag **`v0.1.0`** sind nach Merge manuell bzw. per Release-Schritt zu setzen (**`.agent-os/pr-spec.json`**).

---

## 2026-05-09 — Oracle Hub VM1: Tunnel, Compose, Public Hostname / HTTP 530

Instanz **`terra-hub-01`** (Frankfurt, E2 Micro): Docker/Clone/Tunnel-Connector (systemd) und Compose mit **`hub.override.dev.yml`** + **`hub.override.host-tunnel.yml`** nach **`docs/operations/hub-oracle-vm1-deployment-status.md`**.

**Betrieb:** Connector „connected“ allein reicht nicht — im Tunnel **Public Hostnames** muss der öffentliche **FQDN** auf **`http://127.0.0.1:8080`** zeigen; ohne Eintrag liefert **`curl https://<host>/…`** **HTTP 530** obwohl **`127.0.0.1:8080`** lokal **200** ist. **Ohne** Cloudflare-Zone: DNS nur per **CNAME** auf **`<TUNNEL_UUID>.cfargotunnel.com`** beim Provider. Detail und Fehlerbilder: **`hub-oracle-vm1-deployment-status.md`** §2–§5; **`CLAUDE.md`** Lesepfad; **`deploy/cloudflared/README.md`**.

---
