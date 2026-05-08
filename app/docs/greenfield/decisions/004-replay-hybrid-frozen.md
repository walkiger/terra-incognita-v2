# ADR-004 — Replay-Hybrid-Score (`F.REPLAY.HYBRID.001`) eingefroren

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `protocols/replay-contract.md`,
  `formulas/registry.md F.REPLAY.HYBRID.001`,
  Bestand `backend/db/events.py`.

## Context

Der Replay-Pfad `/api/v1/replay/window` hat im Bestand
(`replay_timeline_window_v4`) eine sorgfältig austarierte
Hybrid-Ranking-Form: BM25 (FTS) plus Substring-Hits, linear
kombiniert mit `(α, β)`-Gewichten. Diese Form wurde in mehreren
Iterationen empirisch justiert.

Greenfield könnte versucht sein, diese Form „neu zu denken". Die
Risiken:

* Bestand-Tests (V1–V10 in `protocols/replay-contract.md` §12)
  müssten umgeschrieben werden.
* Frontend-Caching (`replay_timeline_window`-Hashing) bricht.
* Empirische Justierung wäre verloren.

## Decision

Die Form ist **eingefroren** und in `formulas/registry.md` als
`F.REPLAY.HYBRID.001` mit Status `implemented` markiert. Greenfield
portiert die Bestand-Implementierung aus `backend/db/events.py`
verbatim nach `backend/db/replay_query.py`. Tie-Break-Reihenfolge,
NULL-Behandlung, Effective-Resolver-Logik bleiben bit-identisch.

Erlaubte Erweiterungen ohne Major-Bump:

* Zusätzliche `ranking_policy`-Werte (z.B. `bm25_only_with_decay`),
  solange `auto`-Resolver nicht für sie aufgelöst wird.
* Zusätzliche Score-Komponenten in `score{}` der Antwort, solange
  `combined`-Feld unverändert berechnet wird.

## Consequences

* **Positiv:**
  * Tests V1–V10 bleiben gültig.
  * Frontend-Caching bleibt deterministisch.
  * v1→v2-Migration kann denselben Score in ClickHouse +
    OpenSearch nachbauen, ohne UX-Bruch.
* **Negativ:**
  * Falls eine bessere Form gefunden wird, kostet die Einführung
    eine Major-Bump (v2.0 OpenAPI).
* **Neutral:**
  * Die `(α, β)`-Defaults (`0.6, 0.4`) sind bei Bedarf per
    Feature-Flag justierbar, ohne Schema-Bruch.

## Alternatives Considered

* **Reranker (Cross-Encoder)**: zu schwer für 1 GB-Hub; in v2.0
  als optionaler `ranking_policy=ml_rerank` denkbar.
* **TF-IDF mit Cosine-Similarity**: adäquat, aber Mehraufwand
  ohne sichtbaren Vorteil gegenüber BM25.
* **Reine Recency-Sortierung**: zu reduktiv; Replay verliert
  Such-Charakter.

## References

* `protocols/replay-contract.md`
* `formulas/derivations.md` §7
* Bestand: `backend/db/events.py::query_events_timeline_page`

---

*Greenfield-Initial-ADR.*
