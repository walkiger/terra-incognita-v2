# research/ — PDF & unstructured ingestion (γ skeleton)

Workspace for the **research-agent**: deep PDF analysis with **trackable layers**. Production backend code stays out of here; only data, manifests, schemas, and optional extraction helpers belong here.

## Layout

| Path | Purpose |
|------|---------|
| `incoming/` | **Drop zone** für PDFs während Ingest. **`*.pdf` wird nicht versioniert** (siehe `.gitignore`). |
| `work/` | Mischung aus kurzlebigen Artefakten und **referenzierbaren** Inventaren/Spezifikationen — siehe Dateikopf-Kommentare und Batch-Doku unten. |
| `extracted/` | **Versionierte Artefakte** pro Dokument (JSON/Text gemäß Manifest). **`source.pdf` unter jedem `extracted/<id>/` wird nicht committed** (~binary); bei Bedarf aus PDF neu einspielen (`incoming/` → Ingest). |
| `schema/` | JSON Schemas for manifests and future extraction DTOs. |

## Layer model (L0 → L4)

Progress is recorded in **`extracted/<document_id>/manifest.json`** (see `schema/manifest.schema.json`).

| Layer | Goal | Typical artifacts |
|-------|------|---------------------|
| **L0** | Document identity & bookkeeping | `manifest.json` created; optional file stats |
| **L1** | Barebones text extraction | `l1_raw_text.json` (per-page or single blob + offsets) |
| **L2** | Structural outline | `l2_outline.json` (sections, headings, page spans) |
| **L3** | Structured entities | `l3_entities.json` (authors, citations, definitions, figures refs) |
| **L4** | Deep analysis | `l4_analysis.json` (claims, methods, limitations — prose + structured fields) |
| **L4‑Formeln** *(optional sidecar, batch regen v1)* | Filterbare Gleichungen mit Begründung | `l4_formulas.json` → [`schema/l4_formulas.schema.json`](schema/l4_formulas.schema.json) |

**Rule:** Do not skip layers in the manifest; mark a layer `skipped` with a `reason` string if intentionally deferred.

**Corpus snapshot (2026-05-08):** Full L0–L4 + `l4_formulas` for **64** documents — canonical inventory JSON [`work/inventory_2026-05-08.json`](work/inventory_2026-05-08.json); batch machine summary [`work/_batch_reports/batch_report_2026-05-08.json`](work/_batch_reports/batch_report_2026-05-08.json).

**Batch-Neuauflage (geplant):** Zwei‑PR‑Ablauf und Research‑Agent‑Auftrag — [`work/BATCH_REGEN_PDF_EXTRACTION_SPEC.md`](work/BATCH_REGEN_PDF_EXTRACTION_SPEC.md). Inventar‑Script: [`scripts/research/list_extraction_inventory.py`](../scripts/research/list_extraction_inventory.py).

## `document_id`

Stable id derived from the PDF basename **without** `.pdf`. The title-derived portion is lowercased to `[a-z0-9_-]+` (`scripts/research/pdf_ingest_slug.py`). When ingested via the batch slug helper, a UTC suffix **`_<YYYYMMDD>T<HHMMSS>Z`** is appended (`strftime`, typically uppercase **`T`** / **`Z`**). Pass **`--ts-lowercase`** to emit **`t`/`z`** instead (schema accepts either). Example: `some_paper_title_20260507T081859Z`. Full grammar is locked in `schema/manifest.schema.json`.

## `pdf_sha256` (optional, R1)

**SHA-256** of the ingested PDF file (**64** lowercase hex chars). **Prefer** this top-level field over duplicating the digest only inside **`notes`**. Ingest and batch-fill scripts write the field (`scripts/research/pdf_ingest_slug.py`, `scripts/research/batch_fill_research_layers.py`). Validated by `schema/manifest.schema.json`; see tests `tests/test_research_manifest_jsonschema.py` and `tests/test_research_pdf_sha256_writers.py`.

- Untrusted input — normalize; never execute embedded PDF scripts.
- Outputs must be structured (JSON + schema where provided).
- No backend/API implementation in this tree — propose schemas only.

## Related

- Cursor rule: `.cursor/rules/RESEARCH-DATA-RULES.mdc`
- Agent definition: `.cursor/agents/research-agent.md`
