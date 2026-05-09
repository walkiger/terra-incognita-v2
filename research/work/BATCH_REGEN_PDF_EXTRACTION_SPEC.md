# Batch-Neuauflage: PDF-Extraktion (Vorbereitung → Research-PR)

> **Owner:** `orch` · **Status:** Vorbereitung (dieser Stand) — noch **keine** Löschung alter Artefakte im selben Schritt.  
> **Zweck:** Alte „PDF-Überprüfung“-Ergebnisse unter `research/extracted/` **sauber entfernen** und **in einer einzigen konsistenten Batch** neu erzeugen, mit **messbar besserem Filter‑Signal** (u. a. **Formeln + Begründung der gewählten Form**).

---

## Zwei-PR‑Ablauf (verbindlich)

| PR | Inhalt | `research-agent` |
|----|--------|-------------------|
| **PR‑A (Prep, dieser Branch)** | Spezifikation, JSON‑Schema **`l4_formulas`**, Inventar‑Script **`list_extraction_inventory.py`**, Mindest‑Tests — **ohne** Löschen von `research/extracted/**`. | nicht zwingend |
| **PR‑B (Execution)** | Entfernen der betroffenen Ordner unter `research/extracted/<document_id>/` (artifact trees, nicht zwingend `incoming/*.pdf`), Neuauflage **aller** Manifeste + Layer‑JSON in **einem** Batchlauf mit **schriftlichem Batch‑Report**. | **ja**, sorgfältig |

Zwischen PR‑A merge und Start von PR‑B: kurze Abstimmung in Chat oder PR‑Kommentar, falls sich die Liste der `incoming/`-PDFs geändert hat.

---

## Governance: geschützte Pfade (`NO-SILENT-DELETIONS`)

Unter **`research/**`** gilt der Schutz gegen stille Löschung.

- PR‑B **muss** pro Commit (oder `.agent-os/pr-spec.json`) Zeilen **`approved_deletions:`** mit allen entfernten Präfixen/Pfaden führen, **oder** die Pfade dort als Liste haben.  
- Zusätzlich: Chat‑Freigabe (diese orch‑Spezifikation gilt als Produktintent; die technische Liste der Pfade kommt aus dem Inventar‑Script‑Output vom Tag vor PR‑B).

---

## Produktziele für die Neuauflage (Detailtiefe vs. Terra‑052)

1. **Ein Batch‑Token** für alle Neu‑Slugs dieser Runde — z. B. gemeinsamer UTC‑Suffix **`_20260508TxxxxxxZ`** (konkretes Datum/Uhrzeit legt PR‑B fest). Alle `document_id` im Batch teilen denselben Suffix oder ein explizites `batch_tag` Feld in einem neuen **`batch_report.json`** (siehe unten).

2. **L1–L4 vollständig** pro Dokument gemäß `research/schema/manifest.schema.json`; keine „complete“ ohne Artefakte, die unter `artifacts` geführt werden.

3. **Verbesserte Filterbarkeit:**
   - L3/L4 mit **stabilem Vokabular** für `methods`, `limitations`, Entities (über `schemas` konsistent halten — Research‑Agent dokumentiert eingesetztes Tagset im Batch‑Report).
   - **`l4_formulas.json`** (neues Schema **`l4_formulas.schema.json`**) **pro Dokument Pflicht**, sobald das PDF **≥ 1** nicht‑triviale Gleichung/Definition im Haupttext enthält; wenn gar keine Formeln: leeres `formulas: []` **plus** ein Satz in `notes` im Formeln‑JSON, warum leer.

4. **Formeln:**  
   - **Darstellung:** `presentation.latex` und `presentation.unicode_plain` (lesbar ohne Renderer).  
   - **Warum diese Form:** Pflichtfeld `rationale.why_this_form` (Paper‑Autoren‑Intent, keine Halluzination — bei Unklarheit `confidence: low` + kurze Quelle).  
   - **Symbole:** `symbols[]` mit `symbol`, `description`, Einheit wenn relevant.  
   - **Evidenz:** Seiten + optional `verbatim_snippet` (kurz).

5. **Batch‑Ausgabe (ein Artefakt im Repo‑Root unter `research/work/` oder `research/extracted/_batch_reports/` — Entscheidung PR‑B):**  
   - Datei **`batch_report.json`** mit:  
     - `batch_id`, `started_at`, `completed_at`, `extractor_version`  
     - `documents[]`: je `document_id`, `manifest_path`, Status pro Layer, **`pdf_sha256`**, Liste neuer Artefakte  
     - **`validation`**: jq/jsonschema‑Exit‑Codes oder „manual ok“ Flags  
     - **`formula_stats`**: Anzahl extrahierter Formeln je Dokument.

   (Konkretes Unterverzeichnis legt PR‑B fest; diese Spezifikation verlangt nur: **ein** zusammenhängender Report‑JSON pro Batch.)

---

## Research‑Agent — Auftragskasten für PR‑B (copy‑paste‑fertig)

1. `git checkout main` nach Merge von PR‑A; Branch `research/pdf-extraction-batch-<batch_id>` anlegen.  
2. Inventar vor Löschen:  
   `py scripts/research/list_extraction_inventory.py --json > research/work/inventory_before_<batch_id>.json`  
3. Für alle Ziel‑PDFs in `research/incoming/*.pdf`: alte **`research/extracted/<alter_document_id>/`** Bäume entfernen, die zu **dieselben** inhaltlichen Werken gehören (Namenszuordnung über Titel/Hash im Report dokumentieren).  
4. Slug‑Erzeugung: `py scripts/research/pdf_ingest_slug.py …` mit **gemeinsamem** Batch‑Timestamp.  
5. L0→L4 neu; **`l4_formulas.json`** validieren gegen `research/schema/l4_formulas.schema.json`.  
6. `manifest.notes` um **eine** Semikolon‑Gruppe erweitern: `pdf_sha256=…; extractor=…; layers_run=L1,L2,L3,L4; formula_layer=l4_formulas`.  
7. Batch‑Report schreiben; alle Manifeste jsonschema‑validieren (`tests/test_research_manifest_jsonschema.py` Muster).  
8. PR‑B mit **`approved_deletions:`** im Commit‑Body (vollständige Liste der gelöschten Pfade).

---

## Außerhalb des Scopes

- Backend/Frontend‑Code.  
- Änderung an `manifest.schema.json` **`const` manifest_version** — nur nach expliziter orch‑/schema‑Revision (aktuell bleibt `0.1.0`).

---

## Referenzen

- `research/README.md`, `research/schema/manifest.schema.json`  
- `archive/legacy-docs/Implementierung.research.l0_to_l4.md`  
- `scripts/research/pdf_ingest_slug.py`  
- `.cursor/rules/NO-SILENT-DELETIONS.mdc`
