# catchup.md — Session- und Release-Log (terra-incognita-v2)

> Living document. Kurze, datierte Einträge; keine Romane.

---

## 2026-05-10 — M1 Abschluss Block M1.8–M1.11 (Persistence)

**PR #24**: Litestream Hub (`deploy/litestream`, Compose Profil **`litestream`**, MinIO-CI-Overlay), R2/IAM-Doku (`docs/operations/r2-buckets.md`), Vault **`r2-pull`** (Prometheus `deploy/prometheus/prometheus.vault.yml`), Restore (`scripts/operations/restore_hub.sh`, `docs/operations/restore-drill.md`). Index **M1** komplett **`[x]`**; Tag **`v0.2.0`** nach Merge separat setzen.

---

## 2026-05-09 — M1.5 EncountersRepository (`feature/repo-encounters`)

**PR #21**: `EncountersRepository`, `Encounter` / `EncounterDraft`, SQL CHECK auf `encounters.source` (`schema/0003_encounters_source_check.sql`, Alembic `0003_encounters_source`), `meta.schema_version` / Hub Init jetzt **3**. Index **M1.5** `[x]` und `M1-data-foundation.md` §6 mitgeführt.

---

## 2026-05-09 — M1.4 UsersRepository (`feature/repo-users`)

**PR #20**: `BaseRepository`, `UsersRepository`, Pydantic `User` / `UserCredentials`; Runtime-Deps `pydantic`, `email-validator`. Index **M1.4** `[x]` und `M1-data-foundation.md` §6 mitgeführt.

---

## 2026-05-09 — M1.3 Alembic gemerged; Index-/Doku-Bündel-Regel

**PR #17** (`feat: Alembic migrations bootstrap M1.3`) ist auf **`main`**. **`00-index.md`** und **`M1-data-foundation.md`** §6 werden mit dieser Session nachgezogen (M1.3 **`[x]`**). **PR #18** verlagert Hub-API-Stubs nach **`app/backend/api/`** — für künftige Schritte gilt: **Index-Zeile + Phasendoku (+ bei Pfad-/Kommandoänderung CONTRIBUTING/CLAUDE/README) immer in derselben PR** (`00-index.md` §7, **`docs/operations/branch-and-pr-rules.md`**).

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

## 2026-05-09 — Hub-FQDN `hub.terra-incognita.cloud`, DNS-Zone bei Cloudflare

**Produktions-Hub:** öffentlicher FQDN **`hub.terra-incognita.cloud`** mit Cloudflare Tunnel (Modus B: systemd-Connector, Compose mit **`hub.override.dev.yml`** + **`hub.override.host-tunnel.yml`**). Repo-Doku **`deploy/cloudflared`**, Tunnel-Ingress/`config.hub.yml` und Playbook (**`hub-oracle-vm1-deployment-status.md`**) wurden auf diese Domain ausgerichtet (u. a. **PR #14** nach **`main`**).

**Betrieb:** Lokal **`http://127.0.0.1:8080/v1/health`** bestätigt Stack; extern **`https://hub.terra-incognita.cloud/v1/health`** erst nach **NS-Propagierung** (Registrar → Cloudflare Nameserver) und **CNAME**-Eintrag **`hub`** → **`<TUNNEL_UUID>.cfargotunnel.com`** in der **Cloudflare-Zone** — nicht durch „Subdomain“-UI beim Registrar ohne passenden Tunnel-CNAME ersetzbar (**Playbook §2**, Abschnitt _DNS — Cloudflare-Zone_).

**Governance:** Ein formaler **Verifier**-Lauf kann blocken, wenn pre-merge Behauptungen (z. B. „Smoke von außen grün“) **ohne Nachweis** stehen bleiben — dann entweder **Nachweis** erbringen oder **Governance-/PR-Spec** konsistent dokumentieren („externer Smoke ausstehend bis DNS aktiv“).

---
