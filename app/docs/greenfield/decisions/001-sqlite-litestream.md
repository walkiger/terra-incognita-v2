# ADR-001 — SQLite + Litestream als v1.0-Persistenz

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** ADR-000, `architecture/mvp.md`,
  `implementation/mvp/M1-data-foundation.md`

## Context

Der Hub muss in v1.0 mit ≤ 220 MiB Resident-Memory auskommen
(`runbooks/oom-and-capacity.md` §1). Klassische Server-DBMS
(Postgres, MySQL) verbrauchen idle bereits 80–150 MiB nur für
Hintergrund-Prozesse, ohne dass Daten persistiert sind. Damit
würden sie das Memory-Budget des Hubs sprengen, bevor der erste
Request bedient ist.

Gleichzeitig braucht v1.0 echte Persistenz, Volltextsuche, FK-
Constraints und einen klaren Migrationspfad nach v2.0 (Postgres +
ClickHouse + OpenSearch).

## Decision

Wir setzen **SQLite 3.45+** mit:

* `journal_mode = WAL` (Concurrent-Reader, Single-Writer),
* `synchronous = NORMAL`,
* `mmap_size = 64 MiB`,
* `cache_size = -32000` (≈ 32 MiB),
* FTS5-Virtual-Table für Replay-Volltext (`replay_events_fts`).

**Litestream 0.3+** streamt das WAL kontinuierlich nach Cloudflare
R2 (`s3://terra-incognita-mvp/litestream/...`). Vault-VM zieht
periodisch (Polling alle 60 s) den Mirror und stellt ihn als
Read-Replica zur Verfügung.

Migrationsweg nach v2.0 (siehe ADR-008,
`implementation/production.md` §5): Daten werden Phase-weise in
Postgres + ClickHouse + OpenSearch dual-geschrieben, dann SQLite
read-only gestellt, am Ende abgeschaltet.

## Consequences

* **Positiv:**
  * RSS-Footprint von SQLite + Litestream zusammen < 50 MiB.
  * RPO ≤ 60 s durch kontinuierliches WAL-Streaming.
  * Volltextsuche ohne externe Abhängigkeit (FTS5).
  * Backup ist trivial: `litestream restore -o /var/lib/terra/hub.db
    s3://...`.
* **Negativ:**
  * Single-Writer-Limit verhindert echte horizontale Skalierung
    bereits ab ~200 Schreib-Ops/s. Für v1.0 weit unter dem Bedarf
    (max ~50 Encounter-Inserts/s über alle User).
  * FTS5 ist deutlich limitierter als OpenSearch (kein Synonym,
    kein Stemming für viele Sprachen). v1.0 deckt nur DE+EN ab.
* **Neutral:**
  * Migrationspfad nach Postgres ist gut beschrieben und in
    `implementation/production.md` §5 fixiert.

## Alternatives Considered

* **Postgres direkt auf VM-A**: Memory-Budget-Verletzung
  (s.o.). In v1.0 verworfen.
* **Postgres auf separater Cloud-DB (Aurora/Supabase Free Tier)**:
  Free-Limits zu eng, keine Litestream-äquivalente Replikation
  ohne Zusatzkosten.
* **DuckDB**: gut für Analytik, aber kein WAL-Streamer-Pendant
  und keine Mehrnutzer-Concurrent-Writes.
* **Cloudflare D1**: Free-Tier-Limits attraktiv, aber kein
  WS-/Realtime-Hub-Pfad (D1 ist Cloudflare-Worker-only).

## References

* SQLite-Doku zu WAL: <https://www.sqlite.org/wal.html>
* Litestream-Doku: <https://litestream.io>
* ADR-000, ADR-008
* `architecture/data-model.md` §3

---

*Greenfield-Initial-ADR.*
