# `protocols/pdf-lookup.md` — Formel- und Quellen-Lookup-Vertrag

> **Zweck.** Während der Implementierung wird *immer wieder* ein
> deterministischer, nachvollziehbarer Lookup gegen den
> PDF-Forschungs­korpus benötigt — für Formeln, Beweise, Symbole,
> Hyperparameter, Begründungen.
>
> Dieser Vertrag definiert: **wer fragt, wie gefragt wird, was
> zurückkommt, wann ein neues PDF extrahiert werden muss**.
>
> Komplementär: `.cursor/agents/pdf-lookup-protocol.md` (Agent-Profil
> mit identischen Pflichten, anderer Adressat).

---

## Inhalt

1. [Begründung & Geltungsbereich](#1-begründung--geltungsbereich)
2. [Korpus-Zustand 2026-05-08](#2-korpus-zustand-2026-05-08)
3. [Drei Lookup-Pfade](#3-drei-lookup-pfade)
4. [Anfrage-Schema (Request-Vertrag)](#4-anfrage-schema-request-vertrag)
5. [Antwort-Schema (Response-Vertrag)](#5-antwort-schema-response-vertrag)
6. [Quellen-Vorrang & Konflikt-Auflösung](#6-quellen-vorrang--konflikt-auflösung)
7. [Confidence- & Disambiguierungs-Regeln](#7-confidence--disambiguierungs-regeln)
8. [Negative Antwort: „Nicht im Korpus"](#8-negative-antwort-nicht-im-korpus)
9. [Re-Extraktion neuer PDFs (`research-agent`-Pfad)](#9-re-extraktion-neuer-pdfs-research-agent-pfad)
10. [Caching & Determinismus](#10-caching--determinismus)
11. [Fehlerklassen & Retry-Policy](#11-fehlerklassen--retry-policy)
12. [Anhang A — Beispiele](#anhang-a--beispiele)
13. [Anhang B — Beispiel-`Grep`-Patterns](#anhang-b--beispiel-grep-patterns)

---

## 1. Begründung & Geltungsbereich

* **Begründung.** Die Implementierung darf keine Formel „aus dem
  Gedächtnis" benutzen. Jede mathematische Aussage wird gegen ein
  konkretes PDF (über die `extracted/`-Schicht) verankert; dies ist
  Voraussetzung für den `verified`-Status der Formula Registry.
* **Geltungsbereich.** Anwendbar während:
  * **Implementierungs-Sessions** (`backend-implementation-agent`,
    `frontend-implementation-agent`).
  * **Test-Sessions** (`test-agent-strict-reviewer` — Referenzwerte,
    Ableitungen).
  * **Audit-Sessions** (`code-audit-agent`, `security-code-review-agent`).
  * **Doku-Sessions** (`documentation-agent`, Greenfield-Plan).
* **Nicht-Geltungsbereich.** Reine Tooling-/CI-Aufgaben ohne
  mathematischen Bezug. Hier ist kein Lookup nötig.

---

## 2. Korpus-Zustand 2026-05-08

* **Speicherort.** `research/extracted/<document_id>/`.
* **Pro Dokument vorhanden:**
  * `manifest.json` — Layer-Status (L0–L4).
  * `l1_raw_text.json` — Roher Text mit Seitenangaben.
  * `l2_outline.json` — Outline-/Section-Struktur.
  * `l3_entities.json` — Entitäten/Begriffe.
  * `l4_analysis.json` — Strukturierte Analyse.
  * `l4_formulas.json` — Formel-Liste mit `equation_label`,
    `verbatim_snippet`, `pages`, `confidence`.
  * `source.pdf` — Original-PDF (binär, **nicht** im Lookup
    benutzen — Konversion ist genau die Existenzberechtigung der
    L1–L4-Schicht).
* **Aktuelle Anzahl extrahierter Dokumente:** ≈ 60 (Stand 2026-05-08).
* **Wichtige Lücken (siehe `formulas/registry.md`):**
  * Kanonische Hasani et al. *Closed-Form Continuous-Time*-Veröffentlichung
    (2022) — geplant in `M4.1` über Pfad 3.
  * Kanonisches Hopfield-1982-Paper — geplant in einer EBM-bezogenen
    Folgephase über Pfad 3.

---

## 3. Drei Lookup-Pfade

Der Vertrag kennt **drei** Pfade, in dieser Reihenfolge zu wählen.

### Pfad 1 — `Grep`/`Read` direkt auf `extracted/`

* **Wann.** Begriff/Formel ist mit hoher Wahrscheinlichkeit bereits im
  Korpus.
* **Werkzeuge.**
  * `Grep` über `research/extracted/**/l4_formulas.json` — schnellster
    Treffer für formelbezogene Anfragen.
  * `Grep` über `research/extracted/**/l1_raw_text.json` — wenn `l4`
    nicht ausreicht (z.B. Variablen­glossar, Beweis­schritt).
  * `Read` direkt auf einen identifizierten Treffer-Kandidaten zur
    vollständigen Inspektion.
* **Vorteil.** Deterministisch, schnell, keine Subagent-Latenz.
* **Pflicht.** Vor Pfad 2 oder Pfad 3 ist Pfad 1 zu versuchen — sonst
  CI-Verstoß gegen die Determinismus-Regel.

### Pfad 2 — `explore`-Subagent über die L1–L4-Daten

* **Wann.** Anfrage erfordert *aggregierte* Synthese über mehrere
  Dokumente (z.B. „Welche EBM-Energieformen tauchen im Korpus auf?").
* **Werkzeuge.** `Task(subagent_type=explore, …)` mit explizitem
  Auftrag „lese **nur** L1–L4 unter `research/extracted/<id>/`".
* **Pflicht.** Der Explore-Subagent darf keinen `source.pdf` öffnen
  (würde Tokens verschwenden) und keine neuen Extraktionen anstoßen.

### Pfad 3 — `research-agent` für **neue** Extraktion

* **Wann.** Pfad 1 + 2 erfolglos, das Dokument ist **nicht** in
  `extracted/`, aber benötigt.
* **Werkzeuge.** `Task(subagent_type=research-agent, …)` mit den
  Pflichtangaben:
  * Quelle (URL oder `research/incoming/<file>.pdf`).
  * Geforderte Layer (mindestens L0–L4 inkl. `l4_formulas.json`).
  * Ziel-`document_id` (folgt der Slug-Konvention der bestehenden
    Dokumente; siehe `research/extracted/README.md`).
* **Pflicht.** Nach Abschluss wird die Formula Registry aktualisiert
  und das jeweilige `Implementierung.*.md` referenziert die neue
  `document_id` mit Seitenangabe + Equation-Label.

---

## 4. Anfrage-Schema (Request-Vertrag)

Jede Lookup-Anfrage **muss** die folgenden Felder enthalten —
schriftlich im Sessionprotokoll, im PR-Body, oder im Subagent-Prompt:

```
{
  "request_kind": "formula" | "definition" | "value" | "proof_step",
  "subject":      "kurze, eindeutige Beschreibung",
  "context":      "wozu die Antwort gebraucht wird (Code-Datei, Test, Doc)",
  "preferred_lookup_path": 1 | 2 | 3,
  "requested_fields": ["latex", "verbatim_snippet", "page", "equation_label", "document_id", "pdf_sha256", "context_lines"],
  "must_be_canonical": true | false,
  "fallback_acceptable": true | false
}
```

**Beispiel** (Implementierungs-Session, Pfad 1):

```
{
  "request_kind": "formula",
  "subject":      "CfC Hidden-State-Update (h_{t+1})",
  "context":      "engine/src/terra_engine/core/lnn_kernels.py::cfc_step (M4.2)",
  "preferred_lookup_path": 1,
  "requested_fields": ["latex", "verbatim_snippet", "page", "equation_label", "document_id"],
  "must_be_canonical": true,
  "fallback_acceptable": true
}
```

---

## 5. Antwort-Schema (Response-Vertrag)

Antwort **muss** in dieser Form vorliegen — auch wenn nur menschen-
lesbar im Chat zurückgegeben:

```
{
  "result_kind": "found" | "found_with_caveats" | "not_in_corpus",
  "matches": [
    {
      "document_id":     "<slug>",
      "pdf_sha256":      "<hex>",
      "pages":           [int, ...],
      "equation_label":  "<z.B. (1)>",
      "verbatim_snippet": "<exakter Auszug aus l1_raw_text.json>",
      "latex":           "<rekonstruierte LaTeX-Form, wenn rekonstruierbar>",
      "context_lines":   "<5-10 Zeilen Umfeld aus l1_raw_text.json>",
      "confidence":      "high" | "medium" | "low",
      "source_layer":    "l4_formulas" | "l1_raw_text" | "l2_outline" | "l3_entities" | "l4_analysis"
    }
  ],
  "caveats": [
    "warum ist das ggf. nicht die Bestform?",
    "welcher canonical_paper fehlt im Korpus?"
  ],
  "next_action": "use_match" | "request_path_3_extraction" | "abort_with_owner_decision"
}
```

**Pflichtfelder pro Treffer:** `document_id`, `pages`,
`verbatim_snippet`, `confidence`. Alle anderen Felder sind optional,
aber wenn anfragerseitig angefordert (`requested_fields`), dann
**verbindlich** zu liefern.

---

## 6. Quellen-Vorrang & Konflikt-Auflösung

Bei mehreren Treffern gilt diese Reihenfolge:

1. **Canonical-Paper** (z.B. Hasani 2022 für CfC, Hopfield 1982 für
   Hopfield-Energie). Wird *bevorzugt*, sobald im Korpus.
2. **Sekundärquellen mit identischer Form.** Werden als Begründung
   beigefügt (`caveats[]`).
3. **Verwandte Form / strukturell ähnlich.** Werden klar als „verwandt,
   nicht identisch" gekennzeichnet.

**Konflikt-Auflösung.** Wenn zwei Quellen sich widersprechen
(z.B. unterschiedliche Vorzeichenkonventionen):

* Beide Quellen in `caveats[]` aufführen.
* `must_be_canonical=true` der Anfrage erzwingt einen `next_action =
  request_path_3_extraction` für das fehlende canonical paper.
* `must_be_canonical=false` erlaubt eine *bewusst dokumentierte*
  Fallback-Wahl, die in der Formula Registry unter `Notes:` als
  abweichend zur klassischen Form markiert wird.

---

## 7. Confidence- & Disambiguierungs-Regeln

* **`confidence: high`** — `l4_formulas.json` enthält direkten Treffer
  mit Equation-Label und sauberem `verbatim_snippet`.
* **`confidence: medium`** — `l4_formulas.json` Treffer ohne
  Equation-Label oder mit leichten Mehrdeutigkeiten.
* **`confidence: low`** — Treffer nur in `l1_raw_text.json` /
  `l4_analysis.json`. **Disambiguierung erforderlich:**
  * Mindestens **zwei** Layer (`l1` + `l4_analysis`) müssen die Form
    bestätigen, **oder**
  * Ein Folge-Lookup über Pfad 2 (`explore`-Subagent) muss die
    konsistente Form über mehrere Dokumente belegen.
* **Ablehnung.** Treffer mit `confidence: low` und ohne
  Disambiguierung dürfen **nicht** in `formulas/registry.md` als Quelle
  geführt werden.

---

## 8. Negative Antwort: „Nicht im Korpus"

Antwort `result_kind = "not_in_corpus"` ist verbindlich, wenn:

* Pfad 1 keinen Treffer liefert (über `Grep` mit hinreichend weiten
  Pattern-Varianten — siehe Anhang B).
* Pfad 2 keinen Treffer liefert (`explore`-Subagent meldet 0 Matches).

Dann ist der `next_action` zwangsweise `request_path_3_extraction` mit:

* Vorgeschlagenem `document_id`.
* Quelle (URL, DOI, oder `research/incoming/<file>.pdf`).
* Begründung („wofür wird das gebraucht").

Die Implementierung **darf nicht** weiterlaufen, bis Pfad 3 abgeschlossen
ist — andernfalls wäre die Formula Registry inkonsistent.

---

## 9. Re-Extraktion neuer PDFs (`research-agent`-Pfad)

* **Auftraggeber.** Nur `orch` darf den `research-agent` zur Extraktion
  beauftragen (siehe `GLOBAL-CURSOR-RULES-Agent-OS.mdc`).
* **Eingaben.**
  * Quelle: URL oder Pfad in `research/incoming/`.
  * Ziel-`document_id` (Slug-Konvention).
  * Layer-Anforderung (mindestens L0–L4).
* **Ausgaben.**
  * Vollständige `extracted/<document_id>/`-Struktur.
  * `l4_formulas.json` mit allen mathematischen Aussagen + Confidence.
  * Aktualisierter PR-Body (oder `catchup.md`-Eintrag) mit Verweis
    auf den neuen `document_id`.
* **Akzeptanzkriterium.** `manifest.json` zeigt L0–L4 = `complete`.
* **Größenrahmen.** Neuer Branch `research/<topic>` mit ≤ 5
  Extraktionen pro PR (sonst Review unzumutbar).

---

## 10. Caching & Determinismus

* **Kein Caching innerhalb des Repos.** Jede Anfrage rechnet
  Pfad 1 / 2 frisch. So bleibt der Lookup nachvollziehbar.
* **Determinismus.** Ergebnisse sind deterministisch, **wenn**
  Quellpfade in der Antwort genannt sind und kein Subagent ohne
  Quellen­angabe geantwortet hat.
* **Was ändert das Ergebnis.** Ausschließlich neue Extraktionen über
  Pfad 3 — und diese sind sichtbar (Git-Diff in `research/extracted/`).

---

## 11. Fehlerklassen & Retry-Policy

| Klasse | Beispiel | Retry? | Empfehlung |
|--------|----------|--------|------------|
| `ambiguous_match` | mehrere identische Form-Kandidaten | nein | beide in `matches` aufnehmen, Caveat |
| `low_confidence_only` | nur `l1`/`l4_analysis`-Treffer | nein | Disambiguierung über Pfad 2 |
| `transient_explore_fail` | `explore`-Subagent timeout | ja, 1× | bei 2. Fail → Pfad 3 vorschlagen |
| `path3_quota_block` | `research-agent` kontingent | später | `SUBAGENT-DELEGATION-FALLBACK.mdc` greift; manuelle Extraktion vorbereiten |
| `binary_pdf_only` | PDF da, aber L1–L4 fehlen | nein | Manifest prüfen → `research-agent`-Folgejob |

---

## Anhang A — Beispiele

### A.1 Eine Formel mit klarem Treffer (Pfad 1)

**Anfrage.**

```
"Bitte F.LNN.STATE.001 — CfC Hidden-State-Update — verbatim aus
l4_formulas.json mit Equation-Label und Seite, must_be_canonical=true,
fallback_acceptable=true."
```

**Ablauf.** Greppe `Δt`, `tau`, `forget`, `cfc` über
`research/extracted/**/l4_formulas.json`. Kein Treffer für die
canonical CfC-Form (Hasani 2022 fehlt). `result_kind =
"found_with_caveats"` mit Sekundärquelle (Bengio/Fischer 2016) +
Caveat „canonical paper fehlt → Pfad 3 in M4.1".

### A.2 Mehrere EBM-Energie-Formen (Pfad 2)

**Anfrage.**

```
"Welche EBM-Energie-Formen tauchen im Korpus auf? Brauche eine
Übersicht inkl. document_id und page. preferred_lookup_path=2."
```

**Ablauf.** `explore`-Subagent liest L1+L4 quer durch alle relevanten
EBM-Dokumente. Antwort: `matches[]` mit 4–6 Einträgen, sortiert nach
`confidence: high` zuerst.

### A.3 Negative Antwort + Re-Extraktion (Pfad 3)

**Anfrage.**

```
"Bitte F.EBM.ENERGY.001 — Hopfield 1982 canonical — verbatim mit
Equation-Label."
```

**Ablauf.** Pfad 1: kein Treffer für „Hopfield 1982". Pfad 2:
`explore` bestätigt: nicht im Korpus. Antwort: `result_kind =
"not_in_corpus"`, `next_action = "request_path_3_extraction"`,
vorgeschlagene Quelle: PNAS 1982 (Hopfield, *Neural networks and
physical systems …*).

---

## Anhang B — Beispiel-`Grep`-Patterns

* **Formelsymbole (Pfad 1, schneller Hit-Finder):**
  * `\\Delta\\s*t`, `\\tau`, `dt\\s*/\\s*tau`, `forget`, `gate`, `sigm`
  * `\\bcfc\\b`, `\\bclosed\\s*-?\\s*form\\b`, `liquid\\s*time`
  * `Hopfield`, `\\bHopfield\\s*energy\\b`, `-\\s*1\\s*/\\s*2\\s*x\\^T\\s*W`
  * `BM25`, `bm25`, `score\\s*=\\s*\\\\alpha`, `combined`
* **Tier-Logik:**
  * `tier_min_members`, `_on_tier_stable`, `find_energy_wells`
  * `1,\\s*3,\\s*5,\\s*8,\\s*13`
* **Hyperparameter:**
  * `tick_hz`, `\\bdt\\b`, `\\bD t\\b`
* **Seitenfelder:**
  * `"pages"\\s*:\\s*\\[\\s*\\d`, `"equation_label"\\s*:\\s*"`

> Diese Patterns sind nur Startpunkte. Pflicht: das `Grep`-Pattern
> muss in der Antwort dokumentiert werden, damit der Lookup
> reproduzierbar ist.

---

*Stand: 2026-05-08 · Greenfield-Initial · gilt für alle Sessions, in
denen Code/Tests gegen die Formula Registry geschrieben werden.*
