# Implementierungen.Architektur.md — Gesamtstatus
> Lebendiges Dokument. Jede Session updaten.
> Neue Unterpunkte selbstständig anlegen wenn nötig.
> Ist die einzige Datei die den vollständigen Gesamtstatus zeigt.

**Liefer-/Planungsmodus (ab 2026-05-06):** „MVP“ als **Planungs**-Rubrik geschlossen — neue große Stränge (**Replay/Zeitachse**, Persistenz zweigleisig, tiefe Diagnose, Pre‑Boot mit Pre‑Seed‑Katalog) sind **Produktfäden**. DEC + `CLAUDE.md` + `memory/agents/orchestrator.md` + `memory/system/decisions.md`.

---

## Legende
```
[x] Erledigt    [ ] Offen    [~] In Arbeit    [?] Unklar
```

---

## 1. Infrastruktur & Setup

| Komponente | Status | Datei | Notiz |
|------------|--------|-------|-------|
| GitHub Repo | [x] | terra-incognita | privat, main branch |
| Versionierung | [x] | — | 0.001.001-alpha |
| .gitignore | [x] | .gitignore | — |
| .claude/settings.json | [x] | .claude/ | Claude Code config |
| Git Commit-Konvention | [x] | Anweisungen.md | — |
| Cloudflare Tunnel config | [x] | deploy/cloudflared/ | Greenfield **terra-incognita-v2**: Compose-mount Tunnel-Vorlagen (Hub/Vault) · Produktiver Tunnel weiterhin auf Ziel-VM zu verdrahten |
| systemd services | [ ] | systemd/ | Phase 0.023 (Legacy-Monolith) |
| GitHub Actions CI | [x] | .github/workflows/ci.yml | Greenfield **terra-incognita-v2** M0: lint, type-check, tests+coverage, schema-lint, protected-deletions, secrets-layout, pre-commit-ci, compose-smokes · Stubs **`ci-build-images.yml`**, **`cd-release.yml`**, **`nightly-soak.yml`** (noch ohne produktives Deploy) |
| docker-compose (Greenfield) | [x] | deploy/compose/ | **`hub.yml`** / **`vault.yml`** (+ Overrides Quicktunnel/Dev/Observability) · Legacy Root-`docker-compose.yml` (Phase 0.023) entfällt für v2 |

---

## 2. Dokumentation

| Dokument | Status | Notiz |
|----------|--------|-------|
| CLAUDE.md | [~] | Heute überarbeitet — Orchestrator-Fokus |
| Anweisungen.md | [x] | Regelwerk, living |
| catchup.md | [x] | Session-Log, living |
| Implementierungen.Architektur.md | [x] | Diese Datei |
| Implementierung.backend.api.md | [x] | Runtime Contracts dokumentiert (`fix/runtime-contracts`) |
| Phase-/Epik‑Ist (historische Python‑Phasen) | [x] | In dieser Datei + `catchup.md`; neue Arbeit unter `docs/ORCH_IMPLEMENTATION_PLAN.md` — kein eigenständiges Phasen‑Checklist‑Archiv mehr im Repo |
| **Greenfield-Plan** (Thin-Shell MVP, Produktion, Formeln, PDF-Lookup) | [x] | Kanon **`app/docs/greenfield/`** (Changelog `app/docs/greenfield/CHANGELOG.md`); Hinweis-Stub **`docs/greenfield/README.md`** für alte Links |
| ARCHITECTURE.md | [x] | + Python-Klassen + Audit |
| PRESEED_ENRICHMENT_PLAN.md | [x] | Drei-Layer + Wave-Ist |
| PRESEED_FETCH_PIPELINE.md | [x] | Async Fetch Operational |
| OPERATIONS_DIAGNOSTICS_PERSISTENCE.md | [x] | Zwei‑Gleis Persistenz · Diagnose/Export‑Roadmap · Pre‑Boot‑Optionen bei Neustart |
| MULTILINGUAL_AND_SYSTEM_DESIGN.md | [x] | EN-only bis Design-Session; Zielbild „Sprachen durch Verstehen“ (terra-036) |
| DESIGN_SESSION_FULL_SYSTEM_WORKBOOK.md | [~] | §4.8 + §5 + **terra-044** Anbindung `ORCH_IMPLEMENTATION_PLAN`; P0 weiter BL-DSGN-01..06 bis Session; §7 formal erfüllt + Ergänzung interim‑Plan |
| PRODUCT_REPLAY_AND_TIMELINE.md | [~] | Replay v4 **`q`** · **`q_match`** · **`ranking_mode`** · **`ranking_policy`** (Backend terra‑076 hybrid + terra‑079/080 planner‑v4 mit `bm25_only`/`substring_only`/`combined` und Gewichten α/β; UI‑Select **`ranking_mode`** terra‑077, UI **`ranking_policy`** + Gewichte terra‑081 geplant) + FTS append‑Debouncing (**terra‑075**) + diagnostic counters (**terra‑078**, per‑Policy in **terra‑082** geplant); Density / BL‑DSGN‑05 offen |
| ORCH_IMPLEMENTATION_PLAN.md | [x] | Epik A–**H**; **§8**/**§8.6**; §7 Punkt **8** R2-Entwurf; **terra-063** |
| RESEARCH_SYSTEM_SYNTHESIS_TRACE.md | [x] | Mapping PR **#69**; **§7.0** interpretiv + **§7.1** `l4_formulas_v0` / Batch PR **#68** (**terra-063**) |
| **R2 Workshop (Entwurf)** | [x] | `docs/workshops/R2_METHOD_TAG_RUNTIME_MAPPING_DRAFT.md` — Tag↔Runtime (**#71** / **#72**); **terra-063** |
| Implementierung.research.md | [x] | Governance **R1–R5**; R2 verweist Workshop-Entwurf — **terra-063** |
| ENCOUNTER_GHOST_AGENCY_ROUTER_PLAN.md | [x] | Lemma+Diskurs, Dreischicht‑Ghost‑Queues, Wave‑Pause vs. ms‑Spikes, Agency/Observability — Plan terra-043 |
| GHOST_MATERIALIZATION_PLAN.md | [x] | Ghost-Materialisierung / LOD (Planung, terra-031) · §9 Runtime‑Queues |
| CODE_AUDIT.md | [x] | HTML‑Inventur für **`reference/jarvis_v1.02-stable.html`** — Datei 2026‑05 aus Historie wiederhergestellt |
| HTML_UI_AUDIT.md | [x] | UI‑Element‑Inventur (Zeilen‑Mapping) für **`reference/jarvis_v1.02-stable.html`** — 2026‑05 wiederhergestellt |
| FETCHING.md | [x] | Runtime Boot/Fetch — living doc |
| LOGGING.md | [x] | Event-/Logging‑Konventionen |
| UI.md | [ ] | React/R3F — vor Phase 0.017 |
| jarvis_js.md | [x] | Historischer JS-Snapshot (v1.02) — read-only Referenz, kein Update nötig |
| Foundation_Blueprint.md | [x] | Philosophie — **`reference/docs/Jarvis_Foundation_Blueprint.md`** |

---

## 3. Knowledge Base (preseed)

| Komponente | Status | Notiz |
|------------|--------|-------|
| preseed_legacy.json | [x] | Nur Referenz → `reference/knowledge/preseed_legacy.json` |
| preseed_v2.json EN **w00–w12** | [x] | **`build_preseed.py --all`**: **2302** Anchor-Lemmata (cross-wave dedupe; **85** spätere Duplikat-Anchors entfernt — terra-034); Relations ca. **134051** (Builder) |
| Layer 3 ConceptNet (Sidecars) | [ ] | **Frozen** — public API treated **permanent-offline** (**orch DEC 2026-05-08**); tooling probe/skip only; EN **DataMuse + WordNet** are canonical |
| fetch_datamuse.py | [x] | Async Layer 1 — `docs/PRESEED_FETCH_PIPELINE.md` |
| fetch_wordnet.py | [x] | Layer 2 NLTK |
| fetch_conceptnet.py | [x] | Layer 3 mit Health-Probe / Skip |
| build_preseed.py | [x] | Multi-Layer Merge → `preseed_v2.json` |
| verify.py | [x] | Qualitätsprüfer |
| **Ghost-Materialisierung (Runtime)** | [~] | **Router + Pause + API‑Feedback geliefert** (Epik **C–E**, PR **#57–59**): Drei‑Schicht‑Queue RAM, Diagnostic/WS‑Parität; **vollständige** Ghost‑Materialisierung / LOD weiter `GHOST_MATERIALIZATION_PLAN.md` §9 |
| Multilingual (DE/…) | [~] | **EN-only** implementiert bis Design-Session; Vorbereitung: UI-Locale vs. KG-Sprache — `docs/MULTILINGUAL_AND_SYSTEM_DESIGN.md` |

### 3.1 Quality, Retrofit und laufendes Tracking

| Thema | Status | Notiz |
|-------|--------|-------|
| **Builder weak-quality** | [~] | Aktueller Stand: **9** Lemmata mit Warnungen (Details je Session in `catchup.md`, z. B. terra-030); Ziel: iterativ auf **0** oder dokumentierte Ausnahmen |
| **`defined-by` Partial Fix** | [!] | Lücken bei **Core-20 Primordials** + gezielt **w10/w11** Kern-Attraktoren schließen (mind. Quality Rules: jedes `defWord` → `defined-by`) |
| **Quality Retrofit (Bulk)** | [ ] | Frühere Grobschätzung **~6558** fehlende Relations — als **Legacy-Zahl** behandeln; nach Partial Fix mit `knowledge/scripts/verify.py` / Builder-Reports **neu messen** und Zielbandbreite festlegen |
| **Cross-wave Duplikat-Lemmata** | [x] | **`build_preseed.py --all`:** erste Wave (Sortierung `w*.json`) gewinnt; spätere Anchor-Zeilen entfallen — siehe `docs/PRESEED_ENRICHMENT_PLAN.md` Merge Pipeline |
| **ConceptNet Layer 3 Retro** | [ ] | **Zurückgestellt ohne Zeitplan** — keine aktive Prio bis stabiler Endpunkt (terra-033); weiter tracken für später |
| **Ghost-Materialisierung** | [~] | Runtime **Queue + Telemetrie** (Epik **C–E**); Persistenz/Vollständigkeit → **Epik F** · Agency → **Epik G** · `GHOST_MATERIALIZATION_PLAN.md` §9 |
| **Mehrsprachigkeit / zweite Sprache ohne Extraktion** | [~] | Nur **EN** ship bis Sessions-Ende; Trennung UI-Locale vs. KG — `docs/MULTILINGUAL_AND_SYSTEM_DESIGN.md`; **generelle Design-Session geplant** |
| **API Enrichment / fetch_datamuse** | [x] | Layer 1 werkzeugseitig stabil; Feature-Flags siehe `docs/PRESEED_FETCH_PIPELINE.md` |
| **PDF Research L0–L4 (Batch PR #68)** | [~] | Artefakte unter `research/extracted/` + **`_batch_reports/batch_report.json`**; Provenance **`pdf_sha256` / `document_id`**; Roh‑**`l4_formulas_v0`** nicht blind in Runtime. **Produktpfad:** `docs/ORCH_IMPLEMENTATION_PLAN.md` **§8** (**R1–R5**, `l4_formulas_v1`, Maintainer‑Bundle); Abstimmung **Epik H** (Taxonomie) + **Epik G** (Traces/Tags) vor automatischer Wirkung — **`meta` ALLOW**. |

**w10 Kern-Attraktoren (15–20 Begriffe, maximale Relationsdichte):**
`addition, subtraction, multiplication, division, inverse, equal,
greater, less, zero, one, infinity, set, function, relation, proof`
Jeder Begriff: min. 5 Relations inkl. `defined-by`, `opposite`, `implies`.
Ziel: harte EBM-Gravitationszentren die semantische Sprache verankern.

---

## 4. Backend

### 4.1 Infrastruktur

| Komponente | Version | Status | Doc |
|------------|---------|--------|-----|
| FastAPI skeleton | 0.002 | [x] | Implementierung.backend.api.md |
| Config / Settings | 0.002 | [x] | backend/config/settings.py |
| Locale + Pre-Boot Config | 0.005c | [ ] | Implementierung.backend.locale.md |
| multiprocessing setup | 0.006 | [ ] | — |
| DuckDB storage | 0.016 | [ ] | Implementierung.backend.db.md |
| REST endpoints | 0.016 | [x] | Implementierung.backend.api.md |
| WebSocket Hub | 0.008 | [x] | Implementierung.backend.api.md |
| Runtime API Contracts | fix/runtime-contracts | [x] | DTOs für WS/REST Summary, Events, Full-State, Snapshots |
| systemd + Cloudflare | 0.023 | [ ] | — |

### 4.2 Core Engine

| Komponente | Version | Status | HTML-Ref | Doc |
|------------|---------|--------|----------|-----|
| KG data structures | 0.003 | [x] | §5 L1922 | Implementierung.backend.core.kg.md |
| Preseed loader | 0.003 | [x] | — | Implementierung.backend.core.kg.md |
| CfC LNN | 0.004 | [x] | §10 L2968 | Implementierung.backend.core.lnn.md |
| LNN Architektur B=256, hD=iD | 0.005b | [ ] | — | Implementierung.backend.core.lnn.md |
| `lnn_step()` | 0.004 | [x] | L8272 | — |
| `build_lnn_input()` | 0.004 | [x] | L8213 | — |
| `_lnn_focus()` | 0.004 | [x] | L2673 | — |
| `_on_tier_stable()` | 0.004 | [x] | L8285 | — |
| Hopfield EBM | 0.005 | [x] | §24a L6322 | Implementierung.backend.core.ebm.md |
| `ebm_tick()` | 0.005 | [x] | L6420 | — |
| `hopfield_energy()` | 0.005 | [x] | L6399 | — |
| `adapt_ebm_theta()` | 0.005 | [x] | L6383 | — |
| systemTick 8Hz | 0.006 | [ ] | L6703 | — |
| `kg_spontaneous_prop()` | 0.006 | [ ] | L6645 | — |
| `lnn_to_kg_hebbian()` | 0.006 | [ ] | L6612 | — |
| `_apply_tier_weight_cascade()` | 0.006 | [ ] | L8316 | — |
| Boot sequence | 0.007 | [ ] | §24 L5828 | — |
| `_fetch_wave()` | 0.007 | [ ] | L5916 | — |
| `_batch_pause()` · Pause‑Fenster Epik D | 0.007 | [x] | L6013 | `ghost_pause_*` Settings, `TickState.pause_*`, High‑Drain Budget; PR **#58** |
| WS tick stream | 0.008 | [ ] | — | Implementierung.backend.api.md |
| Hebbian dynamics | 0.009 | [ ] | §8 L2653 | — |
| `synaptic_prune()` | 0.009 | [ ] | L2740 (typo) | — |
| Activation spreading | 0.010 | [ ] | §9 L2845 | — |
| Ghost system + Queue + Feedback (Epik **C–E**) | 0.011+ | [x] | §6 L2104 | `GhostQueueRouter`, WS/`summary` **`ghost_queue`**, `/diagnostic` **`ghost_feedback`**; PR **#57–59**; Contracts `runtime_ghost_queue_v0`, `runtime_pause_window_v0`, `runtime_ghost_feedback_v0` |
| `levenshtein()` / typo | 0.011 | [ ] | L9064 | — |
| `process_word()` | 0.012 | [ ] | L2510 | — |
| `fetch_definition()` | 0.012 | [x] | L2178 | — |
| `write_conceptual_priors()` | 0.012 | [ ] | L2402 | — |
| Boot waves (full) | 0.013 | [ ] | — | — |
| Logging System + addEvent() | 0.013b | [x] | LOGGING.md | — |
| DB Migration Infrastructure | 0.013c | [x] | Session-/Repo‑Spuren (`catchup.md`, DuckDB‑Pfad in Code/Docs) | — |
| EBM Wells + Attractors | 0.014 | [x] | L6327 | Implementierung.backend.core.wells.md |
| Shadow-System (generalisiert) | 0.014 | [ ] | L9126 | Implementierung.backend.core.wells.md |
| `find_energy_wells()` | 0.014 | [ ] | L6793 | — |
| `makeDormant()` | 0.014 | [ ] | L6346 | — |
| `detectTierN(N)` | 0.014 | [ ] | L8464 | — |
| Attractor Shadow System | 0.014 | [ ] | L9126 | — |
| TIER_CONFIG + TIER_NAMES | 0.014 | [ ] | L8068 | — |
| PCD | 0.015 | [x] | L7629 | — |
| Inference Engine R1–R4 | 0.015 | [ ] | L8737 | — |
| Dreaming | später | [ ] | §24b L9721 | — |
| Babble | später | [ ] | L9930 | — |

**ConceptNet-Blocker vor Produktiveinsatz:** Neue Relationstypen aus Layer 3
(`used-for`, `capable-of`, `has-a`, `at-location`, `causes`, `motivated-by`)
müssen in `backend/core/lnn.py` (`_REL_ATTENTION`) und
`backend/core/spreading.py` (`_REL_SPREAD`) registriert werden.

### 4.3 Storage (DuckDB)

| Komponente | Version | Status | Notiz |
|------------|---------|--------|-------|
| Schema Init | 0.016 | [ ] | 7 Tabellen |
| `append_event()` | 0.016 | [ ] | per addEvent()-Call |
| `save_snapshot()` | 0.016 | [ ] | vollständig |
| `restore_snapshot()` | 0.016 | [ ] | Time-Travel |
| `list_snapshots()` | 0.016 | [ ] | — |

---

## 5. Frontend

| Komponente | Version | Status | Notiz |
|------------|---------|--------|-------|
| React + Vite scaffold | 0.017 | [ ] | — |
| Zustand Store + WS Consumer | 0.017 | [ ] | — |
| Three.js / R3F 3D KG | 0.018 | [ ] | — |
| LNN Background Canvas2D | 0.019 | [ ] | — |
| Chat Panel | 0.020 | [ ] | — |
| Tier Panels (Wells, Concepts) | 0.020 | [ ] | — |
| Filter Bar | 0.021 | [ ] | — |
| Camera / Orbit Controls | 0.021 | [ ] | — |
| Pre-Boot Config Panel | 0.027 | [~] | Barebones UI — `Implementierung.frontend.preboot.md`; `/boot/start` → 0.028 |
| Header (T0:N T1:N T2:N T3:N ◌N) | 0.021 | [ ] | — |
| Dreaming / Babble Panel | 0.022 | [ ] | optional |

---

## 6. Deployment

| Komponente | Version | Status | Notiz |
|------------|---------|--------|-------|
| terra.service (systemd) | 0.023 | [ ] | Backend |
| terra-tunnel.service | 0.023 | [ ] | Cloudflare Tunnel |
| cloudflare/tunnel.yml | 0.023 | [ ] | — |
| wrangler.toml (Pages) | 0.023 | [ ] | Frontend CDN |
| .github/workflows/deploy-backend.yml | 0.024 | [ ] | SSH + reload |
| .github/workflows/deploy-frontend.yml | 0.024 | [ ] | Wrangler Pages |
| docker-compose.yml | 0.023 | [ ] | lokale Dev |

---

## 7. Selbstständig anzulegende Docs (wenn Phase erreicht)

Vor jeder Phase anlegen:
```
Implementierung.backend.core.wells.md  ← vor 0.005 (ERSTELLT 2026-05-04)
Implementierung.backend.core.lnn.md    ← vor 0.004
Implementierung.backend.core.ebm.md    ← vor 0.005
Implementierung.backend.core.kg.md     ← vor 0.003
Implementierung.backend.db.md          ← vor 0.016
Implementierung.frontend.md            ← vor 0.017
Implementierung.deployment.md          ← vor 0.023
```
