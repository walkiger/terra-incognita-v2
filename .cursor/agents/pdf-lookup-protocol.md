---
name: pdf-lookup-protocol
description: PDF/Formel-Lookup-Vertrag (kein eigenständiger Subagent — operationelle Anleitung, die im Implementierungs-/Test-/Audit-Workflow als „Pseudo-Subagent" benutzt wird). Wenn andere Subagenten oder das Hauptmodell Formeln, Definitionen, Beweise oder Hyperparameter aus dem Korpus brauchen, dann FOLGEN sie diesem Profil. Kanonische Spezifikation: `app/docs/greenfield/protocols/pdf-lookup.md`.
model: composer-2-fast
is_background: false
---

> **Wichtige Klarstellung.** Diese Datei beschreibt **keinen** neuen
> Subagent-Typ (die `Task`-API erlaubt keine Laufzeit-Registrierung).
> Sie definiert ein **Protokoll**, nach dem alle bestehenden Subagenten
> sowie das Hauptmodell handeln, wenn sie das PDF-Korpus
> (`research/extracted/<document_id>/`) konsultieren.
>
> **Single-Source-of-Truth:** `app/docs/greenfield/protocols/pdf-lookup.md`.
> Diese Datei ist der **operative Spickzettel** — kürzer, mit klaren
> Trigger-Mustern.

---

## Wann dieses Protokoll greift

* Du sollst eine Formel implementieren → **immer**.
* Du brauchst eine Hyperparameter-Begründung aus einem Paper → **immer**.
* Du sollst einen Test-Referenzwert liefern → **immer**.
* Du sollst einen Audit-/Security-Hinweis mit Quellen­bezug abgeben → **immer**.
* Du baust nur Tooling/CI ohne mathematischen Bezug → **nicht nötig**.

---

## 3 Pfade in dieser Reihenfolge

1. **Pfad 1 — direktes Lesen.**
   * `Grep` über `research/extracted/**/l4_formulas.json`,
     `l1_raw_text.json`, `l4_analysis.json`.
   * `Read` auf den getroffenen `<document_id>`-Ordner.
2. **Pfad 2 — `explore`-Subagent.**
   * `Task(subagent_type=explore, …)` mit klarem Auftrag „**nur** unter
     `research/extracted/` lesen, **kein** `source.pdf`".
3. **Pfad 3 — `research-agent` (neue Extraktion).**
   * `Task(subagent_type=research-agent, …)` mit Quelle, geforderter
     `document_id`, Layer-Anforderung L0–L4.
   * Nur durch `orch` zu beauftragen.

> **Regel.** Pfad 1 ist Pflicht vor Pfad 2; Pfad 2 ist Pflicht vor Pfad 3.

---

## Anfrage-Vertrag (im Subagent-Prompt oder Sessionprotokoll)

```
{
  "request_kind":          "formula" | "definition" | "value" | "proof_step",
  "subject":               "<knapp>",
  "context":               "<wofür: Code-Pfad, Test-ID, Doc-Anker>",
  "preferred_lookup_path": 1 | 2 | 3,
  "must_be_canonical":     true | false,
  "fallback_acceptable":   true | false,
  "requested_fields":      ["latex","verbatim_snippet","page","equation_label","document_id","pdf_sha256","context_lines"]
}
```

---

## Antwort-Vertrag (was du IMMER lieferst)

```
{
  "result_kind": "found" | "found_with_caveats" | "not_in_corpus",
  "matches": [
    {
      "document_id":      "<slug>",
      "pdf_sha256":       "<hex>",
      "pages":            [int, ...],
      "equation_label":   "<z.B. (1)>",
      "verbatim_snippet": "<exakter Auszug>",
      "latex":            "<rekonstruierte Form>",
      "context_lines":    "<5–10 Zeilen Umfeld>",
      "confidence":       "high" | "medium" | "low",
      "source_layer":     "l4_formulas" | "l1_raw_text" | "l2_outline" | "l3_entities" | "l4_analysis"
    }
  ],
  "caveats": [...],
  "next_action": "use_match" | "request_path_3_extraction" | "abort_with_owner_decision"
}
```

**Pflichtfelder pro Match:** `document_id`, `pages`, `verbatim_snippet`,
`confidence`. Andere nur, wenn explizit in `requested_fields`.

---

## Confidence-Regeln (Kurzfassung)

* `high` → klarer `l4_formulas`-Treffer mit Equation-Label.
* `medium` → `l4_formulas` ohne Label oder leichte Mehrdeutigkeit.
* `low` → nur `l1_raw_text` / `l4_analysis` → Pflicht: zweiter
  Layer + bevorzugt Pfad-2-Bestätigung.

`low` ohne Disambiguierung darf **nicht** in
`app/docs/greenfield/formulas/registry.md` als Quelle eingetragen werden.

---

## Quellen-Vorrang

1. Canonical Paper (z.B. Hasani 2022 für CfC, Hopfield 1982 für Hopfield).
2. Sekundärquellen mit identischer Form.
3. Verwandte Form (klar als „verwandt, nicht identisch" gekennzeichnet).

---

## Negative Antwort

Wenn Pfad 1 + 2 erfolglos und das Dokument **nicht** in `extracted/`:

* `result_kind = "not_in_corpus"`
* `next_action = "request_path_3_extraction"`
* Implementierung pausiert, bis `research-agent` fertig ist.

---

## Determinismus & Reproduzierbarkeit

* **Kein internes Caching.**
* `Grep`-Patterns in der Antwort dokumentieren.
* Pfad-2-Subagent-Antworten **immer** mit `document_id`, Seite, Layer.

---

## Verbote

* Kein Lesen von `source.pdf` (binär) — Token-Verschwendung.
* Keine Antwort „aus dem Gedächtnis" — nur was im Korpus belegt ist.
* Keine Änderung an `app/docs/greenfield/formulas/registry.md` außerhalb
  einer regulären `documentation-agent`- oder Implementierungs-PR.

---

## Verweise

* Spezifikation (lang): `app/docs/greenfield/protocols/pdf-lookup.md`
* Korpus-Layout: `research/extracted/README.md`
* Registry: `app/docs/greenfield/formulas/README.md` + `…/registry.md`
* Ergänzende Regeln: `Anweisungen.md` §7, `CLAUDE.md` §„Wo finde ich was".

---

*Stand: 2026-05-08 · Greenfield-Initial · gilt repoweit für alle
Subagenten und das Hauptmodell.*
