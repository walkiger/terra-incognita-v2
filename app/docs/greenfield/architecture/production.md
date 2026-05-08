# `architecture/production.md` — Vollausbau-Architektur (v2.0)

> **Lebendiges Dokument.** Ziel-Architektur für den M4-Mac-Deploy.
>
> **Lesepflicht**, sobald die M4-Hardware verfügbar ist und der
> Übergang von v1.x → v2.0 geplant wird. Vorher: orientierende
> Lektüre.
>
> Diese Datei ist absichtlich **weniger detailliert** als
> `architecture/mvp.md`. Detail-Engineering passiert erst, wenn die
> Migration konkret bevorsteht — im selben Stil, in dem dieser
> Greenfield-Plan jetzt entsteht.

---

## Inhalt

1. [Trigger & Zielbild](#1-trigger--zielbild)
2. [Hardware-Annahme](#2-hardware-annahme)
3. [Polyglot-Stack — was, warum, an welcher Stelle](#3-polyglot-stack--was-warum-an-welcher-stelle)
4. [Topologie](#4-topologie)
5. [Was unverändert bleibt](#5-was-unverändert-bleibt)
6. [Was sich ändert](#6-was-sich-ändert)
7. [Migrations-Strategie](#7-migrations-strategie)
8. [Skalierungs-Annahmen](#8-skalierungs-annahmen)
9. [Beobachtbarkeit im Vollausbau](#9-beobachtbarkeit-im-vollausbau)
10. [Risiken im Vollausbau](#10-risiken-im-vollausbau)
11. [Offene Architekturfragen](#11-offene-architekturfragen)

---

## 1. Trigger & Zielbild

**Trigger:** M4-Mac mit ausreichend RAM (Ziel 192 GB) ist als Server
verfügbar. Spätere alternative Trigger:

* Ein anderer dedizierter Server mit ≥ 64 GB RAM, ausreichender SSD und
  guter Anbindung.
* Eine Managed-Kubernetes-Umgebung mit reservierter Kapazität (perspektivisch).

**Zielbild:** Das Drei-Pol-System (LNN ↔ EBM ↔ KG) läuft **vollständig
serverseitig**, multi-tenant, polyglott persistiert, mit dediziertem
Event-Log-Spine. Frontend bleibt Browser-Client. Local Engines bleiben
**unterstützt** als zweiter Compute-Pfad (Power-User behalten ihre
Heim-GPU als Beschleuniger), sind aber kein Standard-Pfad mehr.

**Was v2.0 explizit besser kann als v1.x:**

| Fähigkeit                                        | v1.x | v2.0                                    |
|--------------------------------------------------|------|-----------------------------------------|
| Server-seitige Tick-Engine                       | nein | ja, eigener Prozess, ggf. PEP 703       |
| Multi-User parallel mit eigenem Server-Compute   | nein | ja, mit Engine-Pool pro User             |
| Echtzeit-Cypher-Pfad-Queries auf großem KG       | nein | ja, Neo4j + GDS                          |
| Vektor-Hybrid-Suche skalierbar                   | nein | ja, Qdrant                               |
| Replay-Aggregate-Queries unter 100 ms            | nein | ja, ClickHouse                           |
| Verteilte Volltextsuche                          | nein | ja, OpenSearch                           |
| Event-Log-Replay-Reconstruction (Kafka-API)      | begrenzt | voll, Redpanda                       |
| Tracing End-to-End mit OTel                      | nein | ja                                       |

---

## 2. Hardware-Annahme

**Hauptknoten:** M4-Mac Studio oder Pro mit:

* **CPU:** M4 Pro/Max/Ultra (≥ 12 Performance-Cores)
* **RAM:** ≥ 96 GB (Ziel 192 GB für komfortable Vektor-/KG-Größen)
* **SSD:** ≥ 2 TB
* **GPU:** Apple Silicon GPU mit MPS-Backend (PyTorch nutzbar)

**Sekundärknoten (optional):**

* **Oracle 2× AMD Micro** bleiben als „Public-Edge / Health-Probe / Backup-
  Host" weiter aktiv. Ihre Aufgabe in v2.0:
  * statisches Frontend ausliefern
  * Cloudflare-Tunnel-Failover
  * Public-`/v1/health`-Surface als Heartbeat-Indikator
* Sie laufen **nicht** mehr als Hub im Sinne von v1.x — der Hub ist der M4.

**Backup-Cluster:** R2 bleibt, MinIO-Cluster (auf Heim-Hardware oder bei
einem zweiten Cloud-Provider) ergänzt für höhere Disk-Quote.

---

## 3. Polyglot-Stack — was, warum, an welcher Stelle

| Modul                                  | Engine                | Warum dieser Store                                                                                              |
|----------------------------------------|----------------------|------------------------------------------------------------------------------------------------------------------|
| Knowledge Graph                        | **Neo4j Enterprise** | Echte Graph-Engine, Cypher, GDS-Bibliothek deckt Centrality/Community-Detection ab — direkter Hebel für Tier-Detection auf großen Graphen. |
| Vektorraum (Embeddings)                | **Qdrant**            | Hybrid-Search (Vektor + Payload-Filter), Rust, distributed-fähig.                                                |
| Tick-/Replay-Analytik                  | **ClickHouse**        | Columnar, Materialized Views, sub-Sekunden-Queries über Milliarden Tick-Rows.                                    |
| Operativer Zustand                     | **PostgreSQL 16**     | Konsistenz, Constraints, FKs, JSONB; Sessions, Auth, Cross-Store-Manifeste.                                      |
| Volltext/Multilingual                  | **OpenSearch**        | BM25 + multi-lingual Analyzers + Synonyme + Fuzzy.                                                               |
| Event-Log-Spine                        | **Redpanda**          | Kafka-API, Single-Binary, Rust, kein ZooKeeper.                                                                  |
| Cache + Pub/Sub                        | **DragonflyDB**       | Redis-API, multi-threaded, drop-in-Ersatz.                                                                       |
| Object-Store                           | **MinIO Cluster** + R2 | MinIO als On-Prem-Primary, R2 als Edge-Mirror.                                                                  |
| Tick-Engine                             | Eigener Prozess       | PyTorch + ggf. PEP 703 free-threaded Python.                                                                     |

Diese Tabelle ist **nicht** überraschend, weil sie 1:1 das wiederspiegelt,
was vor dem Hardware-Reality-Check als „Vollausbau" diskutiert wurde —
siehe `00-glossary.md` Kapitel 3.

---

## 4. Topologie

```
                   ┌──────────────────────────────────────────────┐
USERS (Browser) ──►│           CLOUDFLARE EDGE (Free/Paid)         │
                   │  TLS, WAF, R2, optional Workers, Access       │
                   └────┬───────────────────┬────────────────┬─────┘
                        │ HTTPS+WS         │ Static FE       │ R2 (Mirror)
                        ▼                  ▼                 ▼
                   ┌────────────────────────────────────────────┐
                   │             M4-HUB (≥ 96 GB)                │
                   │ ┌──────────────────────────────────────┐    │
                   │ │ Caddy / Nginx (rev-proxy + static FE)│    │
                   │ ├──────────────────────────────────────┤    │
                   │ │ FastAPI (HTTP + WS)  uvicorn N=cores  │    │
                   │ ├──────────────────────────────────────┤    │
                   │ │ Tick-Engine (eigener Prozess)         │◄──┐│
                   │ │  - PyTorch, ggf. py3.13t              │   ││
                   │ │  - Engine-Pool (pro User wählbar)     │   ││
                   │ ├──────────────────────────────────────┤   ││
                   │ │ Projektoren (eigene Prozesse)         │   ││
                   │ │  - Redpanda → Neo4j/Qdrant/Click/OS   │   ││
                   │ ├──────────────────────────────────────┤   ││
                   │ │ Stateful Stores                       │   ││
                   │ │  Neo4j · Qdrant · ClickHouse ·        │   ││
                   │ │  Postgres · OpenSearch · DragonflyDB  │   ││
                   │ │  MinIO · Redpanda                     │   ││
                   │ └──────────────────────────────────────┘   ││
                   └────────────────────┬──────────────────────┘ │
                                        │                          │
                                        ▼                          │
                                 ┌────────────────┐                │
                                 │ Power-User     │                │
                                 │ Workstation    │                │
                                 │ Local Engine   │ ───────────────┘
                                 │ (optional)     │
                                 └────────────────┘
```

**Oracle-VMs** bleiben als „Edge-Sentinel" stehen, übernehmen aber keine
Compute-Last:

* statische Frontend-Auslieferung (Cache-Warmer-Funktion für CF-Edge)
* `/v1/health`-Mirror (Multi-Region-Heartbeat)
* Notnagel-Empfang von Logs, falls M4 unreachable wird

---

## 5. Was unverändert bleibt

* **HTTP-API-Pfade** (`/v1/...`)
* **WebSocket-Channels** (`/ws/v1/viewer`, `/ws/v1/engine`)
* **Replay-Schema** `replay_timeline_window_v4` (und ggf. v5 für
  ClickHouse-Aggregates)
* **JWT-Auth-Schema** (Claims, Token-TTL)
* **Frontend-Codebasis** — komplett identisch, nur neuer API-Endpoint.
* **Local-Engine-Pakete** — können sich weiterhin verbinden; das Engine-
  WS-Protokoll wird abwärtskompatibel um eine zweite Major-Version
  erweitert (`terra-engine.v2`), die alte v1 bleibt für Übergangszeit
  unterstützt.
* **`F.*`-Formel-IDs** und Konsumenten in Engine-Code.

---

## 6. Was sich ändert

### Persistenz

* SQLite **wird abgelöst**, nicht ersetzt: Daten werden in eine neue
  Postgres-Instanz migriert; bestehende Schreibwege gehen ab Cutover in
  Postgres.
* Replay-Events werden ab Cutover doppelt geschrieben: Postgres (für
  Cross-Refs/Joins) + ClickHouse (für Analytik). Übergangsphase ~30 Tage,
  dann Postgres-Spiegel auf das Notwendige reduziert.
* Volltext wandert in OpenSearch; SQLite-FTS5 bleibt während der Übergangsphase aktiv (Read-Path).

### Compute

* Tick-Engine wandert in den **M4-Hub**. Konfig: ein Engine-Prozess pro
  aktivem Tenant, gestartet on-demand, idle-suspended nach 10 min.
* Local-Engine bleibt unterstützt: User mit eigener Hardware können sie
  weiterhin verwenden. Beide Pfade sind interoperabel.

### Event-Log

* NATS JetStream → Redpanda. Migration: NATS-Stream wird in Redpanda
  importiert (`rpk topic create --replay`). Nach Cutover NATS read-only,
  dann nach 30 Tagen abgeschaltet.

### KG-Tier-Detection

* `find_energy_wells()` wird auf Neo4j-GDS portiert. Die `F.KG.TIER.*`-
  Formel-Definitionen bleiben unverändert; nur das Backend wechselt.

### Beobachtbarkeit

* Loki + Tempo + OTel kommen dazu. Prom + Grafana bleiben. Logs werden
  über `OTel-Collector` pipelined.

### Deployment

* Compose bleibt im Dev. Production wechselt auf **k3s** auf M4 (oder
  full Kubernetes, je nach Wartungsaufwand) mit Helm-Charts pro Service.

---

## 7. Migrations-Strategie

Wir wenden ein **Doppel-Schreibe-Pattern** an, damit Cutover ohne
Datenverlust möglich ist:

### Phase P0 — Vorbereitung

* M4 ist verfügbar, alle v2.0-Stores sind installiert und gesund.
* Testdaten-Migration (Snapshot des MVP-SQLite → Polyglot) ist
  geprüft.
* OpenAPI-Diff `v1` → `v2.0` ist null (keine Breaking Changes geplant).

### Phase P1 — Schreiben in Alt + Neu

* Hub schreibt **parallel** in SQLite **und** in Postgres/Neo4j/Qdrant/
  ClickHouse. Lesen bleibt aus SQLite (Confidence-Phase).
* Dauer: 7 Tage. Fehler-Telemetrie: Diff-Counter pro Tabellen-Tupel.

### Phase P2 — Lesen aus Neu

* Bei null Diff: Lesen schaltet auf Polyglot um. SQLite weiter beschrieben
  als Schatten. Dauer: 7 Tage zur Beobachtung.

### Phase P3 — SQLite stilllegen

* SQLite wird Read-only, Litestream-Backup angehalten. Ein letzter
  Vollabzug nach R2 für Audit. Polyglot ist Single Source of Truth.

### Phase P4 — Engine-Wandern

* Bestehende Local-Engine-Sessions werden nicht zwangsweise migriert.
  Server-Engine wird pro User auf Wunsch aktiviert (`POST
  /v1/engine/spawn`). Nach 30 Tagen Default-Verhalten = Server-Engine.

### Rollback-Schritte

* Aus jeder Phase ist Rollback möglich: Lesen / Schreiben kann jederzeit
  auf SQLite zurückgeschwenkt werden, solange SQLite noch beschrieben
  wird (P0–P2).

---

## 8. Skalierungs-Annahmen

| Dimension                                          | v2.0-Zielwert (96 GB)               |
|----------------------------------------------------|-------------------------------------|
| Concurrent Active Tenants (Server-Engine)          | 25                                  |
| Concurrent Viewer-WS                               | 1 000                               |
| Tick-Rate pro aktivem Tenant                       | 8 Hz                                |
| Encounter-Rate Spitze pro Tenant                   | 60 / min                            |
| Persistierte Encounter-Events Total                | 100 Mio (1 Jahr Spitzennutzung)     |
| KG-Knoten pro Tenant                               | 100 k                               |
| KG-Kanten pro Tenant                               | 1 Mio                               |
| Vektor-Embeddings (alle Tenants)                   | 5 Mio (Qdrant Single-Node)          |
| Replay-Query p95                                   | < 200 ms (ClickHouse)               |
| Cypher Pfad-Queries p95                            | < 150 ms (Neo4j Cluster, intra-tenant) |

Bei Erreichen dieser Werte wird ein zweiter M4 als Replikat sinnvoll
oder die Migration auf eine Managed-Cloud-Variante geplant.

---

## 9. Beobachtbarkeit im Vollausbau

* **Metriken:** Prometheus + Grafana erweitert um per-Store-Exporter
  (Neo4j, Qdrant, ClickHouse, Postgres, Redpanda).
* **Logs:** Loki, durch OTel-Collector gespeist. Retention 30 Tage hot,
  90 Tage cold (R2).
* **Traces:** Tempo, mit Sampling 5 % auf Default-Pfaden, 100 % auf
  Engine-Spawn / Snapshot-Upload.
* **Alerts:** Erweitert um Per-Store-Health, Doppel-Schreibe-Lag, Engine-
  Prozess-Liveness.

---

## 10. Risiken im Vollausbau

| Risiko                                             | Mitigation                                                                  |
|----------------------------------------------------|------------------------------------------------------------------------------|
| Polyglot-Operations-Last (zu viele Engines)        | Helm-Charts standardisiert; ein Operator pro Store; klare Runbooks.          |
| Doppel-Schreibe-Drift in P1                        | Diff-Counter in Telemetrie; täglicher Reconcile-Job vor Cutover.             |
| M4 Single-Point-of-Failure                          | R2-/MinIO-Backups, definierter Hot-Spare auf zweitem M4 oder Cloud-Snapshot. |
| Engine-Prozess-Memory-Leak frisst Hub-RAM          | Per-Engine-`memory_max` (cgroup), Restart-Policy, Saturation-Alerts.         |
| GIL-Limit in Tick-Engine                           | PEP 703 free-threaded Python evaluieren; Fallback auf Multi-Process.        |
| Vektor-Index-Rebuild-Zeit                          | Asynchrone Updates; Snapshot-and-restore-Strategie für Qdrant.              |
| Cross-Tenant-Datenleak im Polyglot-Stack           | RBAC pro Store + Repository-Layer-Test-Suite mit `user_id`-Negative-Tests.  |

---

## 11. Offene Architekturfragen

* **Engine-Pooling:** dedizierter Prozess pro Tenant vs. Multi-Tenant-
  Engine-Prozess mit Tenant-Context. Beide Varianten haben Trade-offs;
  Entscheidung mit Test-Daten in P0.
* **WebGPU im Frontend** als Pflicht oder Best-Effort?
* **GDS-Lizenz** Neo4j Enterprise: Kosten klären, Alternative AGE
  (Postgres) für nicht-graphlastige Workloads.
* **Lokale GPU-Beschleunigung**: ROCm vs. CUDA vs. MPS — nur MPS auf M4
  relevant, übrige nur für Power-User.
* **Multi-Region-Cluster:** zweiter M4 in anderer geografischer Zone
  oder Managed-Cloud-Replikat?
* **Schreibpfad-Konsistenz:** Sofort-vs-eventual-konsistent zwischen
  Neo4j und Qdrant — wie wird ein Encounter, der einen neuen Knoten und
  ein neues Embedding erzeugt, atomar persistiert?

---

## 12. Polyglot-Stack — Detail-Profile pro Store

### 12.1 Neo4j Enterprise + GDS

* **Rolle:** kanonische Knowledge-Graph-Speicherung pro Tenant.
* **Datenmodell:**
  * Label `:Concept` (Eigenschaften `tenant_id`, `node_id`, `word`,
    `lang`, `tier`, `created_tick`, `last_seen_tick`, `seen_count`).
  * Label `:Tier` als getrennter Knoten mit Edge `:CONCEPT_OF_TIER`.
  * Beziehungen `[:HEBBIAN {weight, last_update_tick}]` und
    `[:WELL_MEMBER]` zwischen Concepts und Wells.
* **Cypher-Beispiel — Pfade aus einem Concept zur nächsten Tier-3-
  Insel:**
  ```
  MATCH p = shortestPath(
    (start:Concept {tenant_id: $tid, word: $word})-[:HEBBIAN*..6]-
    (target:Concept {tenant_id: $tid, tier: 3}))
  RETURN p LIMIT 5;
  ```
* **GDS-Anwendung:**
  * `Louvain`-Community-Detection pro Tenant für KG-Cluster-Hinweise
    (nutzt der Audit-Layer in v2.x, nicht für Tier-Detection
    selbst — `F.KG.TIER.001` bleibt deterministisch).
  * `Pagerank` als optionaler Bias für `_lnnFocus`-Score.
* **Topologie-Empfehlung:**
  * 1× Core-Server, 2× Read-Replicas → Cypher-Lese-Pfade verteilen.
  * Pro Tenant ein eigenes Database (Neo4j 5 Multi-DB-Feature) ist
    denkbar; Default in v2.0: Single-Database mit `tenant_id`-
    Label-Filter + APOC-Constraints.
* **Backup:**
  * `neo4j-admin database backup`-Job nach MinIO `neo4j/`-Bucket
    täglich.

### 12.2 Qdrant

* **Rolle:** ANN-Suche über LNN-Output- und Encounter-Embeddings.
* **Collections:**
  * `embeddings_lnn` (Größe: `iD = max(B + N*(N+1)/2)`, je nach
    aktuellem höchsten Tier des Tenants — bis 4096; Default 1024
    bei Provisionierung).
  * `embeddings_words` (statisch B = 256, alle Sprachen).
* **Payload pro Punkt:** `tenant_id`, `concept_id`, `tier`,
  `created_tick`.
* **Hybrid-Search:** Vektor-Score + `payload_filter` per
  `tenant_id` + optional `tier`/`lang`.
* **Sharding:** 1 Shard pro Collection in v2.0 Single-Node; Cluster-
  Pfad ab v2.5.
* **Backup:** Snapshot-API → MinIO `qdrant/`-Bucket täglich.

### 12.3 ClickHouse

* **Rolle:** zeit-/ereignis­serielle Workloads — Replay-Aggregate,
  Health-Metriken, Quota-Audit.
* **Tabelle `replay_events_v2`:**
  ```sql
  CREATE TABLE replay_events_v2 (
    tenant_id    UInt64,
    ts           DateTime64(3),
    event_kind   LowCardinality(String),
    word         String,
    meta         String CODEC(ZSTD(3)),
    source_engine LowCardinality(String),
    INDEX idx_word word TYPE bloom_filter GRANULARITY 4,
    INDEX idx_kind event_kind TYPE set(0) GRANULARITY 4
  )
  ENGINE = ReplacingMergeTree
  PARTITION BY (tenant_id, toYYYYMM(ts))
  ORDER BY (tenant_id, ts, event_kind);
  ```
* **Materialized Views:**
  * `replay_events_density_5min` mit `SUM(count)` pro Tenant×Bin.
  * `tier_stability_per_day` als Tracker für Tier-Stabilität pro
    Tenant.
* **Backup:** `clickhouse-backup` nach MinIO täglich.

### 12.4 PostgreSQL 16

* **Rolle:** klassische operative Daten — Auth, Sessions, Snapshots-
  Manifeste, Audit-Log.
* **Schema-Layout:**
  * `auth` Schema: `users`, `refresh_tokens`, `sessions`.
  * `system` Schema: `audit_log`, `engine_registrations`,
    `quota_usage`, `settings`.
  * `snapshots` Schema: `snapshots`, `snapshot_chunks`.
* **Erweiterungen:**
  * `pgcrypto` (UUIDs, HMAC).
  * `pg_partman` für `audit_log`-Partitionierung pro Monat.
* **Replikation:** Logical Replication zu einem Read-Replica auf
  Vault-Hardware.
* **Backup:** `pg_basebackup` täglich + WAL-G für PITR.

### 12.5 OpenSearch

* **Rolle:** Volltext über Replay-Events (`q`-Pfad), multilingual.
* **Indexschema:**
  ```json
  {
    "mappings": {
      "properties": {
        "tenant_id": {"type": "keyword"},
        "ts":        {"type": "date"},
        "event_kind":{"type": "keyword"},
        "word":      {"type": "text", "analyzer": "german"},
        "meta_text": {"type": "text", "analyzer": "german"}
      }
    }
  }
  ```
* **Index-Pattern:** `replay-{tenant_id}-{YYYY-MM}`.
* **Sprachen:** `german`, `english`, `french`, `italian` Analyzer.
  Sprachwahl folgt `users.preferred_lang`.
* **Backup:** Snapshot-Repository → MinIO `opensearch/`.

### 12.6 Redpanda

* **Rolle:** Event-Log-Spine; ersetzt NATS JetStream (siehe
  `protocols/event-log.md` §8).
* **Konfiguration:**
  * 3 Broker auf einer M4 (mit Pin auf separate Cores), in v2.5
    auf zwei M4-Knoten verteilt.
  * Topic `engine_events_v1` mit `replicas=3`,
    `retention.ms=2592000000` (30 d), `compaction=false`.

### 12.7 DragonflyDB

* **Rolle:** Cache + Pub/Sub. Drop-in für Redis.
* **Verwendung:**
  * `quota_usage`-Sliding-Window-Counters,
  * `kv_cache.scope='replay.window'`-Cache,
  * Pub/Sub-Topic `notifications_v2_<tenant_id>` für WS-Push.
* **Persistenz:** Snapshots stündlich; nicht autoritativ.

### 12.8 MinIO + R2

* **MinIO** als On-Prem-Primary für Snapshots, Backups, Audit-Mirror,
  Logs.
* **R2** bleibt als Edge-Mirror für DR + statisches Frontend
  (Cloudflare Pages).
* Replikation per `mc mirror --watch` oder MinIO-`s3:Replication`.

### 12.9 Tick-Engine (Server-Side)

* **Prozess:** ein eigener Python-Prozess pro Tenant (Engine-Pool).
* **Beschleunigung:** PyTorch + MPS-Backend.
* **Lifecycle:** start-on-demand, idle-suspend nach 10 min, hard
  kill nach 60 min Inaktivität.
* **API:** spricht über Redpanda mit Hub.

---

## 13. Cluster-Plan k3s

* **Knoten:**
  * 1× M4 (Server + Worker), Label `role=hub`.
  * 1× Vault-VM (Worker), Label `role=vault`.
  * Optional: 2. M4 als HA-Replica (`role=hub-replica`).
* **Workloads:**
  * StatefulSets für Neo4j, ClickHouse, Postgres, Qdrant,
    OpenSearch, Redpanda, MinIO, DragonflyDB.
  * Deployments für FastAPI-Hub, Tick-Engine-Pools, Frontend.
  * DaemonSets für Vector (Logs) und Node-Exporter (Metrics).
* **Storage:**
  * `local-path-provisioner` für Single-Node-PVCs.
  * Stateful-Stores nutzen NVMe-Backed-PVs auf der M4 (M.2 SSD).
* **Ingress:**
  * Cloudflare-Tunnel-Sidecar (DaemonSet) leitet 443 nach
    `ingress-nginx`/Caddy weiter.
  * mTLS-Validation für `ws/engine` über Caddy + Header-Whitelist.
* **Konfiguration:**
  * Helm-Charts unter `infra/helm/<service>/`.
  * Secrets via External-Secrets-Operator + SOPS.
* **Upgrades:**
  * Rolling-Upgrade pro StatefulSet, max 1 PodDisruptionBudget.
  * Engine-Pool-Drain mit `kubectl drain` führt zu Auto-Migration
    der Engine-Sessions.

---

## 14. Sicherheits-Aktualisierung in v2.0

* **mTLS** zwischen allen internen Services (`linkerd` oder
  `istio` als Service-Mesh).
* **Per-Tenant-Schlüssel** für KEK (jeder Tenant hat eigenen KEK
  unter Hardware-KMS auf M4 — z.B. macOS Keychain mit
  Touch-ID-Zugriff für Admin-Operationen).
* **Identity-Provider** (optional): OIDC-Integration mit Keycloak
  oder Auth0 — für SSO-Benutzer; lokale Email-Login bleibt parallel.
* **Audit-Object-Lock** auf MinIO (5 Jahre, write-once).
* **Cluster-RBAC** (k3s) granular pro Service-Account.

---

## 15. Performance-Ziele (Vollausbau)

| Pfad                                                | Ziel p95   | Ziel p99   |
|-----------------------------------------------------|-----------:|-----------:|
| `GET /v1/replay/window` (ClickHouse + OpenSearch)   |    180 ms  |    400 ms  |
| `GET /v1/kg/path` (Neo4j Cypher, ≤6 hops)            |    120 ms  |    300 ms  |
| `POST /v1/encounters` (Postgres + Redpanda + projektor) | 90 ms  |    250 ms  |
| Engine-Tick-Loop intern                              |    40 ms   |    80 ms   |
| Vektor-Suche (Qdrant top-50, hybrid)                 |    50 ms   |    120 ms  |
| WS-Engine-Event-Ack                                  |    100 ms  |    250 ms  |

---

## 16. Querverweise

* `architecture/mvp.md` — v1.0
* `architecture/data-model.md` §7 — Polyglot-Mapping
* `architecture/security.md` — Threat-Modell + Kontrollen
* `architecture/observability.md` — v2.0-Pipeline
* `implementation/production.md` — v2.0 Was/Wann (ohne Branches)
* `protocols/event-log.md` — NATS → Redpanda Migration
* `formulas/registry.md` — `F.*`-Einträge bleiben gleich
* `00-glossary.md` Kapitel 3 — Polyglot-Begriffe

---

*Stand: 2026-05-08 · Greenfield-Initial · v2.0-Architektur, vertieft.*
