# `M1-data-foundation.md` — Phase M1: Datenfundament

> **Lebendiges Dokument.** Ergebnis: Persistenz-Schicht (SQLite + WAL +
> FTS5) ist aufgebaut, Migrationen kontrolliert, Repository-Layer
> typisiert und getestet, Backup nach Cloudflare R2 läuft, Vault zieht
> Mirror.
>
> **Phase-Tag bei Abschluss:** `v0.2.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M1.1 – M1.11](#4-schritte-m11--m111)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

- **SQLite (WAL + FTS5)** ist Single-Writer-Persistenz auf dem Hub. Schema
  ist von Beginn an stabil genug, dass spätere Phasen nur **additiv**
  migrieren.
- **Repository-Layer** isoliert SQL vom restlichen Backend. Tests laufen
  gegen In-Memory-DB; produktive Pfade gegen das WAL-File.
- **Migrationen** sind monoton vorwärts, wiederholbar und idempotent.
- **Litestream** streamt WAL-Frames kontinuierlich nach R2.
- **Vault** zieht regelmäßig aus R2 und hält eine Read-Mirror-SQLite.
- **Disaster-Recovery-Drill** ist dokumentiert und getestet — neue Hub-
  VM ist in < 5 min produktiv.

**Was M1 nicht tut:**

- Keine HTTP-Routen — die kommen in M5.
- Keine Authentifizierungs-Logik — Schema sieht User vor, aber
  `pwhash_argon2` wird in M5.4 befüllt.
- Keine Replay-Suchlogik — die kommt in M5.8 mit Hybrid-Planner-Port.
- Keine Engine-Anbindung — die kommt in M2.

---

## 2. Vorbedingungen

- M0 abgeschlossen, `v0.1.0` getaggt.
- Compose-Stack `hub.yml --profile minimal` lokal lauffähig.
- SOPS-Secrets aus M0.8 enthalten Platzhalter für `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET`.
- Cloudflare-R2-Bucket ist in der CF-Account-Konsole angelegt
  (Bucket-Name siehe M1.9).

---

## 3. Architektur-Bezug

- `architecture/mvp.md` §6 — Datenmodell, Schema-Auszug
- `architecture/mvp.md` §13 — Speicher-Budget (SQLite-Anteil)
- `Anweisungen.md` §2 — Coding-Standards
- `Anweisungen.md` §4 — Test-Regeln
- `docs/contracts/replay_timeline_window_v4.schema.json` — bestehender
  Replay-Vertrag, dessen SQLite-Tabellen wir hier modellieren

---

## 4. Schritte M1.1 – M1.11

---

### M1.1 — sqlite-baseline-schema

**Branch:** `feature/sqlite-baseline-schema`
**Issue:** `#NNN`
**Vorbedingungen:** M0 grün
**Berührte Pfade:**

```
app/backend/ti_hub/db/schema/
├── 0001_baseline.sql                    ← reines DDL für initiales Schema
├── README.md                            ← Versionierungs-Erklärung
app/backend/ti_hub/db/connection.py      ← Connection-Manager (Async)
app/backend/ti_hub/db/__init__.py
tests/db/test_baseline_schema.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `0001_baseline.sql` definiert Tabellen aus `architecture/mvp.md` §6
   (mindestens `users`, `sessions`, `engine_connections`, `encounters`,
   `replay_events`, `snapshots`, plus `meta`-Tabelle für Schema-Version).
2. **Pragmas** in `connection.py` werden bei jedem Open angewandt:
   - `journal_mode=WAL`
   - `synchronous=NORMAL` (Standard für WAL; durability genügt für unseren
     Workload, Speed-Tradeoff dokumentiert)
   - `foreign_keys=ON`
   - `busy_timeout=5000`
   - `cache_size=-8192` (≈ 8 MB)
   - `temp_store=MEMORY`
3. Connection-Manager ist `async`, basiert auf `aiosqlite`. Single-Writer
   wird durch eine `asyncio.Lock` im Manager erzwungen. Lese-Connections
   parallel.
4. `meta`-Tabelle hat Pflichtfelder: `schema_version INTEGER NOT NULL`,
   `app_version TEXT NOT NULL`, `installed_at INTEGER NOT NULL`.
5. Test verifiziert:
   - Initialer Schema-Load gegen `:memory:` funktioniert.
   - Pragmas sind nach `connection.open()` gesetzt.
   - Schema-Version ist `1`.

**Tests:**

- `tests/db/test_baseline_schema.py::test_schema_creates_all_tables`
- `tests/db/test_baseline_schema.py::test_pragmas_applied`
- `tests/db/test_baseline_schema.py::test_meta_schema_version_set`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün; Schema-Lint im CI bestätigt 1:1-Match
zwischen DDL und Pydantic-Modell-Erwartungen (Pydantic-Modelle existieren
ab M1.4 — der Schema-Linter wird in M5.14 Pflicht).

---

### M1.2 — sqlite-fts5-replay-events

**Branch:** `feature/sqlite-fts5-replay-events`
**Issue:** `#NNN`
**Vorbedingungen:** M1.1 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/schema/0002_replay_fts.sql
app/backend/ti_hub/db/replay_fts.py       ← Indexer / Rebuild-Triggers
tests/db/test_replay_fts.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `0002_replay_fts.sql` legt eine **contentless** FTS5-Virtuelle-Tabelle
   `replay_events_fts` an mit Spalten `payload_text`, `kind`,
   Tokenizer `unicode61 remove_diacritics 2`.
2. `app/backend/ti_hub/db/replay_fts.py` implementiert:
   - `index_event(event)` — fügt eine Row in die FTS-Tabelle ein.
   - `reindex_user(user_id, since=None)` — rebuildet partiell.
   - `rebuild_full()` — leert + füllt komplett (Vorsicht-Pfad).
3. **Debounce-Hook**: Append-Trigger erhöht Counter; Rebuild läuft erst
   nach `replay_fts_rebuild_debounce_s` (Default 30 s, übernommen aus
   `terra-075`). Setting in `settings.py`.
4. Diagnostic-Counter (übernommen aus `terra-078`/`terra-082`):
   - `rebuild_success_total`
   - `rebuild_failure_total`
   - `append_rebuild_skipped_debounce_total`
   - `last_rebuild_ok_unix`
5. Tests: append → search hits, Debounce-Window respektiert, Rebuild
   recovered nach simuliertem FTS-Index-Fehler.

**Tests:**

- `tests/db/test_replay_fts.py::test_index_and_search_basic`
- `tests/db/test_replay_fts.py::test_debounce_window_respected`
- `tests/db/test_replay_fts.py::test_rebuild_recovers_from_corruption`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~450 Lines diff
**Fertig wenn:** AC + CI grün; Bestand `terra-075/078`-Patterns bestätigt
übernommen.

---

### M1.3 — alembic-migrations-bootstrap

**Branch:** `feature/alembic-migrations-bootstrap`
**Issue:** `#NNN`
**Vorbedingungen:** M1.1 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/alembic.ini
app/backend/ti_hub/db/alembic/
├── env.py                                ← sync SQLite engine (normalized URL from env)
├── script.py.mako
└── versions/
    ├── 0001_baseline.py
    └── 0002_replay_fts.py
docs/operations/migrations.md
tests/db/test_alembic_migrations.py
Makefile
.github/workflows/ci.yml
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. Alembic ist konfiguriert für **`TI_HUB_ALEMBIC_URL`** (üblicherweise
   `sqlite+aiosqlite:///…`); **`env.py`** normalisiert intern zu
   **`sqlite:///…`** (synchron), damit das bestehende canonical DDL per
   **`sqlite3.Connection.executescript`** aus den Dateien **`schema/000*.sql`** geladen werden kann.
2. Migrations 0001 und 0002 entsprechen 1:1 den DDLs aus M1.1 / M1.2 —
   das DDL-File ist die Quelle, die Migration ist Ableitung.
3. `make migrate` führt `alembic upgrade head` aus.
4. **No-Down-Policy**: Migrationen haben `downgrade()` als no-op mit
   Kommentar, **nur** für Test-Kontexte. Produktiv wird kein Downgrade
   ausgeführt.
5. CI-Schritt `migration-roundtrip-test`:
   - Frische Datei-SQLite unter `tmpdir` → `upgrade head` → `sqlite_master`-Vergleich gegen dasselbe `0001`+`0002`-`executescript` = keine Abweichung (Alembic-Systemtabelle ausgenommen).
6. `docs/operations/migrations.md` dokumentiert:
   - „Wie eine neue Migration angelegt wird"
   - „Wie ein Notfall-Rollback aussieht (Restore aus R2)"
   - „Was niemals passiert (Down-Migration in Production)"

**Tests:**

- `tests/db/test_alembic_migrations.py::test_upgrade_head_idempotent`
- `tests/db/test_alembic_migrations.py::test_migration_roundtrip_no_diff`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~300 Lines diff
**Fertig wenn:** AC + CI grün; Migration auf Hub-Compose-Stack durch
`make migrate` läuft sauber.

---

### M1.4 — repository-layer-users

**Branch:** `feature/repo-users`
**Issue:** `#NNN`
**Vorbedingungen:** M1.3 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/repos/
├── __init__.py
├── base.py                              ← `BaseRepository` mit Tenant-Helpers
└── users.py
app/backend/models/                      ← Pydantic v2 Modelle
├── __init__.py
└── user.py
tests/db/repos/test_users_repo.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `User` Pydantic-Modell hat: `id`, `email`, `created_at`, `status`,
   `is_admin`. `pwhash_argon2` ist **nicht** im Public-Modell, sondern
   in einer separaten `UserCredentials`-Klasse, die nur das
   Repository sieht.
2. Methoden auf `UsersRepository`:
   - `get_by_id(user_id) -> User | None`
   - `get_by_email(email) -> User | None`
   - `create(email, pwhash) -> User`
   - `update_status(user_id, status)`
   - `set_admin(user_id, is_admin)`
   - `count_active() -> int`
3. **Tenant-Sicherheit**: `BaseRepository` stellt sicher, dass jeder
   Aufruf, der `user_id` betrifft, explizit übergibt. Keine implizite
   „aktueller User"-Logik im Repo.
4. Tests:
   - Happy-Path: create → get_by_email → status update.
   - Negative: doppelte E-Mail → spezifische Exception
     `EmailAlreadyRegistered`.
   - Schema-Constraints: `status NOT IN ('active','disabled')` →
     `IntegrityError` aus SQLite, gemappt auf `RepositoryError`.
5. Coverage des Moduls ≥ 95 %.

**Tests:**

- `tests/db/repos/test_users_repo.py::test_create_and_fetch_by_email`
- `tests/db/repos/test_users_repo.py::test_duplicate_email_raises`
- `tests/db/repos/test_users_repo.py::test_status_update`
- `tests/db/repos/test_users_repo.py::test_admin_flag`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M1.5 — repository-layer-encounters

**Branch:** `feature/repo-encounters`
**Issue:** `#NNN`
**Vorbedingungen:** M1.4 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/repos/encounters.py
app/backend/models/encounter.py
tests/db/repos/test_encounters_repo.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. Methoden auf `EncountersRepository`:
   - `append(user_id, encounter) -> Encounter`
   - `list_for_user(user_id, since=None, limit=100) -> list[Encounter]`
   - `count_for_user_within(user_id, window_seconds) -> int` (für
     Rate-Limit-Check)
2. `Encounter` Pydantic-Modell hat: `id`, `user_id`, `ts`, `word`,
   `scale`, `source`, `context: dict`. `context` wird als JSON
   serialisiert in `context_json`.
3. **Source-Whitelist**: `source ∈ {'user_input', 'ghost', 'walk',
'kg_spontaneous', 'replay'}` — Constraint sowohl SQL als auch
   Pydantic-Validator.
4. Index `idx_encounters_user_ts` ist von M1.1 da; Tests prüfen, dass
   `list_for_user` mit `since` einen Index-Scan auslöst (`EXPLAIN
QUERY PLAN` enthält `USING INDEX`).
5. **Negative-Tests:**
   - Append für Cross-Tenant-`user_id` schlägt fehl, wenn der User
     nicht existiert (`FK fail`).

**Tests:**

- `tests/db/repos/test_encounters_repo.py::test_append_and_list`
- `tests/db/repos/test_encounters_repo.py::test_source_whitelist`
- `tests/db/repos/test_encounters_repo.py::test_index_used`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M1.6 — repository-layer-replay-events

**Branch:** `feature/repo-replay-events`
**Issue:** `#NNN`
**Vorbedingungen:** M1.5 gemerged, M1.2 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/repos/replay_events.py
app/backend/models/replay_event.py
app/backend/ti_hub/db/replay_query.py    ← Hybrid-Planner-Port (terra-076/079/080)
tests/db/repos/test_replay_events_repo.py
tests/db/test_replay_query.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `ReplayEventsRepository`:
   - `append(user_id, event) -> ReplayEvent`
   - `query_window(user_id, window_request) -> ReplayWindowResponse`
   - `count_by_kind(user_id) -> dict[str, int]`
2. `query_window` portiert das **bestehende** Hybrid-Planner-Verhalten
   aus `app/backend/ti_hub/db/events.py` (Versionen `replay_timeline_window_v3`/`v4`),
   inkl. der drei Policies `bm25_only`, `substring_only`, `combined`
   und der Score-Formel `α·bm25/(bm25+1) + β·hits/3` (terra-080).
3. Score-Weights validiert wie in `terra-080`:
   - α/β ∈ [0,1]
   - `combined` mit beiden 0 → 422-Equivalent (Repository wirft
     `InvalidQueryError`)
4. Tie-Break ist `id ASC`, `NULL → 0` (terra-080 RAM-Parität).
5. Filter-Echo: Repository gibt `effective_policy` und `score_weights`
   zurück, damit M5.8 sie 1:1 ans HTTP-Echo durchreichen kann.

**Tests:**

- `tests/db/repos/test_replay_events_repo.py::test_append_writes_to_fts`
- `tests/db/test_replay_query.py::test_chronological_order`
- `tests/db/test_replay_query.py::test_hybrid_bm25_only`
- `tests/db/test_replay_query.py::test_hybrid_substring_only`
- `tests/db/test_replay_query.py::test_hybrid_combined_score`
- `tests/db/test_replay_query.py::test_tie_break_id_asc`
- `tests/db/test_replay_query.py::test_invalid_combined_zero_zero`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff (Hybrid-Planner ist substanziell)
**Fertig wenn:** AC + CI grün; ein bestehendes JSON-Snapshot-Test
(Existiert in `tests/api/test_replay_hybrid_planner.py`-Stil) lässt
sich gegen die neue Repository-Implementierung wiederverwenden.

---

### M1.7 — repository-layer-snapshots-manifest

**Branch:** `feature/repo-snapshots-manifest`
**Issue:** `#NNN`
**Vorbedingungen:** M1.5 gemerged
**Berührte Pfade:**

```
app/backend/ti_hub/db/repos/snapshots.py
app/backend/models/snapshot.py
tests/db/repos/test_snapshots_repo.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `SnapshotsRepository`:
   - `initiate(user_id, scope, expected_size_bytes, content_sha256) -> Snapshot` (Status `uploading`)
   - `complete(snapshot_id, r2_key) -> Snapshot` (Status `ready`)
   - `expire_older_than(threshold_ts) -> list[int]` (gibt Liste der
     aufgegebenen IDs zurück; eigentliches R2-Pruning liegt in M1.10)
   - `list_for_user(user_id, limit=50) -> list[Snapshot]`
2. `content_sha256` ist UNIQUE (DB-Constraint); doppelte Initiate mit
   gleichem Hash → Idempotent: gibt vorhandenen Snapshot zurück, kein
   Fehler.
3. Größenlimit pro Snapshot: 64 MB (siehe `architecture/mvp.md` §9 Eingabe-
   Validierung). Repo wirft `SnapshotTooLargeError`, wenn
   `expected_size_bytes > limit`.
4. **State-Machine** der Snapshots: `uploading → ready` oder
   `uploading → expired`. `ready → expired` ist möglich; alle anderen
   Übergänge → `IllegalSnapshotState`.

**Tests:**

- `tests/db/repos/test_snapshots_repo.py::test_initiate_and_complete`
- `tests/db/repos/test_snapshots_repo.py::test_idempotent_on_same_hash`
- `tests/db/repos/test_snapshots_repo.py::test_size_limit_enforced`
- `tests/db/repos/test_snapshots_repo.py::test_state_machine_transitions`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M1.8 — litestream-config-hub

**Branch:** `feature/litestream-config-hub`
**Issue:** `#NNN`
**Vorbedingungen:** M1.3 gemerged
**Berührte Pfade:**

```
deploy/litestream/config.yml
deploy/compose/hub.yml                    ← Service `litestream` aktiv
docs/operations/litestream.md
tests/integration/test_litestream_smoke.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `litestream/config.yml` streamt `/var/lib/terra/db/terra.sqlite` nach
   `s3://<R2_BUCKET>/litestream/<env>/terra.sqlite/`.
2. **Replication-Settings**:
   - `min-checkpoint-page-count: 1024`
   - `validation-interval: 12h`
   - `retention: 720h` (30 Tage)
3. Service-Definition in `hub.yml` mit korrekten Mounts und Restart-Policy.
4. Smoke-Test (lokal mit MinIO statt R2):
   - Schreibe Test-Row in DB.
   - Litestream-Snapshot ausgeführt.
   - `litestream restore` erstellt eine Kopie.
   - Test-Row ist in der Kopie vorhanden.
5. `docs/operations/litestream.md` dokumentiert:
   - Erstmalige Bucket-Befüllung (`litestream replicate -no-snapshot=false`)
   - Restore-Kommando: `litestream restore -o /tmp/restored.db s3://...`
   - Was zu tun ist, wenn `validation-interval` einen Drift meldet.

**Tests:**

- `tests/integration/test_litestream_smoke.py::test_replicate_and_restore`
- `tests/integration/test_litestream_smoke.py::test_retention_policy_set`

**Ressourcen-Budget:** ~20 MB RAM für Litestream-Service.
**Geschätzte PR-Größe:** ~280 Lines diff
**Fertig wenn:** AC + CI grün; auf Hub-VM mit echten R2-Credentials
manuell verifiziert.

---

### M1.9 — r2-bucket-naming-and-iam

**Branch:** `chore/r2-bucket-naming-and-iam`
**Issue:** `#NNN`
**Vorbedingungen:** M0.8 gemerged (SOPS für Secrets)
**Berührte Pfade:**

```
docs/operations/r2-buckets.md
secrets/hub.sops.yaml                     ← R2-Credentials-Schema bestätigen
secrets/vault.sops.yaml                   ← analog für Vault (read-mostly)
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. **Bucket-Namen** (final, eingefroren):
   - `terra-incognita-prod` — Production
   - `terra-incognita-dev` — Lokale Dev und CI-Smoke
2. **Object-Key-Layout**:
   ```
   litestream/<env>/<dbname>/...                       (Litestream-State)
   snapshots/<user_id>/<ts>-<sha256>.tar.zst            (Engine-Snapshots)
   replay-bundles/<user_id>/<bundle_id>.tar.zst         (optional, M7)
   audit-logs/<yyyy>/<mm>/<dd>.jsonl.zst                (Audit-Logs, später)
   ```
3. **R2-API-Token**:
   - `terra-hub-rw` — RW auf alle Prefixes
   - `terra-vault-r` — RO auf `litestream/`, `snapshots/manifest/` (siehe Vault-Bedarf)
   - `terra-ci-rw` — RW auf `terra-incognita-dev` only
4. `docs/operations/r2-buckets.md` dokumentiert:
   - Erstellung der Tokens via Cloudflare Dashboard
   - Wo sie gespeichert sind (SOPS)
   - Lebensdauer / Rotation (alle 180 Tage)
   - Kosten-Implikationen (R2-Free-Tier-Limits)
5. **Lifecycle-Policy** auf `snapshots/`:
   - Versionen älter als 30 Tage: gelöscht (sofern nicht latest-full)
   - Lifecycle wird via R2-Web-UI oder API angelegt; in der Doku ist die
     gewählte Variante festgehalten.

**Tests:** kein Pytest (Konfigurationsschritt). Stattdessen:

- `tests/test_docs_links.py::test_r2_buckets_doc_present`
- Manueller Smoke: `aws s3 ls s3://terra-incognita-dev/ --endpoint-url …`
  (mit `terra-ci-rw` Token).

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~200 Lines diff
**Fertig wenn:** AC + CI grün; manueller R2-Smoke ok.

---

### M1.10 — vault-r2-pull-worker

**Branch:** `feature/vault-r2-pull-worker`
**Issue:** `#NNN`
**Vorbedingungen:** M0.4 gemerged, M1.8 gemerged, M1.9 gemerged
**Berührte Pfade:**

```
deploy/workers/r2-pull/
├── Dockerfile
├── pull.py
└── README.md
deploy/compose/vault.yml                  ← Service aktivieren
tests/integration/test_r2_pull.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `pull.py` ist ein Python-Script (kein Daemon-Framework nötig):
   - Schleife mit `asyncio.sleep(30)` zwischen Iterationen.
   - Pro Iteration: `litestream restore -if-replica-exists … /var/lib/vault/db/terra.sqlite`.
   - Läuft als nicht-root-User.
   - Loggt JSON-Lines mit `level`, `lag_seconds`, `bytes_pulled`,
     `restore_duration_ms`.
2. **Lag-Metrik** wird auf einem Prom-Endpunkt im Worker ausgesetzt
   (`8081/metrics`), Vault-Prom scrapt es.
3. Wenn `restore` fehlschlägt: Backoff bis 5 min, Alarm-Log.
4. Vault-`caddy` exposed `/vault/status` mit folgendem JSON:
   ```json
   { "ok": true, "last_pull_ts": ..., "lag_s": 12,
     "db_size_bytes": ..., "version": "..." }
   ```
5. CI-Smoke gegen MinIO statt R2 verifiziert End-to-End-Flow.

**Tests:**

- `tests/integration/test_r2_pull.py::test_pulls_initial_replica`
- `tests/integration/test_r2_pull.py::test_subsequent_changes_propagate`
- `tests/integration/test_r2_pull.py::test_metrics_exposed`

**Ressourcen-Budget:** ~60 MB RAM (typisch), ~90 MB Spitze.
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün; Vault zieht in echtem Setup automatisch.

---

### M1.11 — restore-drill-script

**Branch:** `feature/restore-drill-script`
**Issue:** `#NNN`
**Vorbedingungen:** M1.10 gemerged
**Berührte Pfade:**

```
scripts/operations/restore_hub.sh
docs/operations/restore-drill.md
tests/integration/test_restore_script.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**

1. `restore_hub.sh` führt aus (idempotent):
   - Voraussetzungen prüfen (`litestream`, `cloudflared`, Docker).
   - `litestream restore` aus R2.
   - `alembic upgrade head` (sollte no-op sein, wenn DB aktuell).
   - Compose-Services starten.
   - Health-Smoke gegen `https://<hub>/v1/health`.
   - Exit-Code 0 nur, wenn alle Schritte erfolgreich.
2. **Drill-Doc** beschreibt das Szenario „Hub-VM neu provisioniert":
   - VM erstellen, Cloudflared-Tunnel-Credential einbringen, Repo
     clonen, SOPS-Key einbringen, `make secrets-decrypt`,
     `restore_hub.sh` laufen lassen → fertig.
   - Erwartete Dauer: < 5 min ohne SOPS-Key-Setup, < 15 min mit.
3. **Realistischer Drill** wird einmal vor `v1.0`-Release tatsächlich
   ausgeführt (M8) und das Resultat dokumentiert.
4. `tests/integration/test_restore_script.py` testet:
   - Script in einem Docker-in-Docker-Setup (CI-fähig).
   - Restore aus einem MinIO-Replikat.
   - Health-Endpoint antwortet nach Lauf.

**Tests:**

- `tests/integration/test_restore_script.py::test_full_restore_flow`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~280 Lines diff
**Fertig wenn:** AC + CI grün; Drill-Doc reviewed.

---

## 5. Phasen-Gate

M1 gilt als grün abgeschlossen, wenn:

1. M1.1 – M1.11 in `00-index.md` auf `[x]`.
2. Hub-Compose mit Profil `default` läuft 60 Minuten ohne RSS-Drift > 5 %.
3. Litestream-Lag im Grafana-Dashboard `Hub Persistence` < 5 s p95.
4. Vault zieht erfolgreich; `vault.r2-pull-Lag` < 60 s.
5. CI-Job `migration-roundtrip-test` und `compose-smoke` grün.
6. Tag `v0.2.0` gepusht.

---

## 6. Erledigte Änderungen

- **M1.1** `feature/sqlite-baseline-schema` → PR #5 — 2026-05-09
- **M1.2** `feature/sqlite-fts5-replay-events` → PR #16 — 2026-05-09
- **M1.3** `feature/alembic-migrations-bootstrap` → PR #17 — 2026-05-09
- **M1.4** `feature/repo-users` → PR #20 — 2026-05-09
- **M1.5** `feature/repo-encounters` → PR #21 — 2026-05-09
- **M1.6** `feature/repo-replay-events` → PR #22 — 2026-05-10
- **M1.7** `feature/repo-snapshots-manifest` → PR #23 — 2026-05-10

---

_Stand: 2026-05-10 · M1.1–M1.7 erledigt · nächster Schritt M1.8 (`feature/litestream-config-hub`)_
