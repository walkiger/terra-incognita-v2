# Entscheidungen — Übersicht (v2)

**Kanone (Thin-Shell MVP):** [`app/docs/greenfield/decisions/README.md`](../../app/docs/greenfield/decisions/README.md) — dort liegen die ADRs für das neue Produkt.

**Historischer Anhang (Persistenz DuckDB-Ära, archiviert):** [`decisions-archive-persistence-duckdb-era.md`](decisions-archive-persistence-duckdb-era.md) — nur Kontext; technische Kanone für Speicher ist Greenfield **SQLite/Litestream** (siehe ADR‑001 im Ordner oben).

---

**2026-05-09 — Orch:** `.agent-os/pr-spec.json` auf Branch **`chore/knowledge-research-corpus`** zurückgeführt (vorher fälschlich M0.1/`main`). Lokaler Testlauf: `py -m pytest tests/test_repo_layout.py -q` → grün.

**2026-05-09 — Orch:** Ungetracktes **`scripts/`**‑Tooling (CI/Agent‑Helfer, Research‑Utilities) **nicht** in den Knowledge‑Corpus‑PR; eigenständiger Follow‑up (Branch‑Vorschlag in `pr-spec` Tasks). Nur CRLF‑Noise auf `scripts/rewrite_legacy_path_references.py` per `git checkout --` bereinigt.
