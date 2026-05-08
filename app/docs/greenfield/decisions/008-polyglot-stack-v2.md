# ADR-008 — Polyglot-Stack-Auswahl (v2.0)

* **Status:** Accepted (für v2.0, **nicht** für v1.0)
* **Datum:** 2026-05-08
* **Bezug:** `architecture/production.md`,
  `architecture/data-model.md` §7,
  `implementation/production.md`.

## Context

Der v2.0-Stack (auf M4 oder vergleichbarer Hardware) muss Workloads
abbilden, die SQLite-allein nicht skalierbar bedienen kann:

* Graph-Pfad-Queries auf KGs mit ≥ 100 k Knoten pro Tenant.
* Vektor-ANN-Suche (LNN-Embeddings) mit Hybrid-Filter.
* Sub-Sekunden-Aggregat-Queries auf Replay-Events (≥ 100 Mio Rows).
* Multilinguale Volltextsuche.
* Echte Event-Spine mit Replay (Kafka-API).

Eine einzige „One-Size-Fits-All"-DB würde bei mindestens einem dieser
Workloads stark abfallen.

## Decision

Der v2.0-Stack ist polyglott:

* **Neo4j Enterprise + GDS** — Knowledge Graph.
* **Qdrant** — Vektoren (LNN, Embeddings).
* **ClickHouse** — Replay-Aggregate, Health-Metriken.
* **PostgreSQL 16** — operative Daten (Auth, Sessions, Snapshot-
  Manifeste, Audit).
* **OpenSearch** — multilinguale Volltextsuche.
* **Redpanda** — Event-Spine (Kafka-API).
* **DragonflyDB** — Cache + Pub/Sub.
* **MinIO** + R2 — Object-Storage (Snapshots, Audit-Mirror, Logs).

Begründung pro Store: siehe `architecture/production.md` §3 und §12.

## Consequences

* **Positiv:**
  * Jeder Workload hat einen passenden Engine.
  * Skalierbar bis 25 aktive Tenants auf einer M4 (siehe §15
    Performance-Ziele in `architecture/production.md`).
  * Klare Migration v1→v2 (Dual-Write, siehe
    `implementation/production.md` §5).
* **Negativ:**
  * Operations-Last: 8 Stateful-Stores zu pflegen.
  * Higher-Order-Komplexität bei Cross-Store-Konsistenz
    (z.B. neuer Encounter erzeugt Postgres-Row + Redpanda-Event +
    Neo4j-Knoten + Qdrant-Vector).
* **Mitigation:**
  * k3s + Helm-Charts (siehe ADR-012).
  * Engine-Pool pro Tenant (siehe ADR-013).
  * Einheitliches Repository-Layer-Interface, das transactional
    in alle Stores schreibt.

## Alternatives Considered

* **Postgres mit Erweiterungen** (`pgvector`, `Apache AGE`): deckt
  Vektor + Graph gut ab, aber bei großen Volumina deutlich
  langsamer als Neo4j/Qdrant. Bleibt als „Light"-Variante denkbar
  für Tenants mit kleineren Workloads.
* **Single-Vendor (z.B. ArangoDB)**: deckt Graph + Document, fehlt
  ein dedizierter Vektor- und Time-Series-Engine.
* **Cloud-managed-Stack** (Aiven/Confluent/Pinecone): Lock-in +
  laufende Kosten; v2.0-Self-Host bleibt erste Wahl.

## References

* `architecture/production.md` §3, §12, §15
* `architecture/data-model.md` §7, §8
* `implementation/production.md` §5–§9

---

*Greenfield-Initial-ADR.*
