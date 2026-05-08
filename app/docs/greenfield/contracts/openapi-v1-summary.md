# `contracts/openapi-v1-summary.md` — OpenAPI v1 (Zusammenfassung)

> **Zweck.** Lebendige, lesbare Zusammenfassung des `/api/v1/*`-
> Vertrags. Die maschinen­lesbare Quelle wird in M5.14 unter
> `docs/contracts/openapi/v1.json` eingefroren; dieses Dokument
> spiegelt sie in lesbarer Form für Reviewer und Frontend-Autoren.

---

## Inhalt

1. [Versionierung & Pfade](#1-versionierung--pfade)
2. [Auth](#2-auth)
3. [Me / DSGVO](#3-me--dsgvo)
4. [Encounters](#4-encounters)
5. [Replay](#5-replay)
6. [Snapshots](#6-snapshots)
7. [Engine](#7-engine)
8. [Diagnostic](#8-diagnostic)
9. [Admin](#9-admin)
10. [WebSocket-Pfade](#10-websocket-pfade)
11. [Allgemeine Fehlerantworten](#11-allgemeine-fehlerantworten)
12. [Pagination & Cursor](#12-pagination--cursor)
13. [Rate-Limit-Header](#13-rate-limit-header)
14. [Versionspflege](#14-versionspflege)

---

## 1. Versionierung & Pfade

* **Basis-URL** (Public, Cloudflare-Tunnel-vermittelt):
  `https://terra.example/api/v1`
* **Engine-Edge** (Public, separater Hostname):
  `wss://engine.terra.example/ws/v1/engine`
* **Admin-Edge** (intern, IP-allow-list + Tunnel):
  `https://admin.terra.example/api/v1/admin/*`
* **Schema-Datei**: `docs/contracts/openapi/v1.json` (in M5.14).
* **Diff-Policy**:
  * Additive Felder ohne Breaking-Effekt → erlaubt.
  * Entfernen/Umbenennen von Feldern → Major-Bump (`v2`).
  * Pflichtfelder hinzufügen → Major-Bump.

---

## 2. Auth

### 2.1 `POST /api/v1/auth/register`

* **Body**: `{ email, password, display_name, lang }`
* **Validation**: email RFC 5322, password ≥ 12 Zeichen + Common-
  Password-Liste, lang ∈ {de,en}.
* **Response 201**: `{ user_id, email, display_name }`, Cookies
  `access_token` (15 min) und `refresh_token` (30 d) gesetzt.
* **Errors**: `400 invalid_email`, `400 weak_password`,
  `409 email_taken`, `429 rate_limited`.

### 2.2 `POST /api/v1/auth/login`

* **Body**: `{ email, password }`
* **Response 200**: `{ user_id, email, display_name, role }`,
  Cookies gesetzt.
* **Errors**: `401 invalid_credentials`, `403 account_disabled`,
  `429 rate_limited`.

### 2.3 `POST /api/v1/auth/refresh`

* **Cookie-only** (kein Body); rotiert Refresh-Token.
* **Response 200**: `{ ok: true }`.
* **Errors**: `401 invalid_refresh_token`, `401 refresh_reuse_detected`
  (Token-Familie wird revoked).

### 2.4 `POST /api/v1/auth/logout`

* Setzt beide Cookies auf leer + `Max-Age=0`.
* **Response 200**: `{ ok: true }`.

### 2.5 `GET /api/v1/auth/jwks.json`

* Liefert aktive JWK-Liste (Public-Keys).
* **Response 200**: `{ keys: [...] }`.

---

## 3. Me / DSGVO

### 3.1 `GET /api/v1/me`

* **Response 200**: `{ user_id, email, display_name, lang, role,
  created_at_ms, updated_at_ms }`.

### 3.2 `PATCH /api/v1/me`

* **Body**: `{ display_name?, lang?, password? }`.
* **Response 200**: aktualisierte Felder.

### 3.3 `GET /api/v1/me/export`

* DSGVO Art. 15 Auskunft.
* **Response 200**: JSON-Bundle mit `users`, `encounters`,
  `replay_events`, `snapshots`-Manifeste, `audit_log` (eigene
  Aktionen).
* **Performance**: Streaming-Response (`Content-Type: application/x-ndjson`).

### 3.4 `POST /api/v1/me/delete`

* DSGVO Art. 17 Löschung.
* **Body**: `{ confirm: "I_KNOW_WHAT_I_DO" }`.
* **Response 202**: `{ delete_job_id }`.
* Wirkung: User wird sofort `is_disabled=1`, Hard-Delete läuft
  als Hintergrund-Job (Cascade + R2-Purge).

---

## 4. Encounters

### 4.1 `POST /api/v1/encounters`

* **Body**: `{ word, lang?, channel? = "chat", payload? }`.
* **Response 201**: `{ id, ts_ms, ... }`.
* **Errors**: `400 invalid_word`, `429 rate_limited`.

### 4.2 `GET /api/v1/encounters`

* **Query**: `from_ms?, to_ms?, q?, page_size?, cursor?`.
* **Response 200**: `{ events: [...], page: {...} }`.

---

## 5. Replay

Detail: siehe `protocols/replay-contract.md`.

### 5.1 `GET /api/v1/replay/window`

* siehe `protocols/replay-contract.md` §2–§4.

### 5.2 `GET /api/v1/replay/density` (M7.5+)

* **Query**: `from_ms, to_ms, bin = "5min"|"1h"|"1d"`.
* **Response 200**: `{ bins: [{ts_ms, count}, ...] }`.

---

## 6. Snapshots

### 6.1 `GET /api/v1/snapshots`

* **Response 200**: `{ snapshots: [{ id, taken_at_ms, bytes,
  is_active, retention_class }, ...] }`.

### 6.2 `GET /api/v1/snapshots/{id}/url`

* Liefert presigned R2-URL (gültig 5 min).
* **Response 200**: `{ url, expires_at_ms }`.

### 6.3 `PUT /api/v1/snapshots/raw` (Engine-only, mTLS Pflicht)

* siehe `protocols/snapshot.md` §4.

---

## 7. Engine

### 7.1 `POST /api/v1/engine/enroll` (Admin-only in v1.0)

* **Body**: `{ user_id, engine_id, csr_pem, validity_days }`.
* **Response 200**: `{ cert_pem, thumbprint }`.

### 7.2 `GET /api/v1/engine/registrations`

* **Response 200**: `{ engines: [{ engine_id, cert_thumbprint,
  is_active, last_connected_ms }, ...] }`.

### 7.3 `DELETE /api/v1/engine/registrations/{engine_id}` (Admin)

* setzt `is_active=0`, deaktiviert Cert-Pfad.
* **Response 204**.

---

## 8. Diagnostic

### 8.1 `GET /health`

* Public; keine Auth.
* **Response 200**: `{ ok: true, version, db_ok, nats_ok,
  litestream_lag_ms }`.

### 8.2 `GET /api/v1/diagnostic`

* User-Auth nötig.
* **Response 200**: `{ engine_status, fts_count, nats_lag_ms,
  litestream_lag_ms, replay_p95_ms, ws_active }`.

### 8.3 `GET /api/v1/version`

* **Response 200**: `{ version, build_id, schema_hash, formula_registry_hash }`.

---

## 9. Admin

Nur für `is_admin=1`-User. Alle Endpoints schreiben Audit-Einträge.

### 9.1 `GET /api/v1/admin/users`

* `q?, page_size?, cursor?` → `{ users: [...], page: {...} }`.

### 9.2 `POST /api/v1/admin/users/{user_id}/disable`

* setzt `is_disabled=1`, revoked alle Refresh-Tokens.

### 9.3 `POST /api/v1/admin/users/{user_id}/quota`

* **Body**: `{ key, value }`.
* setzt Quota-Override (siehe `runbooks/operations.md` §8).

### 9.4 `GET /api/v1/admin/audit`

* gefilterter Audit-Log-Auszug.

---

## 10. WebSocket-Pfade

### 10.1 `WSS /ws/v1/viewer`

* **Auth**: Cookie (Access-JWT).
* **Subprotokoll**: `terra.viewer.v1`.
* **Server → Client Frames**:
  * `welcome { user_id, server_version, ts_ms }`
  * `event { event_kind, ts_ms, ... }` (gefilterter `replay_events`-
    Push)
  * `summary { ... }`
  * `error { code, message }`
* **Client → Server Frames**:
  * `subscribe { engine_ids?, event_kinds? }`
  * `ping { ts_ms }`

### 10.2 `WSS /ws/v1/engine`

* **Auth**: Cookie (Access-JWT, `scope=engine`) **+** mTLS.
* **Subprotokoll**: `terra.engine.v1`.
* **Engine → Server Frames**: `engine/hello`,
  `engine/encounter`, `engine/tier_emerge`, `engine/well_birth`,
  `engine/well_dormant`, `engine/kg_edge_change`, `engine/summary`,
  `engine/heartbeat`, `engine/snapshot/start`,
  `engine/snapshot/finalize`.
* **Server → Engine Frames**: `server/welcome`,
  `server/snapshot/ack`, `server/snapshot/done`,
  `server/error`, `server/restart_request`.

JSON-Schemas pro Frame: `docs/contracts/event-log/v1/<frame>.json`.

---

## 11. Allgemeine Fehlerantworten

```json
{
  "error_class": "<snake_case>",
  "message": "<human readable>",
  "request_id": "req_..."
}
```

Codes:

* `400 invalid_*` — Validierungs-Fehler.
* `401 unauthenticated` — Cookie fehlt/abgelaufen.
* `403 forbidden` — Rollen-/Scope-Verstoß.
* `404 not_found` — Ressource existiert nicht.
* `409 conflict` — z.B. `email_taken`.
* `429 rate_limited` — Quota erschöpft (`Retry-After`-Header).
* `500 internal_error` — un­erwartet; Audit-Eintrag mit
  `request_id`.
* `503 db_unavailable` / `service_unavailable` — temporär
  (z.B. `Retry-After: 5`).

---

## 12. Pagination & Cursor

* **Cursor** opaker base64-JSON (siehe `protocols/replay-contract.md`
  §8).
* Default `page_size = 50`, max `200`.
* Antwort: `{ next_cursor, prev_cursor?, has_more }`.
* Stateless (Cursor enthält alle Kriterien).

---

## 13. Rate-Limit-Header

Bei jeder limitierten Antwort:

* `X-RateLimit-Bucket` — `login`, `replay`, `snapshot.upload`, ...
* `X-RateLimit-Remaining` — verbleibende Anfragen im Fenster.
* `X-RateLimit-Reset` — UNIX-Sekunden für Reset.
* `Retry-After` — Sekunden bei `429`.

---

## 14. Versionspflege

* **OpenAPI-Diff-Workflow** (CI):
  * Vergleicht `docs/contracts/openapi/v1.json` mit der vom
    Code generierten Live-Spec.
  * Blockiert Merge bei nicht­additiven Änderungen.
* **Frontend-Codegen** (M6+):
  * `pnpm gen:api` erzeugt typed Client aus OpenAPI v1.
* **Test-Pflicht**:
  * Pytest-Suite `tests/contracts/test_openapi_freeze.py` lädt
    `v1.json` + Live-Spec, vergleicht Pfade/Felder.

---

*Stand: 2026-05-08 · Greenfield-Initial · maschinen­lesbare
Single-Source-of-Truth folgt in M5.14.*
