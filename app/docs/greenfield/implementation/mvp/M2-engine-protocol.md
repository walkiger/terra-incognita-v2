# `M2-engine-protocol.md` — Phase M2: Engine-Protokoll

> **Lebendiges Dokument.** Ergebnis: Eingefrorene WS-Vertragsstruktur
> zwischen Local Engine und Hub, NATS-JetStream-Spine eingerichtet,
> Schema-validierter End-to-End-Roundtrip mit Test-Engine, mTLS-Pfad
> dokumentiert und automatisierbar.
>
> **Phase-Tag bei Abschluss:** `v0.3.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M2.1 – M2.7](#4-schritte-m21--m27)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

Wir frieren das **Engine-Protokoll** ein. Nach M2:

* Hub kann eine eingehende WS-Verbindung von Local Engine annehmen.
* Frame-Schemas sind in `docs/contracts/ws/*.schema.json` formal abgelegt.
* NATS JetStream läuft als Compose-Service, Producer/Consumer-Klassen
  sind verfügbar, Schemas validiert.
* Hub akzeptiert nur Frames, die gegen Schema validieren — andere werden
  silent dropped + Metric-Counter erhöht.
* mTLS-Pfad für Engine ist **vollständig dokumentiert**, Test-Cert ist
  generierbar via Skript.
* Snapshot-Upload-Flow (signed slot → binary upload → R2-Promotion) ist
  end-to-end testbar.

**Was M2 nicht tut:**

* Keine eigentliche Engine-Logik (M3).
* Keine Auth-Routen am HTTP-Surface (M5.3 ff). Engine-Auth wird mit
  einem temporären „Test-Token-Issuer" überbrückt, der in M5 abgelöst
  wird.
* Keine Frontend-Integration.

---

## 2. Vorbedingungen

* M0 + M1 abgeschlossen, `v0.2.0` getaggt.
* Hub-Compose läuft, SQLite-Persistenz produktiv.
* R2-Bucket aktiv, Litestream replicating.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §7 — API-Contracts (HTTP + WebSocket)
* `architecture/mvp.md` §8 — Engine-Protokoll
* `architecture/mvp.md` §5 — Datenfluss
* `architecture/mvp.md` §9 — Sicherheit (mTLS-Anteil)
* `Anweisungen.md` §2 — async/await ausnahmslos
* Bestehender Vertrag `runtime_ghost_queue_v0`, `runtime_pause_window_v0`,
  `runtime_ghost_feedback_v0` — wird nicht angefasst, aber als Referenz
  für die Schema-Disziplin genutzt.

---

## 4. Schritte M2.1 – M2.7

---

### M2.1 — engine-ws-frame-schemas

**Branch:** `feature/engine-ws-frame-schemas`
**Issue:** `#NNN`
**Vorbedingungen:** M0 grün
**Berührte Pfade:**
```
docs/contracts/ws/
├── README.md
├── engine_hello.v1.schema.json
├── engine_encounter.v1.schema.json
├── engine_summary.v1.schema.json
├── engine_snapshot.v1.schema.json
├── engine_error.v1.schema.json
├── server_welcome.v1.schema.json
├── server_replay_command.v1.schema.json
├── server_heartbeat.v1.schema.json
├── server_disconnect.v1.schema.json
├── viewer_session_init.v1.schema.json
├── viewer_encounter_new.v1.schema.json
├── viewer_engine_summary.v1.schema.json
├── viewer_engine_availability.v1.schema.json
├── viewer_replay_control.v1.schema.json
backend/api/ws/schemas/                    ← Pydantic-Modelle generiert
tests/contracts/test_ws_schema_lint.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Jedes WS-Frame, das in `architecture/mvp.md` §7 als Beispiel auftaucht,
   hat genau **eine** JSON-Schema-Datei in `docs/contracts/ws/`.
2. Jedes Schema enthält:
   * `$schema: "https://json-schema.org/draft/2020-12/schema"`
   * `title`, `description`
   * `type: object`, `additionalProperties: false`
   * Pflichtfelder `type`, `schema_v` als `const`-Werte
   * `examples: [...]`
3. Pydantic-Modelle in `backend/api/ws/schemas/` sind **automatisch
   abgeleitet** (`datamodel-code-generator`-Step im `make
   contracts-sync`).
4. CI-Job `schema-lint` prüft:
   * Jedes JSON-Schema parsed.
   * Jedes JSON-Beispiel im Schema validiert sich gegen sein Schema.
   * Pydantic-Modelle decken jedes Schema 1:1 ab (kein Schema ohne
     Modell, kein Modell ohne Schema).
5. Versionierung: jedes Schema hat eine Major-Version im Dateinamen
   (`*.v1.schema.json`); Bumps führen zu Side-by-Side-Ablage von
   `*.v2.schema.json`.

**Tests:**
* `tests/contracts/test_ws_schema_lint.py::test_all_schemas_parse`
* `tests/contracts/test_ws_schema_lint.py::test_examples_valid_under_schema`
* `tests/contracts/test_ws_schema_lint.py::test_pydantic_models_match`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff (viele Schemas)
**Fertig wenn:** AC + CI grün; Schema-Lint-Job ist Pflicht-Gate.

---

### M2.2 — nats-jetstream-broker-compose

**Branch:** `feature/nats-jetstream-broker-compose`
**Issue:** `#NNN`
**Vorbedingungen:** M0 grün
**Berührte Pfade:**
```
deploy/nats/nats-server.conf
deploy/compose/hub.yml                    ← Service `nats` aktiv
docs/operations/nats.md
tests/integration/test_nats_broker.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. NATS-Server-Konfiguration:
   * `jetstream { store_dir: "/data/jetstream", max_memory: 64MB, max_file: 1024MB }`
   * Auth: NKey/JWT-basiert; Anonymous-Connect nur localhost
   * `monitoring port: 8222` (intern)
2. Streams werden via `init-streams.sh` (im Compose-Init-Container)
   eingerichtet:
   * `ENCOUNTERS` — Subjects `encounters.>`, retention `interest`,
     max_age 7d, replicas 1.
   * `REPLAY` — `replay.>`, max_age 30d.
   * `SNAPSHOTS` — `snapshots.>`, retention `workqueue`, max_age 30d.
3. NATS-Service hat:
   * `mem_limit: 100m`, `mem_reservation: 60m`
   * Health-Check via `nats-server-rust-cli ping`
4. Tests:
   * Stream-Existenz nach Compose-Up.
   * Publish + Consume innerhalb 100 ms p95.

**Tests:**
* `tests/integration/test_nats_broker.py::test_streams_exist_after_up`
* `tests/integration/test_nats_broker.py::test_basic_publish_consume`
* `tests/integration/test_nats_broker.py::test_jetstream_retention`

**Ressourcen-Budget:** ~80 MB Idle, 120 MB Spitze.
**Geschätzte PR-Größe:** ~280 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M2.3 — nats-event-log-clients

**Branch:** `feature/nats-event-log-clients`
**Issue:** `#NNN`
**Vorbedingungen:** M2.1 gemerged, M2.2 gemerged
**Berührte Pfade:**
```
backend/event_log/
├── __init__.py
├── client.py                              ← async producer/consumer
├── subjects.py                            ← Konstanten + Helfer
└── schemas.py                             ← Imports aus M2.1
tests/event_log/test_client.py
tests/event_log/test_subjects.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `client.py` enthält:
   * `EventLogProducer.publish(subject, payload, schema_v)` — validiert
     gegen das Schema, signiert mit JWT-Service-Token.
   * `EventLogConsumer.subscribe(subject_filter, callback, durable_name)`
     — JetStream-durable-consumer, Ack/Nack-Logik mit Backoff.
2. **Validierung** schlägt vor dem `publish` zu, nicht nachher.
3. **Tenant-Subject-Filter** für Encounter:
   * `encounters.<user_id>.<source>` (z. B. `encounters.42.user_input`)
   * Subject-Helfer in `subjects.py` mit Type-Hints und Tests.
4. **Backoff bei Consumer-Fehler:**
   * Standard: exponentiell, base 1 s, factor 2, max 60 s.
   * Nach 5 Failures pro Message → Dead-Letter-Subject `dlq.<original>`.
5. Tests gegen einen In-Process-NATS oder gegen den Compose-Stack mit
   `pytest-docker-compose`.

**Tests:**
* `tests/event_log/test_client.py::test_producer_validates_payload`
* `tests/event_log/test_client.py::test_producer_publishes_valid`
* `tests/event_log/test_client.py::test_consumer_durable_resumes`
* `tests/event_log/test_client.py::test_dlq_after_max_failures`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M2.4 — engine-ws-handshake-and-mtls

**Branch:** `feature/engine-ws-handshake-and-mtls`
**Issue:** `#NNN`
**Vorbedingungen:** M2.1 gemerged
**Berührte Pfade:**
```
backend/api/ws/engine.py                  ← FastAPI WS-Endpoint
backend/api/ws/auth.py                    ← Token-Validation für WS
backend/api/security/mtls.py              ← Cert-Pinning gegen Cloudflare-Header
deploy/cloudflared/config.hub.yml         ← `originRequest.tlsTimeout` etc.
scripts/operations/issue_engine_cert.sh    ← lokale Test-CA + Engine-Cert
docs/operations/engine-mtls.md
tests/api/ws/test_engine_handshake.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `engine.py` definiert die FastAPI-Route:
   * `@app.websocket("/ws/v1/engine")`
   * Subprotocol `terra-engine.v1` muss vom Client gesendet werden.
   * JWT aus `Authorization: Bearer …` validiert (Test-Token-Issuer aus
     M2.7 / temporär aus `secrets/`).
   * mTLS-Cert wird via Cloudflare-Header
     `Cf-Mtls-Cert-Subject` / `Cf-Mtls-Cert-Issuer` geprüft (Cloudflare
     terminiert mTLS und reicht den Subject durch). Bypass-Mode für
     lokales Dev (kein Cloudflare) ist explizit dokumentiert.
2. Reject-Fälle: schließe WS mit Code 4401 (auth), 4403 (mtls), 4426
   (upgrade required für unbekannte Subprotocols), 4429 (rate limit).
3. **Engine-Singleton-Regel** (siehe `architecture/mvp.md` §12): bei
   zweiter Verbindung desselben Users wird die alte mit
   `server/disconnect{reason: "engine_replaced"}` geschlossen.
4. `scripts/operations/issue_engine_cert.sh` erstellt:
   * Eine lokale Test-CA (`./tmp/ca/...`)
   * Ein Engine-Client-Cert mit CN = `<email>@engine.local`
   * Output zur Verwendung mit `--client-cert` der Engine-CLI.
5. Doku `docs/operations/engine-mtls.md`:
   * Wie eine echte Engine-Cert ausgestellt wird (Cloudflare-Trusted-CA
     vs. eigene CA).
   * Lebensdauer / Rotation.
   * Was passiert, wenn ein Engine-Cert kompromittiert wird (Revocation
     liste / CF Access Update).

**Tests:**
* `tests/api/ws/test_engine_handshake.py::test_rejects_missing_subprotocol`
* `tests/api/ws/test_engine_handshake.py::test_rejects_invalid_token`
* `tests/api/ws/test_engine_handshake.py::test_accepts_valid_handshake`
* `tests/api/ws/test_engine_handshake.py::test_singleton_engine_replaces`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~550 Lines diff
**Fertig wenn:** AC + CI grün; ein Test-Engine kann sich lokal ohne
Cloudflare verbinden, mit gefälschtem CF-Header.

---

### M2.5 — engine-ws-roundtrip-tests

**Branch:** `feature/engine-ws-roundtrip-tests`
**Issue:** `#NNN`
**Vorbedingungen:** M2.4 gemerged, M2.3 gemerged
**Berührte Pfade:**
```
tests/integration/test_engine_roundtrip.py
backend/api/ws/router.py                  ← Frame-Routing zu Repos / NATS
backend/api/ws/dispatch.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Roundtrip-Szenario:
   * Test-Engine connectet.
   * Sendet `engine/hello`. Hub speichert `engine_connections`-Row.
   * Sendet `engine/encounter`. Hub:
     * Schreibt `encounters`-Row.
     * Publish auf NATS `encounters.<user_id>.<source>`.
   * Test-Viewer-Subscriber empfängt das Encounter-Event.
   * Sendet `engine/summary`. Hub aktualisiert in-memory-Summary.
   * Hub schickt `server/heartbeat` periodisch.
   * Test-Engine schickt `engine/disconnect` (oder schließt Socket).
   * Hub setzt `engine_connections.status = 'closed'`.
2. **Latenz-Ziel** im lokalen Loopback: < 50 ms p95 für Encounter →
   Viewer.
3. **Fehlerszenarien**:
   * Schema-Verletzung → Frame wird verworfen, `bad_frame_total`
     Counter erhöht, Engine bleibt verbunden.
   * NATS-Publish-Fehler → Encounter trotzdem in DB persistiert; ein
     `pending_publish`-Marker ermöglicht Retry-Loop.
4. Tests laufen sowohl im In-Process-Mode (FastAPI-TestClient WS) als
   auch im Compose-Mode (`pytest-docker-compose`).

**Tests:**
* `tests/integration/test_engine_roundtrip.py::test_full_happy_path`
* `tests/integration/test_engine_roundtrip.py::test_bad_frame_dropped`
* `tests/integration/test_engine_roundtrip.py::test_publish_failure_retried`
* `tests/integration/test_engine_roundtrip.py::test_disconnect_marks_status`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün; Compose-Smoke-Test im Nightly läuft 24 h
ohne Connection-Leak.

---

### M2.6 — snapshot-upload-flow

**Branch:** `feature/snapshot-upload-flow`
**Issue:** `#NNN`
**Vorbedingungen:** M2.5 gemerged, M1.7 gemerged, M1.9 gemerged
**Berührte Pfade:**
```
backend/api/snapshots.py                  ← Initiate / Complete (HTTP, light)
backend/api/ws/binary.py                   ← WS-Binary-Frame-Receiver
backend/storage/r2.py                      ← R2-Client (async)
tests/api/test_snapshots_flow.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Upload-Flow:
   * Engine sendet `engine/snapshot` mit `scope`, `size_bytes`,
     `content_sha256`.
   * Hub validiert Limit (64 MB), erstellt `snapshots`-Row mit
     `uploading`, vergibt `snapshot_id`, schickt `server/snapshot_grant`
     (signed R2-Multipart-PUT-URL ODER Hub-internen Upload-Token, MVP-
     Default: Hub-internen Upload-Token + Hub forwardet Upload nach R2).
   * Engine streamt Binary-Frames mit `seq` + Chunk; Hub assembelt im
     Hub-Local-Tmp-Pfad und multipart-uploadet zu R2.
   * Nach komplettem Upload: Hub berechnet SHA-256, vergleicht; bei
     Match: `snapshots.complete` aufgerufen, Status `ready`, R2-Key
     persistiert.
2. **Streaming-Disziplin**: Hub puffert nicht das gesamte Bundle im
   RAM. Stattdessen: WS-Binary-Frames werden direkt zu einem
   Tmp-File geschrieben; multipart-Upload erfolgt parallel.
3. Fehlerpfade:
   * SHA-256-Mismatch → `snapshots.expire`, R2-Object löschen,
     Engine-Frame `engine/snapshot_rejected` mit Grund.
   * Timeout (> 5 min ohne weitere Bytes) → analog Cleanup.
4. R2-Client (`backend/storage/r2.py`) nutzt `aiobotocore` (async S3-
   client); Verbindungs-Pool-Limit `max_pool_connections=5`.

**Tests:**
* `tests/api/test_snapshots_flow.py::test_full_upload_and_complete`
* `tests/api/test_snapshots_flow.py::test_sha_mismatch_rejects`
* `tests/api/test_snapshots_flow.py::test_timeout_cleanup`
* `tests/api/test_snapshots_flow.py::test_size_limit_enforced`

**Ressourcen-Budget:** Hub-Tmp-Verzeichnis kurzzeitig bis 64 MB belegt,
RAM stabil.
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün; Snapshot-Upload via Test-Engine
funktioniert.

---

### M2.7 — engine-protocol-version-policy

**Branch:** `docs/engine-protocol-version-policy`
**Issue:** `—`
**Vorbedingungen:** M2.6 gemerged
**Berührte Pfade:**
```
docs/operations/engine-protocol-versioning.md
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Doku enthält:
   * **Subprotocol-Strategie**: ein WS-Subprotocol pro Major-Version
     (`terra-engine.v1`, `terra-engine.v2`).
   * **Schema-Strategie**: `schema_v` pro Frame, neue Felder dürfen
     nur additiv kommen.
   * **Eintrag in der Whitelist**: `(subprotocol, schema_v)`-Paare,
     die der Hub akzeptiert.
   * **Reject-Verhalten**: HTTP 426 Upgrade Required für unbekannte
     Subprotocol-Header; WS-Close 4426 für unbekannte `schema_v` in
     einem akzeptierten Subprotocol.
   * **Migrationsplan**: wie der Hub für 30 Tage parallel `v1` und
     `v2` annehmen kann.
2. `backend/api/ws/version_policy.py` enthält die Whitelist als
   konfigurierbare Konstante; Tests verifizieren Reject-Pfade.

**Tests:**
* `tests/api/ws/test_version_policy.py::test_unknown_subprotocol_rejected`
* `tests/api/ws/test_version_policy.py::test_unknown_schema_v_rejected`
* `tests/api/ws/test_version_policy.py::test_dual_version_window`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff (vorwiegend Doku)
**Fertig wenn:** AC + CI grün.

---

## 5. Phasen-Gate

M2 gilt als grün, wenn:

1. M2.1 – M2.7 in `00-index.md` auf `[x]`.
2. End-to-End-Roundtrip-Test (Test-Engine → Hub → DB → NATS → Viewer)
   im CI grün.
3. NATS-Round-Trip-Latenz-Histogramm hat p95 < 100 ms im Compose-Smoke.
4. mTLS-Pfad mindestens einmal manuell auf der echten Hub-VM geprüft
   (Smoke).
5. Snapshot-Upload mit 32 MB-Bundle funktioniert.
6. Tag `v0.3.0` gepusht.

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M2 noch nicht eröffnet*
