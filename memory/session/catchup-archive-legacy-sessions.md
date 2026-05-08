# catchup-archive — Legacy Session-Protokoll (archiviert)

> Aus **`catchup.md`** ausgelagert, damit die aktive Session-Datei klein bleibt.
> Neue Einträge immer im **Root-`catchup.md`**; bei Bedarf ältere **terra-*** hier suchen.

---

## terra-082 — Replay `replay_fts_ops` Per‑Policy Counters (2026-05-08)

### Kurz

- **Code:** `backend/db/replay_fts_metrics.py` — drei neue Zähler (`hybrid_bm25_only_total`, `hybrid_substring_only_total`, `hybrid_combined_total`) + `record_hybrid_request(policy)`; `routes.py` inkrementiert pro **`GET /replay/timeline`** Hybrid‑Request mit aufgelöster Policy genau einmal.
- **Tests:** `tests/db/test_replay_fts_metrics.py` (3 neue Cases: per‑policy increment unit, diagnostic field presence, API‑level Increment‑Verifikation). Suite **495 passed**.
- **Docs:** OPS §2.3, `archive/legacy-docs/Implementierung.backend.api.md`.
- **PR:** [#93](https://github.com/walkiger/terra-incognita/pull/93)

### Nächstes

- Replay‑Aggregate‑Density (`docs/PRODUCT_REPLAY_AND_TIMELINE.md`) oder BL‑DSGN‑05 Pre‑Boot/Restart‑Truth (siehe `docs/PREBOOT_PLAN.md`).

---

## terra-081 — Replay Hybrid‑Planner UI (`ReplayPage.jsx`) (2026-05-08)

### Kurz

- **Frontend:** Im Hybrid‑Modus Policy‑Select (`auto` | `bm25_only` | `substring_only` | `combined`) und α/β‑Number‑Inputs (Default 0.5/0.5, Step 0.05), nur sichtbar wenn `q` und `ranking_mode=hybrid`; α/β nur bei `combined`. `auto` sendet **kein** `ranking_policy` (Server‑v3‑Defaults bleiben aktiv). Filter‑Echo zeigt aufgelöstes `policy` + `score_weights`.
- **Docs:** `docs/PRODUCT_REPLAY_AND_TIMELINE.md` F.3.
- **PR:** [#92](https://github.com/walkiger/terra-incognita/pull/92)

---

## terra-080 — Replay Hybrid‑Planner Backend `replay_timeline_window_v4` (2026-05-08)

### Kurz

- **Code:** `backend/db/events.py` — `ReplayRankingPolicy` literal + `resolve_effective_ranking_policy()`; `query_events_timeline_page` und `memory_events_matching` mit drei Policies (`bm25_only`, `substring_only`, `combined`); `combined` SQL `(ILIKE ∪ BM25 IS NOT NULL)` + Score `α·bm25/(bm25+1) + β·hits/3` (Tie‑break `id ASC`, NULL → 0). RAM‑Parität via Token‑Overlap‑Proxy.
- **API:** `routes.py` validiert Gewichte ∈ [0,1], unbekannte Enums, both‑zero‑combined; FTS‑Index‑Pflicht für `bm25_only` + `combined` (zusätzlich zu `q_match=fts`). `schema_version` → `replay_timeline_window_v4`. Filter‑Echo um `ranking_policy` + `score_weights` ergänzt.
- **Tests:** `tests/api/test_replay_hybrid_planner.py` (11 cases) + bestehende v3‑Suite weiter grün. Total **493 passed**.
- **Docs:** OPS §2.3, `archive/legacy-docs/Implementierungen.Architektur.md`, `docs/ORCH_IMPLEMENTATION_PLAN.md`.
- **PR:** [#91](https://github.com/walkiger/terra-incognita/pull/91)

---

## terra-079 — Replay Hybrid‑Planner Contract `replay_timeline_window_v4` (2026-05-08)

### Kurz

- **Contract:** `docs/contracts/replay_timeline_window_v4.schema.json` formalisiert `ranking_policy` (`bm25_only` | `substring_only` | `combined`), `score_weights.{bm25,substring}` ∈ [0,1], v3‑Back‑Compat‑Defaults und 422‑Surface.
- **Docs:** `archive/legacy-docs/Implementierung.backend.api.md`, `docs/PRODUCT_REPLAY_AND_TIMELINE.md`.
- **PR:** [#90](https://github.com/walkiger/terra-incognita/pull/90)

---

## terra-078 — Replay **FTS Ops** in **`GET /diagnostic`** (`replay_fts_ops`) (2026-05-08)

### Kurz

- **Code:** **`backend/db/replay_fts_metrics.py`** — Zähler; **`replay_fts.py`** / **`events.py`** — Erfolg/Fehler pro Rebuild‑Aufruf, Skip bei Debounce‑Fenster; **`routes.py`** — Diagnose‑Embed.
- **Felder:** `rebuild_success_total`, `rebuild_failure_total`, `append_rebuild_skipped_debounce_total`, `last_rebuild_ok_unix`, Echo `replay_fts_rebuild_debounce_s`, `fts_index_schema_present`.
- **Tests:** `tests/db/test_replay_fts_metrics.py` + Assertion in **`test_replay_fts_append_debounce`**.
- **Docs:** OPS §2.3, **`archive/legacy-docs/Implementierung.backend.api.md`**, **`memory/runtime/open-issues.md`**.
- **PR:** [#88](https://github.com/walkiger/terra-incognita/pull/88)

### Nächstes

- Hybrid‑Planner‑Policy (**`forward_plan`**) oder BL‑DSGN‑05 wenn Session ansteht.

---

## terra-077 — Replay **`ranking_mode` UI** (`ReplayPage.jsx`) (2026-05-08)

### Kurz

- **Frontend:** Select **chronological** / **hybrid** neben **`q_match`** — Parameter nur mit nicht‑leerem **`q`**; Meta‑Zeile zeigt Server‑Echo **`ranking_mode`**; Eventzeilen zeigen **`score`** wenn numerisch.
- **Docs:** **`archive/legacy-docs/Implementierung.backend.api.md`**, **`docs/PRODUCT_REPLAY_AND_TIMELINE.md`**, **`archive/legacy-docs/Implementierungen.Architektur.md`**.
- **PR:** [#87](https://github.com/walkiger/terra-incognita/pull/87)

### Nächstes

- Hybrid‑Planner‑Policy / Density — **`forward_plan`** in **`.agent-os/pr-spec.json`**.

---

## terra-076 — Replay timeline **`replay_timeline_window_v3`** + **`ranking_mode=hybrid`** (2026-05-08)

### Kurz

- **Contract / API:** `schema_version` **v3** — optional **`ranking_mode`** (`chronological`|`hybrid`); ohne **`q`** Echo null. Hybrid liefert **`events[].score`**, DuckDB‑**`after_id`** ignoriert (**`next_after_id`** null). Substring: Feld‑Treffer‑Score; FTS: **`match_bm25`** Sortierung RAM: Token-/Feld‑Näherung.
- **Code:** **`backend/db/events.py`**, **`backend/api/{routes,models}.py`**; Frontend nur Kommentar‑Bump **`ReplayPage.jsx`**.
- **Tests:** **`tests/api/test_replay_timeline.py`** (+ hybrid / after‑id / validation).
- **Docs:** **`docs/contracts/replay_timeline_window_v3.schema.json`**, Produkt/ORCH/Open‑Issues/Implementierung.
- **PR:** [#86](https://github.com/walkiger/terra-incognita/pull/86)

### Nächstes

- Density / Planner‑Policy (`forward_plan`) — **meta**/orch bei größeren Semantik‑Sprüngen.

---

## terra-075 — Replay **FTS append debounce** (`replay_fts_rebuild_debounce_s`) (2026-05-08)

### Kurz

- **Setting:** `replay_fts_rebuild_debounce_s` / `TERRA_REPLAY_FTS_REBUILD_DEBOUNCE_S` (**`backend/config/settings.py`**) — Default **30 s**, **`0`** = Rebuild nach jedem **`append_event`** (terra‑072).
- **Code:** **`backend/db/events.py`** — **`_maybe_rebuild_replay_fts_after_append`** debounced; **`flush_events`** immer Rebuild bei Rows; Watermark **`reset_replay_fts_append_debounce_clock_for_tests`** für Tests.
- **Tests:** `tests/db/test_replay_fts_append_debounce.py`.
- **Docs:** `docs/OPERATIONS_DIAGNOSTICS_PERSISTENCE.md` §2.3, `archive/legacy-docs/Implementierung.backend.api.md`, `docs/PRODUCT_REPLAY_AND_TIMELINE.md` F.3, `docs/ORCH_IMPLEMENTATION_PLAN.md` Epik F, `memory/runtime/open-issues.md`.
- **PR:** [#85](https://github.com/walkiger/terra-incognita/pull/85)

### Nächstes

- Hybrid‑Ranking / Density (orch‑gated); FTS Metriken wenn nötig — `forward_plan` in **`.agent-os/pr-spec.json`**.

---

## terra-074 — **`.agent-os/pr-spec.json`** Contract‑Registry wiederherstellen (2026-05-08)

### Kurz

- **Motivation:** Nach **terra-073** (#83) enthielt `pr-spec.json` nur noch das schmale Doku‑Slice — **Contracts** und **terra-072‑Kontext** fehlten für Orch‑Visibility.
- **Change:** Vollständige **contracts**‑Map (`replay_timeline_window_v2` …) + **forward_plan** (FTS cadence, Hybrid, BL‑DSGN‑05) + **tasks** als Backlog‑Pointer.
- **PR:** [#84](https://github.com/walkiger/terra-incognita/pull/84)

### Nächstes

- Branch **`feature/replay-fts-ops-cadence`** (Backend) wenn Semantik durch `orch`/`settings` gefixt ist.

---

## terra-073 — Replay **FTS** Betriebs‑Hinweis + **#82** merged record (2026-05-08)

### Kurz

- **Change:** `docs/OPERATIONS_DIAGNOSTICS_PERSISTENCE.md` §2.3 — **Ist‑Code** Replay‑FTS (Rebuild nach `append_event`/`flush_events`/Migrationen, **422** ohne Index, Backlog Debouncing).
- **`catchup.md`:** **`terra-072`** — PR **[#82](https://github.com/walkiger/terra-incognita/pull/82)** als **merged** vermerkt.
- **PR:** [#83](https://github.com/walkiger/terra-incognita/pull/83) — **merged** (squash).

### Nächstes

- Epik **F:** Density / Hybrid‑Ranking; FTS‑Ops‑Debounce wenn Messwerte/Rego — `memory/runtime/open-issues.md`.

---

## terra-072 — Replay **`replay_timeline_window_v2`** + **`q_match`** (**substring** / **fts**) + Ops‑Rebuild (2026-05-08)

### Kurz

- **PR:** [#82](https://github.com/walkiger/terra-incognita/pull/82) — **merged** (squash).
- **Contract:** [`docs/contracts/replay_timeline_window_v2.schema.json`](docs/contracts/replay_timeline_window_v2.schema.json); Response `schema_version` **`replay_timeline_window_v2`**; Filter‑Echo **`filters.q_match`** (`null` ohne `q`; sonst `substring` oder `fts`).
- **DB:** Migration **`0003_events_replay_search_doc.sql`** — Spalte **`replay_search_doc`** (nullable-safe `ADD COLUMN` für ältere DuckDB Parser; **`NOT NULL`** am INSERT in Python garantiert); Backfill wie zuvor; FTS Extension: `backend/db/replay_fts.py`; Rebuild nach **`append_event`**, **`flush_events`**, angewendete Migrationen; **`CURRENT_SCHEMA_VERSION` = 3** (`backend/db/schema.py`).
- **Backend:** `GET /replay/timeline` — optional **`q_match`**; **`fts`** nutzt `(SELECT fts_main_events.match_bm25(events.id, ?)) IS NOT NULL` als Zusatzfilter; **`ORDER BY id ASC`** unverändert; RAM‑Fallback **`fts`** = konjunktive Token‑Näherung. **`422`** wenn **`q_match=fts`** aber kein **`fts_main_events`** (DuckDB).
- **Frontend:** `ReplayPage.jsx` — **`q_match`** Select (**substring** / **fts**) wenn **`q`** gesetzt.
- **Tests:** `tests/api/test_replay_timeline.py` — v2 Schema; RAM/DuckDB **`fts`**; Gate **`422`** ohne Index (nach `drop_fts_index`).
- **Docs:** `archive/legacy-docs/Implementierung.backend.api.md`, ORCH/Product, `open-issues` (FTS Backlog gestaffelt), `catchup`, `.agent-os/pr-spec.json`.

### Nächstes

- Epik **F:** aggregierte Density / Hybrid‑Ranking; **BL‑DSGN‑05** Restart‑Wahrheit — `memory/runtime/open-issues.md`.

---

## terra-071 — Replay **`replay_timeline_window_v1`** + server **`q`** substring (2026-05-08)

### Kurz

- **Contract:** [`docs/contracts/replay_timeline_window_v1.schema.json`](docs/contracts/replay_timeline_window_v1.schema.json); Response `schema_version` **`replay_timeline_window_v1`**; `filters.q` Echo (trim/max 128).
- **Backend:** `GET /replay/timeline?…&q=` — DuckDB **`ILIKE`** auf `json_extract_string(data,'$.message'|'$.msg'|'$.word')` mit **`ESCAPE '\\'`** gegen Wildcards; RAM‑Fallback Substring‑Parität in `memory_events_matching`.
- **Frontend:** `ReplayPage.jsx` sendet **`q`**; lokales Highlight weiter (`q_client` Mirror — `replay_playback_state_v0` Beschreibung angepasst).
- **Tests:** `tests/api/test_replay_timeline.py` (+3 Fälle: Länge‑422, RAM `q`, DuckDB JSON `q`); bestehende Fälle → **v1** `schema_version`.
- **Docs:** `archive/legacy-docs/Implementierung.backend.api.md`, ORCH/Product/Architektur, `open-issues` FTS‑Follow‑Up, `catchup`.
- **PR:** [#81](https://github.com/walkiger/terra-incognita/pull/81) — **draft**.

### Nächstes

- Übernommen durch **`replay_timeline_window_v2` / terra‑072** (Substring bleibt; FTS ergänzend). Tiefer liegende Density-/Hybrid‑Themen und **BL‑DSGN‑05** weiter in `memory/runtime/open-issues.md`.

---

## terra-070 — Epik **F.2**: Replay Playback‑State‑Machine + Scrubber + Client‑Suche (2026-05-08)

### Kurz

- **Vertrag (UI‑seitig):** [`docs/contracts/replay_playback_state_v0.schema.json`](docs/contracts/replay_playback_state_v0.schema.json) — Client‑Zustandsmaschine `paused | playing | stepping`, `speed_ms ∈ {2000, 4000, 10000, 30000}`, `cursor_ts`, `window_since_ts`/`window_until_ts`, `q_client` (≤ 128 Zeichen).
- **`ReplayPage.jsx`:** Playback‑Buttons (Play/Pause/Step), **Speed**-Auswahl, **Scrubber** (Density‑Track + Cursor + Range‑Slider, Klick‑auf‑Eventzeile setzt Cursor, `Use cursor as since_ts`), **Client‑Suche** (`q_client`) mit Trefferhervorhebung; **Backend‑Vertrag (`replay_timeline_window_v0`) unverändert**.
- **Server `q` Volltext** und **BL‑DSGN‑05** Restart‑Wahrheit explizit **deferiert** — Einträge in [`memory/runtime/open-issues.md`](memory/runtime/open-issues.md).
- **Doku:** `docs/PRODUCT_REPLAY_AND_TIMELINE.md` (F.2‑Stand), `docs/ORCH_IMPLEMENTATION_PLAN.md` (Epik F Bullet), `archive/legacy-docs/Implementierungen.Architektur.md` (PRODUCT_REPLAY‑Status), `.agent-os/pr-spec.json`.
- **Tests/Lint:** `py -m pytest archive/legacy-terra/tests/ -q` ⇒ **463 passed**; `npm run lint` (frontend) clean — kein neues Backend‑Verhalten ⇒ keine neuen API‑Tests.
- **Governance:** `meta` Verdict für BL‑DSGN‑05 weiter ausstehend; F.2 enthält ausschließlich UI‑Erweiterungen ohne Vertrag‑Bruch — kein neuer ALLOW erforderlich.
- **PR:** [#80](https://github.com/walkiger/terra-incognita/pull/80) — **merged** (`main`).

### Nächstes

- Übernommen durch **terra-072** (**`replay_timeline_window_v2`** + **`q_match` fts**). weiter: Aggregat‑Density (**open-issues**) + **BL‑DSGN‑05** Restart‑UX. Danach Epik **G** / Research gemäß `memory/agents/orchestrator.md`.

---

## terra-069 — Epik **F**: Replay `/replay` Filter, Live‑Tail vs Pause, Ops‑Flush‑Doku (2026-05-08)

### Kurz

- **`ReplayPage.jsx`:** `getApiBase()`; Filter **session_id** / **event_type** / **since_ts** / **until_ts** / **limit**; **Live‑Tail** (Polling erste Seite) vs. Pause; Apply, Reload, „Load mehr“, Clear time window; 422‑Detail‑Parsing verbessert.
- **Tests:** `tests/api/test_replay_timeline.py` — DuckDB‑Insert‑Szenario für Session+Typ+Zeitfenster.
- **Doku:** `archive/legacy-docs/Implementierung.backend.api.md` (`GET /replay/timeline`), `docs/OPERATIONS_DIAGNOSTICS_PERSISTENCE.md` §2.3 (Retention / Flush‑Rahmen), `docs/ORCH_IMPLEMENTATION_PLAN.md` Epik‑F‑Checkbox, `docs/PRODUCT_REPLAY_AND_TIMELINE.md` Ist‑Hinweis.
- **PR:** [#79](https://github.com/walkiger/terra-incognita/pull/79) — **draft**.

### Nächstes

- Epik **F** Rest: Scrubber, erweitere Suche, BL‑DSGN‑05‑UX nach ORCH‑Plan; dann Epik **G** / Research gemäß `memory/agents/orchestrator.md`.

---

## terra-068 — ConceptNet eingefroren + Boot **`/boot/start`** JSON-Contracts (2026-05-08)

### Kurz

- **ConceptNet:** Öffentliche API wird **projektintern als permanent nicht verfügbar** geführt (**DEC** `memory/system/decisions.md`); `open-issues`, **`docs/PRESEED_ENRICHMENT_PLAN.md`**, **`fetch_conceptnet.py`**-Stub, Architektur §3; **kein Browser‑Scraping** außer zukünftiger Maintainer‑DEC nach Erledigung aller höher priorisierten Ziele.
- **Epik B Vertrag:** **`docs/contracts/boot_start_request_v0.schema.json`** + **`boot_start_response_v0.schema.json`**; Tests `tests/test_boot_start_contract_jsonschema.py`; **`archive/legacy-docs/Implementierung.backend.api.md`** + Hinweise in **`models`** / **`routes`**.
- **Epik A Nachzug:** `memory/runtime/open-issues.md` — **PR [#55](https://github.com/walkiger/terra-incognita/pull/55)** Encounter.
- **PR:** [#78](https://github.com/walkiger/terra-incognita/pull/78) — **merged** (`main`).

### Nächstes

- Epik **F**/Replay-Persistenz, Research **R2/R3**, R1 Builder-Read weiter nach ORCH-Reihenfolge.

---

## terra-066 — orch: Doku aktuell halten, PRs für Doku seltener (2026-05-08)

### Kurz

- **Policy:** Prosa/Memory **`catchup`**, **`Implementierung.*`**, **`memory/`**, **`docs/`** weiterhin **pro Session pflegen**; **eigene reine Doku-PRs** erst bei **größerem**, abgeschlossenem Batch. **DEC:** `memory/system/decisions.md` (*Documentation update frequency vs pull requests*).
- **Unverändert:** Code-/Contract-Änderungen → PR-first, Tests/CI wie bisher.

### Nächstes

- R1 technisch weiter: **Backfill / Builder** (siehe terra-065) als **eigenes Arbeitspaket** mit Scope; Produkt-Spur weiter nach `docs/ORCH_IMPLEMENTATION_PLAN.md`.

---

## terra-065 — R1: Writer setzen `pdf_sha256` auf Manifest (`pdf_ingest` + Batch-Fill) (2026-05-08)

### Kurz

- **`scripts/research/pdf_ingest_slug.py`:** **`pdf_sha256`** = SHA-256 von Ziel-PDF nach Copy (Dry-Run: Quell-PDF).
- **`scripts/research/batch_fill_research_layers.py`:** **`manifest["pdf_sha256"]`** = gleicher Hash wie bisher in **`notes`**.
- **Tests:** `tests/test_research_pdf_sha256_writers.py` (JSON Schema cross-check).
- **PR:** [#77](https://github.com/walkiger/terra-incognita/pull/77) — **merged** (`main`).

### Nächstes

- Preseed/Builder: Feld bei Merge-Pfaden auslesen; optionales Massen-Backfill aus **`notes`** nur mit explizitem Scope.

---

## terra-064 — R1: `pdf_sha256` Top-Level im Research-Manifest-Schema (2026-05-08)

### Kurz

- **`research/schema/manifest.schema.json`:** optionales **`pdf_sha256`** (`^[a-f0-9]{64}$`) — **orch R1** / `archive/legacy-docs/Implementierung.research.md`.
- **Tests:** `tests/test_research_manifest_jsonschema.py` — gültig, ungültig, Großbuchstaben abgelehnt.
- **Doku:** `research/README.md`, `archive/legacy-docs/Implementierung.research.md`, `docs/RESEARCH_SYSTEM_SYNTHESIS_TRACE.md` §10, `docs/ORCH_IMPLEMENTATION_PLAN.md` §8.3 R1.
- **PR:** [#76](https://github.com/walkiger/terra-incognita/pull/76) — **merged** (`main`).

### Nächstes

- siehe **terra-065** (Writer); Builder-Read + optional Backfill weiter offen.

---

## terra-063 — Issues **#71** / **#72**: TRACE §7.1 + R2-Workshop-Entwurf (2026-05-08)

### Kurz

- **`docs/RESEARCH_SYSTEM_SYNTHESIS_TRACE.md`:** §**1.1** Formeln (`l4_formulas_v0`); neuer **§7.1** Machine-extracted + Batch-Aggregate (PR **#68**); **§10** zwei Checkboxen erledigt.  
- **Neu:** `docs/workshops/R2_METHOD_TAG_RUNTIME_MAPPING_DRAFT.md` — 15 Tags aus `batch_report.json` ↔ Terra (Entwurf).  
- **`archive/legacy-docs/Implementierung.research.md`**, **`docs/ORCH_IMPLEMENTATION_PLAN.md`**, **`archive/legacy-docs/Implementierungen.Architektur.md`** synchron.  
- **PR:** schließt **#71** / **#72** nach Merge (Kommentar + `gh issue close`).

### Nächstes

- R3 (`l4_formulas_v1`); R2 **Moderationssession** (`docs/workshops/R2_METHOD_TAG_RUNTIME_MAPPING_DRAFT.md`). R1 **`pdf_sha256`**: Schema + Writer auf **`main`** (**#76**, **#77**); offen: **Builder-Read** + optional **Backfill** (terra-065).

---

## terra-062 — Research: PR **#68** PDF-Batch auf `main` (2026-05-08)

### Kurz

- **`research/extracted/`:** Regeneration **20260508T065744Z** — pro Dokument u. a. **`l4_formulas.json`**, **`_batch_reports/batch_report.json`** (`method_tag_vocabulary`, `formula_stats`, `documents[]`).
- **Merge:** `main` zuvor in den PR-Branch gemergt (Konflikte **keine**); lokal **449** pytest grün; **validate**/**test**/**label** auf PR **#68** grün → **Squash-merge** mit Titel **`research: PDF batch L0-L4 regen 20260508 (#68)`**.
- **Folge:** Issue-Arbeit **#71** / **#72** → erledigt mit **terra-063** (PR folgt).

### Nächstes

- ~~**#71** / **#72**~~ → **terra-063**.

---

## terra-061 — `orch`: §8.6 Synthesis-Backlog + `Implementierung.research` (2026-05-08)

### Kurz

- **`docs/ORCH_IMPLEMENTATION_PLAN.md`:** neuer Abschnitt **§8.6** — Research synthesis backlog **SB-01…SB-07** (Trace ↔ Epik **H/G/F**); §7 Punkt **7**; Revision terra-061; Verweis auf Blocker **PR #68** für `batch_report.json` / R2.
- **`archive/legacy-docs/Implementierung.research.md`:** neu — Governance **R1** (Provenance-Minimum), **R2–R5** Kurzverweis, SB-07, Nicht-Ziele.
- **`docs/RESEARCH_SYSTEM_SYNTHESIS_TRACE.md`:** §10 erste Checkbox **erledigt**; Revision history **(b)**.
- **`archive/legacy-docs/Implementierungen.Architektur.md`:** Doku-Zeilen ORCH / Trace / **Implementierung.research**.
- **PR #70** (`docs/orch-research-synthesis-backlog-071`): squash-merge auf `main`; CI validate/test/label grün; `.agent-os/pr-spec.json` auf dieses Paket ausgerichtet. **Issues:** **#71** (TRACE §7 ↔ `l4_formulas`), **#72** (R2 workshop nach `batch_report.json`).

### Nächstes

- **PR #68** (Draft) — Maintainer-Review/Merge; danach **#71** / **#72** schließen bzw. Workshop ansetzen.
- **PR #68** Merge eröffnet `batch_report.json` auf `main` → **R2**-Workshop (**#72**).

---

## terra-060 — `orch`: Synthese-Trace + Doku-Sync für PR #69 (2026-05-08)

### Kurz

- **Neu:** `docs/RESEARCH_SYSTEM_SYNTHESIS_TRACE.md` — Paper ↔ Subsystem-Mapping über `research/extracted/` (L3/L4/Manifest, ~22 Doku-Ordner). Inhalte: Scope/Limits, **15-Bullet** Exec-Summary, Master-Mapping-Tabelle (I/P/Pl/G), Per-Subsystem-Traces (LNN, EBM, KG, LM↔KG-Fusion, Ghost/Agency, Replay, Epik H), explizite **Non-Goals** (orch §8.4 Echo), interpretiver Formel-Anhang (kein `l4_formulas.json` in diesem Tree → Anhang als **„canonical literature shapes“** markiert, ersetzbar nach `l4_formulas_v1`), **§10 Handoff-Checklist** für die nächste ORCH-Plan-Revision.
- **Sync:** `archive/legacy-docs/Implementierungen.Architektur.md` Doku-Tabelle + `docs/ORCH_IMPLEMENTATION_PLAN.md` §8 verlinken den Synthese-Trace; ORCH revision history terra-060 ergänzt.
- **PR #69** (`docs/orch-research-corpus-full-product`): CI vor Sync-Commit grün (validate/test/label), wird nach diesem Commit aus Draft → Ready geschoben und gemergt.

### Nächstes

- **Erledigt:** §10/Trace-Backlog formal in **ORCH §8.6** (**terra-061**, PR **#70**).  
- Formel-Anhang in TRACE §7 ersetzen sobald `l4_formulas_*` auf `main` — **Issue #71**; PR **#68**-Linie.

---

## terra-059 — `orch`: Research-Batch → Vollprodukt, ORCH §8 (2026-05-08)

### Kurz

- **`docs/ORCH_IMPLEMENTATION_PLAN.md`:** Liefermodus **Vollprodukt** (Header); Epik **F** §3/§4/§6/§7 auf Stand **PR #66** + offene Produktkriterien (Zeitachse, BL-DSGN-05); neuer **§8** — Validierung Research-**PR #68**, **R1–R5**, `l4_formulas_v1`/Maintainer-Bundle, explizit verworfene Pfade; Mermaid **Epik F**-Label; Risiko-Zeile F angepasst. **PR #69.**
- **`archive/legacy-docs/Implementierungen.Architektur.md`:** Tabellenzeile **PDF Research L0–L4** + ORCH-Zeile mit **§8**-Referenz.

### Nächstes

- **PR #68** mergen wenn Gates grün; danach **`method_tag_vocabulary`**-Alignment-Workshop → **Epik H**; **R3/R5** Formel-Pipeline + Export in Implementierung.research / Backlog-Issues.

---

## terra-058 — Epik D (#58) + Epik E (#59) auf main (2026-05-07)

### Kurz

- **PR #58** (Epik **D**): LDV-Zwischenbatch-Pause geklemmt über `ghost_pause_min_s` / `ghost_pause_max_s`; `TickState` Pause-Fenster + High-Tier-Drain-Budget; `GhostQueueRouter.pop_next(allow_high)`; Ghost-Worker via `ensure_ghost_queue_started` während Boot (Pytest: `PYTEST_CURRENT_TEST` skip); `RuntimeSummary` Pause-Felder; Vertrag `runtime_pause_window_v0`.
- **PR #59** (Epik **E**): `RuntimeSummary.ghost_queue` (validiertes Router-Snapshot); **`GET /diagnostic`** → **`ghost_feedback`** (`runtime_ghost_feedback_v0`); Legacy-Feld `ghost_queue` unverändert; Frontend **Header** (`q H:M:L`, Pause-Badge) + **DiagnosticPage**-Karte; Store liest Delta-`summary`; **436** Tests vor Merge grün.

### Nächstes

- **`orch`/Produkt:** **Epik F** (Persistenz + Replay-MVP) — Contracts zuerst, split-PR empfohlen (`feature/epik-f-replay-persistence-mvp` …).
- **Doku-Nachzug:** erledigt mit **PR #60** (ORCH §4/§7, Architektur-Tabelle, Memory-Status).

---

## terra-057 — Merges #55/#56 + Epik C Ghost Router (PR #57, 2026-05-07)

### Kurz

- **PR #55** (Epik A) und **PR #56** (Epik B) auf `main` gemergt; Branch `feature/deferred-boot` mit `main` per Merge-Konflikt in `backend/api/models.py` + `routes.py` aufgelöst (Encounter + BootStart koexistieren).
- **Epik C:** `GhostQueueRouter` — drei Tiers (High/Medium Min-Heap nach Score, Low FIFO), Caps `ghost_queue_*` in `settings.py`, Idempotenz `(lexeme, lang)`, Diagnostic-Feld `ghost_queue`, Background-Task `start_ghost_queue` nach erfolgreichem Boot; Wiring über `ghost_encounter(..., ghost_router=…)` und `process_word(..., ghost_router=…)`.
- **`tests/core/test_ghost_queue_router.py`**, **`tests/core/test_boot_waves.py`** Mock erweitert — **430** Tests grün.

### Nächstes

- Erledigt Nachfolger: **#58**/#**59** (Epik D/E).

## terra-056 — Epik A: Encounter Normalization (feature/encounter-lexeme-discourse, PR TBD, 2026-05-07)

### Kurz

- `normalize_encounter(surface)` → `(lexeme, discourse_mode)` in `backend/api/routes.py`
- `POST /encounter` accepts `surface` (v0) + legacy `word`; calls `process_word(lexeme, ...)`
- `EncounterResponse` added to `backend/api/models.py`
- `tests/api/test_encounter.py`: normalization edge cases + backward compat (417 tests pass)
- `meta` governance check for Epik H Architecture Freeze DEC running in parallel

### Nächstes

- Security review result → fix if needed → commit + PR
- `meta` verdict → update `memory/system/decisions.md` DEC status if ALLOW
- Epik B (Deferred Boot) after PR merge

---

## terra-055 (follow-up) — Epik H scaffolds + manifest jsonschema (#53, 2026-05-07)

### Kurz

- Fünf **doc-only** **`Implementierung.architecture.*.md`** (Epik **H**, terra‑055 Q1–Q8); **`docs/ORCH_IMPLEMENTATION_PLAN.md`** ergänzt (Epik‑Tabelle enthielt **H** bereits; §6 Branch-/Label‑Zeile + Revision history).
- **`document_id`** in **`research/schema/manifest.schema.json`**: **`T`/`t`** und **`Z`/`z`** im UTC‑Suffix; **`pdf_ingest_slug.py --ts-lowercase`** optional.
- **`jsonschema`** in **`requirements-dev.txt`**; **`tests/test_research_manifest_jsonschema.py`** (Draft202012 + ein committed Manifest).
- **`memory/runtime/orch-pending-questions.md`**: Punkte 2–3 erledigt markiert; **`archive/legacy-docs/Implementierung.research.l0_to_l4.md`** von altem „Option A“-Text auf Ist‑Stand gebracht.
- **Cursor → Git:** Commit-Messages **ohne** `Co-authored-by: Cursor …` — Quelle war Client-Attribution, nicht das Repo; Policy in **`Anweisungen.md` §5** + **`memory/system/constraints.md`**; optional **`pre-commit install --hook-type prepare-commit-msg`**; PR **#53**-Historie einmal ohne Trailer neu geschrieben.

### Nächstes

- **PR `#53`:** **gemergt** (squash **`cea286d`** auf `main`, 2026-05-07).
- **`meta`:** terra‑055 DEC (*Research-Guided Architecture Freeze* in `memory/system/decisions.md`) → **`ALLOW`** / Status **`active`**, bevor bindende Contracts oder Produkt‑Code unter **Epik H** starten.
- Optional: **`pre-commit install --hook-type prepare-commit-msg`** lokal (`scripts/strip_cursor_coauthor_trailer.py`).

---

## terra-055 — research: siebzehn PDFs + L0-L4 + Design-Session-Artefakte (PR #49, 2026-05-07)

### Kurz

- Batch-Suffix **`20260507T081859Z`**: siebzehn PDFs unter **`research/incoming/`** sowie je ein Ordner **`research/extracted/<document_id>/`** mit **`manifest.json`** (L0 bis L4 `complete`), Excerpt (**Abstract durch Introduction**) und **`l1_*` bis `l4_*`** Artefakten (Abstract/Intro-basierte Passagen; keine Full-Paper-Tiefenparses).
- Session-Artefakte bewusst unter **`research/work/`** eingecheckt (Ausnahme zur Default-Scratch-Regel): **`DESIGN_SESSION_BRIEFING_terra055_20260507.md`**, **`terra055_page_anchors_20260507.json`**, Hilfsscript **`terra055_page_anchor_sweep.py`** (PDF-Seiten-Verankerung für Zitate).
- Entwurfs-PR: **`#49`** zum Review; danach Fortsetzung Terra-052/Schema und formalisierte DECs aus der Design-Session vorsehen.

### Nächstes

- **`#49`** reviewen/mergen; **terra-053**: `document_id`-Schema vs. reale Slugs (strikt validierbar).
- Design-Session-Ergebnisse (**Q1–Q8**) separat in **`memory/system/decisions.md`** + ggf. neue **Epik-H**-Implementierungs-Docs (governance-sauber, eigener PR).
- **`#46` / `#48`**: terra-052 Extraktion + Research-Log weiterziehen sobald Research-Backlog klar ist.

---

## terra-051 — research/incoming: sechs PDFs ingested + `pdf_ingest_slug.py` (PR #45, 2026-05-07)

### Kurz

- Lokale Downloads (`SLM.pdf`, contrastive / continuous learning, inference PIN, temporal KG, GNN) nach **`research/incoming/`** kopiert mit **slug aus Titel** (Header vor Abstract, Autoren-Zeilen gefiltert) + **gemeinsamer UTC-Zeitstempel-Suffix** `20260507T000032Z` auf allen sechs Dateien (ein Batch-Lauf).
- Pro Papier: **`research/extracted/<document_id>/manifest.json`** (L0 complete) + **`ingest_excerpt_abstract_through_intro.txt`** (Text von Abstract/Index Terms bis Ende Introduction nach Heuristik).
- Hilfsskript **`scripts/research/pdf_ingest_slug.py`** + **`pypdf`** in **`requirements-dev.txt`**.

### Dokument-IDs (Basisnamen ohne `.pdf`)

- `towards_energy_aware_requirements_dependency_classification_knowledge_gr_20260507T000032Z`
- `graph_structure_refinement_with_energy_based_contrastive_learning_20260507T000032Z`
- `hybrid_transformer_model_with_liquid_neural_networks_and_learnable_encod_20260507T000032Z`
- `efficient_bayesian_inference_using_physics_informed_invertible_neural_ne_20260507T000032Z`
- `temporal_knowledge_graph_completion_a_survey_20260507T000032Z`
- `graph_neural_networks_a_review_of_methods_and_applications_20260507T000032Z`

### Nächstes

- **L1** Roh-Text / Parser anbinden; Slug-Länge ggf. Wortgrenze statt hartem 72-Zeichen-Cut.

---

## terra-050 — research/ Skelett PDF L0–L4 (γ, PR #44, 2026-05-07)

### Kurz

- Neuer Baum **`research/`**: `incoming/` (PDFs versionieren), `extracted/<document_id>/` + **`manifest.json`**, `work/` (Scratch-Disziplin), `schema/manifest.schema.json` (**v0.1.0**).
- Layer-Modell **L0** (Identity) … **L4** (Deep analysis) in **`research/README.md`** beschrieben.
- DEC in **`memory/system/decisions.md`** — γ nur Struktur/Schema, keine Extraktions-Skripte in diesem PR.

### Nächstes

- PDFs nach **`research/incoming/`** legen / via Chat — **`research-agent`** füllt Manifest + Artefakte schichtweise.
- **δ:** `.cursor/agents/registry.yaml` + Label-Konsolidierung.
- Optional später: `scripts/research/` oder dediziertes `requirements-research.txt` wenn echte Parser angebunden werden.

---

## terra-049g — CLAUDE.md auf Pointer-Referenz gestutzt (D, PR #43, 2026-05-07)

### Kurz

- **`CLAUDE.md`** verkleinert: lange Duplikate (Drei‑Pol‑Tick, Enrichment‑Layer, LNN‑Dimensionstabelle, Locale‑Beispielcode, Architektur‑Tabelle, Preseed‑JSON‑Block) entfernt — **canonical** bleibt in `docs/ARCHITECTURE.md`, `Implementierung.*.md`, `PRESEED_*`, `decisions.md`.
- Session‑Workflow, Pointer‑Tabelle („Wo finde ich was“), **9 Regeln**, Windows‑Shell-Hinweise **unverändert** inhaltlich relevant.
- Orchestrator-Zeile ergänzt: atomare Commits + Verweis auf **gebündelte Shell** (`Anweisungen.md` §5).
- Motivation: Parent‑Chat lädt `CLAUDE.md` pro Turn — weniger Tokens pro Session.

### Nächstes

- **γ:** `research/` Skelett PDF Deep-Extraction.
- **δ:** `.cursor/agents/registry.yaml`.

---

## terra-049f — Agent-Automation aktivieren (ζ, PR #42, 2026-05-07)

### Kurz

- Drei Workflows unter `.github/workflows/` committet: **Auto Agent Labeling**, **CI Feedback Router** (`workflow_run` auf Agent OS CI Pipeline), **Self-Healing Proposal Generator**.
- Vier Scripts unter `scripts/` committet: `create_pr.py`, `feedback_router.py`, `memory_writer.py`, `self_healing_analyzer.py` — waren vorher untracked; Working Tree damit bei Automation-Themen sauberer.
- Sequenz: vor γ eingeschoben (Token/Kosten-Housekeeping + keine parallel-untracked Artefakte mehr für Routine-PRs).
- Risiko/Follow-up: Auto-Labeling nutzt Substrings („test“ im Titel → `agent:test`) — Feintuning oder Registry aus PR δ.

### Nächstes

- **γ:** `research/` Skelett PDF Deep-Extraction.
- **δ:** `.cursor/agents/registry.yaml` + Label-Gates konsolidieren.

---

## terra-049d — Subagent-Modell-Remap Kosten (E, PR #40, 2026-05-07)

### Kurz

- User-Prio: **Token-/Plan-Verbrauch senken**; Opus 4.7 nur wo Grenznutzen hoch bleibt.
- **`orch`:** `gpt-5.3-codex` (hohe Dispatch-Frequenz).
- **`security-code-review-agent`:** `gpt-5.5-medium`.
- **`backend-implementation-agent` / `frontend-implementation-agent`:** `gpt-5.3-codex`.
- **Unverändert Opus:** `meta`, `code-audit-agent` (Governance + tiefe Legacy-Audits).
- DEC in `memory/system/decisions.md`; Slugs an Cursor-Allowlist angepasst (kein `codex-high` im Front-matter).

### Nächstes

- Weitere Kostentreiber: Parent-Chat-Modell (User auf **Composer 2 Fast** gewechselt), CLAUDE.md-Trim (PR folgt), Batched-Shell-Working-Agreement in `Anweisungen.md` + `orchestrator.md` (PR folgt), Automation aktivieren (PR ζ), dann γ `research/` Skelett.

---

## terra-049c — Subagent Definitions unter Versionskontrolle (β.1, PR #39, 2026-05-06)

### Kurz

- **Befund:** Alle 12 `.cursor/agents/*.md` waren **untracked** — `orch`, `meta`, `heal`, `verifier`, alle Implementation-/Test-/Audit-/Security-/Docs-/Research-Agents lebten nur lokal. Folge: kein Schutz durch das soeben mit PR #38 etablierte `NO-SILENT-DELETIONS`-Gate, keine Reproduzierbarkeit, kein PR-Lifecycle.
- **`.gitignore`:** Pattern `.cursor/*` mit Ausnahme `!.cursor/rules/` ergänzt um `!.cursor/agents/` + `!.cursor/agents/**` — Definitionen können jetzt getrackt werden, restliches `.cursor/`-Cache bleibt ignoriert.
- **Tracking 1:1** wie auf der Platte (User-Wahl A1) — keine Description-Refinements, keine Modell-Änderungen.
- **`is_background: true`** für `code-audit-agent` (6000+-Zeilen-HTML-Audit) und `research-agent` (PDF-Deep-Extraction) ergänzt — entkoppelt token-schwere Spezialisten vom Parent-Agent.
- **15 atomare Single-File-Commits:** `.gitignore` → 12 Agent-Files → DEC → catchup.
- **Pro+-Caveat dokumentiert** (DEC + diese Notiz): Modelle bleiben wie gewählt (`claude-4.7-opus` × 4, `claude-4.6-sonnet` × 2, `gpt-5.3-codex` × 1, `gpt-5.5` × 2, `composer-2` × 3); falls Max Mode für Subagent-Dispatch nicht aktiv ist, fallen die opus/sonnet-Agents still auf Composer zurück. Beobachtung als Telemetrie-Punkt — keine PR-Aktion.

### Nächstes

- **PR γ:** `research/` Skelett (PDF Deep-Extraction L0–L4) — danach kannst du PDFs in den Chat anhängen.
- **PR δ:** Memory-Orchestration + `.cursor/agents/registry.yaml` als Single Source of Truth (löst hardcoded `REQUIRED_AGENT_LABELS` in `scripts/check_pr_labels.py` ab) + decisions.md Reorder auf newest-first.
- **PR ε:** CI Discovery-Run für historische Core-Tests (Q9 Option B).
- **PR ζ:** `.cursor/hooks.json` mit `subagentStart` / `preToolUse` Matchern (Tool-Policy-Härtung pro `GLOBAL-CURSOR-RULES-Agent-OS.mdc`); Recherche `cursor.com/docs/hooks` unmittelbar davor.
- **PR η:** untracked Automation-Scripts aktivieren, die Registry aus PR δ konsumieren.
- **PR θ:** Epik A — `encounter_v0` Contract + Normalization (`meta`-Gate).

---

## terra-049b — NO-SILENT-DELETIONS Gate (β / Variant 3, PR #38, 2026-05-06)

### Kurz

- **Rule** `.cursor/rules/NO-SILENT-DELETIONS.mdc` (`alwaysApply: true`): geschützte Pfade (Living Docs, `docs/`, `knowledge/`, `reference/`, `memory/`, `tests/`, `.github/workflows/`, `.cursor/rules/`, `.cursor/agents/`, Root‑`*.md`), Klassifikation (`ephemeral` / `generated` / `deprecated-but-retained` / `approved-removal`), Approval-Kanäle.
- **Gate-Script** `scripts/check_protected_deletions.py` (lokal: staged Deletions; CI: `origin/<base>...HEAD` Diff). Approval per `approved_deletions:`-Zeile in **irgendeinem** Commit-Body des PR oder per `.agent-os/pr-spec.json` (`approved_deletions: [...]`).
- **Variant 3:** `pre-commit`-Framework — `.pre-commit-config.yaml` registriert Hook `check-protected-deletions`; Aktivierung lokal mit `pip install -r requirements-dev.txt && pre-commit install`.
- **CI:** `.github/workflows/agent-ci.yml` Schritt *Protected Deletions Gate* (blocking), läuft das Script direkt (kein `pre-commit`-Setup im Workflow). `fetch-depth: 0` ergänzt, damit die PR‑Diff‑Auflösung gegen `origin/<base>` greift.
- **Subagent-Fallback** (`SUBAGENT-DELEGATION-FALLBACK.mdc`): Parent‑Agent muss Deletions in der Git‑Hygiene‑Narration klassifizieren; Hinweis auf das blocking Gate ergänzt.
- **DEC** in `memory/system/decisions.md` mit Bezug auf zwei vorausgegangene Silent‑Deletion‑Regressionen (`docs/CODE_AUDIT.md`, `docs/HTML_UI_AUDIT.md`).
- 8 atomare Commits, je ein File — Reihenfolge `requirements-dev.txt` → Hook‑Config → Script → Rule → CI → Fallback‑Update → DEC → catchup.

### Nächstes

- **PR γ:** `research/` Skelett für PDF Deep-Extraction (L0–L4) — danach PDFs via Chat anhängbar.
- Execution-Design-Session (`orch`) — anschließend PR δ (Topology + Memory-Briefings) und PR ε (CI Discovery-Run für historische Core‑Tests, Q9 Option B).
- Automation‑PR ζ (Workflows/Scripts derzeit untracked) bewusst zuletzt, nach Design‑Session.

---

## terra-049a — Hygiene: ConceptNet failed-run policy + .gitattributes (PR #37, 2026-05-06)

### Kurz

- Lokaler **Failed-Run-Record** `knowledge/enriched/en_conceptnet/w00_primordials.json` (5×`error: fetch_failed`, terra-033) entfernt — nie in Git, kein History-Verlust. Ordner ebenfalls entfernt.
- **Policy** `Failed-Run Hygiene` ergänzt in **`docs/PRESEED_FETCH_PIPELINE.md`**: failed-only Outputs werden nicht committet; produktive CN-Outputs bleiben weiter committable (kein `.gitignore`).
- **`.gitattributes`** neu: `* text=auto eol=lf` + `*.ps1` CRLF + Binär-Klassifizierung (PDF, Parquet, DuckDB, Bilder). Beendet die LF/CRLF-Spam-Welle auf Windows; bereitet PDF-Ingest in `research/` vor.
- Teil 1 der orch-Sequenz (terra-049 Plan) — PR α.

### Nächstes

- **PR β:** `NO-SILENT-DELETIONS` Rule + Pre-Commit/CI-Gate (block).
- **PR γ:** `research/` Skelett für PDF Deep-Extraction (L0–L4) — danach kann der User PDFs in den Chat anhängen.
- Execution-Design-Session (`orch`) im Anschluss; Automation-PR (Workflows/Scripts) **erst nach** der Session.

---

## terra-048 — Doku-Hygiene: Phasen‑Archiv entfernt, zweiter HTML‑Snapshot gelöscht, **`docs/CODE_AUDIT.md`** + **`docs/HTML_UI_AUDIT.md`** wiederhergestellt (2026-05-06)

### Kurz

- Archivierte Python‑Phasen‑Checkliste unter **`reference/docs/`** entfernt — Regeln/Invarianten leben in **`Anweisungen.md`** §7, **`CLAUDE.md`**, **`docs/ARCHITECTURE.md`**; Boot-/Fetch in **`docs/FETCHING.md`**; Ist‑/Roadmap‑Tabellen in **`archive/legacy-docs/Implementierungen.Architektur.md`** und **`docs/ORCH_IMPLEMENTATION_PLAN.md`**.
- **`reference/jarvis_v1_00__8_.html`** gelöscht — Kanon für HTML‑Referenz bleibt **`reference/jarvis_v1.02-stable.html`**.
- Aktive Leitdokumente bereinigt: **`CLAUDE.md`**, **`archive/legacy-docs/Implementierungen.Architektur.md`**, **`catchup.md`**, **`memory/system/research-overview-2026-05-05.md`**, **`docs/FETCHING.md`**, **`docs/ORCH_IMPLEMENTATION_PLAN.md`**, **`archive/legacy-docs/Implementierung.backend.api.md`**.
- **`docs/CODE_AUDIT.md`** und **`docs/HTML_UI_AUDIT.md`** wieder aus Git eingespielt (Stand vor terra‑014‑Löschung) — Landing in **`CLAUDE.md`** / **`archive/legacy-docs/Implementierungen.Architektur.md`**.

### Nächstes

- Epik‑Pfad A→G unverändert **`docs/ORCH_IMPLEMENTATION_PLAN.md`**.

---

## terra-047 — Klärung Commit-Betreff = `(#N)` wie 9f638f5 („PR #2“ umgangssprachlich) (2026-05-06)

### Kurz

- **9f638f5** Betreff: `fix: stabilize runtime contracts (#2)` — bindende Schreibweise **`(#NNN)`**, nicht zwingend das Wort „PR“ im Betreff.
- **`Anweisungen.md`** §5 + Cursor-Rules + PR-Template + `CLAUDE.md` + `orchestrator` + Fallback: Referenz + Verhältnis zu optional **`(terra-XXX)`**.

### Nächstes

- Bei PR-gebundener Arbeit Subjects konsequent wie Referenz-Commit.

---

## terra-046 — Pflicht: PR-Nummer `(#NNN)` im Commit-Betreff (2026-05-06)

### Kurz

- Regel dokumentiert in **`Anweisungen.md`** §5 Git-Regeln, **`.cursor/rules/PR-WORKFLOW.mdc`**, **`GLOBAL-CURSOR-RULES-Agent-OS.mdc`**, **`CLAUDE.md`** Session-Ende; Checkliste in **`.github/pull_request_template.md`**.
- **`SUBAGENT-DELEGATION-FALLBACK.mdc`:** Git-Hygiene um Commit-Subject ergänzt.
- **`memory/agents/orchestrator.md`:** Current Notes.

### Nächstes

- Bei jedem PR Draft früh anlegen, damit `(#NNN)` in allen Follow-up-Commits möglich ist.

---

## terra-045 — orch: Agent-Broadcast, Merge‑Gate Umsetzung (2026-05-06)

### Kurz

- **`memory/agents/*`:** einheitlicher Verweis **terra-045** auf [`docs/ORCH_IMPLEMENTATION_PLAN.md`](docs/ORCH_IMPLEMENTATION_PLAN.md) (Epik A–G) + rollenspezifische Aufgaben; neu: `documentation.md`, `heal.md`.
- **`memory/README.md`:** Strukturzeile Agent-Liste + Broadcast-Hinweis.
- **`orchestrator.md`:** nach Merge Epik **A** umsetzungsbereit.
- **Merge:** PR #33 (terra-044 Plan + Contracts) zusammen mit diesem Broadcast erwünscht; danach erste Implementierung = **Epik A** (`encounter_v0`, Router, Tests).

---

## terra-044 — `orch`: Design-Analyse + Umsetzungsplan Epik A–G (2026-05-06)

### Kurz

- **`docs/ORCH_IMPLEMENTATION_PLAN.md`:** Auswertung Workbook vs. terra-043; Verbesserungen (Begriffstrennung Preseed‑Welle vs. Runtime‑Batch‑Pause; **Split BL‑DSGN‑03** in 3a/3b/3c; Interim‑Contracts; trace_id früh; Agency nach stabilem Router); **Mermaid‑Abhängigkeiten**; Epik **A–G** mit Akzeptanzkriterien, Risiken, Branch‑Vorschlag.
- **`docs/contracts/`:** `encounter_v0.schema.json`, `runtime_ghost_queue_v0.schema.json` (interim, session‑supersedable).
- **Angebunden:** Workbook (**§4.8** Ghost‑Zeile, **§7** Hinweis, **Anhang A**, Kopf‑Verknüpfung), `design-session-p0-queue.md`, `memory/agents/orchestrator.md` (priorisierte Aktionen neu), `archive/legacy-docs/Implementierungen.Architektur.md` §2, `CLAUDE.md`.

### Nächstes

- **Epik A** starten oder Session terminieren für **BL‑DSGN‑01/02/05** bevor Persistenz‑Epik F „hart“ wird.

---

## terra-043 — Encounter-Router Plan, Dreischicht-Ghost-Queues, DEC Nomenklatur+Router (2026-05-06)

### Kurz

- **Neu:** `docs/ENCOUNTER_GHOST_AGENCY_ROUTER_PLAN.md` — Lemma/`lexeme` + `surface`/`discourse`, Caps **High 33 / Medium 500 / Low ∞**, Wellen‑Pause vs. Millisekunden‑Attention, Agency‑Logging, Trace‑Mindestfelder; reactive/attentive/reflexive als spätere Operationalisierung.
- **`docs/GHOST_MATERIALIZATION_PLAN.md`:** §§3 ·9 — **ghost vs tier_shadow** im Definitionsblock; §9 Queue‑Kapsel; **Related** ergänzt.
- **`memory/system/decisions.md`:** **Nomenclature — ghost vs tier_shadow**; **Encounter normalization + ghost queue tiers** (Planungs‑DEC, Caps/Timing/HTML‑Analogon).
- **Verknüpft:** `OPERATIONS_DIAGNOSTICS_PERSISTENCE.md`, `archive/legacy-docs/Implementierungen.Architektur.md`, `CLAUDE.md`, `memory/runtime/open-issues.md`, `memory/agents/orchestrator.md`.

### Nächstes

- **`orch`:** JSON‑Contract Encounter‑DTO + `runtime_ghost_*` Queues; **`backend`** `process_word`/Router‑Tests (**`why?`→ `why`** + **`question`** Modus).

---

## terra-041 — Produktphase + Orchestrator gedächtnis (post‑MVP planning) + Replay‑Spec (2026-05-06)

### Kurz

- **DEC neu:** `memory/system/decisions.md` — *Product delivery framing — MVP label superseded for planning*.
- **`memory/agents/orchestrator.md`:** Produkt‑Planungsrahmen, Pflichtlinks `PRODUCT_REPLAY_AND_TIMELINE` + `OPERATIONS_DIAGNOSTICS_PERSISTENCE`, priorisierte Aktion‑Liste angepasst; Workbook‑§7 vs. parallele Produktfäden geklärt.
- **Neu:** `docs/PRODUCT_REPLAY_AND_TIMELINE.md` — dedizierte **Replay**/Zeitachse‑Oberfläche (Pause, Scrub, Filter/Suche‑Max‑Ziel); `orch`‑Ownership ohne Implementierung hier.
- **Aktualisiert:** `CLAUDE.md` (Stand + Session‑Workflow + Tabelle), `archive/legacy-docs/Implementierungen.Architektur.md` (Kopf + §2), `docs/ARCHITECTURE.md` (Baseline‑Terminologie + Produktlinks), `docs/OPERATIONS_DIAGNOSTICS_PERSISTENCE.md` (Gleis A Wording „Engineering‑Baseline“, Verknüpfung Replay‑Doc).

### Nächstes

- Replay/Timeline‑API‑Contract in `archive/legacy-docs/Implementierung.backend.api.md` skizzieren; persistierte Events jenseits FIFO — `orch` Zerlegung.

---

## terra-040 — Betriebs-Doku: Zwei‑Gleis‑DB, Diagnose‑Roadmap, erweiterter Pre‑Boot @ Neustart (2026-05-06)

### Kurz

- **Neu:** `docs/OPERATIONS_DIAGNOSTICS_PERSISTENCE.md` — festgehalten: **zweigleisige** Persistenz‑Strategie (DuckDB MVP + ADR‑Pfad für dokumentenorientierten Store), **Bestand** Diagnose‑Routen/UI, **Ausbauliste** (Snapshot‑Delete nach Export, Log‑Levels, Export‑Manifest, Instrumentierung, Optionen von Haupt‑UI), **Pre‑Boot‑Zielbild:** Standard **Laden** mit reichhaltigen Snapshot‑Metadaten; **Neustart** mit **wählbarem Pre‑Seed** und React‑orientierter Darstellung (Katalog später `GET /preseed/catalog` + `POST /boot/start` 0.028).
- **Verknüpft:** `CLAUDE.md`, `archive/legacy-docs/Implementierungen.Architektur.md` §2, `docs/PREBOOT_PLAN.md`, `archive/legacy-docs/Implementierung.frontend.preboot.md`, `docs/ARCHITECTURE.md` (DuckDB‑Absatz).

**Git:** Commit `88ed3a4` — `docs: operations plan for dual-track DB, diagnostics, pre-boot restart`.

### Nächstes

- API‑Contracts implementieren (`archive/legacy-docs/Implementierung.backend.api.md`) vor `/delete`‑Snapshot, Log‑Queries, Pre‑Seed‑Katalog; dann UI gemäß gleicher Doku.

---

## terra-039 — Persistenz DEC: DuckDB-Baseline vs Mongo langfrist (2026-05-06)

### Kurz

- Frühere Formulierung „Mongo out of scope“ **gelockert**: neue aktive Decision **Persistence store — DuckDB baseline; long-term evaluation (MongoDB etc.)** in `memory/system/decisions.md` (älteren Eintrag deprecates).
- Inhalt: Istdaten `preseed_v2.json` (**2302** Anchors, **~134 051** Relation‑Stubs, **~14 3 MiB**), grobe **Größenordnung** bei **100 000** externen Calls über „Neuigkeitsgrad“ `r` (Tabelle dort); Hinweis, dass häufig **RAM‑KG und Fetch‑Dedupe**, nicht DB‑Wahl, der erste Bottleneck sind.
- `docs/ARCHITECTURE.md`, Workbook DEC-20260506-02 angepasst.

### Nächstes

- Beim konkreten SLO-/Deployment-Schritt kleine ADR: wann echte Produktwahl Mongo vs weiter Duck+Neben‑Stores.

---

## terra-038 — Workbook Vorab-Protokoll + DuckDB (2026-05-06)

### Kurz

- **`docs/DESIGN_SESSION_FULL_SYSTEM_WORKBOOK.md`:** Abschnitt **4.8** (Roadmap-Matrix), **§5** (DEC-20260506-01 P0-Defer-Paket mit **BL-DSGN-01..06**, DEC-20260506-02 DuckDB), **§6** ohne P0-Leerstand, **§7** Checkboxen gesetzt mit Hinweis: formale Gate-Erfüllung für Deferrals; substanzielle P0-Antworten folgen erst **synchroner** Session-Durchgang.
- **Neu:** `memory/runtime/design-session-p0-queue.md` — Zuordnung P0-Fragen → Backlog-ID.
- **`memory/system/decisions.md`:** Persistenzbeschluss *DuckDB MVP, kein Mongo ohne neuen DEC*; Workbook bereits mit earlier „fine planning gated by §7“.
- **`docs/ARCHITECTURE.md`** DuckDB-Kapitel: MVP-Hinweis + Verweis auf Decision.
- **`archive/legacy-docs/Implementierungen.Architektur.md` §2, `memory/agents/orchestrator.md`:** Statuszeilen angepasst.

**Git:** Arbeitspfad dokumentiert zusammen mit den genannten Dateien in einem Commit auf `main` (Nachricht: `docs: design-session workbook defer queue, DuckDB MVP decision, terra-038`).

### Nächstes

- Moderierte Design-Session — §5 Defer-Zeilen durch konkrete `DEC-*` ersetzen; §7 Hinweistext entschärfen sobald geschlossen; Tracker als superseded markieren.

---

## terra-037 — Design-Session Workbook + Planungsdisziplin (2026-05-06)

### Kurz

- Neues Pflicht-Artefakt **`docs/DESIGN_SESSION_FULL_SYSTEM_WORKBOOK.md`**: detaillierte **P0/P1/P2-Fragen** (Drei-Pol, Lemma/Mehrsprachigkeit, Ghost, Boot 0.028, Persistenz, Frontend-Contracts, Datenqualität), **Entscheidungsprotokoll-Vorlage**, Roadmap-Matrix, **Planungsfreigabe-Checkliste** (§7).
- **Orch-Regel:** Feine Epik-/Branch-Planung erst **nach** ausgefülltem Workbook (alle P0 entschieden oder dokumentiert deferiert).
- Verknüpft: `MULTILINGUAL_AND_SYSTEM_DESIGN.md`, `CLAUDE.md`, `archive/legacy-docs/Implementierungen.Architektur.md` §2, `memory/agents/orchestrator.md`, `memory/system/decisions.md`.

### Nächstes

- Session durchführen → DEC-* nach `memory/system/decisions.md` und Architektur-Docs spiegeln → §7 abhaken.

---

## terra-036 — Mehrsprachigkeit: Vorbereitung + EN-only + Design-Session (2026-05-06)

### Kurz

- Neues Strategiedokument **`docs/MULTILINGUAL_AND_SYSTEM_DESIGN.md`**: EN als einzige **implementierte** Laufzeit-/KB-Sprache bis tragfähige Lösungen und eine **generelle System-Design-Session** das Gesamtkonzept (Drei-Pol, Lemma-Raum, Locale vs. Semantik, Boot/Ghost) durchdeklinieren; langfristiges **Zielbild**: weiter Sprachen auch durch **Verstehen** ohne zwingende Massen-API.
- Angebunden: **`archive/legacy-docs/Implementierung.backend.locale.md`** (Policy), **`archive/legacy-docs/Implementierungen.Architektur.md`** §2–§3.1, **`CLAUDE.md`**, **`docs/PREBOOT_PLAN.md`**, **`memory/system/decisions.md`**, **`memory/agents/orchestrator.md`**.

### Nächstes

- Session terminieren und Ergebnis nach **`memory/system/decisions.md`** + Architektur-Sections zurückfließen lassen.

---

## terra-035 — Pre-Boot Modal Barebones (0.027) (2026-05-06)

### Kurz

- **Frontend:** `PreBootModal.jsx` — Session-Overlay (einmal pro Tab bis Bestätigung), Tabs **Neustart** / **Laden**; Prefs → `localStorage` (`terra_preboot_config`); Snapshots → `GET /snapshots`, Restore → `POST /restore/{id}` + `loadStateFull(state)`.
- **Shared:** `frontend/src/api/base.js` — `getApiBase()`; `useWebSocket` nutzt dieselbe Basis-URL.
- **Docs:** `archive/legacy-docs/Implementierung.frontend.preboot.md`, `docs/PREBOOT_PLAN.md` Schritte markiert; `archive/legacy-docs/Implementierungen.Architektur.md` §5 Pre-Boot `[~]`; `CLAUDE.md` 0.027.001-alpha.
- **Nicht:** `POST /boot/start`, deferred Boot → **Phase 0.028**.

### Nächstes

- Backend **0.028**: Boot erst nach `/boot/start`; Frontend-Felder an Settings/Locale binden.

---

## terra-034 — Preseed: Cross-Wave Anchor-Dedupe (2026-05-06)

### Kurz

- **`build_preseed.py --all`:** pro normalisiertem Lemma nur noch **ein** Anchor-Eintrag (erste Wave in Sortierung `w*.json`); **85** spätere Duplikat-Anchors werden ausgelassen → **`preseed_v2.json`**: **2302** Anchors, `_meta.duplicate_anchors_skipped=85`, Relations **134051** (Builder).
- **Tests:** `tests/test_build_preseed_cross_wave.py` (Dedupe-Helfer); **`py -m pytest archive/legacy-terra/tests/ -q`** → **392** passed.
- **Doku/Memory:** `docs/PRESEED_ENRICHMENT_PLAN.md`, `docs/GHOST_MATERIALIZATION_PLAN.md`, `memory/system/decisions.md`, `memory/runtime/open-issues.md` (Duplikat-Issue **resolved** + neues **Runtime enrichment fetch idempotency**).
- **Runtime:** Keine neue API-Anfrage nötig, wenn Lemma **bereits** aus Preseed/KG existiert — Umsetzung noch **offen** (Backend).

### Nächstes

- Boot/Fetch-Pfad: Guard vor Netzwerk (`memory/runtime/open-issues.md`).

---

## terra-033 — ConceptNet ohne Projekt-Prio (2026-05-06)

### Kurz

- **Orch-Entscheidung:** öffentliche **ConceptNet-API** gilt als **unbestimmt nicht verfügbar**; **Layer 3** hat **keine aktive Roadmap-Priorität** (nur Backlog / sporadische Experimente).
- Aktualisiert: `memory/runtime/open-issues.md`, `memory/system/decisions.md` (neuer Decision-Eintrag), `memory/agents/orchestrator.md`, `docs/PRESEED_ENRICHMENT_PLAN.md` (Wave-Tabelle + Execution order), `CLAUDE.md`, `archive/legacy-docs/Implementierungen.Architektur.md` §3 / §3.1.
- Branch **`docs/conceptnet-deferred-no-priority`** → PR (`agent:docs`).

### Nächstes

- Fokus: **Ghost-Contract**, **Duplikat-Merge-Policy**, **`defined-by` Partial Fix**, **0.027 Pre-Boot** — nicht auf CN warten.

---

## terra-032 — KB-Quality-Tracking wiederhergestellt (2026-05-06)

### Kurz

- **`archive/legacy-docs/Implementierungen.Architektur.md` §3.1:** Tabelle **Quality, Retrofit und laufendes Tracking** — weak-quality (**9**, terra-030), `defined-by` Partial Fix (Primordials + w10/w11 Kern), Bulk-Retrofit (**~6558** nur noch als Legacy-Schätzung; Neu-Messung nach Partial Fix), Duplikat-Lemmata, CN-Retro, Ghost, fetch Status.
- **`memory/runtime/open-issues.md`:** neue Issues **defined-by partial fix** + **bulk relations retrofit**; bestehende Einträge mit **Tracking row** auf §3.1 verknüpft.
- **`CLAUDE.md`:** Baustelle Preseed-Qualität verweist auf §3.1 + Open Issues.
- Branch **`docs/track-preseed-quality-and-retrofit`** → PR (`agent:docs`).

### Nächstes

- Nach erstem Retrofit-Lauf: Zahlen mit `verify.py` / Builder aktualisieren und in `catchup.md` festhalten.

---

## terra-031 — Ghost-Materialisierung + Memory-/Doc-Sync (2026-05-06)

### Kurz

- Neuer Plan **`docs/GHOST_MATERIALIZATION_PLAN.md`**: Ghost-Ziele aus dem Preseed, Prioritäts-/Score-Skizze, Batch-Pipeline (async, Budget), UI-LOD/Edge-Limits, Merge-Policy-Optionen für **85** cross-wave Doppel-Lemmata.
- **`docs/PRESEED_ENRICHMENT_PLAN.md`:** Wellentabelle auf Ist-Stand **w02–w12 L1+L2 done**, CN retro pending; Verweis auf Ghost-Plan.
- **`memory/system/decisions.md`:** Decision „Ghost materialization — prioritized async pipeline (planned)“.
- **`memory/runtime/open-issues.md`:** Einträge Ghost-Queue + Duplicate-Anchor-Merge-Policy.
- **`memory/agents/orchestrator.md`:** aktueller EN-w00–w12-Stand + nächste Orchestrator-Schritte (Ghost/Contract/CN-Retro).
- **`archive/legacy-docs/Implementierungen.Architektur.md`:** Knowledge-Base-Tabelle mit aktuellem Preseed-/Pipeline-Status.
- Branch **`docs/plan-ghost-materialization-memory-sync`** → PR mit Label **`agent:docs`** (CI Gate „Validate Agent Labeling“).

### Nächstes

- `orch`: Minimal-Contract GhostCandidate + Score-Persistenz when Phase freigegeben; Merge-Policy für Duplikat-Lemmata festlegen.

---

## terra-030 — w12_discourse + PR #20 merged (2026-05-06)

### Kurz

- **Follow-up:** PR [**#20**](https://github.com/walkiger/terra-incognita/pull/20) (**w11**) nach CI mit Label **`agent:research`** auf **main** gemerged.
- **783** Lemmata **w12_discourse:** DataMuse async (**~4m35s**, **35157** DM-Relations, **780/783** mit Definition); WordNet Full-Rebuild (**~23 s**, NLTK serialisiert); ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **2387** Wörter (w00–w12), **138475** Relations (Builder); **9** weak-quality (**w01:** whom, whose, unless; **w04:** among; **w12:** whether, until, upon, against, yourself).
- Artefakte: `knowledge/enriched/en/w12_discourse.json`, `…/en_wordnet/w12_discourse.json`.
- Branch **`research/phase-026-w12-layer12`** → PR.

### Nächstes

- PR mergen für **w12**; **ConceptNet**-Retro **w00–w12** wenn API gesund; danach Phase **0.027** (Pre-Boot) laut Roadmap.

---

## terra-029 — w11_physics + WordNet Robustheit (2026-05-06)

### Kurz

- **Smoke w00:** DataMuse Checkpoint complete; WordNet OK; ConceptNet **SKIP** (Probe).
- **159** Lemmata **w11_physics:** DataMuse (~47 s async, **7879** DM-Relations laut Lauf) + WordNet Full-Rebuild (~20 s mit NLTK-Serialisierung); ConceptNet **SKIP** (Probe).
- **`fetch_wordnet.py`:** `None`-Synsets in Hypernym-/Hyponym-Ketten überspringen; **`WordNetError`/`ValueError`** bei kaputten Datenzeilen abfangen; **globaler Lock** um NLTK-Zugriffe (Reader ist bei parallelen Workern nicht threadsicher — vorher sporadische Crashes / `ValueError` beim `synsets("test")`-Probe).
- **`preseed_v2.json`**: **1604** Wörter (w00–w11), **91396** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w11_physics.json`, `…/en_wordnet/w11_physics.json`.
- Branch **`research/phase-026-w11-layer12`** → PR.

### Nächstes

- PR mergen; **w12_discourse** gleiches Muster; ConceptNet-Retro w00–w11 wenn API stabil.

---

## terra-028 — w10_number Layer 1+2 (2026-05-06)

### Kurz

- **131** Lemmata: DataMuse (~14m08s, **5035** DM-Relations) + WordNet (viele Adverbien **0 rels** im Log); ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **1445** Wörter (w00–w10), **80399** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w10_number.json`, `…/en_wordnet/w10_number.json`.
- Branch **`research/phase-026-w10-layer12`** → PR.

### Nächstes

- PR mergen; **w11_physics** gleiches Muster; ConceptNet-Retro w00–w10 wenn API stabil.

---

## terra-027 — w09_social Layer 1+2 (2026-05-06)

### Kurz

- **133** Lemmata: DataMuse (~16m30s, **5898** DM-Relations) + WordNet (einige Adjektive **0 rels** im Log); ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **1314** Wörter (w00–w09), **73689** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w09_social.json`, `…/en_wordnet/w09_social.json`.
- Branch **`research/phase-026-w09-layer12`** → PR.

### Nächstes

- PR mergen; **w10_number** gleiches Muster; ConceptNet-Retro w00–w09 wenn API stabil.

---

## terra-026 — w08_values Layer 1+2 (2026-05-06)

### Kurz

- **164** Lemmata: DataMuse (~19m45s, **6071** DM-Relations) + WordNet; ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **1181** Wörter (w00–w08), **65654** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w08_values.json`, `…/en_wordnet/w08_values.json`.
- Branch **`research/phase-026-w08-layer12`** → PR.

### Nächstes

- PR mergen; **w09_social** gleiches Muster; ConceptNet-Retro w00–w08 wenn API stabil.

---

## terra-025 — w07_action Layer 1+2 (2026-05-06)

### Kurz

- **153** Lemmata: DataMuse (~17m35s, **6888** DM-Relations) + WordNet (`should` **no_synsets** in WN-Log); ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **1017** Wörter (w00–w07), **57504** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w07_action.json`, `…/en_wordnet/w07_action.json`.
- Branch **`research/phase-026-w07-layer12`** → PR.

### Nächstes

- PR mergen; **w08_values** gleiches Muster; ConceptNet-Retro w00–w07 wenn API stabil.

---

## terra-024 — w06_language Layer 1+2 (2026-05-06)

### Kurz

- **153** Lemmata: DataMuse (~17 min, **6653** DM-Relations) + WordNet; ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **864** Wörter (w00–w06), **48128** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w06_language.json`, `…/en_wordnet/w06_language.json`.
- Branch **`research/phase-026-w06-layer12`** → PR.

### Nächstes

- PR mergen; **w07_action** gleiches Muster; ConceptNet-Retro w00–w06 wenn API stabil.

---

## terra-023 — w05_cognition Layer 1+2 (2026-05-06)

### Kurz

- **191** Lemmata: DataMuse (~23 min) + WordNet; ConceptNet **SKIP** (Probe).
- **`preseed_v2.json`**: **711** Wörter (w00–w05), **39303** Relations (Builder); **4** weak-quality unverändert (**w01:** whom, whose, unless; **w04:** among).
- Artefakte: `knowledge/enriched/en/w05_cognition.json`, `…/en_wordnet/w05_cognition.json`.
- Branch **`research/phase-026-w05-layer12`** → PR.

### Nächstes

- PR mergen; nächste Wave sobald `knowledge/waves/w06_*.json` existiert; ConceptNet-Retro w00–w05 wenn API stabil.

---

## terra-022 — w04_space Layer 1+2 (2026-05-05)

### Kurz

- **175** Lemmata (Wave nutzt u.a. `spaces`, nicht zwingend Singular `space`): DataMuse (~21 min) + WordNet; ConceptNet **SKIP**.
- **`preseed_v2.json`**: **520** Wörter (w00–w04), **28189** Relations (Builder); **4** weak-quality (**w01:** whom, whose, unless; **w04:** `among`).
- DataMuse meldete **174/175** mit Definition — prüfen welches Lemma ohne Def war (optional Nachziehen).
- Branch **`research/phase-026-w04-layer12`** → PR.

### Nächstes

- PR mergen; **w05** Cognition oder Pause.

---

## terra-021 — w03_existence Layer 1+2 (2026-05-05)

### Kurz

- **192** EN-Wörter: DataMuse (~23 min live fetch) + WordNet; ConceptNet **SKIP** (API-Probe).
- **`preseed_v2.json`**: **345** Wörter (w00–w03), **18199** Relations (Builder); **3** weak-quality weiterhin w01.
- Artefakte: `knowledge/enriched/en/w03_existence.json`, `…/en_wordnet/w03_existence.json`.
- Branch **`research/phase-026-w03-layer12`** → PR wie gewohnt.

### Nächstes

- PR mergen; optional **w04** gleiches Muster; ConceptNet wenn API gesund.

---

## terra-020 — PR #8 + #9 gemerged; w02 Layer 1+2 ohne ConceptNet (2026-05-05)

### Git / Governance

- **PR #8** auf **main** gemerged (Pipeline inkl. WN retro w00/w01, Relation Registry, Cursor Rules, Tests).
- **PR #9** auf **main** gemerged: `fetch_conceptnet.py` **API-Probe** — wenn unreachable → **exit 0**, keine Sidecar-Schreibung (`--force-fetch` / `TERRA_CONCEPTNET_FORCE=1` zum Erzwingen).

### Enrichment

- **w02_grammar_and_structure**: Layer **DataMuse** + **WordNet** durchgelaufen; **ConceptNet** übersprungen (Probe schlägt fehl wie erwartet).
- **`preseed_v2.json`**: **153** Wörter (w00+w01+w02), **7630** Relations gesamt (wie vom Builder geloggt); weiterhin **3** weak-quality w01 Einträge (`whom`, `whose`, `unless`).
- Branch für Daten: **`research/phase-026-w02-layer12`** → PR folgt.

### Nächstes

1. PR für w02-Daten mergen.
2. ConceptNet nachziehen wenn API stabil (`fetch_conceptnet.py` ohne Force-Skip).
3. **w03** oder nächste definierte Welle.

---

## terra-019 — Phase 0.026 Pipeline Branch + Multi-Queue Policy (2026-05-05)

### Kurz

- Branch **`research/phase-026-three-layer-pipeline`** → PR **#8** (`agent:research`, `agent:docs`): drei Layer im Repo — `fetch_wordnet.py`, `fetch_conceptnet.py`, Multi-Merge **`build_preseed.py`**, Backend **`lnn.py` / `spreading.py`** für sechs ConceptNet-Kanten, **`docs/RELATIONS.md`**, Tests (386 grün).
- **WordNet-Retro w00+w01** ausgeführt und committed; **`preseed_v2.json`** neu gebaut (**~4212 Relations**, 90 Wörter; weiterhin 3 weak-quality wie w01).
- **ConceptNet-Retro:** API **`api.conceptnet.io`** lieferte hier **502** — keine `enriched/en_conceptnet/*` Sidecars committed; **kein Blocker** für Merge von DM+WN (eigene Queue).
- **Multi-Queue / Dedupe / „Pop bei Seed“:** dokumentiert in **`docs/PRESEED_ENRICHMENT_PLAN.md`** § Multi-queue; **`memory/system/decisions.md`**; **`memory/runtime/open-issues.md`** (CN-Verfügbarkeit); Hinweis in **`backend/core/ghost.py`** vor Ghost-Queue.
- **Agent OS:** **`.cursor/rules/`** in Git (inkl. `SUBAGENT-DELEGATION-FALLBACK.mdc`); `.gitignore` lässt nur **`rules/`** zu, Rest von `.cursor/` lokal.
- Letzter Doc-Commit dieser Runde: **`b0610d1`** (Policy + Open Issue + Ghost-Kommentar).

### Nächste Schritte

1. PR **#8** nach grünem CI **mergen** (oder Review-Follow-up).
2. Wenn ConceptNet wieder erreichbar: `fetch_conceptnet.py --wave w00/w01` → **`build_preseed.py --all`** → Commit Sidecars + `preseed_v2.json`.
3. **w02** erste net-new Welle (DM+WN sofort; CN wenn API OK).
4. Runtime: später **enqueue/cancel**-Koordinator für Ghost/Fetch (Spec steht im Enrichment-Plan).

---

## terra-018 — Policy: w00+w01 Retro dokumentiert (2026-05-05)

### Dokumentation

**Pflicht vor w02:** w00 und w01 werden nach Einbau der Pipeline (WordNet + ConceptNet + Multi-Merge in `build_preseed.py`) **noch einmal** mit Layer 2 und 3 angereichert; Layer 1 DataMuse bleibt bestehen (optional Refresh nur bei Script-Änderung).

**Wo nachlesen:** `docs/PRESEED_ENRICHMENT_PLAN.md` — Abschnitt **Erste Wellen (w00 + w01): Re-Anreicherung**; aktualisiert auch `CLAUDE.md`, `archive/legacy-docs/Implementierungen.Architektur.md`, `memory/system/decisions.md`.

### Nächste Schritte (Implementierung)

1. `fetch_wordnet.py` / `fetch_conceptnet.py`
2. `build_preseed.py` Multi-Layer
3. w00 Retro → w01 Retro → Rebuild `preseed_v2.json`
4. danach w02

---


### Entscheidungen

**3-Layer EN Enrichment (festgelegt):**
  Layer 1: DataMuse (besteht, w00+w01 fertig)
  Layer 2: NLTK WordNet (zu bauen: fetch_wordnet.py)
  Layer 3: ConceptNet (zu bauen: fetch_conceptnet.py)

**NLTK OMW Experiment-Ergebnis:**
  DE, RU: 0/5 Wörter gefunden — nicht in OMW 1.4
  FR, IT, ES: 4-5/5 — nutzbar für spätere Mehrsprachigkeit
  EN: gut für Ontologie, schwach für Synonymbreite → Ergänzung zu DataMuse, kein Ersatz

**Neue Relationstypen (ConceptNet, noch nicht implementiert):**
  used-for, capable-of, has-a, at-location, causes, motivated-by
  → müssen in lnn.py + spreading.py registriert werden vor Produktiveinsatz

**Wellen-Reihenfolge festgelegt:**
  w02 → w03-w05 (Batch) → w06-w09 (Batch) → w10 (Priorität Math) → w11 (Priorität Physik) → w12

**Sprachen:** EN only aktiv. Mehrsprachigkeit zurückgestellt.

### Nächste Schritte
1. fetch_wordnet.py bauen + testen
2. fetch_conceptnet.py bauen + testen
3. build_preseed.py für Multi-Layer-Merge erweitern
4. w00+w01 re-enrichen mit Layer 2+3 (**Pflicht vor w02**, siehe `PRESEED_ENRICHMENT_PLAN.md`)
5. w02 als erste vollständige 3-Layer-Anreicherung

---

## terra-016 — Phase 0.026 w01: Preseed Enrichment (2026-05-05)

### Was implementiert wurde

**w01_questions_and_structure — 85 Wörter angereichert:**
  Enthält Inhaltswörter (question, mystery, discover) + Funktionswörter (and, or, not)
  Funktionswörter: geringere Confidence erwartet, als quality:weak markiert
  84/85 Wörter mit Definition (85/85 mit Relations)

**preseed_v2.json — aktualisiert:**
  w00 + w01: 90 Einträge gesamt
  3376 Relations gesamt
  1945 KG-Nodes + 3376 Edges beim Laden

**build_preseed.py — Fix:**
  available_waves() filtert jetzt nur Waves mit vorhandenen enriched-Dateien
  Verhindert Absturz wenn w02 noch nicht angereichert ist

### Weak-Quality-Einträge (erwartet)
- `whom` — pos=False, def=True (36 relations)
- `whose` — pos=False, def=False (23 relations)
- `unless` — pos=False, def=True (34 relations)

### Tests
333 grün

### Version
0.026.001-alpha

### Nächste Session
Phase 0.026-w02 — w02_grammar_and_structure (63 Wörter)

---

## terra-015 — Phase 0.026 w00: Preseed Rebuild (2026-05-05)

### Was implementiert wurde

**Preseed-Strategie geändert:**
  Altes preseed.json → reference/knowledge/preseed_legacy.json (read-only)
  Neues preseed_v2.json — von Grund auf neu, nur DataMuse-Daten

**fetch_datamuse.py — Upgrade:**
  --mode primordial: höhere Caps (syn:15, ant:8, hyp:8, trg:12, prp:10)
  enrichment_quality Score (0.0–1.0: Anteil Queries mit Ergebnissen)
  confidence Score (def-Qualität + Relation-Dichte)
  cross_ref Flag: Relation-Targets in derselben Wave markiert
  described-by Relations für Nouns (rel_jja umgekehrt)
  py-statt-python3 in CLI-Hilfe

**build_preseed.py — NEU:**
  Liest knowledge/enriched/en/{wave}.json
  Baut preseed_v2.json von Grund auf neu
  Quality Rules: synonym→similar-to, antonym→opposite, defWord→defined-by
  Validierung: pos + def + min 3 Relations pro Eintrag

**Ergebnis w00:**
  5 Primordials: time, space, soul, self, identity
  315 Relations, 264 KG-Nodes+Edges beim Laden
  Confidence: 1.0 für alle 5 Wörter
  0 schwache Einträge

### Tests
333 grün

### Version
0.026.000-alpha

### Nächste Session
Phase 0.026-w01 — w01_questions_and_structure (85 Wörter)

## Sessions 1–12 — HTML Prototyp (April–Mai 2026)

**Plattform:** Single-file browser HTML (`jarvis_v1.02-stable.html`)
**Ref:** `reference/jarvis_v1.02-stable.html` (10.714 Zeilen)

**Was entstand:**
- Drei-Pol-System (LNN ↔ EBM ↔ KG) vollständig im Browser
- CfC (Closed-Form Cell) LNN mit dynamischem Wachstum (32→128 dims)
- Hopfield EBM mit Well/Attraktor-Erkennung
- Tier-Hierarchie T0–T3 (Attraktor → Well → Konzept → Framework)
- Ghost-System, Typo-Detection
- Boot-Sequenz mit 10 LDV-Batches (~2237 Wörter)
- Drei-Pol-Koordination im systemTick (8Hz)
- Three.js 3D-Visualisierung + LNN-Background-Canvas
- IDB-Persistenz (vollständig, in Docs als "noch offen" falsch dokumentiert)
- Attractor Shadow System (⟡)
- PCD Anti-False-Attractor
- Inference Engine (R1–R4)
- Ghost-Cluster-Erkennung

**Dokumentation (Basis):**
`docs/ARCHITECTURE.md`, `archive/legacy-docs/Implementierungen.Architektur.md`, `docs/FETCHING.md`,
`docs/UI.md`, `docs/LOGGING.md`, `docs/jarvis_js.md`,
`docs/Foundation_Blueprint.md`

---

## Sessions 13–24 — HTML Verbesserungen (Mai 2026)

**Ref:** `docs/IMPLEMENTATION_PLAN.md` (Sessions 14–24 detailliert)

| Session | Was |
|---------|-----|
| 14 | Permanenz-Prinzip: makeDormant(), EBM_WELLS.delete()=0 |
| 15 | Stop-Word Tier-Exclusion + Pre-Boot Config Panel |
| 16 | TIER_CONFIG unified + renameTier() + T3 Status-Machine |
| 17 | Typo-Ghost Detection (Levenshtein vs LDV_ALL) |
| 18 | Cleanup: _lnnStep() unified, initUI(), ghost_created throttle |
| 19 | Attractor Shadow System + Ghost-Cluster Kern |
| 20 | LNN Background Canvas (konzentrische Tier-Ringe) |
| 21 | Shadow Rendering (⟡) + Detail-Panel |
| 22–23 | detectTierN(N) unified + Ghost-Cluster Förderung |
| 24 | Inference Engine (R1–R4) |

---

## Preseed-Sessions (Mai 2026)

**Ref:** `knowledge/preseed.json`, `knowledge/verify.py`

**Was entstand:**
- preseed.json (~2MB) — multilinguales Cold-Start-KB
- verify.py — Qualitätsprüfer (läuft am Session-Start)
- Wave-Struktur w00–w12 (13 Waves, ~2387 EN-Einträge geplant)
- Quality Rules: synonym→similar-to, antonym→opposite, defWord→defined-by
- Cross-Language Edge-Regeln (EN↔Foreign 0.88/0.45, Foreign↔Foreign 0.75/0.35)
- API Test Scripts: test_google_kg.py, test_conceptnet.py, test_datamuse.py

**Aktueller Stand preseed:**
- EN: 711/2387 (29.8%) — w00–w05 attempted, pre-quality-rules
- DE: 520/1240 (41.9%)
- FR/ES/IT/RU: Dummy-Struktur vorhanden
- Quality Issues: ~6.581 (fehlende relations)

---

## terra-001 — Neustart-Planung (Mai 2026, heute)


## terra-015 — Runtime Contracts Stabilisierung (2026-05-05)

### Ziel dieser Session
Branch `fix/runtime-contracts`: Backend- und Frontend-Runtime-Payloads an den
expliziten Contract aus `.agent-os/runtime-contracts-spec.md` angleichen, ohne
Phase 0.026 zu starten.

### Was implementiert wurde

Backend:
- `backend/api/models.py`: explizite DTOs für WebSocket-Envelopes,
  `RuntimeSummary`, `SystemEvent`, Full-State und Snapshot-Responses
- `backend/api/websocket.py`: `state_full` Envelope auf Connect, `delta`
  Envelope mit `tick`, `new_wells`, `events` und vollständigem `summary`
- `backend/api/routes.py`: `/state/full`, `/state/summary`, `/diagnostic`,
  `/snapshot`, `/snapshots`, `/restore/{snapshot_id}` auf gemeinsame Contracts
- `backend/core/tick.py`: EBM-Tick-Aufruf an aktuelle Signatur mit `lnn` und
  Growth-State angepasst

Frontend:
- `frontend/src/hooks/useWebSocket.js`: konsumiert `msg.type`, `msg.events`
  und `msg.summary`
- `frontend/src/store/systemStore.js`: normalisiert Runtime-Summary,
  Tier-Aliase und kanonische `SystemEvent`-Objekte
- `frontend/src/components/ChatPanel.jsx`: nutzt `SystemEvent.type`/`ts`
- `frontend/src/pages/DiagnosticPage.jsx`: bevorzugt `diagnostic.events`,
  akzeptiert `recent_events` nur als temporären Fallback und zeigt Snapshot-
  Restore-Fidelity an

CI:
- `.github/workflows/agent-ci.yml`: Backend-Tests laufen gegen echte Repo-Pfade
  und ignorieren den bekannten Boot-Test-Blocker; Frontend-Lint/Build bleiben
  im CI definiert.

### Gate-Status

- Meta: `GUARDED`
- Test gate: `PASS-WITH-GUARDS`
  - `py -3.11 -m pytest archive/legacy-terra/tests/api/test_runtime_contracts.py -q` → 5 passed
  - `py -3.11 -m pytest archive/legacy-terra/tests/api tests/db/test_persistence.py tests/core/test_tick.py -q` → 59 passed
  - frühere Non-Boot-Baseline: 360 passed, `tests/core/test_boot.py` ignoriert
  - bekannter Blocker: 7 Windows-UTF-8-Fehler in `tests/core/test_boot.py` plus
    ein hängender Boot-Await-Test; nicht runtime-contract-bedingt
  - Frontend-Validierung wurde zuvor vom Implementation-Agent über gebündeltes
    Node als grün gemeldet; letzte Revalidierung konnte lokal nicht laufen, weil
    npm/corepack/lokale Wrapper nicht verfügbar waren
- Security: `PASS` nach Diagnostic-Event-Follow-up

### Dokumentation / Memory

- `archive/legacy-docs/Implementierung.backend.api.md`: Runtime-Contract-Modelle,
  Diagnostic-Verhalten und Snapshot-Fidelity aktualisiert
- `archive/legacy-docs/Implementierungen.Architektur.md`: API Runtime Contracts als aktueller,
  implementierter Status ergänzt
- `memory/`: Runtime-Contract-Entscheidung, Boot-Test-Guard und Phase-0.026-
  Blocker aktualisiert

### Offene Punkte

- Audit-Gate und PR-Erstellung stehen noch aus.
- Phase 0.026 bleibt blockiert, bis PR-Lifecycle und Audit abgeschlossen sind.
- Nach Lifecycle-Abschluss: nächster Branch
  `feature/phase-0026-preseed-enrichment`.

## terra-014 — DataMuse Integration + Relations + Docs Cleanup (2026-05-04)

### Docs aufgeräumt
Gelöscht (veraltet):
  CODE_AUDIT.md, UPDATE_PLAN.md, UI.md, VISUAL_COMPARISON.md,
  HTML_UI_AUDIT.md, IMPLEMENTATION_PLAN.md

Archiviert → reference/docs/:
  Jarvis_Foundation_Blueprint.md

(Hinweis 2026-05-06 / terra-048: archivierte Python‑Phasen‑Checkliste unter reference/docs/ wieder entfernt — Landing jetzt `archive/legacy-docs/Implementierungen.Architektur.md` + `catchup.md`.)

Neu erstellt:
  docs/DATAMUSE.md — vollständige API-Doku + 14-Query-Mapping
  docs/RELATIONS.md — vollständige Relationstypen-Registry

### Neue Relationstypen (aus DataMuse)
  has-instance (rel_gen) — Hyponyms, 0.35
  comprises    (rel_com) — Holonyms, 0.40
  describes    (rel_jja) — Noun für Adjektiv, 0.30

  lnn.py: _REL_ATTENTION um alle 3 erweitert
  spreading.py: _REL_SPREAD um alle 3 erweitert

### fetch_datamuse.py (vollständig neu)
  12 DataMuse-Queries pro Wort (kein Google KG mehr)
  Speichert ALLE DataMuse-Daten:
    pos, def, defs_all, defWords, frequency
    synonyms, antonyms, hypernyms, hyponyms, meronyms, holonyms
    triggers, properties, means_like, followers, predecessors, describes
    relations (vollständig dedupliziert, alle Typen)
  ETA-Anzeige während Processing
  Checkpoint alle 10 Wörter
  ml-Query nur wenn wenige Synonyme
  jja-Query nur für Adjektive

### Neue Tests (noch nicht alle grün — API-Signaturen komplex)
  test_spreading.py (8 Tests)
  test_ghost.py (9 Tests)
  test_wells.py (7 Tests)
  test_pcd.py (8 Tests)
  test_preseed.py (6 Tests)

### Bestehende Tests: 320 grün

## terra-013 — Planung: Preseed Enrichment + Pre-Boot (2026-05-04)

### Analyse

Preseed-Zustand:
  2387 EN Wörter in 13 Waves (w00–w12)
  1676/2387 (70.2%) ohne def/relations/pos — nur Wortlisten
  Sprachen: EN/DE/FR/ES/IT/RU

### Neue Ordnerstruktur (knowledge/)
  waves/        — Skelette: Wortlisten pro Wave (13 JSON-Dateien)
  enriched/en/  — Angereicherte Daten pro Wave (Google KG + DictAPI)
  scripts/      — extract_waves.py, fetch_google_kg.py, merge_enriched.py

### Pre-Boot Config Panel
  Analysiert HTML-Referenz (Z.10387–10650)
  Options: Sprachen, API-Speed, Startmodus, Boot-Länge, Laden
  Plan: Frontend-Modal (Phase 0.027) + Backend /boot/start (Phase 0.028)

### Docs erstellt
  docs/PRESEED_ENRICHMENT_PLAN.md (220 Zeilen)
  docs/PREBOOT_PLAN.md (154 Zeilen)
  CLAUDE.md: aktualisiert

## terra-012 — UI Phase 7: SystemControls + ChatEvents + Tooltip (2026-05-04)

### Was implementiert wurde

**WellPanel.jsx — vollständig neu:**
  Struktur nach HTML-Referenz: Frameworks → Konzepte → System Controls → Wells
  Alle Sektionen einklappbar (defaultOpen per Sektion)
  System Controls integriert (nicht mehr als separates Panel):
    Live Status Bar: E/τ/T/iD
    Cognitive Mode: 6 Buttons (DORMANT/EXPLORING/FOCUSING/DREAMING/CRYSTAL/ENCOUNTER)
    Tier Status: T0/T1/T2/T3/dormant Counts
  Well-Format: ◆ name · ×seen · E=energy · members+

**ChatPanel.jsx:**
  System-Events aus WS-Delta werden ins Chat-Log injiziert:
    well_born → "◆ well born: 'name' E=energy, members=N"
    tier_born → "⟡ tier N born: name"
    fetch → "↓ [Fetch] word"
    error → "✕ error: msg"
  Jeder Event-Typ hat eigene Farbe + Symbol
  Textarea statt input (Crimson Pro, multi-line ready)

**KGLabels.jsx:**
  Hover-Tooltip (createPortal → document.body):
    Node-Name (grün, fett)
    POS, Energie (farbkodiert), Degree
    Ghost-Marker
    Definition (erste 90 Zeichen)

**systemStore.js:**
  recentEvents[] (max 100, FIFO)
  pushEvent() Action

**useWebSocket.js:**
  msg.events[] aus Delta → pushEvent() per Event

### Tests
320 grün

## terra-011 — UI Phase 6: FilterBar + NavBar + ZoomOverlay + Diagnostic (2026-05-04)

### Was implementiert wurde

FilterBar.jsx: vollständig nach HTML-Referenz
  NODES: ghosts/energy/tension/latest/active + Live-Count-Badges
  TIERS: T1/T2/T3/seed + Live-Count-Badges
  Ghost-Modes: NONE/RECENT 15s/HOT ≥3/NEAR WELLS/ALL
  Locate, Edge-Brightness Slider

NavBar.jsx (NEU):
  fit/reset/top/front/side/in/out/orbit — vertikal rechts oben
  OrbitControls via controlsRef

ZoomOverlay.jsx: vollständig
  T0 Attraktor-Namen, T1 Well-Namen+Energie, T2 Konzept-Namen
  LNN-Graph 160×36px: velocity-Linie + h-State Spektrum
  Minimap: Kanten (typ-farbig) + Kamera-Kreis + Fadenkreuz

DiagnosticPage.jsx (NEU — /diagnostic Route):
  System-Übersicht (alle State-Werte)
  Snapshot-Liste mit Restore-Button
  Event-Log mit Filter
  Export als JSON (⬇ export JSON)
  Snapshot speichern (⬇ snapshot)
  RAW Diagnostic JSON (einklappbar)

Header: ⬇ diag Button → öffnet /diagnostic in neuem Tab
main.jsx: pathname-basiertes Routing (/diagnostic → DiagnosticPage)

### Tests
320 grün

## terra-010 — UI Phase 4: ShaderMaterial + Grün + Node-Click (2026-05-04)

### Was implementiert wurde

**KGCanvas.jsx — komplett neu:**
  ShaderMaterial soft-circles (smoothstep 0.30→0.50)
  Perspective-scaling: 280.0 / -mv.z
  Node-Farben nach HTML-Referenz:
    Ghost: #ff6b35 orange, T0: #ff4400, T1: #00a8e8, T2: #00e8c8, T3: #ffe040
    recently active: cyan, new: weiß, high-energy: rot, default: grünlich
  Node-Click: onClick(e.index) auf Points + onClick(e.instanceId) auf Kugeln
  Hover: cursor:pointer
  Tier-Nodes bleiben als Kugeln (InstancedMesh) für Erkennbarkeit

**Header.jsx:**
  Primärfarbe #00e87a (grün) überall
  Titel '*still unknown*' serif 18px mit Glow
  Metriken: E_sys, τ, nodes, edges, ghosts, tension
  Session-Uhr (hh:mm:ss)
  Phase-Badge

**NodeDetailPanel.jsx:**
  URL-Fix: dynamische API-URL (kein hardcoded localhost)
  Slide-in von rechts (transform translateX, 0.3s)
  Vollständig: State, Provenance, Definition, Tier-Badge, Relationships

**FilterBar + WellPanel:** Grün statt Blau

**Docs:**
  CLAUDE.md: v0.025.003-stable
  HTML_UI_AUDIT.md: 467 Zeilen exakte Dokumentation
  VISUAL_COMPARISON.md: 3 Screenshots analysiert
  IMPLEMENTATION_PLAN.md: 298 Zeilen Implementierungsplan

### Tests
320 grün

### Nächste Schritte (IMPLEMENTATION_PLAN.md Prio 2–7)
Prio 2: Filter-Bar Count-Badges + latest/active/T1/T2/T3
Prio 3: Nav-Bar (fit/reset/orbit/follow)
Prio 4: Zoom-Overlay Attraktor/Well-Namen + LNN-Graph
Prio 5: System Controls Sidebar

## terra-009 — HTML UI Audit + 3D Spheres + Edge Weights (2026-05-04)

### HTML UI Audit (docs/HTML_UI_AUDIT.md)
Vollständige Dokumentation jarvis_v1.02-stable.html (467 Zeilen):
- Farbschema: --g:#00e87a (Grün), --o:#ff6b35 (Orange), --c:#00c8de (Cyan)
- ShaderMaterial mit perspective Node-Größe
- Ghost-Farbe: orange (#ff6b35), nicht grau
- Zoom-Overlay: tier-adaptive Stats + LNN-Graph 160×36px
- drawMinimap(): Kanten + Kamera-Kreis + Klick-Navigation
- renderLabelOverlay(): deg-threshold scaling, zoom-culling
- drawLNNCanvas(): lnn.traj3 3D-Trajektorie
- 23 fehlende/unvollständige Features dokumentiert

### Code-Änderungen
KGCanvas.jsx — InstancedMesh + SphereGeometry:
  Echte 3D-Kugeln (SphereGeometry 10×8 Segmente)
  Größe: base + energy*6 + sqrt(deg)*0.4 + tier+2.5
  Ghost: r=0.8, orange-gedimmt (#ff6b35 × 0.35)
  MeshStandardMaterial: roughness=0.4, metalness=0.15
  2x PointLight: warm(0.8) + kalt cyan(0.4)

Kanten: vertexColors, Typ-Farbe × Gewicht × edgeBrightness
  similar-to=grün, co-activated=cyan, opposite=rot,
  is-a=gelb, hebbian=teal, implies=violet

FilterBar: Edge-Brightness Slider (0–100%, default 55%)
systemStore: edgeBrightness state + setEdgeBrightness()

### Version
0.025.002-stable

### Nächste Prioritäten (aus Audit)
1. Primärfarbe Grün (#00e87a) statt Blau
2. Zoom-Overlay tier-adaptive Inhalte vervollständigen
3. Filter-Bar: ✦ latest, ⚡ active, T1/T2/T3 Buttons
4. Nav-Bar (Kamera-Buttons rechts)

## terra-008 — UI Phase 2/3 + ZoomOverlay + Live Deploy (2026-05-04)

### Was implementiert wurde

**Live Deployment (Oracle Cloud + Cloudflare):**
  - VM1 terra-a: 92.5.80.186, Ubuntu 22.04, Docker, E2.1.Micro
  - cloudflared Quick Tunnel läuft
  - System live erreichbar, Boot-Sequenz verifiziert
  - Bug fix: Request Type Annotation in routes.py

**UI Phase 2 — Live KG:**
  - KGCanvas: useFrame → Positionen + Farben live per Frame
  - LNNCanvas: Tier-Dots rotieren, Pulsing mit sin-Wave, E_sys Glow
  - NodeDetailPanel: Gradient Header, hover Kanten-Zeilen

**UI Phase 3 — Labels + LNN Strip:**
  - KGLabels.jsx: HTML-Overlay, THREE.Vector3.project → 2D Labels
    Top-40 Nodes nach Priorität, Tier-Farben, klickbar
  - LNNStrip.jsx: 90px Bar-Chart wie HTML-Referenz
    Tier-Kanal-Backgrounds, τ-Trace, Velocity-Trace

**ZoomOverlay:**
  - Erscheint wenn Kamera-Abstand > 420
  - Info-Panel: phase, nodes, E_sys, tension, τ, iD, ghost, tier
  - Minimap Canvas 180×150px: alle Nodes als farbige Punkte
    Tier-Nodes größer + Glow, Ghost gedimmt

**WS-Fix:**
  - Dynamische URL-Erkennung (lokal vs Cloudflare)
  - nginx.conf: /ws-backend → backend:8000/ws

**Gelöscht:**
  - docs/jarvis_js.md (veraltet)

### Tests
320 grün (unverändert)

## terra-007 (Abschluss) — Phase 0.025 Deployment Checkliste (2026-05-04)

### Checkliste — alle grün
✅ Alle Imports OK (backend.main, core, db, api)
✅ requirements.txt vollständig (fastapi, uvicorn, numpy, duckdb, httpx, pydantic)
✅ DB Init: 2 Migrations, 8 Tabellen (frische DB)
✅ /health → {"status": "ok"}
✅ Frontend Build sauber (583 Module, 304kB gzip)
✅ 320 Tests grün

### Version
0.025.000-stable — Tag v0.025.000-stable

### Alle Docs aktuell
CHANGELOG.md, CLAUDE.md, catchup.md, archive/legacy-docs/Implementierungen.Architektur.md, ARCHITECTURE.md

### Nächste Session
Phase 0.026 — R-GCN Hebbian (Post-1.0)

## terra-007 — Deployment Vorbereitung Phase 0.021–0.024 (2026-05-04)

### Was implementiert wurde

Phase 0.021 — Requirements + Environment:
  requirements.txt, requirements-dev.txt (pinned versions)
  .env.example (alle TERRA_* Variablen dokumentiert)

Phase 0.022 — Docker:
  Dockerfile.backend (python:3.12-slim, uvicorn, healthcheck)
  Dockerfile.frontend (node:20 build → nginx:alpine serve)
  docker-compose.yml (backend + frontend + volume terra_data)
  docker-compose.prod.yml (prod overrides)
  docker/nginx.conf (SPA fallback + WS proxy)
  .dockerignore

Phase 0.023 — Docs:
  README.md (Quick Start, Architektur, API-Tabelle, Stack)
  docs/DEPLOYMENT.md (env vars, backup/restore, troubleshooting)

Phase 0.024 — CI (GitHub Actions):
  .github/workflows/test.yml (pytest auf push/PR)
  .github/workflows/build.yml (Docker build check)

### Version
0.024.000-alpha

### Nächstes
Phase 0.025 — Deployment-Checkliste + v0.025.000-stable Tag

## terra-006 — Paper-Review + _lnn_focus GAT-Upgrade (2026-05-04)

### Paper-Review (5 Papers)
1. Patil et al. (2026) — KGR vs. VSR: validiert KG-Retrieval-Architektur
   KGR: 71–75% weniger Energie, vergleichbare Recall. Unser overlap_ratio() = α-Term.
2. Zeng et al. (2025) — ECL-GSR: validiert EBM + Contrastive Learning
   Hopfield ≈ generativer Term. Hebbian ≈ positive Pairs. PCD ≈ SGLD negatives.
3. Antonesi et al. (2025) — Hybrid Transformer + LNN: validiert CfC-Reservoir
   Adaptives τ besser als statischer spectralRadius.
4. Guan et al. (2023) — PI-INN: Bayessche Inverse Probleme
   Post-1.0: Uncertainty Quantification für Inference-Ergebnisse.
5. Cai et al. (IJCAI 2023) — TKGC Survey: temporal KG
   valid_from + last_seen direkt in 0001_initial.sql (kein live System → keine Migration).
6. GNN Review — theoretische Einordnung: MPNN, GAT, R-GCN

### Code-Änderungen
_lnn_focus(): GAT-style Multi-Head Attention (Veličković et al. 2018)
  Head 1: softmax über KG-Nachbarn × rel_type_weight × GCN-deg-norm
  Head 2: softmax über Tier-Kanäle × tier_weight
  Fusion: gewichtetes Mittel (w1 skaliert mit Nachbar-Anzahl)
  _REL_ATTENTION: similar-to=1.2, co-activated-with=1.0, opposite=0.4, ...

0001_initial.sql: valid_from + last_seen in edges

ARCHITECTURE.md: Theoretische Einordnung mit Paper-Referenzen  
Post-1.0-Roadmap‑Spuren: spätere Phasen in Session‑Logs / `archive/legacy-docs/Implementierungen.Architektur.md` / Epik‑Plan (`docs/ORCH_IMPLEMENTATION_PLAN.md`), nicht mehr als separates Phasen‑Archiv

### Tests
320 grün (unverändert)

## terra-005 — Frontend Phase 0.019/0.020 (2026-05-04)

### Was implementiert wurde

Phase 0.019 — Concept/Framework Panels + Settings:
  - ConceptPanel.jsx: T2 Konzepte, sortiert nach strength, fade-in wenn vorhanden
  - FrameworkPanel.jsx: T3 Frameworks, Tier-Symbol ⟺
  - SettingsPanel.jsx: Collapsible, Cognitive Modes, LNN Diagnostics, Actions
    Inference run: POST /inference/run
    Snapshot: POST /snapshot
  - WellPanel.jsx: integriert ConceptPanel + FrameworkPanel
  - App.jsx: SettingsPanel über ChatPanel (float)

Phase 0.020 — Force-Directed Layout (simStep3D):
  - frontend/src/layout/forceLayout.js
  - simStep3D(): Abstoßung (Barnes-Hut approx), Federkraft, Tier-Gravitation
    REPULSION=800, SPRING_K=0.015, SPRING_LEN=80, DAMPING=0.85
    Throttle: n>200→50%, n>500→20%
  - camFocusSet(members, positions): Centroid + Radius für Kamera-Fokus
  - resetLayout(), getPositions()
  - KGCanvas.jsx: useFrame → simStep3D() pro Frame, layoutRef für Positionen

### Version
0.020.000-alpha

### Nächstes
Phase 0.021+ — Deployment-Vorbereitung, final Frontend-Polish

## terra-004 — Frontend Phase 0.017/0.018 (2026-05-04)

### Was implementiert wurde

Phase 0.017 — React + R3F KG Visualisierung:
  - KGCanvas.jsx: Three.js 3D KG, Tier-Farben, Node-Größe, Edges
  - WellPanel.jsx: Wells-Liste, Tier-Symbole + Farben
  - ChatPanel.jsx: /encounter API, System-Msgs
  - Header.jsx: Phase, Tiers T0–T3, τ, E_sys, Op-Glyph
  - systemStore: Zustand, loadStateFull, applyDelta
  - useWebSocket: WS-Hook, Auto-Reconnect 2s

Phase 0.018 — LNN Canvas + Filter + Node Detail:
  - LNNCanvas.jsx: Canvas2D Radial-Heatmap hinter KG
    Konzentrische Ringe pro Tier-Kanal (T0–T3)
    Pulsiert mit lnn_norm und Tier-Aktivität
  - FilterBar.jsx: ghost/wells/pressure/tension + Search + Ghost-Mode
    getFilteredSet(): highlighted nodes berechnen
    KGCanvas: dimFactor per filter/selection
  - NodeDetailPanel.jsx: Overlay bei Node-Klick
    Tier-Badge, Definition, Kanten-Liste, fetch von /node/{word}
  - BootProgress.jsx: Fortschrittsanzeige bis 'awaiting'

### Version
0.018.000-alpha

### Nächstes
Phase 0.019 — Concept/Framework Panels + Settings
Phase 0.020 — Force-Directed Layout (simStep3D)

## terra-003 — Backend vollständig: Phase 0.012–0.016 (2026-05-04)

### Was implementiert wurde

| Phase | Was | Tests |
|-------|-----|-------|
| 0.012 | processWord + fetchDefinition (dictionaryapi.dev) | T46–T53 |
| 0.013 | Boot Waves: _fetch_wave + _batch_pause (echte API) | T50–T53 |
| 0.013b | Logging System: addEvent() + 4 Modi + EventBuffer | T-Log-1–10 |
| 0.013c | DB Migration Infrastructure (DuckDB, forward-only) | T-Mig-1–7 |
| 0.014 | Tier System: Well Lifecycle, detectTierN(2/3), Shadows | T54–T60 |
| 0.015 | PCD + Inference Engine R1–R4 | T61–T69 |
| 0.016 | DuckDB Persistence + REST Endpoints | T-DB-1–6 |

### Architektur-Entscheidungen festgehalten
- LNN startet sofort bei Boot (B=256) — T0 triggert KEIN Wachstum
- STOP_WORDS_38 in backend/core/constants.py (kein circular import)
- fetch_process_word als Module-Level Alias für Testbarkeit
- Snapshot-Trigger: manual/phase_change/tier_born/session_end/interval
- Event-Flush alle 500ms → DuckDB (addEvent() bleibt sync/RAM)

### Version
0.016.000-alpha — Backend vollständig stabil

### Tests
320 grün (ohne test_boot.py wegen echtem API-Aufruf)

### Nächste Session
Phase 0.017 — Frontend React + R3F
Vor 0.017: UI.md lesen → React/R3F Components Spec

## terra-002 — EBM Design-Session + Codebase-Audit (2026-05-04)

### Ziel dieser Session
Design-Entscheidungen für EBM Wells/Attraktoren/Shadows festhalten.
Anschließend Codebase-Audit: Docs vs. Code vs. Stand.

### Was entschieden und dokumentiert wurde
- `overlap_ratio` = Containment `|A∩B|/min(|A|,|B|)`, Schwelle 0.70 (non-negotiable)
- `seed_attractor_candidates()`: Score 60% LNN + 40% KG, normalisiert, non-deterministisch
- `similar-to`/`opposite` = Gewicht 3.0 beim zweiten Token (semantische Pole)
- `find_energy_wells()` entscheidet Geburt — Seeder ist blind
- Shadow-System generalisiert: TN → T(N+1) für alle Tiers
- `SHADOW_OVERLAP_THRESHOLD = 0.20` (CFG) — > 0 zu permissiv
- Shadow-source_store: T0/T1 → ebm_wells, T2+ → tier_stores[N-1]

### Audit-Ergebnis

**Code-Stand: Phase 0.005 ✅ — 89 Tests grün nach Fixes**

Divergenzen gefunden und behoben:

| # | Problem | Fix |
|---|---------|-----|
| 1 | `_overlap()` in ebm.py war Jaccard (`max`), nicht Containment (`min`) | Gefixt → `overlap_ratio()` |
| 2 | settings.py `ebm_theta=0.5` statt 0.18 | Gefixt |
| 3 | settings.py fehlte `attractor_lnn_weight`, `shadow_overlap_threshold` | Ergänzt |
| 4 | ARCHITECTURE.md §8 beschrieb Phase-0.014-Features als aktuell | Phase-Tag ergänzt |
| 5 | CLAUDE.md fehlte Regel "Docs beschreiben nur implementierten Code" | Regel 9 hinzugefügt |

### Tests
- 89 Tests grün ✅ (83 vorher + 6 neue overlap_ratio Tests)

### Version
0.005.001-alpha (Bugfix: Jaccard → Containment)

### Nächste Session
Phase 0.005b — LNN Architektur-Update (B=256, hD=iD, neue Dimensionsformel)
Phase 0.005c — Locale + Pre-Boot Config System

**Repo:** `https://github.com/walkiger/terra-incognita` (privat)
**Commits:** cacf4fd (main), Tag: v0.001.000-alpha

### Was entschieden wurde

**Tech Stack:**
- Backend: Python 3.12 + FastAPI + asyncio + multiprocessing
- LNN/EBM: numpy (MLX-kompatibel designed für spätere Migration)
- KG: Custom dict + numpy (kein NetworkX)
- Storage: **DuckDB** (embedded, columnar, skaliert 16k→10M+ Nodes)
- Frontend: React 18 + Vite + React Three Fiber + Zustand + Tailwind
- Deployment: lokal + Cloudflare Tunnel (dual orange cloud)

**Versionsschema:** `MAJOR.FEATURE.FIX[-LABEL]`
- 0.001.000-alpha = jetzt
- 1.0.0 = production-ready, keine bekannten Bugs

**Storage-Entscheidung:** DuckDB von Anfang an
- Snapshots: vollständig, alle Tabellen (nodes, edges, wells, tier_objects, events, sessions)
- Events: append-only, sofort per addEvent()
- Time-Travel: durch Schema kostenlos

**WebSocket-Protokoll:** Delta-Ticks (8Hz) + Full-State on Connect + Summary-Block

**Deployment:** Lokal + Cloudflare Tunnel (Pages für Frontend, Tunnel für Backend)
- GitHub Actions → SSH → git pull + reload
- systemd: terra.service + terra-tunnel.service

### Was gebaut wurde
- Repo-Struktur (docs/, knowledge/, reference/, scripts/, .claude/)
- CLAUDE.md (1276 Zeilen, wird heute überarbeitet)
- CODE_AUDIT.md (vollständige Inventur jarvis_v1.02-stable.html)
- ARCHITECTURE.md (Python-Klassen ergänzt)
- archive/legacy-docs/Implementierungen.Architektur.md + Session-Protokoll (historische Python-Phasen)
- Anweisungen.md, catchup.md, archive/legacy-docs/Implementierungen.Architektur.md (heute)

### Was als nächstes kommt
1. Phase 0.002 — Backend-Skeleton (FastAPI + Config)
2. Phase 0.003 — KG data structures
3. Phase 0.004 — LNN: CfC

**Offene Docs die noch fehlen:**
- archive/legacy-docs/Implementierungen.Architektur.md → erstellt heute
- archive/legacy-docs/Implementierung.backend.api.md → Beispiel erstellt heute
- UI.md → React/R3F Komponenten (erst vor Phase 0.017 nötig)

---

## terra-006 — Architektur-Entscheidungen (2026-05-04)

### Ziel dieser Session
Architektur festlegen: LNN-Dimensionen B=256, hD=iD, Locale-System, find_energy_wells() als universelle Tier-Detection.

### Was entschieden wurde

**LNN Dimensions-Formel (festgelegt):**
- B = 256 (Basis-Einheit, konfigurierbar)
- `dim(N) = B × (1 + N×(N+1)/2)`
- hD = iD immer synchron
- T0=256, T1=512, T2=1024, T3=1792, T4=2816, T5=4096, T6=5632
- T0 ist Startpunkt — LNN entsteht bei erstem Attraktor
- CPU bis ~T3/T4, T5+ → MLX/GPU Migration geplant

**find_energy_wells() — universelle Tier-Detection (bestätigt):**
- Eine Funktion für T0→TN — kein totes Code-Ende
- Offenes Ende: T4, T5, T6+ entstehen durch dieselbe Logik
- detectTierN(N) als Regelname ersetzt durch find_energy_wells()

**Locale + Pre-Boot Config System (neu):**
- `backend/config/locale.py` — alle Labels/Namen/Farben
- `backend/config/settings.py` erweitert — alle num. Parameter
- Tier-Namen, Op-Labels, System-Labels lokalisierbar
- B, tick_hz, ebm_theta, well_grace_s etc. alle konfigurierbar
- Prinzip: nichts hardcoded außerhalb dieser beiden Dateien

### Was implementiert wurde
- [docs] CLAUDE.md — vollständig überarbeitet (8 Regeln, neue Architektur-Tabelle)
- [docs] Anweisungen.md — Non-Negotiables erweitert, Locale-Sektion hinzugefügt
- [docs] archive/legacy-docs/Implementierung.backend.locale.md — neu erstellt
- [docs] archive/legacy-docs/Implementierungen.Architektur.md — Phase 0.005b + 0.005c + Locale hinzugefügt

### Nächste Sessions
- **0.005b:** lnn.py refactoren — B=256, hD=iD, neue Wachstumsformel + Tests update
- **0.005c:** locale.py erstellen, settings.py erweitern + Tests
- **0.006:** systemTick 8Hz

---

## terra-005 — Phase 0.005 Hopfield EBM (2026-05-04)

### Ziel dieser Session
Hopfield EBM: WellObject, hopfield_energy, find_energy_wells, make_dormant, ebm_tick.

### Was implementiert wurde
- [docs] `archive/legacy-docs/Implementierung.backend.core.ebm.md` — vor Code
- [feat] `backend/core/ebm.py`
  - `WellObject` dataclass — frozenset members, status-machine, history
  - `hopfield_energy()` — E = -½ Σ w_ij × s_i × s_j, Interferenz-Penalty
  - `hopfield_relax()` — 30-Iter Relaxation, Aktivierungs-Update
  - `find_energy_wells()` — LNN+degree Seeds, 70%-Overlap-Merge, Create/Update/Revival
  - `make_dormant()` — einziger Dormant-Übergang, kein pop/delete
  - `adapt_ebm_theta()` — p70 der Edge-Weights, min 0.05
  - `ebm_tick()` — Boltzmann-Perturbation, Accept/Reject, lnn_step on accept
- [test] `tests/core/test_ebm.py` — T21–T29 (22 Tests)

### Tests
- T21-T22: WellObject defaults + frozenset — ✅
- T23-T24: hopfield_energy Formel + Vorzeichen — ✅
- T25: find_energy_wells erstellt Wells — ✅
- T26-T27: make_dormant + kein Delete — ✅
- T28: adapt_ebm_theta p70 — ✅
- T29: ebm_tick no-crash + node-count — ✅
- **80/80 gesamt grün**

### Version
0.005.000-alpha — 3 Commits

### Nächste Session
Phase 0.006 — systemTick 8Hz (kg_spontaneous_prop + lnn_to_kg_hebbian + _apply_tier_weight_cascade).

---

## terra-004 — Phase 0.004 CfC LNN (2026-05-04)

### Ziel dieser Session
CfC Liquid Neural Network mit step/grow + einzigem Einstiegspunkt lnn_step().

### Was implementiert wurde
- [docs] `archive/legacy-docs/Implementierung.backend.core.lnn.md` — vor Code angelegt
- [feat] `backend/core/lnn.py`
  - `word_vector(word, dim)` — deterministischer hash-basierter Einheitsvektor, gecached
  - `CfC` — step (f/g/s/h_new), grow (Wfi/Wgi expand, alte Gewichte erhalten), norm/delta/velocity properties
  - `lnn_step()` — einziger Einstiegspunkt, Noise-Step bei unbekanntem Wort
  - `build_lnn_input()` — Multi-Tier Vektor, Wachstums-Trigger
  - `_on_tier_stable()` — einzige grow()-Stelle, T0 nie
  - `_lnn_focus()` — Aufmerksamkeits-Score [0.3, 2.0]
- [test] `tests/core/test_lnn.py` — T12–T20 (28 Tests)
- Fix: Biases mit kleinen Random-Werten init (bs=0 → h bleibt Null bei h=0)

### Tests
- T12: init dims/shapes — ✅
- T13: step() ändert h — ✅
- T14: wrong dim raises — ✅
- T15: norm = L2(h) — ✅
- T16: delta nach step — ✅
- T17: grow() expand + alte Gewichte — ✅
- T18: lnn_step noise/known — ✅
- T19: build_lnn_input Länge — ✅
- T20: T0 wächst nicht, T1 wächst, idempotent — ✅
- **58/58 gesamt grün**

### Version
0.004.000-alpha — 3 Commits

### Nächste Session
Phase 0.005 — Hopfield EBM. Zuerst `archive/legacy-docs/Implementierung.backend.core.ebm.md` anlegen.

---

## terra-003 — Phase 0.003 KG Data Structures (2026-05-04)

### Ziel dieser Session
KnowledgeGraph in-memory, preseed.json Loader.

### Was implementiert wurde
- [docs] `archive/legacy-docs/Implementierung.backend.core.kg.md` — vor Code angelegt
- [feat] `backend/core/kg.py` — KgNode, KgEdge, AdjEntry, KnowledgeGraph
  - O(1) Node-Lookup (dict), O(neighbors) adj-Lookup
  - kg_add_node (idempotent), kg_add_edge (idempotent via edge_map)
  - system_energy(), active_system_energy()
  - _check_expand() — auto-expand bei 90% Kapazität
- [feat] `backend/core/preseed.py` — load_preseed(path, kg)
  - EN-Nodes mit vollständigen Relations
  - Foreign-Nodes mit cross-language 'translation' Edges (0.88/0.75)
  - seed_derived=True für alle preseed-Nodes
- [test] `tests/core/test_kg.py` — T4–T11 (24 Tests)

### Tests
- T4a-g: kg_add_node — ✅ grün
- T5a-g: kg_add_edge — ✅ grün
- T6: adj O(neighbors) — ✅ grün
- T7a-c: system_energy — ✅ grün
- T8a-b: auto-expand — ✅ grün
- T9: preseed lädt — ✅ grün
- T10a-b: EN-Relations + seed_derived — ✅ grün
- T11: Cross-Language Edges — ✅ grün
- **30/30 gesamt grün (inkl. Phase 0.002)**

### Version
0.003.000-alpha — 4 Commits

### Nächste Session
Phase 0.004 — CfC LNN. Zuerst `archive/legacy-docs/Implementierung.backend.core.lnn.md` anlegen.

---

## terra-002 — Phase 0.002 Backend Skeleton (2026-05-03)

### Ziel dieser Session
FastAPI Skeleton + Config + pytest setup + Health Endpoint.

### Was implementiert wurde
- [feat] `backend/config/settings.py` — Pydantic-Settings, alle CFG-Werte, env-loadable (TERRA_-Prefix)
- [feat] `backend/main.py` — FastAPI app mit lifespan, GET /health, Platzhalter 0.003–0.016
- [feat] `backend/requirements.txt` + `pytest.ini`
- [docs] `.env.example`
- [test] T1–T3 (health + settings)

### Tests
- T1/T2a/T2b: Health endpoint — ✅ grün
- T3a/T3b/T3c: Settings — ✅ grün
- **6/6 grün**

### Version
0.002.000-alpha — 4 Commits

### Nächste Session
Phase 0.003 — KG data structures. Zuerst `archive/legacy-docs/Implementierung.backend.core.kg.md` anlegen.

---

## Template für nächste Session

```markdown
## terra-00N — [Titel] ([Datum])

### Ziel dieser Session
...

### Was implementiert wurde
- [feat] ...
- [fix] ...

### Tests
- T?: ...grün/rot

### Version
0.00X.00Y-label

### Offene Punkte
- ...

### Nächste Session
...
```
