# `architecture/observability.md` — Beobachtbarkeit, Metriken, SLOs

> **Zweck.** Vollständige Definition aller Metriken, Logs, Traces,
> Alerts und Service-Level-Objectives für v1.0 (Oracle-Free-Tier-Hub +
> Vault) sowie deren Erweiterung in v2.0 (M4-Stack mit Loki/Tempo/
> OpenTelemetry).
>
> Diese Datei ist die Single-Source-of-Truth für die Greenfield-
> Implementierung; Prometheus-Regeln, Grafana-Boards und Alert-Routes
> referenzieren explizit Metric-IDs aus diesem Dokument.

---

## Inhalt

1. [Pipeline-Übersicht v1.0](#1-pipeline-übersicht-v10)
2. [Pipeline-Übersicht v2.0](#2-pipeline-übersicht-v20)
3. [Metric-IDs (kanonische Liste)](#3-metric-ids-kanonische-liste)
4. [Logs — Schema, Felder, Retention](#4-logs--schema-felder-retention)
5. [Traces & Spans](#5-traces--spans)
6. [SLOs & Error-Budgets](#6-slos--error-budgets)
7. [Alert-Routen, Schweregrade, Reaktions­zeiten](#7-alert-routen-schweregrade-reaktionszeiten)
8. [Dashboards (Grafana-Boards)](#8-dashboards-grafana-boards)
9. [Synthetic-Checks](#9-synthetic-checks)
10. [Recording-Rules (Prometheus)](#10-recording-rules-prometheus)
11. [Akzeptanz­kriterien](#11-akzeptanzkriterien)

---

## 1. Pipeline-Übersicht v1.0

```
[Hub VM-A]                     [Vault VM-B]
 ├─ FastAPI ──► /metrics ──┐    ├─ r2-pull
 ├─ Engine-WS              │    ├─ snapshot-processor
 ├─ NATS                   │    └─ /metrics ──┐
 ├─ Litestream             │                  │
 ├─ Caddy                  ├──► Prometheus ◄──┘
 └─ cloudflared            │           │
                           ▼           ▼
                       Grafana    Alertmanager → Webhook
                                                (E-Mail/Discord/CF-Email)

Logs (alle Services):  stdout/stderr → Vector → R2 (`audit/`,
                                                    `app-logs/`)
                                       └─► Promtail-Verzeichnis
                                           (lokal, in v1.0 keine Loki-
                                           Aggregation)
```

---

## 2. Pipeline-Übersicht v2.0

```
[Hub-Cluster auf M4]                       [Vault auf Oracle]
 ├─ FastAPI ──► OTel-Exporter ──┐           ├─ r2-pull
 ├─ Engine-bridge               │           ├─ snapshot-processor
 ├─ Redpanda                    │
 ├─ ClickHouse                  ├──► OTel-Collector
 ├─ Postgres                    │           │
 ├─ Neo4j, Qdrant, OpenSearch   │           ▼
 ├─ DragonflyDB                 │      [Tempo]  [Loki]  [Prometheus]
 ├─ MinIO                       │           │
 └─ Caddy / k3s-Ingress         ▼           ▼
                          Alertmanager   Grafana
```

---

## 3. Metric-IDs (kanonische Liste)

Alle Metriken benannt nach `<service>_<area>_<unit>`-Schema, Prefix
`terra_`. Labels in Klammern.

### 3.1 FastAPI (Hub)

| ID                                            | Type      | Labels                              | Beschreibung |
|-----------------------------------------------|-----------|-------------------------------------|---|
| `terra_http_requests_total`                   | Counter   | `route`,`method`,`status_class`     | Request-Zähler pro Route. |
| `terra_http_request_duration_seconds`         | Histogram | `route`,`method`                    | Latenz pro Route. |
| `terra_http_requests_in_flight`               | Gauge     | `route`                             | Aktuelle parallele Requests. |
| `terra_auth_login_attempts_total`             | Counter   | `outcome` (`ok`/`fail_password`/`fail_disabled`/`fail_locked`) | Login-Statistik. |
| `terra_auth_token_rotations_total`            | Counter   | `outcome` (`ok`/`reuse_detected`)   | Refresh-Token-Rotationen. |
| `terra_replay_requests_total`                 | Counter   | `policy`,`mode`,`q_present`         | Replay-Window-Aufrufe. |
| `terra_replay_query_duration_seconds`         | Histogram | `policy`,`mode`                     | Replay-SQL-Dauer. |
| `terra_replay_planner_choice_total`           | Counter   | `mode_chosen`                       | Auto-Resolver-Entscheidungen. |
| `terra_ws_connections_active`                 | Gauge     | `channel` (`viewer`/`engine`)       | Aktive WS-Verbindungen. |
| `terra_ws_messages_total`                     | Counter   | `direction`,`channel`,`kind`        | WS-Frame-Zähler. |
| `terra_ws_close_total`                        | Counter   | `channel`,`reason`                  | WS-Disconnects. |
| `terra_quota_blocks_total`                    | Counter   | `bucket`                            | Anzahl Quota-induzierter Blocks. |
| `terra_admin_actions_total`                   | Counter   | `action`                            | Admin-Aktionen. |

### 3.2 NATS / Engine-Pfad

| ID                                  | Type      | Labels                                | Beschreibung |
|-------------------------------------|-----------|---------------------------------------|---|
| `terra_engine_events_ingested_total`| Counter   | `event_kind`,`source_engine`           | Replay-Events nach DB. |
| `terra_engine_ingest_lag_ms`        | Histogram | `event_kind`                           | `created_at_ms - ts_ms`. |
| `terra_engine_heartbeat_seconds`    | Gauge     | `engine_id`,`user_id`                   | Sekunden seit letztem Heartbeat. |
| `terra_nats_stream_pending`         | Gauge     | `stream`,`consumer`                     | Lag-Counter. |
| `terra_nats_stream_bytes`           | Gauge     | `stream`                                | Stream-Größe in Bytes. |

### 3.3 Persistenz (SQLite + Litestream)

| ID                                      | Type      | Labels       | Beschreibung |
|-----------------------------------------|-----------|--------------|---|
| `terra_sqlite_wal_bytes`                | Gauge     | `db_name`     | WAL-Größe. |
| `terra_sqlite_busy_total`               | Counter   | `db_name`     | Anzahl `SQLITE_BUSY`. |
| `terra_sqlite_pragma_journal_mode`      | Gauge     | `mode`        | 1 wenn aktiv. |
| `terra_litestream_replication_lag_ms`   | Gauge     | `db_name`     | Sekunden, die Replikation hinterher ist. |
| `terra_litestream_uploads_total`        | Counter   | `db_name`,`outcome` | Upload-Zähler. |
| `terra_r2_uploads_total`                | Counter   | `bucket`,`kind`,`outcome` | Snapshot/Audit-Uploads. |

### 3.4 System-Health

| ID                              | Type    | Labels       | Beschreibung |
|---------------------------------|---------|--------------|---|
| `terra_process_rss_bytes`       | Gauge   | `service`,`pid_label` | Resident-Memory. |
| `terra_process_cpu_seconds_total`| Counter | `service`,`pid_label` | CPU-Zeit. |
| `terra_node_memory_available_bytes` | Gauge | `node`        | Verfügbarer RAM. |
| `terra_node_disk_free_bytes`    | Gauge   | `node`,`mount`| Freier Disk. |
| `terra_node_uptime_seconds`     | Counter | `node`        | Uptime. |

### 3.5 Frontend (gepushed via `/api/v1/telemetry/frontend`, optional)

| ID                                 | Type      | Labels      | Beschreibung |
|------------------------------------|-----------|-------------|---|
| `terra_frontend_lcp_seconds`       | Histogram | `route`     | Largest Contentful Paint. |
| `terra_frontend_inp_ms`            | Histogram | `route`     | Interaction to Next Paint. |
| `terra_frontend_js_errors_total`   | Counter   | `route`,`code`| JS-Fehler. |
| `terra_frontend_ws_reconnect_total`| Counter   | `cause`     | WS-Reconnects. |

---

## 4. Logs — Schema, Felder, Retention

### 4.1 Schema

JSON-Struktur, eine Zeile pro Event:

```json
{
  "ts": "2026-05-08T17:30:00.123Z",
  "level": "INFO",
  "service": "fastapi-hub",
  "event": "http.request.completed",
  "request_id": "req_a1b2c3",
  "user_id": 42,
  "session_id": 7,
  "route": "/api/v1/replay/window",
  "method": "GET",
  "status": 200,
  "latency_ms": 142,
  "engine_id": null,
  "client_ip_h": "<HMAC-SHA256-prefix>",
  "user_agent_class": "browser-chromium-stable",
  "outcome_meta": {"policy":"combined","mode":"auto"},
  "schema_version": 1
}
```

### 4.2 Pflichtfelder

* `ts`, `level`, `service`, `event`, `schema_version`.
* Bei HTTP-Events zusätzlich: `request_id`, `route`, `method`,
  `status`, `latency_ms`.
* Bei Audit-Events zusätzlich: `actor_user_id`, `target_kind`,
  `target_id`, `action`.

### 4.3 Retention (v1.0)

* **Lokal (Caddy/Vector)**: 14 Tage rolling, max 1 GiB pro Service.
* **R2-Mirror**: 90 Tage `standard`, danach `archive` 5 Jahre.
* **Audit-Subset**: 365 Tage `standard`, danach `archive` 5 Jahre.

### 4.4 Retention (v2.0)

* **Loki**: 30 Tage hot, 1 Jahr archive.
* Audit zusätzlich in MinIO mit Object-Lock (5 Jahre).

---

## 5. Traces & Spans

### 5.1 v1.0

* Manuelle Span-Annotation via `request_id`-Korrelation.
* Kein Tracing-Backend (Tempo) deployed (Speicher­budget).
* `request_id` muss in Logs aller Services präsent sein, um
  Cross-Service-Korrelation per `jq` zu ermöglichen.

### 5.2 v2.0

* OpenTelemetry-SDK in FastAPI, Engine-Bridge, Redpanda-Consumer.
* Tempo-Backend, Sampling 5% (1% für `/health`).
* Wichtige Spans:
  * `http.server` (Route-Level).
  * `db.query` (mit `db.system`-Label: `postgres`/`clickhouse`/...).
  * `engine.tick.process` (Engine-Bridge).
  * `replay.search` (Hybrid-Planner-Pfade).

---

## 6. SLOs & Error-Budgets

### 6.1 Verfügbarkeit

| Pfad                       | SLO  | Messfenster | Error-Budget |
|----------------------------|------|--------------|--------------|
| Public Frontend (`/`)      | 99.5%| 30 d         | 3.6 h/Monat  |
| Auth (`/auth/*`)           | 99.5%| 30 d         | 3.6 h        |
| Replay (`/api/v1/replay/*`)| 99.0%| 30 d         | 7.2 h        |
| WS Viewer                  | 98.5%| 30 d         | 10.8 h       |
| WS Engine                  | 99.0%| 30 d         | 7.2 h        |

### 6.2 Latenz

| Endpoint                   | p95   | p99    |
|----------------------------|-------|--------|
| `GET /health`              | 50 ms | 150 ms |
| `POST /auth/login`         | 350 ms| 800 ms |
| `GET /api/v1/replay/window` (DB-warm) | 800 ms | 1500 ms |
| `POST /api/v1/encounters`  | 300 ms| 800 ms |
| `WS engine event ack`      | 250 ms| 600 ms |

### 6.3 Korrektheit

* `replay.compare.eq / (eq + neq) > 99.99 %` (während Dual-Write-Phase
  v1→v2).
* `litestream_replication_lag_ms < 30000` 99% der Zeit.
* `engine_heartbeat_seconds < 15` 99.9% der Zeit (sonst Engine als
  „offline" markiert).

---

## 7. Alert-Routen, Schweregrade, Reaktions­zeiten

| Alert-ID                        | Schwere | Bedingung                                       | Route       | Reaktion |
|---------------------------------|---------|--------------------------------------------------|-------------|----------|
| `A.HUB.RSS.HIGH`               | warn    | `terra_process_rss_bytes{service="fastapi-hub"} / 1024 / 1024 > 500` für 5 min | E-Mail   | 30 min  |
| `A.HUB.RSS.CRIT`               | crit    | wie oben aber > 700 für 2 min                    | Pager      | 5 min   |
| `A.NODE.MEM.LOW`               | crit    | `terra_node_memory_available_bytes / 1024 / 1024 < 100` für 1 min | Pager | 5 min |
| `A.LITESTREAM.LAG`             | warn    | `terra_litestream_replication_lag_ms > 60000` für 5 min | E-Mail | 30 min |
| `A.LITESTREAM.STALL`           | crit    | `terra_litestream_replication_lag_ms > 600000` für 5 min | Pager | 5 min |
| `A.NATS.PENDING`               | warn    | `terra_nats_stream_pending > 1000` für 5 min     | E-Mail   | 30 min  |
| `A.ENGINE.OFFLINE`             | warn    | kein Heartbeat 30 s                              | Webhook  | best-effort |
| `A.AUTH.LOGINFAIL.SPIKE`       | warn    | rate(`terra_auth_login_attempts_total{outcome="fail_password"}`)[5m]>50 | E-Mail | 30 min |
| `A.REFRESH.REUSE`              | crit    | `terra_auth_token_rotations_total{outcome="reuse_detected"}` > 0 in 5 min | Pager | 5 min |
| `A.REPLAY.SLO.BREACH`          | warn    | p95 > 1500 ms 10 min                             | E-Mail   | 60 min  |
| `A.WS.RECONNECTSTORM`          | warn    | rate(`terra_frontend_ws_reconnect_total`)[5m] > 10 | E-Mail | 60 min  |
| `A.R2.UPLOAD.FAIL`             | warn    | rate(`terra_r2_uploads_total{outcome="fail"}`)[5m] > 0.1 | E-Mail | 60 min  |
| `A.OOM.KILL`                   | crit    | `node_vmstat_oom_kill > 0` increase 5 min        | Pager    | 5 min   |
| `A.HEALTH.DROP`                | crit    | Synthetic-Check `/health` nicht 2/3 OK in 5 min  | Pager    | 5 min   |

**Pager-Kanal in v1.0**: Webhook auf Cloudflare-Email-Worker (frei),
Discord-Channel als Fallback. Keine PagerDuty-Lizenz im MVP.

---

## 8. Dashboards (Grafana-Boards)

| Board                        | Inhalt                                     |
|------------------------------|--------------------------------------------|
| `01 — Public Health`         | Verfügbarkeit, p50/p95/p99 für `/`, `/health`, `/auth/*`, `/api/v1/replay/*` |
| `02 — Auth Flow`             | Login-Erfolg/Fehler, Refresh-Reuse, Token-Lifetime |
| `03 — Engine`                | Heartbeats, Events/s, Lag, Backlog         |
| `04 — Replay`                | Query-Volumen, Mode-Verteilung, Top-Queries|
| `05 — System (Hub)`          | RSS, CPU, Disk, OOM-Kill                   |
| `06 — System (Vault)`        | RSS, R2-Pull-Rate, Mirror-Lag              |
| `07 — Litestream/R2`         | Replication-Lag, Upload-Rate, Bucket-Größe |
| `08 — NATS`                  | Pending, Bytes pro Subject                 |
| `09 — Frontend (Web Vitals)` | LCP, INP, CLS, JS-Error-Rate               |
| `10 — Quota & Abuse`         | Block-Counts, Login-Fail-Spikes            |

Alle Boards versioniert unter `infra/grafana/boards/*.json`.

---

## 9. Synthetic-Checks

* **`check_health`** — alle 60 s `GET https://terra.example/health`,
  Erwartung 200 + `version` + `db_ok=true`.
* **`check_login_flow`** — alle 5 min: register-temporary-user →
  login → refresh → me → logout (Test-User-Pfad).
* **`check_replay_smoke`** — alle 10 min: `GET …/replay/window?
  policy=combined&q=test&page_size=10`, Erwartung 200 + `events[]`.
* **`check_ws_handshake`** — alle 5 min: WSS connect bis
  `server/welcome` empfangen.

Synthetic-Checks werden in v1.0 vom **Vault** ausgeführt (entkoppelt
vom Hub) und schreiben Ergebnisse in `system_health` + R2-Mirror.

---

## 10. Recording-Rules (Prometheus)

```yaml
groups:
- name: terra-rules
  interval: 30s
  rules:
  - record: terra:http_requests:rate5m
    expr: sum by (route) (rate(terra_http_requests_total[5m]))
  - record: terra:http_p95:5m
    expr: histogram_quantile(0.95, sum(rate(terra_http_request_duration_seconds_bucket[5m])) by (le, route))
  - record: terra:replay_p95:5m
    expr: histogram_quantile(0.95, sum(rate(terra_replay_query_duration_seconds_bucket[5m])) by (le, policy, mode))
  - record: terra:engine_lag_p99:5m
    expr: histogram_quantile(0.99, sum(rate(terra_engine_ingest_lag_ms_bucket[5m])) by (le, event_kind))
  - record: terra:rss_mb:hub
    expr: max(terra_process_rss_bytes{service="fastapi-hub"}) / 1024 / 1024
```

---

## 11. Akzeptanz­kriterien

Vor `v1.0.0`:

* Alle Metric-IDs aus §3 sind in `/metrics` jeder Service-Instanz
  vorhanden.
* Alle Alert-IDs aus §7 sind in `infra/prometheus/alerts.yml` konfiguriert
  und werden in Grafana sichtbar gerendert.
* Alle Dashboards aus §8 versioniert im Repo (`infra/grafana/boards/`).
* Synthetic-Checks aus §9 laufen seit ≥ 7 Tagen ohne Fehlalarm.
* Recording-Rules aus §10 sind ohne Lint-Fehler im Prometheus-Run.

---

*Stand: 2026-05-08 · Greenfield-Initial · referenziert von M0–M8.*
