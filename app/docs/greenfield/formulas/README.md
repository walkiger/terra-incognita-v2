# `formulas/README.md` — Formula Registry: Konvention & Workflow

> **Lebendiges Dokument.** Konvention zum Pflegen mathematischer
> Formeln, die das Terra-Incognita-System verwendet, mit
> Rückverfolgbarkeit zu PDFs, Tests und Code.

---

## 1. Zweck

Die Formula Registry (`registry.md`) ist die **Single Source of Truth**
für jede Formel, die im Code implementiert wird:

* **Identität:** stabile, sortierbare ID `F.{POL}.{TOPIC}.{NNN}`.
* **Inhalt:** kanonische LaTeX-Form, Symbolerklärung.
* **Quelle:** PDF-Verweis (`document_id` + Seite + `equation_label`).
* **Konsumenten:** Liste der Code-Pfade, die diese Formel verwenden.
* **Tests:** zugehörige Test-IDs.
* **Status:** `spec-ready` / `implemented` / `verified` / `superseded`.

---

## 2. ID-Schema

```
F.{POL}.{TOPIC}.{NNN}
```

* **`POL`** — Pol/Modul des Drei-Pol-Systems oder verwandtes Subsystem.
  Akzeptierte Werte (Stand 2026-05-08):

  | POL       | Bedeutung                                                   |
  |-----------|-------------------------------------------------------------|
  | `LNN`     | Liquid Neural Network (CfC, τ-Modulation, Wachstum)         |
  | `EBM`     | Energy-Based Model (Hopfield-Energie, Wells, Attraktoren)   |
  | `KG`      | Knowledge Graph (Hebbian, Spreading, Tier-Detection)         |
  | `INFER`   | Inference-Engine (R1–R4 Regeln, Pfad-Queries)               |
  | `PRESEED` | Preseed-Pipeline (Quality, Layer-Merge, Wave-Logik)         |
  | `REPLAY`  | Replay (Hybrid-Score, Density-Aggregate, FTS-Score-Funktion)|
  | `LOSS`    | Trainings-Verlust-Funktionen (kommen mit v2.0)              |

  Erweiterung möglich; jede neue POL-Kategorie wird hier dokumentiert.

* **`TOPIC`** — sprechender Bezeichner. Konvention: `UPPER_SNAKE`.

  Beispiele:
  * `STATE`, `GROW`, `INPUT`, `FOCUS` (LNN)
  * `ENERGY`, `WELL`, `ATTRACTOR`, `THETA` (EBM)
  * `HEBBIAN`, `SPREAD`, `TIER`, `RELATION` (KG)
  * `RULE_R1`, `RULE_R2`, `RULE_R3`, `RULE_R4` (INFER)
  * `BM25_HYBRID`, `DENSITY` (REPLAY)

* **`NNN`** — laufende Nummer mit drei Stellen: `001`, `002`, …
  Innerhalb desselben `POL.TOPIC` werden Nummern niemals
  wiederverwendet. Veraltete Formeln behalten ihre Nummer und werden
  als `Status: superseded` markiert; eine neue Variante bekommt eine
  neue Nummer.

---

## 3. Status-Trichter

```
spec-ready  →  implemented  →  verified  →  ─────────► superseded
                                       \─► retracted
```

| Status         | Bedeutung                                                                  |
|----------------|-----------------------------------------------------------------------------|
| `spec-ready`   | LaTeX/Quelle/Konsumenten dokumentiert; Code noch nicht geschrieben          |
| `implemented`  | Code-Pfad existiert und referenziert die ID per Kommentar                   |
| `verified`     | Numerical-Conformance-Test grün; Formel ist tatsächlich korrekt umgesetzt    |
| `superseded`   | Durch eine neuere Variante ersetzt; Eintrag bleibt, aber „siehe F.… NNN"    |
| `retracted`    | Sollte nie produktiv werden; nur historische Referenz                        |

---

## 4. Eintrags-Schema (per Formel)

```markdown
### F.LNN.STATE.001 — CfC Hidden-State Update

**Status:** implemented
**Source:**
- `document_id`: were_rnns_all_we_needed_leo_feng_mila_universit_e_de_montr_eal_borealis_20260508T150735Z
- `pages`: [3, 4]
- `equation_label`: (1)
- `verbatim_snippet`: "..."
- Note: in M4.1 wurde zusätzlich „Closed-Form Continuous-Time Neural Networks" (Hasani 2022) extrahiert und als Sekundärquelle eingetragen.

**LaTeX:**
\[
h_{t+1} = \frac{(h_t \cdot \exp(-\,\Delta t \,/\, \tau)) \;-\; \big(g \cdot s \cdot f\big)}{1 + \frac{\Delta t}{\tau} \cdot f}
\]

**Symbol-Glossar:**
- `h_t` ∈ ℝ^{hD} — verstecker Zustand zum Tick `t`
- `Δt = 1 / tick_hz` — Zeitschritt, Default 0.125 s
- `τ` ∈ [τ_min, τ_max] — Zeit-Konstante (variabel, siehe F.LNN.STATE.002)
- `f` — Forget-Gate, F.LNN.STATE.003
- `g` — Input-Gate, F.LNN.STATE.003
- `s` — Self-Signal (NCP-Wiring), F.LNN.STATE.003

**Consumed by:**
- `engine/src/terra_engine/core/lnn_kernels.py::cfc_step` (NumPy)
- `engine/src/terra_engine/core/lnn_kernels_torch.py::cfc_step` (PyTorch, optional)

**Tests:**
- `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_matches_reference`
- `tests/core/test_lnn_state_001.py::test_F_LNN_STATE_001_zero_input`
- `tests/conformance/numerical/test_F_LNN_STATE_conformance.py`

**Notes:**
- Variante mit gestaffeltem `f` für Multi-Tier-Channel; Originalliteratur
  benutzt einheitliches `f`.
- Numerische Stabilität: Klemmen `τ ∈ [0.05, 5.0]`.
```

Mindest-Felder: `Status`, `Source`, `LaTeX`, `Symbol-Glossar`,
`Consumed by`, `Tests`. `Notes` ist optional, aber empfohlen für jede
Implementierungs-Eigenart.

---

## 5. Workflow

### Eine neue Formel hinzufügen

1. **Lookup-Pfad** wählen (siehe `protocols/pdf-lookup.md`):
   * Pfad 1 (`Grep`/`Read`): wenn die Formel bereits in einem
     extrahierten PDF steht.
   * Pfad 2 (`explore`-Subagent): wenn mehrere PDFs synthetisiert
     werden müssen.
   * Pfad 3 (`research-agent`): wenn die Originalquelle im Korpus
     fehlt → neu extrahieren.
2. **ID vergeben** (`F.POL.TOPIC.NNN`).
3. **Eintrag** in `registry.md` schreiben (Status `spec-ready`).
4. **PR** mit `docs:`-Präfix; reviewt durch Backend- oder Engine-
   Implementierungs-Owner.

### Formel implementieren

1. **Code schreiben** mit Kommentar `# F.POL.TOPIC.NNN` direkt über der
   Stelle, an der die Formel realisiert ist.
2. **Tests** schreiben, die im Eintrag als „Tests" aufgelistet sind.
3. **Status** auf `implemented` setzen, PR mit `feat:`/`refactor:`-
   Präfix.

### Formel verifizieren

1. **Numerical-Conformance-Test** schreiben (Referenz-Werte).
2. CI-Job `numerical-conformance` muss grün sein.
3. **Status** auf `verified`.

### Formel ablösen

1. Neue Variante als neue ID anlegen, z. B. `F.LNN.STATE.004`.
2. Alte Variante bleibt; **Status** auf `superseded`, mit Cross-Reference
   („abgelöst durch F.LNN.STATE.004 — Begründung …").
3. Code-Konsumenten werden umgestellt; alter Code-Pfad entfernt
   (geschieht in eigener PR mit Begründung — `Anweisungen.md` §8 Living
   Document Policy).

---

## 6. Code-Marker-Disziplin

* **Pflicht:** Jede produktive Formel-Implementierung trägt **mindestens
  einen** Kommentar `# F.POL.TOPIC.NNN` direkt über dem Code-Block.
  Mehrere F-IDs in einer Funktion sind erlaubt; eine F-ID pro Block, in
  der sie hauptsächlich realisiert ist.
* **CI-Check:** Linter-Schritt `formulas-marker-coverage` prüft, dass
  jede Registry-ID mit Status `implemented`/`verified` mindestens einen
  Code-Marker im erwarteten Pfad findet.
* **Rückwärtsrichtung:** Linter prüft auch, dass jeder Code-Marker auf
  eine existierende Registry-ID verweist (gegen Tippfehler).

---

## 7. Test-Marker-Disziplin

* Tests, die explizit eine `F.*`-ID prüfen, **müssen** den Funktionsnamen
  in der Form `test_F_POL_TOPIC_NNN_*` tragen (Underscores statt Punkte).
* CI prüft die Existenz der Test-Funktionen, die im Registry-Eintrag
  aufgelistet sind.

---

## 8. PDF-Quellen-Form

Pflicht-Felder pro Source-Eintrag:

* **`document_id`** — Slug des PDFs in `research/extracted/<...>/`. Genau
  derselbe Wert wie in `manifest.json`.
* **`pages`** — Liste der Seiten, auf denen die Formel auftaucht
  (1-indexed, wie im PDF-Reader).
* **`equation_label`** — Originalreferenz im Paper (z. B. `(3)` oder
  `(LNN-1)`); leer, wenn nicht nummeriert.
* **`verbatim_snippet`** — wörtlicher Auszug aus `l4_formulas.json`
  (`evidence.verbatim_snippet`). Bei `confidence: low` zusätzlich
  Hinweis im Eintrag, dass das L1/L2-Surrounding zur Disambiguierung
  herangezogen werden muss.
* **`pdf_sha256`** (optional, empfohlen) — der SHA-256 aus
  `manifest.json.pdf_sha256` für absolute Eindeutigkeit (verhindert
  Drift, falls eine PDF-Version updatet).

Mehrere Quellen pro Formel sind erlaubt und gewünscht — z. B. ein
Methoden-Paper plus ein Survey.

---

## 9. Versionierung der Registry

* Die Registry selbst ist eine `.md`-Datei. Versionsverlauf liegt im
  Git-Log.
* Bei größeren Reorganisationen (z. B. neue POL-Kategorie) gibt es
  einen Eintrag oben in `registry.md`:
  ```markdown
  > **Registry-Schema-Version: 2** (2026-08-12) — POL `LOSS` hinzugefügt für Trainings-Verlust-Funktionen.
  ```

---

## 10. Querverweise

* `registry.md` — die eigentliche Liste
* `../protocols/pdf-lookup.md` — wie PDF-Stellen gefunden werden
* `../implementation/mvp/M4-first-formula-lnn-state.md` — erster realer
  Konsument der Registry
* `../00-glossary.md` Sektion 6 — F-ID-Schema in Kurzform

---

*Stand: 2026-05-08 · Greenfield-Initial*
