# ADR-007 — PDF-Lookup-Protokoll als Pseudo-Subagent

* **Status:** Accepted
* **Datum:** 2026-05-08
* **Bezug:** `protocols/pdf-lookup.md`,
  `.cursor/agents/pdf-lookup-protocol.md`,
  `formulas/registry.md`.

## Context

Während der Implementierung wird wiederholt ein Lookup gegen den
PDF-Korpus (`research/extracted/<document_id>/`) gebraucht — für
Formeln, Symbole, Beweise. Anfänglich wurde überlegt, einen
dedizierten neuen `pdf-lookup`-Subagent zu registrieren, der
schnell und billig diese Anfragen bedient.

Problem: die Cursor-Subagent-API erlaubt keine Laufzeit-Registrierung
neuer `subagent_type`-Werte. Nur die in der `Task`-Tool-Definition
genannten Typen sind verwendbar.

## Decision

Wir formalisieren statt eines neuen Subagent-Typs ein **Protokoll**,
nach dem alle bestehenden Subagenten und das Hauptmodell handeln,
wenn sie das Korpus konsultieren. Drei Pfade in dieser Reihenfolge:

1. **Pfad 1** — Direkt-`Grep`/`Read` auf
   `research/extracted/**/l4_formulas.json`.
2. **Pfad 2** — `explore`-Subagent für Synthese über mehrere
   Dokumente.
3. **Pfad 3** — `research-agent` für **neue** Extraktion (Pfad 1+2
   leer).

Der Vertrag (Anfrage-Schema, Antwort-Schema, Confidence-Regeln,
Quellen-Vorrang) ist in `protocols/pdf-lookup.md` festgehalten und im
Agent-Profil `.cursor/agents/pdf-lookup-protocol.md` als operativer
Spickzettel gespiegelt.

## Consequences

* **Positiv:**
  * Keine Abhängigkeit von einer Cursor-API-Änderung.
  * Pfad 1 ist deterministisch und schnell.
  * Klare Trennung: bestehender `research-agent` ist nur für *neue*
    Extraktionen nötig.
* **Negativ:**
  * Mehrfach­anfragen ähnlicher Form müssen erneut Pfad 1 ausführen
    (kein Caching). Mitigation: Lookup-Patterns (Anhang B in
    `protocols/pdf-lookup.md`) sind dokumentiert.
* **Neutral:**
  * Sollte Cursor in Zukunft Laufzeit-Registrierung erlauben, kann
    das Profil 1:1 als Subagent ausgerollt werden.

## Alternatives Considered

* **Eigener MCP-Server**: aufwendig zu deployen, würde Determinismus
  brechen (Server-Round-Trip).
* **Kein formelles Protokoll, nur ad-hoc Lookups**: führt zu
  Doku-Inkonsistenz und unverifizierten Formeln.

## References

* `protocols/pdf-lookup.md`
* `.cursor/agents/pdf-lookup-protocol.md`
* `formulas/registry.md`

---

*Greenfield-Initial-ADR.*
