# ADR-006 — `F.{POL}.{TOPIC}.{NNN}`-Formel-ID-Schema

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `formulas/README.md`,
  `formulas/registry.md`, `protocols/pdf-lookup.md`.

## Context

Die Implementierung referenziert mathematische Formeln aus mehreren
PDF-Quellen sowie aus eigener Ableitung. Ohne stabile, sortier­bare
IDs wird die Wartung schwer:

* Tests können nicht eindeutig auf eine Formel zeigen.
* Code-Audits können „Wurde diese Formel verifiziert?" nicht
  effizient beantworten.
* Die PDF-Lookup-Subagenten haben keinen klaren Anker.

## Decision

Wir benutzen das Schema **`F.{POL}.{TOPIC}.{NNN}`**:

* `F` — Präfix (literally `F` für „Formula").
* `POL` — System-Pol: `LNN`, `EBM`, `KG`, oder `REPLAY` /
  `INFER` / `LOG` (für sub-systems).
* `TOPIC` — Bereich, kurz, in CAPS:
  * Beispiele LNN: `STATE`, `INPUT`, `GROW`, `FOCUS`, `LOSS`.
  * Beispiele EBM: `ENERGY`, `WELL`, `THETA`, `ATTRACTOR`.
  * Beispiele KG: `HEBBIAN`, `SPREAD`, `TIER`, `PRUNE`.
  * Beispiele REPLAY: `HYBRID`, `DENSITY`, `RANK`.
* `NNN` — sequentielle Nummer pro `(POL, TOPIC)`-Paar, dreistellig,
  führende Nullen.

Beispiele:

* `F.LNN.STATE.001` — CfC Hidden-State-Update.
* `F.EBM.WELL.002` — Member-Set-Immutability.
* `F.REPLAY.HYBRID.001` — Combined-Score.

## Consequences

* **Positiv:**
  * Eindeutig sort­ier­bar; klar lesbar.
  * Code-Marker `# F.LNN.STATE.001` machen Verweise grep­bar.
  * Test-IDs `test_F_LNN_STATE_001_*` koppeln Test ↔ Formel.
* **Negativ:**
  * Refactoring der Topic-Bezeichner ist teuer (alle Verweise
    müssen mitwandern). Mitigation: Topic-Namen bewusst
    konservativ wählen (`STATE`, `INPUT`, `GROW`, …).
* **Neutral:**
  * Schema reicht für > 999 Einträge pro Topic — Erfahrung
    legt nahe, dass weniger als 50 nötig sind.

## Alternatives Considered

* **UUIDs**: nicht lesbar, keine Sortierbarkeit.
* **DOI-ähnliche IDs**: zu starr, koppelt an externe Autorität.
* **Ad-hoc Namen** (z.B. `lnn_step`-formel): nicht eindeutig,
  verwechselt sich mit Funktions­namen.

## References

* `formulas/README.md`
* `formulas/registry.md`
* `protocols/pdf-lookup.md`

---

*Greenfield-Initial-ADR.*
