# `M4-first-formula-lnn-state.md` — Phase M4: Erste echte Formel — LNN State

> **Lebendiges Dokument.** Ergebnis: Die erste echte Formel-Implementierung
> der Engine. `lnn_step()` ist nicht mehr Stub, sondern realisiert das
> Closed-Form-Continuous-Time (CfC) Hidden-State-Update mit numerisch
> verifizierbarer Korrektheit und stabilem Tier-Wachstum (`F.LNN.GROW.*`).
>
> Diese Phase ist der **erste** echte Konsument der **Formula Registry**
> (`app/docs/greenfield/formulas/registry.md`).
>
> **Phase-Tag bei Abschluss:** `v0.5.0`

---

## Inhalt

1. [Phasen-Ziel](#1-phasen-ziel)
2. [Vorbedingungen](#2-vorbedingungen)
3. [Architektur-Bezug](#3-architektur-bezug)
4. [Formel-Bezug (Registry-IDs für diese Phase)](#4-formel-bezug-registry-ids-für-diese-phase)
5. [Schritte M4.1 – M4.9](#5-schritte-m41--m49)
6. [Phasen-Gate](#6-phasen-gate)
7. [Erledigte Änderungen](#7-erledigte-änderungen)

---

## 1. Phasen-Ziel

* **`F.LNN.STATE.001`** ist implementiert: das CfC Hidden-State-Update
  mit Liquid-Time-Constant.
* **`F.LNN.STATE.002`** ist implementiert: die τ-Modulationsfunktion.
* **`F.LNN.GROW.003`** ist implementiert: deterministische Bedingungen
  für Tier-Emergenz und damit `lnn.grow()`.
* `lnn_step(word, scale, state)` ist der **einzige** Eintrittspunkt für
  LNN-Stimulation (`Anweisungen.md` §7).
* `build_lnn_input()` baut den **Multi-Tier-Vektor** (`F.LNN.INPUT.*`).
* `_on_tier_stable()` ist der **einzige** Ort, an dem `lnn.grow()`
  ausgeführt wird.
* Numerische Konformitäts-Suite vergleicht Engine-Output gegen
  vorberechnete Referenz-Werte aus einer reinen NumPy-Referenz-Impl.
* Engine sendet ab dieser Phase **echte** `tier_counts`, `lnn.iD`,
  `lnn.norm`, `lnn.delta` an den Hub. Frontend zeigt sie noch nicht
  (M6) — aber im `/v1/diagnostic` (M5.9) sind sie sichtbar.

**Was M4 NICHT tut:**

* Kein vollständiges EBM-Wells-System — das kommt in einer Folgephase
  (`F.EBM.*`-IDs sind reserviert, aber nicht implementiert).
* Keine vollständige KG-Aktivität — KG bleibt vorerst ein Stub mit den
  notwendigen Hooks für `lnn_to_kg_hebbian()` (Folgephase).
* **Kein Server-seitiger Tick** — die Engine läuft weiter lokal.

---

## 2. Vorbedingungen

* M3 abgeschlossen (`v0.4.0`).
* Engine-Stub-Tick-Loop läuft 8 Hz fehlerfrei.
* Snapshot-Roundtrip funktioniert.
* Lookup-Protokoll (`app/docs/greenfield/protocols/pdf-lookup.md`) ist
  bekannt und einsatzbereit, weil M4 Formeln aus Forschungs-PDFs
  zieht.

---

## 3. Architektur-Bezug

* `architecture/mvp.md` §6 — Datenmodell (LNN-State auf Engine-Seite,
  Server kennt nur Snapshot-Manifest)
* `architecture/mvp.md` §13 — Speicher-Budget (PyTorch ist auf der
  Workstation kein Problem; auf dem Hub existiert es nicht)
* `Anweisungen.md` §2 — Coding-Standards
* `Anweisungen.md` §4 — Test-Regeln
* `Anweisungen.md` §7 — Non-Negotiables LNN
* `docs/ARCHITECTURE.md` §1–§3 — vorhandene LNN-Mathematik aus dem
  bestehenden System; Quelle der Schreibweise und Variablennamen

---

## 4. Formel-Bezug (Registry-IDs für diese Phase)

Die folgenden `F.*`-IDs werden in M4 angelegt **und** befüllt. Alle
weiteren Details (LaTeX, Quelle, Verbatim-Snippet, Konsumenten) werden in
**M4.1** (`app/docs/greenfield/formulas/registry.md`) ausführlich verschriftet.

| ID                  | Kurzbeschreibung                                            | Status nach M4 |
|---------------------|-------------------------------------------------------------|----------------|
| `F.LNN.STATE.001`   | CfC Hidden-State-Update mit Liquid Time-Constant            | implementiert  |
| `F.LNN.STATE.002`   | τ-Modulator (Time-Constant in Abhängigkeit von Input/State) | implementiert  |
| `F.LNN.STATE.003`   | Self-Signal NCP-Wiring `s = tanh(W_sh · h + b_s)`           | implementiert  |
| `F.LNN.INPUT.001`   | Multi-Tier-Input-Vektor-Aufbau                              | implementiert  |
| `F.LNN.INPUT.002`   | Tier-Weight-Bonus auf Input                                 | implementiert  |
| `F.LNN.GROW.001`    | Wachstumsformel `dim(N) = B × (1 + N×(N+1)/2)`              | implementiert  |
| `F.LNN.GROW.002`    | Tier-Min-Members-Schwelle pro Tier                          | implementiert  |
| `F.LNN.GROW.003`    | Tier-Stable-Bedingung: deterministischer Auslöser           | implementiert  |
| `F.LNN.GROW.004`    | Skala für initial-Gewichte neuer Channels                   | implementiert  |

**Quellen-Strategie:**

* Die existierende Mathematik in `docs/ARCHITECTURE.md` ist die Brücke
  zur bisherigen Implementierung (`backend/core/lnn.py`-Verhalten,
  `lnn_step`-Conventions). Sie bleibt **kanonisch**, weil sie die
  Invarianten aus `Anweisungen.md` §7 widerspiegelt.
* PDFs aus `research/extracted/` werden **zusätzlich** als Begründungen
  herangezogen — wo CfC genau herkommt, was die Liquid-Time-Constant
  in der Originalliteratur tut, welche numerischen Eigenschaften
  beweisbar sind.
* **Lookup-Pfad** (siehe `app/docs/greenfield/protocols/pdf-lookup.md`):
  Die Hauptquelle für CfC ist Hasani et al. „Closed-Form Continuous-
  Time Neural Networks" (Nature MI 2022). **Diese ist im Korpus
  derzeit NICHT extrahiert** — `M4.1` initiiert via Lookup-Pfad 3
  (Re-Extraktion über `research-agent`) eine gezielte L0–L4-Extraktion
  dieses einen Papers, bevor die Registry-Einträge final werden.

---

## 5. Schritte M4.1 – M4.9

---

### M4.1 — formula-registry-bootstrap

**Branch:** `docs/formula-registry-bootstrap`
**Issue:** `#NNN`
**Vorbedingungen:** M3 grün; `formulas/README.md` und `formulas/registry.md` existieren als Skelette.
**Berührte Pfade:**
```
app/docs/greenfield/formulas/registry.md       ← Erstbefüllung mit allen F.LNN.*-IDs aus M4
app/docs/greenfield/formulas/README.md         ← finale Konvention
docs/contracts/formulas.schema.json        ← optional, JSON-Schema für künftige automatische Validierung
research/extracted/<closed-form-cfc-paper>/* ← falls re-extrahiert
```

**Formel-Refs:** alle aus Sektion 4.

**Akzeptanzkriterien:**
1. Lookup-Pfad 3 wurde tatsächlich ausgeführt: das CfC-Paper liegt
   extrahiert vor (manifest, l1, l2, l3, l4, l4_formulas) — falls
   nicht öffentlich verfügbar, wird die Quelle abweichend dokumentiert
   (Buchkapitel / Tutorial-Paper / Reproduktion).
2. Jeder F-ID-Eintrag in `registry.md` enthält:
   * **LaTeX**-Bestform.
   * **Source**: `document_id` aus `research/extracted/`, Seite,
     `equation_label` (sofern vorhanden), `verbatim_snippet`.
   * **Consumed by**: erwartete Code-Pfade, z. B.
     `engine/src/terra_engine/core/lnn.py::CfCCell.step` — auch wenn
     die Datei in M4.2 erst beschrieben wird, ist der Pfad fest.
   * **Tests**: erwartete Test-IDs, z. B. `tests/core/test_lnn_state.py::test_F_LNN_STATE_001_*`.
   * **Status**: in M4.1 noch `spec-ready`; wird in M4.2-M4.4 zu
     `implemented`, in M4.8 zu `verified`.
3. README erklärt das ID-Schema (`F.{POL}.{TOPIC}.{NNN}`),
   Status-Trichter, Update-Workflow.
4. CI-Job `formulas-lint`:
   * Prüft, dass jede Registry-ID syntaktisch dem Schema folgt.
   * Prüft, dass jeder im Code referenzierte `# F.LNN.STATE.001`-Marker
     eine Registry-ID trifft.

**Tests:**
* `tests/test_formulas_registry.py::test_id_format`
* `tests/test_formulas_registry.py::test_consumed_by_paths_are_valid`
* `tests/test_formulas_registry.py::test_status_in_allowed_set`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff (Registry kann groß werden)
**Fertig wenn:** AC + CI grün; alle F.LNN.*-Einträge auf `spec-ready`.

---

### M4.2 — f-lnn-state-001-cfc-update

**Branch:** `feature/f-lnn-state-001-cfc-update`
**Issue:** `#NNN`
**Vorbedingungen:** M4.1 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/lnn.py
engine/src/terra_engine/core/lnn_kernels.py    ← reine NumPy-Implementierung (Referenz)
engine/src/terra_engine/core/lnn_kernels_torch.py ← optionale PyTorch-Implementierung
engine/tests/core/test_lnn_state_001.py
```

**Formel-Refs:** `F.LNN.STATE.001`, `F.LNN.STATE.002`, `F.LNN.STATE.003`

**Akzeptanzkriterien:**
1. Klasse `CfCCell`:
   * `__init__(input_dim, hidden_dim, dt=0.125, ...)` — `dt = 1 / tick_hz`.
   * `step(h, u) -> h_new` implementiert F.LNN.STATE.001 unter Verwendung
     von F.LNN.STATE.002 (τ) und F.LNN.STATE.003 (Self-Signal).
   * **Code-Marker**: in der Methode steht ein Kommentar
     `# F.LNN.STATE.001` direkt über der zentralen Update-Zeile.
2. Numerische Implementierung:
   * Default ist die NumPy-Variante (`lnn_kernels.py`). PyTorch-Variante
     ist optional und wird über Config-Flag aktiviert.
   * Keine `torch.compile`/`torch.jit` in M4 — Komplexitätsmanagement.
3. **Konformitäts-Test**: gegen pre-computed Referenz-Werte
   (`tests/core/data/lnn_reference.npz`). Die Referenz-Werte wurden
   extern oder in einem reproduzierbaren Notebook erzeugt — Notebook-
   Code liegt unter `tools/reference/lnn_state_001_reference.ipynb`.
4. Edge-Cases getestet:
   * `iD = B` (frische LNN, kein Tier-Wachstum).
   * `iD > B` (nach Tier-Wachstum).
   * Null-Input-Vektor.
   * `tau_min` / `tau_max` Sättigung.
5. Performance: 1000 Steps mit `iD=B=256`, `hD=256` in < 250 ms auf
   Referenz-Workstation (Notebook misst).

**Tests:**
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_matches_reference`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_zero_input`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_post_grow_dim`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_tau_saturation`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_perf_1000_steps`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~700 Lines diff (Code + Referenz-Daten + Tests)
**Fertig wenn:** AC + CI grün; Registry-Status auf `implemented`.

---

### M4.3 — f-lnn-state-002-tau-modulator

**Branch:** `feature/f-lnn-state-002-tau-modulator`
**Issue:** `#NNN`
**Vorbedingungen:** M4.2 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/lnn.py            ← `tau_modulator(h, u)`
engine/tests/core/test_lnn_state_002.py
```

**Formel-Refs:** `F.LNN.STATE.002`

**Akzeptanzkriterien:**
1. `tau_modulator(h, u, tau_0, W_th, W_ti, b_t)` berechnet τ als
   `τ_0 / (1 + τ_0 · σ(W_th · h + W_ti · u + b_t))` (oder die exakte Form,
   die im Registry-Eintrag F.LNN.STATE.002 fixiert wurde).
2. Werte sind im Intervall `[tau_min, tau_max]` geklemmt; ohne Klammer
   ist die Funktion stetig.
3. Wechselwirkung mit F.LNN.STATE.001 ist deterministisch — bei
   konstantem `(h, u)` ist `τ` konstant.
4. Tests prüfen **Monotonie** an gewählten Stützpunkten.

**Tests:**
* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_clamping`
* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_monotonicity_in_input`
* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_continuity`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M4.4 — f-lnn-grow-003-tier-emergence

**Branch:** `feature/f-lnn-grow-003-tier-emergence`
**Issue:** `#NNN`
**Vorbedingungen:** M4.2 gemerged, M4.3 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/lnn.py            ← `LNN.grow()` mit Wachstumsformel
engine/src/terra_engine/core/tier.py           ← `_on_tier_stable()`, `tier_min_members()`
engine/tests/core/test_lnn_grow.py
engine/tests/core/test_tier_callback.py
```

**Formel-Refs:** `F.LNN.GROW.001`, `F.LNN.GROW.002`, `F.LNN.GROW.003`, `F.LNN.GROW.004`

**Akzeptanzkriterien:**
1. **`F.LNN.GROW.001` Wachstumsformel:** `dim(N) = B × (1 + N×(N+1)/2)`.
   * Implementiert als `target_dim_for_tier(n: int, B: int) -> int`.
   * Tabelle:

     | N | dim(N) bei B=256 |
     |---|------------------|
     | 0 | 256              |
     | 1 | 512              |
     | 2 | 1024             |
     | 3 | 1792             |
     | 4 | 2816             |

   * Tests gegen die Tabelle.

2. **`F.LNN.GROW.002`** `tier_min_members(n)`-Funktion liefert die
   Mindest-Member-Anzahl pro Tier für die Stable-Detection. Default-
   Werte aus `Anweisungen.md` §7 + `docs/ARCHITECTURE.md`.

3. **`F.LNN.GROW.003` Tier-Stable-Bedingung:**
   * In `build_lnn_input()` (M4.6): wenn `len(active_for_tier(n)) >= tier_min_members(n)`
     und `n not in _tier_growth_done`,
   * dann `_on_tier_stable(n)` einmalig.
   * `_on_tier_stable(n)`:
     * `if n == 0: return` (T0 wächst LNN nie)
     * `_tier_growth_done.add(n)`
     * `lnn.grow(extra_channels=B, scale=initial_scale_for_tier(n))`
     * `state.tier_registry.mark_stable(n)`
     * Event `lnn_grew` und `tier_stable` an `event_log` (NATS).

4. **`F.LNN.GROW.004`** initial-Scale: empirische Formel aus
   `docs/ARCHITECTURE.md`: `max(0.08, 0.25 - n × 0.05)`.

5. **Invariante T0 Geburt nicht Wachstum:** `lnn` startet bei `iD = B`
   ausschließlich beim ersten Attraktor-Encounter; das ist nicht
   `lnn.grow()`, sondern `lnn.bootstrap_t0()`.

**Tests:**
* `tests/core/test_lnn_grow.py::test_F_LNN_GROW_001_target_dim_table`
* `tests/core/test_lnn_grow.py::test_F_LNN_GROW_004_initial_scale_curve`
* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_fires_once`
* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_t0_does_not_grow`
* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_idempotent_when_called_twice`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M4.5 — lnn-step-singleton-entrypoint

**Branch:** `feature/lnn-step-singleton-entrypoint`
**Issue:** `#NNN`
**Vorbedingungen:** M4.2 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/lnn.py            ← `lnn_step()` (modul-level)
engine/tests/core/test_lnn_step.py
```

**Formel-Refs:** `F.LNN.STATE.001`, `F.LNN.INPUT.001` (Aufruf), `F.LNN.GROW.003` (indirekt)

**Akzeptanzkriterien:**
1. **Pflicht-Signatur** (aus `Anweisungen.md` §2):
   ```python
   def lnn_step(word: str | None, scale: float, state: SystemState) -> None:
   ```
2. Body:
   * Wenn `word` ein bekanntes KG-Lemma ist: `state.lnn.step(build_lnn_input(word, scale, state))`.
   * Sonst (None oder unbekannt): Rausch-Schritt mit korrekter `iD`-Dimension.
3. **Linter-Regel** in CI: gemustert per `ruff` AST-Plugin oder einem
   eigenen kleinen Check, dass `engine/` keine direkte `LNN.step()`-
   oder `state.lnn.step()`-Aufrufe enthält außer in genau einem
   File (`lnn.py` selbst).
4. Tests:
   * Roundtrip: `lnn_step('water', 2.0, state)` modifiziert `state.lnn.h`.
   * `lnn_step(None, 0.003, state)` läuft mit korrekter Dimension nach
     Tier-Wachstum.
   * `lnn_step('unknown_word', 1.0, state)` fällt zurück auf Rausch-Schritt.

**Tests:**
* `tests/core/test_lnn_step.py::test_lnn_step_known_word`
* `tests/core/test_lnn_step.py::test_lnn_step_noise`
* `tests/core/test_lnn_step.py::test_lnn_step_unknown_word`
* `tests/core/test_lnn_step.py::test_lnn_step_post_grow_dim_correct`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M4.6 — build-lnn-input-multi-tier

**Branch:** `feature/build-lnn-input-multi-tier`
**Issue:** `#NNN`
**Vorbedingungen:** M4.5 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/lnn_input.py
engine/src/terra_engine/core/word_vec.py        ← `wv()` Hash-basiert
engine/src/terra_engine/core/tier.py            ← `vwTier()`-Helfer
engine/tests/core/test_build_lnn_input.py
```

**Formel-Refs:** `F.LNN.INPUT.001`, `F.LNN.INPUT.002`, `F.LNN.GROW.003`

**Akzeptanzkriterien:**
1. **Layout des Multi-Tier-Vektors** (siehe `docs/ARCHITECTURE.md` §3):
   ```
   |  T0-Channel (B)  |  T1-Channel (B)  |  T2-Channel (B)  |  ...  |
   ```
2. T0-Channel: `wv(word, B)` (Hash-basiert).
3. Höhere Tiers: für jeden Tier n>0:
   * Suche aktiver Eintrag des Wortes (Member=2, Adjacent=1, sonst 0).
   * Best-Treffer × `scale × tier_weight(n, seen)`.
   * Wenn keine Treffer: Float-Array(0).
4. Trigger F.LNN.GROW.003 ist hier verdrahtet — das ist der **einzige**
   Ort, an dem `_on_tier_stable()` indirekt aufgerufen wird.
5. Output-Dimension == `state.lnn.iD` zur Laufzeit (Invariante; Test
   prüft).
6. Keine direkten `wv(word, 32)`-Aufrufe außerhalb von `lnn_input.py`.

**Tests:**
* `tests/core/test_build_lnn_input.py::test_layout_t0_only`
* `tests/core/test_build_lnn_input.py::test_layout_with_t1`
* `tests/core/test_build_lnn_input.py::test_growth_trigger_fires`
* `tests/core/test_build_lnn_input.py::test_no_growth_when_under_threshold`
* `tests/core/test_build_lnn_input.py::test_dim_matches_lnn_iD`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~550 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M4.7 — tier-stable-callback-policy

**Branch:** `feature/tier-stable-callback-policy`
**Issue:** `#NNN`
**Vorbedingungen:** M4.4 gemerged, M4.6 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/core/tier.py
engine/src/terra_engine/runtime/event_emitter.py
engine/tests/core/test_tier_stable_callback.py
```

**Formel-Refs:** `F.LNN.GROW.003` (Konsumenten-Glue)

**Akzeptanzkriterien:**
1. `_on_tier_stable(n)` produziert genau **zwei** Engine-Events:
   * `engine/event` mit `kind = "lnn_grew"`,
     payload `{tier: n, prev_dim, new_dim, scale}`.
   * `engine/event` mit `kind = "tier_stable"`,
     payload `{tier: n, lnn_iD, wells, concepts, frameworks}`.
2. Events werden direkt nach `lnn.grow()` geschickt; bei NATS-Fehler
   im Hub wird die Engine **nicht** blockiert (Buffered + Retry).
3. **Idempotenz-Guard**: zweiter Aufruf mit gleichem `n` → no-op.
4. **Reihenfolge**: T0 niemals Trigger; T1 vor T2 vor T3 (numerisch
   monoton in `_tier_growth_done`).

**Tests:**
* `tests/core/test_tier_stable_callback.py::test_two_events_emitted`
* `tests/core/test_tier_stable_callback.py::test_event_payload_shape`
* `tests/core/test_tier_stable_callback.py::test_idempotent_guard`
* `tests/core/test_tier_stable_callback.py::test_t0_never_triggers`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~350 Lines diff
**Fertig wenn:** AC + CI grün.

---

### M4.8 — numerical-conformance-suite

**Branch:** `test/numerical-conformance-suite`
**Issue:** `#NNN`
**Vorbedingungen:** M4.2, M4.3, M4.4, M4.5, M4.6, M4.7 gemerged
**Berührte Pfade:**
```
tools/reference/                          ← Notebooks + Daten
├── lnn_state_001_reference.ipynb
├── lnn_state_002_reference.ipynb
├── lnn_grow_003_reference.ipynb
└── data/
    ├── lnn_state_001.npz
    ├── lnn_state_002.npz
    └── lnn_grow_003.npz
engine/tests/conformance/numerical/
├── __init__.py
├── test_F_LNN_STATE_conformance.py
├── test_F_LNN_GROW_conformance.py
└── test_F_LNN_INPUT_conformance.py
```

**Formel-Refs:** alle F.LNN.* aus M4.

**Akzeptanzkriterien:**
1. **Reference-Notebook**-Pfad ist klar: bei Bedarf reproduzierbar mit
   `make reference-data`. Notebook hat einen festen Random-Seed.
2. **Toleranzen**:
   * Single-Step `h_new`: `np.allclose(actual, expected, rtol=1e-6, atol=1e-9)`.
   * 1000-Step-Trajectory: `rtol=1e-5, atol=1e-8` (numerische Drift
     toleriert).
3. **Cross-Backend-Test**: NumPy-Variante vs. PyTorch-Variante (sofern
   aktiviert) ergibt identische Werte innerhalb der Toleranz.
4. **Marker** in der Status-Tabelle: jede F-ID wechselt von
   `implemented` auf `verified`, sobald die zugehörigen Conformance-
   Tests grün sind.

**Tests:**
* alle `tests/conformance/numerical/...`

**Ressourcen-Budget:** Tests laufen lokal in < 10 s; CI-Job
`numerical-conformance` ist Pflicht-Gate ab M4.
**Geschätzte PR-Größe:** ~600 Lines diff
**Fertig wenn:** AC + CI grün; Registry-Status für alle F.LNN.* auf
`verified`.

---

### M4.9 — engine-summary-now-with-real-state

**Branch:** `feature/engine-summary-real-state`
**Issue:** `—`
**Vorbedingungen:** M4.8 gemerged
**Berührte Pfade:**
```
engine/src/terra_engine/runtime/summary_emitter.py   ← Stub-Werte → echt
engine/tests/runtime/test_summary_real_state.py
```

**Formel-Refs:** —

**Akzeptanzkriterien:**
1. Felder `tier_counts`, `lnn.iD`, `lnn.norm`, `lnn.delta`,
   `lnn.velocity` werden aus dem realen `EngineState` befüllt.
2. `ghost_queue`-Feld bleibt leer (kommt mit künftiger Phase, die
   Ghost-Materialisierung implementiert).
3. Ende-zu-Ende-Smoke: Engine läuft 60 s gegen Hub, Hub-`/v1/diagnostic`
   spiegelt aktuelle Werte.

**Tests:**
* `tests/runtime/test_summary_real_state.py::test_summary_reports_tier_counts`
* `tests/runtime/test_summary_real_state.py::test_summary_reports_lnn_iD_grows`
* `tests/runtime/test_summary_real_state.py::test_summary_velocity_history`

**Ressourcen-Budget:** —
**Geschätzte PR-Größe:** ~250 Lines diff
**Fertig wenn:** AC + CI grün.

---

## 6. Phasen-Gate

M4 gilt als grün, wenn:

1. M4.1 – M4.9 in `00-index.md` auf `[x]`.
2. Alle F.LNN.*-Einträge in `formulas/registry.md` auf `verified`.
3. Numerical-Conformance-Suite ist als CI-Pflicht-Gate aktiv.
4. End-to-End: Engine läuft 30 min, Tier-Stable wird mindestens 1× ausgelöst,
   `lnn.iD` wächst korrekt, Hub-`/v1/diagnostic` zeigt es.
5. Tag `v0.5.0` gepusht.

---

## 7. Erledigte Änderungen

— *(noch leer)*

---

*Stand: 2026-05-08 · Greenfield-Initial · M4 noch nicht eröffnet*
