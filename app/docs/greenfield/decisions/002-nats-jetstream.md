# ADR-002 — NATS JetStream als v1.0-Event-Spine

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `protocols/event-log.md`, `architecture/mvp.md`,
  `implementation/mvp/M2-engine-protocol.md`

## Context

Der Hub muss zwischen Engine-WS-Empfang und SQLite-Schreiben einen
Puffer haben, der:

* Backpressure aushält (Engine sendet im 8 Hz-Tick, SQL-Insert
  kann träger werden),
* Replay-Fähigkeit bietet (bei Subscriber-Crash),
* in v2.0 nahtlos durch Redpanda ersetzbar ist.

## Decision

Wir nutzen **NATS JetStream** in Single-Node-Konfiguration auf der
Hub-VM mit:

* Stream `engine` (file-storage, max 64 MiB, max age 7 d).
* Stream `replay` (memory-storage, max 32 MiB, max age 24 h).
* Stream `system` (file-storage, max 16 MiB, max age 30 d).

Jeder Subscriber (`nats-subscriber`, `health-collector`,
`audit-mirror`) ist ein separater FastAPI-Hintergrund-Task mit
eigener Pull-Consumer-Konfiguration. Idempotenz wird per
`event_id` (Hash über `(user_id, engine_id, ts_ms, event_kind,
canonical(payload))`) sichergestellt (siehe
`protocols/event-log.md` §5).

Für v2.0 wird der Stream auf Redpanda gespiegelt (`bridge-nats-redpanda`,
ADR-008 / `implementation/production.md` §5–§8).

## Consequences

* **Positiv:**
  * RSS-Footprint < 50 MiB.
  * Single-Binary, einfaches systemd-Setup.
  * Replay-Fähigkeit out-of-the-box.
  * Migrationsweg zu Redpanda klar (Kafka-API ist die Brücke).
* **Negativ:**
  * Single-Node = Single-Point-of-Failure auf der Hub-VM.
    Mitigation: bei Hub-Outage ist der Engine-Pfad sowieso unten;
    Snapshot-Path bleibt funktional via Vault-Mirror.
  * 64 MiB max-bytes ist eng — bei Spitze >> 100 Events/s füllt
    der Stream sich in ~2 Tagen. Mitigation: Subscriber-Lag-Alert
    (`A.NATS.PENDING`).
* **Neutral:**
  * Wenn Multi-Region/HA-Anforderung steigt, wechseln wir zu
    NATS-Cluster (Free) oder direkt zu Redpanda (v2.0).

## Alternatives Considered

* **Redis Streams**: Memory-only ohne dauerhafte Disk-Persistenz
  (in v6.x). Verworfen wegen Persistenz-Anforderung.
* **Kafka (single-node)**: Memory-Footprint ≥ 250 MiB, JVM-
  Overhead — sprengt Hub-Budget.
* **Redpanda Single-Node**: Memory-Footprint > 200 MiB in
  v23.x; in v24.x verbessert, aber immer noch im Bereich, der
  Engine-Tick-Inserts blockieren würde.
* **Direkt SQLite ohne Stream**: keine Backpressure-Trennung,
  kein Replay nach Crash — verworfen.

## References

* NATS-Doku: <https://docs.nats.io/jetstream>
* `protocols/event-log.md`
* ADR-008

---

*Greenfield-Initial-ADR.*
