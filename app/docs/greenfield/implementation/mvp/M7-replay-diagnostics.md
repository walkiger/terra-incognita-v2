# `M7-replay-diagnostics.md` — Phase M7: Replay & Diagnostik

> **Lebendiges Dokument.** Ergebnis: Vollständige Replay-Page mit
> Hybrid-Planner-UI, Pause/Step-Steuerung, Density-Stub, Snapshot-
> Lade-Pfad. Diagnostic-Page mit FTS-Counter-Anzeige. Replay-Latenz-
> Gate aktiv.
>
> **Phase-Tag bei Abschluss:** `v0.8.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Schritte M7.1 – M7.8](#4-schritte-m71--m78)
5. [Phasen-Gate](#5-phasen-gate)
6. [Erledigte Änderungen](#6-erledigte-änderungen)

---

## 1. Phasen-Ziel

* Replay-Page führt das vollständige `replay_timeline_window_v4`-
  Verhalten in das Frontend ein — inklusive `q`, `q_match`,
  `ranking_mode`, `ranking_policy`, α/β-Gewichten.
* Pause / Step / Speed-Steuerung kommunizieren mit der Engine via
  `replay/control`.
* Density-Stub zeigt Aggregate-Histogramm (Stub-Daten in MVP, finalisiert
  in v1.x).
* Diagnostic-Page zeigt System-Status, Replay-FTS-Ops-Counter
  (terra-078 / 082), Engine-Status, NATS-Lag.
* Snapshot-Load: User kann eine eigene Snapshot-Bundle-Datei laden und
  abspielen.
* CI-Gate stellt sicher, dass Replay-Hybrid-Query p95 < 800 ms bleibt.

**Was M7 NICHT tut:**

* Keine vollständige Density-Pipeline — nur Stub.
* Keine Erweiterung des Backends (Backend-Pfade aus M5.8/M5.9
  ausreichend).
* Keine Multi-User-Replay-Sicht (jeder sieht eigene Daten).

---

## 2. Vorbedingungen

* M5 abgeschlossen (Replay-API + Diagnostic-API).
* M6 abgeschlossen (Frontend-Skelett, WS-Stream, Tier-Panels).

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §7 — `/v1/replay/*`, `/v1/diagnostic`
* Bestehender Vertrag `replay_timeline_window_v4`
* `Anweisungen.md` §2

---

## 4. Schritte M7.1 – M7.8

---

### M7.1 — replay-page-baseline

**Branch:** `feature/replay-page-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M6 grün
**Berührte Pfade:**
```
frontend/src/replay/
├── ReplayPage.tsx
├── EventList.tsx
├── EventRow.tsx
├── filters/
│   ├── TimeRangeFilter.tsx
│   ├── KindFilter.tsx
│   └── QueryInput.tsx
└── styles.module.css
tests/replay/replay_page.test.tsx
```

**Akzeptanzkriterien:**
1. Route `/app/replay` zeigt eine Tabellen-Ansicht der Replay-Events
   des eingeloggten Users.
2. Filter (oben):
   * Zeitraum (`since` / `until`).
   * Kind (Multi-Select aus dem `replay_event.kind`-Whitelist).
   * Query `q` mit Match-Mode (`fts`/`substring`).
3. Pagination per Cursor (`next_after_id`).
4. Echo-Anzeige: Server-Filter wird unterhalb der Filterleiste
   widergespiegelt — sehr nützlich für Debug.
5. Bei Engine-Online: Live-Updates streamen oben rein, sofern Filter
   passt.

**Tests:**
* `tests/replay/replay_page.test.tsx::renders_event_list`
* `tests/replay/replay_page.test.tsx::filter_by_time_range`
* `tests/replay/replay_page.test.tsx::pagination_works`

**Ressourcen-Budget:** Replay-Page lazy gesplittet (~200 kB gz, M6.13).
**Geschätzte PR-Größe:** ~700 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.2 — replay-page-hybrid-planner-ui

**Branch:** `feature/replay-page-hybrid-planner-ui`
**Issue:** `#NNN`
**Vorbedingungen:** M7.1 gemerged
**Berührte Pfade:**
```
frontend/src/replay/filters/
├── RankingModeFilter.tsx
├── RankingPolicyFilter.tsx
└── ScoreWeightsFilter.tsx
tests/replay/hybrid_filters.test.tsx
```

**Akzeptanzkriterien:**
1. **Ranking Mode Select** (`chronological` | `hybrid`) — sichtbar wenn
   `q` gesetzt.
2. Wenn `hybrid` aktiv:
   * **Ranking Policy Select** (`auto` | `bm25_only` | `substring_only` | `combined`).
   * Bei `combined`: zwei `Number`-Inputs für α (`bm25_weight`) und β
     (`substring_weight`), Default `0.5/0.5`, Step `0.05`.
3. `auto` schickt **kein** `ranking_policy` — Server-Defaults greifen
   (terra-079/080).
4. Filter-Echo zeigt aufgelöste `effective_policy` und
   `score_weights` (nicht nur die clientseitig gewählten).
5. **Bestand**: terra-081-Verhalten wird 1:1 auf die neue Page
   abgebildet.

**Tests:**
* `tests/replay/hybrid_filters.test.tsx::policy_select_visible_in_hybrid`
* `tests/replay/hybrid_filters.test.tsx::weights_visible_only_in_combined`
* `tests/replay/hybrid_filters.test.tsx::auto_policy_omits_param`
* `tests/replay/hybrid_filters.test.tsx::echo_displays_effective_policy`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.3 — replay-page-pause-step-controls

**Branch:** `feature/replay-page-pause-step-controls`
**Issue:** `#NNN`
**Vorbedingungen:** M7.1 gemerged
**Berührte Pfade:**
```
frontend/src/replay/controls/
├── PauseStepBar.tsx
├── SeekToTs.tsx
├── SpeedControl.tsx
└── useReplayControl.ts
tests/replay/controls.test.tsx
```

**Akzeptanzkriterien:**
1. Buttons: Play/Pause, Step-Forward, Step-Back (im MVP ggf. nur Stub —
   Step-Back ist semantisch unklar ohne Snapshot-Diff).
2. Speed-Slider (0.25× / 0.5× / 1× / 2× / 4× / 8×).
3. Seek-Eingabe (Datum + Uhrzeit oder relative `5min before now`).
4. **Sendepfad**: alle Aktionen → `replay/control`-Frame über WS →
   Hub forwardet an Engine. Engine respektiert (M3.5).
5. Anzeige des aktuellen Engine-Status (paused/playing/speed-Mult).

**Tests:**
* `tests/replay/controls.test.tsx::pause_emits_replay_control`
* `tests/replay/controls.test.tsx::seek_emits_with_ts`
* `tests/replay/controls.test.tsx::speed_emits_with_multiplier`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.4 — replay-page-density-stub

**Branch:** `feature/replay-page-density-stub`
**Issue:** `#NNN`
**Vorbedingungen:** M7.1 gemerged
**Berührte Pfade:**
```
frontend/src/replay/density/
├── DensityChart.tsx                          ← Stub mit Mock-Daten
└── README.md
backend/api/routers/replay.py                 ← optional `/v1/replay/density` (Stub)
tests/replay/density.test.tsx
```

**Akzeptanzkriterien:**
1. Chart-Komponente zeigt Histogramm „Events pro Minute" über das
   aktuelle Filter-Fenster.
2. Im MVP: client-seitig aggregieren (vom Replay-Result).
3. Server-seitige Aggregat-API (`/v1/replay/density`) ist als **Stub**
   reserviert — gibt entsprechend gruppierte Werte zurück, aber Caching/
   Materialized-View kommt erst in v1.x.
4. Keine Performance-Regression für Replay-Page.

**Tests:**
* `tests/replay/density.test.tsx::renders_with_mock_data`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~400 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.5 — diagnostic-page-baseline

**Branch:** `feature/diagnostic-page-baseline`
**Issue:** `#NNN`
**Vorbedingungen:** M5.9 gemerged, M6 grün
**Berührte Pfade:**
```
frontend/src/diagnostic/
├── DiagnosticPage.tsx
├── sections/
│   ├── SystemSection.tsx
│   ├── EngineSection.tsx
│   ├── PersistenceSection.tsx
│   └── NatsSection.tsx
tests/diagnostic/diagnostic_page.test.tsx
```

**Akzeptanzkriterien:**
1. Route `/app/diagnostic` ruft `/v1/diagnostic` und rendert die
   Sektionen aus M5.9.
2. **Auto-Refresh** alle 10 s (TanStack Query mit `refetchInterval`).
3. Engine-Sektion zeigt Live-LNN-Werte (verlinkt auf `engineStore` für
   Echtzeit, `/v1/diagnostic` als Fallback).
4. **Admin-Sektion** wird nur sichtbar, wenn JWT-Scope `admin`
   enthält.

**Tests:**
* `tests/diagnostic/diagnostic_page.test.tsx::renders_sections`
* `tests/diagnostic/diagnostic_page.test.tsx::admin_section_hidden_for_viewer`
* `tests/diagnostic/diagnostic_page.test.tsx::auto_refresh`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.6 — diagnostic-page-fts-ops-counters

**Branch:** `feature/diagnostic-page-fts-ops-counters`
**Issue:** `—`
**Vorbedingungen:** M7.5 gemerged
**Berührte Pfade:**
```
frontend/src/diagnostic/sections/ReplayFtsOpsSection.tsx
tests/diagnostic/replay_fts_ops.test.tsx
```

**Akzeptanzkriterien:**
1. Sektion zeigt:
   * `rebuild_success_total`, `rebuild_failure_total`,
     `append_rebuild_skipped_debounce_total` (terra-078).
   * `hybrid_bm25_only_total`, `hybrid_substring_only_total`,
     `hybrid_combined_total` (terra-082).
   * `last_rebuild_ok_unix` als Datums-Format.
2. **Trends**: Mini-Sparkline pro Counter über Zeit (Client-Seite hält
   die letzten 30 Werte zurück).
3. **Echo**: `replay_fts_rebuild_debounce_s` und
   `fts_index_schema_present` werden als Status-Pillen angezeigt.

**Tests:**
* `tests/diagnostic/replay_fts_ops.test.tsx::counters_render`
* `tests/diagnostic/replay_fts_ops.test.tsx::sparkline_updates`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.7 — replay-snapshot-load-and-play

**Branch:** `feature/replay-snapshot-load-and-play`
**Issue:** `#NNN`
**Vorbedingungen:** M7.3 gemerged, M5.7 gemerged
**Berührte Pfade:**
```
frontend/src/replay/snapshot/
├── SnapshotLoader.tsx
├── SnapshotList.tsx
└── snapshotPlayer.ts
backend/api/routers/replay.py                 ← `/v1/replay/load_snapshot/{id}`
tests/replay/snapshot_load.test.tsx
```

**Akzeptanzkriterien:**
1. UI:
   * Liste der eigenen Snapshots (`/v1/snapshots`).
   * Klick → „in Replay laden" — sendet `replay/control{action: 'load_snapshot', args: {id}}` an die Engine.
2. Backend:
   * `/v1/replay/load_snapshot/{id}` validiert Eigentum.
   * Generiert signed R2-URL (Lebensdauer 5 min) und schickt sie an
     die Engine via `server/replay_command{action: 'load_snapshot_signed_url'}`.
3. Engine:
   * Lädt Bundle, ersetzt aktuellen State (oder branchet — die
     genaue Semantik wird in der Engine-Doku M3 nachgezogen, im MVP
     ersetzt).

**Tests:**
* `tests/replay/snapshot_load.test.tsx::list_renders`
* `tests/replay/snapshot_load.test.tsx::load_emits_command`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~500 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M7.8 — replay-latency-gate

**Branch:** `chore/replay-latency-gate`
**Issue:** `—`
**Vorbedingungen:** M7.2 gemerged
**Berührte Pfade:**
```
.github/workflows/ci.yml                    ← Job `replay-latency-bench`
backend/scripts/bench_replay.py              ← Mikro-Benchmark
docs/operations/replay-bench.md
```

**Akzeptanzkriterien:**
1. Bench-Skript:
   * Generiert ~50 k Replay-Events in der Test-DB.
   * Führt 100 Hybrid-Queries aus, misst p95.
   * Schreibt JSON-Report.
2. CI-Gate:
   * Bench läuft nightly.
   * p95 > 800 ms → CI-Fail mit Bench-Report im Artifact.
3. **Skalier-Hinweis**: bei drohendem Fail wird der Hybrid-Planner
   evaluiert (Index-Strategie, Statement-Reuse), nicht der Test
   gelockert.

**Tests:** der Bench-Job ist selbst „der Test".

**Ressourcen-Budget:** Bench-Job auf GitHub-Hosted-Runner (~7 GB RAM)
locker machbar; lokal in < 60 s.
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün; Bench-Report als Artifact verfügbar.

---

## 5. Phasen-Gate

M7 gilt als grün, wenn:

1. M7.1 – M7.8 in `00-index.md` auf `[x]`.
2. Manueller Smoke: User mit Encounter-Stream sieht Replay-Filter
   funktionieren, Hybrid-Planner-UI ist sichtbar, Filter-Echo zeigt
   `effective_policy`.
3. Diagnostic-Page zeigt FTS-Counter, Engine-State.
4. Replay-Latenz-Gate ist Pflicht-Check.
5. Tag `v0.8.0` gepusht.

---

## 6. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M7 noch nicht eröffnet*
