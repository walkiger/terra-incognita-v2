# `architecture/security.md` — Sicherheits-Architektur (v1.0 + v2.0)

> **Zweck.** Threat-Modell, Schutzziele, Kontrollen, Test-Pläne.
> Bindend für alle MVP-Phasen (M0–M8) und als Vertragsbasis für die
> Migration nach v2.0.
>
> Diese Datei verschärft `Anweisungen.md` §7 *Security Baseline* und
> ist die Single-Source-of-Truth, gegen die der
> `security-code-review-agent` Findings kategorisiert.

---

## Inhalt

1. [Schutzziele & Asset-Liste](#1-schutzziele--asset-liste)
2. [Threat-Modell (STRIDE-orientiert)](#2-threat-modell-stride-orientiert)
3. [Identitäts- & Zugriffs­kontrolle](#3-identitäts--zugriffskontrolle)
4. [Transport-Schutz (TLS, mTLS)](#4-transport-schutz-tls-mtls)
5. [Speicher-Schutz (at-rest)](#5-speicher-schutz-at-rest)
6. [Eingabe­validierung & Output-Encoding](#6-eingabevalidierung--output-encoding)
7. [Rate-Limit, Quotas, Abuse-Schutz](#7-rate-limit-quotas-abuse-schutz)
8. [Secrets-Management](#8-secrets-management)
9. [Logging, Audit, Forensik](#9-logging-audit-forensik)
10. [Lieferketten- und Build-Sicherheit](#10-lieferketten--und-build-sicherheit)
11. [Inzident-Reaktion](#11-inzident-reaktion)
12. [Compliance-Bezug](#12-compliance-bezug)
13. [Testplan & Werkzeuge](#13-testplan--werkzeuge)
14. [Akzeptanz­kriterien (Gate-Form)](#14-akzeptanzkriterien-gate-form)

---

## 1. Schutzziele & Asset-Liste

| Asset | Schutzziel | Klassifikation |
|-------|------------|----------------|
| Nutzer­konten (`users`)        | C-I-A      | A (PII)        |
| Refresh-Tokens                  | C-I        | A (PII)        |
| Session-Cookies                 | C-I        | A (PII)        |
| Engine-Client-Zertifikate       | C-I        | A              |
| Snapshots (`tar.zst`)            | C-I-A      | B              |
| Replay-Events                    | C-I        | B              |
| Audit-Logs                      | I-A        | C              |
| KMS-Keys (R2-envelope)          | C          | A              |
| SOPS-Vault-Keys                 | C          | A              |
| Cloudflare-Tunnel-Token         | C          | A              |
| TLS-Zertifikate (Engine-CA)     | C-I        | A              |
| Sourcecode (Repo)               | I          | C              |

C = Confidentiality, I = Integrity, A = Availability.

**Vertrauens­zonen:**

* **Z0 — Internet**: Kein Vertrauen.
* **Z1 — Cloudflare-Edge**: tunnel-vermittelt; vertraut bei
  Validation der Cloudflare-Header (`CF-Connecting-IP`, `CF-Ray`).
* **Z2 — Hub VM-A**: Vertrauen für Eigenprozesse, NICHT für
  empfangene Nutzerdaten.
* **Z3 — Vault VM-B**: Vertrauen für eigene Read-Mirror-Operationen.
* **Z4 — Engine-Workstation (lokal beim Nutzer)**: Vertrauen
  ausschließlich nach mTLS-Authentifizierung.

---

## 2. Threat-Modell (STRIDE-orientiert)

### 2.1 Spoofing

* **T-S-01** Falscher Engine versucht Hub-Verbindung. → mTLS, Cert-
  Thumbprint-Check (`engine_registrations`).
* **T-S-02** Falscher Hub gibt Engine vor. → DNS-Pinning per
  Engine-Konfig + Cert-Pinning (Hub-CA-Hash).
* **T-S-03** XSS auf Frontend, das JWT abgreift. → JWT in
  `httpOnly`-Cookie, `SameSite=Strict`; CSP `script-src 'self'`.

### 2.2 Tampering

* **T-T-01** Manipulation von Snapshots in R2. → SHA-256 in
  `snapshots`-Zeile, server­seitige Verifikation beim Restore;
  zusätzlich envelope-Verschlüsselung mit AEAD (XChaCha20-Poly1305).
* **T-T-02** Manipulation von Replay-Events vor `INSERT`. → NATS-
  JetStream mit `deny_purge`-Limit; signierter Hash in `meta_json`
  (Engine-Signatur per Client-Cert-Key).
* **T-T-03** Manipulation Audit-Log. → R2-Mirror täglich (write-once,
  `Object Lock` bei R2 noch optional, in v2.0 MinIO-Lock zwingend).

### 2.3 Repudiation

* **T-R-01** Engine bestreitet eingespielte Events. → Engine-
  Signatur per Client-Cert-Key über `(ts_ms, event_kind,
  payload_hash)`.

### 2.4 Information Disclosure

* **T-I-01** SQLite-Datei vom VM-Nachbarn lesbar. → POSIX-Permissions
  `0600` für DB-Datei + R2-envelope.
* **T-I-02** Snapshot-Inhalt enthält Klartext. → AEAD vor R2-Upload.
* **T-I-03** Logs enthalten PII. → Strukturierte Logs mit PII-
  Maskierung; `client_ip` HMAC, kein Klartext.

### 2.5 Denial of Service

* **T-D-01** Massen­registrierung → Memory-OOM. → Rate-Limit pro IP +
  CAPTCHA in v1.x (Cloudflare-Bot-Mitigation).
* **T-D-02** Massen­replay-Queries → CPU-OOM. → Per-User-Rate-Limit,
  WAL-Read-Lock-Backpressure.
* **T-D-03** WS-Flood. → `ws.events_1h`-Quota (Sliding-Window).

### 2.6 Elevation of Privilege

* **T-E-01** Cookie-Replay nach Logout. → Refresh-Token-Reuse-
  Detection invalidiert ganze Familie.
* **T-E-02** Admin-API ohne Rolle. → JWT enthält `role` Claim;
  Server prüft erneut gegen `users.is_admin`.

---

## 3. Identitäts- & Zugriffs­kontrolle

### 3.1 Passwörter

* **Argon2id**: `m=64MiB`, `t=2`, `p=1` (M5 Default; per Migration
  upgrade-fähig).
* Mindestlänge 12, kein Common-Password (Liste:
  `assets/security/common-passwords.txt`).
* Optional Passwort­manager-Integration (HIBP-API, **nicht** in v1.0).

### 3.2 JWTs

* RS256, 2048-Bit-Schlüssel, Schlüssel­ID `kid` Pflicht.
* **Access-Token** TTL 15 min, Claims:
  `sub` (user_id), `role` (`user`/`admin`), `lang`, `iat`, `exp`,
  `kid`, `aud=terra-mvp`, `iss=https://terra.example`.
* **Refresh-Token** TTL 30 Tage, Claims minimaler:
  `sub`, `iat`, `exp`, `kid`, `aud=terra-mvp:refresh`, `family_id`.
* Schlüssel­rotation alle 90 Tage; aktive `kid`-Liste in
  `auth/jwks.json`.

### 3.3 Cookies

* `Set-Cookie: <name>=<jwt>; HttpOnly; Secure; SameSite=Strict;
  Path=/; Domain=<root>; Max-Age=...` für Access (15 min) und
  Refresh (30 d).
* Pflicht: kein JS-zugänglicher Cookie-Pfad.

### 3.4 Engine mTLS

* Eigene **Engine-CA** (Self-Signed, gespeichert in SOPS).
* Pro Engine: ECDSA-P-256-Schlüssel + Cert mit
  CN=`engine_id`, `subjectAltName=URI:terra:engine:<engine_id>`.
* Hub validiert: Cert-Chain bis Engine-CA, Thumbprint-Match in
  `engine_registrations`, gültiger Zeitraum.

### 3.5 Admin-Pfad

* Admin-Endpoints unter `/api/v1/admin/*`, eigene Rate-Limits,
  zusätzlicher 2FA-Header (TOTP via `pyotp`) in v1.x.
* Kein Admin-Endpoint, der nicht im Audit-Log landet.

---

## 4. Transport-Schutz (TLS, mTLS)

* **Ingress** durch Cloudflare-Tunnel; eingehende Verbindungen sind
  ausschließlich TLS-1.3 zur Cloudflare-Kante.
* **VM-Interne Pfade**: `localhost`-Bindings; Nicht-TLS akzeptabel
  innerhalb VM.
* **Engine ↔ Hub WSS**: TLS-1.3 mTLS; Engine-Client-Cert + Hub-
  Server-Cert (Cloudflare-managed, validiert per `Cf-Visitor`-
  Header gegen erwartete Cipher-Suites).
* **Hub ↔ Vault**: SSH-Tunnel + WireGuard-Sidecar (in v1.0
  optional; in v2.0 Pflicht).

**Cipher-Suiten (v1.3, eingefroren):**

* `TLS_AES_128_GCM_SHA256`
* `TLS_AES_256_GCM_SHA384`
* `TLS_CHACHA20_POLY1305_SHA256`

---

## 5. Speicher-Schutz (at-rest)

* **SQLite-Datei**: POSIX `0600`, Owner = `caddy`/`fastapi`-User.
  Keine Klartext-Verschlüsselung in v1.0; in v2.0 SQLCipher (Engine-
  Edge-Gerät) optional.
* **WAL nach R2**: Litestream nutzt R2 envelope-Verschlüsselung
  (siehe Snapshots).
* **Snapshots**: `tar.zst` → AEAD (XChaCha20-Poly1305) mit
  user-spezifischem DEK, der per KEK (Master-Key in SOPS) gewrappt
  wird.
* **Backups**: SOPS-verschlüsselt unter `secrets/`, mit
  AGE-Empfängern (mind. 2 für Recovery).

---

## 6. Eingabe­validierung & Output-Encoding

* **API-Eingaben**: Pydantic-Modelle, `extra="forbid"`, Längen
  limits pro Feld (`word ≤ 64`, `payload ≤ 8 KiB`).
* **Path-Params**: Regex-validiert (`encounter_id =
  ^e_\d{13}_[a-z2-7]{6}$`).
* **Replay-Query `q`**: Maximal 256 Zeichen, FTS5 sanitization
  (entfernt `*`, `"`, `MATCH`-Operatoren in `auto`-Mode; im
  `expert`-Mode erlaubt aber rate-limit-belastet).
* **HTML-Output**: nur über React-rendering (kein `dangerouslySet
  InnerHTML`); CSP `script-src 'self'; object-src 'none'`.
* **JSON-Encoding**: orjson, ASCII-only Toggle für Logs.

---

## 7. Rate-Limit, Quotas, Abuse-Schutz

| Endpoint                 | Limit                | Burst | Quelle |
|--------------------------|----------------------|-------|--------|
| `POST /auth/login`        | 10/h pro IP          | 5     | nginx-counter / `quota_usage` |
| `POST /auth/register`     | 3/d pro IP           | 1     | dito    |
| `POST /auth/refresh`      | 60/h pro Token-Familie | 10  | dito    |
| `GET /api/v1/replay/window` | 60/min pro User     | 30    | dito    |
| `GET /api/v1/snapshots`    | 30/min pro User      | 10    | dito    |
| `WS /ws/viewer`            | 1 connection / User  | 0     | Connection-Counter |
| `WS /ws/engine`            | 1 / engine_id         | 0     | dito    |

* **Sliding-Window** Implementierung mit `quota_usage` (Tabelle in
  Data-Model, §3.9).
* **Burst-Buffer** als Token-Bucket, in-process pro Worker.
* **Abuse-Detection**:
  * 5× failed login in 15 min → IP-Blacklist 1 h.
  * 3× refresh-reuse in 24 h → `users.is_disabled=1` + manueller
    Admin-Reset.

---

## 8. Secrets-Management

* **SOPS** (`age`-Empfänger) für `secrets/*.yml`.
* Repository enthält **nur** die `*.enc.yml`-Varianten.
* Empfänger-Liste mind. 2 Personen + 1 CI-Empfänger.
* Rotations-Policy:
  * JWT-Schlüssel: 90 d.
  * Engine-CA: 365 d.
  * R2-Master-Key: 365 d (mit dual-key-rollover-Pfad).
  * Cloudflare-Tunnel-Token: 180 d.

* **Pre-Commit-Gate** `detect-secrets` blockt versehentliche
  Klartext-Commits.

---

## 9. Logging, Audit, Forensik

* **Strukturierte JSON-Logs** (eine Zeile pro Event), Felder:
  `ts`, `level`, `service`, `event`, `user_id` (optional),
  `request_id`, `route`, `latency_ms`, `status`, `error_class`.
* **PII-Maskierung**: `email` → `m***@d***.tld`, IPs als HMAC.
* **Audit-Log** in `audit_log`-Tabelle + Mirror nach R2
  (`audit/year=YYYY/month=MM/day=DD/*.jsonl.gz`).
* **Retention**: 365 d on-line, 5 J in R2 Archive.
* **Forensik-Pfad** (Beispiel: Verdacht auf Account-Übernahme):
  1. Alle Sessions des Users (`sessions`) auflisten.
  2. Audit-Events der letzten 30 Tage filtern.
  3. Refresh-Token-Familien auflisten, ggf. revoken.
  4. R2-Mirror-Diff auf Audit-Log-Konsistenz.

---

## 10. Lieferketten- und Build-Sicherheit

* **`uv`-Lockfile** committed; `pip-audit` in CI (M0).
* **`npm`-Lockfile** committed; `pnpm audit` / `npm audit` in CI.
* **Container-Scan**: `trivy` in CI gegen Hub-/Vault-Images
  (Severity ≥ HIGH blockiert Merge).
* **SBOM**: `syft` erzeugt `sbom-hub.spdx.json` und
  `sbom-vault.spdx.json` für jeden Release.
* **Signaturen**: `cosign` signiert Container-Images; Engine-Wheel
  wird per `cosign sign-blob` mit Engine-CA-Subkey signiert.
* **Reproduzierbarkeit**: `uv` mit `--require-hashes`,
  `pnpm install --frozen-lockfile`.
* **Pre-commit-Hooks** (M0): `ruff`, `mypy`, `prettier`,
  `eslint`, `check_protected_deletions.py`,
  `strip_cursor_coauthor_trailer.py`, `detect-secrets`,
  `gitleaks`.

---

## 11. Inzident-Reaktion

* **Schweregrade**:
  * Sev-1 — aktive Datenexfiltration / Compromise.
  * Sev-2 — DoS, Tunnel-Down, R2-Outage.
  * Sev-3 — degradierte Performance, Quota-Stress.
* **Kommunikation**: privates Channel + Status-Page (statisch,
  CF-Pages, manuell).
* **Runbook-Liste** unter `runbooks/incident-*.md` (siehe
  `runbooks/`).
* **Forensische Snapshots**: SQLite-Dump + R2-Sync-Stop binnen 5
  Minuten nach Sev-1-Klassifizierung.
* **Post-Mortem** binnen 7 Tagen, mit
  `memory/system/decisions.md`-Eintrag.

---

## 12. Compliance-Bezug

* **DSGVO**:
  * Auskunft (Art. 15) → `GET /api/v1/me/export`.
  * Löschung (Art. 17) → `POST /api/v1/me/delete` (siehe
    `data-model.md` §10).
  * Verzeichnis von Verarbeitungstätigkeiten unter `legal/ROPA.md`.
* **TTDSG**:
  * Cookie-Banner mit echten Wahl­möglichkeiten (Pflicht für Marketing-
    Cookies; in v1.0 nur strikt notwendige).
* **TMG/Impressum**: `legal/imprint.md`.
* **AGB/ToS**: `legal/tos.md`, versioniert nach SemVer.

---

## 13. Testplan & Werkzeuge

| Bereich         | Werkzeug         | Frequenz       |
|-----------------|------------------|----------------|
| SAST            | `bandit` + `ruff S`-Regeln | per PR        |
| DAST            | `nikto`-light + `zap-baseline` | nightly      |
| Dependency      | `pip-audit`, `pnpm audit`, `trivy` | per PR + nightly |
| Secrets         | `gitleaks`, `detect-secrets` | per PR        |
| Auth-Flows      | Pytest + `httpx`-Suite         | per PR        |
| Rate-Limits     | Soak-Test (M8.3)               | pre-release   |
| OOM-Verhalten   | k6/locust + cgroup-Limit-Test  | pre-release   |
| Backup-Restore  | Drill (M8.5)                   | monatlich     |
| Tabletop-Übungen | Inzident-Skripte              | quartalsweise |

---

## 14. Akzeptanz­kriterien (Gate-Form)

Vor `v1.0.0` müssen erfüllt sein:

* `pip-audit`/`npm audit`/`trivy`: keine HIGH/CRIT Findings ohne
  dokumentierten Ausschluss.
* Auth-Flows: 100% Coverage der Pytest-Auth-Suite, keine Skips.
* Engine-mTLS: produktiver Cert-Path geprüft, Test-Pfad entfernt.
* Logging: PII-Maskierung in Stichproben (10 Logs) verifiziert.
* Audit: R2-Mirror der letzten 7 Tage rekonstruiert
  Hub-Log 1:1.
* Backup-Restore-Drill bestanden (siehe `runbooks/disaster-recovery.md`).
* Threat-Modell-Tabelle (§2) + Mitigations je Threat verifiziert.
* DSGVO-Endpoints `me/export` + `me/delete` funktionsfähig.

---

*Stand: 2026-05-08 · Greenfield-Initial · bindend für M0–M8 +
Migrationsbasis für v2.0.*
