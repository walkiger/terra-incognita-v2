# `implementation/production.md` — Vollausbau-Implementierung (v2.0)

> **Lebendiges Dokument.** Was wann passiert, wenn der Übergang von
> v1.x auf v2.0 ansteht. **Ohne** vorab-fixierte Git-Branches —
> diese werden zum Zeitpunkt der Migration im selben Stil wie
> `implementation/mvp/00-index.md` ausgearbeitet.
>
> **Zweck:** Erinnerung daran, **was wir wissen wollen**, bevor wir
> auf M4-Hardware umziehen. Je näher der Trigger rückt, desto
> detaillierter wird diese Datei. Heute ist sie ein **Reisepass**,
> nicht eine Reisekarte.

---

## Inhalt

1. [Trigger & Vorlauf](#1-trigger--vorlauf)
2. [Phasen P0–P5 (grobgranular)](#2-phasen-p0p5-grobgranular)
3. [Was passiert, wenn die M4-Hardware ankommt](#3-was-passiert-wenn-die-m4-hardware-ankommt)
4. [Kompatibilitäts-Garantien zwischen v1.x und v2.0](#4-kompatibilitäts-garantien-zwischen-v1x-und-v20)
5. [Datenmigrations-Plan (parallele Schreibphase)](#5-datenmigrations-plan-parallele-schreibphase)
6. [Compute-Migration (Engine in den Server)](#6-compute-migration-engine-in-den-server)
7. [Beobachtbarkeit-Erweiterung](#7-beobachtbarkeit-erweiterung)
8. [Sicherheits-Erweiterung](#8-sicherheits-erweiterung)
9. [Open Tooling & Was nicht jetzt entschieden wird](#9-open-tooling--was-nicht-jetzt-entschieden-wird)

---

## 1. Trigger & Vorlauf

**Trigger:** ein dedizierter Server mit ≥ 96 GB RAM und ausreichendem
Compute (in der Vorzugsvariante: M4-Mac Studio/Pro).

**Vorlauf** — drei Bedingungen, die vor v2.0 in Ruhe vorbereitet werden
sollen, idealerweise schon in v1.x:

1. **`F.*`-Registry ist mature genug.** Mindestens die `F.LNN.*`,
   `F.EBM.*`, `F.KG.*`-Sektionen sind verifiziert. Ohne stabile
   Formel-Sprache ist v2.0 zu fragil.
2. **Polyglot-Stack ist mit Test-Daten lokal validiert.** Auf einer
   Dev-Maschine mit ausreichend RAM kann eine Mini-Polyglot-Compose
   (Neo4j + Qdrant + ClickHouse + Postgres + OpenSearch + Redpanda +
   Dragonfly) lauffähig vorgeführt werden.
3. **Dual-Write-Pattern ist im Code skizziert.** Zumindest ein
   `dual_writer`-Hook im Repository-Layer ist vorhanden, kann
   konfiguriert eingeschaltet werden. Echter Dual-Write läuft erst in
   P1.

---

## 2. Phasen P0–P5 (grobgranular)

| Phase | Inhalt                                                                       | Erwartete Dauer (kalendarisch) |
|-------|-------------------------------------------------------------------------------|--------------------------------|
| P0    | Hardware bereit, Polyglot-Stack lokal voll grün, Migrations-Skripte getestet  | 2–4 Wochen                      |
| P1    | Dual-Write-Phase: alle Schreibwege gehen in Alt + Neu                         | 7 Tage                          |
| P2    | Read-Cutover: Lese-Pfade switchen auf Polyglot. Schatten-Schreiben in Alt    | 7 Tage                          |
| P3    | SQLite stilllegen (read-only); finaler Vollabzug nach R2                     | 1–2 Tage                         |
| P4    | Engine-Migration: Server-Engine wird Default; Local Engine bleibt unterstützt | 30 Tage Übergang                |
| P5    | Beobachtbarkeit-Erweiterung (Tempo + Loki + OTel) + Hardening                | 7 Tage                          |
| —     | **Tag `v2.0.0`**                                                              | nach P5                         |

Diese Phasen werden zur jeweiligen Eröffnungszeit in einem eigenen
`implementation/production/00-index.md` mit Branch-Mapping ausgearbeitet
(strukturanalog zum MVP-`00-index.md`).

---

## 3. Was passiert, wenn die M4-Hardware ankommt

In der unten genannten Reihenfolge — **erst danach wird Code geändert**:

1. **Inventur:** Welche v1.x-PRs / -Issues sind noch offen? Welche sind
   für v2.0 reservierten Bezeichnungen wie „polyglot" gelabelt?
2. **DEC-Eintrag** in `memory/system/decisions.md`: Datum, Hardware-
   Spezifikation, Pfad (`v2.0` startet mit Phase P0).
3. **Repo-Branch `feature/v2-bootstrap`** wird angelegt — alle v2.0-
   Vorbereitungen erfolgen darauf, **`main` bleibt v1.x bis Cutover**.
4. **`implementation/production/00-index.md`** wird angelegt; analog zum
   MVP-Index, aber mit P-Phasen.
5. Polyglot-Stack-Compose wird auf M4 hochgezogen.
6. Test-Daten werden eingespielt.
7. Dual-Write-Hook wird aktiviert.

Erst nach Schritt 7 beginnt die echte P1-Arbeit.

---

## 4. Kompatibilitäts-Garantien zwischen v1.x und v2.0

Folgende Verträge bleiben **rückwärts-kompatibel** über den Cutover:

| Vertrag                                       | Garantie                                                       |
|-----------------------------------------------|----------------------------------------------------------------|
| `/v1/*` HTTP-Pfade                            | bleiben funktional; v2.0 ergänzt `/v2/*` parallel               |
| `/ws/v1/viewer`                               | bleibt funktional; `/ws/v2/viewer` ist Erweiterung              |
| `/ws/v1/engine`                               | bleibt funktional; `/ws/v2/engine` ist Erweiterung              |
| `replay_timeline_window_v4`                   | bleibt; `_v5` für ClickHouse-Aggregates ist Ergänzung           |
| Snapshot-Bundle-Format                        | bleibt; Engine-`schema_v` bleibt akzeptiert                     |
| JWT-Claims                                    | bleiben; `scope: server-engine` als neuer Wert in v2.0          |
| `F.*`-IDs und ihre semantische Definition     | bleiben; Implementierungspfade dürfen wechseln                  |

**Was bricht:** nichts, was in v1.0 als „eingefroren" markiert ist.

---

## 5. Datenmigrations-Plan (parallele Schreibphase)

### Source of Truth pro Datenklasse

| Datenklasse                        | v1.x SoT     | v2.0 SoT       | Migrations-Pfad                                            |
|------------------------------------|--------------|----------------|-------------------------------------------------------------|
| Users / Auth                        | SQLite      | Postgres       | Direkter Dump + `pg_restore`-äquivalente Skripte             |
| Sessions / Refresh                  | SQLite      | Postgres       | optional Re-Login (zur Token-Rotation)                       |
| Encounters                          | SQLite      | Postgres + ClickHouse | Stream-Replay aus NATS-Backup + Postgres-Spiegel        |
| Replay-Events                       | SQLite      | ClickHouse     | dito                                                          |
| KG-Knoten/Kanten                    | Engine-lokal | Neo4j          | Re-Materialisierung aus Snapshot + Preseed                  |
| Embeddings                          | Engine-lokal | Qdrant         | dito                                                          |
| Volltext                            | SQLite FTS5 | OpenSearch     | Re-Index aus Postgres                                        |
| Snapshots                            | R2          | MinIO + R2     | MinIO sync via `mc mirror`                                  |
| Audit-Log                            | SQLite      | Postgres       | direkter Dump                                                 |

### Dual-Write-Schritte (P1)

* **Pro Schreibpfad** wird `dual_writer.write_to_old(...)` und
  `dual_writer.write_to_new(...)` aufgerufen.
* `dual_writer` puffert bei Fehler in der Neu-Schiene; gibt nur Erfolg,
  wenn die Alt-Schiene erfolgreich war (Alt = SoT in P1).
* Diff-Reconciler läuft alle 5 min: zählt Rows, vergleicht Hashes pro
  User. Telemetrie schreibt `dual_write_drift{table,direction}` in
  Prometheus.
* P1 ist erst beendet, wenn Drift 24 h = 0.

### Read-Cutover (P2)

* Lese-Pfade schalten auf Polyglot um.
* Schreiben bleibt dual.
* P2 ist beendet, wenn 7 Tage stabile p95-Latenzen + null Drift.

### Stilllegung (P3)

* Schreiben in Alt wird beendet.
* Litestream-Backup angehalten, finaler Vollabzug nach R2 für Audit.
* SQLite ist read-only; bleibt 90 Tage als Recovery-Pfad bestehen.

---

## 6. Compute-Migration (Engine in den Server)

* In v1.x-Endphase wird der Engine-Prozess so verkapselt, dass er
  **identisch** lokal und serverseitig laufen kann (Container-Image
  `terra-engine:1.x.y`).
* In v2.0 startet der Hub auf Wunsch des Users einen dedizierten
  Engine-Prozess in einer eigenen Sandbox (cgroup-Limit, CUDA/MPS-
  Allokation).
* Local-Engine-Pfad bleibt unterstützt; ein User kann zwischen
  Server- und Local-Compute wechseln. Der WS-Channel ist identisch.
* **Engine-Lifecycle**:
  * `POST /v1/engine/spawn` (admin-only in v1.x → user-initiated in v2.0)
  * `DELETE /v1/engine/{id}` (sanftes Stop)
  * Auto-suspend nach 10 min Idle.
* **Persistenz der Engine-State** wird über Snapshots (Bundle-Format
  unverändert) realisiert. Server-Engine schreibt Snapshots periodisch
  ins MinIO; Wiederanlauf zieht den letzten.

---

## 7. Beobachtbarkeit-Erweiterung

* **Loki** ersetzt das `vector → Datei → R2`-Schema in v2.0; Logs
  fließen via OTel-Collector in Loki, retention 30 Tage hot, 90 Tage
  cold.
* **Tempo** für distributed Tracing. Sampling-Default 5 %, 100 % auf
  `/v1/engine/spawn`, `/v1/snapshots/*`, `/v1/auth/*`.
* **OTel-Auto-Instrumentation** für FastAPI; manuelle Spans für
  Tick-Engine.
* **Grafana-Dashboards** werden um Per-Store-Boards (Neo4j-GDS-Health,
  Qdrant-Index-Stats, ClickHouse-Merge-Tree-Performance) erweitert.

---

## 8. Sicherheits-Erweiterung

* **PostgreSQL-Rollen** mit Least-Privilege; jede Repository-Schicht
  hat eine eigene DB-Rolle.
* **Vault** (HashiCorp Vault oder OpenBao) für Secret-Rotation;
  ersetzt SOPS für Server-Secrets in v2.0.
* **Service-Mesh** (mTLS zwischen Server-Internen-Services) optional —
  Entscheidung in P0.
* **Audit-Log** als WORM (write-once-read-many) in MinIO-mit-Object-Lock.

---

## 9. Open Tooling & Was nicht jetzt entschieden wird

* **k3s vs. Docker-Swarm vs. Compose-on-systemd:** wird in P0 beim Setup
  des M4 entschieden; Default-Recommendation ist k3s wegen Lebensdauer
  + Helm-Chart-Marktbreite.
* **Helm-Charts vs. Kustomize:** Helm; Templates sind Standard-
  Material in der DevOps-Szene.
* **Free-Threaded Python (PEP 703):** Engine kann es nutzen, sobald
  PyTorch und Numpy stable laufen. Heute (2026-05) noch nicht
  default-stabil; Entscheidung in P0/P1.
* **Cloudflare-Free vs. Paid:** wenn DDoS-Pressure steigt, wird Paid
  geprüft. Heute kein Bedarf.
* **Multi-Region:** wird nicht in v2.0 gemacht; Single-M4-Hub reicht.
  Multi-Region-Diskussion ist Thema einer v2.x.
* **Self-Service-Engine-Spawn:** ob ein normaler User in v2.0
  `POST /v1/engine/spawn` darf — oder weiterhin Admin-only — wird
  in P0 mit Last-Profilen entschieden.

---

## 10. Phasen-Detailprotokoll (sobald M4 da)

> Dieser Abschnitt wird zum Zeitpunkt P0 zu einem eigenen
> `implementation/production/00-index.md` — bis dahin reicht hier
> der grobe Plan.

### P0 — Vorbereitung (2–4 Wochen)

| Schritt | Inhalt |
|--------|--------|
| P0.1 | M4 mit macOS frisch eingerichtet, FileVault aktiv |
| P0.2 | Homebrew, OrbStack/Docker Desktop, k3s-Lite (`kind` zum Testen) |
| P0.3 | DNS-Eintrag `hub.terra.example` zeigt auf Cloudflare-Tunnel |
| P0.4 | Polyglot-Stack lokal lauffähig (Compose-Fixture aus `infra/compose/v2-dev/`) |
| P0.5 | Test-Snapshot eines Bestand-Users erfolgreich nach Polyglot importiert |
| P0.6 | OpenAPI-Diff-Workflow: `/v2/*` als additives Schema verifiziert |
| P0.7 | Performance-Benchmarks (synthetic) erreichen Ziele §15 |
| P0.8 | Disaster-Recovery für Polyglot-Stack getestet (Backup → Restore) |

### P1 — Dual-Write (7 Tage)

| Schritt | Inhalt |
|--------|--------|
| P1.1 | Hub-Repository-Layer aktiviert `dual_writer`-Hooks |
| P1.2 | Engine-Bridge schreibt parallel in NATS und Redpanda |
| P1.3 | Reconcile-Job läuft alle 5 min; Drift-Counter → Prometheus |
| P1.4 | Synthetic-Checks für jede Polyglot-Tabelle implementiert |
| P1.5 | Telemetrie zeigt 24 h Drift = 0 für alle Tabellen |
| P1.6 | DEC-Eintrag „P1 stabil" in `memory/system/decisions.md` |

### P2 — Read-Cutover (7 Tage)

| Schritt | Inhalt |
|--------|--------|
| P2.1 | Lese-Pfad `GET /v1/replay/window` schaltet auf ClickHouse + OpenSearch |
| P2.2 | Lese-Pfad `GET /v1/me` schaltet auf Postgres |
| P2.3 | Lese-Pfad `GET /v1/snapshots` schaltet auf Postgres + MinIO |
| P2.4 | Compare-Counter (alt vs. neu) > 99.99 % Match |
| P2.5 | p95-Latenzen erreichen Ziele §15 |
| P2.6 | DEC-Eintrag „P2 stabil" |

### P3 — Stilllegung Alt (1–2 Tage)

| Schritt | Inhalt |
|--------|--------|
| P3.1 | Schreibwege Alt deaktiviert (`dual_writer` → `new_only`) |
| P3.2 | Litestream-Backup angehalten |
| P3.3 | Finaler Vollabzug SQLite → R2 (`audit/legacy/`) |
| P3.4 | NATS-Backup eingefroren, Stream wird read-only |
| P3.5 | Vault-VM stellt um auf Polyglot-Mirror (Postgres-Read-Replica) |

### P4 — Engine-Migration (30 Tage)

| Schritt | Inhalt |
|--------|--------|
| P4.1 | Server-Engine als Default für neue User |
| P4.2 | Bestand-User können `POST /v1/engine/migrate` aufrufen |
| P4.3 | Local-Engine-Pfad bleibt unterstützt (Power-User-Flag) |
| P4.4 | Tick-Engine-Pool stabil (10 parallel) bei 25 aktiven Tenants |

### P5 — Beobachtbarkeits-Erweiterung + Hardening (7 Tage)

| Schritt | Inhalt |
|--------|--------|
| P5.1 | Loki + Tempo + OTel-Collector deployed |
| P5.2 | Service-Mesh-Entscheidung umgesetzt |
| P5.3 | Audit-Log auf MinIO Object-Lock umgestellt |
| P5.4 | KEK-Rotation getestet (siehe `architecture/security.md` §8) |
| P5.5 | DSGVO-Endpoints (`me/export`, `me/delete`) gegen Polyglot getestet |
| P5.6 | DR-Drill auf neuer Topologie (RTO + RPO neu vermessen) |
| P5.7 | DEC-Eintrag „v2.0.0 release-ready" |

---

## 11. Risiken im Migrations­zeitraum

| Risiko                                | Mitigation                                                            |
|---------------------------------------|-----------------------------------------------------------------------|
| Drift während Dual-Write              | Reconcile-Job; Telemetrie mit Pflicht-Schwellen vor P2-Eintritt       |
| Performance-Schock nach Read-Cutover  | Canary-Routing pro User-Cohort; Roll-Back auf SQLite-Lese-Pfad         |
| Engine-State-Verlust beim Wechsel     | Snapshot-Pflicht vor Wechsel; lokaler Snapshot-Cache 7 Tage            |
| Cloudflare-Token-Konflikt              | Pre-flight-Test auf Test-Hostname `hub-canary.terra.example`           |
| Speicher-Run im Polyglot-Stack         | Jeder Store hat eigene cgroup-Limits; Alert bei 80 % Speicher          |
| Nutzer­erwartung „instant migration"   | Kommunikations­plan: Status-Page, Wartungsfenster, Opt-in für P4       |

---

## 12. Querverweise

* `architecture/production.md` — v2.0-Architektur in Detail
* `architecture/data-model.md` §7 — Polyglot-Mapping
* `architecture/mvp.md` §14 — Migrations-Pfad-Übersicht
* `architecture/security.md` — Sicherheits-Updates v2.0
* `architecture/observability.md` — Observability v2.0
* `implementation/mvp/00-index.md` — analog für v1.0
* `formulas/registry.md` — `F.*`-IDs sind unabhängig von der Phase
* `protocols/pdf-lookup.md` — gilt unverändert
* `protocols/event-log.md` — NATS → Redpanda Migration

---

*Stand: 2026-05-08 · Greenfield-Initial · v2.0 noch nicht eröffnet*
