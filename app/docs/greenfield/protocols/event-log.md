# `protocols/event-log.md` — Event-Log-Protokoll (NATS v1.0 → Redpanda v2.0)

> **Zweck.** Ein einziges Event-Log-Vertragsdokument: Subjekte/Topics,
> Event-Schemas, Durability, Idempotenz, Konsumenten, Versionierung.
> Gilt für v1.0 (NATS JetStream) und für v2.0 (Redpanda) — die
> logischen Verträge sind identisch, nur das Transport-Substrat
> wechselt.

---

## Inhalt

1. [Designziele](#1-designziele)
2. [Subjekte/Topics (kanonische Liste)](#2-subjekte-topics-kanonische-liste)
3. [Event-Schemas](#3-event-schemas)
4. [Durability & Limits](#4-durability--limits)
5. [Idempotenz](#5-idempotenz)
6. [Konsumenten](#6-konsumenten)
7. [Schema-Versionierung](#7-schema-versionierung)
8. [v1.0 → v2.0 Migration](#8-v10--v20-migration)
9. [Test-Pfade](#9-test-pfade)

---

## 1. Designziele

* **Eine Quelle der Wahrheit** für alle Event-getriebenen Pfade
  (Engine → Hub → DB, Audit, System).
* **Replay-fähig** in allen Stufen — Engine kann ein Subset
  wiederholen, Hub kann eingefrorene Stream-Segmente neu konsumieren.
* **Keine versteckte Semantik** — jedes Event hat einen klar
  definierten Effekt auf SQL-Persistenz oder Side-Effects.
* **Backpressure** — Konsumenten dürfen nie blockierend werden;
  Lag-Alerts statt Hub-Stillstand.

---

## 2. Subjekte/Topics (kanonische Liste)

> NATS-Subjekt-Form (v1.0). In v2.0 werden `.` durch `_` ersetzt
> und das Präfix wird zur Topic (`engine_events_v1`).

### 2.1 Engine → Hub (Stream `engine`)

| Subjekt                                             | Beschreibung                              |
|------------------------------------------------------|-------------------------------------------|
| `engine.events.<user_id>.<engine_id>.encounter`      | neue Begegnung                            |
| `engine.events.<user_id>.<engine_id>.tier_emerge`    | Tier-Emergenz-Trigger                     |
| `engine.events.<user_id>.<engine_id>.well_birth`     | EBM-Well geboren                          |
| `engine.events.<user_id>.<engine_id>.well_dormant`   | EBM-Well dormant                          |
| `engine.events.<user_id>.<engine_id>.kg_edge_change` | KG-Kanten-Update (Hebbian/Decay)          |
| `engine.events.<user_id>.<engine_id>.summary`        | periodischer Zusammenfassungs-Tick (1/min)|
| `engine.heartbeat.<user_id>.<engine_id>`             | 1× pro 5 s, Lebenszeichen                 |
| `engine.snapshot.uploaded.<user_id>.<engine_id>`     | Snapshot-Upload abgeschlossen (vom Hub gepublished, nicht von der Engine — siehe §6) |

### 2.2 Replay/Frontend (Stream `replay`)

| Subjekt                                  | Beschreibung                              |
|------------------------------------------|-------------------------------------------|
| `replay.window.<user_id>.<request_id>`   | optionaler Antwort-Stream (Push, M7+)     |

### 2.3 System (Stream `system`)

| Subjekt                                  | Beschreibung                              |
|------------------------------------------|-------------------------------------------|
| `system.audit.<actor_user_id>.<action>`  | Audit-Mirror (1:1 von DB-INSERT)           |
| `system.alert.<severity>`                | Alerts (Prometheus → Routing)              |
| `system.health.<service>`                | Service-Health-Pings (1/min)              |

---

## 3. Event-Schemas

Alle Events sind JSON, UTF-8, mit Pflichtfeld `schema_version` und
`event_kind`. Beispiele:

### 3.1 `encounter`

```json
{
  "schema_version": 1,
  "event_kind": "encounter",
  "encounter_id": "e_1714900100000_a7zk8q",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900100000,
  "word": "wahrnehmung",
  "lang": "de",
  "channel": "chat",
  "payload": {"tags": ["philosophy"], "source": "user-input"},
  "engine_signature": {
    "alg": "ecdsa-p256-sha256",
    "thumbprint": "sha256:...",
    "sig_b64": "..."
  }
}
```

### 3.2 `tier_emerge`

```json
{
  "schema_version": 1,
  "event_kind": "tier_emerge",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900250000,
  "tier": 2,
  "members_count": 5,
  "promoted_member_ids": ["w_42_213","w_42_217","w_42_221","w_42_240","w_42_244"],
  "trigger_formula": "F.LNN.GROW.003",
  "engine_signature": {"alg":"ecdsa-p256-sha256","thumbprint":"...","sig_b64":"..."}
}
```

### 3.3 `well_birth`

```json
{
  "schema_version": 1,
  "event_kind": "well_birth",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900300000,
  "well_id": 17,
  "tier": 1,
  "members": ["w_42_001","w_42_017","w_42_032"],
  "theta_at_birth": 0.42,
  "trigger_formula": "F.EBM.WELL.001",
  "engine_signature": {"alg":"ecdsa-p256-sha256","thumbprint":"...","sig_b64":"..."}
}
```

### 3.4 `well_dormant`

```json
{
  "schema_version": 1,
  "event_kind": "well_dormant",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900400000,
  "well_id": 17,
  "reason": "energy_decline_>_threshold",
  "engine_signature": {"alg":"ecdsa-p256-sha256","thumbprint":"...","sig_b64":"..."}
}
```

### 3.5 `kg_edge_change`

```json
{
  "schema_version": 1,
  "event_kind": "kg_edge_change",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900500000,
  "src": "w_42_001",
  "dst": "w_42_017",
  "old_weight": 0.42,
  "new_weight": 0.55,
  "trigger_formula": "F.KG.HEBBIAN.001",
  "engine_signature": {"alg":"ecdsa-p256-sha256","thumbprint":"...","sig_b64":"..."}
}
```

### 3.6 `summary`

```json
{
  "schema_version": 1,
  "event_kind": "summary",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900560000,
  "tick_window_s": 60,
  "metrics": {
    "encounters_in_window": 124,
    "wells_active": 21,
    "tier_max_seen": 3,
    "kg_edges": 9214
  },
  "engine_signature": {"alg":"ecdsa-p256-sha256","thumbprint":"...","sig_b64":"..."}
}
```

### 3.7 `heartbeat`

```json
{
  "schema_version": 1,
  "event_kind": "heartbeat",
  "user_id": 42,
  "engine_id": "macbook-pro-001",
  "ts_ms": 1714900560000,
  "uptime_s": 3600,
  "sw_version": "0.4.1",
  "tick_hz_observed": 8.02,
  "rss_mb": 612.4
}
```

### 3.8 `system.audit`

```json
{
  "schema_version": 1,
  "event_kind": "audit",
  "ts_ms": 1714900560000,
  "actor_user_id": 42,
  "action": "snapshot.upload",
  "target_kind": "snapshot",
  "target_id": "snap_1714900000000_abc123",
  "client_ip_h": "<HMAC>",
  "user_agent_class": "engine-cli",
  "request_id": "req_abc"
}
```

---

## 4. Durability & Limits

### 4.1 v1.0 — NATS JetStream

* Stream `engine`:
  * Storage `file`,
  * `max_age = 7d`,
  * `max_bytes = 64 MiB`,
  * `discard = old`,
  * `retention = limits`,
  * `replicas = 1` (Single-Node).
* Stream `replay`:
  * Storage `memory`,
  * `max_age = 24h`,
  * `max_bytes = 32 MiB`.
* Stream `system`:
  * Storage `file`,
  * `max_age = 30d`,
  * `max_bytes = 16 MiB`.

### 4.2 v2.0 — Redpanda

* Topic `engine_events_v1`:
  * `retention.ms = 30d`,
  * `compaction = false`,
  * `replicas = 3` (Cluster auf M4 + 2× Vault).
* Topic `replay_window_v1`:
  * `retention.ms = 24h`,
  * `replicas = 3`.
* Topic `system_audit_v1`:
  * `retention.ms = 5y`,
  * `compaction = false`,
  * Object-Lock equivalent (MinIO).

---

## 5. Idempotenz

* **Engine-seitig:** Vor dem PUBLISH wird `event_id =
  hash(user_id || engine_id || ts_ms || event_kind || canonical(payload))`
  berechnet; dieser Hash wird in `engine_signature.event_id` mitgeschickt
  (separates Feld in v0.4.x ergänzt).
* **Hub-seitig:** Subscriber-Tabelle `event_dedupe(event_id PK,
  inserted_ms)` (in `system_health` analog) verwirft Duplikate.
* **Replay-Tabelle:** `INSERT OR IGNORE` auf `replay_events` mit
  `event_id` als zusätzlichem unique-Index (M2.4).

---

## 6. Konsumenten

| Konsument             | Subjekte                                | Wirkung                                |
|-----------------------|------------------------------------------|-----------------------------------------|
| `nats-subscriber` (Hub) | `engine.events.*`                       | INSERT in `replay_events` + Cache-Invalid |
| `health-collector` (Hub)| `engine.heartbeat.*`                    | UPDATE `engine_registrations.last_connected_ms`, `system_health` Push |
| `snapshot-processor` (Hub) | (hub-erzeugt) `engine.snapshot.uploaded.*` | UPDATE `snapshots.is_active=1`, R2-Audit |
| `audit-mirror` (Hub)    | `system.audit.*`                        | append-only `audit/`-R2-Mirror          |
| `viewer-ws` (Hub→Frontend) | `engine.events.<user>.*` (Filter)    | WS-Push an verbundene Browser           |

> *Hinweis.* `engine.snapshot.uploaded` ist **kein** Engine-published
> Event — der Hub published es **nach** server­seitiger
> Snapshot-Verifikation (siehe `protocols/snapshot.md` §5). Das hält
> die Snapshot-Wahrheit beim Hub.

---

## 7. Schema-Versionierung

* Pflichtfeld `schema_version` (int, monoton steigend).
* **Additive Änderungen** (neue optionale Felder) → keine Version-
  Bump nötig; Konsumenten ignorieren unbekannte Felder.
* **Schema-Bruch** → neuer `schema_version`-Wert.
* Konsumenten dürfen nie auf nicht implementierten Versionen
  arbeiten — `unsupported_schema_version`-Counter erhöht und Event
  in DLQ-Subjekt `engine.dlq.<reason>` umgeroutet.

---

## 8. v1.0 → v2.0 Migration

* **Phase P0** — Redpanda parallel deployen, leeres Cluster.
* **Phase P1** — Hub-Bridge (`bridge-nats-redpanda`) startet:
  jedes empfangene NATS-Event wird zusätzlich nach Redpanda
  geschrieben. Idempotenz schützt vor Duplikaten.
* **Phase P2** — Konsumenten parallel betreiben (Subscriber gegen
  NATS, „Schatten-Subscriber" gegen Redpanda); Compare-Counter
  erhöhen wenn Inhalte differieren.
* **Phase P3** — Konsumenten schrittweise auf Redpanda umstellen.
* **Phase P4** — NATS-Lese-Pfade abschalten; NATS bleibt 4 Wochen
  als Fallback online.
* **Phase P5** — NATS abbauen.

---

## 9. Test-Pfade

* **Schema-Check (statisch)**: JSON-Schema-Files unter
  `docs/contracts/event-log/<schema_version>/<event_kind>.json`,
  CI-Validation `python -m jsonschema`.
* **Roundtrip (live)**: Pytest-Suite `tests/integration/event_log/
  test_roundtrip_<kind>.py` — Engine-Stub publish → Subscriber
  konsumiert → DB-Zustand verifiziert.
* **Idempotenz**: Pytest `tests/integration/event_log/test_idempotency.py`
  — gleiches Event 3× publish → 1× Insert.
* **DLQ**: Pytest `tests/integration/event_log/test_dlq.py` —
  `schema_version=999` → in DLQ-Subjekt; Counter +1.
* **Bridge (v1→v2)**: `tests/integration/event_log/
  test_bridge_compare.py` — NATS- und Redpanda-Pfad sehen identische
  Inhalte (≥ 99.99 % Match).

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert aus M2, M3, M5,
M8 sowie `architecture/data-model.md` §4 + §7.*
