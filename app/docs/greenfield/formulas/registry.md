# `formulas/registry.md` — Formula Registry

> **Lebendiges Dokument.** Alle Formel-Einträge des Greenfield-Plans.
>
> **Konvention** ↗ `README.md` in diesem Ordner.
> **Lookup-Pfad** ↗ `../protocols/pdf-lookup.md`.
>
> Status-Trichter: `spec-ready → implemented → verified → superseded/retracted`.

---

## Navigations-Index

* [F.LNN.STATE.*](#flnnstate)
* [F.LNN.INPUT.*](#flnninput)
* [F.LNN.GROW.*](#flnngrow)
* [F.LNN.FOCUS.*](#flnnfocus)
* [F.EBM.ENERGY.*](#febmenergy)
* [F.EBM.WELL.*](#febmwell)
* [F.EBM.THETA.*](#febmtheta)
* [F.KG.HEBBIAN.*](#fkghebbian)
* [F.KG.SPREAD.*](#fkgspread)
* [F.KG.TIER.*](#fkgtier)
* [F.REPLAY.HYBRID.*](#freplayhybrid)
* [Quellenliste (Korpus 2026-05-08)](#quellenliste-korpus-2026-05-08)

---

## F.LNN.STATE.*

### F.LNN.STATE.001 — CfC Hidden-State Update (Liquid Time-Constant)

**Status:** spec-ready

**Source:**

* **Primary (canonical):** Hasani et al., *Closed-Form Continuous-Time
  Neural Networks*, Nature Machine Intelligence, 2022.
  *Hinweis: Im aktuellen Korpus (`research/extracted/`) noch nicht
  separat extrahiert. **M4.1 erstellt diese Extraktion** über
  Lookup-Pfad 3 (`research-agent`) — bevor diese ID auf `implemented`
  wechselt, muss der `document_id` hier eingetragen sein.*
* **Secondary (extrahiert):**
  * `document_id`: `arxiv_1510_02777v2_cs_lg_7_feb_2016_early_inference_in_energy_based_mode_20260508T150642Z`
  * `pdf_sha256`: `4aa7edff3c632ad741f5419d3a44870e03dde22e35c635e26eac1d09c1a3e6f1`
  * `pages`: [2]
  * `equation_label`: `(1)` (Bengio/Fischer Leaky-Integration)
  * `verbatim_snippet`:
    > „its previous value, with f = (fx, f h) to denote the parts of f that respectively outputs the predictions on the clamped (visible) units and on the unclamped (hidden) units. The time evolution of the unclamped units is assumed to follow a leaky integration equation, i.e., $h_{t+1} = f_h(s_t, \eta_t) = h_t + \epsilon (R_h(\tilde s_t) - h_t)$ (1)"
  * Note: Diese leaky-integration-Form ist **strukturell verwandt** mit
    der CfC-Form, dient aber nur als sekundäre Begründung der
    Liquid-Time-Constant-Idee. Die kanonische CfC-Variante steht in
    Hasani 2022.

* **Tertiary (extrahiert, gewählter Vergleich):**
  * `document_id`: `were_rnns_all_we_needed_leo_feng_mila_universit_e_de_montr_eal_borealis_20260508T150735Z`
  * `pdf_sha256`: `52828934a227cb83cc72a15194ea1937a6160c6c8e46619a7820dde5d85ccb40`
  * Note: Diskussion vereinfachter, time-folded RNN-Updates;
    historisch instruktiv für die Frage, *was* überhaupt gebraucht wird.

**LaTeX (Bestform für die Implementierung):**

\[
h_{t+1} \;=\; \frac{(h_t \cdot \exp(-\,\Delta t \,/\, \tau)) \;-\; (g \cdot s \cdot f)}{1 \;+\; \frac{\Delta t}{\tau} \cdot f}
\]

**Symbol-Glossar:**

| Symbol      | Domäne / Wert                              | Bedeutung                                                      |
|-------------|---------------------------------------------|----------------------------------------------------------------|
| `h_t`        | ℝ^{hD}                                      | Hidden-State zum Tick `t`                                      |
| `Δt`         | s; `1 / tick_hz` = 0.125 s                  | Zeitschritt                                                    |
| `τ`          | s; `[τ_min, τ_max]`                          | Liquid Time-Constant; Modulation in F.LNN.STATE.002             |
| `f`          | ℝ                                           | Forget-Gate                                                    |
| `g`          | ℝ^{hD}                                      | Input-Gate                                                     |
| `s`          | ℝ^{hD}                                      | Self-Signal (NCP-Wiring)                                        |

**Consumed by:**

* `engine/src/terra_engine/core/lnn_kernels.py::cfc_step` (NumPy)
* `engine/src/terra_engine/core/lnn_kernels_torch.py::cfc_step` (PyTorch, optional)

**Tests:**

* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_matches_reference`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_zero_input`
* `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_post_grow_dim`
* `tests/conformance/numerical/test_F_LNN_STATE_conformance.py`

**Notes:**

* Numerische Stabilität: `τ ∈ [0.05, 5.0]`-Klemme; bei `τ → 0` → Update
  nahe Identität; bei `τ → ∞` → Update vollständig getrieben durch `g·s`.
* In bestehender Implementierung (`docs/ARCHITECTURE.md` §1) wird die
  Form
  `h_new = (h - g·s·f) / (1 + dt/τ · f)` verwendet — algebraisch
  äquivalent zur Bestform oben (mit `exp(-Δt/τ) ≈ 1`-Approximation).
  Greenfield übernimmt **die Bestform mit Exponential**, weil sie für
  große `Δt` numerisch besser ist.

---

### F.LNN.STATE.002 — τ-Modulator

**Status:** spec-ready

**Source:** wie F.LNN.STATE.001 (Hasani 2022 als kanonische Quelle).

**LaTeX:**

\[
\tau(h, u) \;=\; \tau_0 \,/\, \big(1 + \tau_0 \cdot \sigma(W_{th} h + W_{ti} u + b_t)\big)
\]
mit Klammer `τ ∈ [τ_min, τ_max]`.

**Symbol-Glossar:**

* `τ_0` — Default-Time-Constant, learned/initial.
* `W_th, W_ti, b_t` — Lernbare Parameter.
* `σ` — Sigmoid.

**Consumed by:**

* `engine/src/terra_engine/core/lnn_kernels.py::tau_modulator`

**Tests:**

* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_clamping`
* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_monotonicity_in_input`
* `tests/core/test_lnn_state_002.py::test_F_LNN_STATE_002_continuity`

---

### F.LNN.STATE.003 — Self-Signal NCP-Wiring

**Status:** spec-ready

**Source:** abgeleitet aus den NCP-/Worm-Brain-Wiring-Arbeiten (Lechner
et al.). Im Korpus nicht als eigenständiges Paper extrahiert; geplant
als `M4.1`-Extraktion über Lookup-Pfad 3.

**LaTeX:**

\[
s \;=\; \tanh(W_{sh} \cdot h + b_s)
\]

**Symbol-Glossar:**

* `W_sh, b_s` — Lernbare Parameter.

**Consumed by:**

* `engine/src/terra_engine/core/lnn_kernels.py::self_signal`

**Tests:**

* `tests/core/test_lnn_state_003.py::test_F_LNN_STATE_003_bounded`
* `tests/core/test_lnn_state_003.py::test_F_LNN_STATE_003_zero_h_zero_signal`

---

## F.LNN.INPUT.*

### F.LNN.INPUT.001 — Multi-Tier Input-Vektor

**Status:** spec-ready

**Source:** Mathematik aus `docs/ARCHITECTURE.md` §3 + bestehender
Codebasis-Praxis (`backend/core/build_lnn_input`).

**LaTeX (konzeptuell):**

\[
u(w, \text{scale}, \text{state}) \;=\; \mathrm{concat}\Big(\underbrace{\mathrm{wv}(w, B)}_{T_0\text{-Channel}}, \; \underbrace{\mathrm{vw}_1(w) \cdot \alpha_1}_{T_1\text{-Channel}}, \; \dots, \; \underbrace{\mathrm{vw}_N(w) \cdot \alpha_N}_{T_N\text{-Channel}}\Big)
\]
mit `α_n = scale × tier_weight(n, seen)`.

**Symbol-Glossar:**

* `wv(w, B)` — Hash-basierter Wort-Vektor in B Dimensionen.
* `vw_n(w)` — Best-Match-Score in Tier `n`.
* `tier_weight(n, seen)` — Tier-Bonus-Funktion (siehe F.LNN.INPUT.002).

**Consumed by:**

* `engine/src/terra_engine/core/lnn_input.py::build_lnn_input`

**Tests:**

* `tests/core/test_build_lnn_input.py::test_layout_t0_only`
* `tests/core/test_build_lnn_input.py::test_layout_with_t1`
* `tests/core/test_build_lnn_input.py::test_dim_matches_lnn_iD`

---

### F.LNN.INPUT.002 — Tier-Weight-Bonus

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §4 (Hebbian write-back, Tier-Bonus-
Tabelle).

**LaTeX:**

\[
\text{tier\_weight}(n, \text{seen}) \;=\; 1 + 0.5 \cdot n \cdot f_\text{seen}(\text{seen})
\]
mit `f_seen` als Sättigungsfunktion (Default: clamp(seen/3, 0, 1)).

**Consumed by:**

* `engine/src/terra_engine/core/tier.py::tier_weight`

**Tests:**

* `tests/core/test_tier_weight.py::test_F_LNN_INPUT_002_monotonic_in_n`
* `tests/core/test_tier_weight.py::test_F_LNN_INPUT_002_bounded_in_seen`

---

## F.LNN.GROW.*

### F.LNN.GROW.001 — Wachstumsformel pro Tier

**Status:** spec-ready

**Source:** `Anweisungen.md` §7 *Non-Negotiables LNN* + bestehender
Code (`backend/core/lnn.py::grow`).

**LaTeX:**

\[
\dim(N) \;=\; B \cdot \big(1 \;+\; \tfrac{N \cdot (N+1)}{2}\big)
\]

**Tabelle (B = 256):**

| N | dim(N) |
|---|--------|
| 0 | 256    |
| 1 | 512    |
| 2 | 1024   |
| 3 | 1792   |
| 4 | 2816   |
| 5 | 4096   |

**Consumed by:**

* `engine/src/terra_engine/core/lnn.py::target_dim_for_tier`

**Tests:**

* `tests/core/test_lnn_grow.py::test_F_LNN_GROW_001_target_dim_table`

---

### F.LNN.GROW.002 — Tier-Min-Members-Schwelle

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §3 *Growth trigger*.

**LaTeX (Tabellenform):**

\[
\text{tier\_min\_members}(n) \;=\; \begin{cases} 1, & n = 0 \\ 3, & n = 1 \\ 5, & n = 2 \\ 8, & n = 3 \\ 13, & n \geq 4 \end{cases}
\]

(Folge: 1, 3, 5, 8, 13 — Fibonacci-ähnlich; rationalisiert durch die
Vorstellung, dass jede neue Tier-Schicht mehr Stabilität braucht.)

**Consumed by:**

* `engine/src/terra_engine/core/tier.py::tier_min_members`

**Tests:**

* `tests/core/test_tier_thresholds.py::test_F_LNN_GROW_002_tier_min_members_table`

---

### F.LNN.GROW.003 — Tier-Stable-Bedingung

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §3 + `Anweisungen.md` §7
*`_on_tier_stable()` als einzige `lnn.grow()`-Quelle*.

**LaTeX (logisch):**

```
TierStable(n) := |active_for_tier(n)| ≥ tier_min_members(n)
                  ∧ n ∉ _tier_growth_done
                  ∧ n > 0
                  ⟹ _on_tier_stable(n)
```

**Consumed by:**

* `engine/src/terra_engine/core/lnn_input.py::build_lnn_input` (Trigger-Stelle)
* `engine/src/terra_engine/core/tier.py::_on_tier_stable` (Reaktion)

**Tests:**

* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_fires_once`
* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_t0_does_not_grow`
* `tests/core/test_tier_callback.py::test_F_LNN_GROW_003_idempotent_when_called_twice`

---

### F.LNN.GROW.004 — Initial-Scale neuer Channels

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §3 *_onTierStable*.

**LaTeX:**

\[
\text{initial\_scale}(n) \;=\; \max(0.08, \; 0.25 - 0.05 \cdot n)
\]

**Tabelle:**

| n | scale |
|---|-------|
| 1 | 0.20  |
| 2 | 0.15  |
| 3 | 0.10  |
| 4 | 0.08  |
| 5 | 0.08  |

**Consumed by:**

* `engine/src/terra_engine/core/tier.py::initial_scale_for_tier`

**Tests:**

* `tests/core/test_lnn_grow.py::test_F_LNN_GROW_004_initial_scale_curve`

---

## F.LNN.FOCUS.*

### F.LNN.FOCUS.001 — `_lnnFocus(word)` Aufmerksamkeits-Score

**Status:** spec-ready (Implementation in einer Folgephase nach M4)

**Source:** `docs/ARCHITECTURE.md` §5.

**LaTeX:**

\[
\text{focus}(w) \;=\; \mathrm{clip}\Big(0.3 + \frac{1}{C} \sum_{i=0}^{|h|-1} h_i \cdot \mathrm{channel\_factor}(i, w), \; 0.3,\, 2.0\Big)
\]

mit `channel_factor` = Gewichtung pro Tier-Channel auf das Wort `w`.

---

## F.EBM.ENERGY.*

### F.EBM.ENERGY.001 — Hopfield-Energie

**Status:** spec-ready

**Source:** klassische Hopfield-Network-Literatur. Im Korpus mit
verwandten Quellen abgedeckt:

* `document_id`: `equilibrium_propagation_bridging_the_gap_between_energy_based_models_and_20260508T150645Z`
* `document_id`: `implicit_generation_and_modeling_with_energy_based_models_yilun_du_mit_c_20260508T065744Z`
* `document_id`: `maximum_entropy_generators_for_energy_based_models_rithesh_kumar1_sherji_20260508T150650Z`
* Note: alle drei diskutieren Energie-Funktionen über latenten
  Repräsentationen, die mit der Hopfield-Form über KG-Knoten algebraisch
  ähneln. Für die kanonische Hopfield-Form selbst eignet sich Hopfield
  1982 — derzeit nicht im Korpus, in v1.x als ergänzende Extraktion
  geplant.

**LaTeX:**

\[
E(\mathbf{x}) \;=\; -\,\tfrac{1}{2}\, \mathbf{x}^\top W \mathbf{x} \;-\; b^\top \mathbf{x}
\]

mit `x ∈ {0,1}^N` bzw. `[0,1]^N` für die kontinuierliche Variante.

**Consumed by:**

* `engine/src/terra_engine/core/ebm.py::hopfield_energy`

**Tests (in einer Folgephase):**

* `tests/core/test_ebm_energy.py::test_F_EBM_ENERGY_001_zero_x_zero_b_zero_energy`
* `tests/core/test_ebm_energy.py::test_F_EBM_ENERGY_001_symmetric_W`

---

### F.EBM.ENERGY.002 — KG-projizierte Energie pro Knoten

**Status:** spec-ready

**Source:** abgeleitet aus den oben genannten EBM-Quellen +
`docs/ARCHITECTURE.md` §6 (Wells-Lebenszyklus).

**LaTeX:**

\[
E_{\text{node}}(v) \;=\; -\,\sum_{u \in N(v)} W_{vu} \cdot a_u \;-\; b_v
\]

mit `a_u` als aktueller Aktivität von Knoten `u` und `N(v)` als Nachbarn
in `KG_EDGES`.

**Consumed by:** `engine/src/terra_engine/core/ebm.py::node_energy`

---

### F.EBM.ENERGY.003 — Energie-Gradient-Schritt

**Status:** spec-ready

**LaTeX:**

\[
\Delta a_v \;=\; -\eta \cdot \nabla_v E_{\text{node}}(v)
\]

mit `η = ebm_step_size` (default 0.02, settings).

---

## F.EBM.WELL.*

### F.EBM.WELL.001 — Well-Detection-Bedingung

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §6 + `Anweisungen.md` §7
*find_energy_wells universell*.

**LaTeX (logisch):**

```
WellCandidate(v) := E_node(v) < θ
                    ∧ stability_window(v) ≥ s_min
                    ⟹ promote(v, tier_n)
```

mit `θ = ebm_theta` (adaptiv, F.EBM.THETA.001) und `s_min` als
Mindest-Stabilitätsfenster.

**Consumed by:** `engine/src/terra_engine/core/ebm.py::find_energy_wells`

**Tests (Folgephase):**

* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_001_promotes_under_theta`
* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_001_no_promote_outside_window`

---

### F.EBM.WELL.002 — Member-Set-Immutability nach Geburt

**Status:** spec-ready

**Source:** `Anweisungen.md` §7 *Member-Sets immutable*.

**LaTeX (logisch):**

```
∀ well_w ∈ EBM_WELLS:  well_w.members ist frozenset, gesetzt bei birth(w)
                                    danach: well_w.members = const
```

**Consumed by:** `engine/src/terra_engine/core/ebm.py::EBMWell` (frozenset).

**Tests:**

* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_002_members_frozen`
* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_002_immutability_attempt_raises`

---

### F.EBM.WELL.003 — Make-Dormant statt Delete

**Status:** spec-ready

**Source:** `Anweisungen.md` §7 *ebm.wells niemals .pop()/.clear()/del*.

**LaTeX (logisch):**

```
deactivate(well_w) := well_w.dormant = True
                    ∧ EBM_WELLS bleibt verlustfrei
```

**Consumed by:** `engine/src/terra_engine/core/ebm.py::make_dormant`.

**Tests:**

* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_003_make_dormant_keeps_well`
* `tests/core/test_ebm_wells.py::test_F_EBM_WELL_003_no_pop_on_wells`

---

## F.EBM.THETA.*

### F.EBM.THETA.001 — Adaptiver Schwellenwert

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §6 + bestehender Code
(`backend/core/ebm.py::adapt_ebm_theta`).

**LaTeX:**

\[
\theta_{t+1} \;=\; \theta_t + \kappa \cdot \big(\bar{E}_t - \theta_t\big)
\]

mit `κ = ebm_theta_lr` (default 0.01) und `\bar{E}_t` als
gleitendem Durchschnitt der letzten `K` Energien.

**Consumed by:** `engine/src/terra_engine/core/ebm.py::adapt_ebm_theta`.

---

## F.KG.HEBBIAN.*

### F.KG.HEBBIAN.001 — LNN-zu-KG Hebbian-Update

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §4 *LNN → KG*.

**LaTeX:**

\[
W_{ij}^{\text{new}} \;=\; \min(1.0, \; W_{ij} + \eta \cdot b_{\text{tier}}(t_i, t_j))
\]

für die obersten 6 Knoten nach `_lnnFocus`-Score, mit
`b_tier(t_i, t_j) = 1 + 0.5 \cdot \max(t_i, t_j)`.

**Consumed by:** `engine/src/terra_engine/core/kg.py::lnn_to_kg_hebbian`.

---

### F.KG.HEBBIAN.002 — Decay für untere Knoten

**Status:** spec-ready

**LaTeX:**

\[
W_{ij}^{\text{new}} \;=\; \max(0, \; W_{ij} - \delta)
\]

für die unteren 12 Knoten, ohne Tier-Bonus, `δ = lnn_kg_decay` (default
0.0005).

**Consumed by:** `engine/src/terra_engine/core/kg.py::lnn_to_kg_hebbian`.

---

### F.KG.HEBBIAN.003 — Synaptic Pruning

**Status:** spec-ready

**LaTeX (logisch):**

```
prune(edge_e) := W_e < W_min
              ∧ stability_age(e) > τ_stable
              ⟹ remove(edge_e)
```

**Consumed by:** `engine/src/terra_engine/core/kg.py::synaptic_prune`.

---

## F.KG.SPREAD.*

### F.KG.SPREAD.001 — Spontaneous Activation Spreading

**Status:** spec-ready

**Source:** `docs/ARCHITECTURE.md` §9.

**LaTeX:**

\[
a_{v}^{\text{new}} \;=\; \alpha \cdot a_v + (1-\alpha) \cdot \frac{1}{|N(v)|} \sum_{u \in N(v)} W_{vu} \cdot a_u
\]

mit `α = spread_decay` (default 0.85).

**Consumed by:** `engine/src/terra_engine/core/kg.py::kg_spontaneous_prop`.

---

## F.KG.TIER.*

### F.KG.TIER.001 — Universelle Tier-Detection

**Status:** spec-ready

**Source:** `Anweisungen.md` §7 *find_energy_wells universell* +
`docs/ARCHITECTURE.md` §6.

**LaTeX (algorithmisch):**

```
find_energy_wells(state) :=
  for v in candidates:
     if WellCandidate(v) holds: promote(v, infer_tier(v))
  return promoted
```

mit `infer_tier(v)` = strukturelle Komplexität des Member-Sets.

**Consumed by:** `engine/src/terra_engine/core/ebm.py::find_energy_wells`.

---

### F.KG.TIER.002 — Stop-Word-Ausschluss

**Status:** spec-ready

**Source:** `Anweisungen.md` §7 *Stop-Words niemals T1+ Members*.

**LaTeX (logisch):**

```
∀ w ∈ STOP_WORDS, ∀ tier_n > 0:
   w ∉ tier_n.members  (außer lift_tier_exclusion(w))
```

**Consumed by:** `engine/src/terra_engine/core/tier.py::tier_stop_word_filter`.

---

## F.REPLAY.HYBRID.*

### F.REPLAY.HYBRID.001 — Hybrid-Combined-Score

**Status:** **implemented** (Bestand terra-080).

**Source:** Spezifikation in `docs/contracts/replay_timeline_window_v4.schema.json`
und `archive/legacy-docs/Implementierung.backend.api.md`. Numerischer Hintergrund:
* BM25 (Robertson/Spärck Jones, klassisch).
* Substring-Hits-Normalisierung (selbst entwickelt).
* Linearkombination mit `(α, β)`-Gewichten.

**LaTeX:**

\[
\text{score}(e) \;=\; \alpha \cdot \frac{\text{bm25}(e)}{\text{bm25}(e) + 1} \;+\; \beta \cdot \frac{\text{hits}(e)}{3}
\]

mit `α, β ∈ [0, 1]`, `NULL → 0`, Tie-Break `id ASC`.

**Consumed by:**

* **Bestand:** `backend/db/events.py::query_events_timeline_page`
* **Greenfield:** `backend/db/replay_query.py::query_window` (M1.6 portiert)

**Tests:**

* `tests/db/test_replay_query.py::test_hybrid_combined_score` (Greenfield)
* `tests/api/test_replay_hybrid_planner.py` (Bestand, weiterhin grün)

---

### F.REPLAY.HYBRID.002 — Effective-Policy-Resolver

**Status:** **implemented** (Bestand terra-080).

**LaTeX (logisch, Auszug):**

```
resolve_effective_ranking_policy(req) :=
  if req.ranking_policy == "auto":
     return default("combined" if q present and FTS available, else "substring_only")
  return req.ranking_policy
```

**Consumed by:** `backend/db/events.py::resolve_effective_ranking_policy`,
neu auch `backend/db/replay_query.py::resolve_effective_ranking_policy`.

---

## Quellenliste (Korpus 2026-05-08)

Auswahl der für die Registry relevantesten extrahierten Dokumente:

| `document_id`                                                                                       | Titel-Hinweis                                                                  | Verwendet für                                       |
|------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|------------------------------------------------------|
| `arxiv_1510_02777v2_cs_lg_7_feb_2016_early_inference_in_energy_based_mode_20260508T150642Z`           | Bengio/Fischer — Early Inference in EBMs                                       | `F.LNN.STATE.001` Sekundär; EBM-Hintergrund          |
| `equilibrium_propagation_bridging_the_gap_between_energy_based_models_and_20260508T150645Z`           | Equilibrium Propagation                                                        | `F.EBM.ENERGY.001` Hintergrund                       |
| `implicit_generation_and_modeling_with_energy_based_models_yilun_du_mit_c_20260508T065744Z`           | Du/MIT — Implicit Generation                                                   | `F.EBM.ENERGY.001` Hintergrund                       |
| `maximum_entropy_generators_for_energy_based_models_rithesh_kumar1_sherji_20260508T150650Z`           | MaxEnt EBMs                                                                    | `F.EBM.ENERGY.001` Hintergrund                       |
| `published_as_a_conference_paper_at_iclr_2024_learning_energy_based_model_20260508T150724Z`            | ICLR 2024 — Learning EBM                                                       | `F.EBM.ENERGY.001` Hintergrund                       |
| `arxiv_2507_02092v1_cs_lg_2_jul_2025_energy_based_transformers_are_scalab_20260508T150810Z`           | Energy-Based Transformers                                                      | EBM-Skalierung; Vollausbau                           |
| `were_rnns_all_we_needed_leo_feng_mila_universit_e_de_montr_eal_borealis_20260508T150735Z`            | Were RNNs All We Needed?                                                       | `F.LNN.STATE.001` Tertiär                            |
| `gated_feedback_recurrent_neural_networks_20260508T150641Z`                                            | Gated Feedback RNN                                                             | LNN-Hintergrund                                      |
| `how_to_construct_deep_recurrent_neural_networks_20260508T150640Z`                                     | Pascanu — Deep Recurrent NNs                                                   | LNN-Hintergrund                                      |
| `on_the_di_culty_of_training_recurrent_neural_networks_20260508T150638Z`                              | Pascanu — Difficulty of Training RNNs                                          | LNN-Hintergrund (Stabilität)                          |
| `hybrid_transformer_model_with_liquid_neural_networks_and_learnable_encod_20260508T065744Z`            | Hybrid Transformer + LNN                                                       | LNN-Anwendung — nicht Bestform-Quelle                 |
| `temporal_knowledge_graph_completion_a_survey_20260508T065744Z`                                       | Temporal KG Completion                                                         | KG-Spreading/Hebbian-Hintergrund                     |
| `a_survey_on_graph_neural_networks_for_knowledge_graph_completion_20260508T065744Z`                   | GNN-for-KG Survey                                                              | KG-Hintergrund                                       |
| `graph_neural_networks_a_review_of_methods_and_applications_20260508T065744Z`                         | GNN Review                                                                     | KG-Hintergrund                                       |
| `graph_structure_refinement_with_energy_based_contrastive_learning_20260508T065744Z`                  | EBM-Contrastive auf Graphs                                                     | EBM × KG Schnittstelle                               |
| `published_as_a_conference_paper_at_iclr_2022_neural_methods_for_logical_20260508T065744Z`            | Neural Methods for Logical Reasoning                                           | INFER-Hintergrund                                    |
| `neural_answering_logical_queries_on_knowledge_graphs_20260508T065744Z`                               | Logical Queries on KGs                                                         | INFER-Hintergrund                                    |

**Hinweise zu Lookup-Confidence:**

* Bei Einträgen mit `confidence: low` in `l4_formulas.json` ziehen wir
  zur Disambiguierung `l4_analysis.json` und/oder `l1_raw_text.json`
  hinzu (siehe `protocols/pdf-lookup.md`).
* Bei Sekundär-/Tertiär-Quellen verschieben wir die endgültige
  Bestform der Formel in den Notes-Block des Eintrags und markieren,
  welche Variante implementiert wurde.

---

*Stand: 2026-05-08 · Greenfield-Initial · alle Einträge `spec-ready`,
außer `F.REPLAY.HYBRID.001/002` (Bestand `implemented`).*
