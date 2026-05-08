# `architecture/data-model.md` — Kanonisches Datenmodell v1.0 → v2.0

> **Zweck.** Ein **lebendiges**, vollständiges Datenmodell aller
> Speicher­schichten — sowohl für die v1.0-MVP-Phase auf 2× AMD Micro
> (SQLite + NATS JetStream + Cloudflare R2) als auch für die
> v2.0-Vollausbaustufe auf M4 (Polyglot-Stack).
>
> Die v1.0-Kapitel sind **autoritativ** für die MVP-Implementierung
> (M0–M8). Die v2.0-Kapitel sind **Vertrag** dafür, **wie** die
> Migration ohne Bruch funktioniert: was Eins-zu-Eins migriert wird,
> was umgeformt wird, was neu hinzukommt.

---

## Inhalt

1. [Geltungsbereich & Stabilitäts­zusagen](#1-geltungsbereich--stabilitätszusagen)
2. [Domänen­modell (Begriffe, IDs)](#2-domänenmodell-begriffe-ids)
3. [v1.0 — SQLite-Schema (autoritativ)](#3-v10--sqlite-schema-autoritativ)
4. [v1.0 — NATS-Subjekte & Stream-Grenzen](#4-v10--nats-subjekte--stream-grenzen)
5. [v1.0 — R2-Bucket-Layout](#5-v10--r2-bucket-layout)
6. [v1.0 — Engine-Snapshot-Format](#6-v10--engine-snapshot-format)
7. [v2.0 — Polyglot-Mapping pro Tabelle/Stream](#7-v20--polyglot-mapping-pro-tabellestream)
8. [Migration v1 → v2 (Dual-Write)](#8-migration-v1--v2-dual-write)
9. [Konsistenz- & Integritäts­regeln](#9-konsistenz--integritätsregeln)
10. [Aufbewahrungs- & Lösch­regeln](#10-aufbewahrungs--löschregeln)
11. [Schutzklassen, PII, DSGVO-Bezug](#11-schutzklassen-pii-dsgvo-bezug)
12. [Beispieldaten](#12-beispieldaten)

---

## 1. Geltungsbereich & Stabilitäts­zusagen

* Dieses Dokument deckt **alle** persistierten Datenformen ab, die
  über einen Laufzeit­zyklus hinaus existieren:
  * Relationale Tabellen (SQLite/Postgres),
  * Event-Streams (NATS/Redpanda),
  * Object Storage (R2/MinIO),
  * Snapshots (Engine-seitig erzeugt, server­seitig gespeichert).
* **Stabilitätszusagen v1.0**:
  * `replay_events`-Spalten sind **eingefroren** ab `v0.5.x` (M5).
  * `snapshots.manifest_json`-Schema ist **eingefroren** ab `v0.3.x` (M2).
  * NATS-Subjekt­namen (`engine.events.*`, `engine.heartbeat.*`,
    `replay.window.*`) sind **eingefroren** ab `v0.3.x` (M2).
  * Cookies/JWT-Claims sind **eingefroren** ab `v0.5.x` (M5).
* **Stabilitätszusagen v2.0**:
  * v1.x-API-Pfade bleiben gültig (`/api/v1/...`, `/ws/...`).
  * Die unten unter §7 genannten Mapping-Tabellen erlauben einen
    *Dual-Write*-Migrations­pfad ohne Schema-Bruch.

---

## 2. Domänen­modell (Begriffe, IDs)

> Vollständig referenziert in `00-glossary.md`. Hier die in
> Datenbank­zeilen sichtbare Form.

* **`UserID`** — `INTEGER PRIMARY KEY` in v1.0; `BIGINT` in v2.0.
* **`SessionID`** — `BIGINT` mit Schemata `<unix_ms_at_create>` plus
  4-Bit-Salt (vermeidet Kollisionen bei parallelen Sessions).
* **`EncounterID`** — String der Form
  `e_<unix_ms>_<6char-base32-rand>`; sortier­bar nach Zeit.
* **`SnapshotID`** — String `snap_<unix_ms>_<6char-base32>`.
* **`EventID`** — `BIGINT AUTOINCREMENT` (SQLite); in v2.0
  ULID/UUIDv7-basiert für globale Ordnung.
* **`F.{POL}.{TOPIC}.{NNN}`** — Formel-IDs (siehe `formulas/registry.md`).
* **`Lang`** — ISO-639-1 Zwei-Zeichen-Code (`de`, `en`, `fr`, …); in
  v1.0 nur `de`/`en` ausgeliefert.

---

## 3. v1.0 — SQLite-Schema (autoritativ)

### 3.1 Tabelle `users`

```sql
CREATE TABLE users (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  email           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,             -- Argon2id Encoded String
  display_name    TEXT NOT NULL,
  preferred_lang  TEXT NOT NULL DEFAULT 'de',-- 'de'|'en'
  is_admin        INTEGER NOT NULL DEFAULT 0,-- 0/1 boolean
  is_disabled     INTEGER NOT NULL DEFAULT 0,
  created_at_ms   INTEGER NOT NULL,
  updated_at_ms   INTEGER NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
```

**Regeln:**

* `email` wird **klein­geschrieben** und Whitespace-getrimmt
  gespeichert (DB-seitig per `BEFORE INSERT/UPDATE`-Trigger erzwungen,
  applikativ zusätzlich validiert).
* `password_hash` enthält den **kompletten** Argon2id-Encoded String
  (`$argon2id$v=19$m=…,t=…,p=…$<salt>$<hash>`).
* `is_admin = 1` darf nur durch CLI-Pfad gesetzt werden
  (`scripts/admin.py promote --user-id ...`); kein API-Endpoint.

### 3.2 Tabelle `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash      TEXT NOT NULL,                   -- SHA-256 hex (kein Plaintext)
  parent_token_id INTEGER REFERENCES refresh_tokens(id) ON DELETE SET NULL,
  issued_at_ms    INTEGER NOT NULL,
  expires_at_ms   INTEGER NOT NULL,
  rotated_at_ms   INTEGER,                          -- gesetzt bei Reuse-Detection
  revoked         INTEGER NOT NULL DEFAULT 0,
  user_agent      TEXT,
  ip_hash         TEXT                              -- HMAC-SHA-256(ip, server_secret)
);

CREATE INDEX idx_rt_user ON refresh_tokens(user_id);
CREATE INDEX idx_rt_active ON refresh_tokens(user_id, revoked, expires_at_ms);
```

**Regeln:**

* Nur `token_hash` gespeichert; das Klartext-Token verlässt nie den
  Server (außer im Set-Cookie der Antwort).
* **Refresh-Token-Reuse-Detection**: Wenn ein bereits rotiertes Token
  erneut verwendet wird → ganze Token-Familie revoken
  (`UPDATE … SET revoked=1 WHERE user_id=? AND parent_token_id IS NOT NULL`).
* `ip_hash` ist HMAC, kein Klartext (Datenschutz, siehe §11).

### 3.3 Tabelle `sessions`

```sql
CREATE TABLE sessions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at_ms INTEGER NOT NULL,
  ended_at_ms   INTEGER,
  channel       TEXT NOT NULL,    -- 'web'|'engine'
  client_meta   TEXT              -- JSON-blob
);

CREATE INDEX idx_sessions_user ON sessions(user_id, started_at_ms);
```

### 3.4 Tabelle `encounters`

```sql
CREATE TABLE encounters (
  id            TEXT PRIMARY KEY,             -- 'e_<unix_ms>_<rand6>'
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id    INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
  ts_ms         INTEGER NOT NULL,
  word          TEXT NOT NULL,
  lang          TEXT NOT NULL DEFAULT 'de',
  channel       TEXT NOT NULL,                 -- 'chat'|'engine_input'|'replay_simulated'
  payload_json  TEXT NOT NULL,                 -- JSON: tags, source, raw
  created_at_ms INTEGER NOT NULL
);

CREATE INDEX idx_enc_user_ts ON encounters(user_id, ts_ms);
CREATE INDEX idx_enc_word    ON encounters(word);
```

### 3.5 Tabelle `replay_events`

```sql
CREATE TABLE replay_events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ts_ms           INTEGER NOT NULL,             -- Engine-Zeit
  event_kind      TEXT NOT NULL,                -- 'encounter'|'tier_emerge'|'well_birth'|'well_dormant'|'kg_edge_change'|'summary'
  word            TEXT,                         -- nullable; nicht alle Events haben Wort
  meta_json       TEXT NOT NULL,                -- JSON-Payload je event_kind
  source_engine   TEXT,                         -- engine_id (slug) der Quelle
  ingest_lag_ms   INTEGER,                      -- created_at_ms - ts_ms
  created_at_ms   INTEGER NOT NULL
);

CREATE INDEX idx_re_user_ts        ON replay_events(user_id, ts_ms);
CREATE INDEX idx_re_user_kind_ts   ON replay_events(user_id, event_kind, ts_ms);

-- FTS5-Spiegel für Hybrid-Ranking
CREATE VIRTUAL TABLE replay_events_fts USING fts5(
  word, meta_text, event_kind UNINDEXED,
  content='replay_events',
  content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER replay_events_ai AFTER INSERT ON replay_events BEGIN
  INSERT INTO replay_events_fts(rowid, word, meta_text)
  VALUES (NEW.id, COALESCE(NEW.word,''), json_extract(NEW.meta_json, '$.text'));
END;

CREATE TRIGGER replay_events_ad AFTER DELETE ON replay_events BEGIN
  INSERT INTO replay_events_fts(replay_events_fts, rowid, word, meta_text)
  VALUES ('delete', OLD.id, COALESCE(OLD.word,''), json_extract(OLD.meta_json, '$.text'));
END;

CREATE TRIGGER replay_events_au AFTER UPDATE ON replay_events BEGIN
  INSERT INTO replay_events_fts(replay_events_fts, rowid, word, meta_text)
  VALUES ('delete', OLD.id, COALESCE(OLD.word,''), json_extract(OLD.meta_json, '$.text'));
  INSERT INTO replay_events_fts(rowid, word, meta_text)
  VALUES (NEW.id, COALESCE(NEW.word,''), json_extract(NEW.meta_json, '$.text'));
END;
```

### 3.6 Tabelle `snapshots`

```sql
CREATE TABLE snapshots (
  id              TEXT PRIMARY KEY,                       -- 'snap_<unix_ms>_<rand6>'
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  engine_id       TEXT NOT NULL,
  taken_at_ms     INTEGER NOT NULL,
  uploaded_at_ms  INTEGER NOT NULL,
  bytes           INTEGER NOT NULL,
  sha256_hex      TEXT NOT NULL,
  manifest_json   TEXT NOT NULL,                            -- siehe §6
  r2_key          TEXT NOT NULL,                            -- 's/{user_id}/{snapshot_id}.tar.zst'
  is_active       INTEGER NOT NULL DEFAULT 1,
  retention_class TEXT NOT NULL DEFAULT 'standard'          -- 'standard'|'archive'|'pinned'
);

CREATE INDEX idx_snap_user_ts ON snapshots(user_id, taken_at_ms);
CREATE INDEX idx_snap_active  ON snapshots(user_id, is_active);
```

### 3.7 Tabelle `engine_registrations`

```sql
CREATE TABLE engine_registrations (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  engine_id          TEXT NOT NULL,                   -- selbstgewählter Slug
  cert_thumbprint    TEXT NOT NULL,                   -- SHA-256(client cert)
  first_connected_ms INTEGER NOT NULL,
  last_connected_ms  INTEGER NOT NULL,
  is_active          INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX uq_eng_user_engine ON engine_registrations(user_id, engine_id);
CREATE INDEX idx_eng_thumb            ON engine_registrations(cert_thumbprint);
```

### 3.8 Tabelle `audit_log`

```sql
CREATE TABLE audit_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_ms         INTEGER NOT NULL,
  actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action        TEXT NOT NULL,                      -- 'login'|'register'|'rotate-token'|'snapshot.upload'|'engine.connect'|'admin.*'
  target_kind   TEXT,                                 -- 'user'|'snapshot'|'engine'|...
  target_id     TEXT,
  meta_json     TEXT,
  client_ip_h   TEXT,
  user_agent    TEXT
);

CREATE INDEX idx_audit_actor_ts ON audit_log(actor_user_id, ts_ms);
CREATE INDEX idx_audit_action_ts ON audit_log(action, ts_ms);
```

### 3.9 Tabelle `quota_usage`

```sql
CREATE TABLE quota_usage (
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  bucket      TEXT NOT NULL,         -- 'snapshot.bytes_30d'|'replay.requests_1d'|'ws.events_1h'|'login.fail_15m'
  window_ms   INTEGER NOT NULL,      -- Fenster-Anker (gerundet)
  value       INTEGER NOT NULL,
  updated_ms  INTEGER NOT NULL,
  PRIMARY KEY (user_id, bucket, window_ms)
);

CREATE INDEX idx_qu_bucket_window ON quota_usage(bucket, window_ms);
```

### 3.10 Tabelle `system_health`

```sql
CREATE TABLE system_health (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_ms       INTEGER NOT NULL,
  metric_key  TEXT NOT NULL,           -- 'rss_mb'|'cpu_pct'|'fts_count'|'nats_lag_ms'|'litestream_replication_lag_ms'
  value_num   REAL NOT NULL,
  meta_json   TEXT
);

CREATE INDEX idx_sh_key_ts ON system_health(metric_key, ts_ms);
```

### 3.11 Tabelle `settings`

```sql
CREATE TABLE settings (
  user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  key       TEXT NOT NULL,
  value     TEXT NOT NULL,        -- JSON-encoded
  updated_ms INTEGER NOT NULL,
  PRIMARY KEY (user_id, key)
);
```

### 3.12 Tabelle `kv_cache`

```sql
CREATE TABLE kv_cache (
  scope       TEXT NOT NULL,        -- 'replay.window'|'preseed.lookup'
  key         TEXT NOT NULL,
  value_blob  BLOB NOT NULL,
  expires_ms  INTEGER NOT NULL,
  bytes       INTEGER NOT NULL,
  PRIMARY KEY (scope, key)
);

CREATE INDEX idx_kv_expires ON kv_cache(expires_ms);
```

> *Hinweis.* `kv_cache` dient nur als sehr leichter In-Process-Hilfs­
> cache. Für ernsthaftes Caching wird in v2.0 **DragonflyDB** ergänzt;
> `kv_cache` wird dann optional auf passive Replikation gestellt.

---

## 4. v1.0 — NATS-Subjekte & Stream-Grenzen

* Stream `engine` (Persistenz: file, max 64 MiB, max age 7d):
  * `engine.events.<user_id>.<engine_id>.<event_kind>` — alle Events
    aus Engine.
  * `engine.heartbeat.<user_id>.<engine_id>` — 1× pro 5 s.
  * `engine.summary.<user_id>.<engine_id>` — 1× pro Minute.
* Stream `replay` (Persistenz: memory, max 32 MiB, max age 24h):
  * `replay.window.<user_id>.<request_id>` — Server-seitige Antwort­
    streams für progressives Laden (optional, M7+).
* Stream `system` (Persistenz: file, max 16 MiB, max age 30d):
  * `system.audit.<actor_user_id>.<action>` — gespiegelte Audit-Events.
  * `system.alert.<severity>` — Alerts aus Prometheus → Routing.

**Subscriber-Identitäten (v1.0):**

| Service                  | abonniert                                 |
|--------------------------|-------------------------------------------|
| `nats-subscriber` (Hub)  | `engine.events.*` → `replay_events`-INSERT |
| `snapshot-processor`     | `engine.snapshot.uploaded.*`              |
| `health-collector`       | `engine.heartbeat.*`                      |
| `audit-mirror`           | `system.audit.*`                          |
| `r2-pull` (Vault)        | nichts (eigener R2-Polling-Loop)          |

---

## 5. v1.0 — R2-Bucket-Layout

Bucket: `terra-incognita-mvp` (Cloudflare R2, eu-central, single region).

```
/litestream/<db_name>/wal/...
/litestream/<db_name>/snapshots/...

/snapshots/<user_id>/<snapshot_id>.tar.zst
/snapshots/<user_id>/<snapshot_id>.manifest.json

/audit/year=YYYY/month=MM/day=DD/<batch>.jsonl.gz
/health/year=YYYY/month=MM/day=DD/<batch>.jsonl.gz

/legal/tos/<version>.md
/legal/privacy/<version>.md
```

**Aufbewahrung:**

* `litestream/` — Lifecycle-Rule: 30 Tage Standard, danach `archive`.
* `snapshots/` — keine Auto-Löschung; per `retention_class`-Spalte
  gesteuert.
* `audit/`, `health/` — 365 Tage `standard`, danach `archive` 5 Jahre.

**Verschlüsselung:**

* SSE-S3 (R2-managed) plus client­seitige envelope-Verschlüsselung
  für `snapshots/*.tar.zst` mit `kms_key_id` aus SOPS-Vault.

---

## 6. v1.0 — Engine-Snapshot-Format

Snapshot ist ein **`tar.zst`** mit folgendem Inhalt:

```
manifest.json
state/lnn.npz                # NumPy-NPZ: hidden state, weights, tau
state/ebm.npz                # NumPy-NPZ: theta_history, well_states
state/kg/nodes.parquet       # KG-Knoten
state/kg/edges.parquet       # KG-Kanten
state/kg/wells.parquet       # Well-Snapshots
state/tier/active_for_tier.parquet
state/seed/preseed_version.txt
state/random/rng_state.json
checks/sha256.txt            # Datei → SHA-256 Hash
checks/format_version.txt    # 'v1.0.0'
```

**`manifest.json`** (eingefroren ab `v0.3.x`):

```json
{
  "snapshot_id": "snap_1714900000000_abc123",
  "format_version": "v1.0.0",
  "engine_id": "macbook-pro-001",
  "user_id": 42,
  "taken_at_ms": 1714900000000,
  "tick_index": 192123,
  "metrics": {
    "tier_max_seen": 3,
    "active_for_tier": {"0": 712, "1": 84, "2": 19, "3": 5},
    "ebm_wells_count": 27,
    "ebm_wells_dormant": 6,
    "kg_nodes": 1834,
    "kg_edges": 9214
  },
  "files": [
    {"path": "state/lnn.npz", "bytes": 1234567, "sha256": "..."},
    ...
  ],
  "preseed_version": "v2.5.0",
  "config_hash": "...",
  "schema": "https://schemas.terra.local/snapshot/v1.0.0.json"
}
```

---

## 7. v2.0 — Polyglot-Mapping pro Tabelle/Stream

| v1.0 Quelle                       | v2.0 Ziel                                        | Grund                          |
|-----------------------------------|---------------------------------------------------|--------------------------------|
| `users`, `refresh_tokens`, `sessions`, `engine_registrations`, `audit_log`, `settings` | PostgreSQL 16 (`auth`, `system` Schemas) | klassische Relationaldaten     |
| `encounters`, `replay_events`     | ClickHouse (Append-only) + OpenSearch (Volltext) | Time-Series + Volltext         |
| `replay_events_fts`               | OpenSearch (`replay_events`-Index)               | nativer FTS-Engine             |
| `snapshots` (Manifest)            | PostgreSQL `snapshots` + MinIO `snapshots/`       | Manifeste relational, Blobs S3 |
| `quota_usage`                     | DragonflyDB                                       | sub-ms Lese-Latenz             |
| `kv_cache`                        | DragonflyDB                                       | dito                            |
| `system_health`                   | ClickHouse (`metrics` Tabelle) + Prometheus       | Aggregations­workloads         |
| KG (Engine-intern, Snapshot)      | Neo4j 5 + GDS                                     | Graph-native Query             |
| LNN-Embeddings (Engine)           | Qdrant                                            | ANN-Suche                      |
| NATS `engine`-Subjects            | Redpanda (`engine.events.v1`)                     | persistente Event-Spine        |

> *Hinweis.* SQLite bleibt in v2.0 als „Edge-DB" auf Engine-Hardware
> einsatz­fähig, falls Offline-Betrieb gewünscht ist; sie wird **nicht**
> mehr server­seitig genutzt.

---

## 8. Migration v1 → v2 (Dual-Write)

* **Phase P0 — Vorbereitung.**
  * v2.0-Stack auf M4 deployen (lokal),
  * leere Schemas (PostgreSQL, ClickHouse, Neo4j, Qdrant, OpenSearch).
* **Phase P1 — Backfill.**
  * SQLite-Dump → CSV/Parquet → ClickHouse `INSERT … FROM file(…)`.
  * `users`, `sessions`, `audit_log` → `pg_dump → pg_restore` Schema.
  * Snapshots-Blobs werden 1:1 nach MinIO kopiert (`r2-to-minio`-Job).
* **Phase P2 — Dual-Write.**
  * Hub schreibt **gleichzeitig** in v1.0-SQLite und v2.0-Stores.
  * Engine schreibt **gleichzeitig** in NATS und Redpanda.
  * Lese-Pfade bleiben SQLite-/NATS-zentriert.
* **Phase P3 — Schatten-Reads.**
  * Lese-Pfade lesen v2.0-Stores zusätzlich; Antwort­vergleich
    instrumentiert (`metrics: replay.compare.eq`/`.neq`).
* **Phase P4 — Cutover.**
  * Lese-Pfade auf v2.0 umgestellt.
  * SQLite/NATS auf Read-Only (4 Wochen Zurück­fall-Periode).
* **Phase P5 — Abschluss.**
  * SQLite/NATS-Pfade entfernt; v2.0 ist Single-Source-of-Truth.

---

## 9. Konsistenz- & Integritäts­regeln

* **Encounter-Idempotenz.** Eine Engine darf das gleiche
  `encounter_id` höchstens einmal erfolgreich an den Hub senden;
  Retry mit identischer ID ist No-Op (`INSERT OR IGNORE`).
* **Replay-Event-Idempotenz.** `(user_id, source_engine, ts_ms,
  event_kind, hash(meta_json))` bildet ein logisches Idempotenz-Tupel;
  Duplikate werden im NATS-Subscriber verworfen.
* **Snapshot-Atomarität.** `snapshots`-Zeile wird **erst** als
  `is_active=1` markiert, wenn:
  * SHA-256 verifiziert ist,
  * R2-Upload `ETag`-bestätigt ist,
  * Manifest gegen JSON-Schema validiert wurde.
* **Refresh-Token-Familie.** Bei Reuse-Detection wird die ganze
  Familie revoked (siehe §3.2).
* **Quota-Atomar-Update.** `INSERT … ON CONFLICT DO UPDATE` auf
  `quota_usage` mit `value = value + ?` und `updated_ms = ?`.

---

## 10. Aufbewahrungs- & Lösch­regeln

| Daten                  | Standard | Maximum (Pro-Account) | Auto-Löschung |
|------------------------|----------|------------------------|---------------|
| `replay_events`        | 90 Tage  | 365 Tage              | Cron `nightly_cleanup`, ältere Events nach `audit/`-Bucket gespiegelt |
| `encounters`           | 365 Tage | 5 Jahre                | wie oben       |
| `snapshots`            | manuell  | 25 (Anzahl)            | LRU-Cleanup, jüngste 25 bleiben |
| `audit_log`            | 365 Tage | 5 Jahre                | nach R2 verschoben |
| `quota_usage`          | 30 Tage  | 90 Tage               | Truncate ältere Fenster |
| `system_health`        | 14 Tage  | 90 Tage               | Truncate         |
| `kv_cache`             | je `expires_ms` | —                | Cron `kv_expire`  |

**Account-Löschung:**

* Hard-Delete-Pfad: `users` Zeile + Cascade.
* Engine-Registrierungen werden 30 Tage gehalten, dann hart gelöscht.
* R2-Snapshots werden synchron gelöscht (Job `r2-purge`).
* `audit_log`-Zeilen werden anonymisiert (`actor_user_id = NULL`,
  `ip_h = NULL`), bleiben aber 5 Jahre als rechtliche Spur.

---

## 11. Schutzklassen, PII, DSGVO-Bezug

* **Klasse A (PII):** `users.email`, `users.display_name`,
  `audit_log.client_ip_h` (auch wenn HMAC). Speicherung verschlüsselt
  at-rest (SQLite mit SQLCipher in v2.0; in v1.0 R2-Replikation
  envelope-verschlüsselt).
* **Klasse B (Inhalt):** `encounters.payload_json`,
  `replay_events.meta_json`. Kann frei vom Nutzer gewählten Text
  enthalten — wird beim Export einbezogen.
* **Klasse C (Telemetrie):** `system_health`, `quota_usage`. Anonym,
  aber pro `user_id` zugeordnet.
* **DSGVO Auskunfts-/Lösch-Pfad:**
  * `GET /api/v1/me/export` → JSON-Export aller A/B-Daten.
  * `POST /api/v1/me/delete` → Hard-Delete (siehe §10).

---

## 12. Beispieldaten

### `encounter`-Eintrag

```json
{
  "id": "e_1714900100000_a7zk8q",
  "user_id": 42,
  "session_id": 31,
  "ts_ms": 1714900100000,
  "word": "wahrnehmung",
  "lang": "de",
  "channel": "chat",
  "payload_json": {"tags": ["philosophy"], "source": "user-input", "raw": "Wahrnehmung als Begegnung"},
  "created_at_ms": 1714900100120
}
```

### `replay_event` (Tier-Emerge)

```json
{
  "id": 1893421,
  "user_id": 42,
  "ts_ms": 1714900250000,
  "event_kind": "tier_emerge",
  "word": null,
  "meta_json": {
    "tier": 2,
    "members_count": 5,
    "promoted_member_ids": ["w_42_213","w_42_217","w_42_221","w_42_240","w_42_244"],
    "trigger_formula": "F.LNN.GROW.003",
    "text": "Tier 2 stable: 5 members"
  },
  "source_engine": "macbook-pro-001",
  "ingest_lag_ms": 87,
  "created_at_ms": 1714900250087
}
```

### `snapshot.manifest.json` (aus §6, gekürzt)

```json
{
  "snapshot_id": "snap_1714900000000_abc123",
  "format_version": "v1.0.0",
  "engine_id": "macbook-pro-001",
  "user_id": 42,
  "metrics": {"tier_max_seen": 3, "ebm_wells_count": 27}
}
```

---

*Stand: 2026-05-08 · Greenfield-Initial · autoritativ für M0–M8;
M4-Migrationsplan referenziert §7 + §8.*
