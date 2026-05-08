# `protocols/replay-contract.md` — Replay-API-Vertrag (v4 frozen)

> **Zweck.** Vollständige, eingefrorene Spezifikation der
> Replay-Timeline-API (`/api/v1/replay/window`) — sowohl HTTP-Form
> als auch SQL-Vertrags­form, kompatibel mit dem bestehenden
> `replay_timeline_window_v4`-Schema.
>
> **Geltung.** Eingefroren ab v0.5.x (M5). Jede Änderung verlangt
> Major-Bump (v2.0.0) **oder** additive Felder mit Default = `null`.
>
> **Single-Source-of-Truth** für `backend/db/replay_query.py`,
> `frontend/src/replay/*` und alle Tests gegen die Replay-Schicht.

---

## Inhalt

1. [Zweck und Ziel-Performance](#1-zweck-und-ziel-performance)
2. [HTTP-Endpoint](#2-http-endpoint)
3. [Query-Parameter (kanonisch)](#3-query-parameter-kanonisch)
4. [Response-Schema](#4-response-schema)
5. [Ranking-Modes & Effective-Policy-Resolver](#5-ranking-modes--effective-policy-resolver)
6. [Hybrid-Combined-Score (`F.REPLAY.HYBRID.001`)](#6-hybrid-combined-score-freplayhybrid001)
7. [SQL-Vertrag (Bind-Parameter, Tie-Break)](#7-sql-vertrag-bind-parameter-tie-break)
8. [Pagination & Cursor-Form](#8-pagination--cursor-form)
9. [Cache-Verhalten (`kv_cache.scope='replay.window'`)](#9-cache-verhalten-kv_cachescopereplaywindow)
10. [Fehlerantworten](#10-fehlerantworten)
11. [Beispiele](#11-beispiele)
12. [Test-Vektor-Liste](#12-test-vektor-liste)

---

## 1. Zweck und Ziel-Performance

* **Ziel** — exakt eine Server-Antwort, die das Frontend für die
  Replay-Timeline rendern kann; deterministisches Ranking; FTS-
  optionale Hybrid-Suche; Pagination ohne State-Server-Side.
* **Performance-Vertrag** — p95 < 800 ms, p99 < 1500 ms, gemessen am
  Hub auf VM-A bei kalter SQLite-Cache-Phase (M7.8 latency gate).

---

## 2. HTTP-Endpoint

* **Methode**: `GET /api/v1/replay/window`
* **Auth**: Bearer-Cookie (Access-Token) erforderlich.
* **Permissions**: `user`-Rolle reicht; Admin-Bypass nicht erlaubt
  (Admin liest seine eigene Timeline, nicht fremde).
* **CORS**: nicht relevant (gleicher Origin via Cloudflare-Tunnel).

---

## 3. Query-Parameter (kanonisch)

Alle Parameter sind URL-encoded. Pflicht (`Pflicht`) / Optional
(`Optional`).

| Param          | Typ   | Default     | Pflicht?   | Beschreibung |
|----------------|-------|-------------|------------|--------------|
| `from_ms`      | int   | now-7d      | Optional   | Untere Zeitgrenze (inklusiv). |
| `to_ms`        | int   | now         | Optional   | Obere Zeitgrenze (exklusiv). |
| `event_kind`   | enum  | `*`          | Optional   | Komma-Liste: `encounter,tier_emerge,well_birth,well_dormant,kg_edge_change,summary,*` |
| `q`            | str   | leer         | Optional   | Volltext-Query (max. 256 Zeichen). |
| `q_match`      | enum  | `auto`       | Optional   | `exact` (FTS5 Phrase), `prefix` (FTS5 prefix), `auto` (Heuristik), `disabled` (kein FTS) |
| `ranking_mode` | enum  | `auto`       | Optional   | `relevance`, `recency`, `auto` |
| `ranking_policy`| enum | `auto`       | Optional   | `bm25_only`, `substring_only`, `combined`, `auto` |
| `alpha`        | float | `0.6`        | Optional   | Gewicht `bm25 / (bm25+1)`-Term im Combined-Score (0..1). |
| `beta`         | float | `0.4`        | Optional   | Gewicht `hits/3`-Term (0..1). |
| `page_size`    | int   | `50`         | Optional   | 1..200. |
| `cursor`       | str   | leer         | Optional   | Opaker Cursor (siehe §8). |
| `density`      | enum  | `off`        | Optional   | `off`, `bin5min`, `bin1h`, `bin1d` (M7.5+) |
| `lang`         | str   | aus JWT       | Optional   | Override; wird in v1.0 nur an Frontend zurückgegeben. |

**Validation:**

* `from_ms ≤ to_ms`; sonst `400 invalid_window`.
* `to_ms - from_ms ≤ 90 d`; sonst `400 window_too_large`.
* `alpha + beta ≤ 1.5` Empfehlung, kein Hard-Limit (Score wird
  intern nicht normalisiert).
* `event_kind`-Liste: nur erlaubte Werte; `*` darf nicht mit anderen
  kombiniert werden.

---

## 4. Response-Schema

```json
{
  "window": {
    "from_ms": 1714800000000,
    "to_ms":   1714900000000,
    "event_kind": ["encounter","tier_emerge"],
    "q": "wahrnehmung",
    "q_match_used": "exact",
    "ranking_mode_used":   "relevance",
    "ranking_policy_used": "combined",
    "alpha_used": 0.6,
    "beta_used":  0.4
  },
  "events": [
    {
      "id": 1893421,
      "ts_ms": 1714900250000,
      "event_kind": "tier_emerge",
      "word": null,
      "meta": { "...": "..." },
      "score": {
        "bm25": 1.83,
        "hits": 2,
        "combined": 0.732,
        "tier_break_id": 1893421
      }
    }
  ],
  "page": {
    "size": 50,
    "next_cursor": "eyJ0aWVfaWQiOjE4OTM0MjEsInRzIjoxNzE0OTAwMjUwMDAwfQ==",
    "prev_cursor": null,
    "has_more": true
  },
  "density": null,
  "schema_version": 4
}
```

**Pflichtfelder pro Event**: `id`, `ts_ms`, `event_kind`, `meta`,
`score.tier_break_id`. Andere `score`-Felder dürfen `null` sein, wenn
der Mode sie nicht berechnet (`ranking_policy=substring_only` →
`bm25=null`, `combined=null`).

---

## 5. Ranking-Modes & Effective-Policy-Resolver

```python
def resolve_effective_ranking_policy(req) -> str:
    if req.ranking_policy != "auto":
        return req.ranking_policy
    if req.q and fts_available_for_user(req.user_id):
        return "combined"
    if req.q:
        return "substring_only"
    return "recency"  # virtuelle Policy: kein Score, nur ts_ms DESC
```

```python
def resolve_effective_ranking_mode(req, policy_used) -> str:
    if req.ranking_mode != "auto":
        return req.ranking_mode
    if policy_used in ("combined","bm25_only","substring_only"):
        return "relevance"
    return "recency"
```

```python
def resolve_effective_q_match(req) -> str:
    if req.q_match != "auto":
        return req.q_match
    if not req.q:
        return "disabled"
    return "exact" if " " in req.q.strip() else "prefix"
```

> **Vertrag.** Resolver sind in **Bestand** (`backend/db/events.py`)
> bereits implementiert (`resolve_effective_*`). Greenfield ist
> bit-identisch. Test­vektoren §12 bestätigen.

---

## 6. Hybrid-Combined-Score (`F.REPLAY.HYBRID.001`)

Berechnung pro Treffer:

```
bm25_norm   = bm25 / (bm25 + 1)             # NULL-safe: NULL → 0
hits_norm   = hits / 3                       # NULL → 0
combined    = alpha * bm25_norm + beta * hits_norm
```

Sortierung: `combined DESC, ts_ms DESC, id ASC` (Tie-Break-Reihenfolge
ist im Vertrag eingefroren — Tests verlassen sich darauf).

---

## 7. SQL-Vertrag (Bind-Parameter, Tie-Break)

### 7.1 Statement-Skeleton

```sql
WITH
  fts_hits AS (
    SELECT rowid AS id, bm25(replay_events_fts) AS bm25
    FROM replay_events_fts
    WHERE replay_events_fts MATCH :fts_query
  ),
  base AS (
    SELECT re.id, re.ts_ms, re.event_kind, re.word,
           re.meta_json,
           IFNULL(fh.bm25, NULL) AS bm25,
           CASE WHEN :q IS NULL OR :q = '' THEN 0
                ELSE
                  (CASE WHEN re.word LIKE '%' || :q || '%' THEN 1 ELSE 0 END)
                + (CASE WHEN json_extract(re.meta_json,'$.text') LIKE '%' || :q || '%' THEN 1 ELSE 0 END)
                + (CASE WHEN re.word IS :q THEN 1 ELSE 0 END)
           END AS hits
    FROM replay_events AS re
    LEFT JOIN fts_hits AS fh ON fh.id = re.id
    WHERE re.user_id = :user_id
      AND re.ts_ms >= :from_ms
      AND re.ts_ms <  :to_ms
      AND ( :event_kind_csv = '*'
            OR re.event_kind IN (SELECT value FROM json_each(:event_kind_json)) )
  ),
  scored AS (
    SELECT base.*,
           CASE :policy
             WHEN 'bm25_only'      THEN IFNULL(bm25/(bm25+1), 0.0)
             WHEN 'substring_only' THEN (hits/3.0)
             WHEN 'combined'       THEN :alpha * IFNULL(bm25/(bm25+1), 0.0)
                                       + :beta  * (hits/3.0)
             ELSE NULL
           END AS combined
    FROM base
  )
SELECT id, ts_ms, event_kind, word, meta_json, bm25, hits, combined
FROM scored
WHERE :cursor_filter      -- entwurfshalber leer; siehe §8
ORDER BY
  CASE :mode WHEN 'relevance' THEN combined END DESC NULLS LAST,
  ts_ms DESC,
  id ASC
LIMIT :page_size + 1;
```

> **Hinweis.** Genau diese Form (mit `IFNULL`-Schutz und `NULLS LAST`)
> ist im Bestand `backend/db/events.py` implementiert. Greenfield
> portiert sie verbatim nach `backend/db/replay_query.py`.

### 7.2 Bind-Parameter

* `:user_id`     — JWT `sub`.
* `:from_ms`, `:to_ms` — Validierte Werte aus §3.
* `:event_kind_csv`, `:event_kind_json` — Beide aus Eingabe abgeleitet
  (`*` ↔ Liste `[]`).
* `:q`, `:fts_query` — `q` ist Klartext, `fts_query` ist FTS5-
  formatiert (`"…"` für `exact`, `…*` für `prefix`).
* `:policy`, `:mode` — aus Resolvern.
* `:alpha`, `:beta` — aus Eingabe (Defaults).
* `:page_size` — limit + 1 (für `has_more`-Detektion).

### 7.3 FTS5-Quoting

* `q_match=exact`: `"<sanitized>"`-Form, alle `"` entfernt, alle
  reservierten FTS5-Operatoren (`*`, `:`, `+`, `^`, `(`, `)`)
  entfernt.
* `q_match=prefix`: einzelnes Token, `<sanitized>*`.
* `q_match=disabled`: kein `MATCH`, leere `fts_hits`-Tabelle.

---

## 8. Pagination & Cursor-Form

* **Cursor** ist ein base64-kodiertes JSON `{ "ts": int, "id": int }`,
  exakt das Tie-Break-Tupel der letzten Zeile.
* `cursor_filter` (§7.1) wird zu:

  ```sql
  AND (ts_ms < :cur_ts OR (ts_ms = :cur_ts AND id > :cur_id))
  ```
* `prev_cursor` wird in v1.0 nicht erzeugt (kein Backward-Pagination
  in MVP). Frontend cached die zuletzt geladenen Pages.
* `has_more` wird ermittelt durch `len(results) == page_size + 1`.

**Stabilität:** Cursor ist deterministisch und kann zwischen Sessions
benutzt werden. Cursor-Validierung lehnt manipulierte Cursor mit
`400 invalid_cursor` ab.

---

## 9. Cache-Verhalten (`kv_cache.scope='replay.window'`)

* **Cache-Key**: SHA-256(`user_id || from_ms || to_ms || event_kind ||
  q || q_match_used || policy_used || mode_used || alpha || beta ||
  page_size || cursor`).
* **TTL**: 30 s; bei `q is None` → 60 s; bei `event_kind=*` ohne `q`
  → 120 s.
* **Größe**: max 32 KiB pro Eintrag (sonst Skip-Cache + Counter).
* **Invalidation**: jeder `INSERT INTO replay_events` durch den NATS-
  Subscriber löscht alle Cache-Einträge mit `user_id`-Prefix.

---

## 10. Fehlerantworten

| Code | `error_class`                | Auslöser                                  |
|------|------------------------------|-------------------------------------------|
| 400  | `invalid_window`              | `from_ms > to_ms`                          |
| 400  | `window_too_large`            | Fenster > 90 d                             |
| 400  | `invalid_event_kind`          | unbekannter Wert in Liste                  |
| 400  | `invalid_cursor`              | base64-/JSON-Decode-Fehler oder Schemafail |
| 400  | `invalid_q_too_long`          | `q` > 256                                  |
| 401  | `unauthenticated`             | kein/abgelaufener Cookie                  |
| 403  | `forbidden`                   | (z.B. Admin-Pfad ohne Rolle)               |
| 429  | `rate_limited`                | `quota_usage` block                        |
| 503  | `db_unavailable`              | SQLite-Lock-Timeout / WAL-Stall            |

Antwort­körper:

```json
{
  "error_class": "invalid_window",
  "message": "from_ms must be ≤ to_ms",
  "request_id": "req_a1b2c3"
}
```

---

## 11. Beispiele

### 11.1 Combined-Hybrid (auto)

**Request**:

```
GET /api/v1/replay/window?from_ms=1714800000000&to_ms=1714900000000
                         &q=wahrnehmung&page_size=20
```

**Effektive Resolver**:

* `q_match_used = "prefix"` (Single-Token)
* `policy_used = "combined"`
* `mode_used = "relevance"`
* `alpha=0.6, beta=0.4` (Defaults)

### 11.2 Recency only (no q)

**Request**:

```
GET /api/v1/replay/window?from_ms=1714800000000&to_ms=1714900000000&page_size=50
```

**Effektive Resolver**:

* `q_match_used = "disabled"`
* `policy_used = "auto"` → bei leerem `q` → `recency`-Branch
* `mode_used = "recency"`

Score-Felder pro Event: alle `null`; Reihenfolge `ts_ms DESC`.

### 11.3 Substring only (FTS deaktiviert)

**Request**:

```
GET /api/v1/replay/window?q=wahrn&q_match=disabled&ranking_policy=substring_only
```

* FTS-Branch leer.
* `combined = hits/3.0`.
* `mode_used = "relevance"`.

---

## 12. Test-Vektor-Liste

Diese Vektoren werden **wortwörtlich** in Pytest-Suites geprüft:

| ID  | Eingabe (Auszug)                                        | Erwartetes `q_match_used` / `policy_used` / `mode_used` |
|-----|---------------------------------------------------------|----------------------------------------------------------|
| V1  | `q=wahrnehmung`                                         | `prefix` / `combined` / `relevance` |
| V2  | `q=wahrnehmung als idee`                                | `exact` / `combined` / `relevance` |
| V3  | (kein `q`)                                              | `disabled` / `recency` / `recency` |
| V4  | `q=wahrn`, `ranking_policy=bm25_only`                    | `prefix` / `bm25_only` / `relevance` |
| V5  | `q=wahrn`, `q_match=disabled`, `ranking_policy=substring_only` | `disabled` / `substring_only` / `relevance` |
| V6  | `q=wahrn`, `ranking_mode=recency`                        | `prefix` / `combined` / `recency` |
| V7  | `q=wahrn`, `alpha=0.9`, `beta=0.1`                       | wie V1, aber `alpha_used=0.9` |
| V8  | `event_kind=encounter,tier_emerge`                      | normale Filterung; `policy_used=recency` (kein `q`) |
| V9  | `from_ms=now`, `to_ms=now-1h`                            | 400 `invalid_window` |
| V10 | `q=` 257 Zeichen                                         | 400 `invalid_q_too_long` |

---

*Stand: 2026-05-08 · Greenfield-Initial · eingefroren ab v0.5.x ·
referenziert aus M5, M7, `formulas/registry.md F.REPLAY.HYBRID.*`.*
