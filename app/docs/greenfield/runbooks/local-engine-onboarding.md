# `runbooks/local-engine-onboarding.md` — Lokale Engine in Betrieb nehmen

> **Zweck.** Schritt-für-Schritt-Anleitung für einen User, der die
> `terra-engine` lokal installiert und sich am Hub anmeldet.
> Komplementär zu `implementation/mvp/M3-local-engine-skeleton.md`
> (Implementierungs-Sicht) und `protocols/event-log.md`
> (Wire-Vertrag).

---

## Inhalt

1. [Voraussetzungen](#1-voraussetzungen)
2. [Engine-Account vorbereiten (Admin)](#2-engine-account-vorbereiten-admin)
3. [Engine installieren](#3-engine-installieren)
4. [Engine konfigurieren](#4-engine-konfigurieren)
5. [Erstverbindung & Hello-Frame](#5-erstverbindung--hello-frame)
6. [Snapshot anlegen](#6-snapshot-anlegen)
7. [Hard-Reset / Reset-from-Snapshot](#7-hard-reset--reset-from-snapshot)
8. [Update der Engine-Version](#8-update-der-engine-version)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Voraussetzungen

* **Hardware (Workstation):**
  * macOS 14+ / Ubuntu 22.04+ / Windows 11 (WSL2 empfohlen).
  * RAM ≥ 4 GB frei (Engine peakt bei ~1.5 GB unter Voll­last).
  * Disk ≥ 5 GB für Snapshots + lokales State.
* **Software:**
  * Python 3.12 (System oder per `pyenv`).
  * `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
  * Nur lokal benutzte Tools: `git`, `openssl`.
* **Account-Vorbereitung:**
  * Aktiver User-Account auf `terra.example`.
  * Engine-CA-Cert + eigener Engine-Cert (Schritt 2).

---

## 2. Engine-Account vorbereiten (Admin)

Aktuell ist `engine:enroll` admin-only (siehe
`runbooks/operations.md` §9.1):

```bash
# auf Admin-Workstation
py scripts/admin.py engine:enroll \
  --user-id 42 --engine-id macbook-pro-001 \
  --csr ./from-user/macbook-pro-001.csr \
  --validity-days 365
# liefert: macbook-pro-001.crt
```

User-CSR wird vom User auf seiner Workstation erzeugt:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out engine.key
openssl req -new -key engine.key -out engine.csr \
  -subj "/CN=macbook-pro-001/O=terra-engine"
```

Admin sendet zurück:

* `engine.crt` (Client-Cert)
* `engine-ca.crt` (CA-Cert für Hub-Verify)

---

## 3. Engine installieren

```bash
# auf User-Workstation
mkdir -p ~/terra-engine
cd ~/terra-engine

# Wheel installieren (öffentlich gehostet auf Cloudflare R2 oder
# über privaten PyPI-Mirror)
uv pip install terra-engine==1.0.0

# verifizieren
terra-engine --version
# Output: terra-engine 1.0.0  (build_id=abc1234)
```

---

## 4. Engine konfigurieren

Konfig-Datei `~/.config/terra-engine/config.toml`:

```toml
[server]
hub_url            = "wss://engine.terra.example/ws/v1/engine"
hub_ca_pem         = "/Users/me/.config/terra-engine/hub-ca.pem"

[client]
engine_id          = "macbook-pro-001"
client_cert_pem    = "/Users/me/.config/terra-engine/engine.crt"
client_key_pem     = "/Users/me/.config/terra-engine/engine.key"
client_ca_pem      = "/Users/me/.config/terra-engine/engine-ca.crt"

[auth]
# Bearer holen wir per CLI:
bearer_path        = "/Users/me/.config/terra-engine/bearer.jwt"

[runtime]
tick_hz            = 8
log_level          = "INFO"
snapshot_dir       = "/Users/me/.local/share/terra-engine/snapshots"
state_dir          = "/Users/me/.local/share/terra-engine/state"

[features]
mps_enabled        = true       # Apple Silicon GPU
allow_offline      = true       # darf offline weiterticken
```

Berechtigungen:

```bash
chmod 0600 ~/.config/terra-engine/engine.key
chmod 0600 ~/.config/terra-engine/bearer.jwt
```

Bearer initial holen:

```bash
terra-engine auth login --email me@example.com
# Browser öffnet sich für Login → Cookie wird zu Engine-Bearer
# konvertiert (Engine-Scope-JWT)
# bearer.jwt ist gespeichert, gültig 14 d
```

---

## 5. Erstverbindung & Hello-Frame

```bash
terra-engine connect
```

Was passiert:

```
[INFO] connecting wss://engine.terra.example/ws/v1/engine ...
[INFO] TLS 1.3, mTLS handshake OK
[INFO] sending engine/hello {engine_id, sw_version, snapshot_id?}
[INFO] received server/welcome {server_version, accepted: true}
[INFO] tick loop started @ 8 Hz
```

* `--restore-from-snapshot=<id>` lädt einen vorherigen State von R2.
* `--no-tick` lässt den Loop pausiert (für Diagnostik-Verbindung).

Heartbeat-Frames laufen alle 5 s; im Hub-`/diagnostic` taucht der
Engine als **online** auf.

---

## 6. Snapshot anlegen

```bash
# manuell:
terra-engine snapshot create --comment "after first 10 minutes"

# Auto-Snapshots (Default):
# - alle 30 min, wenn ≥ 100 Encounters seit letztem Snapshot.
# - vor Auto-Suspend nach Idle 10 min.
```

Was passiert:

1. State wird lokal in `state_dir/<snapshot_id>/` geschrieben.
2. `tar.zst` mit `manifest.json`-First wird erzeugt.
3. AEAD-Verschlüsselung (DEK random, KEK aus SOPS-Schlüssel).
4. `engine/snapshot/start`-Frame an Hub.
5. `PUT /api/v1/snapshots/raw` mit Bytes.
6. `engine/snapshot/finalize`-Frame.
7. Hub-Response: `is_active=1`.

Lokal bleibt eine Kopie 7 Tage, dann LRU-cleanup
(`snapshot_dir`-Aufräumung via `terra-engine snapshot prune`).

---

## 7. Hard-Reset / Reset-from-Snapshot

```bash
# Engine zurücksetzen (Tier 0, leeres KG):
terra-engine reset --confirm "I_KNOW_WHAT_I_DO"

# Aus Snapshot wiederherstellen:
terra-engine restore --snapshot-id snap_1714900000000_abc123
```

Hard-Reset ist destruktiv — alle lokalen LNN/EBM/KG-Daten gehen
verloren. Snapshots auf dem Server bleiben unberührt (können neu
heruntergezogen werden).

---

## 8. Update der Engine-Version

```bash
# Update auf neuere Version
uv pip install --upgrade terra-engine

# Kompatibilitäts-Test
terra-engine compat-check --hub
# Output: 'engine 1.0.x ↔ hub 1.0.x  : OK'
```

* Engine-Wheels sind **abwärts­kompatibel** für mindestens eine
  Hub-Version. Bei Schema-Bruch (Major-Bump) wird `compat-check`
  fehlschlagen und einen Migrations-Pfad zeigen.

---

## 9. Troubleshooting

### „401 invalid_engine_cert"

* Cert-Thumbprint verifizieren:
  ```bash
  openssl x509 -in ~/.config/terra-engine/engine.crt -fingerprint -sha256 -noout
  ```
* In `engine_registrations`-Tabelle muss derselbe Thumbprint
  `is_active=1` haben.
* Falls deaktiviert: Admin re-enrolln lassen.

### „401 unauthenticated" (Bearer abgelaufen)

```bash
terra-engine auth login --email me@example.com
```

### „server/welcome accepted=false, reason=schema_unsupported"

* Engine-Version inkompatibel zum Hub. Update einspielen
  (siehe §8).

### „RSS > 1.5 GB"

* `tick_hz` reduzieren (`config.toml [runtime] tick_hz = 4`).
* Snapshot anlegen + neu starten (Memory-Drift).
* Falls dauerhaft: Bug-Report mit `terra-engine debug bundle`
  (anonymisiert + lokales Log gepackt).

### „WS-Reconnect-Loop"

* Cloudflare-Tunnel-Status prüfen
  (`runbooks/cloudflare-tunnel.md` §10).
* Bearer prüfen: `terra-engine auth status`.
* Fallback: `terra-engine connect --offline-cache` (lokal weiter
  ticken, später nachreichen).

### „lange Snapshot-Upload-Zeit"

* `terra-engine snapshot create --upload=manual` und manuell
  hochladen lassen.
* Cloudflare-Tunnel `terra_r2_uploads_total{outcome="fail"}`
  beobachten; ggf. Auto-Snapshot pausieren.

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus
`implementation/mvp/M3-local-engine-skeleton.md`.*
