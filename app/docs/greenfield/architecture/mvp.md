# `architecture/mvp.md` — MVP-Architektur (v1.0, Pfad B)

> **Lebendiges Dokument.** Lesepflicht vor jeder Code-Arbeit am MVP.
>
> Beschreibt **was** das v1.0-System ist, **wie** es topologisch aufgebaut
> ist, **welche Services** an welchem Ort laufen, **welche Verträge** sie
> miteinander erfüllen — und **warum** der Plan genau diese Form hat,
> obwohl er offensichtlich nicht der Vollausbau ist.

---

## Inhalt

1. [Ziel & Nicht-Ziel](#1-ziel--nicht-ziel)
2. [Hardware-Topologie](#2-hardware-topologie)
3. [High-Level-Diagramm](#3-high-level-diagramm)
4. [Service-Inventar](#4-service-inventar)
5. [Datenfluss](#5-datenfluss)
6. [Datenmodell](#6-datenmodell)
7. [API-Contracts (HTTP + WebSocket)](#7-api-contracts-http--websocket)
8. [Engine-Protokoll (Local Engine ↔ Hub)](#8-engine-protokoll-local-engine--hub)
9. [Sicherheit](#9-sicherheit)
10. [Beobachtbarkeit](#10-beobachtbarkeit)
11. [Deployment](#11-deployment)
12. [Multi-User](#12-multi-user)
13. [Speicher-Budget](#13-speicher-budget)
14. [Migration nach v2.0](#14-migration-nach-v20)
15. [Risiken & Mitigationen](#15-risiken--mitigationen)
16. [Offene Fragen](#16-offene-fragen)

---

## 1. Ziel & Nicht-Ziel

### Ziel

* Ein **öffentlich erreichbares Schaufenster** des Drei-Pol-Systems mit
  Authentifizierung und Multi-User-Fähigkeit, das auf 2× Oracle Always-Free
  AMD Micro VMs betrieben werden kann.
* Vollständige **API-Verträge** und **Persistenz**, die in v2.0 unverändert
  weitergeführt werden — kein „Throw-away-MVP".
* **Local Engine** als unterstützter, dokumentierter Compute-Pfad: Nutzer mit
  einer ausreichend dimensionierten Workstation können den Drei-Pol-Loop bei
  sich rechnen lassen und Encounters live an den Hub streamen.
* **Replay & `/diagnostic`** voll funktional über den Hub, inklusive
  Hybrid-Suchplaner aus dem Bestand (`replay_timeline_window_v4`).
* **Disaster-Recovery in Minuten** über Litestream → Cloudflare R2.

### Nicht-Ziel

* **Kein server-seitiges LNN/EBM/KG-Compute.** PyTorch alleine belegt
  ~400 MB RSS und passt nicht in 1 GB neben den anderen Diensten. Die Engine
  wandert erst in v2.0 in den Server.
* **Kein Polyglot-Stack.** Neo4j, Qdrant, ClickHouse, OpenSearch, Redpanda
  bleiben v2.0 vorbehalten.
* **Keine eigene Auth-IdP.** Wir bauen keinen OAuth-Provider; wir nutzen
  signierte JWTs aus einer Hub-internen User-Tabelle plus optional
  Cloudflare Access für Admin-Routen.
* **Keine eingebaute LLM-Integration.** Das Drei-Pol-System ist absichtlich
  kein LLM-Wrapper (`Anweisungen.md` §1).
* **Kein 8-Hz-Tick auf dem Hub.** Der 8-Hz-Tick lebt in der Local Engine.
  Was den Hub erreicht, sind Encounter-Events und periodische Snapshots.

### Was nach v1.0 NICHT mehr verhandelt wird

Diese Punkte sind **eingefroren**, sobald v1.0 ausgeliefert ist —
Änderungen erfordern v2.0:

| Eingefroren                                              | Begründung                                                |
|----------------------------------------------------------|-----------------------------------------------------------|
| HTTP-Pfade `/v1/...`                                     | OpenAPI-Versions-Handshake mit Frontend & Engine          |
| WebSocket-Channel `/ws/v1/engine`                        | Local Engines sind „im Feld"                              |
| WebSocket-Channel `/ws/v1/viewer`                        | Frontend-Clients sind „im Feld"                           |
| Replay-Event-Schema `replay_timeline_window_v4`          | Bereits ausgeliefert (terra-079/080)                      |
| Snapshot-Bundle-Format                                    | Snapshots leben langfristig in R2                         |
| Auth-Token-Form (JWT RS256, Claim-Set)                    | Token im Wild würden bei Wechsel ungültig                 |
| `F.*`-Formel-IDs                                          | Test-Suiten und Dokumentation referenzieren stabil        |

---

## 2. Hardware-Topologie

### Verfügbar (Stand 2026-05-08)

| Knoten           | Typ                          | RAM    | OCPU   | Disk         | Netz                       |
|------------------|------------------------------|--------|--------|--------------|----------------------------|
| **VM-A — Hub**    | Oracle `VM.Standard.E2.1.Micro` | 1 GB   | ⅛      | 50 GB Block  | Public via CF Tunnel       |
| **VM-B — Vault**  | Oracle `VM.Standard.E2.1.Micro` | 1 GB   | ⅛      | 50 GB Block  | Public via CF Tunnel (alt) |
| **CF Tunnel × 2** | `cloudflared`                 | —      | —      | —            | bereits eingerichtet       |
| **CF R2**         | Object Storage                | —      | —      | 10 GB free   | S3-API, kein Egress-Cent   |
| **Local Engine**  | Workstation des Nutzers       | ≥ 4 GB empfohlen | ≥ 2 Cores | beliebig | Outbound-only zu Hub     |

Die zwei VMs befinden sich in derselben Region. Das ist **kein**
geographischer Failover, sondern **Rollen-Trennung** + Backup-Pfad.

### Was die 1-GB-Grenze bedeutet (gemessen, nicht geschätzt)

Idle-Resident-Set typischer Container/Prozesse, gegen die wir budgetieren
müssen:

| Komponente                                                         | RSS Idle      |
|--------------------------------------------------------------------|---------------|
| Linux + Docker daemon (Ubuntu 24.04 minimal)                       | ~200 MB        |
| Caddy (statisches Frontend + Reverse-Proxy)                        | ~30 MB         |
| FastAPI / uvicorn (1 Worker, ohne PyTorch)                         | ~90 MB         |
| NATS JetStream (small stream, file-store)                          | ~80 MB         |
| `cloudflared`                                                      | ~40 MB         |
| Litestream                                                         | ~20 MB         |
| Prometheus Node-Exporter                                            | ~20 MB         |
| Logging Sidecar (z. B. `vector` minimal)                            | ~30 MB         |

Hub-Idle-Summe: **~510 MB**. Headroom für Lastspitzen, Concurrent-WS,
Page-Cache: **~490 MB**. Realistisch.

Nicht im Hub-Profil:

| Würde nicht passen                                                 | RSS Minimum   | Warum nicht im MVP                              |
|--------------------------------------------------------------------|---------------|-------------------------------------------------|
| PostgreSQL 16 + AGE + pgvector + TimescaleDB                       | ~500 MB        | reißt Headroom auf, kein OOM-Spielraum          |
| Tick-Engine mit PyTorch (`import torch`)                           | ~400 MB        | gleicher Grund                                   |
| Neo4j / Qdrant / ClickHouse                                        | je ≥ 600 MB    | gleicher Grund                                   |

---

## 3. High-Level-Diagramm

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│   USER BROWSERS                              POWER-USER WORKSTATIONS │
│   (Multi-User, parallel)                     (optional Local Engine)│
│                                                                   │
│        │ HTTPS + WS                              │ WSS (Engine)    │
│        ▼                                         ▼                 │
│ ╔══════════════════════════════════════════════════════════════╗ │
│ ║                  CLOUDFLARE EDGE (Free)                       ║ │
│ ║   ─ DNS, TLS, WAF, Tunnel-Termination, optional CF Access     ║ │
│ ║   ─ R2 Object Storage (10 GB free, 0¢ egress)                 ║ │
│ ╚══════════════════════════════════════════════════════════════╝ │
│        │ cloudflared QUIC          │ cloudflared QUIC              │
│        ▼ (primary)                  ▼ (secondary, frontend mirror) │
│   ┌────────────────────────┐    ┌────────────────────────┐        │
│   │     VM-A: HUB           │    │     VM-B: VAULT         │        │
│   │   (1 GB / ⅛ OCPU)       │    │   (1 GB / ⅛ OCPU)       │        │
│   │                          │    │                          │        │
│   │ ┌────────────────────┐  │    │ ┌────────────────────┐  │        │
│   │ │ Caddy (rev-proxy)   │  │    │ │ Caddy (static fe)   │  │        │
│   │ ├────────────────────┤  │    │ ├────────────────────┤  │        │
│   │ │ FastAPI + WS        │  │    │ │ Backup Worker       │  │        │
│   │ │  - /v1/...          │  │    │ │  (R2 → SQLite repl) │  │        │
│   │ │  - /ws/v1/engine    │  │    │ ├────────────────────┤  │        │
│   │ │  - /ws/v1/viewer    │  │    │ │ Snapshot Processor  │  │        │
│   │ ├────────────────────┤  │    │ │  (replay materializ)│  │        │
│   │ │ NATS JetStream      │  │    │ ├────────────────────┤  │        │
│   │ │  - encounters.*     │◄─┼────┼─┤ NATS subscriber     │  │        │
│   │ │  - replay.*         │  │    │ └────────────────────┘  │        │
│   │ │  - snapshots.*      │  │    │ ┌────────────────────┐  │        │
│   │ ├────────────────────┤  │    │ │ SQLite (read repl)  │  │        │
│   │ │ SQLite (primary,    │  │    │ │  - hot R2 mirror    │  │        │
│   │ │  WAL, journal)      │  │    │ └────────────────────┘  │        │
│   │ │  - users            │  │    └─┬──────────────────────┘        │
│   │ │  - sessions         │  │      │ R2 pull                        │
│   │ │  - encounters       │  │      ▼                                 │
│   │ │  - replay_events    │  │    ┌────────────────────┐              │
│   │ │  - snapshots (ref)  │  │    │ Cloudflare R2      │              │
│   │ ├────────────────────┘  │    │  - litestream/...  │              │
│   │ │ Litestream → R2     │──┼───►│  - snapshots/...   │              │
│   │ ├────────────────────┤  │    │  - replay-bundles/ │              │
│   │ │ cloudflared         │  │    └────────────────────┘              │
│   │ ├────────────────────┤  │                                         │
│   │ │ Prometheus + Grafa  │  │    ┌────────────────────┐              │
│   │ │ (slim)              │  │    │ cloudflared        │              │
│   │ └────────────────────┘  │    │ (failover)         │              │
│   │                          │    └────────────────────┘              │
│   └──────────┬───────────────┘                                       │
│              │ NATS replication (push)                                │
│              └────────────────────────────────────────────────────►   │
└──────────────────────────────────────────────────────────────────┘
```

Lesart:

* **Browser** verbinden sich nur über die Cloudflare-Edge — niemals direkt
  mit den Oracle-IPs. Es gibt keine offenen Inbound-Ports auf den VMs.
* **Local Engine** verbindet sich ebenfalls über die Cloudflare-Edge an den
  Hub-WS-Endpoint. Es gibt keinen direkten Engine-zu-Vault-Pfad.
* **Vault** ist passiv. Der Vault zieht Daten aus R2 und konsumiert nur
  spezifische NATS-Streams, um synchron zu bleiben.

---

## 4. Service-Inventar

### Hub (VM-A)

| Service               | Image / Quelle                                | RSS (Idle) | Verbindlich?            |
|-----------------------|-----------------------------------------------|-------------|-------------------------|
| `caddy`               | `caddy:2-alpine`                              | ~30 MB      | ja                      |
| `api`                 | eigenes Image (`python:3.12-slim` + uvicorn)  | ~100 MB     | ja                      |
| `nats`                | `nats:alpine` mit JetStream                   | ~80 MB      | ja                      |
| `litestream`          | `litestream/litestream`                        | ~20 MB      | ja                      |
| `cloudflared`         | `cloudflare/cloudflared`                      | ~40 MB      | ja                      |
| `prom-node-exporter`  | `prom/node-exporter`                          | ~20 MB      | ja                      |
| `prom-server`         | `prom/prometheus` (slim, lokal scrapen)        | ~80 MB      | ja                      |
| `grafana`             | `grafana/grafana-oss` (read-only Dash)         | ~110 MB     | optional, default an    |
| `vector`              | `timberio/vector` minimal                      | ~30 MB      | optional                |

`api` ist ein eigener Service-Container, der die FastAPI-App via uvicorn
ausführt. **Genau ein** uvicorn-Worker — auf 1 GB ist Multi-Worker
schädlich (jeder Worker bringt eigene Imports mit; bei async-IO ohnehin
unnötig).

Storage-Volumes (Docker named volumes):

| Volume                  | Pfad im Container         | Inhalt                                     |
|-------------------------|---------------------------|---------------------------------------------|
| `hub-sqlite`            | `/var/lib/terra/db/`      | `terra.sqlite` + WAL                        |
| `hub-nats-jetstream`    | `/var/lib/nats/jetstream/`| persistierte Streams                        |
| `hub-prom-data`         | `/var/lib/prometheus/`    | TSDB-Block-Daten (kurze Retention, 7 Tage)  |
| `hub-grafana-config`    | `/etc/grafana/`           | Dashboards, Datasource-Config                |
| `hub-cloudflared-cred`  | `/etc/cloudflared/`       | Tunnel-Credentials                           |

### Vault (VM-B)

| Service              | Zweck                                              |
|----------------------|----------------------------------------------------|
| `caddy`              | statisches Frontend (Mirror), Health-Page          |
| `cloudflared`        | sekundärer Tunnel (Failover für Frontend)          |
| `r2-pull`            | Backup-Worker, holt regelmäßig Litestream-Snapshots aus R2 nach lokaler SQLite |
| `snapshot-processor` | konsumiert NATS `snapshots.*`, materialisiert `.tar.zst` und legt sie in R2 ab |
| `nats-subscriber`    | dünner NATS-Client, nur für die Streams, die der Vault braucht |
| `prom-node-exporter` | Metriken                                           |

Die Vault-SQLite ist **read-only** für den Rest des Systems. Niemand
schreibt direkt hinein. Sie dient dazu, im Disaster-Fall einen frischen
Hub binnen Minuten zu rekonstruieren.

### Local Engine (Nutzer-Workstation)

| Komponente                | Zweck                                                      |
|---------------------------|-------------------------------------------------------------|
| `terra-engine` (Python)    | LNN/EBM/KG-Loop, 8-Hz-Tick, lokales Working-State-SQLite     |
| `terra-engine-cli`         | Bedienung: `connect`, `status`, `snapshot`, `replay-load`    |
| Local SQLite               | Sitzungs-Working-State                                       |
| Optional: Docker           | `docker compose -f local-engine.yml up`                      |

Die Local Engine wird im Repo als eigener Top-Level-Modul ausgeliefert
(`engine/`). Sie spricht ausschließlich mit dem Hub über
`wss://<hub>/ws/v1/engine`.

---

## 5. Datenfluss

### Encounter-Pfad (Live, von Local Engine zum Browser)

```
Local Engine                 Hub (FastAPI + NATS + SQLite)              Browser
─────────────                ─────────────────────────────             ────────
1. Encounter detected
2. encounter_event(...)
   └─► WSS push
                              3. /ws/v1/engine receives
                              4. validate(JWT, schema)
                              5. write to SQLite (encounters)
                              6. publish to NATS encounters.<user_id>
                                 └─► fan-out to /ws/v1/viewer subscribers
                                                                       7. subscriber receives
                                                                       8. UI updates
```

Latenz-Ziel End-to-End (Engine → Browser): **< 250 ms p95** im selben
Kontinent. Cloudflare-Edge ist dabei der dominante Faktor (TLS-Handshake
findet einmal statt, danach reines QUIC-Tunneling).

### Replay-Pfad

```
1. Browser GET /v1/replay/timeline?...&q=...&ranking_mode=hybrid
2. FastAPI evaluates against SQLite (FTS5 + custom hybrid scorer)
3. Response body matches replay_timeline_window_v4
```

Wir übernehmen den Hybrid-Planner aus dem Bestand
(`backend/db/events.py::resolve_effective_ranking_policy`) ohne
funktionale Änderungen. SQLite-FTS5 ersetzt im MVP die DuckDB-FTS-
Implementierung; das Contract bleibt identisch.

### Snapshot-Pfad

```
1. Local Engine periodically: snapshot_request(scope=full|delta)
2. Engine builds snapshot bundle locally
3. Engine PUTs binary to /v1/snapshots (multipart, signed URL chain)
4. Hub forwards to NATS snapshots.<user_id>
5. Vault.snapshot-processor consumes, computes content hash
6. Vault uploads .tar.zst to R2: snapshots/<user_id>/<ts>-<hash>.tar.zst
7. Vault writes manifest row to its read-only SQLite (later mirrored)
8. Hub-SQLite gets manifest row via Litestream-out-of-band mechanism (M7)
```

R2 wird als „Cold Storage" genutzt; Hub-SQLite hält nur den Index/Manifest.

### Backup-Pfad

```
Hub-SQLite WAL frames
   └─► Litestream
       └─► R2 (litestream/<segment>/...)
   └─► (parallel) Vault.r2-pull holt eingehenden Stream
       und ersetzt seine lokale read-only-SQLite alle 30 s
```

Wenn der Hub stirbt: neuer Hub kann mit `litestream restore` aus R2 in
< 60 s einen vollständigen DB-State wieder aufbauen.

---

## 6. Datenmodell

### Speicherort-Übersicht

| Datenklasse                                | Ort (MVP)                                   | v2.0-Ziel                          |
|--------------------------------------------|---------------------------------------------|------------------------------------|
| User-/Session-/Auth-Stammdaten             | Hub-SQLite                                  | PostgreSQL                          |
| Encounter-Events (chronologisch)           | Hub-SQLite, FTS5 für Suche                  | ClickHouse (für Replay)             |
| Replay-Events (terra-079ff Hybrid-Schema)  | Hub-SQLite, gleicher Tabellen-Layout        | ClickHouse                          |
| KG-Knoten (eingelesen aus Preseed)         | Hub-SQLite (wenn Browse-Mode), sonst Engine | Neo4j                               |
| KG-Kanten                                  | Hub-SQLite (Browse-Mode), sonst Engine      | Neo4j                               |
| LNN-Working-State                          | **Local Engine** (lokale SQLite)            | Postgres + Object Snapshots          |
| EBM-Wells                                   | **Local Engine** + periodische Snapshots    | Neo4j (Tier-Detection auf GDS)      |
| Konzept-Embeddings (sobald genutzt)         | Local Engine (Numpy-Memmap)                 | Qdrant                              |
| Snapshots (Bundles)                         | R2                                           | MinIO                                |
| Volltext-Indizes für Suche                  | SQLite FTS5                                  | OpenSearch                          |

### Hub-SQLite-Schema (Auszug — vollständige Definition in M1)

```sql
-- users
CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  pwhash_argon2 TEXT NOT NULL,
  created_at    INTEGER NOT NULL,           -- unix epoch
  status        TEXT NOT NULL CHECK (status IN ('active','disabled')),
  is_admin      INTEGER NOT NULL DEFAULT 0
);

-- sessions
CREATE TABLE sessions (
  id            TEXT PRIMARY KEY,           -- ulid
  user_id       INTEGER NOT NULL REFERENCES users(id),
  created_at    INTEGER NOT NULL,
  expires_at    INTEGER NOT NULL,
  scope         TEXT NOT NULL,              -- 'viewer' | 'engine'
  client_label  TEXT
);

-- engine connections (active state, ephemeral)
CREATE TABLE engine_connections (
  id            TEXT PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  session_id    TEXT NOT NULL REFERENCES sessions(id),
  protocol_ver  TEXT NOT NULL,
  connected_at  INTEGER NOT NULL,
  last_heartbeat INTEGER NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('online','idle','closed'))
);

-- encounters (per-user encounter stream)
CREATE TABLE encounters (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  ts            INTEGER NOT NULL,
  word          TEXT,
  scale         REAL NOT NULL,
  source        TEXT NOT NULL,              -- 'user_input' | 'ghost' | 'walk' | ...
  context_json  TEXT NOT NULL                -- JSON, validated by API
);
CREATE INDEX idx_encounters_user_ts ON encounters(user_id, ts DESC);

-- replay_events (chronological tick log; layout matches existing terra contracts)
CREATE TABLE replay_events (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  ts            INTEGER NOT NULL,
  kind          TEXT NOT NULL,
  payload_json  TEXT NOT NULL,
  schema_ver    INTEGER NOT NULL
);
CREATE INDEX idx_replay_user_ts ON replay_events(user_id, ts);

-- replay_events FTS5 mirror (Hybrid-Planner support)
CREATE VIRTUAL TABLE replay_events_fts USING fts5(
  payload_text,
  kind,
  content='',                                -- contentless, hand-fed
  tokenize='unicode61 remove_diacritics 2'
);

-- snapshots (manifests; binary lives in R2)
CREATE TABLE snapshots (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  ts            INTEGER NOT NULL,
  scope         TEXT NOT NULL,              -- 'full' | 'delta'
  size_bytes    INTEGER NOT NULL,
  content_sha256 TEXT NOT NULL UNIQUE,
  r2_key        TEXT NOT NULL UNIQUE,
  status        TEXT NOT NULL CHECK (status IN ('uploading','ready','expired'))
);
```

Alle `*_json`-Spalten werden **vor** dem Schreiben gegen ein JSON-Schema
geprüft (siehe `docs/contracts/`); ungeprüftes JSON darf nicht persistiert
werden.

### Schema-Migration

Migrations werden über **`alembic`** verwaltet (auch wenn das
SQLAlchemy-Tool meist mit Postgres assoziiert ist — es funktioniert mit
SQLite einwandfrei, sobald wir es konfigurieren). Alternativen wie
`yoyo-migrations` werden bewusst nicht eingesetzt (geringere Verbreitung
im FastAPI-Ökosystem).

Migrations-Disziplin:

* **Vorwärts-monoton**: keine Down-Migrations in Production. Down nur in
  Tests.
* **Idempotent**: jede Migration muss `CREATE IF NOT EXISTS` /
  `DROP IF EXISTS` benutzen oder explizit beweisen, dass sie nur einmal
  läuft.
* **Schema-Version in `meta`-Tabelle**: zusätzlich zur Alembic-Historie
  pflegen wir eine eigene `meta`-Zeile mit der aktuellen Schema-Version,
  damit Backups eindeutig zuordenbar sind.

---

## 7. API-Contracts (HTTP + WebSocket)

### HTTP — `/v1/*`

Alle Endpunkte sind unter `https://<hub-host>/v1/` erreichbar. OpenAPI 3.1
wird automatisch aus den FastAPI-Routen generiert; Quelle ist
`backend/api/`.

#### Public (kein Auth)

| Method | Path                  | Zweck                                          |
|--------|-----------------------|------------------------------------------------|
| GET    | `/v1/health`          | Liveness-Probe für Cloudflare + Monitoring     |
| GET    | `/v1/version`         | `{api: "1.0.x", schema: 5, ...}`               |
| POST   | `/v1/auth/login`      | E-Mail + Passwort → JWT (RS256, 60-min)        |
| POST   | `/v1/auth/refresh`    | Refresh-Token → neues JWT                      |
| POST   | `/v1/auth/register`   | optional, default off (Admin-only Onboarding)  |

#### Authenticated — User Surface

| Method | Path                                             | Zweck                                                                   |
|--------|--------------------------------------------------|-------------------------------------------------------------------------|
| GET    | `/v1/me`                                         | Account-Status, Engine-Connections                                      |
| GET    | `/v1/encounters?since=...&limit=...`             | Encounter-Strom des Users                                               |
| POST   | `/v1/encounters`                                 | Encounter-Event manuell einfügen (z. B. aus Web-Chat)                  |
| GET    | `/v1/replay/timeline?...`                        | **Bestand** terra-076/079/080/082 — Hybrid-Planner unverändert          |
| GET    | `/v1/replay/density?...`                         | reserviert (terra-082 ff Density)                                       |
| POST   | `/v1/snapshots/initiate`                         | Engine fordert Snapshot-Upload-Slot an                                  |
| POST   | `/v1/snapshots/{id}/complete`                    | Engine markiert Upload als abgeschlossen                                |
| GET    | `/v1/snapshots`                                  | Liste der Snapshots des Users                                           |
| GET    | `/v1/snapshots/{id}`                             | Manifest + signierte R2-URL                                              |
| GET    | `/v1/diagnostic`                                 | **Bestand** — vollständiges Diagnose-Embed (terra-078/082 Counter)      |

#### Admin (`is_admin=1` + Cloudflare Access optional)

| Method | Path                              | Zweck                                |
|--------|-----------------------------------|--------------------------------------|
| GET    | `/v1/admin/users`                 | User-Liste                            |
| POST   | `/v1/admin/users`                 | User anlegen                          |
| PATCH  | `/v1/admin/users/{id}`            | enable/disable, admin-Flag           |
| GET    | `/v1/admin/connections`           | aktive Engine-/Viewer-Verbindungen   |
| POST   | `/v1/admin/maintenance/restart-tunnel` | sanftes `cloudflared`-Reload      |

### WebSocket — `/ws/v1/*`

| Path                | Subprotocol  | Auth                | Zweck                                            |
|---------------------|--------------|---------------------|--------------------------------------------------|
| `/ws/v1/viewer`     | `terra-viewer.v1` | JWT (Query oder Header) | Live-Push an Browser-Frontend                    |
| `/ws/v1/engine`     | `terra-engine.v1` | JWT + mTLS-Cert         | bidirektionaler Engine-Channel                   |

WS-Frames sind **JSON-Lines** (eine JSON-Map pro Frame). Binary-Frames
sind für Snapshot-Upload-Streaming reserviert (M2.4).

#### Viewer-Channel — Server → Client

```jsonc
// session bootstrap (immediately after authentication)
{ "type": "session/init", "schema_v": 1,
  "user_id": 17, "server_time_ms": 1715180400123,
  "active_engine": true,
  "feature_flags": { "ghost_queue": true, "replay_v4": true } }

// encounter pushed live
{ "type": "encounter/new", "schema_v": 1, "id": 9281,
  "ts": 1715180400500, "word": "...", "scale": 2.0,
  "source": "user_input", "context": { ... } }

// summary update (existing terra `summary` shape kept compatible)
{ "type": "engine/summary", "schema_v": 1,
  "tier_counts": { "T0": 12, "T1": 6, "T2": 3, "T3": 1 },
  "lnn": { "iD": 256, "norm": 0.84, "delta": 0.012 },
  "ghost_queue": { ... } }

// engine availability changed (local engine connected/lost)
{ "type": "engine/availability", "schema_v": 1, "online": true,
  "engine_label": "..." }

// server lifecycle
{ "type": "server/heartbeat", "schema_v": 1, "ts": 1715180401000 }
{ "type": "server/shutdown", "schema_v": 1, "graceful": true,
  "reconnect_after_ms": 2000 }
```

#### Viewer-Channel — Client → Server

```jsonc
// keepalive pong
{ "type": "client/pong", "schema_v": 1, "rx_ts": 1715180401000 }

// the user manually sends an encounter (e.g. chat input)
{ "type": "user/encounter", "schema_v": 1, "word": "...", "scale": 2.0,
  "context": { "ui_origin": "chat" } }

// replay control: pause/play/seek (forwarded to engine if connected)
{ "type": "replay/control", "schema_v": 1,
  "action": "pause" | "play" | "seek_to_ts" | "speed",
  "args": { ... } }
```

#### Engine-Channel — Engine → Server

```jsonc
{ "type": "engine/hello", "schema_v": 1,
  "engine_version": "1.0.0", "torch_version": "2.4.0",
  "device": "cuda:0", "label": "max-rig" }

{ "type": "engine/encounter", "schema_v": 1, "ts": 1715180400500,
  "word": "...", "scale": 2.0, "source": "user_input",
  "context": { ... } }

{ "type": "engine/summary", "schema_v": 1,
  "tier_counts": { ... }, "lnn": { ... }, "ghost_queue": { ... } }

{ "type": "engine/snapshot", "schema_v": 1, "scope": "full",
  "snapshot_id": 42, "size_bytes": 18234521,
  "content_sha256": "..." }     // followed by binary frames

{ "type": "engine/error", "schema_v": 1,
  "code": "lnn_ood", "msg": "...", "context": { ... } }
```

#### Engine-Channel — Server → Engine

```jsonc
{ "type": "server/welcome", "schema_v": 1,
  "engine_id": "01HXXXXX...", "session_token": "..." }

{ "type": "server/replay_command", "schema_v": 1,
  "action": "pause" | "play" | "seek_to_ts" | "speed",
  "args": { ... } }

{ "type": "server/heartbeat", "schema_v": 1, "ts": 1715180401000 }

{ "type": "server/disconnect", "schema_v": 1, "reason": "..." }
```

Alle Frames werden zentral gegen JSON-Schema validiert. Schemas leben in
`docs/contracts/ws/*.schema.json` und werden im CI-Pipeline-Step
`schema-lint` gegen die TS-/Python-Modelle geprüft.

### Bestehende Contracts, die unverändert übernommen werden

| Contract                                              | Quelle                                                                |
|-------------------------------------------------------|----------------------------------------------------------------------|
| `replay_timeline_window_v4`                            | `docs/contracts/replay_timeline_window_v4.schema.json`               |
| `runtime_ghost_queue_v0`                               | bestehender Bestand (`archive/legacy-docs/Implementierung.backend.api.md`)               |
| `runtime_pause_window_v0`                              | bestehender Bestand                                                  |
| `runtime_ghost_feedback_v0`                            | bestehender Bestand                                                  |

Der Greenfield-MVP **erweitert** diese Liste, **ersetzt** keinen Vertrag.

---

## 8. Engine-Protokoll (Local Engine ↔ Hub)

Detaillierter Vertrag zwischen Local Engine und Hub. Lebt parallel zum
WS-Channel `/ws/v1/engine`.

### Verbindungs-Lifecycle

1. **TLS-Handshake** mit dem Hub via Cloudflare-Edge.
2. **WS-Upgrade** mit `Sec-WebSocket-Protocol: terra-engine.v1`.
3. **JWT-Authentifizierung** im `Authorization`-Header **plus**
   **mTLS-Client-Zertifikat** (Cloudflare-Tunnel-Konfig spiegelt das durch).
4. Engine sendet `engine/hello`. Hub antwortet mit `server/welcome`.
5. Engine ist online: empfängt `replay_command`-Steuerungen,
   sendet Encounters, Summaries, Snapshots.
6. Heartbeat alle 10 s in beide Richtungen. 30 s ohne Pong → Hub
   markiert Engine `idle`.
7. Bei sanftem Shutdown: `server/disconnect` mit `reason="rotating"`,
   Engine reconnected mit Backoff 2/4/8 s.

### Protokoll-Versionierung

* **`engine_version`** im `engine/hello` ist informativ für
  Diagnose-/Debug-Zwecke.
* **`schema_v`** auf jedem Frame ist verbindlich. Der Hub akzeptiert nur
  `schema_v` aus seiner Whitelist; unbekannte Versionen → soft drop +
  Telemetrie-Log.
* **Major-Bumps** des WS-Subprotocol erzwingen Engine-Update vor
  Connect (HTTP 426 Upgrade Required im Handshake).

### Was die Local Engine vom Hub erwartet

* **Stabile Encounter-Replay-Pause-Semantik:** Wenn der Browser pause
  drückt, soll die Engine stoppen. Hub sendet `replay_command{action:"pause"}`.
* **Eindeutige Engine-IDs:** ein User darf gleichzeitig nicht zwei
  Engines online haben (Hub erzwingt das). Eine zweite Verbindung kickt
  die erste — mit klarer Statusmeldung.
* **Snapshot-Slot-Vergabe:** Engine fragt vor dem Upload nach einem
  signierten Slot, um nicht direkt mit R2 zu sprechen.

### Was die Local Engine NICHT erwarten darf

* Keine Server-seitige Persistenz für rohe Tick-Daten zwischen Snapshots.
  Das ist Engine-Sache. Server speichert Snapshots + Encounter-Strom +
  Summaries.
* Kein Automatik-Reset. Der Server greift nicht in Engine-State ein.
* Kein Ratenlimit auf Snapshot-Anlage in v1.0 (kommt mit v1.x bei Bedarf).
  Wir vertrauen, dass eine korrekte Engine maximal 1× pro 10 min einen
  Full-Snapshot, häufiger Deltas, schreibt.

### Detail-Vertrag steht in `M2-engine-protocol.md`

Implementierungs-Plan-Datei `implementation/mvp/M2-engine-protocol.md`
definiert: Schema-Dateien, Test-Suite, mTLS-Konfiguration,
Authentifizierungs-Reihenfolge, Reconnect-Mathe.

---

## 9. Sicherheit

### Surface-Annahmen

* **Cloudflare-Edge** als TLS-Terminator und WAF. Der Hub-Tunnel ist
  ausschließlich über das Cloudflare-Backend erreichbar — kein direkter
  IP-Hit.
* **Keine offenen Inbound-Ports** auf den Oracle-VMs. `iptables` defaultet
  auf DROP für externe Quellen. SSH ist über Cloudflare-Access-WARP +
  Bastion-Pattern abgesichert (separater Cloudflared-Tunnel mit `ssh`-Type).

### Authentifizierung

* **Passwörter:** Argon2id (`argon2-cffi`) mit empfohlenem
  `time=3, mem=64 MiB, parallelism=2`.
* **JWT:** RS256, Schlüsselpaar als Hub-Secret (4096-Bit RSA).
  Access-Token TTL 60 min, Refresh-Token TTL 30 Tage, rotierend.
  Claims: `sub`, `email`, `scope ∈ {viewer, engine, admin}`,
  `iat`, `exp`, `jti`.
* **Refresh-Token** als HTTP-Only-Cookie mit `SameSite=Lax`. Access-Token
  wird im Browser im Memory gehalten (nicht localStorage).

### Autorisierung

* **Tenant-Isolation pro `user_id`.** Kein API-Pfad erlaubt Zugriff auf
  andere User-Daten. Im SQL gilt: jede Query auf User-Daten muss
  `user_id = ?` enthalten — durchgesetzt durch Repository-Layer.
* **Engine-Sessions** kollidieren nicht mit Viewer-Sessions: ein Token mit
  `scope=viewer` kann nicht das Engine-WS öffnen.
* **Admin-Routen** sind zusätzlich hinter Cloudflare Access geschützt
  (optional, recommended). Access-Policy: `email ∈ admin@…`.

### Eingabe-Validierung

* **JSON-Schema-First.** Jeder eingehende JSON-Body wird zentral
  validiert. Pydantic-Modelle sind die Schreibweise; sie werden zu
  JSON-Schema kompiliert und im OpenAPI ausgespielt.
* **Größenbeschränkungen:** Encounter-Body max 4 KB, Snapshot-Initiate
  max 16 KB Manifest, Snapshot-Binary max 64 MB pro Bundle.
* **Rate-Limits per Token + IP:** 600 req/min global pro Token,
  60 req/min für Auth-Routen pro IP, 1 Snapshot-Initiate pro 30 s pro
  User.

### Geheimnisse

* **SOPS** mit AGE-Key. Hub-Secrets liegen verschlüsselt im Repo unter
  `secrets/hub.sops.yaml`. CI entschlüsselt zur Deploy-Zeit. Vault-Key
  liegt nicht im Repo.
* **Cloudflare-Tunnel-Credentials** liegen nur in `hub-cloudflared-cred`-
  Volume; wir committen sie nicht. `.gitignore` deckt
  `secrets/*.unencrypted.*` und `cloudflared/*.json` ab.

### Logging-Hygiene

* **Keine Passwörter, JWTs, Argon2-Hashes oder Refresh-Tokens** im Log —
  weder Plain noch maskiert. Der zentrale Logger filtert über
  Header-Allowlist.
* **PII-Felder** (E-Mails) werden im aggregierten Log auf das erste
  Domain-Label reduziert (`m***@domain.tld`) und nur im Audit-Log
  unverkürzt geführt.

### Threat-Modell (Kurzfassung)

| Bedrohung                              | Mitigation                                         |
|----------------------------------------|----------------------------------------------------|
| Cred-Stuffing auf `/v1/auth/login`     | Argon2id + Rate-Limit + optional CAPTCHA an v1.x  |
| Token-Diebstahl aus Browser-Storage    | Token nur im Memory; Refresh nur als HttpOnly      |
| Engine-Token-Spoofing                  | mTLS-Client-Cert zusätzlich zu JWT                 |
| Resource-Exhaustion                    | Body-Limits, Rate-Limits, OOM-Guards in Compose    |
| Open-Tunnel-Hijack auf VM              | nur ausgehender CF-Tunnel, kein offener Port       |
| SQLi in Replay-Suche                   | Parameterisierte Queries; FTS-Eingabe escaped      |
| XSS im Frontend                         | strikte CSP `default-src 'self'`; React-DOM-Escape |

---

## 10. Beobachtbarkeit

### Metriken (Prometheus, Hub-lokal)

* **System-Metriken:** Node-Exporter (CPU, RAM, Disk-IO, Netz).
* **API-Metriken:** Standard-FastAPI-Middleware schreibt Histogramme:
  `http_request_duration_seconds{route,method,code}`,
  `http_in_flight_requests`, `http_request_size_bytes`.
* **Domain-Metriken** (eigener Prom-Client):
  * `terra_encounters_total{user, source}`
  * `terra_engine_connections_active{user}`
  * `terra_replay_fts_ops{policy}` — übernehmen aus terra-082
  * `terra_snapshots_uploaded_total{scope}`
  * `terra_litestream_lag_seconds`
  * `terra_nats_consumer_lag{stream, consumer}`

### Dashboards (Grafana)

| Dashboard                | Inhalt                                                          |
|--------------------------|------------------------------------------------------------------|
| `Hub Health`             | RAM/CPU/Disk-Free, OOM-Killer-Events, Service-Restart-Counter   |
| `Hub API`                | Req/s, p95-Latenz pro Route, 4xx/5xx-Breakdown                  |
| `Hub Realtime`           | aktive WS-Connections, Encounter-Throughput, NATS-Lag           |
| `Hub Replay`             | Replay-Hybrid-Counters, FTS-Rebuild-Stats                       |
| `Hub Persistence`        | Litestream-Lag, R2-Upload-Errors                                 |
| `Vault`                  | r2-pull-Lag, Snapshot-Processor-Throughput                      |

### Tracing — bewusst NICHT im MVP

OTel-Tracing (`tempo`) wird im MVP **ausgelassen**, weil der Speicherplatz
es nicht hergibt. Stattdessen reicht **strukturiertes JSON-Logging** mit
`trace_id` per Request (selbst generiert oder aus dem CF-Header `cf-ray`).

### Logging

* **Format:** JSON Lines, Schlüssel `ts, level, service, msg, trace_id, …`.
* **Sammlung:** `vector` reads `journald` per Service, schreibt in eine
  rotierte Datei unter `/var/log/terra/`. Optional → R2 (komprimiert,
  täglich) für Audit-Zwecke. Keine externen Logging-SaaS-Integration im
  MVP.
* **Retention:** 14 Tage lokal, 90 Tage in R2.

### Alerting (minimal)

`prom-server` mit `alertmanager` oder dem leichteren `grafana-alerting`:

| Alert                                         | Schwelle                                       | Wohin                |
|-----------------------------------------------|------------------------------------------------|----------------------|
| Hub-RAM-Utilization > 92 %                    | 5 min sustained                                | E-Mail + CF Webhook  |
| Hub-Filesystem-Free < 5 GB                    | sofort                                         | E-Mail               |
| Service `api` neu gestartet > 3× / 30 min     |                                                | E-Mail               |
| Litestream-Lag > 90 s                         | 10 min sustained                               | E-Mail               |
| `cloudflared` down                            | 60 s                                           | E-Mail               |
| Vault-r2-pull-Lag > 5 min                     | 10 min sustained                               | E-Mail               |

---

## 11. Deployment

### Layer 1 — Image-Build

* GitHub Actions Workflow `ci-build-images.yml` baut bei jedem Push auf
  `main` und auf `feature/*`-Branches multi-arch fähige Images, **aber
  liefert auf Oracle nur `amd64`** aus (AMD-VMs sind x86).
* Images werden zu **Cloudflare Image Registry** (R2-basiertes ECR-
  Substitut) oder GitHub Container Registry gepusht. MVP-Default:
  **GHCR** (`ghcr.io/walkiger/terra-incognita-*`).
* Signed Images (`cosign`), SBOM (`syft`) im CI generiert.

### Layer 2 — Konfiguration

* Compose-Dateien:
  * `deploy/compose/hub.yml` — VM-A
  * `deploy/compose/vault.yml` — VM-B
  * `deploy/compose/local-engine-dev.yml` — Workstation (Dev)
* `*.env`-Dateien werden aus SOPS-Secrets generiert, **nicht** committed.

### Layer 3 — Deploy auf Oracle

* Deploy-Tool: **Ansible** (Playbook `deploy/ansible/site.yml`).
* Connection: über Cloudflare-WARP-bridged SSH oder
  `cloudflared access ssh`. Keine offene Port-22-Exposition.
* Flow:
  1. `ansible-playbook site.yml --limit hub` → Hub aktualisieren.
  2. Health-Check `curl https://<hub-host>/v1/health` → 200.
  3. `ansible-playbook site.yml --limit vault` → Vault aktualisieren.
* Rollback: `ansible-playbook site.yml --limit hub -e image_tag=previous`.
  GHCR hält die letzten 10 Tags vorrätig.

### Layer 4 — Cloudflare-Konfiguration

* Tunnel-Routen:
  * `terra.<example>.tld` → Hub `api` (HTTPS)
  * `app.terra.<example>.tld` → Hub `caddy` (Frontend statisch — Caddy
    serviert Build-Output)
  * `mirror.app.terra.<example>.tld` → Vault `caddy` (Notnagel-Frontend)
* Access-Policies:
  * `/v1/admin/*` → Cloudflare Access, Allowlist
  * Sonstige Pfade → public, Auth über JWT
* Cache-Settings: API-Pfade `Cache-Control: no-store`,
  Static-Bundle (`/assets/...`) immutable + 1 Jahr.

### Health-Probes

* `/v1/health` antwortet **immer in < 50 ms**:
  ```json
  { "ok": true,
    "version": "1.0.x",
    "schema": 5,
    "uptime_s": 1234,
    "deps": { "sqlite": "ok", "nats": "ok", "litestream": "ok" } }
  ```
* `/v1/diagnostic` ist **vollständige** Diagnose und nicht für Cloudflare-
  Healthcheck geeignet. (Bestand terra-078/082 wird unverändert genutzt.)

### Releases

* Tag pro v0.x.0-Bump: `git tag v0.5.0 && git push --tags`.
* GitHub Action `cd-release.yml` baut Final-Image, signiert, schreibt
  Release-Notes aus `catchup.md`-Diff seit letztem Tag.
* `v1.0.0` ist die einzige Major-Marke des MVP-Plans; danach `v1.x.y`.

---

## 12. Multi-User

### Modell

* **Pro registriertem Account ein Encounter-Strom.** Streams sind
  unabhängig. Es gibt **keine** Cross-User-KG-Sicht im MVP — der
  Knowledge-Graph eines Users ist *seiner*.
* **Concurrency-Ziel:** ~50 gleichzeitige Viewer-WS-Connections und
  ~10 gleichzeitige Engine-WS-Connections auf VM-A (RAM-Limit
  realistisch).
* **Anonymous Browse-Mode:** Optional kann ein read-only Pfad
  `/v1/public/preseed` eingerichtet werden (KG-Snapshot der Preseed-Daten,
  ohne User-Encounters). MVP-Default: aus.

### Tenant-Isolation

* **DB:** jede Query enthält `user_id`. Repository-Layer verbietet
  Verstöße via Pydantic-Model.
* **NATS:** Subjects pro User (`encounters.<user_id>`,
  `replay.<user_id>`, `snapshots.<user_id>`). Subscriptions filtern
  serverseitig per Token-Claim.
* **R2:** Object-Keys mit Prefix `<user_id>/`. Kein Listing-Endpunkt im
  Hub-API, der das überschreitet.

### Kollisionen

* **Mehrere Engines pro User:** explizit unterbunden. Hub trackt einen
  einzelnen aktiven `engine_connection` pro User; ein zweiter Connect
  schließt die alte Verbindung mit `server/disconnect{ reason: "engine_replaced" }`.
* **Mehrere Viewer pro User:** erlaubt und gewollt (Tab-Wechsel, mehrere
  Geräte). Alle bekommen denselben Stream.

### Quotas (MVP-Default)

| Resource                    | Pro User    |
|-----------------------------|-------------|
| Encounter-Schreibrate       | 30 / min    |
| Snapshot-Volumen total       | 1 GB         |
| Anzahl gehaltener Snapshots | 50          |
| Replay-Query-Rate           | 60 / min    |

Verstöße: weiches Throttling (HTTP 429 + `Retry-After`), kein Account-
Block.

---

## 13. Speicher-Budget

### Hub (1 GB)

| Komponente                    | RAM (typisch) | Spitze (Last)        |
|-------------------------------|---------------|----------------------|
| Linux + Docker                | 200 MB        | 240 MB               |
| Caddy                         | 30 MB         | 40 MB                |
| FastAPI / uvicorn (1 worker)  | 100 MB        | 180 MB (10 WS)       |
| NATS JetStream                | 80 MB         | 120 MB (Spitze)      |
| Litestream                    | 20 MB         | 30 MB                |
| cloudflared                   | 40 MB         | 60 MB                |
| Prom + Node-Exporter          | 100 MB        | 120 MB               |
| Grafana (optional, default an)| 110 MB        | 130 MB               |
| Reserve                       | —             | 80 MB                |
| **Summe**                      | **680 MB**     | **~1000 MB Spitze**   |

**Wenn Spitzen > 920 MB:** Grafana abschalten (`compose --profile minimal up`)
zur Entlastung.

### Vault (1 GB)

| Komponente                    | RAM (typisch) | Spitze (Last)        |
|-------------------------------|---------------|----------------------|
| Linux + Docker                | 200 MB        | 240 MB               |
| Caddy (statisches FE)         | 30 MB         | 40 MB                |
| cloudflared                   | 40 MB         | 60 MB                |
| r2-pull worker                | 60 MB         | 90 MB                |
| snapshot-processor            | 80 MB         | 200 MB (zstd-Compress)|
| nats-subscriber               | 50 MB         | 70 MB                |
| Node-Exporter                 | 20 MB         | 30 MB                |
| Reserve                       | —             | 250 MB               |
| **Summe**                      | **480 MB**     | **~730 MB Spitze**    |

**Vault hat mehr Headroom**, weil keine Live-User-Last anfällt.

### Disk (50 GB Block pro VM)

* Hub: SQLite (~5 GB Erwartung), NATS-JetStream (~2 GB max),
  Prom-TSDB 7d (~2 GB), Image-Cache (~3 GB), Logs (~1 GB), Reserve
  (~37 GB).
* Vault: SQLite-Mirror (~5 GB), Image-Cache (~3 GB), Snapshot-Buffer
  vor R2-Upload (~5 GB), Logs (~1 GB), Reserve (~36 GB).

### R2 (10 GB free)

| Inhalt                     | Erwartung 1.0 / Jahr | Wachstum  |
|----------------------------|---------------------|-----------|
| Litestream-Backups (Hub)   | 1–3 GB              | langsam   |
| Snapshots (Pro User × 50)  | 0.5 GB pro User × 20 = 10 GB | linear |
| Replay-Bundles (optional)  | < 0.5 GB            | langsam   |
| **Summe**                   | **~13 GB im Schwellenfall** | mit Pruning steuerbar |

**Pruning-Strategie:** Snapshots > 30 Tage alt + älter als der jeweils
zuletzt verfügbare Full-Snapshot werden automatisch verworfen (Lifecycle-
Policy in R2 + `vault.snapshot-processor`).

---

## 14. Migration nach v2.0

Der MVP ist so gebaut, dass v1.x → v2.0 **kein Rewrite** ist, sondern eine
Service-für-Service-Verschiebung. Details in
`architecture/production.md`. Hier nur der Pfad in einem Satz pro
Komponente:

| Komponente            | v1.0                         | v2.0                                     |
|-----------------------|-------------------------------|------------------------------------------|
| HTTP-API              | FastAPI                      | FastAPI (unverändert, neu deployt)        |
| WebSocket-API         | FastAPI                      | FastAPI (unverändert, neu deployt)        |
| Persistenz            | SQLite + Litestream + R2     | PostgreSQL 16 + MinIO Cluster             |
| Encounter-Stream      | SQLite Tabelle                | ClickHouse + Postgres-Spiegel             |
| Replay-Suche          | SQLite FTS5                   | OpenSearch                                |
| KG                    | (lokal in Engine)             | Neo4j Enterprise                          |
| Vektoren              | (lokal in Engine, Numpy)      | Qdrant                                     |
| Event-Log             | NATS JetStream                | Redpanda (Kafka-API)                      |
| Cache / Pub/Sub       | (NATS reicht)                 | DragonflyDB                               |
| Tick-Engine           | Local Workstation             | M4-Hub (eigener Prozess, ggf. Free-Threaded Python 3.13t) |
| Frontend              | identisch                     | identisch                                 |
| Tunnel                | Cloudflare Free                | Cloudflare Free, ggf. Paid                |
| Observability         | Prom + Grafana                | + Loki + Tempo + OTel                     |

**Migration läuft inkrementell:** v2.0 schreibt eine Phase lang **parallel**
in alt + neu, bis das neue System konsistent ist. Erst dann wird das alte
abgeschaltet.

---

## 15. Risiken & Mitigationen

| Risiko                                                                | Wahrscheinlichkeit | Impact   | Mitigation                                                                                                      |
|-----------------------------------------------------------------------|--------------------|----------|-----------------------------------------------------------------------------------------------------------------|
| OOM-Kill auf Hub bei Lastspitze                                       | mittel             | hoch     | Compose-`mem_limit` pro Service; OOM-Killer-Reihenfolge per `oom_score_adj`; Grafana abschaltbar                 |
| SQLite-Lock-Contention bei vielen Concurrent-Writern                  | niedrig            | mittel   | Single-Writer-Pattern erzwingen; alle Schreibwege durchs API gebündelt; WAL aktiv                                |
| R2-Free-Tier-Limit überschritten                                      | mittel             | mittel   | Pruning-Lifecycle; Soft-Quota pro User; Frühwarn-Alert bei 80 %                                                  |
| Cloudflare-Free-Tunnel rate-limit                                     | niedrig            | mittel   | wir liegen weit unter den 50 Mbps; Fallback Vault-Tunnel + DNS-Failover                                            |
| Local Engine fehlerhaft → falsche Encounters in Stream                | mittel             | mittel   | Schema-Validierung am Hub; Anomaliedetektor („Encounter-Burst") loggt Warnungen                                  |
| AMD-Micro-VM ungeplant terminiert (Oracle-Always-Free-Politik)        | niedrig            | hoch     | Litestream-Backup → R2 → minutiöses Restore; Vault als Hot-Spare; Doku „Replace VM"                              |
| Token-Diebstahl                                                       | mittel             | hoch     | mTLS für Engine; kurze Token-TTL; Refresh-Token-Rotation; `jti`-Revoke-Liste                                       |
| Replay-FTS-Index korrumpiert                                          | niedrig            | mittel   | Rebuild-Hook (terra-075/078) bleibt aktiv; Health-Probe prüft `fts_index_schema_present`                          |
| User registriert sich, fragt Daten, verschwindet (DSGVO-Right-to-Erase) | mittel             | mittel   | Endpoint `DELETE /v1/me` löscht alle User-Daten (DB + R2); 30-Tage-Retention dokumentiert                         |
| Nutzer ohne Workstation kann „nichts tun"                             | hoch               | mittel   | Browse-/Demo-Modus mit Preseed-KG read-only (optional in M6); klar kommuniziert in Onboarding                     |

---

## 16. Offene Fragen

* **Public-Demo-Modus:** Wollen wir in v1.0 schon einen anonymen
  Read-Only-Modus für Preseed-Browse anbieten? (Dann: M6 erweitert um
  Anonymous-Pfad.)
* **Multi-Region-Failover:** In v1.x denkbar, dass Vault in einer anderen
  Oracle-Region steht. Im MVP nicht.
* **Self-Service-Registrierung:** Default off (Admin-only Onboarding).
  Soll das in v1.x auf Self-Service mit E-Mail-Bestätigung wechseln?
* **Cloudflare Workers für statische Asset-Auslieferung:** Workers-Free
  hat 100 k Requests/Tag. Würde Hub-Load reduzieren.
* **Public KG-Browse:** Wenn ja, was ist der Inhalt — Preseed-Snapshot
  oder eine kuratierte Untermenge?

---

## 17. Querverweise

* `00-glossary.md` — Begriffe
* `architecture/production.md` — v2.0
* `implementation/mvp/00-index.md` — Phasen, Status, Branches
* `formulas/registry.md` — `F.*`-Formel-Einträge
* `protocols/pdf-lookup.md` — PDF-Recherche-Vertrag
* `Anweisungen.md` §7 — Non-Negotiables, die hier nicht wiederholt sind
* `docs/ARCHITECTURE.md` — Architektur des bestehenden Systems
  (Quelle für Tier-Hierarchie, LNN-Mathematik, EBM-Wells-Lebenszyklus)
* `docs/contracts/replay_timeline_window_v4.schema.json` — Replay-Vertrag

---

*Stand: 2026-05-08 · Greenfield-Initial · Pfad B*
