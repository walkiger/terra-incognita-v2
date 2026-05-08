# `M5-api-surface.md` — Phase M5: API-Surface

> **Lebendiges Dokument.** Ergebnis: Vollständige FastAPI-App mit Auth,
> Multi-User-Tenant-Isolation, Encounter-/Snapshot-/Replay-/Diagnostic-
> /Admin-Routen, beiden WebSocket-Channels, Rate-Limits — und einem
> eingefrorenen OpenAPI-Schema `v1`.
>
> **Phase-Tag bei Abschluss:** `v0.6.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M5.1 – M5.14](#4-schritte-m51--m514)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

* Public-API ist vollständig implementiert und getestet.
* OpenAPI 3.1 wird automatisch aus FastAPI-Routen abgeleitet und in
  `docs/contracts/openapi/v1.json` eingefroren.
* Auth ist produktionsreif (JWT RS256, Argon2id, Refresh-Token-Rotation).
* WebSocket-Channels sind aktiv und konsumieren / publizieren NATS-
  Subjects.
* Rate-Limits / Quotas funktionieren und sind getestet.
* `/v1/diagnostic` zeigt **echte** Werte aus M4-Engine + Hub-Komponenten.
* `/v1/admin/*` ist hinter Cloudflare Access geschützt (optional, in M8
  finalisiert).

**Was M5 NICHT tut:**

* Kein Frontend (M6).
* Kein Replay-UI-Polish (M7).
* Kein Tunnel-Hardening (M8).

---

## 2. Vorbedingungen

* M0–M4 abgeschlossen (`v0.5.0`).
* Engine produziert echten LNN-State.
* Hub-DB-Schema ist stabil; Repository-Layer komplett.
* NATS spricht produktiv mit der Engine.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §7 — API-Contracts (HTTP + WS)
* `architecture/mvp.md` §9 — Sicherheit (Auth, Token, Eingabe-Validierung)
* `architecture/mvp.md` §12 — Multi-User
* `Anweisungen.md` §2, §4
* Bestehende Replay-Schemas `replay_timeline_window_v4`

---

## 4. Schritte M5.1 – M5.14

---

### M5.1 — fastapi-app-skeleton

**Branch:** `feature/fastapi-app-skeleton`
**Issue:** `#NNN`
**Vorbedingungen:** M0 grün
**Berührte Pfade:**
```
backend/api/
├── __init__.py
├── app.py                                 ← `create_app()`
├── lifespan.py                            ← Startup/Shutdown-Hooks
├── deps.py                                ← FastAPI-Dependencies (DB, Repos, …)
├── errors.py                              ← Globale Exception-Handler
├── middleware/
│   ├── __init__.py
│   ├── request_id.py
│   ├── access_log.py
│   └── csp.py
├── routers/                                ← leer; Router pro Feature in M5.2+
└── ws/                                     ← bereits aus M2.4 / M2.7 vorbereitet
backend/main.py                              ← uvicorn entry point
tests/api/test_app_factory.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `create_app()` ist die einzige Stelle, an der eine FastAPI-App
   instanziiert wird (auch in Tests). Keine module-level App.
2. Lifespan-Hook erstellt: DB-Connection-Pool, NATS-Producer, Repo-
   Instanzen, schließt sie sauber.
3. Globale Exception-Handler:
   * `ValidationError` → 422 mit standardisiertem JSON.
   * `RepositoryError` → 500 (mit Trace-ID, ohne Internals nach außen).
   * `AuthError` → 401 oder 403 je nach Subklasse.
4. Middleware:
   * `request_id` injiziert `X-Request-ID` aus Header oder generiert ULID.
   * `access_log` schreibt JSON-Lines.
   * `csp` setzt strikte Content-Security-Policy `default-src 'self'`.
5. **Keine Routen außer `/`** in M5.1 — Smoke gibt `{"app": "terra", "v": "..."}` zurück.

**Tests:**
* `tests/api/test_app_factory.py::test_app_creates_with_dependencies`
* `tests/api/test_app_factory.py::test_request_id_middleware`
* `tests/api/test_app_factory.py::test_csp_header_present`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.2 — http-health-and-version

**Branch:** `feature/http-health-and-version`
**Issue:** `—` (trivial)
**Vorbedingungen:** M5.1 gemerged
**Berührte Pfade:**
```
backend/api/routers/health.py
backend/api/routers/version.py
backend/api/diagnostics/dep_status.py
tests/api/test_health.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `GET /v1/health` antwortet in < 50 ms im Idle:
   ```json
   { "ok": true,
     "version": "0.5.x",
     "schema": 5,
     "uptime_s": 1234,
     "deps": { "sqlite": "ok", "nats": "ok", "litestream": "ok" } }
   ```
2. **Dependency-Status** wird real geprüft:
   * SQLite: `SELECT 1`.
   * NATS: Producer schickt `health.ping`, Subscriber bestätigt
     in < 200 ms; bei Timeout → `degraded`.
   * Litestream: Process Liveness-Check über Hub-internen Endpoint
     (`http://litestream:9090/snapshots/...`).
3. `GET /v1/version` ist statisch JSON, von `/v1/health` getrennt
   (manche LB-Healthchecks brauchen leichte Variante).
4. Wenn `deps` einen Status `down` enthält: HTTP-Status bleibt 200,
   `ok` ist `false`. Cloudflare-LB muss diese Logik kennen (Doku in
   `architecture/mvp.md` §11).

**Tests:**
* `tests/api/test_health.py::test_health_under_50ms`
* `tests/api/test_health.py::test_health_dep_status_when_nats_down`
* `tests/api/test_health.py::test_version_static`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~280 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.3 — auth-jwt-rs256

**Branch:** `feature/auth-jwt-rs256`
**Issue:** `#NNN`
**Vorbedingungen:** M5.1 gemerged
**Berührte Pfade:**
```
backend/api/security/jwt.py
backend/api/routers/auth.py
backend/api/deps_auth.py
tests/api/test_auth_jwt.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. JWT-Bibliothek: `python-jose[cryptography]` oder `pyjwt[crypto]`.
2. Schlüsselpaar als 4096-Bit RSA, Private-Key in
   SOPS (`secrets/hub.sops.yaml.JWT_PRIVATE_KEY`), Public-Key
   öffentlich an `/v1/.well-known/jwks.json`.
3. Claims (verbindlich):
   * `sub` — String, User-ID
   * `email` — String
   * `scope` — `viewer` | `engine` | `admin`
   * `iat` — Issue Time
   * `exp` — Expiry (≤ 60 min für Access-Token)
   * `jti` — ULID, eindeutige Token-ID
4. `POST /v1/auth/login` (Email/PW) → `{access_token, refresh_token, expires_in}`.
5. **Negative-Tests**:
   * Falsches PW → 401.
   * Disabled User → 403.
   * Falsche Algorithm-Behauptung im JWT-Header (`alg=none`) → 401.

**Tests:**
* `tests/api/test_auth_jwt.py::test_login_success_returns_tokens`
* `tests/api/test_auth_jwt.py::test_login_wrong_password_401`
* `tests/api/test_auth_jwt.py::test_disabled_user_403`
* `tests/api/test_auth_jwt.py::test_alg_none_attack_rejected`
* `tests/api/test_auth_jwt.py::test_jwks_endpoint_returns_public_key`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.4 — auth-passwords-argon2

**Branch:** `feature/auth-passwords-argon2`
**Issue:** `—`
**Vorbedingungen:** M5.3 gemerged
**Berührte Pfade:**
```
backend/api/security/passwords.py
backend/db/repos/users.py                  ← Schreib-Helfer für `pwhash_argon2`
tests/api/test_passwords.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Bibliothek `argon2-cffi`, Profil `time_cost=3, memory_cost=64MiB, parallelism=2`.
2. `hash(password) -> str` und `verify(password, hash) -> bool`. Letzterer
   wirft **niemals** auf falschem Hash, sondern gibt `False` zurück.
3. Rehash-on-verify-Logik: wenn der Hash gegen ein altes Profil läuft,
   wird er beim nächsten erfolgreichen Login mit aktuellem Profil
   re-hasht.
4. Negativ-Test: leeres PW, Whitespace-Only-PW, sehr lange PW (≥ 4096
   Zeichen) → klare Fehler / Limits.

**Tests:**
* `tests/api/test_passwords.py::test_hash_and_verify_roundtrip`
* `tests/api/test_passwords.py::test_verify_wrong_password_false`
* `tests/api/test_passwords.py::test_verify_corrupt_hash_false`
* `tests/api/test_passwords.py::test_password_length_limit`
* `tests/api/test_passwords.py::test_rehash_on_verify`

**Ressourcen-Budget:** Argon2 ist absichtlich teuer (~50 ms per Verify);
Rate-Limits in M5.13 verhindern DoS.
**Geschätzte PR-Größe:** ~280 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.5 — auth-refresh-tokens

**Branch:** `feature/auth-refresh-tokens`
**Issue:** `#NNN`
**Vorbedingungen:** M5.3 gemerged
**Berührte Pfade:**
```
backend/api/security/refresh.py
backend/api/routers/auth.py                ← `/v1/auth/refresh`, `/v1/auth/logout`
backend/db/repos/refresh_tokens.py
backend/db/schema/0003_refresh_tokens.sql
tests/api/test_auth_refresh.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. **Refresh-Token-Rotation**: jedes `/refresh` invalidiert das alte
   Token, gibt neues + neues Access-Token zurück. Doppelnutzung des
   alten Tokens → Verdacht auf Diebstahl, gesamte User-Refresh-Kette
   für diesen User wird invalidiert (Pflicht-Re-Login).
2. Refresh-Token in HttpOnly-Cookie (`Secure`, `SameSite=Lax`) **plus**
   in Body bei Login (für nicht-Browser-Clients wie der Engine, sofern
   sie Refresh nutzt — engine nutzt eher Service-Token, aber API ist
   konsistent).
3. Token-TTL Refresh: 30 Tage; Tabelle `refresh_tokens` mit
   `(jti, user_id, issued_at, expires_at, revoked_at)`.
4. `/v1/auth/logout` invalidiert das aktuelle Refresh-Token + clear
   Cookie.

**Tests:**
* `tests/api/test_auth_refresh.py::test_refresh_rotates`
* `tests/api/test_auth_refresh.py::test_double_use_revokes_chain`
* `tests/api/test_auth_refresh.py::test_logout_invalidates`
* `tests/api/test_auth_refresh.py::test_expired_refresh_rejected`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.6 — http-encounters-routes

**Branch:** `feature/http-encounters-routes`
**Issue:** `#NNN`
**Vorbedingungen:** M5.3 gemerged, M1.5 gemerged
**Berührte Pfade:**
```
backend/api/routers/encounters.py
backend/api/models/encounters_api.py
tests/api/test_encounters_api.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `GET /v1/encounters?since=...&limit=...&source=...`
   * Authenticated, scope `viewer`.
   * `since`-Timestamp / `cursor`-Pagination.
   * Default-Limit 100, Max-Limit 500.
2. `POST /v1/encounters`
   * Body: `{ word, scale, source = 'user_input', context }`.
   * Validierung: Body ≤ 4 KB, `source ∈ Whitelist`.
   * Rate-Limit pro User 30/min (in M5.13 finalisiert).
   * Schreibt Encounter, publish auf NATS (Hub-Encoder kümmert sich um
     ggf. Engine-Forward).
3. **Tenant-Isolation-Test** (Pflicht): User A kann nicht User B's
   Encounters lesen — Negative-Suite.

**Tests:**
* `tests/api/test_encounters_api.py::test_post_encounter_persists`
* `tests/api/test_encounters_api.py::test_get_encounters_paginates`
* `tests/api/test_encounters_api.py::test_cannot_read_other_users_encounters`
* `tests/api/test_encounters_api.py::test_invalid_source_422`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~450 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.7 — http-snapshots-routes

**Branch:** `feature/http-snapshots-routes`
**Issue:** `#NNN`
**Vorbedingungen:** M5.3 gemerged, M1.7 gemerged, M2.6 gemerged
**Berührte Pfade:**
```
backend/api/routers/snapshots.py
tests/api/test_snapshots_api.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `POST /v1/snapshots/initiate`:
   * Body: `{ scope, expected_size_bytes, content_sha256 }`.
   * Antwort: `{ snapshot_id, upload_token, expires_at }`.
   * Idempotent über `content_sha256`.
2. `POST /v1/snapshots/{id}/complete`:
   * Authentifiziert mit `upload_token` (zusätzlich zum Bearer).
   * Antwort: vollständiges Snapshot-Manifest.
3. `GET /v1/snapshots`:
   * Listet eigene Snapshots paginated.
4. `GET /v1/snapshots/{id}`:
   * Manifest + signierte R2-URL (Lebensdauer 5 min).
5. **DELETE /v1/snapshots/{id}** (User-initiated):
   * Markiert `expired`, plant R2-Delete in der Vault-Worker-Queue.

**Tests:**
* `tests/api/test_snapshots_api.py::test_initiate_then_complete_flow`
* `tests/api/test_snapshots_api.py::test_idempotent_initiate_same_hash`
* `tests/api/test_snapshots_api.py::test_signed_url_short_lived`
* `tests/api/test_snapshots_api.py::test_delete_own_snapshot`
* `tests/api/test_snapshots_api.py::test_cannot_access_other_users_snapshot`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.8 — http-replay-timeline-v4-port

**Branch:** `feature/http-replay-timeline-v4-port`
**Issue:** `#NNN`
**Vorbedingungen:** M1.6 gemerged (Hybrid-Planner-Port)
**Berührte Pfade:**
```
backend/api/routers/replay.py
backend/api/models/replay_api.py            ← Pydantic, gegen replay_timeline_window_v4
tests/api/test_replay_timeline_v4.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. **Port aus dem Bestand 1:1**: jede Test-Suite, die in
   `tests/api/test_replay_timeline.py` und
   `tests/api/test_replay_hybrid_planner.py` existiert (terra-076 ff),
   wird hier wiederverwendet — die Erwartungen ändern sich nicht.
2. `GET /v1/replay/timeline?...` akzeptiert Parameter:
   * `q`, `q_match` (`fts`|`substring`)
   * `ranking_mode` (`chronological`|`hybrid`)
   * `ranking_policy` (`auto`|`bm25_only`|`substring_only`|`combined`)
   * `bm25_weight` (`α`), `substring_weight` (`β`)
   * Pagination
3. Antwort enthält `schema_version: "replay_timeline_window_v4"`,
   Filter-Echo, ggf. `score`-Feld pro Event, `next_after_id`,
   `effective_policy`, `score_weights`.
4. **Validierungs-Regeln** wie in terra-080:
   * α/β ∈ [0,1], beide 0 mit `combined` → 422.
   * `bm25_only` und `combined` benötigen FTS-Index → 503 wenn
     unavailable.
5. Counter (terra-082) werden bei jedem Hybrid-Hit erhöht; das
   `/v1/diagnostic` aus M5.9 spiegelt sie.

**Tests:**
* alle aus dem terra-076..082-Bestand, gegen die neue API neu verdrahtet
* zusätzlich: `tests/api/test_replay_timeline_v4.py::test_schema_version_v4`

**Ressourcen-Budget:** Replay-Query p95 < 800 ms im MVP-Hub (siehe
`00-index.md` Sektion 4 Latenz-Gate für M7).
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün; bestehende Test-Suite voll grün.

---

### M5.9 — http-diagnostic-port

**Branch:** `feature/http-diagnostic-port`
**Issue:** `#NNN`
**Vorbedingungen:** M5.8 gemerged, M4.9 gemerged
**Berührte Pfade:**
```
backend/api/routers/diagnostic.py
backend/api/diagnostics/aggregator.py
tests/api/test_diagnostic.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `GET /v1/diagnostic` (authenticated, scope `viewer` reicht für
   eigene Daten; scope `admin` für globale Sektionen).
2. Inhalt:
   * `system` — Uptime, Version, Schema-Version
   * `engine` — Status der eigenen Engine-Connection (online/idle, last_summary, lnn-State)
   * `replay_fts_ops` — Counter aus terra-078/082
   * `nats` — Consumer-Lag pro Stream
   * `litestream` — Lag in Sekunden
3. Performance: < 200 ms p95.
4. **Bestand**: `replay_fts_ops` aus terra-078/082 wird unverändert
   übernommen; das ist deren neue Heimat.

**Tests:**
* `tests/api/test_diagnostic.py::test_diagnostic_includes_engine_state`
* `tests/api/test_diagnostic.py::test_diagnostic_includes_replay_fts_ops`
* `tests/api/test_diagnostic.py::test_diagnostic_admin_only_sections`
* `tests/api/test_diagnostic.py::test_diagnostic_under_200ms`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~450 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.10 — http-admin-routes

**Branch:** `feature/http-admin-routes`
**Issue:** `#NNN`
**Vorbedingungen:** M5.3 gemerged
**Berührte Pfade:**
```
backend/api/routers/admin.py
tests/api/test_admin_api.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Alle Routen unter `/v1/admin/*`:
   * Pflicht-Scope `admin` im JWT.
   * Optional zusätzlich Cloudflare-Access-Header-Check (in M8 enforced).
2. Routen:
   * `GET /v1/admin/users` — paginiert.
   * `POST /v1/admin/users` — neuer User, generiert temporäres PW.
   * `PATCH /v1/admin/users/{id}` — `status`, `is_admin`.
   * `GET /v1/admin/connections` — aktive Engine-/Viewer-WS.
   * `POST /v1/admin/maintenance/restart-tunnel` — sanftes Cloudflared-Reload (Hub-side; Vault-side optional).
3. **Audit-Log**: jede Admin-Aktion wird in `audit_log`-Tabelle
   gespeichert (separates 0004-Migration, falls noch nicht vorhanden).

**Tests:**
* `tests/api/test_admin_api.py::test_admin_only_scope`
* `tests/api/test_admin_api.py::test_user_create_emits_audit`
* `tests/api/test_admin_api.py::test_status_update_disables_login`
* `tests/api/test_admin_api.py::test_connections_listing`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.11 — ws-viewer-channel

**Branch:** `feature/ws-viewer-channel`
**Issue:** `#NNN`
**Vorbedingungen:** M2.1 gemerged, M5.3 gemerged, M2.3 gemerged
**Berührte Pfade:**
```
backend/api/ws/viewer.py
backend/api/ws/dispatch.py                  ← bereits vorhanden, erweitern
tests/api/ws/test_viewer_channel.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `/ws/v1/viewer` Subprotocol `terra-viewer.v1`.
2. Auth via Bearer-Token im Query-Parameter `?token=...` (für Browser-
   WS, da Browser keine Custom-Header bei WS senden) **oder**
   `Authorization`-Header (für nicht-Browser-Clients).
3. Initialer Frame `session/init`.
4. Subscribe auf NATS-Subjects der eigenen `user_id`:
   `encounters.<user_id>.>` etc. → broadcast in den eigenen WS.
5. Eingehende Frames vom Client:
   * `client/pong` — Heartbeat-Response.
   * `user/encounter` — neuer Encounter aus Web-Chat.
   * `replay/control` — Pause/Play/Speed; vom Hub an die jeweils
     verbundene Engine forwardet (`server/replay_command`).
6. Bei Hub-Shutdown: `server/shutdown` mit `reconnect_after_ms`.

**Tests:**
* `tests/api/ws/test_viewer_channel.py::test_session_init_sent_first`
* `tests/api/ws/test_viewer_channel.py::test_encounter_fan_out`
* `tests/api/ws/test_viewer_channel.py::test_user_encounter_inserts`
* `tests/api/ws/test_viewer_channel.py::test_replay_control_forwarded_to_engine`

**Ressourcen-Budget:** Viewer-Connection ~2 MB RAM (NATS-Subscriber +
WS-Buffer); 50 Connections = ~100 MB.
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.12 — ws-engine-channel

**Branch:** `feature/ws-engine-channel`
**Issue:** `#NNN`
**Vorbedingungen:** M2.4 gemerged, M5.3 gemerged
**Berührte Pfade:**
```
backend/api/ws/engine.py                  ← bereits vorhanden, hier finalisiert
tests/api/ws/test_engine_channel_full.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. M2.4-Skelett wird zur produktiven Implementierung erweitert:
   * Persistierung von `engine_connections`-Rows (online/idle/closed).
   * Forwarding von `engine/encounter` → DB + NATS publish.
   * Forwarding von `engine/summary` → cache (Dragonfly-Free, falls
     verwendbar; sonst SQLite-Memory-Cache `engine_summary_cache`).
   * Forwarding von `engine/snapshot` → M2.6-Flow auslösen.
   * Heartbeat: alle 10 s `server/heartbeat`. 30 s ohne Pong → idle.
2. **Singleton-Engine-Regel** vollständig durchgesetzt.
3. **Backpressure**: wenn DB-Schreibrate gegen Limits stößt, schickt
   Hub `server/backpressure` an Engine — Engine drosselt Encounter-
   Rate.

**Tests:**
* `tests/api/ws/test_engine_channel_full.py::test_engine_connection_lifecycle`
* `tests/api/ws/test_engine_channel_full.py::test_encounter_persists_and_publishes`
* `tests/api/ws/test_engine_channel_full.py::test_summary_cache_updates`
* `tests/api/ws/test_engine_channel_full.py::test_singleton_kicks_old`
* `tests/api/ws/test_engine_channel_full.py::test_backpressure_signal`

**Ressourcen-Budget:** Engine-Connection ~3 MB RAM; 10 = ~30 MB.
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.13 — rate-limits-and-quotas

**Branch:** `feature/rate-limits-and-quotas`
**Issue:** `#NNN`
**Vorbedingungen:** M5.6, M5.7, M5.11, M5.12 gemerged
**Berührte Pfade:**
```
backend/api/middleware/ratelimit.py
backend/api/quotas.py
tests/api/test_ratelimit.py
tests/api/test_quotas.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Token-Bucket-Implementierung; Bucket-State im Memory pro
   uvicorn-Worker (1 Worker, also kein Cross-Worker-Issue).
2. **Defaults** wie in `architecture/mvp.md` §12:
   * 600 req/min total per Token
   * 60 req/min auf Auth-Routes per IP
   * 30 Encounters/min per User
   * 1 Snapshot-Initiate/30 s per User
   * 60 Replay-Queries/min per User
3. Bei Hit: HTTP 429 mit `Retry-After`-Header.
4. Hard-Quotas (M-Limits):
   * Snapshot-Volumen-Sum ≤ 1 GB → bei Initiate Check.
   * Anzahl gehaltener Snapshots ≤ 50 → ältester wird beim Anlegen
     verworfen.
5. **Konfigurierbar** via `settings.py`; Tests prüfen Override.

**Tests:**
* `tests/api/test_ratelimit.py::test_burst_then_throttle`
* `tests/api/test_ratelimit.py::test_retry_after_header`
* `tests/api/test_quotas.py::test_snapshot_volume_quota`
* `tests/api/test_quotas.py::test_snapshot_count_eviction`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M5.14 — openapi-freeze-v1

**Branch:** `docs/openapi-freeze-v1`
**Issue:** `#NNN`
**Vorbedingungen:** M5.1 – M5.13 gemerged
**Berührte Pfade:**
```
docs/contracts/openapi/v1.json             ← exportiertes Schema
backend/api/openapi_meta.py                 ← Metadata-Konfig
tests/contracts/test_openapi_freeze.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. `make openapi-export` schreibt `docs/contracts/openapi/v1.json`
   reproducibly (sortierte Keys, stabiler Ordering).
2. CI-Job `openapi-diff`:
   * Vergleicht aktuelle OpenAPI mit `docs/contracts/openapi/v1.json`.
   * Bricht bei **non-additiven** Änderungen (entfernte Felder,
     entfernte Endpoints, Typ-Änderungen).
3. Doku ergänzt um:
   * `docs/contracts/openapi/README.md` mit Versions-Strategie.
   * Hinweis: `v2.json` für M2.0 wird parallel gepflegt, nicht
     überschrieben.

**Tests:**
* `tests/contracts/test_openapi_freeze.py::test_export_deterministic`
* `tests/contracts/test_openapi_freeze.py::test_no_breaking_change_against_baseline`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~300 Lines diff
**Fertig wenn:** AC + CI grün; OpenAPI-Diff-Gate ab dieser Phase
Pflicht.

---

## 5. Phasen-Gate

M5 gilt als grün, wenn:

1. M5.1 – M5.14 in `00-index.md` auf `[x]`.
2. End-to-End-Test: User registriert (per Admin), loggt sich ein, baut
   Engine-WS auf, Engine schickt Encounters → werden in Replay-Timeline
   sichtbar (HTTP-Query) → werden im `/v1/diagnostic` reflektiert.
3. OpenAPI-Diff-Gate ist aktiv und grün.
4. Tag `v0.6.0` gepusht.

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M5 noch nicht eröffnet*
